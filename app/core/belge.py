"""Belge çevirisi: DOCX, PDF, görüntü (OCR), TXT/MD — TR / EN / AR.

İlkeler (kullanıcı kuralı):
- Resimler, tablolar, antet (üst/alt bilgi görselleri), sayfa yapısı korunur; yalnız metin değişir.
- Arapçaya çeviride paragraflar ve tablolar sağdan sola (bidi), yazı tipi Arapça uyumlu; Arapçadan çeviride soldan sağa.
- Yalnız resim içeren paragraflar ortalanır.
- DOCX'te paragraf içi biçim (kalın, italik, renk…) dil modeline <1>…</1> etiketleriyle gönderilip korunur;
  etiket desteklemeyen motorda paragraf tek biçimle yazılır.
- PDF'te metin blokları aynı yere, aynı punto/renkle (sığmazsa küçültülerek) yazılır; görseller ve çizgiler kalır.
  Taranmış (metinsiz) sayfa OCR ile okunur, çevirisi o sayfanın hemen ardına yeni sayfa olarak eklenir.
"""
from __future__ import annotations
import copy, html, io, os, re
from . import ceviri as CV

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
XML = 'http://www.w3.org/XML/1998/namespace'
AR_FONT = 'Arial'
EXTS = {'.docx': 'docx', '.pdf': 'pdf', '.txt': 'txt', '.md': 'txt', '.csv': 'txt', '.log': 'txt', '.param': 'txt',
        '.png': 'img', '.jpg': 'img', '.jpeg': 'img', '.bmp': 'img', '.tif': 'img', '.tiff': 'img', '.webp': 'img', '.gif': 'img'}
_TEXT_ONLY = {'rPr', 't', 'tab', 'br', 'cr', 'lastRenderedPageBreak', 'noBreakHyphen', 'softHyphen'}


def q(t):
    return '{%s}%s' % (W, t)


def kind(path):
    return EXTS.get(os.path.splitext(path)[1].lower())


def out_name(path, tgt):
    b, e = os.path.splitext(path)
    k = kind(path)
    e = '.docx' if k == 'img' else e
    return f'{b}_{tgt.upper()}{e}'


# =============================================================== DOCX
def _loc(el):
    return el.tag.split('}')[-1]


def _owner_p(r):
    a = r.getparent()
    while a is not None and a.tag != q('p'): a = a.getparent()
    return a


def _run_text(r):
    out = []
    for c in r:
        n = _loc(c)
        if n == 't': out.append(c.text or '')
        elif n == 'tab': out.append('\t')
        elif n in ('br', 'cr') and c.get(q('type')) not in ('page', 'column'): out.append('\n')
        elif n == 'noBreakHyphen': out.append('-')
    return ''.join(out)


def _text_only(r):
    for c in r:
        n = _loc(c)
        if n not in _TEXT_ONLY: return False
        if n == 'br' and c.get(q('type')) in ('page', 'column'): return False
    return any(_loc(c) in ('t', 'tab') for c in r)


def _rkey(r):
    rp = r.find(q('rPr'))
    if rp is None: return ''
    rp = copy.deepcopy(rp)
    for t in ('lang', 'noProof', 'rtl', 'cs', 'szCs', 'bCs', 'iCs', 'rFonts', 'proofErr'):
        for e in rp.findall(q(t)): rp.remove(e)
    from lxml import etree
    return etree.tostring(rp)


def _segments(p):
    """Paragrafın çevrilecek parçaları: aynı ebeveynde art arda gelen, alan (field) dışı yalın metin koşuları."""
    segs = []; cur = []; depth = 0
    for r in p.iter(q('r')):
        if _owner_p(r) is not p: continue
        fc = r.find(q('fldChar'))
        if fc is not None:
            ty = fc.get(q('fldCharType'))
            if ty == 'begin': depth += 1
            elif ty == 'end': depth = max(0, depth - 1)
            if cur: segs.append(cur); cur = []
            continue
        if depth or not _text_only(r) or (cur and r.getparent() is not cur[-1].getparent()):
            if cur: segs.append(cur); cur = []
            if depth or not _text_only(r): continue
        cur.append(r)
    if cur: segs.append(cur)
    return segs


def _groups(runs):
    g = []
    for r in runs:
        k = _rkey(r)
        if g and g[-1][0] == k: g[-1][1].append(r)
        else: g.append((k, [r]))
    return g


def _tagged(groups):
    if len(groups) == 1: return ''.join(_run_text(r) for r in groups[0][1])
    return ''.join(f'<{i + 1}>' + ''.join(_run_text(r) for r in rs) + f'</{i + 1}>' for i, (_, rs) in enumerate(groups))


_TAG = re.compile(r'<(\d+)>(.*?)</\1>', re.S)


def _parse_tagged(s, n):
    """'<1>a</1><2>b</2>' → [(grup, metin)] ya da None (bozuksa)."""
    out = []; pos = 0
    for m in _TAG.finditer(s):
        pre = s[pos:m.start()]
        if pre.strip():
            if not out: return None
            out[-1] = (out[-1][0], out[-1][1] + pre)
        elif pre and out: out[-1] = (out[-1][0], out[-1][1] + pre)
        k = int(m.group(1)) - 1
        if not 0 <= k < n or re.search(r'</?\d+>', m.group(2)): return None
        out.append((k, m.group(2))); pos = m.end()
    tail = s[pos:]
    if tail.strip():
        if not out: return None
        out[-1] = (out[-1][0], out[-1][1] + tail)
    return out if out else None


def _new_run(proto, text):
    from lxml import etree
    r = etree.Element(q('r'))
    rp = proto.find(q('rPr'))
    if rp is not None: r.append(copy.deepcopy(rp))
    parts = re.split(r'(\t|\n)', text)
    for x in parts:
        if x == '\t': etree.SubElement(r, q('tab'))
        elif x == '\n': etree.SubElement(r, q('br'))
        elif x:
            t = etree.SubElement(r, q('t')); t.text = x; t.set('{%s}space' % XML, 'preserve')
    return r


def _write_segment(runs, groups, out):
    parsed = _parse_tagged(out, len(groups)) if len(groups) > 1 else None
    if parsed is None: parsed = [(0, CV.strip_tags(out))]
    parent = runs[0].getparent(); idx = parent.index(runs[0])
    news = [_new_run(groups[k][1][0], txt) for k, txt in parsed if txt]
    for r in runs: parent.remove(r)
    for i, nr in enumerate(news): parent.insert(idx + i, nr)
    return news


def _child(parent, tag, first=False):
    from lxml import etree
    e = parent.find(q(tag))
    if e is None:
        e = etree.Element(q(tag))
        if first: parent.insert(0, e)
        else: parent.append(e)
    return e


def _ppr(p):
    return _child(p, 'pPr', first=True)


_PPR_ORDER = ['pStyle', 'keepNext', 'keepLines', 'pageBreakBefore', 'framePr', 'widowControl', 'numPr', 'suppressLineNumbers', 'pBdr',
              'shd', 'tabs', 'suppressAutoHyphens', 'kinsoku', 'wordWrap', 'overflowPunct', 'topLinePunct', 'autoSpaceDE', 'autoSpaceDN',
              'bidi', 'adjustRightInd', 'snapToGrid', 'spacing', 'ind', 'contextualSpacing', 'mirrorIndents', 'suppressOverlap', 'jc',
              'textDirection', 'textAlignment', 'textboxTightWrap', 'outlineLvl', 'divId', 'cnfStyle', 'rPr', 'sectPr', 'pPrChange']
_TBL_ORDER = ['tblStyle', 'tblpPr', 'tblOverlap', 'bidiVisual', 'tblStyleRowBandSize', 'tblStyleColBandSize', 'tblW', 'jc',
              'tblCellSpacing', 'tblInd', 'tblBorders', 'shd', 'tblLayout', 'tblCellMar', 'tblLook', 'tblCaption', 'tblDescription', 'tblPrChange']
_RPR_ORDER = ['rStyle', 'rFonts', 'b', 'bCs', 'i', 'iCs', 'caps', 'smallCaps', 'strike', 'dstrike', 'outline', 'shadow', 'emboss', 'imprint',
              'noProof', 'snapToGrid', 'vanish', 'webHidden', 'color', 'spacing', 'w', 'kern', 'position', 'sz', 'szCs', 'highlight', 'u',
              'effect', 'bdr', 'shd', 'fitText', 'vertAlign', 'rtl', 'cs', 'em', 'lang', 'eastAsianLayout', 'specVanish', 'oMath']


def _ins(parent, tag, order):
    """Şema sırasına uygun yere öğe ekle (Word sıraya duyarlı)."""
    from lxml import etree
    e = parent.find(q(tag))
    if e is not None: return e
    e = etree.Element(q(tag))
    i = order.index(tag) if tag in order else len(order)
    pos = len(parent)
    for j, c in enumerate(parent):
        n = _loc(c)
        if n in order and order.index(n) > i: pos = j; break
    parent.insert(pos, e)
    return e


def _set_dir(p, rtl, runs=None):
    pp = _ppr(p)
    if rtl:
        _ins(pp, 'bidi', _PPR_ORDER)
        jc = pp.find(q('jc'))
        if jc is not None and jc.get(q('val')) in ('left', 'start'): pp.remove(jc)
    else:
        for e in pp.findall(q('bidi')): pp.remove(e)
    for r in (runs if runs is not None else [r for r in p.iter(q('r')) if _owner_p(r) is p]):
        rp = r.find(q('rPr'))
        if rtl:
            if rp is None:
                from lxml import etree
                rp = etree.Element(q('rPr')); r.insert(0, rp)
            _ins(rp, 'rtl', _RPR_ORDER)
            f = _ins(rp, 'rFonts', _RPR_ORDER)
            f.set(q('cs'), AR_FONT)
            sz = rp.find(q('sz'))
            if sz is not None and rp.find(q('szCs')) is None: _ins(rp, 'szCs', _RPR_ORDER).set(q('val'), sz.get(q('val')))
            if rp.find(q('b')) is not None: _ins(rp, 'bCs', _RPR_ORDER)
            if rp.find(q('i')) is not None: _ins(rp, 'iCs', _RPR_ORDER)
            _ins(rp, 'lang', _RPR_ORDER).set(q('bidi'), 'ar-SA')
        elif rp is not None:
            for e in rp.findall(q('rtl')): rp.remove(e)


def _has_image(p):
    return any(_loc(e) in ('drawing', 'pict', 'object') for e in p.iter())


def _parts(doc, headers=True):
    from docx.opc.part import XmlPart
    seen = set(); out = []
    for part in doc.part.package.iter_parts():
        n = str(part.partname)
        if not re.match(r'/word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$', n): continue
        if not headers and re.search(r'header|footer', n): continue
        if not isinstance(part, XmlPart) or id(part) in seen: continue
        seen.add(id(part)); out.append(part)
    return out


def translate_docx(src_path, dst_path, src, tgt, settings=None, usage=None, on_progress=None, cancel=None, headers=True):
    import docx
    doc = docx.Document(src_path)
    jobs = []   # (p, runs, groups, text)
    paras = []
    for part in _parts(doc, headers):
        for p in part.element.iter(q('p')):
            paras.append(p)
            for runs in _segments(p):
                g = _groups(runs)
                txt = _tagged(g)
                if CV.needs(CV.strip_tags(txt)): jobs.append((p, runs, g, txt))
    texts = [j[3] for j in jobs]
    if src not in CV.LANGS: src = CV.detect(' '.join(CV.strip_tags(x) for x in texts[:80]))
    T = CV.Translator(settings, usage)
    outs = T.run(texts, src, tgt, on_progress, cancel)
    touched = {}
    for (p, runs, g, txt), o in zip(jobs, outs):
        news = _write_segment(runs, g, o)
        touched.setdefault(id(p), (p, []))[1].extend(news)
    rtl, was_rtl = tgt == 'ar', src == 'ar'
    for p in paras:
        if rtl or was_rtl:
            _set_dir(p, rtl)
        if _has_image(p) and not CV.needs(''.join(_run_text(r) for r in p.iter(q('r')))):
            pp = _ppr(p); _ins(pp, 'jc', _PPR_ORDER).set(q('val'), 'center')
    if rtl or was_rtl:
        for part in _parts(doc, headers):
            for tp in part.element.iter(q('tblPr')):
                if rtl: _ins(tp, 'bidiVisual', _TBL_ORDER)
                else:
                    for e in tp.findall(q('bidiVisual')): tp.remove(e)
    doc.save(dst_path)
    T.report['src'] = src
    return T.report


# =============================================================== PDF
def _pdf():
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf
    return pymupdf


def _fonts_dir():
    import sys
    for b in (getattr(sys, '_MEIPASS', None), os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))):
        if b and os.path.isdir(os.path.join(b, 'fccore', 'fonts')): return os.path.join(b, 'fccore', 'fonts')
    return None


CSS = ('@font-face {font-family: lat; src: url(Inter-400.ttf);} @font-face {font-family: lat; src: url(Inter-700.ttf); font-weight: bold;}'
       '@font-face {font-family: ara; src: url(NotoSansArabic-400.ttf);} @font-face {font-family: ara; src: url(NotoSansArabic-700.ttf); font-weight: bold;}'
       '* {margin:0; padding:0;} p {line-height: 1.15;}')


def _blocks(page):
    d = page.get_text('dict')
    W_ = page.rect.width
    out = []
    for b in d.get('blocks', []):
        if b.get('type') != 0: continue
        lines = []; sizes = {}; color = 0; bold = 0; nspan = 0
        for ln in b.get('lines', []):
            t = ''.join(s.get('text', '') for s in ln.get('spans', []))
            if t.strip(): lines.append((t, ln['bbox']))
            for s in ln.get('spans', []):
                if not s.get('text', '').strip(): continue
                k = round(s.get('size', 10), 1); sizes[k] = sizes.get(k, 0) + len(s['text'])
                color = s.get('color', 0); bold += 1 if (s.get('flags', 0) & 16) or 'Bold' in s.get('font', '') else 0; nspan += 1
        if not lines: continue
        text = ''
        for i, (t, _) in enumerate(lines):
            if i == 0: text = t.rstrip(); continue
            if text.endswith('-') and not text.endswith(' -'): text = text[:-1] + t.lstrip()
            elif re.match(r'^\s*(?:[-•▪◦·*]|\d+[.)])\s', t): text += '\n' + t.strip()
            else: text += ' ' + t.strip()
        x0, y0, x1, y1 = b['bbox']
        cx = (x0 + x1) / 2
        center = abs(cx - W_ / 2) < W_ * 0.04 and (x1 - x0) < W_ * 0.75 and len(lines) <= 3
        right = x0 > W_ * 0.55
        out.append({'bbox': b['bbox'], 'text': text, 'size': max(sizes, key=sizes.get) if sizes else 10, 'color': color,
                    'bold': nspan and bold > nspan / 2, 'align': 'center' if center else ('right' if right else '')})
    return out


def _scanned(page, blocks):
    chars = sum(len(b['text']) for b in blocks)
    if chars > 40: return False
    area = page.rect.width * page.rect.height
    img = 0
    for info in page.get_image_info():
        x0, y0, x1, y1 = info['bbox']; img += max(0, x1 - x0) * max(0, y1 - y0)
    return img > area * 0.4


def _html(text, size, color, bold, align, tgt):
    rtl = tgt == 'ar'
    fam = 'ara, lat' if rtl else 'lat, ara'
    # MuPDF dir="rtl" kutusunda left/right mantıksaldır (left = başlangıç = sağ); boş bırakılınca sağa yaslar.
    # Kaynakta sağa yaslı blok Arapçada aynalanır: 'right' (= son = sol).
    al = align or ('' if rtl else 'left')
    col = '#%06x' % (color or 0)
    body = '<br>'.join(html.escape(x) for x in text.split('\n'))
    return (f'<p dir="{"rtl" if rtl else "ltr"}" style="font-family:{fam};font-size:{size:.1f}pt;color:{col};'
            f'{"font-weight:bold;" if bold else ""}{f"text-align:{al}" if al else ""}">{body}</p>')


def _grow(M, pr, r, obst, size):
    """Çeviri metni için kutuyu boş alana doğru büyüt: yatayda simetrik kenar boşluğuna (Arapçada sağ kenara hizalanabilsin),
    dikeyde alttaki ilk engele kadar. Başka bir bloğa / görsele taşmaz."""
    W_, H_ = pr.width, pr.height
    others = [o for o in obst if not (abs(o.x0 - r.x0) < .5 and abs(o.y0 - r.y0) < .5 and abs(o.x1 - r.x1) < .5)]
    g = M.Rect(min(r.x0, max(18, W_ - r.x1)), r.y0, max(r.x1, min(W_ - 18, W_ - r.x0)), r.y1)
    if any(g.intersects(o) and not r.intersects(o) for o in others): g = M.Rect(r)
    below = [o.y0 for o in others if o.y0 >= r.y1 - 1 and o.x0 < g.x1 and o.x1 > g.x0]
    lim = min(below + [H_ - 24]) - 1
    g.y1 = max(r.y1 + size * 0.3, min(lim, r.y1 + size * 4))
    return g


def translate_pdf(src_path, dst_path, src, tgt, settings=None, usage=None, on_progress=None, cancel=None):
    M = _pdf()
    doc = M.open(src_path)
    pages = []
    for page in doc:
        bl = _blocks(page)
        pages.append((page.number, bl, _scanned(page, bl)))
    texts = [b['text'] for _, bl, sc in pages if not sc for b in bl if CV.needs(b['text'])]
    if src not in CV.LANGS: src = CV.detect(' '.join(texts[:80]))
    # taranmış sayfalar: OCR
    from . import ocr as OCR
    scans = {}
    for no, bl, sc in pages:
        if sc:
            if cancel and cancel(): break
            t, _ = OCR.ocr(OCR.pdf_page_image(doc[no]), src if src in CV.LANGS else 'auto', settings, usage)
            scans[no] = t
    if scans and src not in CV.LANGS: src = CV.detect(' '.join(scans.values()))
    T = CV.Translator(settings, usage)
    total_n = len(texts) + sum(1 for _ in scans)
    outs = T.run(texts, src, tgt, (lambda d, n, e: on_progress(d, total_n, e)) if on_progress else None, cancel)
    it = iter(outs)
    fd = _fonts_dir()
    arch = M.Archive(fd) if fd else None
    for no, bl, sc in pages:
        if sc: continue
        page = doc[no]
        todo = [b for b in bl if CV.needs(b['text'])]
        if not todo: continue
        for b in todo: page.add_redact_annot(M.Rect(b['bbox']))
        kw = {'images': M.PDF_REDACT_IMAGE_NONE}
        if hasattr(M, 'PDF_REDACT_LINE_ART_NONE'): kw['graphics'] = M.PDF_REDACT_LINE_ART_NONE
        page.apply_redactions(**kw)
        obst = [M.Rect(b['bbox']) for b in bl] + [M.Rect(i['bbox']) for i in page.get_image_info()]
        for b in todo:
            o = next(it)
            r = _grow(M, page.rect, M.Rect(b['bbox']), obst, b['size'])
            page.insert_htmlbox(r, _html(o, b['size'], b['color'], b['bold'], b['align'], tgt), css=CSS, archive=arch, scale_low=0.35)
    # taranmış sayfanın çevirisi: hemen arkasına yeni sayfa (sondan başa ekle ki sayfa numaraları kaymasın)
    if scans:
        tx = {}
        st = CV.Translator(settings, usage, engine_list=T.engines)
        for no, t in scans.items():
            o, rep = CV.translate_text(t, src, tgt, settings, usage, translator=st)
            tx[no] = o
            for k, v in rep['engines'].items(): T.report['engines'][k] = T.report['engines'].get(k, 0) + v
        for no in sorted(tx, reverse=True):
            ref = doc[no].rect
            np_ = doc.new_page(no + 1, width=ref.width, height=ref.height)
            head = {'tr': f'Çeviri — sayfa {no + 1}', 'en': f'Translation — page {no + 1}', 'ar': f'الترجمة — الصفحة {no + 1}'}[tgt]
            box = M.Rect(42, 42, ref.width - 42, ref.height - 42)
            body = _html(head, 13, 0x1F3A5F, True, '', tgt) + '<br>' + ''.join(
                _html(par, 10.5, 0, False, 'justify' if tgt != 'ar' else '', tgt) + '<br>' for par in tx[no].split('\n\n') if par.strip())
            np_.insert_htmlbox(box, body, css=CSS, archive=arch, scale_low=0.3)
    doc.save(dst_path, garbage=3, deflate=True)
    T.report['src'] = src; T.report['scanned'] = len(scans)
    return T.report


# =============================================================== görüntü / metin
def _rtl_para(p):
    _set_dir(p._p, True)


def translate_image(src_path, dst_path, src, tgt, settings=None, usage=None, on_progress=None, cancel=None, ocr_text=None):
    """Görüntü → OCR → çeviri → DOCX (orijinal görüntü ortada + başlık + çeviri)."""
    from . import ocr as OCR
    import docx
    from docx.shared import Cm, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    eng_ocr = ''
    if ocr_text is None: ocr_text, eng_ocr = OCR.ocr(src_path, src if src in CV.LANGS else 'auto', settings, usage)
    if src not in CV.LANGS: src = CV.detect(ocr_text)
    out, rep = translate_text(ocr_text, src, tgt, settings, usage, on_progress, cancel)
    d = docx.Document()
    sec = d.sections[0]
    sec.left_margin = sec.right_margin = Cm(2); sec.top_margin = sec.bottom_margin = Cm(1.8)
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    from PIL import Image
    im = Image.open(src_path); w, h = im.size
    maxw = (sec.page_width - sec.left_margin - sec.right_margin) / 914400 * 2.54
    wcm = min(maxw, w / 96 * 2.54)
    if h / w * wcm > 13: wcm = 13 * w / h
    buf = io.BytesIO(); im.convert('RGB').save(buf, 'PNG'); buf.seek(0)
    p.add_run().add_picture(buf, width=Cm(wcm))
    L = {'tr': ('Çeviri', 'Kaynak metin (OCR)'), 'en': ('Translation', 'Source text (OCR)'), 'ar': ('الترجمة', 'النص الأصلي (التعرف الضوئي)')}
    hd = d.add_paragraph(); r = hd.add_run(L[tgt][0]); r.bold = True; r.font.size = Pt(14); r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    if tgt == 'ar': _rtl_para(hd)
    for par in out.split('\n'):
        x = d.add_paragraph(par); x.paragraph_format.space_after = Pt(2)
        if tgt == 'ar': _rtl_para(x)
        else: x.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    hd2 = d.add_paragraph(); r = hd2.add_run(L[tgt][1]); r.bold = True; r.font.size = Pt(11); r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    if tgt == 'ar': _rtl_para(hd2)
    for par in ocr_text.split('\n'):
        x = d.add_paragraph(); rr = x.add_run(par); rr.font.size = Pt(9); rr.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
        if src == 'ar': _rtl_para(x)
    d.save(dst_path)
    rep['src'] = src; rep['ocr'] = eng_ocr
    return rep


def translate_text(text, src, tgt, settings=None, usage=None, on_progress=None, cancel=None):
    return CV.translate_text(text, src, tgt, settings, usage, on_progress, cancel)


def translate_file(src_path, dst_path, src, tgt, settings=None, usage=None, on_progress=None, cancel=None):
    k = kind(src_path)
    if k == 'docx': return translate_docx(src_path, dst_path, src, tgt, settings, usage, on_progress, cancel)
    if k == 'pdf': return translate_pdf(src_path, dst_path, src, tgt, settings, usage, on_progress, cancel)
    if k == 'img': return translate_image(src_path, dst_path, src, tgt, settings, usage, on_progress, cancel)
    if k == 'txt':
        raw = open(src_path, 'rb').read()
        for enc in ('utf-8-sig', 'cp1254', 'cp1256', 'latin-1'):
            try: txt = raw.decode(enc); break
            except UnicodeDecodeError: continue
        out, rep = CV.translate_text(txt, src, tgt, settings, usage, on_progress, cancel)
        with open(dst_path, 'w', encoding='utf-8-sig' if tgt == 'ar' else 'utf-8') as f: f.write(out)
        return rep
    raise ValueError('unsupported file type')
