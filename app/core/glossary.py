"""Havacılık / ArduPilot terim sözlüğü (EN → TR / AR).

Bütün çeviriler (parametre açıklamaları, log mesajları, YZ çevirileri) bu sözlüğe bağlıdır:
- tools_data/translate.py makine çevirisinde terimleri yer tutucuya alır, çeviriden sonra bu karşılıkları koyar;
- fix() eski / hatalı makine çevirilerini çalışma anında düzeltir ("ön kol" → "arm öncesi" gibi);
- prompt() YZ çeviri isteklerine eklenir.
Kural: uçuş modu adları ve kısaltmalar (ARM, EKF, RTL, LOITER, PWM…) çevrilmez.
"""
from __future__ import annotations
import re

GV = 3   # sözlük sürümü: değişince makine çevirileri yeniden yapılır

# (İngilizce desen, Türkçe, Arapça). Uzun ifadeler önce gelmeli.
TERMS = [
    (r'pre-?arm(?:ing)?(?: checks?)?', 'arm öncesi kontrol', 'فحوصات ما قبل التسليح (Pre-arm)'),
    (r'auto-?arm(?:ing|ed)?', 'otomatik arm', 'التسليح التلقائي'),
    (r'disarm(?:ed|ing|s)?', 'disarm', 'نزع التسليح (Disarm)'),
    (r'arm(?:ed|ing|s)?', 'arm', 'التسليح (Arm)'),
    (r'fail-?safes?', 'failsafe', 'وضع الطوارئ (Failsafe)'),
    (r'geo-?fences?|fences?', 'geofence (sanal sınır)', 'السياج الجغرافي (Fence)'),
    (r'rally points?', 'rally noktası', 'نقطة التجمع (Rally)'),
    (r'way-?points?', 'yol noktası (waypoint)', 'نقطة المسار (Waypoint)'),
    (r'home (?:location|position|point)|home', 'home noktası', 'نقطة الانطلاق (Home)'),
    (r'airspeed', 'hava hızı', 'السرعة الجوية'),
    (r'ground ?speed', 'yer hızı', 'السرعة الأرضية'),
    (r'vertical speed|climb rate|sink rate', 'dikey hız', 'السرعة العمودية'),
    (r'throttle', 'gaz', 'الخانق (Throttle)'),
    (r'roll', 'yatış (roll)', 'الدحرجة (Roll)'),
    (r'pitch', 'yunuslama (pitch)', 'الميل الطولي (Pitch)'),
    (r'yaw', 'sapma (yaw)', 'الانعراج (Yaw)'),
    (r'heading', 'yön (heading)', 'الاتجاه (Heading)'),
    (r'attitude', 'tutum (attitude)', 'الوضعية (Attitude)'),
    (r'bank angle', 'yatış açısı', 'زاوية الانعطاف'),
    (r'angle of attack|AoA', 'hücum açısı', 'زاوية الهجوم'),
    (r'stall', 'stall (perdövites)', 'الانهيار الهوائي (Stall)'),
    (r'flare', 'flare (iniş düzleştirmesi)', 'التسوية قبل الملامسة (Flare)'),
    (r'loiter', 'Loiter', 'Loiter (التحويم)'),
    (r'take-?off', 'kalkış', 'الإقلاع'),
    (r'landing', 'iniş', 'الهبوط'),
    (r'go-?around', 'pas geçme (go-around)', 'إعادة المحاولة (Go-around)'),
    (r'approach', 'yaklaşma', 'الاقتراب'),
    (r'cross-?track', 'rota sapması (crosstrack)', 'الانحراف الجانبي عن المسار'),
    (r'trim', 'trim', 'التريم (Trim)'),
    (r'aileron', 'kanatçık (aileron)', 'الجنيح (Aileron)'),
    (r'elevator', 'irtifa dümeni (elevator)', 'الرافع (Elevator)'),
    (r'rudder', 'istikamet dümeni (rudder)', 'الدفة (Rudder)'),
    (r'elevons?', 'elevon', 'إيليفون'),
    (r'flaperons?', 'flaperon', 'فلابيرون'),
    (r'flaps?', 'flap', 'القلاب (Flap)'),
    (r'spoilers?', 'spoiler', 'المفسد الهوائي (Spoiler)'),
    (r'v-?tail', 'V kuyruk', 'الذيل V'),
    (r'tail-?sitters?', 'tail-sitter', 'تيل سيتر (Tailsitter)'),
    (r'quad-?planes?', 'QuadPlane', 'QuadPlane'),
    (r'transitions?', 'geçiş (transition)', 'الانتقال (Transition)'),
    (r'tilt-?rotors?', 'tilt-rotor', 'المراوح القابلة للإمالة'),
    (r'collective(?: pitch)?', 'kolektif hatve', 'الخطوة الجماعية (Collective)'),
    (r'cyclic', 'siklik', 'الدوري (Cyclic)'),
    (r'swash-?plate', 'swashplate (eğik tabla)', 'الصحن المتأرجح (Swashplate)'),
    (r'tail rotor', 'kuyruk rotoru', 'الدوار الخلفي'),
    (r'main rotor', 'ana rotor', 'الدوار الرئيسي'),
    (r'autorotation', 'otorotasyon', 'الدوران الذاتي (Autorotation)'),
    (r'propellers?|props?', 'pervane', 'المروحة'),
    (r'motors?', 'motor', 'المحرك'),
    (r'ESCs?', 'ESC', 'ESC'),
    (r'servos?', 'servo', 'سيرفو'),
    (r'gimbals?', 'gimbal', 'جيمبال'),
    (r'rangefinders?|range finders?', 'mesafe sensörü (rangefinder)', 'حساس المسافة (Rangefinder)'),
    (r'lidar', 'LiDAR', 'ليدار'),
    (r'compass(?:es)?|magnetometers?', 'pusula', 'البوصلة'),
    (r'barometers?|baro', 'barometre', 'البارومتر'),
    (r'accelerometers?|accels?', 'ivmeölçer', 'مقياس التسارع'),
    (r'gyro(?:scope)?s?', 'jiroskop', 'الجيروسكوب'),
    (r'airspeed sensor|pitot(?: tube)?', 'hava hızı sensörü (pitot)', 'حساس السرعة الجوية (بيتو)'),
    (r'telemetry', 'telemetri', 'القياس عن بعد (Telemetry)'),
    (r'ground (?:control )?station|GCS', 'yer kontrol istasyonu (GCS)', 'محطة التحكم الأرضية (GCS)'),
    (r'transmitter', 'kumanda vericisi', 'جهاز الإرسال'),
    (r'receiver', 'alıcı', 'المستقبل'),
    (r'autopilot|flight controller', 'otopilot', 'الطيار الآلي'),
    (r'gains?', 'kazanç', 'الكسب (Gain)'),
    (r'feed-?forward', 'ileri besleme (FF)', 'التغذية الأمامية (FF)'),
    (r'integrator', 'integral terimi', 'المكامل (Integrator)'),
    (r'derivative', 'türev', 'المشتق'),
    (r'slew rate', 'değişim hızı sınırı (slew)', 'معدل التغير (Slew)'),
    (r'dead-?zone|dead-?band', 'ölü bölge', 'المنطقة الميتة'),
    (r'expo', 'expo', 'الأسية (Expo)'),
    (r'bit-?mask', 'bit maskesi', 'قناع البتات'),
    (r'notch filter', 'çentik filtresi (notch)', 'مرشح الشق (Notch)'),
    (r'harmonic notch', 'harmonik çentik filtresi', 'مرشح الشق التوافقي'),
    (r'precision landing|precland', 'hassas iniş (PrecLand)', 'الهبوط الدقيق (PrecLand)'),
    (r'parachute', 'paraşüt', 'المظلة'),
    (r'winch', 'vinç', 'الرافعة'),
    (r'gripper', 'tutucu (gripper)', 'الماسك (Gripper)'),
    (r'sprayer', 'ilaçlama sistemi', 'نظام الرش'),
    (r'mission', 'görev', 'المهمة'),
    (r'vehicle', 'araç', 'المركبة'),
    (r'aircraft', 'hava aracı', 'الطائرة'),
    (r'payload', 'faydalı yük', 'الحمولة'),
    (r'battery|batteries', 'batarya', 'البطارية'),
    (r'cells?', 'hücre', 'الخلية'),
    (r'brown-?out', 'voltaj düşmesi (brownout)', 'انخفاض الجهد (Brownout)'),
    (r'ignition', 'ateşleme', 'الإشعال'),
    (r'choke', 'jikle', 'الخانق الهوائي (Choke)'),
    (r'starter', 'marş', 'المشغّل (Starter)'),
    (r'RPM', 'devir (RPM)', 'الدوران في الدقيقة (RPM)'),
    (r'wind', 'rüzgâr', 'الرياح'),
    (r'gust', 'hamle (ani rüzgâr)', 'هبة الرياح'),
    (r'altitude', 'irtifa', 'الارتفاع'),
    (r'AGL', 'yerden yükseklik (AGL)', 'الارتفاع فوق الأرض (AGL)'),
    (r'AMSL', 'deniz seviyesinden yükseklik (AMSL)', 'الارتفاع فوق سطح البحر (AMSL)'),
    (r'terrain following|terrain', 'arazi', 'التضاريس'),
    (r'geo-?location', 'coğrafi konum', 'الموقع الجغرافي'),
]
# Çevrilmeyen uçuş modları / kısaltmalar (yer tutucuyla aynen korunur)
KEEP = ['RTL', 'SmartRTL', 'QRTL', 'AUTO', 'GUIDED', 'STABILIZE', 'ALT_HOLD', 'AltHold', 'POSHOLD', 'PosHold', 'LAND', 'QLAND', 'QLOITER',
        'QHOVER', 'QSTABILIZE', 'QACRO', 'QAUTOTUNE', 'FBWA', 'FBWB', 'CRUISE', 'MANUAL', 'ACRO', 'CIRCLE', 'TAKEOFF', 'AUTOTUNE',
        'BRAKE', 'DRIFT', 'SPORT', 'FLIP', 'THROW', 'ZIGZAG', 'FLOWHOLD', 'FOLLOW', 'AVOID_ADSB', 'EKF', 'AHRS', 'IMU', 'GPS', 'GNSS', 'RTK',
        'PWM', 'PID', 'RC', 'MAVLink', 'DroneCAN', 'UAVCAN', 'CAN', 'OSD', 'ADSB', 'ADS-B', 'TECS', 'L1', 'NAVL1', 'SITL', 'Lua', 'EFI', 'ICE',
        'VTOL', 'FFT', 'DShot', 'BLHeli', 'SBUS', 'CRSF', 'ELRS', 'PPM', 'I2C', 'SPI', 'UART']

# Makine çevirisinin zaten doğru çevirdiği genel kelimeler: yer tutucuya alınmaz (akıcılık bozulmasın)
SOFT = {'kalkış', 'iniş', 'yaklaşma', 'pervane', 'motor', 'ESC', 'servo', 'pusula', 'barometre', 'ivmeölçer', 'jiroskop', 'görev', 'araç',
        'hava aracı', 'faydalı yük', 'batarya', 'hücre', 'rüzgâr', 'irtifa', 'arazi', 'coğrafi konum', 'alıcı', 'paraşüt', 'vinç', 'türev',
        'ateşleme', 'marş', 'telemetri', 'LiDAR', 'gimbal', 'flap', 'spoiler', 'V kuyruk', 'tail-sitter', 'QuadPlane', 'tilt-rotor', 'kuyruk rotoru', 'ana rotor'}

_COMPILED = [(re.compile(r'(?<![A-Za-z_])(?:' + p + r')(?![A-Za-z_])', re.I), tr, ar) for p, tr, ar in TERMS]
_KEEP = re.compile(r'(?<![A-Za-z0-9_])(' + '|'.join(re.escape(k) for k in sorted(KEEP, key=len, reverse=True)) + r')(?![A-Za-z0-9_])')
_IDENT = re.compile(r'\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b')   # parametre adları: Q_ASSIST_SPEED


def _tok(i):
    a = 'ABCDEFGHJKLMNPRSTUVWXYZ'
    return 'XQ' + a[i // len(a) % len(a)] + a[i % len(a)] + 'Z'


def protect(text):
    """Terimleri yer tutucuya alır: (yeni metin, [(tok, tür, değer)])."""
    out = []; n = [0]
    def sub_keep(m):
        t = _tok(n[0]); n[0] += 1; out.append((t, 'keep', m.group(0))); return t
    text = _IDENT.sub(sub_keep, text)
    text = _KEEP.sub(sub_keep, text)
    for i, (rx, tr, ar) in enumerate(_COMPILED):
        if tr in SOFT: continue
        def sub_term(m, i=i):
            t = _tok(n[0]); n[0] += 1; out.append((t, 'term', i)); return t
        text = rx.sub(sub_term, text)
    return text, out


_SUFFIX_TR = re.compile(r"'(?:y?[ıiuüae]|[dt][ae]n?|n[ıiuü]n|[ıiuü]n|l[ae]r\w*|y[ae]|n[ae]|[ıiuü]|y?l[ae])\b")


def restore(text, toks, lang):
    """Yer tutucuları sözlük karşılığıyla değiştirir; eksik yer tutucu varsa None döner."""
    li = 1 if lang == 'tr' else 2
    for t, kind, v in toks:
        if t not in text: return None
        if kind == 'keep': rep = v
        else: rep = TERMS[v][li]
        if lang == 'tr' and kind == 'term':
            text = re.sub(re.escape(t) + _SUFFIX_TR.pattern, rep, text)
        text = text.replace(t, rep)
    return text


# ----------------------------------------------- eski çevirileri düzeltme (çalışma anında)
FIX = {
    'tr': [(r'[ÖöOo]n kol', 'arm öncesi kontrol'), (r'\bsilahsızlandır\w*', 'disarm'), (r'\bsilahlan\w*|\bsilahland\w*', 'arm'),
           (r'\b[Kk]ol(?:u|lar[ıi]?)? (?:aç|kapat|çöz)\w*', 'arm/disarm'),
           (r'\b[Yy]uvarlanma\b|\b[Yy]uvarlama\b|\b[Yy]ürütme ekseni\b|\b[Rr]ol ekseni\b', 'Yatış (roll) ekseni'),
           (r'\b[Yy]umruk\b', 'sapma (yaw)'), (r'\b[Kk]ırçık kesim\b', 'yunuslama (pitch) trimi'),
           (r'\bgaz kelebeği\b', 'gaz'), (r'\bgazlama\b', 'gaz'), (r'\b[Çç]it\b', 'geofence'), (r'\b[Rr]alli\b', 'rally'),
           (r'\bevin\b', 'home noktasının'), (r'\b[Ee]vden\b', 'home noktasından'), (r'\b[Ee]ve\b(?= dön)', 'home noktasına'),
           (r'\b[Çç]apraz (?:çizgi|yol)\b', 'rota sapması (crosstrack)'), (r'\b[Ee]ntegratör\w*', 'integral terimi'),
           (r'\b[Uu]zaklık ölçer\w*', 'mesafe sensörü'), (r'\b[Kk]uyruk rotoru düzenleme\b', 'kuyruk rotoru trimi'),
           (r'\b[Dd]ümen uçakları\b', 'yalnız rudder kumandalı uçaklar'), (r'\bdisarm(?:\'?[ıi]|\'yi)\b', 'disarm'),
           (r"\barm'(?:ye|yi|nin|den|de)\b", 'arm'), (r'\bToplu\b', 'Kolektif'), (r'\bbaşlık\b', 'yön (heading)')],
    'ar': [(r'العرض$', 'عرض فحوصات ما قبل التسليح'), (r'المنزل', 'نقطة الانطلاق (Home)'), (r'السيارة', 'المركبة'),
           (r'عجلة التشغيل', 'الخانق'), (r'الضغط في الوضع اليدوي', 'الخانق في الوضع اليدوي'), (r'التأرجح', 'الانعراج (Yaw)'),
           (r'الالتفاف', 'الانعراج (Yaw)'), (r'طلاء', 'تريم'), (r'السور', 'السياج الجغرافي'), (r'الخطوط العابرة', 'الانحراف الجانبي عن المسار'),
           (r'\bgain\b', 'الكسب'), (r'أكتسب|مكاسب', 'الكسب'), (r'جهاز تحكم', 'وحدة تحكم'), (r'مراقب', 'وحدة تحكم')],
}
_FIXC = {k: [(re.compile(a), b) for a, b in v] for k, v in FIX.items()}


def fix(text, lang):
    if not text or lang not in _FIXC: return text
    for rx, b in _FIXC[lang]: text = rx.sub(b, text)
    return text


def _en(p):
    x = re.split(r'[(\[]', p.split('|')[0])[0]
    return x.replace('?', '').strip()


def prompt(lang):
    """YZ çeviri isteğine eklenecek sözlük özeti."""
    li = 1 if lang == 'tr' else 2
    pairs = [f"{_en(t[0])} = {t[li]}" for t in TERMS[:70]]
    return ('Use standard aviation terminology. Keep flight mode names, acronyms and parameter names unchanged (' + ', '.join(KEEP[:30])
            + ' …). Glossary: ' + '; '.join(pairs))


def lt(d, lang):
    """{'en','tr','ar'} sözlüğünden metin: elle yazılmış çeviri > sözlükle düzeltilmiş makine çevirisi > İngilizce."""
    if not d: return ''
    if d.get(lang): return d[lang]
    en = d.get('en') or ''
    if lang != 'en' and en:
        try:
            from .pcenter import PDB
            x = PDB.get().mt(en, lang)
            if x: return x
        except Exception:
            pass
    return en
