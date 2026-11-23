"""Antet (letterhead) yardımcıları.

- Hazır antetler (programa gömülü) 'builtin:<dosya>' olarak saklanır; her cihazda çalışır.
- Tam sayfa antet görseli: üst/alt antet bantları otomatik bulunur, içerik antetle çakışmaz.
- Word şablonu (.docx) içe aktarma: üstbilgideki metin kutuları, logo, çizgi ve filigran
  tam sayfa bir antet görseline dönüştürülür (DOCX ve PDF'te aynı görünüm).
- Besmele yalnızca ilk sayfada (rapor oluşturucular bunu gövdenin başına ekler).
- Önizleme: 1. ve 2. sayfanın küçük görüntüsü.
"""
from __future__ import annotations
import hashlib, io, os, re, zipfile
from xml.etree import ElementTree as ET
from .paths import data_dir, res

PAGE_W_CM, PAGE_H_CM = 21.0, 29.7
BUILTIN_PREFIX = 'builtin:'
PRESET_NAME = 'Savunma Bakanlığı – Sabit Kanat'
PRESET = {'org': '', 'sub': '', 'logo': '', 'bg': BUILTIN_PREFIX + 'mod_fixed_wing.jpg', 'color': '#6B5426',
          'watermark': '', 'footer': '', 'prepared_by': '', 'besmele': True, 'top_cm': 0}


def resolve(p):
    """Şablondaki yol -> gerçek dosya yolu (gömülü antetler dahil). Yoksa ''."""
    if not p: return ''
    if p.startswith(BUILTIN_PREFIX):
        p = res('data', 'letterheads', p[len(BUILTIN_PREFIX):])
    return p if os.path.exists(p) else ''


def besmele_path():
    return res('data', 'letterheads', 'besmele.png')


def _cache_dir():
    d = os.path.join(data_dir(), 'letterheads', 'cache'); os.makedirs(d, exist_ok=True); return d


def _key(path):
    st = os.stat(path)
    return hashlib.sha1(f'{os.path.abspath(path)}|{st.st_mtime_ns}|{st.st_size}'.encode('utf-8')).hexdigest()[:16]


def prepared_bg(path, max_w=1654):
    """Raporlara gömülecek, boyutu küçültülmüş (≈200 dpi) JPEG kopyası. Orijinal 3–10 MB olabilir."""
    from PIL import Image
    out = os.path.join(_cache_dir(), _key(path) + '.jpg')
    if os.path.exists(out): return out
    im = Image.open(path)
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA'); bg = Image.new('RGB', im.size, 'white'); bg.paste(im, mask=im.split()[-1]); im = bg
    else:
        im = im.convert('RGB')
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    im.save(out, quality=88, optimize=True, progressive=True)
    return out


def bands(path):
    """Tam sayfa antet görselinde üst ve alt antet bantlarını bulur.
    (top_cm, bottom_cm): içerik bu boşluklardan sonra başlamalı."""
    from PIL import Image
    import numpy as np
    im = Image.open(path).convert('L')
    w = 600; h = round(w * PAGE_H_CM / PAGE_W_CM)
    a = np.asarray(im.resize((w, h), Image.BILINEAR), dtype=np.int16)
    # "Mürekkep": yazı, logo ve çizgiler. Açık gri filigran desenleri sayılmaz.
    bgv = np.median(a)
    ink = (a < min(185, bgv - 45)).sum(axis=1)
    rows = np.where(ink >= 3)[0]
    cm_per_px = PAGE_H_CM / h
    top_lim = int(h * 0.30); bot_lim = int(h * 0.78)
    top_rows = rows[rows < top_lim]; bot_rows = rows[rows > bot_lim]
    top = (top_rows.max() + 1) * cm_per_px + 0.45 if len(top_rows) else 0.0
    bottom = (h - bot_rows.min()) * cm_per_px + 0.35 if len(bot_rows) else 0.0
    return round(top, 2), round(bottom, 2)


def margins(lh):
    """(top_cm, bottom_cm, bg_path_or_''). Kullanıcı üst boşluğu elle verdiyse o kullanılır."""
    bg = resolve(lh.get('bg') or '')
    if not bg:
        return None, None, ''
    try:
        top, bottom = bands(bg)
    except Exception:
        top, bottom = 3.6, 0.0
    try: man = float(lh.get('top_cm') or 0)
    except Exception: man = 0
    if man > 0: top = man
    return max(top, 1.6), max(bottom, 1.6), bg


# ---------------------------------------------------------------- DOCX şablonu içe aktarma
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
WP = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}'
A_ = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
R_ = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
V = '{urn:schemas-microsoft-com:vml}'
WPS = '{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}'
MC = '{http://schemas.openxmlformats.org/markup-compatibility/2006}'
EMU_CM = 360000.0
TW_CM = 567.0

_WIN_FONTS = {
    'times new roman': ('times.ttf', 'timesbd.ttf'), 'arial': ('arial.ttf', 'arialbd.ttf'),
    'calibri': ('calibri.ttf', 'calibrib.ttf'), 'cambria': ('cambria.ttc', 'cambriab.ttf'),
    'simplified arabic': ('simpo.ttf', 'simpbdo.ttf'), 'traditional arabic': ('trado.ttf', 'tradbdo.ttf'),
    'segoe ui': ('segoeui.ttf', 'segoeuib.ttf'), 'tahoma': ('tahoma.ttf', 'tahomabd.ttf'),
}


def _font(name, size_px, bold=False, arabic=False):
    from PIL import ImageFont
    cands = []
    wd = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
    n = (name or 'times new roman').lower()
    if n in ('majorbidi', 'minorbidi', 'majorhansi', 'minorhansi', ''): n = 'times new roman'
    if n in _WIN_FONTS: cands.append(os.path.join(wd, _WIN_FONTS[n][1 if bold else 0]))
    cands.append(os.path.join(wd, 'timesbd.ttf' if bold else 'times.ttf'))
    for f in (('FreeSerifBold.ttf', 'FreeSerif.ttf'), ('LiberationSerif-Bold.ttf', 'LiberationSerif-Regular.ttf')):
        for d in ('/usr/share/fonts/truetype/freefont', '/usr/share/fonts/truetype/liberation'):
            cands.append(os.path.join(d, f[0] if bold else f[1]))
    try:
        from matplotlib import font_manager
        cands.append(font_manager.findfont('DejaVu Sans' + (':bold' if bold else '') if arabic else 'DejaVu Serif' + (':bold' if bold else '')))
    except Exception:
        pass
    for c in cands:
        if c and os.path.exists(c):
            try: return ImageFont.truetype(c, max(6, int(size_px)), layout_engine=ImageFont.Layout.BASIC)
            except Exception: pass
    return ImageFont.load_default()


def _is_ar(s):
    return any('\u0600' <= ch <= '\u06FF' or '\uFB50' <= ch <= '\uFEFF' for ch in s)


def _shape(s):
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(s))
    except Exception:
        return s


def import_docx(path, dpi=200):
    """Word antet şablonunu tam sayfa PNG antete dönüştürür.
    Döner: {'bg': png_yolu, 'besmele': bool, 'texts': [...]}"""
    from PIL import Image, ImageDraw
    z = zipfile.ZipFile(path)
    names = set(z.namelist())
    doc = ET.fromstring(z.read('word/document.xml'))
    rels = _rels(z, 'word/_rels/document.xml.rels')
    body_txt = ''.join(t.text or '' for t in doc.iter(W + 't'))
    has_besmele = '\uFDFD' in body_txt or 'بسم الله' in re.sub('[\u064B-\u0652\u0670]', '', body_txt)
    sect = None
    for s in doc.iter(W + 'sectPr'): sect = s
    pg = {'w': 11906, 'h': 16838, 'top': 1440, 'left': 1800, 'right': 1800, 'header': 708}
    hdr_refs = {}
    if sect is not None:
        e = sect.find(W + 'pgSz')
        if e is not None:
            pg['w'] = int(e.get(W + 'w', pg['w'])); pg['h'] = int(e.get(W + 'h', pg['h']))
        e = sect.find(W + 'pgMar')
        if e is not None:
            for k in ('top', 'left', 'right', 'header'):
                try: pg[k] = abs(int(e.get(W + k, pg[k])))
                except Exception: pass
        for e in sect.findall(W + 'headerReference'):
            hdr_refs[e.get(W + 'type')] = e.get(R_ + 'id')
    # Tüm sayfalarda görünen üstbilgi: 'default' (yoksa first/even)
    rid = hdr_refs.get('default') or hdr_refs.get('first') or hdr_refs.get('even')
    pxcm = dpi / 2.54
    Wpx, Hpx = round(pg['w'] / TW_CM * pxcm), round(pg['h'] / TW_CM * pxcm)
    page = Image.new('RGB', (Wpx, Hpx), 'white')
    texts = []
    if not rid or rid not in rels:
        raise ValueError('no header')
    hpath = 'word/' + rels[rid].lstrip('/').replace('word/', '')
    hdr = ET.fromstring(z.read(hpath))
    hrels = _rels(z, os.path.dirname(hpath) + '/_rels/' + os.path.basename(hpath) + '.rels')

    def img_bytes(r):
        t = hrels.get(r)
        if not t: return None
        p = os.path.normpath(os.path.join(os.path.dirname(hpath), t)).replace('\\', '/')
        return z.read(p) if p in names else None

    L = pg['left'] / TW_CM; Rm = pg['right'] / TW_CM; T = pg['top'] / TW_CM
    PW, PH = pg['w'] / TW_CM, pg['h'] / TW_CM
    para_y = pg['header'] / TW_CM  # üstbilgi paragrafının üst kenarı

    # 1) VML filigran (Word "Resim filigranı")
    for sh in hdr.iter(V + 'shape'):
        im_el = sh.find(V + 'imagedata')
        if im_el is None: continue
        b = img_bytes(im_el.get(R_ + 'id'))
        if not b: continue
        st = dict(kv.split(':', 1) for kv in (sh.get('style') or '').split(';') if ':' in kv)
        def pt(v):
            v = (v or '').strip()
            try:
                if v.endswith('pt'): return float(v[:-2]) / 72 * 2.54
                if v.endswith('in'): return float(v[:-2]) * 2.54
                if v.endswith('cm'): return float(v[:-2])
                return float(v) / 72 * 2.54
            except Exception: return None
        wcm = pt(st.get('width')) or PW; hcm = pt(st.get('height')) or PH
        relh = st.get('mso-position-horizontal-relative', 'margin'); relv = st.get('mso-position-vertical-relative', 'margin')
        bx = (0, PW) if relh == 'page' else (L, PW - Rm)
        by = (0, PH) if relv == 'page' else (T, PH - T)
        x = bx[0] + ((bx[1] - bx[0]) - wcm) / 2; y = by[0] + ((by[1] - by[0]) - hcm) / 2
        try:
            im = Image.open(io.BytesIO(b)).convert('RGB').resize((max(1, round(wcm * pxcm)), max(1, round(hcm * pxcm))), Image.LANCZOS)
            if im_el.get('gain') or im_el.get('blacklevel'):  # "Soluklaştır"
                im = Image.blend(im, Image.new('RGB', im.size, 'white'), 0.6)
            page.paste(im, (round(x * pxcm), round(y * pxcm)))
        except Exception:
            pass

    # 2) Üstbilginin normal akışı: paragraflar, satır içi resimler, tablolar, alt çizgiler
    try:
        _flow(hdr, page, img_bytes, L, PW - Rm, para_y, pxcm, dpi, texts)
    except Exception:
        pass

    # 3) DrawingML nesneleri (metin kutuları, resimler, çizgiler) — arkadakiler önce
    anchors = []
    for an in hdr.iter(WP + 'anchor'):
        anchors.append((0 if an.get('behindDoc') == '1' else 1, int(an.get('relativeHeight') or 0), an))
    anchors.sort(key=lambda x: (x[0], x[1]))
    d = ImageDraw.Draw(page)
    for _, _, an in anchors:
        ext = an.find(WP + 'extent')
        if ext is None: continue
        wcm = int(ext.get('cx')) / EMU_CM; hcm = int(ext.get('cy')) / EMU_CM
        x = _pos(an.find(WP + 'positionH'), wcm, {'page': (0, PW), 'margin': (L, PW - Rm), 'column': (L, PW - Rm),
                                                  'character': (L, PW - Rm), 'leftMargin': (0, L), 'rightMargin': (PW - Rm, PW),
                                                  'insideMargin': (0, L), 'outsideMargin': (PW - Rm, PW)}, L)
        y = _pos(an.find(WP + 'positionV'), hcm, {'page': (0, PH), 'margin': (T, PH - T), 'paragraph': (para_y, PH),
                                                  'line': (para_y, PH), 'topMargin': (0, T), 'bottomMargin': (PH - T, PH)}, para_y)
        box = (round(x * pxcm), round(y * pxcm), round((x + wcm) * pxcm), round((y + hcm) * pxcm))
        blip = an.find('.//' + A_ + 'blip')
        if blip is not None and an.find('.//' + WPS + 'txbx') is None:
            b = img_bytes(blip.get(R_ + 'embed'))
            if b:
                try:
                    im = Image.open(io.BytesIO(b)).convert('RGBA').resize((max(1, box[2] - box[0]), max(1, box[3] - box[1])), Image.LANCZOS)
                    page.paste(im, box[:2], im)
                except Exception:
                    pass
            continue
        wsp = an.find('.//' + WPS + 'wsp')
        if wsp is None: continue
        sppr = wsp.find(WPS + 'spPr')
        fill = sppr.find(A_ + 'solidFill') if sppr is not None else None
        if fill is not None:
            c = fill.find(A_ + 'srgbClr')
            col = '#' + (c.get('val') if c is not None else 'BFBFBF')
            geom = sppr.find(A_ + 'prstGeom')
            r_ = min(box[3] - box[1], box[2] - box[0]) // 2 if geom is not None and geom.get('prst') == 'roundRect' else 0
            d.rounded_rectangle(box, radius=r_, fill=col) if r_ else d.rectangle(box, fill=col)
        ln = sppr.find(A_ + 'ln') if sppr is not None else None
        if ln is not None and ln.find(A_ + 'noFill') is None and ln.find(A_ + 'solidFill') is not None and wsp.find(WPS + 'txbx') is None:
            c = ln.find(A_ + 'solidFill/' + A_ + 'srgbClr')
            lw = max(1, round(int(ln.get('w') or 12700) / EMU_CM * pxcm))
            d.line([box[0], box[1], box[2], box[3]], fill='#' + (c.get('val') if c is not None else '808080'), width=lw)
        tx = wsp.find(WPS + 'txbx')
        if tx is None: continue
        bp = wsp.find(WPS + 'bodyPr')
        ins = {k: int(bp.get(k)) / EMU_CM if bp is not None and bp.get(k) else dflt for k, dflt in
               (('lIns', 0.254), ('tIns', 0.127), ('rIns', 0.254), ('bIns', 0.127))}
        lines = []
        for p in tx.iter(W + 'p'):
            ppr = p.find(W + 'pPr')
            jc = 'left'; mult = 1.0; after = 0.0
            if ppr is not None:
                j = ppr.find(W + 'jc')
                if j is not None: jc = j.get(W + 'val', 'left')
                sp = ppr.find(W + 'spacing')
                if sp is not None:
                    if sp.get(W + 'line') and (sp.get(W + 'lineRule') in (None, 'auto')): mult = int(sp.get(W + 'line')) / 240
                    if sp.get(W + 'after'): after = int(sp.get(W + 'after')) / TW_CM
            txt = ''; size = None; bold = False; fname = None
            for r in p.iter(W + 'r'):
                rpr = r.find(W + 'rPr')
                if rpr is not None:
                    sz = rpr.find(W + 'szCs') if size is None else None
                    s2 = rpr.find(W + 'sz')
                    if s2 is not None: size = int(s2.get(W + 'val')) / 2
                    elif sz is not None: size = int(sz.get(W + 'val')) / 2
                    if rpr.find(W + 'b') is not None: bold = True
                    f = rpr.find(W + 'rFonts')
                    if f is not None and not fname: fname = f.get(W + 'ascii') or f.get(W + 'cs')
                for t in r.iter(W + 't'): txt += t.text or ''
            lines.append({'t': txt.strip(), 'size': size or 11.0, 'bold': bold, 'jc': jc, 'mult': mult, 'after': after, 'font': fname})
        while lines and not lines[-1]['t']: lines.pop()
        if not lines: continue
        heights = [ln_['size'] / 72 * 2.54 * 1.15 * ln_['mult'] + ln_['after'] for ln_ in lines]
        total = sum(heights)
        bx0, bx1 = x + ins['lIns'], x + wcm - ins['rIns']
        yy = y + ins['tIns']
        if bp is not None and bp.get('anchor') == 'ctr': yy = y + (hcm - total) / 2
        elif bp is not None and bp.get('anchor') == 'b': yy = y + hcm - ins['bIns'] - total
        for ln_, hh in zip(lines, heights):
            if ln_['t']:
                ar = _is_ar(ln_['t'])
                f = _font(ln_['font'], ln_['size'] / 72 * dpi, ln_['bold'], ar)
                s = _shape(ln_['t']) if ar else ln_['t']
                tw = d.textlength(s, font=f)
                jc = ln_['jc']
                if jc == 'center':
                    tx0 = (bx0 + bx1) / 2 * pxcm - tw / 2
                elif jc in ('right', 'end'):
                    tx0 = bx1 * pxcm - tw
                else:
                    tx0 = bx0 * pxcm
                line_h = ln_['size'] / 72 * dpi * 1.15 * ln_['mult']
                ty = yy * pxcm + (line_h - ln_['size'] / 72 * dpi) / 2
                d.text((tx0, ty), s, font=f, fill='black')
                texts.append(ln_['t'])
            yy += hh
    out_dir = os.path.join(data_dir(), 'letterheads'); os.makedirs(out_dir, exist_ok=True)
    base = re.sub(r'[^\w\-]+', '_', os.path.splitext(os.path.basename(path))[0])[:40] or 'antet'
    out = os.path.join(out_dir, f'{base}_{hashlib.sha1(z.read(hpath)).hexdigest()[:6]}.png')
    page.save(out, optimize=True)
    return {'bg': out, 'besmele': has_besmele, 'texts': texts}


def _para_items(p, img_bytes):
    """Paragrafın metni ve satır içi resimleri (metin kutuları ve yüzen nesneler hariç)."""
    items = []; size = None; bold = False; fname = None
    for r in p.findall(W + 'r') + [x for h in p.findall(W + 'hyperlink') for x in h.findall(W + 'r')]:
        rpr = r.find(W + 'rPr')
        if rpr is not None:
            s2 = rpr.find(W + 'sz') if rpr.find(W + 'sz') is not None else rpr.find(W + 'szCs')
            if s2 is not None and size is None: size = int(s2.get(W + 'val')) / 2
            if rpr.find(W + 'b') is not None: bold = True
            f = rpr.find(W + 'rFonts')
            if f is not None and not fname: fname = f.get(W + 'ascii') or f.get(W + 'cs')
        for el in r:
            if el.tag == W + 't': items.append(('t', el.text or ''))
            elif el.tag == W + 'tab': items.append(('t', '    '))
            elif el.tag == W + 'drawing':
                inl = el.find(WP + 'inline')
                if inl is None: continue
                blip = inl.find('.//' + A_ + 'blip'); ext = inl.find(WP + 'extent')
                if blip is not None and ext is not None:
                    b = img_bytes(blip.get(R_ + 'embed'))
                    if b: items.append(('i', (b, int(ext.get('cx')) / EMU_CM, int(ext.get('cy')) / EMU_CM)))
    ppr = p.find(W + 'pPr'); jc = 'left'; border = None; after = 0.0; mult = 1.0
    if ppr is not None:
        j = ppr.find(W + 'jc')
        if j is not None: jc = j.get(W + 'val', 'left')
        if ppr.find(W + 'bidi') is not None and jc in ('left', 'start'): jc = 'right'
        sp = ppr.find(W + 'spacing')
        if sp is not None:
            if sp.get(W + 'after'): after = int(sp.get(W + 'after')) / TW_CM
            if sp.get(W + 'line') and sp.get(W + 'lineRule') in (None, 'auto'): mult = int(sp.get(W + 'line')) / 240
        b = ppr.find(W + 'pBdr/' + W + 'bottom')
        if b is not None and b.get(W + 'val') not in (None, 'nil', 'none'):
            col = b.get(W + 'color'); col = '#' + col if col and col != 'auto' else '#000000'
            border = (col, max(0.5, int(b.get(W + 'sz') or 4) / 8))
    return items, size or 11.0, bold, fname, jc, after, mult, border


def _draw_para(page, p, img_bytes, x0, x1, y, pxcm, dpi, texts):
    from PIL import Image, ImageDraw
    items, size, bold, fname, jc, after, mult, border = _para_items(p, img_bytes)
    d = ImageDraw.Draw(page)
    txt = ''.join(v for k, v in items if k == 't').strip()
    imgs = [v for k, v in items if k == 'i']
    lh = size / 72 * 2.54 * 1.15 * mult
    h = max([lh if txt else 0] + [ih for _, _, ih in imgs]) or lh
    parts = []
    for b, iw, ih in imgs:
        try:
            im = Image.open(io.BytesIO(b)).convert('RGBA').resize((max(1, round(iw * pxcm)), max(1, round(ih * pxcm))), Image.LANCZOS)
            parts.append(('i', im))
        except Exception:
            pass
    if txt:
        ar = _is_ar(txt); f = _font(fname, size / 72 * dpi, bold, ar); s = _shape(txt) if ar else txt
        parts.append(('t', (s, f, d.textlength(s, font=f)))); texts.append(txt)
    tot = sum(v.width if k == 'i' else v[2] for k, v in parts) + 10 * max(0, len(parts) - 1)
    if jc == 'center': cx = (x0 + x1) / 2 * pxcm - tot / 2
    elif jc in ('right', 'end'): cx = x1 * pxcm - tot
    else: cx = x0 * pxcm
    base = y * pxcm
    for k, v in parts:
        if k == 'i':
            page.paste(v, (round(cx), round(base + (h * pxcm - v.height) / 2)), v); cx += v.width + 10
        else:
            s, f, w = v
            d.text((cx, base + (h * pxcm - size / 72 * dpi) / 2), s, font=f, fill='black'); cx += w + 10
    y += h
    if border:
        col, wpt = border
        d.line([x0 * pxcm, y * pxcm + 2, x1 * pxcm, y * pxcm + 2], fill=col, width=max(1, round(wpt / 72 * dpi)))
        y += 0.1
    return y + after


def _flow(hdr, page, img_bytes, x0, x1, y, pxcm, dpi, texts):
    for el in hdr:
        if el.tag == W + 'p':
            y = _draw_para(page, el, img_bytes, x0, x1, y, pxcm, dpi, texts)
        elif el.tag == W + 'tbl':
            cols = [int(g.get(W + 'w') or 0) / TW_CM for g in el.findall(W + 'tblGrid/' + W + 'gridCol')]
            bidi = el.find(W + 'tblPr/' + W + 'bidiVisual') is not None
            for tr in el.findall(W + 'tr'):
                cells = tr.findall(W + 'tc')
                if not cells: continue
                ws = cols if len(cols) == len(cells) and sum(cols) > 0 else [(x1 - x0) / len(cells)] * len(cells)
                sc = (x1 - x0) / sum(ws) if sum(ws) > (x1 - x0) else 1.0
                xs = []; cx = x0
                for w in ws: xs.append((cx, cx + w * sc)); cx += w * sc
                if bidi: xs = [(x0 + x1 - b, x0 + x1 - a) for a, b in xs]
                ymax = y
                for (a, b), tc in zip(xs, cells):
                    yy = y
                    for p in tc.findall(W + 'p'):
                        yy = _draw_para(page, p, img_bytes, a + 0.1, b - 0.1, yy, pxcm, dpi, texts)
                    ymax = max(ymax, yy)
                y = ymax
    return y


def _rels(z, p):
    try:
        x = ET.fromstring(z.read(p))
    except Exception:
        return {}
    return {e.get('Id'): e.get('Target') for e in x}


def _pos(el, size, frames, dflt):
    if el is None: return dflt
    frm = frames.get(el.get('relativeFrom'), (dflt, dflt + size))
    off = el.find(WP + 'posOffset')
    if off is not None and off.text:
        return frm[0] + int(off.text) / EMU_CM
    al = el.find(WP + 'align')
    a = (al.text or '').strip() if al is not None else ''
    if a in ('center',): return frm[0] + ((frm[1] - frm[0]) - size) / 2
    if a in ('right', 'bottom', 'outside'): return frm[1] - size
    return frm[0]


# ---------------------------------------------------------------- Önizleme
def preview_images(lh, lang='tr', width=420):
    """[1. sayfa, 2. sayfa] PIL görüntüleri: antet + (yalnızca 1. sayfada) besmele + örnek içerik."""
    from PIL import Image, ImageDraw
    Hh = round(width * PAGE_H_CM / PAGE_W_CM); pxcm = width / PAGE_W_CM
    top, bottom, bg = margins(lh)
    col = lh.get('color') or '#1E3A8A'
    pages = []
    for n in (1, 2):
        if bg:
            pg = Image.open(prepared_bg(bg)).convert('RGB').resize((width, Hh), Image.LANCZOS)
        else:
            pg = Image.new('RGB', (width, Hh), 'white'); d = ImageDraw.Draw(pg)
            d.rectangle([0, 0, width, round(0.32 * pxcm)], fill=col)
            d.line([round(1.8 * pxcm), round(2.5 * pxcm), width - round(1.8 * pxcm), round(2.5 * pxcm)], fill=col, width=1)
            d.rectangle([round(1.8 * pxcm), round(0.9 * pxcm), round(9 * pxcm), round(1.4 * pxcm)], fill=col)
            top, bottom = 2.9, 1.6
        d = ImageDraw.Draw(pg)
        y = top * pxcm; x0 = 1.8 * pxcm; x1 = width - 1.8 * pxcm
        if n == 1 and lh.get('besmele'):
            try:
                b = Image.open(besmele_path()).convert('RGBA'); bw = round(6.5 * pxcm)
                b = b.resize((bw, round(b.height * bw / b.width)), Image.LANCZOS)
                pg.paste(b, (round((width - bw) / 2), round(y)), b); y += b.height + 0.35 * pxcm
            except Exception:
                pass
        # Örnek içerik blokları
        if n == 1:
            d.rectangle([width * 0.28, y, width * 0.72, y + 0.55 * pxcm], fill=col); y += 1.0 * pxcm
        rtl = lang == 'ar'
        while y < Hh - bottom * pxcm - 0.5 * pxcm:
            d.rectangle([x0, y, x0 + (x1 - x0) * 0.45, y + 0.28 * pxcm] if not rtl else [x1 - (x1 - x0) * 0.45, y, x1, y + 0.28 * pxcm], fill=col)
            y += 0.5 * pxcm
            for i in range(4):
                if y > Hh - bottom * pxcm - 0.3 * pxcm: break
                w_ = (x1 - x0) * (0.97 if i < 3 else 0.6)
                d.rectangle([x0, y, x0 + w_, y + 0.16 * pxcm] if not rtl else [x1 - w_, y, x1, y + 0.16 * pxcm], fill='#9CA3AF')
                y += 0.33 * pxcm
            y += 0.35 * pxcm
        # İçerik sınırını göster (kesik çizgi)
        for xx in range(int(x0), int(x1), 8):
            d.line([xx, top * pxcm - 2, xx + 4, top * pxcm - 2], fill='#EF4444')
        pages.append(pg)
    return pages
