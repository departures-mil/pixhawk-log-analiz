"""Analiz özetini arayüz için HTML'e dönüştürür (QTextBrowser)."""
from __future__ import annotations
import html, os
from ..core import texts
from ..core.analysis import fmt_t
from ..core.report import R, ReportData
from .common import VERDICT_COL, STATUS_COL

E = html.escape


def _facts(A, lg):
    rd = ReportData.__new__(ReportData)  # yalnızca facts_rows için hafif nesne
    rd.A = A; rd.lang = lg
    u = A.L.unix_at(A.flights[0][0] if A.flights else 0)
    import time
    rd.flight_date = time.strftime('%Y-%m-%d %H:%M', time.localtime(u)) if u else '-'
    return ReportData.facts_rows(rd)


def build(A, lg):
    d = 'rtl' if lg == 'ar' else 'ltr'
    al = 'right' if lg == 'ar' else 'left'
    v = A.verdict.get('kind', 'normal'); vc = VERDICT_COL.get(v, '#64748B')
    sc = A.overall; scc = STATUS_COL['good' if sc >= 80 else ('warn' if sc >= 55 else 'bad')]
    h = [f'<div dir="{d}" style="text-align:{al}">']
    h.append(f'<table width="100%" cellpadding="12" cellspacing="0"><tr>'
             f'<td bgcolor="{vc}" width="75%"><span style="font-size:17pt;font-weight:700;color:white">{E(R("verdict", lg))}: {E(texts.T("v_" + v, lg))}</span><br>'
             f'<span style="color:white">{E(texts.T("v_desc_" + v, lg))}</span></td>'
             f'<td bgcolor="#111C33" align="center"><span style="font-size:28pt;font-weight:800;color:{scc}">{sc}</span><br><span style="color:#94A3B8">/100 · {E(R("overall", lg))}</span></td></tr></table>')
    # Neden düştü? (net hüküm)
    try:
        from ..core import why
        y = why.render(A, lg, fmt_t)
    except Exception:
        y = {}
    if y:
        col = '#F87171' if v == 'crash' else '#FBBF24'
        h.append(f'<table width="100%" cellpadding="10" cellspacing="0"><tr><td bgcolor="#1E1B2E">'
                 f'<span style="font-size:14pt;font-weight:700;color:{col}">❓ {E(y["title"])}</span><br>'
                 f'<span style="font-size:12pt;color:#F8FAFC"><b>{E(y["sentence"])}</b></span><br>'
                 f'<span style="color:#93C5FD"><b>{E(y["conf_text"])}</b></span>')
        if y['why']: h.append(f'<br><span style="color:#CBD5E1">{E(y["why"])}</span>')
        if y['chain']: h.append(f'<br><span style="color:#94A3B8"><i>{E(y["chain_h"])}: {E(y["chain"])}</i></span>')
        if y['evidence']:
            h.append(f'<br><b style="color:#93C5FD">{E(y["evid_h"])}</b><ul>' + ''.join(f'<li>{E(e)}</li>' for e in y['evidence']) + '</ul>')
        if y.get('weather'): h.append(f'<span style="color:#A5B4FC">🌦 {E(y["weather"])}</span><br>')
        if y['notes']:
            h.append(f'<b style="color:#FBBF24">{E(y["ctx_h"])}</b><ul>' + ''.join(f'<li>{E(n)}</li>' for n in y['notes']) + '</ul>')
        if y['prevent']: h.append(f'<b style="color:#86EFAC">{E(y["todo_h"])}</b><br>{E(y["prevent"])}')
        h.append('<br><a href="ai:why" style="color:#60A5FA">🤖 ' + E(R('why_ai', lg)) + '</a> &nbsp; '
                 '<a href="go:solver" style="color:#60A5FA">🩺 ' + E(R('why_solver', lg)) + '</a> &nbsp; '
                 '<a href="fb:why" style="color:#86EFAC">' + E(_fbt(lg)) + '</a>')
        h.append('</td></tr></table>')
    else:
        h.append('<p><a href="fb:why" style="color:#86EFAC">' + E(_fbt(lg)) + '</a></p>')
    # Sağlık
    h.append(f'<h3 style="color:#93C5FD">{E(R("summary", lg))}</h3><table width="100%" cellpadding="5" cellspacing="2">')
    for k, x in A.health.items():
        c = STATUS_COL[x['status']]
        w = max(2, int(x['score']))
        h.append(f'<tr><td width="28%">{E(texts.T("dom_" + k, lg))}</td><td width="8%" align="center"><b style="color:{c}">{x["score"]}</b></td>'
                 f'<td><table width="{w}%" cellspacing="0" cellpadding="0"><tr><td bgcolor="{c}" height="10"></td></tr></table></td>'
                 f'<td width="14%" style="color:{c}">{E(texts.T("st_" + x["status"], lg))}</td></tr>')
    h.append('</table>')
    # Temel bilgiler
    h.append(f'<h3 style="color:#93C5FD">{E(R("facts", lg))}</h3><table width="100%" cellpadding="4" cellspacing="0" border="0">')
    for i, (a, b) in enumerate(_facts(A, lg)):
        bg = '#111C33' if i % 2 else '#0F1A30'
        h.append(f'<tr bgcolor="{bg}"><td width="35%" style="color:#94A3B8">{E(a)}</td><td>{E(chr(0x2066) + str(b) + chr(0x2069)) if lg == "ar" else E(str(b))}</td></tr>')
    h.append('</table>')
    if A.verdict.get('evidence'):
        h.append(f'<h3 style="color:#93C5FD">{E(R("evidence", lg))}</h3><ul>')
        for e in A.verdict['evidence']: h.append(f'<li>{E(texts.render(e, lg, fmt_t))}</li>')
        h.append('</ul>')
    if A.root:
        c = A.root['cause']
        col = '#F87171' if v == 'crash' else '#FBBF24'
        h.append(f'<h3 style="color:{col}">{E(R("root_cause", lg))}: {E(texts.T("cause_" + c, lg))} ({fmt_t(A.root.get("t", 0))})</h3>')
        h.append(f'<p><b>{E(R("root_what", lg))}</b><br>{E(texts.T("why_" + c, lg))}</p>')
        if A.root.get('chain'):
            h.append(f'<p><b>{E(R("root_chain", lg))}</b></p><table cellpadding="3">')
            for s in A.root['chain']:
                h.append(f'<tr><td style="color:#93C5FD">{fmt_t(s["t"])}</td><td>{E(texts.chain_step(s, lg, fmt_t))}</td></tr>')
            h.append('</table>')
        h.append(f'<p><b>{E(R("root_prev", lg))}</b><br>{E(texts.T("prevent_" + c, lg))}</p>')
        if A.root.get('others'):
            h.append(f'<p style="color:#94A3B8">{E(R("root_others", lg))}: {E(", ".join(texts.T("cause_" + o, lg) for o in A.root["others"]))}</p>')
    # Sağlık ayrıntıları
    h.append(f'<h3 style="color:#93C5FD">{E(R("health", lg))}</h3>')
    for k, x in A.health.items():
        c = STATUS_COL[x['status']]
        fs = x['findings']
        h.append(f'<p><b style="color:{c}">{E(texts.T("dom_" + k, lg))} · {x["score"]}</b><br>' +
                 ('<br>'.join('• ' + E(texts.render(f, lg)) for f in fs) if fs else f'<span style="color:#94A3B8">{E(R("no_find", lg))}</span>') + '</p>')
    if A.phases:
        h.append(f'<h3 style="color:#93C5FD">{E(R("phases", lg))}</h3><table width="100%" cellpadding="4" cellspacing="0">')
        h.append('<tr bgcolor="#162238">' + ''.join(f'<th align="{al}">{E(R(k, lg))}</th>' for k in ('p_phase', 'p_time', 'p_dur', 'p_alt', 'p_spd', 'p_thr', 'p_att')) + '</tr>')
        f1 = lambda x, u='': f'{x:.0f}{u}' if isinstance(x, (int, float)) else '-'
        for i, p in enumerate(A.phases):
            s = p['stats']; bg = '#111C33' if i % 2 else '#0F1A30'
            spd = s.get('as_mean') if s.get('as_mean') is not None else s.get('gs_mean')
            h.append(f'<tr bgcolor="{bg}"><td>{E(texts.T("ph_" + p["name"], lg))}</td><td>{fmt_t(p["t0"])}–{fmt_t(p["t1"])}</td><td>{fmt_t(s.get("dur", 0))}</td>'
                     f'<td>{f1(s.get("alt_mean"))}/{f1(s.get("alt_max"))} m</td><td>{f1(spd, " m/s")}</td><td>{f1(s.get("thr_mean"), "%")}</td>'
                     f'<td>{f1(s.get("roll_max"))}°/{f1(s.get("pitch_max"))}°</td></tr>')
        h.append('</table>')
    # Yapay zekâ anomali tespiti
    info_ = getattr(A, 'anomaly_info', None)
    if info_:
        from ..core.report import anomaly_rows
        h.append(f'<h3 style="color:#93C5FD">🧠 {E(R("anomaly", lg))}</h3><p style="color:#CBD5E1">{E(R("anom_intro", lg).format(n=info_["windows"], k=info_["learned_flights"], i=info_["index"]))}</p>')
        rows = anomaly_rows(A, lg)
        if rows:
            h.append('<table width="100%" cellpadding="4" cellspacing="0">')
            for i, (a, b, c) in enumerate(rows):
                h.append(f'<tr bgcolor="{"#111C33" if i % 2 else "#0F1A30"}"><td width="18%" style="color:#FBBF24"><a href="t:{A.anomalies[i]["t0"]:.1f}" style="color:#FBBF24">{E(a)}</a></td><td width="8%">{E(b)}</td><td>{E(c)}</td></tr>')
            h.append('</table>')
        else:
            h.append(f'<p style="color:#4ADE80">✔ {E(R("anom_none", lg))}</p>')
    # Pilot performansı
    pl = getattr(A, 'pilot', None) or {}
    if pl.get('scores'):
        from ..core.fleet import sname
        h.append(f'<h3 style="color:#93C5FD">👨‍✈️ {E(R("pilot", lg))} · {pl.get("overall")}/100</h3><table width="100%" cellpadding="3">')
        for k, v_ in pl['scores'].items():
            c = STATUS_COL['good' if v_ >= 80 else ('warn' if v_ >= 55 else 'bad')]
            h.append(f'<tr><td width="28%">{E(sname(k, lg))}</td><td width="8%"><b style="color:{c}">{v_}</b></td><td><table width="{max(2, v_)}%" cellspacing="0" cellpadding="0"><tr><td bgcolor="{c}" height="8"></td></tr></table></td></tr>')
        h.append(f'</table><p style="color:#94A3B8">{E(R("pilot_note", lg))}</p>')
    # Hava durumu
    from ..core import weather as W
    wr = W.rows(A, lg)
    h.append(f'<h3 style="color:#93C5FD">🌦 {E(R("weather", lg))}</h3><table width="100%" cellpadding="3">')
    for a, b in wr:
        h.append(f'<tr><td width="35%" style="color:#94A3B8">{E(a)}</td><td>{E(b)}</td></tr>')
    h.append('</table>')
    if A.param_findings:
        h.append(f'<h3 style="color:#93C5FD">{E(R("params", lg))}</h3>')
        for f in A.param_findings:
            c = {0: '#60A5FA', 1: '#FBBF24', 2: '#F87171'}[f['sev']]
            h.append(f'<p><b style="color:{c}">{E(R("sev" + str(f["sev"]), lg))}</b> — {E(texts.render(f["text"], lg))}</p>')
    h.append('</div>')
    return ''.join(h)


def lesson_html(key, lg):
    from ..core.rtexts import LESSON
    L = LESSON.get(key)
    if not L: return ''
    i = ('tr', 'en', 'ar').index(lg); d = 'rtl' if lg == 'ar' else 'ltr'
    return (f'<div dir="{d}"><p>ⓘ <b>{E(R("why_see", lg))}</b> {E(L["what"][i])}</p>'
            f'<table width="100%" cellpadding="8" cellspacing="4"><tr>'
            f'<td bgcolor="#14532D" width="33%"><b>{E(R("th_normal", lg))}</b><br>{E(L["normal"][i])}</td>'
            f'<td bgcolor="#713F12" width="33%"><b>{E(R("th_warn", lg))}</b><br>{E(L["warn"][i])}</td>'
            f'<td bgcolor="#7F1D1D"><b>{E(R("th_danger", lg))}</b><br>{E(L["danger"][i])}</td></tr></table></div>')


def _fbt(lg):
    from .i18n8 import U8
    return U8['fb_link'][{'tr': 0, 'en': 1, 'ar': 2}.get(lg, 0)]
