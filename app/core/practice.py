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


def _q(k, lang, **a): return Q[k][LI[lang]].format(**a)


def _shuffle(correct, wrong, rnd):
    opts = [correct] + [w for w in dict.fromkeys(wrong) if w != correct][:3]
    rnd.shuffle(opts)
    return opts, opts.index(correct)


def generate(A=None, lang='tr', n=10, seed=None):
    rnd = random.Random(seed)
    out = []
    if A is not None:
        f = A.facts
        if 'takeoff_t' in f:
            c = f['takeoff_t']; w = [abs(c + d) for d in rnd.sample([-90, -45, -20, 25, 60, 120], 3)]
            o, i = _shuffle(fmt_t(c), [fmt_t(x) for x in w], rnd)
            out.append({'q': _q('takeoff', lang), 'opts': o, 'ans': i, 'exp': EXPL['takeoff'][LI[lang]] + f' ({fmt_t(c)})'})
        if 'land_t' in f:
            c = f['land_t']; w = [max(0, c + d) for d in rnd.sample([-120, -60, -30, 30, 75], 3)]
            o, i = _shuffle(fmt_t(c), [fmt_t(x) for x in w], rnd)
            out.append({'q': _q('landing', lang), 'opts': o, 'ans': i, 'exp': EXPL['landing'][LI[lang]] + f' ({fmt_t(c)})'})
        if 'max_alt' in f:
            c = f['max_alt']; w = [c * k for k in rnd.sample([0.4, 0.6, 1.5, 2.0, 2.6], 3)]
            o, i = _shuffle(f'{c:.0f} m', [f'{x:.0f} m' for x in w], rnd)
            out.append({'q': _q('maxalt', lang), 'opts': o, 'ans': i, 'exp': EXPL['maxalt'][LI[lang]]})
        if 'min_volt' in f:
            c = f['min_volt']; w = [c + d for d in rnd.sample([-3, -1.8, 1.5, 2.5, 4], 3)]
            o, i = _shuffle(f'{c:.1f} V', [f'{x:.1f} V' for x in w], rnd)
            out.append({'q': _q('minvolt', lang), 'opts': o, 'ans': i, 'exp': EXPL['minvolt'][LI[lang]]})
        kinds = ['normal', 'incident', 'crash', 'noflight']
        vk = A.verdict.get('kind', 'normal')
        o, i = _shuffle(T('v_' + vk, lang), [T('v_' + k, lang) for k in kinds], rnd)
        out.append({'q': _q('verdict', lang), 'opts': o, 'ans': i, 'exp': T('v_desc_' + vk, lang)})
        cause = (A.root or {}).get('cause')
        if cause and vk in ('crash', 'incident'):
            allc = ['gps', 'ekf', 'battery', 'radio', 'stall', 'vibration', 'compass', 'power', 'control']
            o, i = _shuffle(T('cause_' + cause, lang), [T('cause_' + x, lang) for x in rnd.sample(allc, 5)], rnd)
            out.append({'q': _q('cause', lang), 'opts': o, 'ans': i, 'exp': T('why_' + cause, lang)})
        if A.health:
            worst = min(A.health, key=lambda k: A.health[k]['score'])
            o, i = _shuffle(T('dom_' + worst, lang), [T('dom_' + k, lang) for k in rnd.sample(list(A.health), min(5, len(A.health)))], rnd)
            out.append({'q': _q('worst', lang), 'opts': o, 'ans': i,
                        'exp': f"{T('dom_' + worst, lang)}: {A.health[worst]['score']}/100"})
        if f.get('modes'):
            c = f['modes'][0][1]
            pool = ['MANUAL', 'FBWA', 'AUTO', 'RTL', 'LOITER', 'CRUISE', 'TAKEOFF', 'STABILIZE', 'GUIDED', 'QHOVER']
            o, i = _shuffle(c, rnd.sample(pool, 6), rnd)
            out.append({'q': _q('firstmode', lang), 'opts': o, 'ans': i, 'exp': 'MODE / Mode, ModeNum, Rsn'})
    # Kütüphane soruları
    try:
        msgs = json.load(open(res('data', 'logmsgs.json'), encoding='utf-8'))
        core = [k for k, v in msgs.items() if v.get('core') and v['desc'].get(lang)]
        for _ in range(4):
            k = rnd.choice(core)
            o, i = _shuffle(k, rnd.sample(core, 6), rnd)
            out.append({'q': _q('msg', lang, d=msgs[k]['desc'][lang][:160]), 'opts': o, 'ans': i, 'exp': f"{k}: {msgs[k]['desc'][lang]}"})
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
            out.append({'q': _q('param', lang, d=d[:180]), 'opts': o, 'ans': i, 'exp': f'{k}: {P[k][keyl][0]}'})
    except Exception:
        pass
    rnd.shuffle(out)
    return out[:n]
