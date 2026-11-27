"""Alıştırma modu: açık logdan ve kütüphanelerden otomatik soru üretir, puanlar ve açıklar."""
from __future__ import annotations
import json, random
from .analysis import fmt_t
from .texts import T
from .paths import res

Q = {
    'takeoff': ('Bu uçuşta kalkış hangi anda oldu?', 'When did the takeoff happen in this flight?', 'متى حدث الإقلاع في هذه الرحلة؟'),
    'landing': ('Uçuş hangi anda sona erdi (iniş/son)?', 'When did the flight end (landing/end)?', 'متى انتهت الرحلة (الهبوط/النهاية)؟'),
    'maxalt': ('Ulaşılan en yüksek irtifa yaklaşık kaç metre?', 'What was the approximate maximum altitude (m)?', 'ما هو أعلى ارتفاع تقريبي (م)؟'),
    'verdict': ('Bu logun sonucu nedir?', 'What is the outcome of this log?', 'ما نتيجة هذا السجل؟'),
    'cause': ('Olayın en olası kök nedeni nedir?', 'What is the most likely root cause?', 'ما السبب الجذري الأرجح؟'),
    'worst': ('Sağlık puanı en düşük alan hangisi?', 'Which area has the lowest health score?', 'أي مجال لديه أدنى درجة صحة؟'),
    'firstmode': ('Logdaki ilk uçuş modu hangisi?', 'Which is the first flight mode in the log?', 'ما هو أول وضع طيران في السجل؟'),
    'minvolt': ('En düşük batarya gerilimi yaklaşık kaç volt?', 'What was the approximate minimum battery voltage?', 'ما أدنى جهد للبطارية تقريبًا؟'),
    'msg': ('"{d}" bilgisi hangi log mesajında bulunur?', 'Which log message contains: "{d}"?', 'أي رسالة سجل تحتوي على: "{d}"؟'),
    'param': ('Şu açıklama hangi parametreye aittir: "{d}"', 'Which parameter matches this description: "{d}"', 'أي معامل يطابق هذا الوصف: "{d}"'),
}
EXPL = {
    'takeoff': ('Kalkış, STAT.isFlying veya irtifa/hız artışından tespit edilir.', 'Takeoff is detected from STAT.isFlying or the rise in altitude/speed.', 'يُكتشف الإقلاع من STAT.isFlying أو ارتفاع الارتفاع/السرعة.'),
    'landing': ('Bitiş, uçuş durumunun sona erdiği an veya kırımda logun bittiği andır.', 'The end is when flying state stops, or the log end in a crash.', 'النهاية هي توقف حالة الطيران أو نهاية السجل عند التحطم.'),
    'maxalt': ('POS.RelHomeAlt (eve göre irtifa) en yüksek değeri.', 'Maximum of POS.RelHomeAlt (altitude above home).', 'أعلى قيمة لـ POS.RelHomeAlt (الارتفاع فوق نقطة الانطلاق).'),
    'minvolt': ('BAT.Volt en düşük değeri; yük altında gerilim düşer.', 'Minimum of BAT.Volt; voltage sags under load.', 'أدنى قيمة لـ BAT.Volt؛ ينخفض الجهد تحت الحمل.'),
}
LI = {'tr': 0, 'en': 1, 'ar': 2}

# Yanlış cevap açıklamaları
WN = {
    'time': ('"{x}" değil: o anda araç {st} (irtifa ≈ {a:.0f} m). Doğru an {c}.', '"{x}" is wrong: at that moment the vehicle was {st} (altitude ≈ {a:.0f} m). The correct time is {c}.', '"{x}" خطأ: في تلك اللحظة كانت المركبة {st} (الارتفاع ≈ {a:.0f} م). الوقت الصحيح {c}.'),
    'num': ('"{x}" değil: logdaki gerçek değer {c} (fark %{d:.0f}).', '"{x}" is wrong: the real value in the log is {c} ({d:.0f}% off).', '"{x}" خطأ: القيمة الفعلية في السجل {c} (فرق {d:.0f}%).'),
    'verdict': ('"{x}" değil: {wd} Bu logda ise: {cd}', '"{x}" is wrong: {wd} In this log: {cd}', '"{x}" خطأ: {wd} أما في هذا السجل: {cd}'),
    'cause': ('"{x}" değil: bu logda {dom} alanının puanı {s}/100 ve bu nedenin tipik izi görülmüyor. Asıl zincir {c} ile başlıyor.', '"{x}" is wrong: here the {dom} score is {s}/100 and the typical trace of this cause is missing. The chain starts with {c}.', '"{x}" خطأ: درجة {dom} هنا {s}/100 ولا يظهر الأثر المعتاد لهذا السبب. السلسلة تبدأ بـ {c}.'),
    'worst': ('"{x}" değil: bu alanın puanı {s}/100; en düşük olan {w} ({sw}/100).', '"{x}" is wrong: its score is {s}/100; the lowest is {w} ({sw}/100).', '"{x}" خطأ: درجته {s}/100؛ الأدنى هو {w} ({sw}/100).'),
    'mode': ('"{x}" değil: logdaki ilk MODE kaydı {c}.', '"{x}" is wrong: the first MODE record in the log is {c}.', '"{x}" خطأ: أول سجل MODE هو {c}.'),
    'lib': ('"{x}" değil: {x} şunu tutar → {d}', '"{x}" is wrong: {x} holds → {d}', '"{x}" خطأ: {x} يحتوي على ← {d}'),
    'st_ground': ('yerdeydi', 'on the ground', 'على الأرض'), 'st_air': ('havadaydı', 'airborne', 'في الجو'),
}
CAUSE_DOM = {'gps': 'gps', 'ekf': 'ekf', 'battery': 'power', 'radio': 'rc', 'stall': 'airspeed', 'vibration': 'vibration',
             'compass': 'ekf', 'power': 'power', 'control': 'control', 'motor': 'motors', 'pilot': 'rc'}
CAUSE_CHART = {'gps': 'c_gps', 'ekf': 'c_ekf', 'battery': 'c_bat', 'radio': 'c_sticks', 'stall': 'c_alt', 'vibration': 'c_vibe',
               'compass': 'c_mag', 'power': 'c_bat', 'control': 'c_att', 'motor': 'c_motors', 'pilot': 'c_sticks'}
DOM_CHART = {'gps': 'c_gps', 'vibration': 'c_vibe', 'power': 'c_bat', 'ekf': 'c_ekf', 'control': 'c_att', 'servo': 'c_rcou',
             'rc': 'c_sticks', 'airspeed': 'c_alt', 'cpu': 'c_timeline', 'motors': 'c_motors', 'vtol': 'c_alt'}


def _w(k, lang, **a):
    return WN[k][LI[lang]].format(**a)


def _q(k, lang, **a): return Q[k][LI[lang]].format(**a)


def _shuffle(correct, wrong, rnd):
    opts = [correct] + [w for w in dict.fromkeys(wrong) if w != correct][:3]
    rnd.shuffle(opts)
    return opts, opts.index(correct)


def generate(A=None, lang='tr', n=10, seed=None):
    rnd = random.Random(seed)
    out = []
    import numpy as np

    def alt_at(x):
        tr = A.track
        if tr is None: return 0.0
        return float(np.interp(x, tr['t'], tr['rel']))

    def state_at(x):
        return WN['st_air' if A.in_flight([x])[0] else 'st_ground'][LI[lang]]

    def parse_t(s_):
        p_ = s_.split(':'); return sum(float(v) * 60 ** i for i, v in enumerate(reversed(p_)))
    if A is not None:
        f = A.facts
        if 'takeoff_t' in f:
            c = f['takeoff_t']; w = [abs(c + d) for d in rnd.sample([-90, -45, -20, 25, 60, 120], 3)]
            o, i = _shuffle(fmt_t(c), [fmt_t(x) for x in w], rnd)
            out.append({'q': _q('takeoff', lang), 'opts': o, 'ans': i, 'exp': EXPL['takeoff'][LI[lang]] + f' ({fmt_t(c)})', 'chart': 'c_alt', 't': c,
                        'wexp': [_w('time', lang, x=x, st=state_at(parse_t(x)), a=alt_at(parse_t(x)), c=fmt_t(c)) for x in o]})
        if 'land_t' in f:
            c = f['land_t']; w = [max(0, c + d) for d in rnd.sample([-120, -60, -30, 30, 75], 3)]
            o, i = _shuffle(fmt_t(c), [fmt_t(x) for x in w], rnd)
            out.append({'q': _q('landing', lang), 'opts': o, 'ans': i, 'exp': EXPL['landing'][LI[lang]] + f' ({fmt_t(c)})', 'chart': 'c_alt', 't': c,
                        'wexp': [_w('time', lang, x=x, st=state_at(parse_t(x)), a=alt_at(parse_t(x)), c=fmt_t(c)) for x in o]})
        if 'max_alt' in f:
            c = f['max_alt']; w = [c * k for k in rnd.sample([0.4, 0.6, 1.5, 2.0, 2.6], 3)]
            o, i = _shuffle(f'{c:.0f} m', [f'{x:.0f} m' for x in w], rnd)
            out.append({'q': _q('maxalt', lang), 'opts': o, 'ans': i, 'exp': EXPL['maxalt'][LI[lang]], 'chart': 'c_alt', 't': f.get('max_alt_t'),
                        'wexp': [_w('num', lang, x=x, c=f'{c:.0f} m', d=abs(float(x.split()[0]) - c) / max(1, abs(c)) * 100) for x in o]})
        if 'min_volt' in f:
            c = f['min_volt']; w = [c + d for d in rnd.sample([-3, -1.8, 1.5, 2.5, 4], 3)]
            o, i = _shuffle(f'{c:.1f} V', [f'{x:.1f} V' for x in w], rnd)
            out.append({'q': _q('minvolt', lang), 'opts': o, 'ans': i, 'exp': EXPL['minvolt'][LI[lang]], 'chart': 'c_bat', 't': None,
                        'wexp': [_w('num', lang, x=x, c=f'{c:.1f} V', d=abs(float(x.split()[0]) - c) / max(1, abs(c)) * 100) for x in o]})
        kinds = ['normal', 'incident', 'crash', 'noflight']
        vk = A.verdict.get('kind', 'normal')
        o, i = _shuffle(T('v_' + vk, lang), [T('v_' + k, lang) for k in kinds], rnd)
        inv = {T('v_' + k, lang): k for k in kinds}
        out.append({'q': _q('verdict', lang), 'opts': o, 'ans': i, 'exp': T('v_desc_' + vk, lang), 'chart': 'c_timeline', 't': f.get('land_t'),
                    'wexp': [_w('verdict', lang, x=x, wd=T('v_desc_' + inv.get(x, 'normal'), lang), cd=T('v_desc_' + vk, lang)) for x in o]})
        cause = (A.root or {}).get('cause')
        if cause and vk in ('crash', 'incident'):
            allc = ['gps', 'ekf', 'battery', 'radio', 'stall', 'vibration', 'compass', 'power', 'control', 'motor']
            o, i = _shuffle(T('cause_' + cause, lang), [T('cause_' + x, lang) for x in rnd.sample(allc, 5)], rnd)
            invc = {T('cause_' + x, lang): x for x in allc}
            def wc(x):
                k_ = invc.get(x, 'gps'); dom = CAUSE_DOM.get(k_, 'gps'); h_ = A.health.get(dom, {})
                return _w('cause', lang, x=x, dom=T('dom_' + dom, lang), s=h_.get('score', '-'), c=T('cause_' + cause, lang))
            out.append({'q': _q('cause', lang), 'opts': o, 'ans': i, 'exp': T('why_' + cause, lang), 'chart': CAUSE_CHART.get(cause, 'c_timeline'),
                        't': A.root.get('t'), 'wexp': [wc(x) for x in o]})
        if A.health:
            worst = min(A.health, key=lambda k: A.health[k]['score'])
            o, i = _shuffle(T('dom_' + worst, lang), [T('dom_' + k, lang) for k in rnd.sample(list(A.health), min(5, len(A.health)))], rnd)
            invd = {T('dom_' + k, lang): k for k in A.health}
            out.append({'q': _q('worst', lang), 'opts': o, 'ans': i,
                        'exp': f"{T('dom_' + worst, lang)}: {A.health[worst]['score']}/100", 'chart': DOM_CHART.get(worst, 'c_health'), 't': None,
                        'wexp': [_w('worst', lang, x=x, s=A.health.get(invd.get(x, worst), {}).get('score', '-'), w=T('dom_' + worst, lang), sw=A.health[worst]['score']) for x in o]})
        if f.get('modes'):
            c = f['modes'][0][1]
            pool = ['MANUAL', 'FBWA', 'AUTO', 'RTL', 'LOITER', 'CRUISE', 'TAKEOFF', 'STABILIZE', 'GUIDED', 'QHOVER']
            o, i = _shuffle(c, rnd.sample(pool, 6), rnd)
            out.append({'q': _q('firstmode', lang), 'opts': o, 'ans': i, 'exp': 'MODE / Mode, ModeNum, Rsn', 'chart': 'c_timeline', 't': f['modes'][0][0],
                        'wexp': [_w('mode', lang, x=x, c=c) for x in o]})
    # Kütüphane soruları
    try:
        msgs = json.load(open(res('data', 'logmsgs.json'), encoding='utf-8'))
        core = [k for k, v in msgs.items() if v.get('core') and v['desc'].get(lang)]
        for _ in range(4):
            k = rnd.choice(core)
            o, i = _shuffle(k, rnd.sample(core, 6), rnd)
            out.append({'q': _q('msg', lang, d=msgs[k]['desc'][lang][:160]), 'opts': o, 'ans': i, 'exp': f"{k}: {msgs[k]['desc'][lang]}", 'lib': 'msgs', 'key': k,
                        'wexp': [_w('lib', lang, x=x, d=(msgs.get(x, {}).get('desc', {}).get(lang) or '')[:200]) for x in o]})
    except Exception:
        pass
    try:
        P = json.load(open(res('data', 'params.json'), encoding='utf-8'))['params']
        keyl = 'en' if lang == 'en' else lang
        names = [k for k, v in P.items() if v.get(keyl) and not v.get('old')]
        for _ in range(3):
            k = rnd.choice(names); d = P[k][keyl][1] or P[k][keyl][0]
            g = P[k].get('g', '')
            sib = [x for x in names if x.startswith(k.split('_')[0]) and x != k] or names
            o, i = _shuffle(k, rnd.sample(sib, min(6, len(sib))) + rnd.sample(names, 3), rnd)
            out.append({'q': _q('param', lang, d=d[:180]), 'opts': o, 'ans': i, 'exp': f'{k}: {P[k][keyl][0]}', 'lib': 'params', 'key': k,
                        'wexp': [_w('lib', lang, x=x, d=((P.get(x, {}).get(keyl) or P.get(x, {}).get('en') or ['', ''])[0])[:200]) for x in o]})
    except Exception:
        pass
    rnd.shuffle(out)
    return out[:n]
