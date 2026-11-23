"""Filo takibi ve pilot kartları.

* Her hava aracı seri numarasıyla (uçuş kartının benzersiz kimliği, logdan otomatik) kaydedilir.
* Uçuş saatleri arşivdeki analizlerden toplanır; bakım, motor ve batarya değişimleri kayıt altına alınır.
* "Bu uçak X saat sonra bakıma girmeli" uyarıları ve motor / batarya ömrü hesaplanır.
* Pilot kartı: aynı pilotun uçuşlarındaki iniş, gaz yönetimi, hız, yumuşaklık, irtifa ve rota puanları.
"""
from __future__ import annotations
import json, time, uuid

MAINT_KINDS = ('inspection', 'motor', 'battery', 'propeller', 'servo', 'repair', 'other')
KIND_NAMES = {
    'inspection': ('Periyodik bakım / kontrol', 'Periodic inspection', 'فحص دوري'),
    'motor': ('Motor değişimi', 'Motor replacement', 'استبدال المحرك'),
    'battery': ('Batarya değişimi', 'Battery replacement', 'استبدال البطارية'),
    'propeller': ('Pervane değişimi', 'Propeller replacement', 'استبدال المروحة'),
    'servo': ('Servo değişimi', 'Servo replacement', 'استبدال السيرفو'),
    'repair': ('Onarım', 'Repair', 'إصلاح'),
    'other': ('Diğer', 'Other', 'أخرى'),
}
DEFAULTS = {'maint_interval_h': 25.0, 'motor_life_h': 200.0, 'battery_cycles': 300, 'prop_life_h': 50.0}
SCORE_NAMES = {
    'landing': ('İniş kalitesi', 'Landing quality', 'جودة الهبوط'), 'throttle': ('Gaz yönetimi', 'Throttle management', 'إدارة الخانق'),
    'speed': ('Hız kontrolü', 'Speed control', 'التحكم بالسرعة'), 'smooth': ('Kumanda yumuşaklığı', 'Control smoothness', 'سلاسة التحكم'),
    'alt_hold': ('İrtifa tutma', 'Altitude holding', 'الحفاظ على الارتفاع'), 'nav': ('Rota takibi', 'Track keeping', 'تتبع المسار'),
}


def kname(k, lang='tr'):
    return KIND_NAMES.get(k, (k, k, k))[('tr', 'en', 'ar').index(lang) if lang in ('tr', 'en', 'ar') else 0]


def sname(k, lang='tr'):
    return SCORE_NAMES.get(k, (k, k, k))[('tr', 'en', 'ar').index(lang) if lang in ('tr', 'en', 'ar') else 0]


def ensure_aircraft(archive, A):
    """Analizdeki seri numarası filoda yoksa otomatik ekle."""
    sn = getattr(A, 'serial', '')
    if not sn: return None
    if archive.rec_get('aircraft', sn) is None:
        archive.rec_put('aircraft', sn, {'id': sn, 'serial': sn, 'name': f"{getattr(A, 'board_name', '') or A.vehicle} · {sn[-6:]}",
                                        'profile': A.profile, 'notes': '', 'created': time.strftime('%Y-%m-%d'), **DEFAULTS})
    return sn


def add_maint(archive, serial, kind, date, note='', by='', hours_at=None):
    mid = uuid.uuid4().hex[:12]
    if hours_at is None: hours_at = stats(archive, serial)['hours']
    archive.rec_put('maint', mid, {'id': mid, 'serial': serial, 'kind': kind, 'date': date, 'note': note, 'by': by, 'hours_at': round(hours_at, 2)})
    return mid


def flights_of(archive, serial):
    return [r for r in archive.list() if (r.get('aircraft') or '') == serial]


def stats(archive, serial):
    ac = archive.rec_get('aircraft', serial) or {**DEFAULTS}
    fl = sorted(flights_of(archive, serial), key=lambda r: r.get('flight_ts') or 0)
    hours = sum((r.get('flight_time') or 0) for r in fl) / 3600.0
    mts = [m for m in archive.rec_list('maint') if m.get('serial') == serial]
    mts.sort(key=lambda m: (m.get('date') or '', m.get('hours_at') or 0))

    def since(kind):
        last = [m for m in mts if m.get('kind') == kind]
        return hours - (last[-1].get('hours_at') or 0) if last else hours

    def flights_since(kind):
        last = [m for m in mts if m.get('kind') == kind]
        if not last: return len(fl)
        h0 = last[-1].get('hours_at') or 0; acc = 0.0; n = 0
        for r in fl:
            acc += (r.get('flight_time') or 0) / 3600.0
            if acc > h0 + 1e-6: n += 1
        return n
    s_insp = since('inspection'); s_mot = since('motor'); s_prop = since('propeller'); n_bat = flights_since('battery')
    iv = float(ac.get('maint_interval_h') or DEFAULTS['maint_interval_h'])
    ml = float(ac.get('motor_life_h') or DEFAULTS['motor_life_h'])
    pl = float(ac.get('prop_life_h') or DEFAULTS['prop_life_h'])
    bl = int(ac.get('battery_cycles') or DEFAULTS['battery_cycles'])
    warn = []
    due = iv - s_insp
    if due <= 0: warn.append(('maint_over', 2, {'h': round(-due, 1)}))
    elif due <= iv * 0.15: warn.append(('maint_soon', 1, {'h': round(due, 1)}))
    if s_mot >= ml: warn.append(('motor_over', 2, {'h': round(s_mot, 1), 'l': ml}))
    elif s_mot >= ml * 0.85: warn.append(('motor_soon', 1, {'h': round(s_mot, 1), 'l': ml}))
    if s_prop >= pl: warn.append(('prop_over', 1, {'h': round(s_prop, 1), 'l': pl}))
    if n_bat >= bl: warn.append(('bat_over', 2, {'n': n_bat, 'l': bl}))
    elif n_bat >= bl * 0.85: warn.append(('bat_soon', 1, {'n': n_bat, 'l': bl}))
    crashes = sum(1 for r in fl if r.get('verdict') == 'crash'); inc = sum(1 for r in fl if r.get('verdict') == 'incident')
    if crashes and (not mts or (mts[-1].get('hours_at') or 0) < hours - 1e-6 and any(r.get('verdict') == 'crash' for r in fl[-1:])):
        warn.append(('after_crash', 2, {}))
    return {'hours': hours, 'flights': len(fl), 'crashes': crashes, 'incidents': inc, 'since_inspection': s_insp, 'next_due_h': due,
            'motor_hours': s_mot, 'motor_life': ml, 'prop_hours': s_prop, 'battery_cycles': n_bat, 'battery_limit': bl,
            'maint': mts, 'warnings': warn, 'avg_score': (sum(r.get('overall') or 0 for r in fl) / len(fl)) if fl else None,
            'last_flight': (fl[-1].get('flight_date') or fl[-1].get('analyzed_at')) if fl else ''}


WARN_TXT = {
    'maint_over': ('Periyodik bakım {h} saat GECİKTİ — uçuştan önce bakım yapın.', 'Periodic maintenance OVERDUE by {h} h — service before flying.', 'الصيانة الدورية متأخرة {h} ساعة — نفّذ الصيانة قبل الطيران.'),
    'maint_soon': ('Bu uçak {h} saat sonra bakıma girmeli.', 'This aircraft is due for maintenance in {h} h.', 'يجب صيانة هذه الطائرة بعد {h} ساعة.'),
    'motor_over': ('Motor ömrü doldu: {h}/{l} saat.', 'Motor life exceeded: {h}/{l} h.', 'انتهى عمر المحرك: {h}/{l} ساعة.'),
    'motor_soon': ('Motor ömrünün sonuna yaklaşıldı: {h}/{l} saat.', 'Motor near end of life: {h}/{l} h.', 'المحرك قريب من نهاية عمره: {h}/{l} ساعة.'),
    'prop_over': ('Pervaneler {h}/{l} saat kullanıldı; kontrol edin/değiştirin.', 'Propellers used {h}/{l} h; inspect/replace.', 'المراوح استُخدمت {h}/{l} ساعة؛ افحص/استبدل.'),
    'bat_over': ('Batarya çevrim ömrü doldu: {n}/{l}.', 'Battery cycle life exceeded: {n}/{l}.', 'انتهى عمر دورات البطارية: {n}/{l}.'),
    'bat_soon': ('Batarya çevrimi sınıra yaklaştı: {n}/{l}.', 'Battery cycles near the limit: {n}/{l}.', 'دورات البطارية قريبة من الحد: {n}/{l}.'),
    'after_crash': ('Son uçuş kırımla bitti: kayıtlı onarım/kontrol yok.', 'The last flight ended in a crash: no repair/inspection recorded.', 'انتهت الرحلة الأخيرة بتحطم: لا يوجد إصلاح/فحص مسجل.'),
}


def warn_text(w, lang='tr'):
    k, sev, a = w
    return WARN_TXT[k][('tr', 'en', 'ar').index(lang) if lang in ('tr', 'en', 'ar') else 0].format(**a)


def all_warnings(archive, lang='tr'):
    out = []
    for ac in archive.rec_list('aircraft'):
        st = stats(archive, ac['id'])
        for w in st['warnings']: out.append((ac, w[1], warn_text(w, lang)))
    return out


# ------------------------------------------------------------------ pilotlar
def add_pilot(archive, name, license_='', notes=''):
    pid = uuid.uuid4().hex[:10]
    archive.rec_put('pilot', pid, {'id': pid, 'name': name, 'license': license_, 'notes': notes, 'created': time.strftime('%Y-%m-%d')})
    return pid


def pilot_card(archive, pid):
    fl = sorted([r for r in archive.list() if (r.get('pilot') or '') == pid], key=lambda r: r.get('flight_ts') or 0)
    per = []
    agg = {}
    for r in fl:
        try: ps = json.loads(r.get('pilot_scores') or '{}')
        except Exception: ps = {}
        sc = ps.get('scores') or {}
        per.append({'date': r.get('flight_date') or (r.get('analyzed_at') or '')[:16], 'name': r.get('name'), 'overall': ps.get('overall'),
                    'scores': sc, 'verdict': r.get('verdict'), 'flight_time': r.get('flight_time') or 0})
        for k, v in sc.items(): agg.setdefault(k, []).append(v)
    avg = {k: sum(v) / len(v) for k, v in agg.items()}
    trend = None
    ov = [p['overall'] for p in per if p['overall'] is not None]
    if len(ov) >= 4:
        h = len(ov) // 2; trend = sum(ov[h:]) / len(ov[h:]) - sum(ov[:h]) / h
    return {'flights': per, 'avg': avg, 'overall': (sum(avg.values()) / len(avg)) if avg else None, 'n': len(fl),
            'hours': sum(p['flight_time'] for p in per) / 3600.0, 'crashes': sum(1 for p in per if p['verdict'] == 'crash'), 'trend': trend,
            'weakest': min(avg, key=avg.get) if avg else None, 'strongest': max(avg, key=avg.get) if avg else None}


def radar_png(avg: dict, lang='tr', title=''):
    import io, math
    from matplotlib.figure import Figure
    from .charts import shape
    keys = [k for k in SCORE_NAMES if k in avg]
    if len(keys) < 3: return None
    fig = Figure(figsize=(4.6, 4.2), dpi=120)
    ax = fig.add_subplot(111, polar=True)
    ang = [i / len(keys) * 2 * math.pi for i in range(len(keys))] + [0]
    vals = [avg[k] for k in keys] + [avg[keys[0]]]
    ax.plot(ang, vals, color='#2563EB', lw=2); ax.fill(ang, vals, color='#2563EB', alpha=0.25)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels([shape(sname(k, lang), lang) for k in keys], fontsize=7)
    ax.set_ylim(0, 100); ax.set_yticks([25, 50, 75, 100]); ax.tick_params(labelsize=6)
    if title: ax.set_title(shape(title, lang), fontsize=9)
    fig.tight_layout(); b = io.BytesIO(); fig.savefig(b, format='png'); return b.getvalue()


def pilot_pdf(archive, pid, path, lang='tr', lh=None):
    """Pilot performans kartını antetli PDF olarak üretir."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Spacer, Image
    import io
    from . import report as RP, letterhead as LHM
    p = archive.rec_get('pilot', pid) or {'name': pid}
    c = pilot_card(archive, pid)
    st = RP.pdf_kit(lang, lh)
    P, H1, H2, tbl, W_ = st['P'], st['H1'], st['H2'], st['tbl'], st['W']
    i = ('tr', 'en', 'ar').index(lang)
    L_ = {'title': ('Pilot Performans Kartı', 'Pilot Performance Card', 'بطاقة أداء الطيار'), 'flights': ('Uçuş', 'Flights', 'الرحلات'),
          'hours': ('Uçuş saati', 'Flight hours', 'ساعات الطيران'), 'crash': ('Kırım', 'Crashes', 'التحطم'), 'overall': ('Genel puan', 'Overall', 'الدرجة العامة'),
          'trend': ('Eğilim', 'Trend', 'الاتجاه'), 'weak': ('Geliştirilecek alan', 'Area to improve', 'مجال للتحسين'),
          'strong': ('Güçlü alan', 'Strongest area', 'نقطة القوة'), 'list': ('Uçuşlar', 'Flights', 'الرحلات'), 'date': ('Tarih', 'Date', 'التاريخ'),
          'file': ('Dosya', 'File', 'الملف'), 'score': ('Puan', 'Score', 'الدرجة'), 'lic': ('Lisans', 'License', 'الرخصة')}
    g = lambda k: L_[k][i]
    story = [P(g('title'), st['TT']), Spacer(1, 4), P(f"{p.get('name')}" + (f" · {g('lic')}: {p.get('license')}" if p.get('license') else ''), H2)]
    rows = [[g('flights'), str(c['n'])], [g('hours'), f"{c['hours']:.1f}"], [g('crash'), str(c['crashes'])],
            [g('overall'), f"{c['overall']:.0f}/100" if c['overall'] is not None else '-'],
            [g('trend'), (f"{c['trend']:+.1f}" if c['trend'] is not None else '-')],
            [g('strong'), sname(c['strongest'], lang) if c['strongest'] else '-'], [g('weak'), sname(c['weakest'], lang) if c['weakest'] else '-']]
    story.append(tbl(rows, None, [6 * cm, W_ - 6 * cm]))
    rp = radar_png(c['avg'], lang)
    if rp:
        story.append(Spacer(1, 6)); im = Image(io.BytesIO(rp), width=10 * cm, height=10 * cm * 4.2 / 4.6); im.hAlign = 'CENTER'; story.append(im)
    if c['avg']:
        story.append(tbl([[sname(k, lang), f'{v:.0f}'] for k, v in c['avg'].items()], None, [8 * cm, 3 * cm]))
    story.append(P(g('list'), H1))
    fr = [[f['date'], f['name'] or '', str(f['overall'] if f['overall'] is not None else '-')] for f in c['flights'][-40:]]
    if fr: story.append(tbl(fr, [g('date'), g('file'), g('score')], [4 * cm, W_ - 7 * cm, 3 * cm]))
    st['build'](path, story, g('title'))
    return path
