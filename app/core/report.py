"""Antetli DOCX ve PDF rapor üretimi (TR/EN/AR, Arapça sağdan sola)."""
from __future__ import annotations
import io, os, time, hashlib, json, re, uuid, copy
import numpy as np
from .analysis import Analysis, fmt_t
from .rtexts import RT, LESSON
from . import texts
from . import why as why_mod, charts, knowledge as K, letterhead as LHM

SEV_COL = {0: '2563EB', 1: 'D97706', 2: 'DC2626'}
ST_COL = {'good': '16A34A', 'warn': 'D97706', 'bad': 'DC2626'}
V_COL = {'normal': '16A34A', 'incident': 'D97706', 'incident_minor': 'CA8A04', 'crash': 'DC2626', 'noflight': '6B7280'}

DEFAULT_LH = {'org': '', 'sub': '', 'logo': '', 'bg': '', 'color': '#1E3A8A', 'watermark': '', 'footer': '', 'prepared_by': '',
              'besmele': False, 'top_cm': 0}


def R(key, lang):
    return RT[key][('tr', 'en', 'ar').index(lang)]


def _strip_md(s):
    return re.sub(r'\*\*(.+?)\*\*', r'\1', s).replace('`', '')


SECTIONS = ['summary', 'incident', 'facts', 'root', 'ai', 'health', 'anomaly', 'pilot', 'weather', 'phases', 'charts', 'timeline', 'params', 'thresholds', 'verify']
SHORT = ['summary', 'incident', 'facts', 'root', 'ai', 'health', 'anomaly', 'weather', 'params', 'verify']


def resolve_sections(cfg=None, mode='long'):
    """cfg: [[anahtar, açık], …] (Ayarlar > Rapor şablon düzenleyici). Kısa modda yalnızca SHORT bölümleri."""
    order = [k for k, _ in (cfg or [])] if cfg else list(SECTIONS)
    order += [k for k in SECTIONS if k not in order]
    on = {k: v for k, v in (cfg or [])} if cfg else {k: True for k in SECTIONS}
    out = [k for k in order if k in SECTIONS and on.get(k, True)]
    if mode == 'short': out = [k for k in out if k in SHORT]
    return out


class ReportData:
    """Rapor için hazırlanmış, dile göre çevrilmiş içerik."""
    def __init__(self, A: Analysis, lang='tr', ai_text=None, online_map=True, map_src='osm', charts_on=None, sections=None, mode='long'):
        self.A = A; self.lang = lang; self.ai_text = ai_text
        self.mode = mode
        if sections and isinstance(sections[0], (list, tuple)): sections = resolve_sections(sections, mode)   # şablon düzenleyici biçimi
        elif sections and mode == 'short': sections = [k for k in sections if k in SHORT]
        self.sections = sections or resolve_sections(None, mode)
        self.id = time.strftime('%Y%m%d') + '-' + uuid.uuid4().hex[:8].upper()
        self.generated = time.strftime('%Y-%m-%d %H:%M')
        L = A.L
        u = L.unix_at(A.flights[0][0] if A.flights else 0)
        self.flight_date = time.strftime('%Y-%m-%d %H:%M', time.localtime(u)) if u else '-'
        self.imgs = []
        if 'charts' in self.sections:
            for key, fn in charts.ALL:
                if charts_on and key not in charts_on: continue
                try:
                    b = fn(A, lang)
                except Exception:
                    b = None
                if b: self.imgs.append((key, b))
        self.map = None
        if 'charts' in self.sections:
            try: self.map = charts.chart_map(A, lang, online=online_map, src=map_src)
            except Exception: pass
        self.health_img = charts.chart_health(A, lang) if mode == 'long' else None
        self.timeline_img = charts.chart_timeline(A, lang) if 'timeline' in self.sections else None
        if 'weather' in self.sections and getattr(A, 'weather', None) is None and online_map:
            try:
                from . import weather
                weather.for_analysis(A)
            except Exception:
                pass
        self.pilot_img = None
        if 'pilot' in self.sections and (getattr(A, 'pilot', None) or {}).get('scores'):
            try:
                from .fleet import radar_png
                self.pilot_img = radar_png(A.pilot['scores'], lang)
            except Exception:
                pass
        self.aircraft_name = ''; self.pilot_name = ''

    def t(self, key, **a):
        return texts.T(key, self.lang, **a)

    def incident(self):
        """Resmî olay raporu içeriği (yalnız kaza ya da ciddi sorunlu uçuşta): [(başlık, [satırlar] | tablo)]."""
        A = self.A; lg = self.lang; v = A.verdict.get('kind')
        if v not in ('crash', 'incident') or (v == 'incident' and A.verdict.get('severity') == 'minor'): return None
        y = why_mod.render(A, lg, fmt_t) or {}
        f = A.facts; tr = A.track
        place = f"{tr['lat'][-1]:.6f}, {tr['lon'][-1]:.6f}" if tr is not None and len(tr['lat']) else '-'
        info = getattr(A, 'info', {}) or {}
        cls = texts.T('v_' + texts.vkey(A.verdict), lg)
        b1 = [(R('inc_class', lg), cls), (R('f_vehicle', lg), f"{A.vehicle} · {A.L.version or '-'}"),
              (R('inc_serial', lg), getattr(A, 'serial', '') or '-'), (R('f_date', lg), self.flight_date),
              (R('inc_time', lg), fmt_t(why_mod._end_t(A))), (R('inc_place', lg), place),
              (R('inc_operator', lg), info.get('pilot') or ''), (R('report_id', lg), self.id)]
        b2 = [y['sentence']] if y else [texts.T('v_desc_' + texts.vkey(A.verdict), lg)]
        b3 = [[fmt_t(s_['t']), texts.chain_step(s_, lg, fmt_t)] for s_ in (A.root or {}).get('chain', [])]
        b4 = [texts.render(e, lg, fmt_t) for e in A.verdict.get('evidence', []) if e.get('k') != 'cr_landed']
        if y: b4 += [e for e in y.get('evidence', []) if e not in b4]
        b5 = list(y.get('notes', [])) if y else []
        oth = (A.root or {}).get('others') or []
        if oth: b5.append(R('root_others', lg) + ': ' + ', '.join(self.t('cause_' + o) for o in oth))
        try:
            from . import baseline
            bh, bl = baseline.render(A, lg)
            if bl: b5.append(R('inc_baseline', lg) + ': ' + '; '.join(bl))
        except Exception:
            pass
        ph = getattr(A, 'physics', None) or {}
        if ph.get('tw'): b5.append(f"{R('inc_physics', lg)}: T/W ≈ {ph['tw']}, hover {round(ph['hover_thr'] * 100)}%" +
                                   (f", {ph['hover_w']} W" if ph.get('hover_w') else ''))
        c = (A.root or {}).get('cause')
        b6 = [y['prevent']] if y and y.get('prevent') else ([self.t('prevent_' + c)] if c else [])
        b7 = [y['conf_text']] if y else []
        gaps = list(getattr(A, 'gaps', []) or [])
        if gaps:
            try:
                b7.append(R('inc_gaps', lg) + ': ' + why_mod._na({'g': gaps}, lg)['g'])
            except Exception:
                b7.append(R('inc_gaps', lg) + ': ' + ', '.join(gaps))
        b7.append(R('inc_limits', lg))
        sign = [[R(k, lg), '', '', ''] for k in ('inc_prepared', 'inc_reviewed', 'inc_approved')]
        return {'b1': b1, 'b2': b2, 'b3': b3, 'b4': b4, 'b5': b5, 'b6': b6, 'b7': b7, 'sign': sign,
                'sign_h': ['', R('inc_name', lg), R('inc_sign', lg), R('inc_date', lg)]}

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
        from . import profiles
        rows.insert(2, (R('f_profile', lg), profiles.name(getattr(A, 'profile', 'plane'), lg)))
        if getattr(A, 'serial', ''): rows.append((R('f_serial', lg), A.serial))
        if getattr(self, 'aircraft_name', ''): rows.append((R('f_aircraft', lg), self.aircraft_name))
        if getattr(self, 'pilot_name', ''): rows.append((R('f_pilot', lg), self.pilot_name))
        try:
            from . import flightinfo as FI
            rows += [(a, b) for a, b in FI.rows(getattr(A, 'info', {}) or {}, lg)]
        except Exception:
            pass
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
    top_cm, bot_cm, _bg = LHM.margins(lh)
    sec.left_margin = sec.right_margin = Cm(1.8); sec.top_margin = Cm(top_cm or 3.0); sec.bottom_margin = Cm(max(bot_cm or 0, 2.0))
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
    _letterhead_docx(doc, sec, lh, rd, rtl, para, set_rtl, run_rtl)

    # ---- Besmele: yalnızca ilk sayfanın başında (gövdede olduğu için sonraki sayfalarda görünmez)
    if lh.get('besmele') and os.path.exists(LHM.besmele_path()):
        bp = doc.add_paragraph(); bp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        bp.paragraph_format.space_before = Pt(0); bp.paragraph_format.space_after = Pt(6)
        bp.add_run().add_picture(LHM.besmele_path(), width=Cm(6.5))

    para(R('title', lg), bold=True, size=20, col=lh['color'].lstrip('#').upper(), align=WD_ALIGN_PARAGRAPH.CENTER, space=0)
    para(f"{R('subtitle', lg)} · {os.path.basename(A.L.path)}", size=9, col='6B7280', align=WD_ALIGN_PARAGRAPH.CENTER, space=10)
    v = texts.vkey(A.verdict)
    long_ = rd.mode != 'short'

    def s_summary():
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
        if A.health:
            items = list(A.health.items())
            rows = [['● ' + rd.t('dom_' + k), str(h['score']), rd.t('st_' + h['status'])] for k, h in items]
            cols = [[None, None, {'good': 'DCFCE7', 'warn': 'FEF3C7', 'bad': 'FEE2E2'}[h['status']]] for _, h in items]
            heading(R('summary', lg), 2)
            table(rows, [R('h_area', lg), R('h_score', lg), R('h_status', lg)], [8, 3, 4], cols)

    def s_incident():
        d = rd.incident()
        if not d: return
        heading(R('inc_title', lg))
        heading(R('inc_1', lg), 2); table([list(r) for r in d['b1']], None, [6, 11])
        heading(R('inc_2', lg), 2)
        for x in d['b2']: para(x, bold=True, size=11)
        if d['b3']:
            heading(R('inc_3', lg), 2); table(d['b3'], [R('e_time', lg), R('e_text', lg)], [3, 14])
        for key, items in (('inc_4', d['b4']), ('inc_5', d['b5']), ('inc_6', d['b6']), ('inc_7', d['b7'])):
            if not items: continue
            heading(R(key, lg), 2)
            for x in items: para('• ' + x, size=9.5, space=2)
        heading(R('inc_8', lg), 2); table(d['sign'], d['sign_h'], [4, 5, 4, 4])

    def s_facts():
        heading(R('facts', lg), 2)
        table([list(r) for r in rd.facts_rows()], None, [6, 11])
        if v == 'crash' or A.verdict.get('evidence'):
            heading(R('evidence', lg), 2)
            for e in A.verdict.get('evidence', []):
                para('• ' + texts.render(e, lg, fmt_t), size=9.5, space=2)

    def s_root():
        if not A.root: return
        y = why_mod.render(A, lg, fmt_t)
        if y:
            heading(y['title'])
            para(y['sentence'], bold=True, size=12.5, col='DC2626' if v == 'crash' else 'D97706')
            para(y['conf_text'], bold=True, size=10, col='1D4ED8')
            if y['why']: para(y['why'], size=10)
            if y['chain']: para(y['chain_h'] + ': ' + y['chain'], size=9.5, italic=True)
            if y['evidence']:
                heading(y['evid_h'], 2)
                for e in y['evidence']: para('• ' + e, size=9.5, space=2)
            if y.get('weather'): para(y['weather'], size=9.5)
            if y['notes']:
                heading(y['ctx_h'], 2)
                for n in y['notes']: para('• ' + n, size=9.5, space=2)
        heading(R('root', lg))
        c = A.root['cause']
        para(f"{R('root_cause', lg)}: {rd.t('cause_' + c)}  ({fmt_t(A.root.get('t', 0))})", bold=True, size=11.5, col='DC2626' if v == 'crash' else 'D97706')
        heading(R('root_what', lg), 2); para(rd.t('why_' + c))
        heading(R('root_chain', lg), 2)
        rows = [[fmt_t(s_['t']), texts.chain_step(s_, lg, fmt_t)] for s_ in A.root.get('chain', [])]
        if rows: table(rows, [R('e_time', lg), R('e_text', lg)], [3, 14])
        heading(R('root_prev', lg), 2); para(rd.t('prevent_' + c))
        oth = A.root.get('others') or []
        if oth: para(R('root_others', lg) + ': ' + ', '.join(rd.t('cause_' + o) for o in oth), italic=True, size=9.5)

    def s_ai():
        if not rd.ai_text: return
        heading(R('ai', lg)); para(R('ai_note', lg), italic=True, size=8.5, col='6B7280')
        for line in rd.ai_text.splitlines():
            s_ = _strip_md(line).strip()
            if not s_: continue
            if s_.startswith('#'): para(s_.lstrip('# '), bold=True, size=11)
            else: para(s_, size=9.5, space=3)

    def s_health():
        heading(R('health', lg))
        if rd.health_img and long_: image(rd.health_img, 15)
        rows = []; cols = []
        for k, h in A.health.items():
            fnd = '\n'.join('• ' + texts.render(f, lg) for f in h['findings']) or R('no_find', lg)
            rows.append([rd.t('dom_' + k), str(h['score']), fnd]); cols.append([None, {'good': 'DCFCE7', 'warn': 'FEF3C7', 'bad': 'FEE2E2'}[h['status']], None])
        if rows: table(rows, [R('h_area', lg), R('h_score', lg), R('h_find', lg)], [4, 2, 11], cols)

    def s_anomaly():
        info_ = getattr(A, 'anomaly_info', None)
        if not info_: return
        heading(R('anomaly', lg))
        para(R('anom_intro', lg).format(n=info_['windows'], k=info_['learned_flights'], i=info_['index']), size=9.5)
        rows = anomaly_rows(A, lg)
        if rows: table(rows, [R('a_time', lg), R('a_score', lg), R('a_feats', lg)], [3.4, 1.8, 11.8])
        else: para(R('anom_none', lg), italic=True, size=9.5)

    def s_pilot():
        pl = A.pilot or {}
        if not pl.get('scores'): return
        heading(R('pilot', lg)); para(R('pilot_note', lg), italic=True, size=8.5, col='6B7280')
        if rd.pilot_img: image(rd.pilot_img, 8.5)
        from .fleet import sname
        table([[sname(k, lg), str(v_)] for k, v_ in pl['scores'].items()] + [[R('overall', lg), str(pl.get('overall'))]], None, [8, 3])

    def s_weather():
        from . import weather as W_
        heading(R('weather', lg))
        table([[a_, b_] for a_, b_ in W_.rows(A, lg)], None, [6, 11])

    def s_phases():
        if not A.phases: return
        heading(R('phases', lg))
        rows = []
        f1 = lambda x, u='': f'{x:.0f}{u}' if isinstance(x, (int, float)) else '-'
        for p_ in A.phases:
            s_ = p_.get('stats', {})
            rows.append([rd.t('ph_' + p_['name']), f"{fmt_t(p_['t0'])}–{fmt_t(p_['t1'])}", fmt_t(s_.get('dur', 0)),
                         f"{f1(s_.get('alt_mean'))}/{f1(s_.get('alt_max'))} m", f1(s_.get('as_mean') if s_.get('as_mean') is not None else s_.get('gs_mean'), ' m/s'),
                         f1(s_.get('thr_mean'), '%'), f"{f1(s_.get('roll_max'))}°/{f1(s_.get('pitch_max'))}°"])
        table(rows, [R(k, lg) for k in ('p_phase', 'p_time', 'p_dur', 'p_alt', 'p_spd', 'p_thr', 'p_att')], [2.4, 3.4, 1.8, 2.6, 2.2, 2, 2.6])

    def s_charts():
        heading(R('charts', lg))
        if rd.map:
            image(rd.map, 16)
            if long_: _lesson_docx(rd, 'c_map', para, table, heading, lg)
        for key, b_ in rd.imgs:
            image(b_)
            if long_: _lesson_docx(rd, key, para, table, heading, lg)

    def s_timeline():
        heading(R('timeline', lg))
        if rd.timeline_img: image(rd.timeline_img)
        ev = [e for e in A.events if e['sev'] > 0 or e['cat'] in ('mode', 'flight')][:150]
        rows = [[fmt_t(e['t']), R('cat_' + e['cat'], lg), texts.render(e['text'], lg)] for e in ev]
        cols = [[None, None, {0: None, 1: 'FEF3C7', 2: 'FEE2E2'}[e['sev']]] for e in ev]
        if rows: table(rows, [R('e_time', lg), R('e_type', lg), R('e_text', lg)], [2.6, 2.4, 12], cols)

    def s_params():
        heading(R('params', lg))
        rows = [[R('sev' + str(f['sev']), lg), texts.render(f['text'], lg)] for f in A.param_findings]
        cols = [[{0: 'DBEAFE', 1: 'FEF3C7', 2: 'FEE2E2'}[f['sev']], None] for f in A.param_findings]
        table(rows, None, [2.6, 14.4], cols)

    def s_thresholds():
        heading(R('thresholds', lg))
        rows = []
        for key in ('c_gps', 'c_vibe', 'c_bat', 'c_ekf', 'c_att', 'c_mag'):
            Ls = LESSON[key]; i = ('tr', 'en', 'ar').index(lg)
            rows.append([R(key, lg), Ls['normal'][i], Ls['warn'][i], Ls['danger'][i]])
        table(rows, ['', R('th_normal', lg), R('th_warn', lg), R('th_danger', lg)], [3.2, 4.6, 4.6, 4.6],
              [[None, 'DCFCE7', 'FEF3C7', 'FEE2E2'] for _ in rows])
        para(R('offline_note', lg) if not rd.ai_text else R('ai_note', lg), italic=True, size=8, col='6B7280')

    def s_verify():
        heading(R('verify', lg), 2)
        tb = doc.add_table(rows=1, cols=2)
        c0, c1 = tb.rows[0].cells; c0.width = Cm(4); c1.width = Cm(13)
        c0.paragraphs[0].add_run().add_picture(io.BytesIO(rd.qr_png()), width=Cm(3.2))
        p = c1.paragraphs[0]; set_rtl(p); r = p.add_run(f"{R('report_id', lg)}: {rd.id}\n{R('generated', lg)}: {rd.generated}\n\n{R('verify_txt', lg)}"); r.font.size = Pt(9); run_rtl(r)

    fns = {k: f for k, f in locals().items() if k.startswith('s_')}
    for k in rd.sections:
        fn = fns.get('s_' + k)
        if fn:
            try: fn()
            except Exception:
                import traceback; traceback.print_exc()
    doc.save(path)
    return path


def anomaly_rows(A, lg):
    from .anomaly import fname
    rows = []
    for it in (getattr(A, 'anomalies', None) or [])[:8]:
        parts = []
        for f in it['feats']:
            val = '-' if f['v'] is None else f"{f['v']:.2f}"
            parts.append(f"{fname(f['k'], lg)}: {val} / {f['exp']:.2f} (z={f['z']})")
        rows.append([f"{fmt_t(it['t0'])}–{fmt_t(it['t1'])}", f"{it['score']:.1f}", '; '.join(parts)])
    return rows


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
    bg = LHM.resolve(lh.get('bg') or '')
    if bg:
        with open(LHM.prepared_bg(bg), 'rb') as f:
            add_anchor(f.read(), 'letterhead')
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


def pdf_kit(lg, lh=None, rid='', footer_extra=''):
    """Antetli PDF yapı taşları (rapor, pilot kartı, sertifika aynı görünümü paylaşır)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.lib.utils import ImageReader
    from xml.sax.saxutils import escape
    _fonts()
    lh = {**DEFAULT_LH, **(lh or {})}
    rtl = lg == 'ar'
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

    top_cm, bot_cm, bg_src = LHM.margins(lh)
    bg_img = LHM.prepared_bg(bg_src) if bg_src else None

    class _RD:  # _wm_png yalnızca dil bilgisini kullanır
        lang = lg
    wm = None if bg_img else _wm_png(lh, _RD)
    wm_bytes = None
    if wm:
        b = io.BytesIO(); wm.save(b, format='PNG'); wm_bytes = b.getvalue()

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
        ft = (lh.get('footer') + ' · ' if lh.get('footer') else '') + (f"{R('report_id', lg)}: {rid}" if rid else footer_extra) + \
            (f" · {R('prepared_by', lg)}: {lh['prepared_by']}" if lh.get('prepared_by') else '') + f" · {d.page}"
        fy = 0.75 * cm if not (bg_img and bot_cm and bot_cm > 1.7) else (bot_cm - 0.75) * cm
        c.drawCentredString(Wp / 2, fy, charts.shape(ft, lg))
        c.restoreState()

    def build(path, story, title, encrypt=None):
        kw = {}
        if encrypt:
            from reportlab.lib import pdfencrypt
            kw['encrypt'] = pdfencrypt.StandardEncryption(encrypt, ownerPassword=encrypt + '#owner', canPrint=1, canModify=0, canCopy=1, strength=128)
        doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=(top_cm if bg_img else 2.9) * cm,
                                bottomMargin=(bot_cm if bg_img else 1.6) * cm, title=title, author=lh.get('prepared_by') or lh.get('org') or 'Pixhawk Log Analiz',
                                subject=rid or title, **kw)
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        return path

    def besmele():
        if lh.get('besmele') and os.path.exists(LHM.besmele_path()):
            from PIL import Image as _PI
            from reportlab.platypus import Spacer
            bw_, bh_ = _PI.open(LHM.besmele_path()).size
            bi = Image(LHM.besmele_path(), width=6.5 * cm, height=6.5 * cm * bh_ / bw_); bi.hAlign = 'CENTER'
            return [bi, Spacer(1, 6)]
        return []

    return dict(P=P, tbl=tbl, img=img, base=base, small=small, H1=H1, H2=H2, TT=TT, W=W_, main=main, rtl=rtl, build=build,
                besmele=besmele, colors=colors, cm=cm, lh=lh)


def build_pdf(rd: ReportData, path, lh=None, encrypt=None):
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
    lg = rd.lang; A = rd.A
    K_ = pdf_kit(lg, lh, rd.id)
    P, tbl, img, base, small, H1, H2, TT, W_, rtl = (K_[k] for k in ('P', 'tbl', 'img', 'base', 'small', 'H1', 'H2', 'TT', 'W', 'rtl'))
    long_ = rd.mode != 'short'
    story = K_['besmele']()
    story += [P(R('title', lg), TT), Spacer(1, 2), P(f"{R('subtitle', lg)} · {os.path.basename(A.L.path)}", ParagraphStyle('c', parent=small, alignment=TA_CENTER, textColor=colors.HexColor('#6B7280'))), Spacer(1, 8)]
    v = texts.vkey(A.verdict)

    def s_summary():
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
        story.extend([card, Spacer(1, 8)])
        if A.health:
            story.append(P(R('summary', lg), H2))
            items = list(A.health.items())
            story.append(tbl([[rd.t('dom_' + k), str(h['score']), rd.t('st_' + h['status'])] for k, h in items], [R('h_area', lg), R('h_score', lg), R('h_status', lg)],
                             [9 * cm, 3 * cm, W_ - 12 * cm], [[None, None, {'good': 'DCFCE7', 'warn': 'FEF3C7', 'bad': 'FEE2E2'}[h['status']]] for _, h in items]))

    def s_incident():
        d = rd.incident()
        if not d: return
        if long_: story.append(PageBreak())
        story.append(P(R('inc_title', lg), H1))
        story.extend([P(R('inc_1', lg), H2), tbl([list(r) for r in d['b1']], None, [5.5 * cm, W_ - 5.5 * cm])])
        story.append(P(R('inc_2', lg), H2))
        for x in d['b2']: story.append(P(x, ParagraphStyle('b2', parent=base, fontName='DJB')))
        if d['b3']:
            story.extend([P(R('inc_3', lg), H2), tbl(d['b3'], [R('e_time', lg), R('e_text', lg)], [3 * cm, W_ - 3 * cm])])
        for key, items in (('inc_4', d['b4']), ('inc_5', d['b5']), ('inc_6', d['b6']), ('inc_7', d['b7'])):
            if not items: continue
            story.append(P(R(key, lg), H2))
            for x in items: story.append(P('• ' + x))
        story.append(P(R('inc_8', lg), H2))
        sg = [list(r) for r in d['sign']]
        story.append(tbl(sg, d['sign_h'], [3.5 * cm] + [(W_ - 3.5 * cm) / 3] * 3, fs=9))

    def s_facts():
        story.append(P(R('facts', lg), H2))
        story.append(tbl([list(r) for r in rd.facts_rows()], None, [5.5 * cm, W_ - 5.5 * cm]))
        if A.verdict.get('evidence'):
            story.append(P(R('evidence', lg), H2))
            for e in A.verdict['evidence']: story.append(P('• ' + texts.render(e, lg, fmt_t)))

    def s_root():
        if not A.root: return
        if long_: story.append(PageBreak())
        y = why_mod.render(A, lg, fmt_t)
        if y:
            story.append(P(y['title'], H1))
            story.append(P(y['sentence'], ParagraphStyle('ws', parent=H2, textColor=colors.HexColor('#DC2626' if v == 'crash' else '#D97706'))))
            story.append(P('<b>' + y['conf_text'] + '</b>'))
            if y['why']: story.append(P(y['why']))
            if y['chain']: story.append(P('<i>' + y['chain_h'] + ': ' + y['chain'] + '</i>', small))
            if y['evidence']:
                story.append(P(y['evid_h'], H2))
                for e in y['evidence']: story.append(P('• ' + e))
            if y.get('weather'): story.append(P(y['weather'], small))
            if y['notes']:
                story.append(P(y['ctx_h'], H2))
                for n in y['notes']: story.append(P('• ' + n))
        story.append(P(R('root', lg), H1))
        c = A.root['cause']
        story.append(P(f"{R('root_cause', lg)}: {rd.t('cause_' + c)} ({fmt_t(A.root.get('t', 0))})", ParagraphStyle('rc', parent=H2, textColor=colors.HexColor('#DC2626' if v == 'crash' else '#D97706'))))
        story.extend([P(R('root_what', lg), H2), P(rd.t('why_' + c)), P(R('root_chain', lg), H2)])
        rows = [[fmt_t(s_['t']), texts.chain_step(s_, lg, fmt_t)] for s_ in A.root.get('chain', [])]
        if rows: story.append(tbl(rows, [R('e_time', lg), R('e_text', lg)], [3 * cm, W_ - 3 * cm]))
        story.extend([P(R('root_prev', lg), H2), P(rd.t('prevent_' + c))])
        if A.root.get('others'): story.append(P(R('root_others', lg) + ': ' + ', '.join(rd.t('cause_' + o) for o in A.root['others']), small))

    def s_ai():
        if not rd.ai_text: return
        story.extend([P(R('ai', lg), H1), P(R('ai_note', lg), small), Spacer(1, 4)])
        for line in rd.ai_text.splitlines():
            s_ = _strip_md(line).strip()
            if s_: story.append(P(s_.lstrip('# '), H2 if s_.startswith('#') else base))

    def s_health():
        if long_: story.append(PageBreak())
        story.append(P(R('health', lg), H1))
        if rd.health_img and long_: story.append(img(rd.health_img, W_ * 0.85))
        rows = []; bgs = []
        for k, h in A.health.items():
            rows.append([rd.t('dom_' + k), str(h['score']), '\n'.join('• ' + texts.render(f, lg) for f in h['findings']) or R('no_find', lg)])
            bgs.append([None, {'good': 'DCFCE7', 'warn': 'FEF3C7', 'bad': 'FEE2E2'}[h['status']], None])
        if rows: story.append(tbl(rows, [R('h_area', lg), R('h_score', lg), R('h_find', lg)], [4 * cm, 1.8 * cm, W_ - 5.8 * cm], bgs))

    def s_anomaly():
        info_ = getattr(A, 'anomaly_info', None)
        if not info_: return
        story.append(P(R('anomaly', lg), H1))
        story.append(P(R('anom_intro', lg).format(n=info_['windows'], k=info_['learned_flights'], i=info_['index'])))
        rows = anomaly_rows(A, lg)
        if rows: story.append(tbl(rows, [R('a_time', lg), R('a_score', lg), R('a_feats', lg)], [3.2 * cm, 1.6 * cm, W_ - 4.8 * cm], fs=7.6))
        else: story.append(P(R('anom_none', lg), small))

    def s_pilot():
        pl = A.pilot or {}
        if not pl.get('scores'): return
        from .fleet import sname
        story.extend([P(R('pilot', lg), H1), P(R('pilot_note', lg), small)])
        t_ = tbl([[sname(k, lg), str(v_)] for k, v_ in pl['scores'].items()] + [[R('overall', lg), str(pl.get('overall'))]], None, [5.5 * cm, 2 * cm])
        if rd.pilot_img:
            im = img(rd.pilot_img, 7.5 * cm)
            row = [t_, im] if not rtl else [im, t_]
            tt = Table([row], colWidths=[8 * cm, W_ - 8 * cm] if not rtl else [W_ - 8 * cm, 8 * cm]); tt.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
            story.append(tt)
        else:
            story.append(t_)

    def s_weather():
        from . import weather as W
        story.append(P(R('weather', lg), H1))
        story.append(tbl([[a_, b_] for a_, b_ in W.rows(A, lg)], None, [5.5 * cm, W_ - 5.5 * cm]))

    def s_phases():
        if not A.phases: return
        story.append(P(R('phases', lg), H1))
        f1 = lambda x, u='': f'{x:.0f}{u}' if isinstance(x, (int, float)) else '-'
        rows = [[rd.t('ph_' + p_['name']), f"{fmt_t(p_['t0'])}–{fmt_t(p_['t1'])}", fmt_t(p_['stats'].get('dur', 0)),
                 f"{f1(p_['stats'].get('alt_mean'))}/{f1(p_['stats'].get('alt_max'))} m", f1(p_['stats'].get('as_mean') if p_['stats'].get('as_mean') is not None else p_['stats'].get('gs_mean'), ' m/s'),
                 f1(p_['stats'].get('thr_mean'), '%'), f"{f1(p_['stats'].get('roll_max'))}°/{f1(p_['stats'].get('pitch_max'))}°"] for p_ in A.phases]
        story.append(tbl(rows, [R(k, lg) for k in ('p_phase', 'p_time', 'p_dur', 'p_alt', 'p_spd', 'p_thr', 'p_att')], [2.2 * cm, 3.4 * cm, 1.8 * cm, 2.5 * cm, 2.2 * cm, 2 * cm, W_ - 14.1 * cm], fs=7.5))

    def lesson(key):
        Ls = LESSON.get(key)
        if not Ls or not long_: return []
        i = ('tr', 'en', 'ar').index(lg)
        return [P('ⓘ ' + R('why_see', lg) + ' ' + Ls['what'][i], ParagraphStyle('l', parent=small, textColor=colors.HexColor('#1F2937'))),
                tbl([[Ls['normal'][i], Ls['warn'][i], Ls['danger'][i]]], [R('th_normal', lg), R('th_warn', lg), R('th_danger', lg)], [W_ / 3] * 3, [['DCFCE7', 'FEF3C7', 'FEE2E2']], fs=7.2), Spacer(1, 8)]

    def s_charts():
        story.extend([PageBreak(), P(R('charts', lg), H1)])
        if rd.map: story.append(KeepTogether([img(rd.map, W_ * 0.9)] + lesson('c_map')))
        for key, b in rd.imgs: story.append(KeepTogether([img(b)] + lesson(key)))

    def s_timeline():
        story.extend([PageBreak(), P(R('timeline', lg), H1)])
        if rd.timeline_img: story.append(img(rd.timeline_img))
        ev = [e for e in A.events if e['sev'] > 0 or e['cat'] in ('mode', 'flight')][:150]
        if ev:
            story.append(tbl([[fmt_t(e['t']), R('cat_' + e['cat'], lg), texts.render(e['text'], lg)] for e in ev], [R('e_time', lg), R('e_type', lg), R('e_text', lg)],
                             [2.4 * cm, 2.2 * cm, W_ - 4.6 * cm], [[None, None, {0: None, 1: 'FEF3C7', 2: 'FEE2E2'}[e['sev']]] for e in ev], fs=7.5))

    def s_params():
        story.append(P(R('params', lg), H1))
        story.append(tbl([[R('sev' + str(f['sev']), lg), texts.render(f['text'], lg)] for f in A.param_findings], None, [2.4 * cm, W_ - 2.4 * cm],
                         [[{0: 'DBEAFE', 1: 'FEF3C7', 2: 'FEE2E2'}[f['sev']], None] for f in A.param_findings]))

    def s_thresholds():
        story.append(P(R('thresholds', lg), H1))
        i = ('tr', 'en', 'ar').index(lg)
        rows = [[R(k, lg), LESSON[k]['normal'][i], LESSON[k]['warn'][i], LESSON[k]['danger'][i]] for k in ('c_gps', 'c_vibe', 'c_bat', 'c_ekf', 'c_att', 'c_mag')]
        story.append(tbl(rows, ['', R('th_normal', lg), R('th_warn', lg), R('th_danger', lg)], [3 * cm] + [(W_ - 3 * cm) / 3] * 3, [[None, 'DCFCE7', 'FEF3C7', 'FEE2E2'] for _ in rows], fs=7.2))
        story.append(P(R('offline_note', lg) if not rd.ai_text else R('ai_note', lg), small))

    def s_verify():
        qr = Image(io.BytesIO(rd.qr_png()), width=3 * cm, height=3 * cm)
        vt = [P(f"{R('report_id', lg)}: {rd.id}", H2, W_ - 4 * cm), P(f"{R('generated', lg)}: {rd.generated}", base, W_ - 4 * cm), P(R('verify_txt', lg), small, W_ - 4 * cm)]
        vr = [qr, vt] if not rtl else [vt, qr]
        t = Table([vr], colWidths=[3.6 * cm, W_ - 3.6 * cm] if not rtl else [W_ - 3.6 * cm, 3.6 * cm]); t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        story.extend([Spacer(1, 8), P(R('verify', lg), H2), t])

    fns = {k: f for k, f in locals().items() if k.startswith('s_')}
    for k in rd.sections:
        fn = fns.get('s_' + k)
        if fn:
            try: fn()
            except Exception:
                import traceback; traceback.print_exc()
    return K_['build'](path, story, R('title', lg), encrypt=encrypt)


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 20), b''): h.update(ch)
    return h.hexdigest()


def sample_pdf(path, lh=None, lang='tr'):
    """Antet önizlemesi için sentetik bir uçuştan gerçek örnek PDF rapor üretir."""
    import tempfile
    from . import synth, loader
    from .analysis import Analysis
    d = tempfile.mkdtemp(prefix='lh_prev_'); p = os.path.join(d, 'ornek.BIN')
    synth.generate(p, 'normal')
    rd = ReportData(Analysis(loader.load(p)), lang if lang in ('tr', 'en', 'ar') else 'tr', None, online_map=False)
    build_pdf(rd, path, lh)
    return path
