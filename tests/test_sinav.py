"""v1.1.11 Sınav: görselli grafik soruları, yorum (açık uçlu) puanlama, optik form okuma, kâğıt sınav PDF'leri, telefon sunucusu,
Sınav sekmesi arayüzü."""
import base64, io, json, os, random, urllib.request
import numpy as np
import pytest

from app.core import qbank as QB, exam as X, visq, omr, paper


def _archive(tmp_path):
    from app.core.archive import Archive
    return Archive(str(tmp_path / 'a.db'))


def test_visual_pool():
    vis = [q for q in QB.builtin() if q.get('img')]
    assert len(vis) >= 200
    kinds = {(q.get('case') or {}).get('label') for q in vis}
    assert {'crash', 'normal'} <= kinds
    hints = {bool((q.get('case') or {}).get('hint')) for q in vis}
    assert hints == {True, False}          # ipuçlu (gerçek işaretli) ve ipuçsuz grafikler birlikte
    assert any(QB.is_open(q) for q in vis) and any(not QB.is_open(q) for q in vis)
    for q in vis:
        assert QB.validate(q) is None, q['id']
        assert all((q['q'] or {}).get(lg) for lg in ('tr', 'en', 'ar')), q['id']
    for ref in {q['img'] for q in vis}:
        b = QB.img_bytes(ref)
        assert b and b[:4] == b'\x89PNG', ref


def test_open_scoring():
    kw = {'tr': list(visq.KW['vibration'])}
    good = 'Titreşim çok yüksek, Z ekseni 60 sınırını geçiyor, pervaneler dengesiz, EKF bozuldu ve araç düştü'
    sc, hit = visq.score_open(good, kw); assert visq.suggest_points(sc) == 1
    wrong = 'GPS uydu sayısı düştü, pusula hatası var, kumanda sinyali kesildi ve araç kontrolsüz kaldı'
    assert visq.suggest_points(visq.score_open(wrong, kw)[0]) == 0
    # 60 içinde "6" sayılmaz; ana kavram yoksa en çok yarım puan
    n = {'tr': list(visq.KW['normal'])}
    assert visq.suggest_points(visq.score_open('Titreşim arttı, Z ekseninde 60 üstü; pervaneleri dengeleyin, EKF bozuldu', n)[0]) <= 0.5
    assert visq.score_open('', kw)[0] == 0


def _exam(arc, n_mc=3, n_open=1, lang='tr'):
    rnd = random.Random(3); vis = [q for q in QB.builtin() if q.get('img')]
    pick = rnd.sample([q for q in vis if not QB.is_open(q)], n_mc) + rnd.sample([q for q in vis if QB.is_open(q)], n_open)
    qs = [QB.to_item(q, lang, rnd) for q in pick]
    cid = X.create_class(arc, 'S1', 'H', ['1023 Ali Veli', '1024 Ayşe Kaya'])
    eid = X.create_exam(arc, cid, 'Grafik sınavı', None, lang, len(qs), 30, 60, {'type': 'builder'}, questions=qs)
    return arc.rec_get('exam', eid)


def test_grade_and_regrade(tmp_path):
    arc = _archive(tmp_path); ex = _exam(arc)
    assert len(ex['code']) == 4 and ex['code'].isdigit()
    ans = [q['ans'] if q.get('type') != 'open' else 'kısa' for q in ex['questions']]
    r = X.save_result(arc, ex, 'Ali', ans, 0, 60)
    assert r['score'] == 3 and X.pending(ex, r) == 1
    k = str(next(i for i, q in enumerate(ex['questions']) if q.get('type') == 'open'))
    r2 = X.regrade(arc, r, {k: 1})
    assert r2['score'] == 4 and r2['pct'] == 100 and r2['passed'] and r2['cert_id'] and X.pending(ex, r2) == 0
    r3 = X.regrade(arc, r2, {k: 0.5}); assert r3['score'] == 3.5


def _sheet_photo(n, ans, no, rot=3):
    """PDF'e gerek olmadan optik formun benzeri: köşe kareleri + işaretli kabarcıklar, döndürülmüş ve gürültülü."""
    from PIL import Image, ImageDraw, ImageFilter
    px = 6.0; W, H = int(210 * px), int(297 * px)
    im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im)
    s = omr.L['fid']['size']
    for x, y in omr.L['fid']['pos']: d.rectangle([x * px, y * px, (x + s) * px, (y + s) * px], fill='black')
    r = omr.L['r'] * px

    def bub(x, y, fill):
        d.ellipse([x * px - r, y * px - r, x * px + r, y * px + r], outline=(90, 90, 90), width=2, fill=(35, 35, 40) if fill else None)
    for q in range(n):
        for k in range(4):
            bub(*omr.ans_xy(q, k), (ans[q] == k) or (ans[q] == -2 and k in (0, 2)))
    for c, dg in enumerate(no):
        for v in range(10): bub(*omr.no_xy(c, v), v == int(dg))
    bg = Image.new('RGB', (int(W * 1.2), int(H * 1.15)), (75, 65, 60))
    bg.paste(im.rotate(rot, expand=True, fillcolor=(75, 65, 60)), (50, 70))
    a = np.asarray(bg).astype(float) * np.linspace(1.0, 0.8, bg.width)[None, :, None] + np.random.default_rng(2).normal(0, 8, (bg.height, bg.width, 3))
    out = io.BytesIO(); Image.fromarray(np.clip(a, 0, 255).astype('uint8')).filter(ImageFilter.GaussianBlur(0.7)).save(out, 'JPEG', quality=85)
    return out.getvalue()


def test_omr_read_and_grade(tmp_path):
    n = 30; ans = [(i * 3) % 4 for i in range(n)]; ans[4] = -1; ans[7] = -2
    res = omr.read(_sheet_photo(n, ans, '00001023'), n, 4)
    assert res['ok'], res
    assert res['answers'] == ans
    assert res['no'] == '00001023'
    assert omr.read(b'\xff\xd8not-an-image', 10, 4)['ok'] is False
    arc = _archive(tmp_path); ex = _exam(arc, 3, 1)
    rr = omr.read(_sheet_photo(4, [q['ans'] if q.get('type') != 'open' else -1 for q in ex['questions']], '00001023'), 4, 4)
    r = paper.grade_sheet(arc, ex, rr, ['1023 Ali Veli'])
    assert r['student'] == 'Ali Veli' and r['via'] == 'omr' and r['score'] == 3


@pytest.mark.parametrize('lang', ['tr', 'ar'])
def test_paper_pdfs(tmp_path, lang):
    arc = _archive(tmp_path); ex = _exam(arc, 3, 1, lang)
    for fn, name in ((paper.booklet_pdf, 'b.pdf'), (paper.key_pdf, 'k.pdf')):
        p = fn(ex, str(tmp_path / name)); assert open(p, 'rb').read(5) == b'%PDF-' and os.path.getsize(p) > 20000
    p = paper.sheet_pdf(ex, str(tmp_path / 's.pdf'), 'Okul', 2); assert open(p, 'rb').read(5) == b'%PDF-'
    kt = paper.key_text(ex)
    assert ex['code'] in kt and '4-✎' in kt or '✎' in kt


def test_phone_server(tmp_path):
    from app.core import canli
    arc = _archive(tmp_path); ex = _exam(arc, 3, 1)
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    C = canli.Canli(arc, str(tmp_path))
    st = C.start(ex, ['1023 Ali Veli', '1024 Ayşe Kaya'])
    base = 'http://127.0.0.1:%d/' % st['port']

    def post(p, b):
        rq = urllib.request.Request(base + p, data=json.dumps(b).encode(), headers={'Content-Type': 'application/json'})
        return json.loads(op.open(rq, timeout=10).read())
    try:
        assert b'<html' in op.open(base, timeout=10).read().lower()
        assert post('api/giris', {'ad': 'Ali Veli', 'no': '1023', 'code': '0000'})['ok'] is False
        j = post('api/giris', {'ad': 'Ali Veli', 'no': '1023', 'code': ex['code']})
        assert j['ok'] and len(j['paper']) == 4
        im = next(p['img'] for p in j['paper'] if p.get('img'))
        assert op.open(base + im.lstrip('/'), timeout=10).read()[:4] == b'\x89PNG'
        ans = [0 if p['type'] != 'open' else 'Motor çıkışı doyuma gitti, pervane ve ESC kontrol edilmeli' for p in j['paper']]
        assert post('api/cevap', {'token': j['token'], 'answers': ans, 'final': True})['ok']
        rs = X.results_of(arc, ex['id']); assert len(rs) == 1 and rs[0]['via'] == 'phone' and rs[0]['auto']
        C.set_scan(ex, ['1023 Ali Veli', '1024 Ayşe Kaya'])
        pic = _sheet_photo(4, [q['ans'] if q.get('type') != 'open' else -1 for q in ex['questions']], '00001024')
        r = post('api/okut', {'code': ex['code'], 'image': 'data:image/jpeg;base64,' + base64.b64encode(pic).decode()})
        assert r['ok'] and r['read'] and r['d'] == 3 and r['ad'] == 'Ayşe Kaya'
    finally:
        C.stop()


def test_exam_tab_ui(win, monkeypatch):
    from app.ui import pages_x as PX
    monkeypatch.setattr(PX, 'info', lambda *a, **k: None)
    X.create_class(win.archive, 'Pilot-UI', 'H', ['1 Ali'])
    win.goto('exam'); pg = win.pages['exam']; pg.on_show()
    assert pg.tabs.count() == 3
    b = pg.builder; b.refresh()
    b.typ.setCurrentIndex(b.typ.findData('img')); b.n.setValue(8); b._auto()
    assert len(b.sheet) == 8 and all(q.get('img') for q in b.sheet)
    b._save(False)
    ex = b.last_exam; assert ex and len(ex['questions']) == 8 and ex.get('code')
    pg.tabs.setCurrentIndex(2); pg.s_exam.setCurrentIndex(pg.s_exam.findData(ex['id'])); pg.s_name.setCurrentText('1 Ali'); pg.start()
    for i, q in enumerate(ex['questions']):
        pg.qi = i; pg._show_q()
        if q.get('type') == 'open': pg.s_open.setPlainText('titreşim pervane')
        else: pg.opts[q['ans']].setChecked(True)
        pg._save_ans()
    assert pg.s_img.raw
    monkeypatch.setattr('PySide6.QtWidgets.QMessageBox.question', lambda *a, **k: 0)
    pg.finish(force=True)
    rs = X.results_of(win.archive, ex['id']); assert rs and rs[0]['score'] >= sum(1 for q in ex['questions'] if q.get('type') != 'open')
