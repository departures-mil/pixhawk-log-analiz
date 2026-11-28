"""OCR (görüntüden metin): ekran görüntüsü, fotoğraf, taranmış bakım formu / belge.

Sıra: önce ÇEVRİMİÇİ görü modeli (kullanıcının kendi Gemini / Claude anahtarı, yoksa anahtarsız ücretsiz model),
internet yoksa ya da hata olursa ÇEVRİMDIŞI Tesseract 5 LSTM (tessdata_best; Türkçe + İngilizce + Arapça).
Çevrimdışında görüntü önce iyileştirilir (gri ton, küçükse 2-3 kat büyütme, kontrast); dil 'auto' ise Latin ve Arapça
ayrı ayrı okunup güveni yüksek olan seçilir.
"""
from __future__ import annotations
import base64, io, json, os, re, shutil, subprocess, tempfile
from . import ceviri as CV

PROMPT = ('Transcribe ALL text in this image exactly as written, in its original language (do NOT translate). Keep the reading '
          'order, line breaks, headings, numbered/bulleted lists and form fields ("Label: value"). Render tables as Markdown tables. '
          'Keep numbers, part numbers, parameter names and units exactly. Arabic text must be in normal logical order. '
          'Output only the transcription, no comments.')
TESS_LANG = {'tr': 'tur+eng', 'en': 'eng', 'ar': 'ara+eng'}


class NoOCR(RuntimeError):
    pass


def _img(image):
    from PIL import Image
    if isinstance(image, Image.Image): return image
    if isinstance(image, (bytes, bytearray)): return Image.open(io.BytesIO(image))
    return Image.open(image)


def _png(im, max_side=2400):
    im = im.convert('RGB')
    w, h = im.size; k = max(w, h) / max_side
    if k > 1: im = im.resize((int(w / k), int(h / k)))
    b = io.BytesIO(); im.save(b, 'PNG', optimize=True)
    return b.getvalue()


# ------------------------------------------------------------------ çevrimiçi
def _online(prov, settings, usage, png):
    from . import ai
    b64 = base64.b64encode(png).decode()
    key = ai._keys(settings).get(prov, '')
    if prov == 'gemini':
        g = ai.GeminiAdvisor(None, key, settings.get('gemini_model') or ai.PROVIDERS['gemini']['default'], 'en', usage, 'low')
        d = g._gen({'contents': [{'role': 'user', 'parts': [{'inline_data': {'mime_type': 'image/png', 'data': b64}}, {'text': PROMPT}]}],
                    'generationConfig': g._cfg(8192)})
        c = (d.get('candidates') or [{}])[0].get('content') or {}
        return ''.join(p.get('text', '') for p in c.get('parts', []) if not p.get('thought')).strip()
    if prov == 'anthropic':
        import anthropic
        cl = anthropic.Anthropic(api_key=key, max_retries=2, timeout=180)
        r = cl.messages.create(model=settings.get('model') or ai.PROVIDERS['anthropic']['default'], max_tokens=8000,
                               messages=[{'role': 'user', 'content': [{'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png', 'data': b64}},
                                                                      {'type': 'text', 'text': PROMPT}]}])
        if usage:
            try: usage.add(r.usage, {})
            except Exception: pass
        return ''.join(getattr(b, 'text', '') for b in r.content if getattr(b, 'type', '') == 'text').strip()
    d = ai._free_post({'model': settings.get('free_model') or 'openai', 'max_tokens': 6000, 'temperature': 0,
                       'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': PROMPT},
                                                                 {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + b64}}]}]})
    return ai._free_text(d)[0]


# ------------------------------------------------------------------ çevrimdışı
def tesseract():
    from . import paketler
    exe = paketler.tesseract_exe()
    if exe: return exe, paketler.tessdata_dir()
    exe = os.environ.get('PX_TESSERACT') or shutil.which('tesseract')
    if not exe and os.name == 'nt':
        for c in (r'C:\Program Files\Tesseract-OCR\tesseract.exe', os.path.expandvars(r'%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe')):
            if os.path.isfile(c): exe = c; break
    return (exe, None) if exe else (None, None)


def offline_available():
    return tesseract()[0] is not None


def prepare(im):
    """Tesseract için iyileştirme: gri ton, küçük görüntüyü büyüt (yazı yüksekliği ~30 px), kontrast."""
    from PIL import Image, ImageOps, ImageFilter
    g = ImageOps.exif_transpose(im).convert('L')
    w, h = g.size
    k = 1
    if w < 1000: k = 3
    elif w < 1800: k = 2
    if k > 1: g = g.resize((w * k, h * k), Image.LANCZOS)
    g = ImageOps.autocontrast(g, cutoff=1)
    g = g.filter(ImageFilter.UnsharpMask(radius=1.5, percent=80, threshold=2))
    # koyu tema ekran görüntüsü: zemin koyuysa ters çevir (Tesseract koyu yazı / açık zemin ister)
    hist = g.histogram(); dark = sum(hist[:96]); light = sum(hist[160:])
    if dark > light * 1.4: g = ImageOps.invert(g)
    return g


def _run_tess(exe, tdir, path, langs, psm=3):
    cmd = [exe, path, 'stdout', '-l', langs, '--oem', '1', '--psm', str(psm), '-c', 'preserve_interword_spaces=1']
    if tdir: cmd[3:3] = ['--tessdata-dir', tdir]
    cmd.append('tsv')
    kw = {'creationflags': 0x08000000} if os.name == 'nt' else {}
    r = subprocess.run(cmd, capture_output=True, timeout=600, **kw)
    if r.returncode != 0: raise RuntimeError((r.stderr or b'').decode('utf-8', 'replace')[-300:])
    return parse_tsv(r.stdout.decode('utf-8', 'replace'))


def parse_tsv(tsv):
    """Tesseract TSV → (metin, ortalama güven, kelime sayısı, bloklar[{bbox, text}])."""
    rows = [l.split('\t') for l in tsv.splitlines()[1:]]
    lines = {}; confs = []; boxes = {}
    for r in rows:
        if len(r) < 12 or r[0] != '5': continue
        txt = r[11].strip()
        if not txt: continue
        b, p, ln = int(r[2]), int(r[3]), int(r[4])
        lines.setdefault((b, p, ln), []).append(txt)
        c = float(r[10])
        if c >= 0: confs.append((c, len(txt)))
        x, y, w, h = map(int, r[6:10])
        bb = boxes.setdefault((b, p), [x, y, x + w, y + h, []])
        bb[0] = min(bb[0], x); bb[1] = min(bb[1], y); bb[2] = max(bb[2], x + w); bb[3] = max(bb[3], y + h)
    out = []; prev = None
    for (b, p, ln) in sorted(lines):
        if prev is not None and (b, p) != prev: out.append('')
        out.append(' '.join(lines[(b, p, ln)])); prev = (b, p)
        boxes[(b, p)][4].append(' '.join(lines[(b, p, ln)]))
    n = sum(k for _, k in confs)
    mean = sum(c * k for c, k in confs) / n if n else 0
    blocks = [{'bbox': v[:4], 'text': ' '.join(v[4])} for _, v in sorted(boxes.items())]
    return '\n'.join(out).strip(), mean, len(confs), blocks


def ocr_offline(image, lang='auto', with_blocks=False):
    exe, tdir = tesseract()
    if not exe: raise NoOCR('offline OCR pack not installed')
    im = prepare(_img(image))
    fd, path = tempfile.mkstemp(suffix='.png'); os.close(fd)
    try:
        im.save(path)
        cands = [TESS_LANG[lang]] if lang in TESS_LANG else ['tur+eng', 'ara+eng']
        best = None
        for L in cands:
            try:
                r = _run_tess(exe, tdir, path, L)
            except RuntimeError:
                if L == cands[-1] and best is None: raise
                continue
            score = r[1] * (r[2] ** 0.5)
            if best is None or score > best[0]: best = (score, r, L)
        if not best: raise NoOCR('tesseract failed')
        text, conf, n, blocks = best[1]
        k = im.size[0] / max(1, _img(image).size[0])
        if k != 1:
            for b in blocks: b['bbox'] = [int(v / k) for v in b['bbox']]
        text = fix_ids(text)
        return (text, conf, blocks) if with_blocks else text
    finally:
        try: os.remove(path)
        except OSError: pass


# ------------------------------------------------------------------ genel
def ocr(image, lang='auto', settings=None, usage=None):
    """(metin, motor adı). Önce çevrimiçi görü modeli, olmazsa çevrimdışı Tesseract."""
    s = settings or {}
    last = None
    if CV.mode(s) in ('auto', 'online') and CV.online_ok(s):
        from . import ai
        png = None
        for p in ai._order(s):
            if p == 'free' and not s.get('free_ai', True): continue
            if p != 'free' and not ai._keys(s).get(p): continue
            try:
                png = png or _png(_img(image))
                t = _online(p, s, usage, png)
                if t and t.strip():
                    return _clean(t), {'gemini': 'Google Gemini', 'anthropic': 'Anthropic Claude', 'free': 'Pollinations'}[p]
            except Exception as e:
                last = e
    if CV.mode(s) != 'online' and offline_available():
        return ocr_offline(image, lang), 'Tesseract 5 (offline)'
    raise last or NoOCR('no OCR engine')


def _clean(t):
    t = re.sub(r'^```\w*\s*|\s*```$', '', t.strip())
    return fix_ids(t.strip())


_PN = {}


def param_names():
    """ArduPilot parametre adları (OCR'da '_' kaybolunca geri koymak için)."""
    if 'n' not in _PN:
        n = set()
        try:
            import gzip
            from .paths import res
            with gzip.open(res('data', 'params_full.json.gz'), 'rt', encoding='utf-8') as f:
                n = set(json.load(f).get('params', {}))
        except Exception:
            pass
        _PN['n'] = n
    return _PN['n']


_WRUN = re.compile(r'\b[A-Z0-9]{1,10}(?:[ _]{1,2}[A-Z0-9]{1,14}){1,6}\b')


def fix_ids(text):
    """OCR'da bozulan parametre adlarını onar: 'O ASSIST SPEED' → 'Q_ASSIST_SPEED', 'BATT  MONITOR' → 'BATT_MONITOR'."""
    names = param_names()
    if not names or not text: return text

    def cands(ws):
        j = '_'.join(ws)
        yield j
        if ws[0] in ('O', '0'): yield 'Q_' + '_'.join(ws[1:])
        yield j.replace('0', 'O')

    def rep(m):
        ws = re.split(r'[ _]+', m.group(0))
        out = []; i = 0
        while i < len(ws):
            for k in range(len(ws), i + 1, -1):
                hit = next((c for c in cands(ws[i:k]) if c in names), None)
                if hit: out.append(hit); i = k; break
            else:
                out.append(ws[i]); i += 1
        res_ = ' '.join(out)
        return m.group(0) if res_.replace('_', ' ') == m.group(0).replace('_', ' ') and '_' not in res_ else res_
    return _WRUN.sub(rep, text)


def pdf_page_image(page, dpi=300):
    """PyMuPDF sayfası → PIL görüntü (taranmış sayfa OCR'ı için)."""
    from PIL import Image
    pix = page.get_pixmap(dpi=dpi)
    return Image.open(io.BytesIO(pix.tobytes('png')))
