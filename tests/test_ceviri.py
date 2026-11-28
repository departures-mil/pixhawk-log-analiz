"""Çeviri Merkezi: motor sırası, sözlük/kalite denetimi, çeviri hafızası, belge (DOCX/PDF/görüntü), OCR, çevrimdışı paket indirme."""
import hashlib, http.server, io, json, os, re, shutil, threading, time, zipfile
import pytest
from app.core import ceviri as CV, belge as B, ocr as O, paketler as PK


class Fake(CV.Engine):
    """Kelime başına işaret koyan sahte motor (etiketleri korur)."""
    def __init__(self, name='fake', markup=True, fail=False, rank=50, tag='llm'):
        self.name, self.markup, self.fail, self.rank, self.tag = name, markup, fail, rank, tag
        self.calls = 0

    def batch(self, segs, src, tgt, ents, iss):
        self.calls += 1
        if self.fail: raise RuntimeError('down')
        return [re.sub(r'(?<![<\d/])\b([A-Za-zÇĞİŞÖÜçğışöü]{2,})\b', lambda m: f'{tgt}:{m.group(1)}', s) for s in segs]


@pytest.fixture
def tm(tmp_path):
    return CV.TM(str(tmp_path / 'tm.sqlite'))


def test_detect():
    assert CV.detect('The aircraft must be checked before flight.') == 'en'
    assert CV.detect('Uçuş öncesi kontrol yapılmalı ve batarya değiştirilmeli.') == 'tr'
    assert CV.detect('يجب فحص الطائرة قبل الطيران.') == 'ar'
    assert not CV.needs('Q_ASSIST_SPEED') and not CV.needs('12.5') and CV.needs('Check the GPS')


def test_quality_check_terms_numbers_ids():
    ents = CV.entries({'tx_terms': [{'en': 'tail boom', 'tr': 'kuyruk kirişi', 'ar': 'ذراع الذيل'}]})
    src = 'Pre-arm checks failed: set Q_ASSIST_SPEED to 16 and inspect the tail boom.'
    good = 'Arm öncesi kontrol başarısız: Q_ASSIST_SPEED değerini 16 yapın ve kuyruk kirişini inceleyin.'
    assert CV.check(src, good, 'en', 'tr', ents) == []
    bad = 'Ön kol başarısız: ASSIST hızını 15 yapın ve kuyruğu inceleyin.'
    kinds = {k for k, _, _ in CV.check(src, bad, 'en', 'tr', ents)}
    assert {'term', 'num', 'id'} <= kinds
    # Arapça hedef: parantez içindeki uluslararası ad da kabul
    assert not [x for x in CV.check('Throttle failsafe', 'وضع الطوارئ للخانق', 'en', 'ar', ents) if x[0] == 'term']
    # TR → AR yönünde de kaynak terim bulunur
    rel = [e.en for e in CV.relevant('Uçuştan önce arm öncesi kontrol yapıldı, gaz kesildi', 'tr', ents)]
    assert 'pre-arm' in rel and 'throttle' in rel


def test_translator_order_fallback_tm_and_user_correction(tm):
    a, b = Fake('A', fail=True), Fake('B')
    T = CV.Translator({}, None, tm, [a, b])
    out = T.run(['Motor failure on landing.', '42', 'Q_ASSIST_SPEED'], 'en', 'tr')
    assert out[0].startswith('tr:Motor') and out[1] == '42' and out[2] == 'Q_ASSIST_SPEED'
    assert a.calls == 1 and b.calls == 1 and T.report['engines'] == {'B': 1}
    # ikinci kez: hafızadan (motor çağrılmaz)
    T2 = CV.Translator({}, None, tm, [b]); T2.run(['Motor failure on landing.'], 'en', 'tr')
    assert b.calls == 1 and T2.report['tm'] == 1
    # kullanıcı düzeltmesi her şeyden önce gelir
    tm.put('Motor failure on landing.', 'en', 'tr', 'İnişte motor arızası.', 'user')
    assert CV.Translator({}, None, tm, [b]).run(['Motor failure on landing.'], 'en', 'tr') == ['İnişte motor arızası.']
    # daha düşük dereceli önbellek, daha iyi motor varken kullanılmaz
    tm.put('Stall warning.', 'en', 'ar', 'nllb-out', 'nllb')
    assert CV.Translator({}, None, tm, [Fake('LLM')]).run(['Stall warning.'], 'en', 'ar')[0] != 'nllb-out'
    tm.put('Spin warning.', 'en', 'ar', 'nllb-out', 'nllb')
    assert CV.Translator({}, None, tm, [Fake('N', rank=20, tag='nllb')]).run(['Spin warning.'], 'en', 'ar')[0] == 'nllb-out'
    # motor yoksa ve hafızada da yoksa anlaşılır hata
    with pytest.raises(CV.NoEngine):
        CV.Translator({'lang': 'tr'}, None, tm, []).run(['Brand new sentence here.'], 'en', 'tr')


def test_markup_stripped_for_plain_engines(tm):
    e = Fake('plain', markup=False)
    out = CV.Translator({}, None, tm, [e]).run(['<1>Date:</1><2> today</2>'], 'en', 'tr')
    assert '<' not in out[0]


def test_builtin_memory_used_for_param_texts(tm):
    d = CV.TM.builtin('tr')
    if not d: pytest.skip('params_tx yok')
    en, trx = next(iter(d.items()))
    hit = tm.get(en, 'en', 'tr')
    assert hit and hit[1] == 'builtin'


def test_translate_text_keeps_structure(tm, monkeypatch):
    monkeypatch.setattr(CV, '_tm', lambda: tm)
    out, rep = CV.translate_text('1. Check battery\n\n- Inspect propeller\n|||\nQ_ENABLE', 'en', 'tr', {}, None,
                                 translator=CV.Translator({}, None, tm, [Fake()]))
    lines = out.split('\n')
    assert lines[0] == '1. tr:Check tr:battery' and lines[1] == '' and lines[2].startswith('- tr:Inspect') and lines[3] == '|||' and lines[4] == 'Q_ENABLE'


def test_engine_selection_modes(monkeypatch, tmp_path):
    monkeypatch.setenv('PX_PACKS_DIR', str(tmp_path))
    s = {'gemini_key': 'AIzaXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX', 'free_ai': True}
    names = [type(e).__name__ for e in CV.engines(s, net=True)]
    assert names[0] == 'LLMEngine' and 'GoogleEngine' in names and 'NLLBEngine' not in names
    assert CV.engines(dict(s, tx_private=True), net=True) == []          # gizli belge: sunucuya gönderilmez
    d = tmp_path / 'nllb-3.3b'; d.mkdir(); (d / '.ok').write_text('{}')
    e = CV.engines(dict(s, tx_mode='offline'), net=True)
    assert [type(x).__name__ for x in e] == ['NLLBEngine'] and e[0].name == 'NLLB-200 3.3B'
    e = CV.engines(s, net=False)                                         # internet yok → çevrimdışı
    assert [type(x).__name__ for x in e] == ['NLLBEngine']
    e = CV.engines(s, net=True)
    assert type(e[-1]).__name__ == 'NLLBEngine'                         # çevrimiçi önce, en sonda çevrimdışı


def test_llm_engine_prompt_glossary_and_review(monkeypatch):
    from app.core import ai
    seen = []

    def chat(settings, usage, prov, system, prompt, mt):
        seen.append((system, prompt))
        arr = json.loads(prompt[prompt.index('['):])
        if 'chief aviation editor' in prompt:
            return json.dumps(['REVIEWED ' + x['draft'] for x in arr], ensure_ascii=False)
        return json.dumps(['Arm öncesi kontrol başarısız; gaz %d.' % 50 if 'Pre-arm' in x else 'x' for x in arr])
    monkeypatch.setattr(ai, '_chat1', chat)
    e = CV.LLMEngine({}, None, 'gemini', 'max')
    out = e.batch(['Pre-arm check failed; throttle 50.', 'Hello'], 'en', 'tr', CV.entries({}), [])
    assert out[0].startswith('REVIEWED Arm öncesi') and len(seen) == 2
    assert 'arm öncesi kontrol' in seen[0][0] and 'gaz' in seen[0][0] and 'Formal' in seen[0][0]
    # bozuk cevap → hata (sıradaki motora geçilir)
    monkeypatch.setattr(ai, '_chat1', lambda *a: 'not json')
    with pytest.raises(Exception):
        CV.LLMEngine({}, None, 'free', 'std').batch(['a b'], 'en', 'tr', [], [])


def test_google_engine_protects_terms(monkeypatch):
    g = CV.GoogleEngine()
    sent = []

    def one(text, src, tgt):
        sent.append(text)
        return text.replace('the', 'bu')   # yer tutucular aynen döner
    monkeypatch.setattr(g, '_one', one)
    out = g.batch(['Set FBWA and check the airspeed sensor before arming.'], 'en', 'tr', [], [])
    assert 'XQ' in sent[0] and 'FBWA' in out[0] and 'hava hızı' in out[0]


def test_nllb_pipeline_pivot_and_placeholders(monkeypatch, tmp_path):
    e = CV.NLLBEngine(str(tmp_path))
    calls = []

    def raw(sents, src, tgt):
        calls.append((src, tgt, list(sents)))
        return [f'[{tgt}]' + s for s in sents]
    monkeypatch.setattr(e, '_raw', raw)
    out = e.batch(['Uçuş tamam. Q_ENABLE açık.\nİkinci satır.'], 'tr', 'ar', [], [])
    assert [c[:2] for c in calls] == [('tr', 'en'), ('en', 'ar')]          # İngilizce pivot
    assert 'Q_ENABLE' in out[0] and '\n' in out[0]
    assert len(calls[0][2]) == 3                                           # cümlelere bölündü


# ---------------------------------------------------------------- belgeler
def _png(tmp_path, color='red', size=(240, 120)):
    from PIL import Image
    p = tmp_path / f'{color}.png'; Image.new('RGB', size, color).save(p)
    return str(p)


@pytest.fixture
def fake_engines(monkeypatch, tm):
    monkeypatch.setattr(CV, '_tm', lambda: tm)
    monkeypatch.setattr(CV, 'engines', lambda s, u=None, net=None: [Fake()])


def test_docx_keeps_images_format_and_rtl(tmp_path, fake_engines):
    import docx
    d = docx.Document()
    p = d.add_paragraph(); r = p.add_run('Tarih: '); r.bold = True; p.add_run('uçuş yapıldı.')
    t = d.add_table(rows=1, cols=2); t.cell(0, 0).text = 'Parça'; t.cell(0, 1).text = 'Pervane'
    d.add_paragraph().add_run().add_picture(_png(tmp_path))
    d.sections[0].header.paragraphs[0].text = 'Bakım birimi'
    src = tmp_path / 'a.docx'; d.save(src)
    dst = tmp_path / 'a_AR.docx'
    rep = B.translate_docx(str(src), str(dst), 'auto', 'ar', {})
    assert rep['src'] == 'tr'
    d2 = docx.Document(dst)
    p0 = d2.paragraphs[0]
    assert p0.runs[0].bold and p0.runs[0].text.startswith('ar:Tarih') and not p0.runs[1].bold   # paragraf içi biçim korundu
    assert len(d2.inline_shapes) == 1                                                              # resim korundu
    assert d2.tables[0].cell(0, 1).text == 'ar:Pervane'
    assert d2.sections[0].header.paragraphs[0].text.startswith('ar:Bakım')
    x = zipfile.ZipFile(dst).read('word/document.xml').decode()
    assert '<w:bidi/>' in x and '<w:rtl/>' in x and '<w:bidiVisual/>' in x and 'w:cs="Arial"' in x
    assert '<w:jc w:val="center"/>' in x                                                           # resim paragrafı ortalandı
    # Arapçadan geri: sağdan sola kaldırılır
    back = tmp_path / 'b.docx'
    B.translate_docx(str(dst), str(back), 'ar', 'tr', {})
    assert '<w:bidi/>' not in zipfile.ZipFile(back).read('word/document.xml').decode()


def test_docx_fields_are_not_moved(tmp_path, fake_engines):
    import docx
    from docx.oxml import parse_xml
    d = docx.Document()
    p = d.add_paragraph('Page ')
    W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    for xml in (f'<w:r {W}><w:fldChar w:fldCharType="begin"/></w:r>', f'<w:r {W}><w:instrText> PAGE </w:instrText></w:r>',
                f'<w:r {W}><w:fldChar w:fldCharType="separate"/></w:r>', f'<w:r {W}><w:t>1</w:t></w:r>', f'<w:r {W}><w:fldChar w:fldCharType="end"/></w:r>'):
        p._p.append(parse_xml(xml))
    p.add_run(' of report')
    src = tmp_path / 'f.docx'; d.save(src); dst = tmp_path / 'f2.docx'
    B.translate_docx(str(src), str(dst), 'en', 'tr', {})
    x = zipfile.ZipFile(dst).read('word/document.xml').decode()
    assert 'PAGE' in x and x.index('tr:Page') < x.index('fldCharType="begin"') < x.index('tr:report')


def test_pdf_same_layout_keeps_images(tmp_path, fake_engines):
    pymupdf = B._pdf()
    from reportlab.pdfgen import canvas
    src = tmp_path / 'r.pdf'
    c = canvas.Canvas(str(src)); c.setFont('Helvetica', 12)
    c.drawString(60, 760, 'The aircraft landed after a motor failure.'); c.drawImage(_png(tmp_path), 100, 500, 200, 100)
    c.drawString(60, 470, 'Figure 1 propeller damage'); c.save()
    dst = tmp_path / 'r_TR.pdf'
    rep = B.translate_pdf(str(src), str(dst), 'en', 'tr', {})
    doc = pymupdf.open(str(dst))
    txt = doc[0].get_text()
    assert 'tr:aircraft' in txt and 'tr:propeller' in txt and 'The aircraft' not in txt
    assert len(doc[0].get_images()) == 1 and rep['scanned'] == 0


def test_pdf_scanned_page_gets_translation_page(tmp_path, fake_engines, monkeypatch):
    pymupdf = B._pdf()
    src = tmp_path / 's.pdf'
    d = pymupdf.open(); pg = d.new_page()
    pg.insert_image(pg.rect, filename=_png(tmp_path, 'white', (595, 842))); d.save(str(src))
    monkeypatch.setattr(O, 'ocr', lambda im, lg, s=None, u=None: ('Battery voltage low.', 'test'))
    dst = tmp_path / 's_TR.pdf'
    rep = B.translate_pdf(str(src), str(dst), 'en', 'tr', {})
    doc = pymupdf.open(str(dst))
    assert rep['scanned'] == 1 and doc.page_count == 2 and 'tr:Battery' in doc[1].get_text()


def test_image_to_docx_and_txt(tmp_path, fake_engines):
    import docx
    img = _png(tmp_path, 'blue'); dst = tmp_path / 'i.docx'
    B.translate_image(img, str(dst), 'en', 'ar', {}, ocr_text='Replace the propeller.')
    d = docx.Document(dst)
    assert len(d.inline_shapes) == 1 and any('ar:Replace' in p.text for p in d.paragraphs)
    t = tmp_path / 'n.txt'; t.write_text('Check GPS.\nCheck compass.', encoding='utf-8')
    B.translate_file(str(t), str(tmp_path / 'n_TR.txt'), 'en', 'tr', {})
    assert (tmp_path / 'n_TR.txt').read_text(encoding='utf-8').splitlines() == ['tr:Check tr:GPS.', 'tr:Check tr:compass.']
    assert B.out_name('C:/x/form.jpg', 'ar').endswith('form_AR.docx')


# ---------------------------------------------------------------- OCR
def test_ocr_helpers():
    tsv = ('level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
           '5\t1\t1\t1\t1\t1\t10\t10\t50\t20\t96\tPervane\n5\t1\t1\t1\t1\t2\t70\t10\t50\t20\t90\tdeğişti\n'
           '5\t1\t2\t1\t1\t1\t10\t60\t50\t20\t80\tO\n5\t1\t2\t1\t1\t2\t30\t60\t50\t20\t80\tASSIST\n5\t1\t2\t1\t1\t3\t90\t60\t50\t20\t80\tSPEED\n')
    text, conf, n, blocks = O.parse_tsv(tsv)
    assert text == 'Pervane değişti\n\nO ASSIST SPEED' and n == 5 and len(blocks) == 2
    assert O.fix_ids(text).endswith('Q_ASSIST_SPEED') and O.fix_ids('BAKIM FORMU') == 'BAKIM FORMU'
    from PIL import Image
    dark = Image.new('RGB', (400, 100), (20, 20, 20))
    assert O.prepare(dark).getpixel((5, 5)) > 200            # koyu tema ekran görüntüsü ters çevrilir


@pytest.mark.skipif(not O.offline_available(), reason='tesseract yok')
def test_ocr_offline_real(tmp_path):
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(os.path.join(B._fonts_dir(), 'Inter-400.ttf'), 24)
    im = Image.new('RGB', (900, 120), 'white'); ImageDraw.Draw(im).text((20, 30), 'Pervane değişimi yapıldı: 25,2 V', font=f, fill='black')
    t = O.ocr_offline(im, 'auto')
    assert 'Pervane' in t and '25,2' in t


# ---------------------------------------------------------------- paketler
class _H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        p = self.translate_path(self.path)
        data = open(p, 'rb').read()
        rng = self.headers.get('Range')
        if rng:
            a = int(rng.split('=')[1].split('-')[0])
            self.send_response(206); self.send_header('Content-Length', str(len(data) - a)); self.end_headers(); self.wfile.write(data[a:])
        else:
            self.send_response(200); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)


def test_pack_download_parts_sha_resume_unzip(tmp_path, monkeypatch):
    srv_dir = tmp_path / 'srv'; srv_dir.mkdir()
    blob = os.urandom(300_000)
    parts = [blob[:120_000], blob[120_000:]]
    for i, x in enumerate(parts): (srv_dir / f'model.bin.p{i}').write_bytes(x)
    (srv_dir / 'config.json').write_text('{}')
    z = io.BytesIO()
    with zipfile.ZipFile(z, 'w') as zf: zf.writestr('Tesseract-OCR/tesseract.exe', b'exe'); zf.writestr('Tesseract-OCR/tessdata/tur.traineddata', b'x')
    (srv_dir / 'ocr.zip').write_bytes(z.getvalue())
    H = lambda b: hashlib.sha256(b).hexdigest()
    handler = lambda *a, **k: _H(*a, directory=str(srv_dir), **k)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    u = f'http://127.0.0.1:{srv.server_port}/'
    man = {'packs': {
        'nllb-1.3b': {'version': '1', 'files': [
            {'path': 'model.bin', 'size': len(blob), 'sha256': H(blob),
             'parts': [{'url': u + f'model.bin.p{i}', 'size': len(x), 'sha256': H(x)} for i, x in enumerate(parts)]},
            {'path': 'config.json', 'size': 2, 'sha256': H(b'{}'), 'url': u + 'config.json'}]},
        'ocr': {'version': '1', 'files': [{'path': 'ocr.zip', 'size': len(z.getvalue()), 'sha256': H(z.getvalue()), 'url': u + 'ocr.zip', 'unzip': True}]}}}
    monkeypatch.setenv('PX_PACKS_DIR', str(tmp_path / 'packs'))
    # yarım kalmış parça: kaldığı yerden devam
    part_dir = tmp_path / 'packs' / 'nllb-1.3b.part'; part_dir.mkdir(parents=True)
    (part_dir / 'model.bin.p00').write_bytes(parts[0][:50_000])
    seen = []
    d = PK.download('nllb-1.3b', lambda a, b: seen.append((a, b)), man=man)
    assert open(os.path.join(d, 'model.bin'), 'rb').read() == blob and PK.installed('nllb-1.3b')
    assert seen[-1][0] == seen[-1][1] == PK.total_size(man['packs']['nllb-1.3b'])
    assert PK.nllb_dir() == d and PK.nllb_dir('nllb-3.3b') == d
    PK.download('ocr', man=man)
    assert PK.tesseract_exe().endswith('tesseract.exe') and PK.tessdata_dir().endswith('tessdata')
    # iptal
    PK.remove('nllb-1.3b')
    with pytest.raises(PK.Cancelled):
        PK.download('nllb-1.3b', cancel=lambda: True, man=man)
    assert not PK.installed('nllb-1.3b')
    # bozuk SHA reddedilir
    man['packs']['nllb-1.3b']['files'][1]['sha256'] = '0' * 64
    PK.remove('nllb-1.3b')
    with pytest.raises(RuntimeError):
        PK.download('nllb-1.3b', man=man)
    srv.shutdown()


# ---------------------------------------------------------------- arayüz
def _wait(qapp, cond, sec=20):
    t = time.time()
    while time.time() - t < sec:
        qapp.processEvents()
        if cond(): return True
        time.sleep(0.02)
    return False


def test_translate_page_ui(win, qapp, monkeypatch, tm):
    monkeypatch.setattr(CV, '_tm', lambda: tm)
    monkeypatch.setattr(CV, 'engines', lambda s, u=None, net=None: [Fake('Google Gemini')])
    win.goto('translate'); qapp.processEvents()
    pg = win.pages['translate']
    assert pg.tabs.count() == 5
    pg.t_in.setPlainText('Pre-arm check failed.\nReplace the propeller.')
    pg.t_tgt.setCurrentIndex(pg.t_tgt.findData('ar'))
    pg.translate_now()
    assert _wait(qapp, lambda: pg.t_out.toPlainText().startswith('ar:'))
    assert pg.t_out.document().defaultTextOption().textDirection() == __import__('PySide6.QtCore', fromlist=['Qt']).Qt.RightToLeft
    assert 'Google Gemini' in pg.t_rep.text()
    # düzeltmeyi kaydet → hafıza tablosunda görünür
    pg.t_out.setPlainText('فشل فحص ما قبل التسليح.\nاستبدل المروحة.')
    pg._save_fix()
    assert pg.tm_tbl.rowCount() == 2
    # sözlüğe kullanıcı terimi
    pg.g_en.setText('tail boom'); pg.g_tr.setText('kuyruk kirişi'); pg.g_ar.setText('ذراع الذيل'); pg._add_term()
    assert pg.g_tbl.item(0, 0).text() == 'tail boom'
    win.settings['tx_terms'] = []
    # paket listesi
    assert pg.p_tbl.rowCount() == 3
    os.makedirs('/tmp/px-shots', exist_ok=True)
    win.grab().save('/tmp/px-shots/ceviri.png')
