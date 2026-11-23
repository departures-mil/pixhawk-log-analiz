"""Antetli DOCX ve PDF rapor üretimi (TR/EN/AR, Arapça sağdan sola)."""
from __future__ import annotations
import io, os, time, hashlib, json, re, uuid, copy
import numpy as np
from .analysis import Analysis, fmt_t
from .rtexts import RT, LESSON
from . import texts, charts, knowledge as K

SEV_COL = {0: '2563EB', 1: 'D97706', 2: 'DC2626'}
ST_COL = {'good': '16A34A', 'warn': 'D97706', 'bad': 'DC2626'}
V_COL = {'normal': '16A34A', 'incident': 'D97706', 'crash': 'DC2626', 'noflight': '6B7280'}

DEFAULT_LH = {'org': '', 'sub': '', 'logo': '', 'bg': '', 'color': '#1E3A8A', 'watermark': '', 'footer': '', 'prepared_by': ''}


def R(key, lang):
    return RT[key][('tr', 'en', 'ar').index(lang)]


def _strip_md(s):
    return re.sub(r'\*\*(.+?)\*\*', r'\1', s).replace('`', '')


class ReportData:
    """Rapor için hazırlanmış, dile göre çevrilmiş içerik."""
    def __init__(self, A: Analysis, lang='tr', ai_text=None, online_map=True, map_src='osm', charts_on=None):
        self.A = A; self.lang = lang; self.ai_text = ai_text
        self.id = time.strftime('%Y%m%d') + '-' + uuid.uuid4().hex[:8].upper()
        self.generated = time.strftime('%Y-%m-%d %H:%M')
        L = A.L
        u = L.unix_at(A.flights[0][0] if A.flights else 0)
        self.flight_date = time.strftime('%Y-%m-%d %H:%M', time.localtime(u)) if u and L.kind == 'bin' else (time.strftime('%Y-%m-%d %H:%M', time.localtime(u)) if u else '-')
        self.imgs = []
        for key, fn in charts.ALL:
            if charts_on and key not in charts_on: continue
            try:
                b = fn(A, lang)
            except Exception:
                b = None
            if b: self.imgs.append((key, b))
        self.map = None
        try: self.map = charts.chart_map(A, lang, online=online_map, src=map_src)
        except Exception: pass
        self.health_img = charts.chart_health(A, lang)
        self.timeline_img = charts.chart_timeline(A, lang)

    def t(self, key, **a):
        return texts.T(key, self.lang, **a)

    def facts_rows(self):
        A = self.A; L = A.L; f = A.facts; lg = self.lang
        def tt(x): return fmt_t(x) if x is not None else '-'
        rows = [
            (R('f_file', lg), os.path.basename(L.path)),
            (R('f_vehicle', lg), f"{A.vehicle} · {L.version or '-'}"),
            (R('f_date', lg), self.flight_date),
            (R('f_logdur', lg), fmt_t(L.duration)),
            (R('f_flight', lg), fmt_t(f.get('flight_time', 0)) + (f"  ({f.get('n_flights')})" if f.get('n_flights', 0) > 1 else '')),
            (R('f_takeoff', lg), tt(f.get('takeoff_t'))),
            (R('f_land', lg), tt(f.get('land_t'))),
            (R('f_maxalt', lg), f"{f['max_alt']:.1f} m @ {fmt_t(f['max_alt_t'])}" if 'max_alt' in f else '-'),
            (R('f_dist', lg), f"{f.get('distance', 0) / 1000:.2f} km / {f.get('max_dist', 0):.0f} m"),
            (R('f_speed', lg), f"{f.get('max_gs', 0):.1f} / {f.get('max_as', 0):.1f} m/s"),
            (R('f_batt', lg), (f"{f['min_volt']:.2f} V" if 'min_volt' in f else '-') + (f" / {f['used_mah']:.0f} mAh" if f.get('used_mah') else '')),
        ]
        if L.board: rows.append((R('f_board', lg), str(L.board)))
        return rows

    def verify_payload(self):
        A = self.A
        return f"PLA1|{self.id}|{A.verdict.get('kind')}|{A.overall}|{os.path.basename(A.L.path)[:40]}"

    def qr_png(self):
        import qrcode
        q = qrcode.QRCode(box_size=6, border=1); q.add_data(self.verify_payload()); q.make(fit=True)
        b = io.BytesIO(); q.make_image(fill_color='black', back_color='white').save(b, format='PNG'); return b.getvalue()


# ------------------------------------------------------------------ DOCX
def build_docx(rd: ReportData, path, lh=None):
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor, Emu
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    lh = {**DEFAULT_LH, **(lh or {})}
    lg = rd.lang; rtl = lg == 'ar'; A = rd.A
    doc = Document()
    sec = doc.sections[0]
    sec.page_height = Cm(29.7); sec.page_width = Cm(21.0)
    sec.left_margin = sec.right_margin = Cm(1.8); sec.top_margin = Cm(3.0 if not lh['bg'] else 3.6); sec.bottom_margin = Cm(2.2)
    sec.header_distance = Cm(0.8); sec.footer_distance = Cm(0.8)
    st = doc.styles['Normal']; st.font.name = 'Calibri'; st.font.size = Pt(10)
    st.element.rPr.rFonts.set(qn('w:cs'), 'Arial'); st.element.rPr.rFonts.set(qn('w:eastAsia'), 'Calibri')
    if rtl:
        szcs = OxmlElement('w:szCs'); szcs.set(qn('w:val'), '22'); st.element.rPr.append(szcs)
    color = RGBColor.from_string(lh['color'].lstrip('#').upper()[:6] or '1E3A8A')

    def set_rtl(p):
        if not rtl: return
        pPr = p._p.get_or_add_pPr(); b = OxmlElement('w:bidi'); b.set(qn('w:val'), '1'); pPr.insert(0, b)
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    def run_rtl(r):
        if rtl:
            rPr = r._r.get_or_add_rPr(); e = OxmlElement('w:rtl'); e.set(qn('w:val'), '1'); rPr.append(e)

    def para(text, bold=False, size=None, col=None, align=None, space=4, italic=False, container=None):
        p = (container or doc).add_paragraph(); set_rtl(p)
        if align is not None and not rtl: p.alignment = align
        r = p.add_run(text); r.bold = bold; r.italic = italic; run_rtl(r)
        if size: r.font.size = Pt(size)
        if col: r.font.color.rgb = RGBColor.from_string(col)
        p.paragraph_format.space_after = Pt(space)
        return p

    def heading(text, lvl=1):
        p = para(text, bold=True, size=14 if lvl == 1 else 11.5, col=lh['color'].lstrip('#').upper(), space=6)
        p.paragraph_format.space_before = Pt(10 if lvl == 1 else 6)
        if lvl == 1:
            pPr = p._p.get_or_add_pPr(); bdr = OxmlElement('w:pBdr'); b = OxmlElement('w:bottom')
            for k, v in (('val', 'single'), ('sz', '8'), ('space', '1'), ('color', lh['color'].lstrip('#'))): b.set(qn('w:' + k), v)
            bdr.append(b); pPr.append(bdr)
        return p

    def shade(cell, hexcol):
        tcPr = cell._tc.get_or_add_tcPr(); s = OxmlElement('w:shd'); s.set(qn('w:val'), 'clear'); s.set(qn('w:color'), 'auto'); s.set(qn('w:fill'), hexcol); tcPr.append(s)

    def table(rows, header=None, widths=None, colors=None):
        cols = len(rows[0]) if rows else len(header)
        if rtl:
            rows = [list(reversed(r)) for r in rows]; header = list(reversed(header)) if header else None
            widths = list(reversed(widths)) if widths else None
        tb = doc.add_table(rows=0, cols=cols); tb.style = 'Table Grid'; tb.alignment = WD_TABLE_ALIGNMENT.CENTER
        if rtl:
            tblPr = tb._tbl.tblPr; b = OxmlElement('w:bidiVisual'); tblPr.append(b)
            rows = [list(reversed(r)) for r in rows]; header = list(reversed(header)) if header else None
            widths = list(reversed(widths)) if widths else None
        if header:
            cells = tb.add_row().cells
            for c, h in zip(cells, header):
                c.text = ''; p = c.paragraphs[0]; set_rtl(p); r = p.add_run(str(h)); r.bold = True; r.font.size = Pt(9); r.font.color.rgb = RGBColor(255, 255, 255); run_rtl(r)
                shade(c, lh['color'].lstrip('#'))
        for ri, row in enumerate(rows):
            cells = tb.add_row().cells
            for ci, (c, v) in enumerate(zip(cells, row)):
                c.text = ''; p = c.paragraphs[0]; set_rtl(p); r = p.add_run(str(v)); r.font.size = Pt(9); run_rtl(r)
                if colors and colors[ri] and colors[ri][ci]:
                    shade(c, colors[ri][ci])
            if ri % 2 == 1 and not (colors and colors[ri]):
                for c in cells: shade(c, 'F8FAFC')
        if widths:
            for row in tb.rows:
                for c, w in zip(row.cells, widths): c.width = Cm(w)
        doc.add_paragraph().paragraph_format.space_after = Pt(2)
        return tb

    def image(b, width_cm=17.2):
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(io.BytesIO(b), width=Cm(width_cm))
        p.paragraph_format.space_after = Pt(2)

    # ---- Antet (başlık/altbilgi + arka plan)
    hdr = sec.header; hp = hdr.paragraphs[0]
    _letterhead_docx(doc, sec, lh, rd, rtl, para, set_rtl, run_rtl)

    # ---- Başlık ve özet kartı
    para(R('title', lg), bold=True, size=20, col=lh['color'].lstrip('#').upper(), align=WD_ALIGN_PARAGRAPH.CENTER, space=0)
    para(f"{R('subtitle', lg)} · {os.path.basename(A.L.path)}", size=9, col='6B7280', align=WD_ALIGN_PARAGRAPH.CENTER, space=10)
    v = A.verdict.get('kind', 'normal')
    tb = doc.add_table(rows=1, cols=2); tb.alignment = WD_TABLE_ALIGNMENT.CENTER
    if rtl: tb._tbl.tblPr.append(OxmlElement('w:bidiVisual'))
    c0, c1 = tb.rows[0].cells
    shade(c0, V_COL[v]); c0.width = Cm(11); c1.width = Cm(6)
    p = c0.paragraphs[0]; set_rtl(p); r = p.add_run(R('verdict', lg) + ': ' + rd.t('v_' + v)); r.bold = True; r.font.size = Pt(15); r.font.color.rgb = RGBColor(255, 255, 255); run_rtl(r)
    p2 = c0.add_paragraph(); set_rtl(p2); r = p2.add_run(rd.t('v_desc_' + v)); r.font.size = Pt(9.5); r.font.color.rgb = RGBColor(255, 255, 255); run_rtl(r)
    sc = A.overall; scol = ST_COL['good' if sc >= 80 else ('warn' if sc >= 55 else 'bad')]
    shade(c1, 'F8FAFC')
    p = c1.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER; r = p.add_run(f'{sc}'); r.bold = True; r.font.size = Pt(30); r.font.color.rgb = RGBColor.from_string(scol)
    p = c1.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; r = p.add_run('/100 · ' + R('overall', lg)); r.font.size = Pt(8); run_rtl(r)
    doc.add_paragraph()
    # Trafik ışıkları
    if A.health:
        items = list(A.health.items())
        rows = [[('● ' if True else '') + rd.t('dom_' + k), str(h['score']), rd.t('st_' + h['status'])] for k, h in items]
        cols = [[None, None, ST_COL[h['status']].replace('16A34A', 'DCFCE7').replace('D97706', 'FEF3C7').replace('DC2626', 'FEE2E2')] for _, h in items]
        heading(R('summary', lg), 2)
        table(rows, [R('h_area', lg), R('h_score', lg), R('h_status', lg)], [8, 3, 4], cols)
    heading(R('facts', lg), 2)
    table([list(r) for r in rd.facts_rows()], None, [6, 11])
    if v == 'crash' or A.verdict.get('evidence'):
        heading(R('evidence', lg), 2)
        for e in A.verdict.get('evidence', []):
            para('• ' + texts.render(e, lg, fmt_t), size=9.5, space=2)

    # ---- Kök neden
    if A.root:
        heading(R('root', lg))
        c = A.root['cause']
        para(f"{R('root_cause', lg)}: {rd.t('cause_' + c)}  ({fmt_t(A.root.get('t', 0))})", bold=True, size=11.5, col='DC2626' if v == 'crash' else 'D97706')
        heading(R('root_what', lg), 2); para(rd.t('why_' + c))
        heading(R('root_chain', lg), 2)
        rows = [[fmt_t(s['t']), texts.chain_step(s, lg, fmt_t)] for s in A.root.get('chain', [])]
        if rows: table(rows, [R('e_time', lg), R('e_text', lg)], [3, 14])
        heading(R('root_prev', lg), 2); para(rd.t('prevent_' + c))
        oth = A.root.get('others') or []
        if oth: para(R('root_others', lg) + ': ' + ', '.join(rd.t('cause_' + o) for o in oth), italic=True, size=9.5)

    # ---- AI
    if rd.ai_text:
        heading(R('ai', lg)); para(R('ai_note', lg), italic=True, size=8.5, col='6B7280')
        for line in rd.ai_text.splitlines():
            s = _strip_md(line).strip()
            if not s: continue
            if s.startswith('#'): para(s.lstrip('# '), bold=True, size=11)
            else: para(s, size=9.5, space=3)

    # ---- Sağlık ayrıntıları
    heading(R('health', lg))
    if rd.health_img: image(rd.health_img, 15)
    rows = []; cols = []
    for k, h in A.health.items():
        fnd = '\n'.join('• ' + texts.render(f, lg) for f in h['findings']) or R('no_find', lg)
        rows.append([rd.t('dom_' + k), str(h['score']), fnd]); cols.append([None, {'good': 'DCFCE7', 'warn': 'FEF3C7', 'bad': 'FEE2E2'}[h['status']], None])
    if rows: table(rows, [R('h_area', lg), R('h_score', lg), R('h_find', lg)], [4, 2, 11], cols)

    # ---- Aşamalar
    if A.phases:
        heading(R('phases', lg))
        rows = []
        for p_ in A.phases:
            s = p_.get('stats', {})
            f1 = lambda x, u='': f'{x:.0f}{u}' if isinstance(x, (int, float)) else '-'
            rows.append([rd.t('ph_' + p_['name']), f"{fmt_t(p_['t0'])}–{fmt_t(p_['t1'])}", fmt_t(s.get('dur', 0)),
                         f"{f1(s.get('alt_mean'))}/{f1(s.get('alt_max'))} m", f1(s.get('as_mean') if s.get('as_mean') is not None else s.get('gs_mean'), ' m/s'),
                         f1(s.get('thr_mean'), '%'), f"{f1(s.get('roll_max'))}°/{f1(s.get('pitch_max'))}°"])
        table(rows, [R(k, lg) for k in ('p_phase', 'p_time', 'p_dur', 'p_alt', 'p_spd', 'p_thr', 'p_att')], [2.4, 3.4, 1.8, 2.6, 2.2, 2, 2.6])

    # ---- Grafikler + ders notları
    heading(R('charts', lg))
    if rd.map:
        image(rd.map, 16); _lesson_docx(rd, 'c_map', para, table, heading, lg)
    for key, b in rd.imgs:
        image(b); _lesson_docx(rd, key, para, table, heading, lg)

    # ---- Zaman çizelgesi
    heading(R('timeline', lg))
    if rd.timeline_img: image(rd.timeline_img)
    ev = [e for e in A.events if e['sev'] > 0 or e['cat'] in ('mode', 'flight')][:150]
    rows = [[fmt_t(e['t']), R('cat_' + e['cat'], lg), texts.render(e['text'], lg)] for e in ev]
    cols = [[None, None, {0: None, 1: 'FEF3C7', 2: 'FEE2E2'}[e['sev']]] for e in ev]
    if rows: table(rows, [R('e_time', lg), R('e_type', lg), R('e_text', lg)], [2.6, 2.4, 12], cols)

    # ---- Parametre denetimi
    heading(R('params', lg))
    rows = [[R('sev' + str(f['sev']), lg), texts.render(f['text'], lg)] for f in A.param_findings]
    cols = [[{0: 'DBEAFE', 1: 'FEF3C7', 2: 'FEE2E2'}[f['sev']], None] for f in A.param_findings]
    table(rows, None, [2.6, 14.4], cols)

    # ---- Eğitim eki
    heading(R('thresholds', lg))
    rows = []
    for key in ('c_gps', 'c_vibe', 'c_bat', 'c_ekf', 'c_att', 'c_mag'):
        Ls = LESSON[key]; i = ('tr', 'en', 'ar').index(lg)
        rows.append([R(key, lg), Ls['normal'][i], Ls['warn'][i], Ls['danger'][i]])
    table(rows, ['', R('th_normal', lg), R('th_warn', lg), R('th_danger', lg)], [3.2, 4.6, 4.6, 4.6],
          [[None, 'DCFCE7', 'FEF3C7', 'FEE2E2'] for _ in rows])
    para(R('offline_note', lg) if not rd.ai_text else R('ai_note', lg), italic=True, size=8, col='6B7280')

    # ---- Doğrulama
    heading(R('verify', lg), 2)
    tb = doc.add_table(rows=1, cols=2)
    c0, c1 = tb.rows[0].cells; c0.width = Cm(4); c1.width = Cm(13)
    c0.paragraphs[0].add_run().add_picture(io.BytesIO(rd.qr_png()), width=Cm(3.2))
    p = c1.paragraphs[0]; set_rtl(p); r = p.add_run(f"{R('report_id', lg)}: {rd.id}\n{R('generated', lg)}: {rd.generated}\n\n{R('verify_txt', lg)}"); r.font.size = Pt(9); run_rtl(r)
    doc.save(path)
    return path


def _lesson_docx(rd, key, para, table, heading, lg):
    Ls = LESSON.get(key)
    if not Ls: return
    i = ('tr', 'en', 'ar').index(lg)
    para('ⓘ ' + R('why_see', lg) + ' ' + Ls['what'][i], size=9, col='1F2937', space=2, italic=True)
    table([[Ls['normal'][i], Ls['warn'][i], Ls['danger'][i]]], [R('th_normal', lg), R('th_warn', lg), R('th_danger', lg)], [5.7, 5.7, 5.7],
          [['DCFCE7', 'FEF3C7', 'FEE2E2']])


def _wm_png(lh, rd):
    """Arka plan filigranı: logo (soluk) veya kurum adı."""
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance
    W, H = 1240, 1754
    img = Image.new('RGBA', (W, H), (255, 255, 255, 0))
    if lh.get('logo') and os.path.exists(lh['logo']):
        try:
            lg_ = Image.open(lh['logo']).convert('RGBA'); lg_.thumbnail((760, 760))
            a = lg_.split()[-1].point(lambda x: int(x * 0.07)); lg_.putalpha(a)
            img.paste(lg_, ((W - lg_.width) // 2, (H - lg_.height) // 2), lg_)
            return img
        except Exception:
            pass
    txt = lh.get('watermark') or lh.get('org') or ''
    if not txt:
        return None
    d = ImageDraw.Draw(img)
    try:
        from matplotlib import font_manager
        fp = font_manager.findfont('DejaVu Sans:bold')
        f = ImageFont.truetype(fp, 110)
    except Exception:
        f = ImageFont.load_default()
    if rd.lang == 'ar': txt = charts.shape(txt, 'ar')
    tw = d.textlength(txt, font=f)
    t = Image.new('RGBA', (int(tw) + 40, 160), (255, 255, 255, 0)); ImageDraw.Draw(t).text((20, 10), txt, font=f, fill=(30, 58, 138, 20))
    t = t.rotate(35, expand=True)
    img.paste(t, ((W - t.width) // 2, (H - t.height) // 2), t)
    return img


def _anchor_xml(rid, cx, cy, name='bg', behind=True, x=0, y=0):
    return f'''<wp:anchor xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="0" behindDoc="{1 if behind else 0}" locked="1" layoutInCell="1" allowOverlap="1">
<wp:simplePos x="0" y="0"/><wp:positionH relativeFrom="page"><wp:posOffset>{x}</wp:posOffset></wp:positionH><wp:positionV relativeFrom="page"><wp:posOffset>{y}</wp:posOffset></wp:positionV>
<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/><wp:docPr id="{abs(hash(name)) % 10000 + 100}" name="{name}"/><wp:cNvGraphicFramePr/>
<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="{name}.png"/><pic:cNvPicPr/></pic:nvPicPr>
<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:anchor>'''


def _letterhead_docx(doc, sec, lh, rd, rtl, para, set_rtl, run_rtl):
    from docx.shared import Pt, Cm, RGBColor, Emu
    from docx.oxml import parse_xml
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    hdr = sec.header; hp = hdr.paragraphs[0]
    W, H = Emu(int(21.0 * 360000)), Emu(int(29.7 * 360000))
    def add_anchor(png_bytes, name):
        part = hdr.part
        rid, _img = part.get_or_add_image(io.BytesIO(png_bytes))
        run = hp.add_run()
        drawing = OxmlElement('w:drawing'); drawing.append(parse_xml(_anchor_xml(rid, int(W), int(H), name)))
        run._r.append(drawing)
    if lh.get('bg') and os.path.exists(lh['bg']):
        from PIL import Image
        im = Image.open(lh['bg']).convert('RGB'); b = io.BytesIO(); im.save(b, format='PNG')
        add_anchor(b.getvalue(), 'letterhead')
    else:
        # Üretilmiş antet: renkli şerit + logo + kurum adı
        from PIL import Image, ImageDraw
        Wp, Hp = 1240, 1754
        img = Image.new('RGBA', (Wp, Hp), (255, 255, 255, 0)); d = ImageDraw.Draw(img)
        col = tuple(int(lh['color'].lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
        d.rectangle([0, 0, Wp, 14], fill=col + (255,)); d.rectangle([0, Hp - 10, Wp, Hp], fill=col + (255,))
        d.rectangle([0, 150, Wp, 153], fill=col + (90,))
        wm = _wm_png(lh, rd)
        if wm: img.alpha_composite(wm)
        b = io.BytesIO(); img.save(b, format='PNG'); add_anchor(b.getvalue(), 'letterhead')
        # Logo + kurum adı
        tb = hdr.add_table(rows=1, cols=2, width=Cm(17.4))
        if rtl: tb._tbl.tblPr.append(OxmlElement('w:bidiVisual'))
        c0, c1 = tb.rows[0].cells; c0.width = Cm(2.6); c1.width = Cm(14.8)
        if lh.get('logo') and os.path.exists(lh['logo']):
            try: c0.paragraphs[0].add_run().add_picture(lh['logo'], height=Cm(1.6))
            except Exception: pass
        p = c1.paragraphs[0]; set_rtl(p)
        r = p.add_run(lh.get('org') or R('title', rd.lang)); r.bold = True; r.font.size = Pt(13); r.font.color.rgb = RGBColor(*col); run_rtl(r)
        if lh.get('sub'):
            p = c1.add_paragraph(); set_rtl(p); r = p.add_run(lh['sub']); r.font.size = Pt(8.5); r.font.color.rgb = RGBColor(0x6B, 0x72, 0x80); run_rtl(r)
    # Altbilgi
    fp = sec.footer.paragraphs[0]; set_rtl(fp)
    txt = (lh.get('footer') or '') + (' · ' if lh.get('footer') else '') + f"{R('report_id', rd.lang)}: {rd.id}" + (f" · {R('prepared_by', rd.lang)}: {lh['prepared_by']}" if lh.get('prepared_by') else '') + f" · {R('page', rd.lang)} "
    r = fp.add_run(txt); r.font.size = Pt(7.5); r.font.color.rgb = RGBColor(0x6B, 0x72, 0x80); run_rtl(r)
    for code in ('begin', None, 'end'):
        rr = fp.add_run(); rr.font.size = Pt(7.5)
        if code:
            fc = OxmlElement('w:fldChar'); fc.set(qn('w:fldCharType'), code); rr._r.append(fc)
        else:
            it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve'); it.text = 'PAGE'; rr._r.append(it)


# ------------------------------------------------------------------- PDF
def _fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from matplotlib import font_manager
    try:
        pdfmetrics.getFont('DJ'); return
    except Exception:
        pass
    reg = font_manager.findfont('DejaVu Sans'); bold = font_manager.findfont('DejaVu Sans:bold')
    pdfmetrics.registerFont(TTFont('DJ', reg)); pdfmetrics.registerFont(TTFont('DJB', bold))
    from reportlab.lib.fonts import addMapping
    addMapping('DJ', 0, 0, 'DJ'); addMapping('DJ', 1, 0, 'DJB'); addMapping('DJ', 0, 1, 'DJ'); addMapping('DJ', 1, 1, 'DJB')


def build_pdf(rd: ReportData, path, lh=None):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from xml.sax.saxutils import escape
    _fonts()
    lh = {**DEFAULT_LH, **(lh or {})}
    lg = rd.lang; rtl = lg == 'ar'; A = rd.A
    main = colors.HexColor(lh['color'] if lh['color'].startswith('#') else '#' + lh['color'])
    al = TA_RIGHT if rtl else TA_LEFT
    base = ParagraphStyle('b', fontName='DJ', fontSize=9, leading=12.5, alignment=al, textColor=colors.HexColor('#111827'))
    small = ParagraphStyle('s', parent=base, fontSize=7.6, leading=10)
    H1 = ParagraphStyle('h1', parent=base, fontName='DJB', fontSize=13.5, leading=17, textColor=main, spaceBefore=8, spaceAfter=5)
    H2 = ParagraphStyle('h2', parent=base, fontName='DJB', fontSize=10.5, leading=14, textColor=main, spaceBefore=6, spaceAfter=3)
    TT = ParagraphStyle('tt', parent=base, fontName='DJB', fontSize=19, leading=24, alignment=TA_CENTER, textColor=main)
    W_ = A4[0] - 3.6 * cm

    def ar_lines(text, style, width):
        import arabic_reshaper
        from bidi.algorithm import get_display
        out = []
        for para_ in str(text).split('\n'):
            words = para_.split(' '); line = ''
            for w in words:
                cand = (line + ' ' + w).strip()
                if stringWidth(arabic_reshaper.reshape(cand), style.fontName, style.fontSize) > width - 4 and line:
                    out.append(get_display(arabic_reshaper.reshape(line))); line = w
                else:
                    line = cand
            out.append(get_display(arabic_reshaper.reshape(line)))
        return '<br/>'.join(escape(x) for x in out)

    def P(text, style=base, width=None):
        if rtl:
            return Paragraph(ar_lines(text, style, width or W_), style)
        return Paragraph(escape(str(text)).replace('\n', '<br/>'), style)

    def tbl(rows, header=None, widths=None, bg=None, fs=8):
        cs = ParagraphStyle('c', parent=base, fontSize=fs, leading=fs + 3)
        hs = ParagraphStyle('ch', parent=cs, fontName='DJB', textColor=colors.white)
        widths = widths or [W_ / len(rows[0])] * len(rows[0])
        data = []
        if header: data.append([P(h, hs, w) for h, w in zip(header, widths)])
        for r in rows: data.append([P(c, cs, w) for c, w in zip(r, widths)])
        if rtl:
            data = [list(reversed(r)) for r in data]; widths = list(reversed(widths))
        t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
        ts = [('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CBD5E1')), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
              ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4), ('TOPPADDING', (0, 0), (-1, -1), 2.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5)]
        if header: ts.append(('BACKGROUND', (0, 0), (-1, 0), main))
        off = 1 if header else 0
        n = len(widths)
        for ri, r in enumerate(rows):
            if bg and bg[ri]:
                for ci, c in enumerate(bg[ri]):
                    if c:
                        cc = (n - 1 - ci) if rtl else ci
                        ts.append(('BACKGROUND', (cc, ri + off), (cc, ri + off), colors.HexColor('#' + c)))
            elif ri % 2: ts.append(('BACKGROUND', (0, ri + off), (-1, ri + off), colors.HexColor('#F8FAFC')))
        t.setStyle(TableStyle(ts)); return t

    def img(b, w=W_):
        from PIL import Image as PI
        im = PI.open(io.BytesIO(b)); r = im.height / im.width
        return Image(io.BytesIO(b), width=w, height=w * r)

    story = []
    story += [P(R('title', lg), TT), Spacer(1, 2), P(f"{R('subtitle', lg)} · {os.path.basename(A.L.path)}", ParagraphStyle('c', parent=small, alignment=TA_CENTER, textColor=colors.HexColor('#6B7280'))), Spacer(1, 8)]
    v = A.verdict.get('kind', 'normal')
    vs = ParagraphStyle('v', parent=base, fontName='DJB', fontSize=14, leading=18, textColor=colors.white)
    vd = ParagraphStyle('vd', parent=base, fontSize=8.8, leading=12, textColor=colors.white)
    sc = A.overall; scol = colors.HexColor('#' + ST_COL['good' if sc >= 80 else ('warn' if sc >= 55 else 'bad')])
    big = ParagraphStyle('big', parent=base, fontName='DJB', fontSize=28, leading=32, alignment=TA_CENTER, textColor=scol)
    cap = ParagraphStyle('cap', parent=small, alignment=TA_CENTER)
    left = [P(R('verdict', lg) + ': ' + rd.t('v_' + v), vs, 11.3 * cm), P(rd.t('v_desc_' + v), vd, 11.3 * cm)]
    right = [Paragraph(str(sc), big), P('/100 · ' + R('overall', lg), cap, 5.5 * cm)]
    row = [left, right] if not rtl else [right, left]
    card = Table([row], colWidths=[11.8 * cm, W_ - 11.8 * cm] if not rtl else [W_ - 11.8 * cm, 11.8 * cm])
    card.setStyle(TableStyle([('BACKGROUND', (0 if not rtl else 1, 0), (0 if not rtl else 1, 0), colors.HexColor('#' + V_COL[v])),
                              ('BACKGROUND', (1 if not rtl else 0, 0), (1 if not rtl else 0, 0), colors.HexColor('#F8FAFC')),
                              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]))
    story += [card, Spacer(1, 8)]
    if A.health:
        story.append(P(R('summary', lg), H2))
        items = list(A.health.items())
        story.append(tbl([[rd.t('dom_' + k), str(h['score']), rd.t('st_' + h['status'])] for k, h in items], [R('h_area', lg), R('h_score', lg), R('h_status', lg)],
                         [9 * cm, 3 * cm, W_ - 12 * cm], [[None, None, {'good': 'DCFCE7', 'warn': 'FEF3C7', 'bad': 'FEE2E2'}[h['status']]] for _, h in items]))
    story.append(P(R('facts', lg), H2))
    story.append(tbl([list(r) for r in rd.facts_rows()], None, [5.5 * cm, W_ - 5.5 * cm]))
    if A.verdict.get('evidence'):
        story.append(P(R('evidence', lg), H2))
        for e in A.verdict['evidence']: story.append(P('• ' + texts.render(e, lg, fmt_t)))
    if A.root:
        story.append(PageBreak()); story.append(P(R('root', lg), H1))
        c = A.root['cause']
        story.append(P(f"{R('root_cause', lg)}: {rd.t('cause_' + c)} ({fmt_t(A.root.get('t', 0))})", ParagraphStyle('rc', parent=H2, textColor=colors.HexColor('#DC2626' if v == 'crash' else '#D97706'))))
        story += [P(R('root_what', lg), H2), P(rd.t('why_' + c)), P(R('root_chain', lg), H2)]
        rows = [[fmt_t(s['t']), texts.chain_step(s, lg, fmt_t)] for s in A.root.get('chain', [])]
        if rows: story.append(tbl(rows, [R('e_time', lg), R('e_text', lg)], [3 * cm, W_ - 3 * cm]))
        story += [P(R('root_prev', lg), H2), P(rd.t('prevent_' + c))]
        if A.root.get('others'): story.append(P(R('root_others', lg) + ': ' + ', '.join(rd.t('cause_' + o) for o in A.root['others']), small))
    if rd.ai_text:
        story += [P(R('ai', lg), H1), P(R('ai_note', lg), small), Spacer(1, 4)]
        for line in rd.ai_text.splitlines():
            s = _strip_md(line).strip()
            if s: story.append(P(s.lstrip('# '), H2 if s.startswith('#') else base))
    story += [PageBreak(), P(R('health', lg), H1)]
    if rd.health_img: story.append(img(rd.health_img, W_ * 0.85))
    rows = []; bgs = []
    for k, h in A.health.items():
        rows.append([rd.t('dom_' + k), str(h['score']), '\n'.join('• ' + texts.render(f, lg) for f in h['findings']) or R('no_find', lg)])
        bgs.append([None, {'good': 'DCFCE7', 'warn': 'FEF3C7', 'bad': 'FEE2E2'}[h['status']], None])
    if rows: story.append(tbl(rows, [R('h_area', lg), R('h_score', lg), R('h_find', lg)], [4 * cm, 1.8 * cm, W_ - 5.8 * cm], bgs))
    if A.phases:
        story.append(P(R('phases', lg), H1))
        f1 = lambda x, u='': f'{x:.0f}{u}' if isinstance(x, (int, float)) else '-'
        rows = [[rd.t('ph_' + p_['name']), f"{fmt_t(p_['t0'])}–{fmt_t(p_['t1'])}", fmt_t(p_['stats'].get('dur', 0)),
                 f"{f1(p_['stats'].get('alt_mean'))}/{f1(p_['stats'].get('alt_max'))} m", f1(p_['stats'].get('as_mean') if p_['stats'].get('as_mean') is not None else p_['stats'].get('gs_mean'), ' m/s'),
                 f1(p_['stats'].get('thr_mean'), '%'), f"{f1(p_['stats'].get('roll_max'))}°/{f1(p_['stats'].get('pitch_max'))}°"] for p_ in A.phases]
        story.append(tbl(rows, [R(k, lg) for k in ('p_phase', 'p_time', 'p_dur', 'p_alt', 'p_spd', 'p_thr', 'p_att')], [2.2 * cm, 3.4 * cm, 1.8 * cm, 2.5 * cm, 2.2 * cm, 2 * cm, W_ - 14.1 * cm], fs=7.5))
    story += [PageBreak(), P(R('charts', lg), H1)]
    def lesson(key):
        Ls = LESSON.get(key)
        if not Ls: return []
        i = ('tr', 'en', 'ar').index(lg)
        return [P('ⓘ ' + R('why_see', lg) + ' ' + Ls['what'][i], ParagraphStyle('l', parent=small, textColor=colors.HexColor('#1F2937'))),
                tbl([[Ls['normal'][i], Ls['warn'][i], Ls['danger'][i]]], [R('th_normal', lg), R('th_warn', lg), R('th_danger', lg)], [W_ / 3] * 3, [['DCFCE7', 'FEF3C7', 'FEE2E2']], fs=7.2), Spacer(1, 6)]
    if rd.map: story.append(KeepTogether([img(rd.map, W_ * 0.9)] + lesson('c_map')))
    for key, b in rd.imgs: story.append(KeepTogether([img(b)] + lesson(key)))
    story += [PageBreak(), P(R('timeline', lg), H1)]
    if rd.timeline_img: story.append(img(rd.timeline_img))
    ev = [e for e in A.events if e['sev'] > 0 or e['cat'] in ('mode', 'flight')][:150]
    if ev:
        story.append(tbl([[fmt_t(e['t']), R('cat_' + e['cat'], lg), texts.render(e['text'], lg)] for e in ev], [R('e_time', lg), R('e_type', lg), R('e_text', lg)],
                         [2.4 * cm, 2.2 * cm, W_ - 4.6 * cm], [[None, None, {0: None, 1: 'FEF3C7', 2: 'FEE2E2'}[e['sev']]] for e in ev], fs=7.5))
    story.append(P(R('params', lg), H1))
    story.append(tbl([[R('sev' + str(f['sev']), lg), texts.render(f['text'], lg)] for f in A.param_findings], None, [2.4 * cm, W_ - 2.4 * cm],
                     [[{0: 'DBEAFE', 1: 'FEF3C7', 2: 'FEE2E2'}[f['sev']], None] for f in A.param_findings]))
    story.append(P(R('thresholds', lg), H1))
    i = ('tr', 'en', 'ar').index(lg)
    rows = [[R(k, lg), LESSON[k]['normal'][i], LESSON[k]['warn'][i], LESSON[k]['danger'][i]] for k in ('c_gps', 'c_vibe', 'c_bat', 'c_ekf', 'c_att', 'c_mag')]
    story.append(tbl(rows, ['', R('th_normal', lg), R('th_warn', lg), R('th_danger', lg)], [3 * cm] + [(W_ - 3 * cm) / 3] * 3, [[None, 'DCFCE7', 'FEF3C7', 'FEE2E2'] for _ in rows], fs=7.2))
    story.append(P(R('offline_note', lg) if not rd.ai_text else R('ai_note', lg), small))
    qr = Image(io.BytesIO(rd.qr_png()), width=3 * cm, height=3 * cm)
    vt = [P(f"{R('report_id', lg)}: {rd.id}", H2, W_ - 4 * cm), P(f"{R('generated', lg)}: {rd.generated}", base, W_ - 4 * cm), P(R('verify_txt', lg), small, W_ - 4 * cm)]
    vr = [qr, vt] if not rtl else [vt, qr]
    t = Table([vr], colWidths=[3.6 * cm, W_ - 3.6 * cm] if not rtl else [W_ - 3.6 * cm, 3.6 * cm]); t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story += [Spacer(1, 8), P(R('verify', lg), H2), t]

    bg_img = None
    if lh.get('bg') and os.path.exists(lh['bg']):
        bg_img = lh['bg']
    wm = None if bg_img else _wm_png(lh, rd)
    wm_bytes = None
    if wm:
        b = io.BytesIO(); wm.save(b, format='PNG'); wm_bytes = b.getvalue()
    from reportlab.lib.utils import ImageReader

    def on_page(c, d):
        c.saveState()
        Wp, Hp = A4
        if bg_img:
            c.drawImage(ImageReader(bg_img), 0, 0, Wp, Hp)
        else:
            if wm_bytes: c.drawImage(ImageReader(io.BytesIO(wm_bytes)), 0, 0, Wp, Hp, mask='auto')
            c.setFillColor(main); c.rect(0, Hp - 0.32 * cm, Wp, 0.32 * cm, fill=1, stroke=0); c.rect(0, 0, Wp, 0.22 * cm, fill=1, stroke=0)
            x = 1.8 * cm
            if lh.get('logo') and os.path.exists(lh['logo']):
                try:
                    ir = ImageReader(lh['logo']); iw, ih = ir.getSize(); h = 1.5 * cm; w = h * iw / ih
                    lx = (Wp - 1.8 * cm - w) if rtl else x
                    c.drawImage(ir, lx, Hp - 2.25 * cm, w, h, mask='auto'); x += w + 0.3 * cm
                except Exception: pass
            c.setFillColor(main); c.setFont('DJB', 12.5)
            org = lh.get('org') or R('title', lg)
            orgs = charts.shape(org, lg)
            if rtl: c.drawRightString(Wp - 1.8 * cm - (2 * cm if lh.get('logo') else 0), Hp - 1.35 * cm, orgs)
            else: c.drawString(x, Hp - 1.35 * cm, orgs)
            if lh.get('sub'):
                c.setFillColor(colors.HexColor('#6B7280')); c.setFont('DJ', 8)
                s = charts.shape(lh['sub'], lg)
                if rtl: c.drawRightString(Wp - 1.8 * cm - (2 * cm if lh.get('logo') else 0), Hp - 1.85 * cm, s)
                else: c.drawString(x, Hp - 1.85 * cm, s)
            c.setStrokeColor(main); c.setLineWidth(0.6); c.line(1.8 * cm, Hp - 2.5 * cm, Wp - 1.8 * cm, Hp - 2.5 * cm)
        c.setFont('DJ', 7); c.setFillColor(colors.HexColor('#6B7280'))
        ft = (lh.get('footer') + ' · ' if lh.get('footer') else '') + f"{R('report_id', lg)}: {rd.id}" + (f" · {R('prepared_by', lg)}: {lh['prepared_by']}" if lh.get('prepared_by') else '') + f" · {R('page', lg)} {d.page}"
        c.drawCentredString(Wp / 2, 0.75 * cm, charts.shape(ft, lg))
        c.restoreState()

    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=(3.6 if bg_img else 2.9) * cm, bottomMargin=1.6 * cm,
                            title=R('title', lg), author=lh.get('prepared_by') or lh.get('org') or 'Pixhawk Log Analiz', subject=rd.id)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return path


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 20), b''): h.update(ch)
    return h.hexdigest()
