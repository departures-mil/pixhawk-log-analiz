"""Uçuş bilgileri formu (log incelemeden önce sorulan sorular).

Kırım yaşandı mı, motor tipi (elektrikli: hücre sayısı / benzinli: cc), gövde tipi, otopilot modeli ve ek alanlar.
- Seçenekler Ayarlar > Log soruları bölümünden eklenip çıkarılabilir; soru tamamen kapatılabilir.
- detect(): logdan (parametreler, mesajlar, kart kimliği) offline tahmin.
- ai_fill(): internet ve kullanıcının kendi YZ anahtarı varsa boş kalan alanları yapay zekâ tahmin eder.
- Analiz bu cevaplara göre ayarlanır (profil, titreşim eşikleri, batarya denetimi, kırım kararı, kök neden notları).
"""
from __future__ import annotations
import json, re

LI = {'tr': 0, 'en': 1, 'ar': 2}


def _l(x, lang):
    if isinstance(x, str): return x
    return x[LI.get(lang, 0)]


Y = ('Evet', 'Yes', 'نعم'); N = ('Hayır', 'No', 'لا'); U = ('Bilmiyorum', 'Unknown', 'لا أعرف')

QUESTIONS = [
    {'id': 'crashed', 'kind': 'choice', 'icon': '💥', 'label': ('Kırım yaşandı mı?', 'Did a crash happen?', 'هل حدث تحطم؟'),
     'opts': [('yes', ('Evet, kırım oldu', 'Yes, it crashed', 'نعم، تحطمت')),
              ('hard', ('Sert iniş / hafif hasar', 'Hard landing / minor damage', 'هبوط عنيف / ضرر طفيف')),
              ('no', ('Hayır, sorunsuz indi', 'No, landed normally', 'لا، هبطت بشكل طبيعي')),
              ('unknown', U)]},
    {'id': 'power', 'kind': 'choice', 'icon': '⛽', 'label': ('Motor tipi', 'Power plant', 'نوع المحرك'),
     'opts': [('electric', ('Elektrikli', 'Electric', 'كهربائي')),
              ('gas', ('Benzinli (içten yanmalı)', 'Petrol / gas (ICE)', 'بنزين (احتراق داخلي)')),
              ('glow', ('Metanollü (glow / nitro)', 'Glow / nitro', 'ميثانول (نيترو)')),
              ('hybrid', ('Hibrit (benzinli itki + elektrikli dikey)', 'Hybrid (ICE pusher + electric lift)', 'هجين (دفع بنزين + رفع كهربائي)')),
              ('turbine', ('Türbin / jet', 'Turbine / jet', 'توربين / نفاث')),
              ('unknown', U)]},
    {'id': 'gas_cc', 'kind': 'edit', 'icon': '🛢', 'show_if': ('power', ('gas', 'glow', 'hybrid')),
     'label': ('Motor hacmi (cc)', 'Engine displacement (cc)', 'سعة المحرك (cc)'),
     'opts': [(x, x + ' cc') for x in ('10', '15', '20', '26', '30', '35', '40', '50', '55', '60', '62', '70', '85', '100', '110',
                                        '120', '150', '170', '200', '250')]},
    {'id': 'stroke', 'kind': 'choice', 'icon': '🔧', 'show_if': ('power', ('gas', 'hybrid')),
     'label': ('Zaman', 'Engine cycle', 'نوع الدورة'),
     'opts': [('2t', ('2 zamanlı', '2-stroke', 'ثنائي الشوط')), ('4t', ('4 zamanlı', '4-stroke', 'رباعي الشوط')),
              ('wankel', ('Wankel (döner)', 'Wankel (rotary)', 'محرك فانكل')), ('unknown', U)]},
    {'id': 'cells', 'kind': 'edit', 'icon': '🔋', 'show_if': ('power', ('electric', 'hybrid')),
     'label': ('Batarya hücre sayısı (S)', 'Battery cells (S)', 'عدد خلايا البطارية (S)'),
     'opts': [(f'{n}', f'{n}S') for n in (2, 3, 4, 5, 6, 8, 10, 12, 14, 18)]},
    {'id': 'airframe', 'kind': 'choice', 'icon': '✈', 'label': ('Gövde / model tipi', 'Airframe type', 'نوع هيكل الطائرة'),
     'opts': [('conventional', ('Sabit kanat – normal kuyruk', 'Fixed wing – conventional tail', 'جناح ثابت – ذيل تقليدي')),
              ('ttail', ('Sabit kanat – T kuyruk', 'Fixed wing – T-tail', 'جناح ثابت – ذيل T')),
              ('vtail', ('Sabit kanat – V kuyruk (V-tail)', 'Fixed wing – V-tail', 'جناح ثابت – ذيل V')),
              ('elevon', ('Uçan kanat / elevon', 'Flying wing / elevon', 'جناح طائر / إيليفون')),
              ('twinboom', ('Çift kuyruk kirişli (twin boom)', 'Twin boom', 'ذيل مزدوج')),
              ('glider', ('Planör / motorlu planör', 'Glider / motor glider', 'طائرة شراعية')),
              ('quadplane', ('VTOL – QuadPlane', 'VTOL – QuadPlane', 'VTOL – كوادبلين')),
              ('tiltrotor', ('VTOL – tilt-rotor', 'VTOL – tilt-rotor', 'VTOL – مراوح قابلة للإمالة')),
              ('tailsitter', ('VTOL – tail-sitter', 'VTOL – tail-sitter', 'VTOL – تيل سيتر')),
              ('quad', ('Multikopter – 4 motor (quad)', 'Multicopter – quad', 'رباعي المراوح')),
              ('hexa', ('Multikopter – 6 motor (hexa)', 'Multicopter – hexa', 'سداسي المراوح')),
              ('octa', ('Multikopter – 8 motor (octa)', 'Multicopter – octa', 'ثماني المراوح')),
              ('x8', ('Multikopter – koaksiyel X8', 'Multicopter – coaxial X8', 'ثماني محوري X8')),
              ('y6', ('Multikopter – Y6', 'Multicopter – Y6', 'Y6')),
              ('tri', ('Multikopter – tri', 'Multicopter – tri', 'ثلاثي المراوح')),
              ('heli', ('Helikopter', 'Helicopter', 'مروحية')),
              ('rover', ('Kara aracı', 'Ground rover', 'مركبة أرضية')),
              ('boat', ('Tekne', 'Boat', 'قارب')),
              ('sub', ('Denizaltı (ArduSub)', 'Submarine (ArduSub)', 'غواصة')),
              ('unknown', U)]},
    {'id': 'autopilot', 'kind': 'edit', 'icon': '🧠', 'label': ('Otopilot (marka / model)', 'Autopilot (brand / model)', 'الطيار الآلي (الماركة / الطراز)'),
     'opts': [(x, x) for x in ('Pixhawk 1 (FMUv2)', 'Pixhawk 1 2MB (FMUv3)', 'Pixhawk 2.1 / Cube Black', 'Cube Purple', 'Cube Yellow',
                               'Cube Orange', 'Cube Orange+', 'Cube Blue', 'Cube Red', 'Pixhawk 4', 'Pixhawk 4 Mini', 'Pixhawk 5X',
                               'Pixhawk 6C', 'Pixhawk 6C Mini', 'Pixhawk 6X', 'Pixhawk 6X Pro', 'Holybro Durandal', 'Holybro Kakute H7',
                               'CUAV V5+', 'CUAV V5 Nano', 'CUAV X7 / X7+', 'CUAV Nora', 'CUAV Pixhack', 'mRo Pixracer', 'mRo Control Zero',
                               'Matek H743 (Wing/Slim/Mini)', 'Matek F765-Wing', 'Matek F405-Wing', 'SpeedyBee F405 Wing', 'Omnibus F4',
                               'Navio2 (Raspberry Pi)', 'Diğer / Other')]},
    {'id': 'gps', 'kind': 'edit', 'icon': '🛰', 'label': ('GPS / pusula modülü', 'GPS / compass module', 'وحدة GPS / البوصلة'),
     'opts': [(x, x) for x in ('Here 2', 'Here 3', 'Here 3+', 'Here 4', 'Holybro M8N', 'Holybro M9N', 'Holybro M10', 'Holybro H-RTK F9P',
                               'CUAV NEO 3', 'CUAV NEO 3 Pro', 'CUAV C-RTK 2', 'Matek M10Q-5883', 'Beitian BN-880', 'Diğer / Other')]},
    {'id': 'airspeed', 'kind': 'choice', 'icon': '🌬', 'label': ('Hava hızı sensörü', 'Airspeed sensor', 'حساس السرعة الجوية'),
     'opts': [('digital', ('Var – dijital (MS4525 / DLVR / SDP3x)', 'Yes – digital (MS4525 / DLVR / SDP3x)', 'نعم – رقمي')),
              ('analog', ('Var – analog', 'Yes – analog', 'نعم – تماثلي')), ('no', ('Yok', 'None', 'لا يوجد')), ('unknown', U)]},
    {'id': 'prop', 'kind': 'text', 'icon': '🌀', 'label': ('Pervane ölçüsü', 'Propeller size', 'مقاس المروحة'), 'ph': '22x10, 15x5.5 …'},
    {'id': 'weight', 'kind': 'text', 'icon': '⚖', 'label': ('Kalkış ağırlığı (kg)', 'Take-off weight (kg)', 'وزن الإقلاع (كغ)'), 'ph': '12.5'},
    {'id': 'purpose', 'kind': 'choice', 'icon': '🎯', 'label': ('Uçuşun amacı', 'Purpose of flight', 'غرض الرحلة'),
     'opts': [('maiden', ('İlk uçuş', 'Maiden flight', 'الرحلة الأولى')), ('test', ('Test uçuşu', 'Test flight', 'رحلة اختبار')),
              ('tuning', ('Ayar / AUTOTUNE', 'Tuning / AUTOTUNE', 'ضبط / AUTOTUNE')), ('mission', ('Görev', 'Mission', 'مهمة')),
              ('training', ('Eğitim', 'Training', 'تدريب')), ('demo', ('Gösteri', 'Demonstration', 'عرض')), ('unknown', U)]},
    {'id': 'pilot', 'kind': 'text', 'icon': '👤', 'label': ('Pilot / operatör', 'Pilot / operator', 'الطيار / المشغل')},
    {'id': 'location', 'kind': 'text', 'icon': '📍', 'label': ('Uçuş yeri', 'Flight location', 'مكان الطيران')},
    {'id': 'notes', 'kind': 'text', 'icon': '📝', 'label': ('Ne gözlemlediniz? (kısa not)', 'What did you observe? (short note)', 'ماذا لاحظت؟ (ملاحظة قصيرة)')},
]
QBYID = {q['id']: q for q in QUESTIONS}

PROFILE_OF = {'conventional': 'plane', 'ttail': 'plane', 'vtail': 'plane', 'elevon': 'plane', 'twinboom': 'plane', 'glider': 'plane',
              'quadplane': 'vtol', 'tiltrotor': 'vtol', 'tailsitter': 'vtol', 'quad': 'copter', 'hexa': 'copter', 'octa': 'copter',
              'x8': 'copter', 'y6': 'copter', 'tri': 'copter', 'heli': 'heli', 'rover': 'rover', 'boat': 'rover', 'sub': 'rover'}


# ------------------------------------------------------------------ ayarlar
def conf(settings):
    c = dict(settings.get('fi') or {})
    c.setdefault('ask', True); c.setdefault('ai_fill', True)
    c.setdefault('off', []); c.setdefault('add', {}); c.setdefault('del', {})
    return c


def options(qid, settings, lang='tr'):
    """Sorunun seçenekleri [(id, etiket)] — Ayarlar'daki ekle/çıkar uygulanmış."""
    q = QBYID[qid]; c = conf(settings)
    dele = set(c['del'].get(qid, []))
    out = [(k, _l(lab, lang)) for k, lab in q.get('opts', []) if k not in dele]
    for x in c['add'].get(qid, []):
        if x and x not in dele and all(x != k for k, _ in out): out.append((x, x))
    return out


def questions(settings):
    off = set(conf(settings)['off'])
    return [q for q in QUESTIONS if q['id'] not in off]


def label(qid, lang='tr'):
    return _l(QBYID[qid]['label'], lang)


def value_label(qid, val, lang='tr'):
    q = QBYID.get(qid)
    if not q or val in (None, ''): return ''
    for k, lab in q.get('opts', []):
        if k == val: return _l(lab, lang)
    return str(val)


def rows(info, lang='tr'):
    """Rapor/özet için [(soru, cevap)] — boş ve 'bilinmiyor' olanlar atlanır."""
    out = []
    for q in QUESTIONS:
        v = (info or {}).get(q['id'])
        if v in (None, '', 'unknown'): continue
        si = q.get('show_if')
        if si and (info or {}).get(si[0]) not in si[1]: continue
        out.append((label(q['id'], lang), value_label(q['id'], v, lang)))
    return out


# --------------------------------------------------------- logdan tahmin
BOARD_IDS = {9: 'Pixhawk 1 2MB (FMUv3)', 11: 'Pixhawk 4', 50: 'Pixhawk 4', 120: 'Cube Yellow', 140: 'Cube Orange',
             1063: 'Cube Orange+', 53: 'Pixhawk 6X', 56: 'Pixhawk 6C', 1013: 'Matek H743 (Wing/Slim/Mini)'}
BOARD_PAT = [(r'cube\s*orange\s*(plus|\+)|cubeorangeplus', 'Cube Orange+'), (r'cube\s*orange', 'Cube Orange'),
             (r'cube\s*yellow', 'Cube Yellow'), (r'cube\s*purple', 'Cube Purple'), (r'cube\s*blue', 'Cube Blue'), (r'cube\s*red', 'Cube Red'),
             (r'cube\s*black|pixhawk\s*2', 'Pixhawk 2.1 / Cube Black'), (r'pixhawk\s*6x', 'Pixhawk 6X'),
             (r'pixhawk\s*6c[\s-]*mini', 'Pixhawk 6C Mini'), (r'pixhawk\s*6c', 'Pixhawk 6C'), (r'pixhawk\s*5x', 'Pixhawk 5X'),
             (r'pixhawk\s*4[\s-]*mini|ph4[\s-]*mini', 'Pixhawk 4 Mini'), (r'pixhawk\s*4|fmuv5', 'Pixhawk 4'), (r'durandal', 'Holybro Durandal'),
             (r'kakuteh7', 'Holybro Kakute H7'), (r'cuav[\s-]*x7|\bx7\b', 'CUAV X7 / X7+'), (r'nora', 'CUAV Nora'),
             (r'cuav[\s-]*v5\s*nano|v5nano', 'CUAV V5 Nano'), (r'cuav[\s-]*v5|cuavv5', 'CUAV V5+'), (r'pixracer', 'mRo Pixracer'),
             (r'controlzero', 'mRo Control Zero'), (r'matekh743|matek\s*h743', 'Matek H743 (Wing/Slim/Mini)'),
             (r'matekf765|matek\s*f765', 'Matek F765-Wing'), (r'matekf405|matek\s*f405', 'Matek F405-Wing'),
             (r'speedybee', 'SpeedyBee F405 Wing'), (r'omnibus', 'Omnibus F4'), (r'navio', 'Navio2 (Raspberry Pi)'),
             (r'pixhawk\s*1[\s-]*1m|fmuv2', 'Pixhawk 1 (FMUv2)'), (r'pixhawk\s*1|fmuv3', 'Pixhawk 1 2MB (FMUv3)')]


def detect(L):
    """Logdan cevap tahmini: (cevaplar, kaynak). Bulunamayan alan boş kalır."""
    P = L.params; v = L.vehicle; out = {}
    def p(k, d=0):
        try: return float(P.get(k, d) or 0)
        except Exception: return d
    # otopilot
    txt = ' '.join(x for _, x in L.texts[:120]).lower() + ' ' + str(getattr(L, 'version', '') or '').lower()
    for pat, name in BOARD_PAT:
        if re.search(pat, txt): out['autopilot'] = name; break
    if 'autopilot' not in out:
        try:
            b = int(float(L.board)) if str(getattr(L, 'board', '') or '').strip() else None
            if b in BOARD_IDS: out['autopilot'] = BOARD_IDS[b]
        except Exception: pass
    # gövde
    fn = {int(p(f'SERVO{i}_FUNCTION')) for i in range(1, 17)}
    if v == 'Plane':
        if p('Q_ENABLE') >= 1:
            out['airframe'] = 'tailsitter' if p('Q_TAILSIT_ENABLE') >= 1 else ('tiltrotor' if p('Q_TILT_ENABLE') >= 1 or p('Q_TILT_MASK') > 0 else 'quadplane')
        elif fn & {79, 80}: out['airframe'] = 'vtail'
        elif fn & {77, 78}: out['airframe'] = 'elevon'
        elif 19 in fn or 4 in fn: out['airframe'] = 'conventional'
    elif v == 'Copter':
        if any(k.startswith(('H_SW_', 'H_COL_')) for k in P) or 'heli' in str(getattr(L, 'version', '')).lower():
            out['airframe'] = 'heli'
        else:
            out['airframe'] = {1: 'quad', 2: 'hexa', 3: 'octa', 4: 'x8', 5: 'y6', 7: 'tri', 6: 'heli', 11: 'heli', 13: 'heli'}.get(int(p('FRAME_CLASS', 1)), 'quad')
    elif v == 'Rover':
        out['airframe'] = 'boat' if int(p('FRAME_CLASS')) == 2 else 'rover'
    elif v == 'Sub':
        out['airframe'] = 'sub'
    # motor
    ice = p('ICE_ENABLE') >= 1
    if ice: out['power'] = 'hybrid' if p('Q_ENABLE') >= 1 else 'gas'
    b = L.s('BAT')
    if b.has('Volt'):
        try:
            import numpy as np
            vm = float(np.nanmax(b['Volt']))
            if 5 < vm < 110:      # 1S..24S; daha büyükse sensör ölçeği hatalı
                n = max(1, round(vm / 4.2))
                if not ice: out.setdefault('power', 'electric')
                if out.get('power') in ('electric', 'hybrid'): out['cells'] = str(n)
        except Exception: pass
    # hava hızı
    if v == 'Plane':
        at = P.get('ARSPD_TYPE', P.get('ARSPD1_TYPE'))
        if at is not None:
            at = int(float(at)); out['airspeed'] = 'no' if at == 0 else ('analog' if at == 2 else 'digital')
    # kırım (otopilotun kendi kaydı)
    st = L.s('STAT')
    hard = any(s == 12 and c != 0 for _, s, c in L.errors) or any('crash' in x.lower() for _, x in L.texts)
    try:
        if st.has('Crash') and float(st['Crash'].max()) > 0: hard = True
    except Exception: pass
    if hard: out['crashed'] = 'yes'
    return out, {k: 'log' for k in out}


# ------------------------------------------------------------ YZ ile tahmin
def ai_fill(L, settings, usage, current):
    """Boş alanları kullanıcının kendi YZ anahtarıyla tahmin eder. Sadece kesin çıkarım yapılanlar döner."""
    from . import ai as AI
    if not AI.available(settings): return {}
    want = [q['id'] for q in QUESTIONS if q['id'] in ('airframe', 'power', 'gas_cc', 'cells', 'autopilot', 'airspeed', 'gps')
            and current.get(q['id']) in (None, '', 'unknown')]
    if not want: return {}
    keys = sorted(k for k in L.params if k.startswith(('Q_ENABLE', 'Q_FRAME', 'Q_TILT', 'Q_TAILSIT', 'FRAME_', 'ICE_', 'SERVO', 'ARSPD',
                                                          'BATT_', 'GPS_TYPE', 'COMPASS_DEV_ID', 'BRD_', 'RPM', 'EFI_', 'MOT_PWM', 'THR_')))[:160]
    ctx = {'vehicle': L.vehicle, 'firmware': L.version, 'board_id': getattr(L, 'board', ''),
           'messages': [x for _, x in L.texts[:60]], 'params': {k: L.params[k] for k in keys}}
    choices = {q: [k for k, _ in options(q, settings, 'en')] for q in want}
    prompt = ('From this ArduPilot log context, infer ONLY these fields: ' + ', '.join(want) + '.\n'
              'Allowed values (pick exactly one or "unknown"; gas_cc/cells/autopilot/gps may also be another short value):\n'
              + json.dumps(choices, ensure_ascii=False) + '\nContext:\n' + json.dumps(ctx, ensure_ascii=False, default=str)[:14000]
              + '\nAnswer with a single JSON object {field: value}. Use "unknown" when not sure.')
    txt = AI.chat(settings, usage, 'You are an ArduPilot expert. Reply with JSON only.', prompt, max_tokens=800)
    m = re.search(r'\{.*\}', txt or '', re.S)
    if not m: return {}
    try: d = json.loads(m.group(0))
    except Exception: return {}
    return {k: str(v) for k, v in d.items() if k in want and v not in (None, '', 'unknown')}


# --------------------------------------------------- analize etkisi
def profile_for(info):
    return PROFILE_OF.get((info or {}).get('airframe') or '')


def is_ice(info):
    return (info or {}).get('power') in ('gas', 'glow', 'turbine')


def cc(info):
    try: return float(re.sub(r'[^0-9.]', '', str((info or {}).get('gas_cc') or '')) or 0)
    except Exception: return 0.0


def adjust_thresholds(th, info):
    """Benzinli/metanollü motorlarda doğal titreşim yüksektir: eşikler motor hacmine göre yükseltilir."""
    info = info or {}
    if info.get('power') in ('gas', 'glow', 'hybrid'):
        k = 1.0 if info.get('power') != 'hybrid' else 0.6
        c = cc(info)
        add_w = (8 + (5 if c >= 50 else 0) + (5 if c >= 100 else 0)) * k
        add_b = (12 + (8 if c >= 50 else 0) + (8 if c >= 100 else 0)) * k
        if info.get('stroke') == '2t': add_w += 3 * k; add_b += 4 * k
        th['vibe_warn'] += add_w; th['vibe_bad'] += add_b
    return th
