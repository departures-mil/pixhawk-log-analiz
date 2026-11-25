"""Optik cevap formu: sayfa düzeni (mm) ve okuma (fotoğraf / tarama / telefon).

Sınav Hazırlama Sistemi'nin (departures-mil/sinav-hazirlama, renderer/omr.js) aynı düzeni ve aynı okuma yöntemi; burada
numpy ile. Düzen: A4 dikey; dört köşede 8 mm siyah kare; solda 8 haneli öğrenci numarası ızgarası; altta 4 blok × 25 satır
= en çok 100 soru, her satırda en çok 5 şık. Okuma: yerel eşikleme → köşe kareleri (bağlı bileşenler, küçültülmüş
görüntüde) → homografi → her kabarcıkta koyuluk oranı.
"""
from __future__ import annotations
import io
import numpy as np

L = {
    'page': (210, 297),
    'fid': {'size': 8, 'pos': [(10, 10), (192, 10), (10, 279), (192, 279)]},
    'no': {'x': 24, 'y': 70, 'dx': 7, 'dy': 6, 'cols': 8, 'rows': 10},
    'ans': {'x': [26, 72, 118, 164], 'y': 150, 'dx': 6.5, 'dy': 4.9, 'rows': 25, 'opts': 5},
    'r': 2.3,
    'max': 100,
}
BLANK, MULTI = -1, -2


def fid_center(i):
    x, y = L['fid']['pos'][i]; s = L['fid']['size']
    return (x + s / 2, y + s / 2)


def ans_xy(q, k):
    a = L['ans']; b, r = divmod(q, a['rows'])
    return (a['x'][b] + k * a['dx'], a['y'] + r * a['dy'])


def no_xy(c, d):
    n = L['no']
    return (n['x'] + c * n['dx'], n['y'] + d * n['dy'])


# ------------------------------------------------------------------ homografi
def homography(src, dst):
    A = []; b = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    try:
        h = np.linalg.solve(np.array(A, float), np.array(b, float))
    except np.linalg.LinAlgError:
        return None

    def f(x, y):
        w = h[6] * x + h[7] * y + 1
        return ((h[0] * x + h[1] * y + h[2]) / w, (h[3] * x + h[4] * y + h[5]) / w)
    return f


# ------------------------------------------------------------------ görüntü
def to_gray(data, max_dim=1700):
    """Bayt (jpg/png/…) ya da dosya yolu → (gri uint8 dizi, genişlik, yükseklik); en çok max_dim piksel."""
    from PIL import Image, ImageOps
    im = Image.open(io.BytesIO(data) if isinstance(data, (bytes, bytearray)) else data)
    try: im = ImageOps.exif_transpose(im)   # telefon fotoğrafı yönü
    except Exception: pass
    im = im.convert('L')
    s = min(1.0, max_dim / max(im.size))
    if s < 1: im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.BILINEAR)
    return np.asarray(im, dtype=np.uint8)


def binarize(g):
    """Yerel ortalamaya göre koyu (1) / açık (0) — eşit olmayan ışıkta da çalışır."""
    h, w = g.shape
    I = np.zeros((h + 1, w + 1), np.float64); I[1:, 1:] = g.astype(np.float64).cumsum(0).cumsum(1)
    r = max(8, round(min(w, h) / 24))
    ys = np.arange(h); xs = np.arange(w)
    y0 = np.clip(ys - r, 0, h); y1 = np.clip(ys + r + 1, 0, h); x0 = np.clip(xs - r, 0, w); x1 = np.clip(xs + r + 1, 0, w)
    S = I[y1][:, x1] - I[y0][:, x1] - I[y1][:, x0] + I[y0][:, x0]
    n = (y1 - y0)[:, None] * (x1 - x0)[None, :]
    mean = S / n
    return ((g < mean * 0.78) & (g < 170)).astype(np.uint8)


def components(b, min_area):
    """Koyu bölgeler (4 komşuluk), saf Python + numpy; küçültülmüş görüntüde kullanılır."""
    h, w = b.shape
    lab = np.zeros(b.shape, np.int32); out = []; cid = 0
    flat = b.ravel(); lf = lab.ravel()
    for i in np.flatnonzero(flat):
        if lf[i]: continue
        cid += 1; st = [i]; lf[i] = cid; px = []
        while st:
            p = st.pop(); px.append(p); y, x = divmod(p, w)
            if x > 0 and flat[p - 1] and not lf[p - 1]: lf[p - 1] = cid; st.append(p - 1)
            if x < w - 1 and flat[p + 1] and not lf[p + 1]: lf[p + 1] = cid; st.append(p + 1)
            if y > 0 and flat[p - w] and not lf[p - w]: lf[p - w] = cid; st.append(p - w)
            if y < h - 1 and flat[p + w] and not lf[p + w]: lf[p + w] = cid; st.append(p + w)
        if len(px) >= min_area:
            a = np.array(px); ys, xs = np.divmod(a, w)
            out.append({'area': len(px), 'minx': int(xs.min()), 'maxx': int(xs.max()), 'miny': int(ys.min()), 'maxy': int(ys.max()),
                        'cx': float(xs.mean()), 'cy': float(ys.mean())})
    for c in out:
        c['bw'] = c['maxx'] - c['minx'] + 1; c['bh'] = c['maxy'] - c['miny'] + 1
    return out


def find_fiducials(b):
    """Dört köşe karesinin merkezleri (tam çözünürlükte) ya da None. Bileşenler ≤ 420 px'lik küçük kopyada aranır."""
    h, w = b.shape
    s = min(1.0, 420 / max(w, h)); step = max(1, int(round(1 / s)))
    sb = b[::step, ::step]; sh, sw = sb.shape
    md = min(sw, sh)
    comps = components(sb, max(6, round((md * 0.012) ** 2)))
    cand = [c for c in comps if 0.55 < c['bw'] / c['bh'] < 1.8 and c['area'] / (c['bw'] * c['bh']) > 0.6 and md * 0.018 < c['bw'] < md * 0.12]
    corners = [(0, 0), (sw, 0), (0, sh), (sw, sh)]
    out = []
    for i, (X, Y) in enumerate(corners):
        q = [c for c in cand if (c['cx'] > sw / 2 if i % 2 else c['cx'] < sw / 2) and (c['cy'] < sh / 2 if i < 2 else c['cy'] > sh / 2)]
        if not q: return None
        q.sort(key=lambda c: np.hypot(c['cx'] - X, c['cy'] - Y) / np.sqrt(c['area']))
        out.append(q[0])
    sz = [np.sqrt(c['area']) for c in out]
    if min(sz) < max(sz) * 0.45: return None
    # tam çözünürlükte ağırlık merkezi (kutunun biraz genişi)
    res = []
    for c in out:
        x0 = max(0, (c['minx'] - 1) * step); x1 = min(w, (c['maxx'] + 2) * step); y0 = max(0, (c['miny'] - 1) * step); y1 = min(h, (c['maxy'] + 2) * step)
        win = b[y0:y1, x0:x1]
        if win.sum() < 4: res.append((c['cx'] * step, c['cy'] * step)); continue
        ys, xs = np.nonzero(win)
        res.append((float(xs.mean() + x0), float(ys.mean() + y0)))
    return res


def fill_ratio(b, cx, cy, rr):
    h, w = b.shape
    y0 = max(0, int(np.floor(cy - rr))); y1 = min(h, int(np.ceil(cy + rr)) + 1)
    x0 = max(0, int(np.floor(cx - rr))); x1 = min(w, int(np.ceil(cx + rr)) + 1)
    if y1 <= y0 or x1 <= x0: return 0.0
    yy, xx = np.mgrid[y0:y1, x0:x1]
    m = (xx - cx) ** 2 + (yy - cy) ** 2 <= rr * rr
    n = int(m.sum())
    return float(b[y0:y1, x0:x1][m].sum()) / n if n else 0.0


def choose(f, on=0.42):
    order = np.argsort(f)[::-1]
    m = f[order[0]]; s = f[order[1]] if len(f) > 1 else -1
    if m < on: return BLANK
    if s >= on and s > m * 0.7: return MULTI
    return int(order[0])


def read(img, n_q, n_opts=5, on=0.42):
    """img: bayt / yol / gri dizi. → {'ok', 'answers': [-1 boş | -2 çift | 0..], 'no', 'fills', 'corners'} ya da {'ok': False, 'err'}"""
    try:
        g = img if isinstance(img, np.ndarray) else to_gray(img)
    except Exception:
        return {'ok': False, 'err': 'IMG'}
    b = binarize(g)
    fids = find_fiducials(b)
    if not fids: return {'ok': False, 'err': 'CORNERS'}
    H = homography([fid_center(i) for i in range(4)], fids)
    if not H: return {'ok': False, 'err': 'CORNERS'}
    r = L['r']

    def ratio(x, y):
        u, v = H(x, y); u2, v2 = H(x + r, y)
        return fill_ratio(b, u, v, np.hypot(u2 - u, v2 - v) * 0.62)
    n = max(1, min(L['max'], n_q or L['max'])); k_ = max(2, min(L['ans']['opts'], n_opts))
    fills = []; answers = []
    for q in range(n):
        f = np.array([ratio(*ans_xy(q, k)) for k in range(k_)])
        fills.append([round(float(x), 3) for x in f]); answers.append(choose(f, on))
    no = ''
    for c in range(L['no']['cols']):
        f = np.array([ratio(*no_xy(c, d)) for d in range(L['no']['rows'])])
        k = choose(f, on)
        no += str(k) if k >= 0 else ('*' if k == MULTI else ' ')
    return {'ok': True, 'answers': answers, 'no': no.strip(), 'fills': fills, 'corners': fids}


# ------------------------------------------------------------------ form PDF'i
def sheet_pdf(path, title, code, n, n_opts=5, lang='tr', school='', copies=1, letters=None):
    """Optik cevap formu (A4, ölçüler mm — okuyucuyla birebir aynı)."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.pagesizes import A4
    from . import report as RP
    RP._fonts()
    T = SHEET_T; i = ('tr', 'en', 'ar').index(lang) if lang in ('tr', 'en', 'ar') else 0
    rtl = lang == 'ar'

    def sh(s):
        if not rtl: return s
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(s))
    Ls = letters or (['أ', 'ب', 'ج', 'د', 'هـ'] if rtl else ['A', 'B', 'C', 'D', 'E'])
    n = max(1, min(L['max'], n)); k_ = max(2, min(5, n_opts))
    c = canvas.Canvas(path, pagesize=A4)
    H = 297

    def Y(y): return (H - y) * mm

    def txt(x, y, s, size=8, bold=False, align='l', color=(0, 0, 0)):
        c.setFont('DJB' if bold else 'DJ', size); c.setFillColorRGB(*color)
        s = sh(s)
        if align == 'c': c.drawCentredString(x * mm, Y(y), s)
        elif align == 'r': c.drawRightString(x * mm, Y(y), s)
        else: c.drawString(x * mm, Y(y), s)
    for _ in range(max(1, copies)):
        c.setFillColorRGB(0, 0, 0)
        for (x, y) in L['fid']['pos']:
            s = L['fid']['size']; c.rect(x * mm, Y(y + s), s * mm, s * mm, stroke=0, fill=1)
        if school: txt(105, 16, school, 11, True, 'c')
        txt(105, 23, title or '', 13, True, 'c')
        txt(105, 30, T['title'][i], 10, False, 'c', (0.2, 0.2, 0.2))
        txt(105, 40, f"{T['code'][i]}: {code}  ·  {n} {T['q'][i]}", 8, False, 'c', (0.33, 0.33, 0.33))
        N = L['no']
        txt(N['x'] - 4 + N['dx'] * N['cols'] / 2, N['y'] - 14, T['no'][i], 8, True, 'c')
        c.setStrokeColorRGB(0.5, 0.5, 0.5); c.setLineWidth(0.3 * mm)
        c.roundRect((N['x'] - 5) * mm, Y(N['y'] - 18 + N['dy'] * 10 + 15), (N['dx'] * N['cols'] + 3) * mm, (N['dy'] * 10 + 15) * mm, 2 * mm)
        for col in range(N['cols']):
            c.setStrokeColorRGB(0.33, 0.33, 0.33); c.rect((N['x'] - 3 + col * N['dx']) * mm, Y(N['y'] - 11 + 7), 6 * mm, 7 * mm)
            for d in range(10): _bubble(c, *no_xy(col, d), str(d), Y)
        fx = 92; fr = 190
        from reportlab.pdfbase.pdfmetrics import stringWidth
        for k, key in enumerate(('name', 'class', 'sign')):
            y = N['y'] - 14 + k * 9
            lab = (':' + T[key][i]) if rtl else (T[key][i] + ':')
            lw = stringWidth(sh(T[key][i] + ':'), 'DJB', 10) / mm + 2
            c.setDash(1, 2); c.setStrokeColorRGB(0.2, 0.2, 0.2); c.setLineWidth(0.3 * mm)
            if rtl:
                txt(fr, y, T[key][i] + ':', 10, True, 'r'); c.line(fx * mm, Y(y + 0.8), (fr - lw) * mm, Y(y + 0.8))
            else:
                txt(fx, y, lab, 10, True); c.line((fx + lw) * mm, Y(y + 0.8), fr * mm, Y(y + 0.8))
            c.setDash()
        for k, key in enumerate(('rule', 'nohelp')):
            _wrap(c, txt, fr if rtl else fx, N['y'] + 16 + k * 12, T[key][i], 96, 8.2, 'r' if rtl else 'l')
        A = L['ans']
        blocks = (n + A['rows'] - 1) // A['rows']
        for bl in range(blocks):
            x0, y0 = ans_xy(bl * A['rows'], 0)
            for k in range(k_): txt(x0 + k * A['dx'], y0 - 5, Ls[k], 8, True, 'c')
            rows = min(A['rows'], n - bl * A['rows'])
            c.setStrokeColorRGB(0.53, 0.53, 0.53); c.setLineWidth(0.3 * mm)
            c.roundRect((x0 - 10) * mm, Y(y0 - 9 + rows * A['dy'] + 6.5), (A['dx'] * (k_ - 1) + 13.5) * mm, (rows * A['dy'] + 6.5) * mm, 2 * mm)
        for q in range(n):
            x, y = ans_xy(q, 0)
            txt(x - 3.6, y + 1.0, str(q + 1), 8, True, 'r')
            for k in range(k_): _bubble(c, *ans_xy(q, k), Ls[k], Y)
        c.showPage()
    c.save()
    return path


def _bubble(c, x, y, label, Y):
    from reportlab.lib.units import mm
    r = L['r']
    c.setStrokeColorRGB(0.27, 0.27, 0.27); c.setLineWidth(0.25 * mm); c.circle(x * mm, Y(y), (r - 0.12) * mm, stroke=1, fill=0)
    c.setFillColorRGB(0.72, 0.72, 0.72); c.setFont('DJ', 6.3)
    lab = label
    if any('؀' <= ch <= 'ۿ' for ch in lab):
        import arabic_reshaper
        from bidi.algorithm import get_display
        lab = get_display(arabic_reshaper.reshape(lab))
    c.drawCentredString(x * mm, Y(y + 0.8), lab)


def _wrap(c, txt, x, y, s, width_mm, size, align='l'):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.lib.units import mm
    words = s.split(' '); line = ''; k = 0
    for w in words:
        cand = (line + ' ' + w).strip()
        if stringWidth(cand, 'DJ', size) > width_mm * mm and line:
            txt(x, y + k * 4, line, size, False, align, (0.2, 0.2, 0.2)); k += 1; line = w
        else:
            line = cand
    if line: txt(x, y + k * 4, line, size, False, align, (0.2, 0.2, 0.2))


SHEET_T = {
    'title': ('OPTİK CEVAP FORMU', 'ANSWER SHEET', 'ورقة الإجابة'),
    'code': ('Sınav kodu', 'Exam code', 'رمز الاختبار'), 'q': ('soru', 'questions', 'سؤالاً'),
    'no': ('ÖĞRENCİ NO', 'STUDENT NO', 'رقم الطالب'),
    'name': ('Adı Soyadı', 'Name', 'الاسم'), 'class': ('Sınıfı', 'Class', 'الصف'), 'sign': ('İmza', 'Signature', 'التوقيع'),
    'rule': ('Yalnızca yumuşak kurşun kalem kullanın. Yuvarlağı tamamen doldurun. Değiştirirken iyice silin. Formu katlamayın.',
             'Use a soft pencil only. Fill the circle completely. Erase cleanly to change. Do not fold.',
             'استخدم قلم رصاص ليّنًا فقط. املأ الدائرة كاملة. امسح جيدًا عند التغيير. لا تطوِ الورقة.'),
    'nohelp': ('Numaranızı kutulara yazın ve altındaki yuvarlakları doldurun. Yazılı (yorum) sorularını kitapçığa cevaplayın.',
               'Write your number in the boxes and fill the circles below. Answer the written (interpretation) questions in the booklet.',
               'اكتب رقمك في المربعات واملأ الدوائر تحتها. أجب عن الأسئلة الكتابية (التفسير) في الكراسة.'),
}
