"""3B tekrara bağlı adım adım ders rehberi.

Analizden "şu saniyede şunu izle" adımları üretilir: arm, kalkış, tırmanış, mod değişimleri, uyarılar,
ML anomalileri, kök neden zinciri ve iniş/kırım. Her adımda 3B tekrar o ana gider, ilgili grafik işaretlenir.
"""
from __future__ import annotations
from .analysis import fmt_t
from . import texts, knowledge as K

LI = {'tr': 0, 'en': 1, 'ar': 2}
S = {
    'arm': (('Motorlar arm edildi', 'Motors armed', 'تم تسليح المحركات'),
            ('İzle: araç yerde, gaz sıfırda. Arm öncesi kontroller (prearm) bu andan önce geçmiş olmalı.', 'Watch: vehicle on the ground, throttle at zero. Pre-arm checks must pass before this moment.', 'راقب: المركبة على الأرض والخانق صفر. يجب اجتياز فحوص ما قبل التسليح قبل هذه اللحظة.')),
    'takeoff': (('Kalkış', 'Take-off', 'الإقلاع'),
                ('İzle: irtifa ve hız birlikte artmalı, yatış/yunuslama sakin kalmalı. Grafikte irtifanın düzgün yükselişine bakın.', 'Watch: altitude and speed should rise together with calm roll/pitch. On the chart, check for a smooth climb.', 'راقب: يجب أن يرتفع الارتفاع والسرعة معاً مع ثبات الدوران/الميل.')),
    'maxalt': (('En yüksek irtifa', 'Maximum altitude', 'أعلى ارتفاع'),
               ('İzle: tırmanış bitip seyre geçiş. Gazın düşüp hızın sabitlendiği an.', 'Watch: end of climb and transition to cruise; throttle reduces and speed settles.', 'راقب: نهاية الصعود والانتقال إلى الطيران المستقر.')),
    'mode': (('Mod değişimi: {m}', 'Mode change: {m}', 'تغيير الوضع: {m}'),
             ('İzle: mod değişince aracın davranışı nasıl değişiyor? {r}', 'Watch: how does the behaviour change after the mode switch? {r}', 'راقب: كيف يتغير السلوك بعد تبديل الوضع؟ {r}')),
    'warn': (('Uyarı: {x}', 'Warning: {x}', 'تحذير: {x}'),
             ('İzle: bu mesaj hangi belirtiyle aynı anda geliyor? Zaman çizelgesi ve ilgili grafiğe bakın.', 'Watch: which symptom appears together with this message? Check the timeline and the related chart.', 'راقب: أي عرض يظهر مع هذه الرسالة؟ راجع الخط الزمني والرسم المرتبط.')),
    'anom': (('Alışılmadık bölüm (yapay zekâ)', 'Unusual segment (AI)', 'مقطع غير معتاد (ذكاء اصطناعي)'),
             ('İzle: {f} normal uçuşlara göre belirgin farklı. Turuncu işaretli aralığı grafikle karşılaştırın.', 'Watch: {f} differs clearly from normal flights. Compare the orange-marked range on the chart.', 'راقب: {f} يختلف بوضوح عن الرحلات الطبيعية. قارن المدى المعلّم بالبرتقالي.')),
    'root': (('Kök neden başlangıcı: {c}', 'Root cause onset: {c}', 'بداية السبب الجذري: {c}'),
             ('İzle: sorun ilk burada görülüyor. {w}', 'Watch: the problem first appears here. {w}', 'راقب: تظهر المشكلة لأول مرة هنا. {w}')),
    'landing': (('İniş', 'Landing', 'الهبوط'),
                ('İzle: alçalma hızı yere yaklaşırken azalmalı, yatış küçük kalmalı; sıçrama olmamalı.', 'Watch: sink rate should reduce near the ground, bank small, no bounce.', 'راقب: يجب أن ينخفض معدل الهبوط قرب الأرض مع ميل صغير ودون ارتداد.')),
    'crash': (('Kırım anı', 'Impact', 'لحظة التحطم'),
              ('İzle: logun bittiği an; irtifa, tutum ve titreşimdeki son değişimler kırımı doğruluyor.', 'Watch: the end of the log; the last changes in altitude, attitude and vibration confirm the impact.', 'راقب: نهاية السجل؛ التغيرات الأخيرة في الارتفاع والوضعية والاهتزاز تؤكد التحطم.')),
}
CAUSE_CHART = {'gps': 'c_gps', 'ekf': 'c_ekf', 'battery': 'c_bat', 'radio': 'c_sticks', 'stall': 'c_alt', 'vibration': 'c_vibe',
               'compass': 'c_mag', 'power': 'c_bat', 'control': 'c_att', 'motor': 'c_motors', 'pilot': 'c_sticks'}


def _s(k, lang, i, **a):
    return S[k][i][LI.get(lang, 0)].format(**a)


def build(A, lang='tr', max_steps=24):
    st = []
    f = A.facts
    if A.armed: st.append({'t': A.armed[0][0], 'k': 'arm', 'chart': 'c_timeline'})
    if 'takeoff_t' in f: st.append({'t': f['takeoff_t'], 'k': 'takeoff', 'chart': 'c_alt'})
    if 'max_alt_t' in f: st.append({'t': f['max_alt_t'], 'k': 'maxalt', 'chart': 'c_alt'})
    for t, n, _, r in A.L.modes[:10]:
        rs = K.MODE_REASON.get(r)
        st.append({'t': t, 'k': 'mode', 'chart': 'c_alt', 'a': {'m': K.mode_name(A.vehicle, n), 'r': K.tr3(rs, lang) if rs else ''}})
    n_w = 0
    for e in A.events:
        if e['sev'] >= 2 or (e['sev'] == 1 and e['cat'] == 'msg' and n_w < 4):
            n_w += 1
            st.append({'t': e['t'], 'k': 'warn', 'chart': 'c_timeline', 'a': {'x': texts.render(e['text'], lang)[:90]}})
            if n_w >= 6: break
    from .anomaly import fname
    for it in (getattr(A, 'anomalies', None) or [])[:3]:
        k0 = it['feats'][0]['k'] if it['feats'] else 'vibe'
        ch = {'vibe': 'c_vibe', 'clip': 'c_vibe', 'sats': 'c_gps', 'hdop': 'c_gps', 'att_err': 'c_att', 'thr': 'c_rcou', 'v_drop': 'c_bat',
              'curr': 'c_bat', 'ekf': 'c_ekf', 'mag_dev': 'c_mag', 'alt_err': 'c_alt', 'xtrack': 'c_alt', 'as_gs': 'c_alt', 'cpu': 'c_timeline'}.get(k0, 'c_alt')
        st.append({'t': it['t0'], 't1': it['t1'], 'k': 'anom', 'chart': ch, 'a': {'f': fname(k0, lang)}})
    if A.root and A.root.get('cause') not in (None, 'unknown'):
        c = A.root['cause']
        st.append({'t': A.root.get('t', 0), 'k': 'root', 'chart': CAUSE_CHART.get(c, 'c_timeline'),
                   'a': {'c': texts.T('cause_' + c, lang), 'w': texts.T('why_' + c, lang)[:220]}})
    if A.flights:
        st.append({'t': A.flights[-1][1], 'k': 'crash' if A.verdict.get('kind') == 'crash' else 'landing', 'chart': 'c_alt'})
    st.sort(key=lambda x: x['t'])
    # aynı ana çok yakın tekrarları ayıkla
    out = []
    for s in st:
        if out and abs(s['t'] - out[-1]['t']) < 1.0 and s['k'] == out[-1]['k']: continue
        out.append(s)
    out = out[:max_steps]
    for s in out:
        a = s.get('a', {})
        s['title'] = _s(s['k'], lang, 0, **a); s['text'] = _s(s['k'], lang, 1, **a); s['time'] = fmt_t(s['t'])
    return out
