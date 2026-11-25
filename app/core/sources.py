"""Her görsel ve tablonun KAYNAĞI: değer logdaki hangi mesaj.alan'dan, hangi Full Parameter List parametresinden okunuyor,
Mission Planner'da (Review a Log / Config → Full Parameter List) ve Pixhawk'ta nerede bulunur.

Kullanım: rows(A, key, lg) → {'fields': [...], 'params': [...]} · footer(A, key, lg) → grafik altı kaynak satırı ·
html(A, key, lg) → Açıklama sekmesi için "Bu değerler nereden geliyor?" paneli · short(A, key, lg) → tablo altı tek satır.
"""
from __future__ import annotations
import html as _H, json, threading
from .paths import res

E = _H.escape
LI = {'tr': 0, 'en': 1, 'ar': 2}


def tx(tup, lg):
    return tup[LI.get(lg, 1)] if isinstance(tup, (tuple, list)) else tup


# Grafik dışı tablolar ve bölümler (grafikler viz.MP'de)
EXTRA = {
    'c_map': (['POS.Lat', 'POS.Lng', 'POS.RelHomeAlt', 'GPS.Lat', 'GPS.Lng', 'GPS.Status', 'MODE.Mode', 'CMD.Lat'],
              ['RTL_ALTITUDE', 'ALT_HOLD_RTL', 'FENCE_ENABLE', 'FENCE_RADIUS', 'WP_RADIUS']),
    'c_health': (['GPS.NSats', 'VIBE.VibeZ', 'BAT.Volt', 'XKF4.SV', 'ATT.Roll', 'RCOU.C3', 'RCIN.C3', 'ARSP.Airspeed', 'PM.Load'], []),
    'sec_modes': (['MODE.Mode', 'MODE.ModeNum', 'MODE.Rsn', 'RCIN.C8'], ['FLTMODE_CH', 'MODE_CH', 'FLTMODE1', 'FLTMODE2', 'FLTMODE3',
                                                                     'FLTMODE4', 'FLTMODE5', 'FLTMODE6', 'INITIAL_MODE']),
    'sec_motors': (['RCOU.C1', 'RCOU.C2', 'RCOU.C3', 'RCOU.C4', 'ESC.RPM'], ['FRAME_CLASS', 'FRAME_TYPE', 'Q_FRAME_CLASS', 'Q_FRAME_TYPE',
                                                                            'MOT_SPIN_MAX', 'Q_M_SPIN_MAX']),
    'sec_phases': (['POS.RelHomeAlt', 'GPS.Alt', 'GPS.Spd', 'ARSP.Airspeed', 'CTUN.ThO', 'ATT.Roll', 'ATT.Pitch'], ['THR_MAX', 'AIRSPEED_CRUISE']),
    'sec_facts': (['GPS.GWk', 'GPS.GMS', 'POS.RelHomeAlt', 'GPS.Spd', 'ARSP.Airspeed', 'BAT.Volt', 'BAT.CurrTot', 'EV.Id'], ['BATT_CAPACITY', 'BATT_MONITOR']),
    'sec_events': (['EV.Id', 'ERR.Subsys', 'ERR.ECode', 'MSG.Message', 'MODE.Mode'], []),
    'dom_gps': (['GPS.NSats', 'GPS.HDop', 'GPS.Status', 'GPA.HAcc'], ['GPS_TYPE', 'GPS_GNSS_MODE', 'AHRS_GPS_MINSATS']),
    'dom_vibration': (['VIBE.VibeX', 'VIBE.VibeY', 'VIBE.VibeZ', 'VIBE.Clip'], ['INS_ACCEL_FILTER', 'INS_HNTCH_ENABLE']),
    'dom_power': (['BAT.Volt', 'BAT.Curr', 'BAT.CurrTot', 'POWR.Vcc'], ['BATT_MONITOR', 'BATT_CAPACITY', 'BATT_LOW_VOLT', 'BATT_CRT_VOLT', 'BATT_FS_LOW_ACT']),
    'dom_ekf': (['XKF4.SV', 'XKF4.SP', 'XKF4.SH', 'XKF4.SM'], ['FS_EKF_THRESH', 'FS_EKF_ACTION', 'EK3_ENABLE']),
    'dom_control': (['ATT.Roll', 'ATT.DesRoll', 'ATT.Pitch', 'ATT.DesPitch'], ['ROLL_LIMIT_DEG', 'PTCH_LIM_MAX_DEG', 'PTCH_LIM_MIN_DEG', 'ANGLE_MAX']),
    'dom_servo': (['RCOU.C1', 'RCOU.C2', 'RCOU.C3', 'RCOU.C4'], ['SERVO1_FUNCTION', 'SERVO1_MIN', 'SERVO1_MAX', 'SERVO3_FUNCTION']),
    'dom_rc': (['RCIN.C1', 'RCIN.C3', 'EV.Id'], ['RCMAP_THROTTLE', 'THR_FS_VALUE', 'FS_THR_VALUE', 'THR_FAILSAFE', 'FS_SHORT_ACTN', 'FS_LONG_ACTN']),
    'dom_airspeed': (['ARSP.Airspeed', 'ARSP.DiffPress', 'CTUN.As'], ['ARSPD_TYPE', 'ARSPD_USE', 'ARSPD_RATIO', 'AIRSPEED_MIN']),
    'dom_cpu': (['PM.Load', 'PM.NLon', 'PM.MaxT'], ['SCHED_LOOP_RATE', 'LOG_BITMASK']),
    'dom_motors': (['RCOU.C1', 'RCOU.C2', 'RCOU.C3', 'RCOU.C4', 'ESC.RPM'], ['MOT_SPIN_MAX', 'MOT_SPIN_MIN', 'MOT_PWM_MIN', 'MOT_PWM_MAX', 'Q_M_SPIN_MAX', 'Q_M_SPIN_MIN']),
    'dom_vtol': (['QTUN.Alt', 'QTUN.DAlt', 'QTUN.CRt', 'RCOU.C5', 'RCOU.C6', 'RCOU.C7', 'RCOU.C8'], ['Q_ENABLE', 'Q_FRAME_CLASS', 'Q_FRAME_TYPE', 'Q_TRANSITION_MS',
                                                                                                    'Q_ASSIST_SPEED', 'Q_M_SPIN_MAX', 'Q_M_THST_HOVER']),
    'dom_compass': (['MAG.MagX', 'MAG.MagY', 'MAG.MagZ'], ['COMPASS_USE', 'COMPASS_MOTCT', 'COMPASS_ORIENT']),
}

T = {
    'title': ('🔎 Bu değerler nereden geliyor?', '🔎 Where do these values come from?', '🔎 من أين تأتي هذه القيم؟'),
    'intro': ('Grafikteki her çizgi logdaki bir MESAJ.ALAN\'dır; kesikli eşik çizgileri ve kanal görevleri ise Pixhawk\'taki parametrelerden '
              '(Full Parameter List) okunur. Aynısını Mission Planner\'da şöyle açarsınız:',
              'Each line is a MESSAGE.FIELD in the log; dashed limit lines and channel roles are read from Pixhawk parameters '
              '(Full Parameter List). Open the same in Mission Planner like this:',
              'كل خط في الرسم هو رسالة.حقل في السجل؛ خطوط الحدود المتقطعة ووظائف القنوات تُقرأ من معاملات Pixhawk '
              '(Full Parameter List). افتح الشيء نفسه في Mission Planner هكذا:'),
    'h_log': ('📒 Log alanları (Review a Log)', '📒 Log fields (Review a Log)', '📒 حقول السجل (Review a Log)'),
    'h_par': ('⚙ Parametreler (Full Parameter List) — bu logdaki değerler', '⚙ Parameters (Full Parameter List) — values in this log',
              '⚙ المعاملات (Full Parameter List) — القيم في هذا السجل'),
    'c_field': ('Alan', 'Field', 'الحقل'), 'c_mean': ('Anlamı', 'Meaning', 'المعنى'), 'c_mp': ('Mission Planner\'da', 'In Mission Planner', 'في Mission Planner'),
    'c_par': ('Parametre', 'Parameter', 'المعامل'), 'c_val': ('Değer', 'Value', 'القيمة'), 'c_def': ('Varsayılan', 'Default', 'الافتراضي'),
    'mp_log2': ('DATA → Review a Log → logu aç → sol ağaçta {m} ▸ {f}', 'DATA → Review a Log → open the log → left tree {m} ▸ {f}',
                'DATA → Review a Log → افتح السجل → الشجرة اليسرى {m} ▸ {f}'),
    'mp_par': ('CONFIG → Full Parameter List → Ara kutusuna {p} yazın', 'CONFIG → Full Parameter List → type {p} in Search',
               'CONFIG → Full Parameter List → اكتب {p} في البحث'),
    'pix': ('Pixhawk\'ta: parametreler kartın içinde saklanır; Mission Planner bağlıyken "Refresh Params" ile okunur, logun başında da PARM mesajı olarak kayıtlıdır '
            '(Review a Log → PARM). Değeri değiştirince "Write Params" ile karta yazılır.',
            'On the Pixhawk: parameters are stored on the board; with Mission Planner connected "Refresh Params" reads them, and the log also records them as PARM '
            'messages (Review a Log → PARM). After changing a value, "Write Params" writes it to the board.',
            'في Pixhawk: تُخزَّن المعاملات في اللوحة؛ يقرؤها Mission Planner عند الاتصال بزر "Refresh Params"، كما يسجلها السجل كرسائل PARM '
            '(Review a Log → PARM). بعد تغيير القيمة يكتبها "Write Params" إلى اللوحة.'),
    'tus': ('Zaman: her satırın TimeUS alanı (mikrosaniye). Programdaki "TimeUS" değerini Review Log\'un altındaki tabloda arayarak aynı ana gidin.',
            'Time: every row has a TimeUS field (microseconds). Search the program\'s "TimeUS" value in the table under Review Log to reach the same moment.',
            'الزمن: لكل سطر حقل TimeUS (ميكروثانية). ابحث عن قيمة "TimeUS" من البرنامج في جدول Review Log للوصول إلى اللحظة نفسها.'),
    'ft_log': ('Kaynak · log: ', 'Source · log: ', 'المصدر · السجل: '), 'ft_par': ('parametre: ', 'parameters: ', 'المعاملات: '),
    'none': ('Bu logda bu grafiğin kaynak alanı yok.', 'This log has no source field for this chart.', 'لا يحتوي هذا السجل على حقل مصدر لهذا الرسم.'),
    'nolog': ('(bu logda yok)', '(not in this log)', '(غير موجود في هذا السجل)'),
}


def t(k, lg):
    return tx(T[k], lg)


# ------------------------------------------------------------------ sözlükler (tembel)
_LK = threading.Lock()
_MSGS = None


def _msgs():
    global _MSGS
    with _LK:
        if _MSGS is None:
            try:
                with open(res('data', 'logmsgs.json'), encoding='utf-8') as f: _MSGS = json.load(f)
            except Exception:
                _MSGS = {}
    return _MSGS


def split(fld):
    """'IMU[1].AccZ' → ('IMU', '[1]', 'AccZ')"""
    m, _, f = fld.partition('.')
    base, br, inst = m.partition('[')
    return base, ('[' + inst) if br else '', f


def field_meaning(fld, lg):
    base, _, f = split(fld)
    M = _msgs().get(base) or {}
    d = (M.get('fields') or {}).get(f) or {}
    if not d: return ''
    return d.get(lg) or d.get('en') or ''


def msg_meaning(base, lg):
    d = (_msgs().get(base) or {}).get('desc') or {}
    return d.get(lg) or d.get('en') or ''


def param_text(name, vehicle, lg):
    """(görünen ad, açıklama, birim, varsayılan) — Parametre Merkezi kütüphanesinden."""
    try:
        from .pcenter import PDB
        db = PDB.get(); v = vehicle if vehicle in db.vehicles else None
        dn, d, _ = db.text(name, v, lg)
        m = db.meta(name, v) or {}
        return dn or '', d or '', m.get('u') or '', m.get('default')
    except Exception:
        return '', '', '', None


def value_label(name, value, vehicle, lg):
    """Seçenekli parametrede değerin adı (ör. SERVO3_FUNCTION=70 → Throttle)."""
    try:
        from .pcenter import PDB, value_label as vl
        db = PDB.get(); v = vehicle if vehicle in db.vehicles else None
        m = db.meta(name, v) or {}
        lab = vl(value, m.get('vals'))
        return db.lbl(lab, lg) if lab else ''
    except Exception:
        return ''


def mp_log_path(fld, lg):
    base, inst, f = split(fld)
    return t('mp_log2', lg).format(m=base + inst, f=f)


def mp_par_path(p, lg):
    return t('mp_par', lg).format(p=p)


def _has(L, fld):
    base, inst, f = split(fld)
    for m in (base + inst, base):
        if m in L.msgs:
            try:
                s = L.s(m)
                return (not f) or s.has(f) or m in ('MODE', 'EV', 'ERR', 'MSG', 'CMD')
            except Exception:
                return True
    if any(k.startswith(base + '[') for k in L.msgs): return True
    return base in ('MODE', 'EV', 'ERR', 'MSG', 'ISBD', 'CMD') and bool(getattr(L, 'modes', None) or getattr(L, 'events', None) or getattr(L, 'texts', None))


def raw(A, key):
    """(alanlar, [(param, değer)]) — logda bulunanlar."""
    from . import viz
    if key in viz.MP and any(viz.MP[key]): return viz.mp_info(A, key)
    f, p = EXTRA.get(key, ([], []))
    L = A.L
    ok = [x for x in f if _has(L, x)]
    if key in ('sec_motors', 'dom_motors', 'dom_vtol'):
        ms = viz.motors(A)
        if ms or key == 'sec_motors':
            ok = [f'RCOU.{m["ch"]}' for m in ms] + [x for x in ok if not x.startswith('RCOU.')]
        p = [f'SERVO{m["ch"][1:]}_FUNCTION' for m in ms] + list(p)
    if key == 'sec_modes':
        try:
            ch = int(L.params.get('FLTMODE_CH') or L.params.get('MODE_CH') or 8)
            ok = [x for x in ok if not x.startswith('RCIN.')] + [f'RCIN.C{ch}']
        except Exception: pass
    if key == 'dom_servo':
        try:
            rl = viz.channel_roles(A)
            ok = [f'RCOU.{r["ch"]}' for r in rl] or ok
            p = [f'SERVO{r["ch"][1:]}_{s}' for r in rl for s in ('FUNCTION', 'MIN', 'MAX')] or p
        except Exception: pass
    seen = set(); pv = []
    for k in p:
        if k in L.params and k not in seen:
            seen.add(k); pv.append((k, L.params[k]))
    return ok, pv


def rows(A, key, lg):
    f, pv = raw(A, key)
    veh = getattr(A, 'vehicle', None)
    F = [{'name': x, 'meaning': field_meaning(x, lg), 'msg': msg_meaning(split(x)[0], lg), 'mp': mp_log_path(x, lg)} for x in f]
    P = []
    for n, v in pv:
        dn, d, u, df = param_text(n, veh, lg)
        P.append({'name': n, 'value': v, 'title': dn, 'desc': d, 'unit': u, 'default': df, 'mp': mp_par_path(n, lg),
                  'label': value_label(n, v, veh, lg)})
    return {'fields': F, 'params': P}


def _fmt(v):
    try:
        f = float(v)
        return str(int(f)) if f.is_integer() else f'{f:.4g}'
    except Exception:
        return str(v)


def footer(A, key, lg, width=150):
    """Grafik altı kaynak yazısı (en çok 2 satır)."""
    try:
        f, pv = raw(A, key)
    except Exception:
        return ''
    if not f and not pv: return ''
    a = t('ft_log', lg) + '  '.join(f[:14]) if f else ''
    b = t('ft_par', lg) + '  '.join(f'{n}={_fmt(v)}' for n, v in pv[:10]) if pv else ''
    lines = []
    for s in (a, b):
        if not s: continue
        if len(s) > width: s = s[:width - 1].rsplit('  ', 1)[0] + ' …'
        lines.append(s)
    return '\n'.join(lines)


def fields_brief(A, key, n=3):
    """Tablo hücresi için kısa alan listesi (ör. 'GPS.NSats · GPS.HDop')."""
    try:
        f, _ = raw(A, key)
    except Exception:
        return ''
    return ' · '.join(f[:n])


def short(A, key, lg):
    """Tablo altı tek satır: 'Kaynak · log: … · parametre: …'"""
    return footer(A, key, lg, width=400).replace('\n', '   ·   ')


def html(A, key, lg, dark=True):
    """Açıklama sekmesi için kaynak paneli (QTextBrowser HTML)."""
    if A is None: return ''
    try:
        r = rows(A, key, lg)
    except Exception:
        return ''
    d = 'rtl' if lg == 'ar' else 'ltr'; al = 'right' if lg == 'ar' else 'left'
    hc, mc, bg1, bg2, hb = ('#93C5FD', '#94A3B8', '#111C33', '#0F1A30', '#162238') if dark else ('#1D4ED8', '#475569', '#F8FAFC', '#EEF2F7', '#E2E8F0')
    h = [f'<div dir="{d}" style="text-align:{al}"><h3 style="color:{hc}">{E(t("title", lg))}</h3><p style="color:{mc}">{E(t("intro", lg))}</p>']
    if not r['fields'] and not r['params']:
        h.append(f'<p style="color:{mc}">{E(t("none", lg))}</p></div>'); return ''.join(h)
    if r['fields']:
        h.append(f'<p><b>{E(t("h_log", lg))}</b></p><table width="100%" cellpadding="4" cellspacing="0">'
                 f'<tr bgcolor="{hb}"><th align="{al}">{E(t("c_field", lg))}</th><th align="{al}">{E(t("c_mean", lg))}</th><th align="{al}">{E(t("c_mp", lg))}</th></tr>')
        for i, x in enumerate(r['fields']):
            mean = (E(x['meaning']) + (f' <span style="color:{mc}">— {E(x["msg"][:90])}</span>' if x['msg'] else '')) if x['meaning'] else E(x['msg'][:120])
            h.append(f'<tr bgcolor="{bg1 if i % 2 else bg2}"><td><code><b>{E(x["name"])}</b></code></td><td>{mean}</td>'
                     f'<td style="color:{mc}">{E(x["mp"])}</td></tr>')
        h.append('</table>')
    if r['params']:
        h.append(f'<p><b>{E(t("h_par", lg))}</b></p><table width="100%" cellpadding="4" cellspacing="0">'
                 f'<tr bgcolor="{hb}"><th align="{al}">{E(t("c_par", lg))}</th><th align="{al}">{E(t("c_val", lg))}</th>'
                 f'<th align="{al}">{E(t("c_def", lg))}</th><th align="{al}">{E(t("c_mean", lg))}</th></tr>')
        for i, p in enumerate(r['params']):
            df = '' if p['default'] is None else _fmt(p['default'])
            diff = df != '' and df != _fmt(p['value'])
            val = f'<b style="color:{"#FBBF24" if diff else "inherit"}">{E(_fmt(p["value"]))}</b>' + (f' {E(p["unit"])}' if p['unit'] else '') + \
                (f'<br><span style="color:{mc}">= {E(p["label"])}</span>' if p.get('label') else '')
            desc = (f'<b>{E(p["title"])}</b> — ' if p['title'] else '') + E((p['desc'] or '')[:220])
            h.append(f'<tr bgcolor="{bg1 if i % 2 else bg2}"><td><code><b>{E(p["name"])}</b></code></td><td>{val}</td><td style="color:{mc}">{E(df)}</td>'
                     f'<td>{desc}<br><span style="color:{mc}">{E(p["mp"])}</span></td></tr>')
        h.append('</table>')
    h.append(f'<p style="color:{mc}">⏱ {E(t("tus", lg))}<br>🧩 {E(t("pix", lg))}</p></div>')
    return ''.join(h)
