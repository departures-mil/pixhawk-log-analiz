"""Motor Yönleri Bankası öğretici ayrıntısı (v1.1.20): her çerçeve için kurulum parametreleri, motor çıkışları,
logda sinyalin okunacağı alanlar ve adım adım log okuma. TR/EN/AR.

Çıkış eşlemesi: açık log varsa SERVOn_FUNCTION parametrelerinden GERÇEK çıkış; yoksa önerilen örnek
(QuadPlane: kaldırma motorları SERVO5'ten başlar, çünkü 1–4 uçağın yüzeyleri/gazıdır; kopter: SERVO1'den).
Log alanı: çıkış n → RCOU.Cn (1–14), RCO2.Cn (15–18), RCO3.Cn (19–32); ESC telemetrisi ESC[n-1] (BLHeli/DShot).
"""
from __future__ import annotations
import html
from . import motororder as MO

E = html.escape
L3 = MO.L3


def _t(v, lg):
    return v[L3.get(lg, 0)] if isinstance(v, (tuple, list)) else v


T = {
    's1': ('1. Bu çerçeveyi tanıyın', '1. Get to know this frame', '1. تعرّف على هذا الهيكل'),
    's2': ('2. Kurulum parametreleri', '2. Setup parameters', '2. معاملات الإعداد'),
    's3': ('3. Motor çıkışları ve logda okunacak alanlar', '3. Motor outputs and the log fields to read', '3. مخارج المحركات والحقول التي تُقرأ في السجل'),
    's4': ('4. Logda adım adım nasıl okunur', '4. How to read it in the log, step by step', '4. كيف تقرأه في السجل خطوة بخطوة'),
    's5': ('5. Uçmadan önce kontrol', '5. Check before flying', '5. فحص قبل الطيران'),
    'p_cols': (('Parametre', 'Değer', 'Ne yapar'), ('Parameter', 'Value', 'What it does'), ('المعامل', 'القيمة', 'ماذا يفعل')),
    'p_log': ('Logdaki değer', 'Value in log', 'القيمة في السجل'),
    'm_cols': (('Motor', 'SERVOn_FUNCTION', 'Çıkış', 'Logda sinyal', 'ESC telemetrisi', 'Konum', 'Dönüş', 'Test'),
               ('Motor', 'SERVOn_FUNCTION', 'Output', 'Signal in log', 'ESC telemetry', 'Position', 'Rotation', 'Test'),
               ('المحرك', 'SERVOn_FUNCTION', 'المخرج', 'الإشارة في السجل', 'قياس ESC', 'الموضع', 'الدوران', 'اختبار')),
    'ex': ('örnek', 'example', 'مثال'), 'real': ('bu logda', 'in this log', 'في هذا السجل'), 'none': ('atanmamış!', 'not assigned!', 'غير مُسند!'),
    'ex_note': ('Çıkış sütunu öneridir: hangi SERVO çıkışını kullanacağınız serbesttir, önemli olan SERVOn_FUNCTION değeridir. '
                'Bir log açıksa tablo o uçağın gerçek eşlemesini gösterir.',
                'The output column is a suggestion: you may use any SERVO output, what matters is the SERVOn_FUNCTION value. '
                'With a log open, the table shows that aircraft\'s real mapping.',
                'عمود المخرج اقتراح: يمكنك استخدام أي مخرج SERVO، المهم هو قيمة SERVOn_FUNCTION. '
                'عند فتح سجل يعرض الجدول الإسناد الحقيقي لتلك الطائرة.'),
    'real_note': ('Tablo açık logun parametrelerinden okundu (gerçek çıkışlar).', 'Table read from the open log\'s parameters (real outputs).',
                  'قُرئ الجدول من معاملات السجل المفتوح (المخارج الحقيقية).'),
    'open_lb': ('📈 Bu motorların sinyallerini Log Gezgini\'nde aç', '📈 Open these motor signals in the Log Browser', '📈 افتح إشارات هذه المحركات في مستعرض السجل'),
    'open_esc': ('📈 ESC devirlerini (RPM) aç', '📈 Open ESC RPM', '📈 افتح دورات ESC'),
    'no_sig': ('Bu sinyaller açık logda yok (RCOU/ESC kaydı kapalı olabilir: LOG_BITMASK).', 'These signals are not in the open log (RCOU/ESC logging may be off: LOG_BITMASK).',
               'هذه الإشارات غير موجودة في السجل المفتوح (قد يكون تسجيل RCOU/ESC معطلاً: LOG_BITMASK).'),
    'need_log': ('(önce bir log açın)', '(open a log first)', '(افتح سجلاً أولاً)'),
}

# ------------------------------------------------------------------ parametre açıklamaları
PX = {
    'Q_ENABLE': ('QuadPlane özelliğini açar. 1 yaptıktan sonra otopilotu yeniden başlatın ve parametre listesini yenileyin; Q_ parametreleri ancak o zaman görünür.',
                 'Turns QuadPlane on. After setting 1, reboot the autopilot and refresh the parameter list; the Q_ parameters only appear then.',
                 'يفعّل QuadPlane. بعد ضبطه على 1 أعد تشغيل الطيار الآلي وحدّث قائمة المعاملات؛ لا تظهر معاملات Q_ إلا بعدها.'),
    'CLASS': ('Çerçeve sınıfı: kaç motor ve hangi düzen (1 quad, 2 hexa, 3 octa, 4 X8, 5 Y6, 7 tri, 10 tailsitter, 12 dodecahexa, 14 deca).',
              'Frame class: how many motors and which layout (1 quad, 2 hexa, 3 octa, 4 X8, 5 Y6, 7 tri, 10 tailsitter, 12 dodecahexa, 14 deca).',
              'فئة الهيكل: عدد المحركات وترتيبها (1 رباعي، 2 سداسي، 3 ثماني، 4 X8، 5 Y6، 7 ثلاثي، 10 tailsitter، 12 dodecahexa، 14 عشاري).'),
    'TYPE': ('Çerçeve tipi: motorların gövdeye göre dizilişi ve numaralandırma (0 +, 1 X, 2 V, 3 H, 4 V kuyruk …). Resimdeki numaralar bu değere göredir.',
             'Frame type: how the motors sit on the frame and are numbered (0 +, 1 X, 2 V, 3 H, 4 V-tail …). The numbers in the picture follow this value.',
             'نوع الهيكل: توزيع المحركات وترقيمها (0 +، 1 X، 2 V، 3 H، 4 ذيل V …). أرقام الصورة تتبع هذه القيمة.'),
    'FUNC': ('Bu çıkışa hangi motorun bağlı olduğunu söyler: 33 = Motor1, 34 = Motor2 … (Motor n = 32 + n). ESC kablosunu bu çıkışa takın.',
             'Tells which motor is on this output: 33 = Motor1, 34 = Motor2 … (Motor n = 32 + n). Plug the ESC lead into this output.',
             'يحدد أي محرك على هذا المخرج: 33 = Motor1، 34 = Motor2 … (Motor n = 32 + n). صل سلك ESC بهذا المخرج.'),
    'PWM_TYPE': ('ESC haberleşme türü: 0 normal PWM (ESC kalibrasyonu gerekir), 4–7 DShot150/300/600/1200 (kalibrasyon gerekmez, telemetri verebilir).',
                 'ESC protocol: 0 normal PWM (needs ESC calibration), 4–7 DShot150/300/600/1200 (no calibration, can give telemetry).',
                 'بروتوكول ESC: 0 PWM عادي (يحتاج معايرة ESC)، 4–7 DShot150/300/600/1200 (بلا معايرة، ويمكنه إرسال القياسات).'),
    'PWM_MIN': ('Motor durukken gönderilen PWM. ESC kalibrasyonundaki alt değerle aynı olmalı.', 'PWM sent when the motor is stopped. Must match the low end of the ESC calibration.',
                'إشارة PWM عند توقف المحرك. يجب أن تطابق الحد الأدنى في معايرة ESC.'),
    'PWM_MAX': ('Tam gazda gönderilen PWM. Logda motor sürekli bu değere dayanıyorsa itki yetmiyor demektir.',
                'PWM sent at full throttle. If a motor sits at this value in the log, it is running out of thrust.',
                'إشارة PWM عند الخانق الكامل. إذا بقي محرك عند هذه القيمة في السجل فالدفع غير كافٍ.'),
    'SPIN_ARM': ('Arm edilince motorların döneceği gaz (0–1). Hepsi aynı anda ve düzgün dönmeli.', 'Throttle the motors spin at when armed (0–1). All must start together and run smoothly.',
                 'الخانق الذي تدور به المحركات عند التسليح (0–1). يجب أن تبدأ معاً وتدور بسلاسة.'),
    'SPIN_MIN': ('Uçuşta hiçbir motorun inmeyeceği en düşük gaz; SPIN_ARM\'dan biraz yüksek olmalı (durma/desync önlenir).',
                 'Lowest throttle any motor drops to in flight; a little above SPIN_ARM (prevents stalls/desync).',
                 'أدنى خانق لأي محرك أثناء الطيران؛ أعلى قليلاً من SPIN_ARM (يمنع التوقف/فقدان التزامن).'),
    'SPIN_MAX': ('Motorun doyduğu üst sınır (genelde 0.95).', 'Upper limit where the motor saturates (usually 0.95).', 'الحد الأعلى لتشبع المحرك (عادة 0.95).'),
    'HOVER': ('Askıda (hover) ortalama gaz. Logda gerçek askı gazı bundan çok farklıysa ağırlık/pervane uyumsuz.',
              'Average throttle in hover. If the real hover throttle in the log is far from this, weight/props are mismatched.',
              'متوسط الخانق في التحويم. إذا اختلف الخانق الحقيقي في السجل كثيراً فالوزن/المراوح غير متناسبة.'),
    'EXPO': ('Motor itki eğrisi düzeltmesi (genelde 0.55–0.75).', 'Motor thrust-curve linearisation (usually 0.55–0.75).', 'تصحيح منحنى دفع المحرك (عادة 0.55–0.75).'),
    'BLH': ('BLHeli/DShot ESC telemetrisinin ve geçişli ayarın açık olduğu çıkışların bit maskesi; ESC[n] logu bununla gelir.',
            'Bitmask of outputs with BLHeli/DShot telemetry and passthrough; the ESC[n] log comes from this.',
            'قناع بتات المخارج التي عليها قياسات BLHeli/DShot؛ سجل ESC[n] يأتي من هنا.'),
    'TILT_MASK': ('Hangi motorların eğildiği (bit maskesi): 1 = Motor1, 2 = Motor2, 3 = ikisi.', 'Which motors tilt (bitmask): 1 = Motor1, 2 = Motor2, 3 = both.',
                  'أي المحركات تميل (قناع بتات): 1 = Motor1، 2 = Motor2، 3 = كلاهما.'),
    'TILT_TYPE': ('Eğme türü: 0 sürekli, 1 ikili (aç/kapa), 2 vektörlü yaw, 3 bicopter.', 'Tilt type: 0 continuous, 1 binary, 2 vectored yaw, 3 bicopter.',
                  'نوع الإمالة: 0 مستمر، 1 ثنائي، 2 انعراج موجّه، 3 bicopter.'),
    'TILT_SERVO': ('Eğme servosu çıkışı: 41 TiltMotorsFront, ya da sol/sağ ayrı ise 75 TiltMotorFrontLeft / 76 TiltMotorFrontRight.',
                   'Tilt servo output: 41 TiltMotorsFront, or 75 TiltMotorFrontLeft / 76 TiltMotorFrontRight for separate left/right.',
                   'مخرج مؤازر الإمالة: 41 TiltMotorsFront، أو 75 TiltMotorFrontLeft / 76 TiltMotorFrontRight للأيسر/الأيمن.'),
    'TAILSIT': ('Tailsitter kipini açar (uçak burnu yukarıda kalkar/iner).', 'Enables tailsitter mode (takes off and lands nose-up).',
                'يفعّل وضع tailsitter (إقلاع وهبوط والأنف للأعلى).'),
    'ELEVON': ('Elevonlar: 77 ElevonLeft, 78 ElevonRight. Askıda pitch/yaw bunlarla yapılır.', 'Elevons: 77 ElevonLeft, 78 ElevonRight. In hover pitch/yaw come from them.',
               'الإيلفونات: 77 ElevonLeft، 78 ElevonRight. في التحويم يأتي الميل/الانعراج منها.'),
    'THR_LR': ('Sol/sağ itki: 73 ThrottleLeft, 74 ThrottleRight.', 'Left/right thrust: 73 ThrottleLeft, 74 ThrottleRight.', 'الدفع الأيسر/الأيمن: 73 ThrottleLeft، 74 ThrottleRight.'),
    'FWD': ('İleri uçuş motoru (Throttle). QuadPlane\'de kaldırma motorlarından ayrıdır.', 'Forward-flight motor (Throttle). On a QuadPlane it is separate from the lift motors.',
            'محرك الطيران الأمامي (Throttle). في QuadPlane منفصل عن محركات الرفع.'),
    'TRI_SV': ('Kuyruk servosu (Motor7 = 39): arka motoru yatırarak yaw verir.', 'Tail servo (Motor7 = 39): tilts the rear motor to give yaw.',
               'مؤازر الذيل (Motor7 = 39): يميل المحرك الخلفي لإعطاء الانعراج.'),
    'TRI_REV': ('Kuyruk servosu yönü (1 ya da -1): sağa yaw komutunda motor doğru yöne yatmalı.', 'Tail servo direction (1 or -1): on a right-yaw command the motor must tilt the right way.',
                'اتجاه مؤازر الذيل (1 أو -1): عند أمر انعراج يميني يجب أن يميل المحرك بالاتجاه الصحيح.'),
    'TRI_ANG': ('Kuyruk servosunun en büyük yatma açısı (derece).', 'Maximum tilt angle of the tail servo (degrees).', 'أقصى زاوية لمؤازر الذيل (درجات).'),
    'THR_MAX': ('En yüksek gaz yüzdesi. Logda gaz sürekli buna dayanıyorsa güç yetmiyor.', 'Maximum throttle percentage. If throttle sits here in the log, power is short.',
                'أقصى نسبة خانق. إذا بقي الخانق عنده في السجل فالقدرة غير كافية.'),
    'THR_MIN': ('En düşük gaz yüzdesi (elektrikli uçakta 0).', 'Minimum throttle percentage (0 on electric planes).', 'أدنى نسبة خانق (0 في الطائرات الكهربائية).'),
    'SLEW': ('Gazın saniyedeki en büyük değişimi (%).', 'Maximum throttle change per second (%).', 'أقصى تغير للخانق في الثانية (%).'),
    'RUDD_DT': ('Dümen komutunun iki motor arasındaki farka karışma oranı (diferansiyel itki).', 'How much rudder is mixed into the difference between the two motors (differential thrust).',
                'نسبة مزج الدفة في الفرق بين المحركين (دفع تفاضلي).'),
    'REV': ('İleri komutta bir taraf geri dönüyorsa o çıkışı ters çevirin.', 'If one side runs backwards on a forward command, reverse that output.',
            'إذا دار جانب للخلف عند أمر الأمام فاعكس ذلك المخرج.'),
    'ROV_THR': ('En yüksek gaz yüzdesi.', 'Maximum throttle percentage.', 'أقصى نسبة خانق.'),
}


def _params(fr, P, lg):
    """[(parametre, önerilen değer, açıklama)]"""
    g = fr['group']; k = fr['kind']; c = fr.get('cls'); ty = fr.get('type')
    nmot = len([m for m in fr['motors'] if isinstance(m['n'], int)])
    out = []
    if g == 'qp':
        out.append(('Q_ENABLE', '1', PX['Q_ENABLE']))
        out.append(('Q_FRAME_CLASS', str(c), PX['CLASS']))
        if k == 'matrix': out.append(('Q_FRAME_TYPE', str(ty), PX['TYPE']))
        if k == 'tailsitter':
            out += [('Q_TAILSIT_ENABLE', '1', PX['TAILSIT']), ('SERVOn_FUNCTION', '73 / 74', PX['THR_LR']), ('SERVOn_FUNCTION', '77 / 78', PX['ELEVON'])]
        else:
            out.append(('SERVOn_FUNCTION', f'33 … {32 + max(m["n"] for m in fr["motors"] if isinstance(m["n"], int))}', PX['FUNC']))
        if k == 'tri':
            out += [('Q_TILT_MASK', '3', PX['TILT_MASK']), ('Q_TILT_TYPE', '0 / 1 / 2', PX['TILT_TYPE']), ('SERVOn_FUNCTION', '41 / 75 / 76', PX['TILT_SERVO'])]
        out.append(('SERVO3_FUNCTION', '70', PX['FWD']))
        pre = 'Q_M_'
    elif g == 'mc':
        out.append(('FRAME_CLASS', str(c), PX['CLASS']))
        if k == 'matrix': out.append(('FRAME_TYPE', str(ty) if ty is not None and ty >= 0 else '—', PX['TYPE']))
        out.append(('SERVOn_FUNCTION', f'33 … {32 + max(m["n"] for m in fr["motors"] if isinstance(m["n"], int))}', PX['FUNC']))
        if k == 'tri':
            out += [('SERVO7_FUNCTION', '39', PX['TRI_SV']), ('MOT_YAW_SV_REV', '1 / -1', PX['TRI_REV']), ('MOT_YAW_SV_ANGLE', '30', PX['TRI_ANG'])]
        pre = 'MOT_'
    else:
        if fr['id'] == 'pl_single':
            return [('SERVO3_FUNCTION', '70', PX['FWD']), ('THR_MAX', '100', PX['THR_MAX']), ('THR_MIN', '0', PX['THR_MIN']),
                    ('THR_SLEWRATE', '100', PX['SLEW']), ('SERVO3_MIN / SERVO3_MAX', '1000 / 2000', PX['PWM_MIN']), ('SERVO_BLH_MASK', '—', PX['BLH'])]
        if fr['id'] == 'pl_twin':
            return [('SERVOn_FUNCTION', '73 / 74', PX['THR_LR']), ('RUDD_DT_GAIN', '10', PX['RUDD_DT']), ('THR_MAX', '100', PX['THR_MAX']),
                    ('THR_SLEWRATE', '100', PX['SLEW']), ('SERVO_BLH_MASK', '—', PX['BLH'])]
        return [('SERVO1_FUNCTION', '73', PX['THR_LR']), ('SERVO3_FUNCTION', '74', PX['THR_LR']), ('MOT_PWM_TYPE', '0', PX['PWM_TYPE']),
                ('MOT_THR_MAX', '100', PX['ROV_THR']), ('MOT_SLEWRATE', '100', PX['SLEW']), ('SERVO1_REVERSED / SERVO3_REVERSED', '0 / 1', PX['REV'])]
    out += [(pre + 'PWM_TYPE', '0 / 4–7', PX['PWM_TYPE']), (pre + 'PWM_MIN', '1000', PX['PWM_MIN']), (pre + 'PWM_MAX', '2000', PX['PWM_MAX']),
            (pre + 'SPIN_ARM', '0.10', PX['SPIN_ARM']), (pre + 'SPIN_MIN', '0.15', PX['SPIN_MIN']), (pre + 'SPIN_MAX', '0.95', PX['SPIN_MAX']),
            (pre + 'THST_HOVER', '0.35', PX['HOVER']), (pre + 'THST_EXPO', '0.65', PX['EXPO']), ('SERVO_BLH_MASK', '—', PX['BLH'])]
    return out


# ------------------------------------------------------------------ motor çıkışları
def fn_of(m):
    if m.get('fn'): return int(m['fn'])
    return 32 + m['n'] if isinstance(m['n'], int) else None


def outputs(fr, P=None):
    """{motor kimliği: [(çıkış no, gerçek mi)]}. P verilirse SERVOn_FUNCTION'dan gerçek eşleme, yoksa örnek."""
    res = {}
    real = bool(P) and any(k.startswith('SERVO') and k.endswith('_FUNCTION') for k in P)
    base = 4 if fr['group'] == 'qp' and fr['kind'] != 'tailsitter' else 0
    ex_lr = {'qp_tailsitter': {73: 5, 74: 6}, 'pl_twin': {73: 3, 74: 5}, 'rv_skid': {73: 1, 74: 3}, 'pl_single': {70: 3}}
    for m in fr['motors']:
        fn = fn_of(m)
        if real:
            chs = [int(k[5:-9]) for k, v in P.items() if k.startswith('SERVO') and k.endswith('_FUNCTION') and k[5:-9].isdigit() and int(v) == fn]
            res[str(m['n'])] = [(c, True) for c in sorted(chs)]
        else:
            if fr['id'] in ex_lr: c = ex_lr[fr['id']].get(fn)
            else: c = base + m['n'] if isinstance(m['n'], int) else None
            res[str(m['n'])] = [(c, False)] if c else []
    if fr['kind'] == 'tri':
        res['servo'] = [(c, True) for c in sorted(int(k[5:-9]) for k, v in (P or {}).items() if k.startswith('SERVO') and k.endswith('_FUNCTION')
                                                   and k[5:-9].isdigit() and int(v) == 39)] if real else [(7, False)]
    return res, real


def log_field(ch):
    if ch is None: return ''
    if ch <= 14: return f'RCOU.C{ch}'
    if ch <= 18: return f'RCO2.C{ch}'
    return f'RCO3.C{ch}'


def esc_field(ch):
    return f'ESC[{ch - 1}].RPM' if ch else ''


# ------------------------------------------------------------------ anlatım
def _intro(fr, lg):
    mots = [m for m in fr['motors']]
    ccw = [str(m['n']) for m in mots if m['yaw'] > 0]; cw = [str(m['n']) for m in mots if m['yaw'] < 0]
    n = len(mots); k = fr['kind']; g = fr['group']
    P = []
    if k == 'matrix':
        P.append(_t((f'{n} kaldırma motoru var: {len(ccw)} tanesi saat yönünün tersine (mavi: {", ".join(ccw) or "—"}), {len(cw)} tanesi saat yönüne (yeşil: {", ".join(cw) or "—"}) döner.',
                     f'There are {n} lift motors: {len(ccw)} spin counter-clockwise (blue: {", ".join(ccw) or "—"}), {len(cw)} spin clockwise (green: {", ".join(cw) or "—"}).',
                     f'يوجد {n} محركات رفع: {len(ccw)} تدور عكس عقارب الساعة (أزرق: {", ".join(ccw) or "—"})، و{len(cw)} مع عقارب الساعة (أخضر: {", ".join(cw) or "—"}).'), lg))
        if ccw and cw:
            P.append(_t(('Yaw (burun sağa-sola) nasıl yapılır: pervaneler gövdeyi ters yöne döndürmeye çalışır. Otopilot bir yön grubunu hızlandırıp diğerini yavaşlatınca '
                         'gövde döner. Bu yüzden iki grubun eşit sayıda ve doğru yönde olması şarttır.',
                         'How yaw works: each prop tries to turn the frame the opposite way. The autopilot speeds up one rotation group and slows the other, so the '
                         'frame turns. That is why both groups must be equal and spin the right way.',
                         'كيف يتم الانعراج: كل مروحة تحاول تدوير الهيكل بالاتجاه المعاكس. يسرّع الطيار الآلي مجموعة ويبطئ الأخرى فيدور الهيكل. '
                         'لذلك يجب أن تتساوى المجموعتان وتدورا بالاتجاه الصحيح.'), lg))
        if any(m.get('level') for m in mots):
            P.append(_t(('Bu çerçevede her kolda üst üste iki motor var. Üst ve alt motor ters yöne döner; böylece kolun torku birbirini götürür. '
                         'Alt motor üsttekinin hava akımında çalıştığı için aynı itki için daha fazla gaz ister: logda alt motorların biraz yüksek olması normaldir.',
                         'Each arm carries two stacked motors. Top and bottom spin opposite ways so their torque cancels. The bottom motor works in the top one\'s '
                         'downwash and needs more throttle for the same thrust: slightly higher bottom outputs in the log are normal.',
                         'كل ذراع يحمل محركين فوق بعضهما. يدوران باتجاهين متعاكسين فيلغي عزمهما بعضه. المحرك السفلي يعمل في تيار العلوي '
                         'ويحتاج خانقاً أكبر للدفع نفسه: ارتفاع مخارج السفلية قليلاً في السجل أمر طبيعي.'), lg))
        if g == 'qp':
            P.append(_t(('QuadPlane\'de bu motorlar yalnız dikey kalkış/iniş (Q modları) ve geçiş sırasında çalışır; ileri uçuşta durur. İleri uçuş motoru ayrıdır (Throttle = 70). '
                         'Uçağın yüzeyleri ve gazı genelde SERVO1–4\'te olduğu için kaldırma motorları çoğunlukla SERVO5\'ten başlatılır.',
                         'On a QuadPlane these motors run only for vertical take-off/landing (Q modes) and transition; they stop in forward flight. The forward motor is '
                         'separate (Throttle = 70). Because the plane\'s surfaces and throttle usually sit on SERVO1–4, lift motors usually start at SERVO5.',
                         'في QuadPlane تعمل هذه المحركات فقط للإقلاع/الهبوط العمودي (أوضاع Q) وأثناء الانتقال؛ وتتوقف في الطيران الأمامي. محرك الطيران الأمامي منفصل (Throttle = 70). '
                         'وبما أن أسطح الطائرة وخانقها عادة على SERVO1–4 فتبدأ محركات الرفع غالباً من SERVO5.'), lg))
        else:
            P.append(_t(('Kopterde motorlar genelde SERVO1\'den sırayla bağlanır (Motor1 = SERVO1 …), ama SERVOn_FUNCTION değeri doğru olduğu sürece başka çıkış da kullanılabilir.',
                         'On a copter motors are usually wired from SERVO1 in order (Motor1 = SERVO1 …), but any output works as long as SERVOn_FUNCTION is right.',
                         'في الكوبتر توصَل المحركات عادة من SERVO1 بالترتيب (Motor1 = SERVO1 …)، لكن يصلح أي مخرج ما دام SERVOn_FUNCTION صحيحاً.'), lg))
    note = MO.note(fr, lg)
    if note: P.append('⚠ ' + note)
    return P


def _steps(fr, outs, lg, P):
    k = fr['kind']; g = fr['group']
    pre = 'Q_M_' if g == 'qp' else 'MOT_'
    pmax = (P or {}).get(pre + 'PWM_MAX')
    pm = f' ({pre}PWM_MAX = {pmax:g})' if pmax else f' ({pre}PWM_MAX)'
    cw = [m['n'] for m in fr['motors'] if m['yaw'] < 0]; ccw = [m['n'] for m in fr['motors'] if m['yaw'] > 0]

    def f(n):
        o = outs.get(str(n)) or []
        return log_field(o[0][0]) if o and o[0][0] else f'Motor{n}'
    if fr['id'] == 'pl_single':
        return [_t(x, lg) for x in (
            ('Log Gezgini\'nde CTUN.ThO (otopilotun istediği gaz, %) ve RCOU.C3 (motora giden PWM) alanlarını birlikte açın.',
             'In the Log Browser open CTUN.ThO (throttle the autopilot asks for, %) together with RCOU.C3 (PWM sent to the motor).',
             'في مستعرض السجل افتح CTUN.ThO (الخانق الذي يطلبه الطيار الآلي، %) مع RCOU.C3 (PWM المرسل للمحرك).'),
            ('Tırmanışta ve düz uçuşta gaz sürekli THR_MAX\'a dayanıyorsa motor/pervane gücü yetersizdir ya da batarya zayıflamıştır (BAT.Volt ile birlikte bakın).',
             'If throttle sits at THR_MAX in climbs and cruise, the motor/prop lacks power or the battery is weak (check together with BAT.Volt).',
             'إذا بقي الخانق عند THR_MAX في الصعود والطيران المستوي فقدرة المحرك/المروحة غير كافية أو البطارية ضعيفة (انظر معه BAT.Volt).'),
            ('ESC telemetrisi varsa ESC[k].RPM: gaz artarken devir artmıyorsa motor/ESC sorunu (desync, kopuk kablo) vardır.',
             'With ESC telemetry, ESC[k].RPM: if RPM does not rise with throttle there is a motor/ESC problem (desync, loose wire).',
             'مع قياسات ESC، ESC[k].RPM: إذا لم ترتفع الدورات مع الخانق فهناك مشكلة محرك/ESC (فقدان تزامن، سلك مفكوك).'))]
    if fr['id'] == 'pl_twin' or fr['id'] == 'rv_skid' or k == 'tailsitter':
        a, b = f('L'), f('R')
        return [_t(x, lg) for x in (
            (f'Log Gezgini\'nde sol motoru ({a}) ve sağ motoru ({b}) birlikte açın.', f'In the Log Browser open the left motor ({a}) and right motor ({b}) together.',
             f'في مستعرض السجل افتح المحرك الأيسر ({a}) والأيمن ({b}) معاً.'),
            ('Düz giderken iki çıkış birbirine yakın olmalı. Aradaki fark dönüş (yaw/dümen) komutudur: sürekli bir taraf yüksekse araç o tarafa çekiyordur '
             '(motor/pervane farkı, eğik montaj ya da ağırlık dengesizliği).',
             'Going straight the two outputs should be close. The difference is the turn (yaw/rudder) command: if one side is always higher the vehicle pulls to '
             'that side (motor/prop difference, crooked mount or weight imbalance).',
             'أثناء السير المستقيم يجب أن يتقارب المخرجان. الفرق هو أمر الالتفاف (انعراج/دفة): إذا كان جانب أعلى دائماً فالمركبة تنحرف نحوه '
             '(فرق محرك/مروحة، تركيب مائل أو عدم توازن الوزن).'),
            ('Bir çıkış en üst değere dayanıp kalıyorsa o taraf yetişemiyor: motor zayıf ya da arızalı olabilir.',
             'If one output sits at its maximum, that side cannot keep up: the motor may be weak or failing.',
             'إذا بقي مخرج عند حده الأعلى فذلك الجانب لا يواكب: قد يكون المحرك ضعيفاً أو معطلاً.'))]
    out = [
        (f'Log Gezgini\'nde motor çıkışlarını açın ({", ".join(f(m["n"]) for m in fr["motors"] if isinstance(m["n"], int))}). Bunlar otopilotun her motora gönderdiği PWM\'dir (µs).',
         f'In the Log Browser open the motor outputs ({", ".join(f(m["n"]) for m in fr["motors"] if isinstance(m["n"], int))}). These are the PWM (µs) the autopilot sends to each motor.',
         f'في مستعرض السجل افتح مخارج المحركات ({", ".join(f(m["n"]) for m in fr["motors"] if isinstance(m["n"], int))}). هذه إشارات PWM (µs) التي يرسلها الطيار الآلي لكل محرك.'),
        (f'Askıda (hover) bütün motorlar birbirine yakın olmalı (aralarında 100–150 µs\'den az fark). Bir motor sürekli diğerlerinden yüksekse o köşe ağırdır, '
         f'ya da o motor/pervane zayıftır.',
         f'In hover all motors should be close (less than 100–150 µs apart). If one motor is always higher, that corner is heavy or that motor/prop is weak.',
         f'في التحويم يجب أن تتقارب كل المحركات (فرق أقل من 100–150 µs). إذا كان محرك أعلى دائماً فتلك الزاوية ثقيلة أو المحرك/المروحة ضعيف.'),
        (f'Bir motor en üst değere{pm} dayanıp kalıyorsa doygunluktur: o motor itki yetiştiremiyor. Aynı anda çapraz karşısındaki motor en alta iniyorsa '
         f'bu neredeyse kesin motor/ESC/pervane kaybıdır.',
         f'If a motor sits at its maximum{pm} it is saturated: it cannot give enough thrust. If the diagonally opposite motor drops to minimum at the same time, '
         f'it is almost certainly a motor/ESC/prop loss.',
         f'إذا بقي محرك عند الحد الأعلى{pm} فهو مشبع: لا يعطي دفعاً كافياً. وإذا نزل المحرك المقابل قطرياً إلى الأدنى في الوقت نفسه '
         f'فهذا شبه مؤكد فقدان محرك/ESC/مروحة.'),
    ]
    if cw and ccw:
        out.append((f'Yaw dengesi: saat yönü grubu ({", ".join(map(str, cw))}) ile ters grup ({", ".join(map(str, ccw))}) ortalamaları karşılaştırın. '
                    'Bir grup sürekli yüksekse bir motor eğik takılmıştır ya da kollar burulmuştur; otopilot yaw tutmak için o grubu zorluyordur.',
                    f'Yaw balance: compare the averages of the clockwise group ({", ".join(map(str, cw))}) and the counter-clockwise group ({", ".join(map(str, ccw))}). '
                    'If one group is always higher a motor is mounted crooked or an arm is twisted; the autopilot is working that group to hold yaw.',
                    f'توازن الانعراج: قارن متوسط مجموعة عقارب الساعة ({", ".join(map(str, cw))}) والمجموعة المعاكسة ({", ".join(map(str, ccw))}). '
                    'إذا كانت مجموعة أعلى دائماً فهناك محرك مائل أو ذراع ملتوٍ؛ والطيار الآلي يجهد تلك المجموعة ليحافظ على الانعراج.'))
    out += [
        ('Kalkışta araç hemen devriliyorsa ve aynı anda bir motor en üste, karşısındaki en alta gidiyorsa motor sırası ya da dönüş yönü yanlıştır: '
         'Motor Testi ile A, B, C… sırasını ve okları kontrol edin.',
         'If the vehicle flips right at take-off and one motor goes to max while the opposite goes to min, the motor order or rotation is wrong: '
         'check the A, B, C… order and the arrows with Motor Test.',
         'إذا انقلبت المركبة فور الإقلاع وذهب محرك للأعلى والمقابل للأدنى فترتيب المحركات أو اتجاه الدوران خاطئ: '
         'افحص ترتيب A، B، C… والأسهم عبر اختبار المحركات.'),
        ('ESC telemetrisi varsa (SERVO_BLH_MASK / DShot) ESC[k].RPM, Curr ve Temp alanlarına bakın: komut (RCOU) artarken devir artmıyorsa motor/ESC kopukluğu '
         '(desync) ya da pervane kayması vardır; bir motorun akımı diğerlerinden çok yüksekse o motor ya da yatağı zorlanıyordur.',
         'With ESC telemetry (SERVO_BLH_MASK / DShot) look at ESC[k].RPM, Curr and Temp: if RPM does not follow the command (RCOU) there is a motor/ESC desync '
         'or a slipping prop; a motor drawing much more current than the others, or its bearing, is struggling.',
         'مع قياسات ESC (SERVO_BLH_MASK / DShot) انظر إلى ESC[k].RPM وCurr وTemp: إذا لم تتبع الدورات الأمر (RCOU) فهناك فقدان تزامن '
         'أو انزلاق مروحة؛ وإذا سحب محرك تياراً أعلى بكثير فذلك المحرك أو محمله يعاني.'),
    ]
    if g == 'qp':
        out.append(('QuadPlane geçişinde QTUN (askı tutum/irtifa) ve CTUN.ThO ile birlikte okuyun: geçişte hız artarken kaldırma motorları yavaşça azalmalı; '
                    'ileri uçuşa geçtikten sonra durmalıdır (Q_ASSIST_SPEED altında yardım için yeniden çalışabilirler).',
                    'During a QuadPlane transition read them with QTUN (hover attitude/altitude) and CTUN.ThO: as speed builds the lift motors should ramp down; '
                    'after the transition they stop (below Q_ASSIST_SPEED they may run again to assist).',
                    'أثناء انتقال QuadPlane اقرأها مع QTUN (وضعية/ارتفاع التحويم) وCTUN.ThO: مع ازدياد السرعة يجب أن تنخفض محركات الرفع تدريجياً؛ '
                    'وبعد الانتقال تتوقف (وتحت Q_ASSIST_SPEED قد تعمل مجدداً للمساعدة).'))
    if k == 'tri':
        s = (outs.get('servo') or [(7, False)])[0][0]
        out.append((f'Kuyruk servosu {log_field(s)}: askıda orta değer (SERVO{s}_TRIM) çevresinde olmalı. Sürekli bir tarafa yatık duruyorsa yaw dengesizdir '
                    '(arka motor eğik ya da ön motorlar farklı).',
                    f'Tail servo {log_field(s)}: in hover it should stay near its centre (SERVO{s}_TRIM). If it always leans one way, yaw is unbalanced '
                    '(rear motor crooked or front motors different).',
                    f'مؤازر الذيل {log_field(s)}: في التحويم يجب أن يبقى قرب منتصفه (SERVO{s}_TRIM). إذا مال دائماً لجهة فالانعراج غير متوازن '
                    '(المحرك الخلفي مائل أو الأماميان مختلفان).'))
    return [_t(x, lg) for x in out]


def _check(fr, lg):
    if fr['group'] == 'other' and fr['id'] != 'pl_twin' and fr['id'] != 'rv_skid':
        items = [('Pervane takılı değilken arm edip gazı yavaşça artırın; motor düzgün ve doğru yönde dönmeli.', 'With the prop off, arm and raise throttle slowly; the motor must run smoothly the right way.',
                  'بدون المروحة سلّح وارفع الخانق ببطء؛ يجب أن يدور المحرك بسلاسة وبالاتجاه الصحيح.')]
    else:
        items = [('Pervaneleri çıkarın. Mission Planner → Kurulum → İsteğe bağlı donanım → Motor Testi\'nde A, B, C… düğmelerine sırayla basın; dönen motor resimde o harfin olduğu yerde olmalı.',
                  'Remove the props. In Mission Planner → Setup → Optional Hardware → Motor Test press A, B, C… in turn; the spinning motor must be where that letter is in the picture.',
                  'انزع المراوح. في Mission Planner ← الإعداد ← العتاد الاختياري ← اختبار المحركات اضغط A، B، C… بالترتيب؛ يجب أن يدور المحرك الموجود في موضع ذلك الحرف في الصورة.'),
                 ('Her motorun dönüşü resimdeki okla aynı olmalı. Ters dönen motorda ESC\'nin üç kablosundan ikisini değiştirin (DShot/BLHeli\'de yazılımla da çevrilebilir).',
                  'Each motor must spin like the arrow in the picture. On a reversed motor swap two of the three ESC wires (with DShot/BLHeli it can also be reversed in software).',
                  'يجب أن يدور كل محرك مثل السهم في الصورة. في المحرك المعكوس بدّل سلكين من أسلاك ESC الثلاثة (ويمكن عكسه برمجياً مع DShot/BLHeli).'),
                 ('Pervaneyi dönüş yönüne uygun takın (CW/CCW pervane): pervanenin kalın, yuvarlak kenarı dönüş yönünde önde olmalı.',
                  'Fit the prop that matches the rotation (CW/CCW prop): the thick, rounded leading edge must face the direction of rotation.',
                  'ركّب المروحة المناسبة للاتجاه (CW/CCW): الحافة السميكة المستديرة يجب أن تتقدم باتجاه الدوران.'),
                 ('İlk kalkışı alçakta yapın; logda motor çıkışlarının birbirine yakın olduğunu kontrol edin.', 'Make the first take-off low; check in the log that the motor outputs stay close together.',
                  'اجعل الإقلاع الأول منخفضاً؛ وتحقق في السجل أن مخارج المحركات متقاربة.')]
    return [_t(x, lg) for x in items]


def html_for(fr, lg, P=None, has_log=False):
    """Öğretici ayrıntı HTML'i. P = açık logun parametreleri (gerçek çıkış eşlemesi ve 'Logdaki değer' sütunu)."""
    lgi = L3.get(lg, 0)
    outs, real = outputs(fr, P)
    h = [f'<h3>{E(_t(T["s1"], lg))}</h3>'] + [f'<p>{E(p)}</p>' for p in _intro(fr, lg)]
    # parametreler
    cols = list(T['p_cols'][lgi]) + ([_t(T['p_log'], lg)] if P else [])
    h.append(f'<h3>{E(_t(T["s2"], lg))}</h3><table border="1" cellspacing="0" cellpadding="4" style="border-collapse:collapse">')
    h.append('<tr>' + ''.join(f'<th>{E(c)}</th>' for c in cols) + '</tr>')
    for p, v, ex in _params(fr, P, lg):
        lv = ''
        if P:
            x = P.get(p)
            lv = f'<td>{x:g}</td>' if isinstance(x, (int, float)) else '<td></td>'
        h.append(f'<tr><td><code>{E(p)}</code></td><td>{E(v)}</td><td>{E(_t(ex, lg))}</td>{lv}</tr>')
    h.append('</table>')
    # motorlar
    h.append(f'<h3>{E(_t(T["s3"], lg))}</h3><table border="1" cellspacing="0" cellpadding="4" style="border-collapse:collapse">')
    h.append('<tr>' + ''.join(f'<th>{E(c)}</th>' for c in T['m_cols'][lgi]) + '</tr>')
    rows = MO.rows(fr, lg)
    order = sorted(fr['motors'], key=lambda z: (isinstance(z['n'], str), z['n'] if isinstance(z['n'], int) else 0, str(z['n'])))
    keys = []; esc = []
    for m, r in zip(order, rows):
        fn = fn_of(m); o = outs.get(str(m['n'])) or []
        if o:
            ch = ', '.join(f'SERVO{c}' for c, _ in o); lf = ', '.join(log_field(c) for c, _ in o); ef = ', '.join(esc_field(c) for c, _ in o)
            tag = _t(T['real'] if real else T['ex'], lg)
            keys += [log_field(c) for c, _ in o]; esc += [esc_field(c) for c, _ in o]
        else:
            ch = _t(T['none'], lg) if real else '—'; lf = ef = '—'; tag = ''
        h.append(f'<tr><td><b>{E(r[0])}</b></td><td><code>{fn if fn else "—"}</code></td><td>{E(ch)} <span style="color:#64748B">({E(tag)})</span></td>'
                 f'<td><code>{E(lf)}</code></td><td><code>{E(ef)}</code></td><td>{E(r[1])}</td><td>{E(r[2])}</td><td>{E(r[3])}</td></tr>')
    if fr['kind'] == 'tri':
        o = outs.get('servo') or []
        ch = ', '.join(f'SERVO{c}' for c, _ in o) or '—'
        h.append(f'<tr><td><b>{E(_t(("Kuyruk servosu", "Tail servo", "مؤازر الذيل"), lg))}</b></td><td><code>39</code></td><td>{E(ch)}</td>'
                 f'<td><code>{E(", ".join(log_field(c) for c, _ in o) or "—")}</code></td><td>—</td><td>{E(MO.pos_text({"x": 0, "y": -1}, lg))}</td><td>—</td><td></td></tr>')
        keys += [log_field(c) for c, _ in o]
    h.append('</table>')
    h.append(f'<p style="color:#64748B">{E(_t(T["real_note"] if real else T["ex_note"], lg))}</p>')
    keys = [k for k in dict.fromkeys(keys) if k]; esc = [k for k in dict.fromkeys(esc) if k]
    if keys:
        extra = '' if has_log else f' <span style="color:#64748B">{E(_t(T["need_log"], lg))}</span>'
        h.append(f'<p><a href="lb:{",".join(keys)}">{E(_t(T["open_lb"], lg))}</a>{extra}'
                 + (f' &nbsp;·&nbsp; <a href="lb:{",".join(esc)}">{E(_t(T["open_esc"], lg))}</a>' if esc else '') + '</p>')
    h.append(f'<h3>{E(_t(T["s4"], lg))}</h3><ol>' + ''.join(f'<li>{E(s)}</li>' for s in _steps(fr, outs, lg, P)) + '</ol>')
    h.append(f'<h3>{E(_t(T["s5"], lg))}</h3><ol>' + ''.join(f'<li>{E(s)}</li>' for s in _check(fr, lg)) + '</ol>')
    return ''.join(h)
