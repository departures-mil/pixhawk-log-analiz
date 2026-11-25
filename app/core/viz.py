"""Görselleştirme bilgisi: uçuş modu bölümleri ve renkleri, kanal görevleri (SERVOn_FUNCTION / RCMAP), motor yerleşimi
ve isimleri, motor olayları (durma, doyma), gerçek saat ve Mission Planner alan/parametre eşlemesi. Grafikler ve arayüz
bu modülü ortak kullanır; hepsi TR / EN / AR."""
from __future__ import annotations
import math, time as _time
import numpy as np
from . import knowledge as K

LG = ('tr', 'en', 'ar')


def _i(lg):
    return LG.index(lg) if lg in LG else 0


def tx(tup, lg):
    return tup[_i(lg)]


# ------------------------------------------------------------------ uçuş modları
# Her modun sabit rengi (ad → renk); aynı mod her grafikte, haritada ve tabloda aynı renktedir.
MODE_COL = {
    'MANUAL': '#64748B', 'STABILIZE': '#0EA5E9', 'TRAINING': '#06B6D4', 'ACRO': '#F43F5E', 'FBWA': '#22C55E', 'FBWB': '#84CC16',
    'CRUISE': '#14B8A6', 'AUTOTUNE': '#EAB308', 'AUTO': '#3B82F6', 'RTL': '#F97316', 'LOITER': '#A855F7', 'TAKEOFF': '#0284C7',
    'AVOID_ADSB': '#EF4444', 'GUIDED': '#6366F1', 'CIRCLE': '#D946EF', 'QSTABILIZE': '#38BDF8', 'QHOVER': '#2DD4BF',
    'QLOITER': '#C084FC', 'QLAND': '#FB7185', 'QRTL': '#FB923C', 'QAUTOTUNE': '#FACC15', 'QACRO': '#FDA4AF', 'THERMAL': '#FDE047',
    'LOITER_ALT_QLAND': '#F472B6', 'AUTOLAND': '#E11D48',
    'ALT_HOLD': '#10B981', 'LAND': '#EC4899', 'DRIFT': '#A3E635', 'SPORT': '#F59E0B', 'FLIP': '#DC2626', 'POSHOLD': '#8B5CF6',
    'BRAKE': '#78716C', 'THROW': '#BE185D', 'GUIDED_NOGPS': '#818CF8', 'SMART_RTL': '#EA580C', 'FLOWHOLD': '#65A30D',
    'FOLLOW': '#0891B2', 'ZIGZAG': '#7C3AED', 'SYSTEMID': '#9CA3AF', 'AUTOROTATE': '#B91C1C', 'AUTO_RTL': '#C2410C', 'TURTLE': '#57534E',
}

MODE_DESC = {
    'MANUAL': ('Pilot kumanda yüzeylerini doğrudan yönetir; otopilot hiçbir düzeltme yapmaz.', 'Pilot drives the control surfaces directly; no autopilot stabilisation.', 'يتحكم الطيار مباشرة بأسطح التحكم؛ لا يقوم الطيار الآلي بأي تصحيح.'),
    'STABILIZE': ('Otopilot uçağı/aracı düz tutar; yön, gaz ve irtifa pilotta.', 'Autopilot keeps the aircraft level; heading, throttle and altitude are up to the pilot.', 'يحافظ الطيار الآلي على استواء المركبة؛ الاتجاه والخانق والارتفاع بيد الطيار.'),
    'TRAINING': ('Eğitim modu: pilot yatış/yunuslama sınırları içinde serbest.', 'Training mode: pilot is free within roll/pitch limits.', 'وضع التدريب: الطيار حر ضمن حدود الدوران والميلان.'),
    'ACRO': ('Akrobasi: çubuk açısal hız ister, otomatik düzeltme yok.', 'Acro: stick commands rotation rate, no self-levelling.', 'الأكروبات: العصا تطلب معدل الدوران دون تسوية تلقائية.'),
    'FBWA': ('Fly-By-Wire A: çubuk yatış/yunuslama açısı ister, otopilot açıları sınırlar; gaz pilotta.', 'Fly-By-Wire A: stick commands bank/pitch angle within limits; throttle is manual.', 'FBWA: العصا تطلب زاوية الدوران/الميلان ضمن حدود؛ الخانق يدوي.'),
    'FBWB': ('Fly-By-Wire B: otopilot irtifa ve hızı tutar; çubuk irtifa/hız değiştirir.', 'Fly-By-Wire B: autopilot holds altitude and speed; stick changes them.', 'FBWB: يحافظ الطيار الآلي على الارتفاع والسرعة؛ العصا تغيّرهما.'),
    'CRUISE': ('Seyir: FBWB gibi, ayrıca rota (yön) kilitlenir.', 'Cruise: like FBWB with heading/track lock.', 'الطيران المستقر: مثل FBWB مع تثبيت المسار.'),
    'AUTOTUNE': ('Otomatik PID ayarı yapılır.', 'Automatic PID tuning in progress.', 'ضبط PID تلقائي.'),
    'AUTO': ('Görev (waypoint) listesini otomatik uçar.', 'Flies the mission (waypoints) automatically.', 'يطير المهمة (نقاط المسار) تلقائياً.'),
    'RTL': ('Eve dönüş: başlangıç noktasına döner.', 'Return to launch: flies back home.', 'العودة إلى نقطة الإقلاع.'),
    'LOITER': ('Bulunduğu noktada daire çizer / yerinde durur.', 'Circles / holds position at the current point.', 'يدور / يثبت فوق النقطة الحالية.'),
    'TAKEOFF': ('Otomatik kalkış.', 'Automatic takeoff.', 'إقلاع تلقائي.'),
    'GUIDED': ('Yer istasyonunun verdiği noktaya gider.', 'Flies to a point given by the ground station.', 'يذهب إلى نقطة تحددها المحطة الأرضية.'),
    'CIRCLE': ('Sabit daire çizer (çoğu zaman failsafe sonrası).', 'Flies a fixed circle (often after a failsafe).', 'يدور في دائرة ثابتة (غالباً بعد طوارئ).'),
    'QSTABILIZE': ('VTOL: kaldırma motorlarıyla düz tutma; gaz ve konum pilotta.', 'VTOL: lift motors keep level; throttle and position are manual.', 'VTOL: محركات الرفع تحافظ على الاستواء؛ الخانق والموقع يدويان.'),
    'QHOVER': ('VTOL: irtifa tutar, yatay konum pilotta.', 'VTOL: holds altitude, horizontal position manual.', 'VTOL: يثبت الارتفاع، الموقع الأفقي يدوي.'),
    'QLOITER': ('VTOL: konum ve irtifa tutar (GPS).', 'VTOL: holds position and altitude (GPS).', 'VTOL: يثبت الموقع والارتفاع (GPS).'),
    'QLAND': ('VTOL: dikey iniş.', 'VTOL: vertical landing.', 'VTOL: هبوط عمودي.'),
    'QRTL': ('VTOL: eve dönüp dikey iner.', 'VTOL: returns home and lands vertically.', 'VTOL: يعود ويهبط عمودياً.'),
    'QAUTOTUNE': ('VTOL PID otomatik ayarı.', 'VTOL automatic PID tuning.', 'ضبط PID تلقائي لـ VTOL.'),
    'QACRO': ('VTOL akrobasi.', 'VTOL acro.', 'أكروبات VTOL.'),
    'THERMAL': ('Termik akımda süzülür.', 'Soars in a thermal.', 'يحلق في تيار حراري.'),
    'LOITER_ALT_QLAND': ('İrtifa kaybedip dikey iniş.', 'Loiters down then lands vertically.', 'يهبط بالدوران ثم يهبط عمودياً.'),
    'AUTOLAND': ('Sabit kanat otomatik iniş.', 'Fixed-wing automatic landing.', 'هبوط تلقائي للجناح الثابت.'),
    'ALT_HOLD': ('İrtifa tutar; yatay konum pilotta.', 'Holds altitude; horizontal position manual.', 'يثبت الارتفاع؛ الموقع الأفقي يدوي.'),
    'LAND': ('Bulunduğu yere iner.', 'Lands at the current location.', 'يهبط في المكان الحالي.'),
    'SPORT': ('Hız kontrollü sportif uçuş.', 'Rate-controlled sport flying.', 'طيران رياضي بالتحكم في المعدل.'),
    'POSHOLD': ('Konum tutma; çubuk bırakılınca durur.', 'Position hold; stops when sticks are released.', 'تثبيت الموقع؛ يتوقف عند ترك العصا.'),
    'BRAKE': ('Hızla durur ve yerinde kalır.', 'Stops quickly and holds.', 'يتوقف بسرعة ويثبت.'),
    'SMART_RTL': ('Geldiği yoldan eve döner.', 'Returns home along the path it came.', 'يعود عبر المسار الذي جاء منه.'),
    'DRIFT': ('Uçak gibi koordineli dönüşler.', 'Plane-like coordinated turns.', 'انعطافات منسقة كالطائرة.'),
    'FLIP': ('Otomatik takla.', 'Automatic flip.', 'انقلاب تلقائي.'),
    'THROW': ('Elden fırlatma ile kalkış.', 'Throw-to-start takeoff.', 'إقلاع بالرمي.'),
    'AUTO_RTL': ('Görevdeki iniş dizisine geçerek döner.', 'Returns via the mission landing sequence.', 'يعود عبر تسلسل الهبوط في المهمة.'),
    'TURTLE': ('Ters dönmüş aracı motorla çevirme.', 'Flips an upside-down vehicle back over.', 'يقلب المركبة المقلوبة.'),
    'AUTOROTATE': ('Helikopter otorotasyon inişi.', 'Helicopter autorotation.', 'الهبوط بالدوران الذاتي للمروحية.'),
}

# ArduPilot ModeReason (AP_Vehicle/ModeReason.h)
REASON = {
    0: ('Bilinmiyor', 'Unknown', 'غير معروف'), 1: ('Kumanda (RC) anahtarı', 'RC switch', 'مفتاح جهاز التحكم'),
    2: ('Yer istasyonu komutu', 'Ground station command', 'أمر المحطة الأرضية'), 3: ('Radyo failsafe', 'Radio failsafe', 'طوارئ الراديو'),
    4: ('Batarya failsafe', 'Battery failsafe', 'طوارئ البطارية'), 5: ('Yer istasyonu failsafe', 'GCS failsafe', 'طوارئ المحطة الأرضية'),
    6: ('EKF failsafe', 'EKF failsafe', 'طوارئ EKF'), 7: ('GPS glitch', 'GPS glitch', 'خلل GPS'), 8: ('Görev bitti', 'Mission end', 'انتهاء المهمة'),
    9: ('Gazla iniş iptali', 'Throttle land escape', 'إلغاء الهبوط بالخانق'), 10: ('Coğrafi sınır ihlali', 'Fence breached', 'خرق السياج'),
    11: ('Arazi failsafe', 'Terrain failsafe', 'طوارئ التضاريس'), 12: ('Fren zaman aşımı', 'Brake timeout', 'انتهاء مهلة الفرملة'),
    13: ('Takla tamamlandı', 'Flip complete', 'اكتمال الانقلاب'), 14: ('Engelden kaçınma', 'Avoidance', 'التجنب'),
    15: ('Kaçınmadan dönüş', 'Avoidance recovery', 'التعافي من التجنب'), 16: ('Fırlatma tamamlandı', 'Throw complete', 'اكتمال الرمي'),
    17: ('Uçuş sonlandırma', 'Terminate', 'إنهاء الطيران'), 18: ('Oyuncak modu', 'Toy mode', 'وضع اللعبة'),
    19: ('Kırım failsafe', 'Crash failsafe', 'طوارئ التحطم'), 20: ('Süzülme (motor çalışıyor)', 'Soaring, motor running', 'التحليق والمحرك يعمل'),
    21: ('Termik algılandı', 'Thermal detected', 'رُصد تيار حراري'), 22: ('Termik zayıfladı', 'Thermal weakened', 'ضعف التيار الحراري'),
    23: ('VTOL geçişi başarısız', 'VTOL transition failed', 'فشل انتقال VTOL'), 24: ('VTOL kalkışı başarısız', 'VTOL takeoff failed', 'فشل إقلاع VTOL'),
    25: ('Failsafe', 'Failsafe', 'الطوارئ'), 26: ('Açılış (başlangıç modu)', 'Initialised (boot mode)', 'بدء التشغيل'),
    27: ('Yüzeye çıkış tamam', 'Surface complete', 'اكتمل الصعود'), 28: ('Derinlik hatası', 'Bad depth', 'خطأ العمق'),
    29: ('Sızıntı failsafe', 'Leak failsafe', 'طوارئ التسرب'), 30: ('Servo testi', 'Servo test', 'اختبار السيرفو'),
    31: ('Açılış', 'Startup', 'بدء التشغيل'), 32: ('Betik (script)', 'Scripting', 'سكربت'), 33: ('Kullanılamıyor', 'Unavailable', 'غير متاح'),
    34: ('Otorotasyon başladı', 'Autorotation start', 'بدء الدوران الذاتي'), 35: ('Otorotasyondan çıkış', 'Autorotation bailout', 'الخروج من الدوران الذاتي'),
    36: ('Süzülme: irtifa yüksek', 'Soaring: altitude too high', 'التحليق: الارتفاع مرتفع'), 37: ('Süzülme: irtifa düşük', 'Soaring: altitude too low', 'التحليق: الارتفاع منخفض'),
    38: ('Süzülme: sürüklenme', 'Soaring: drift exceeded', 'التحليق: تجاوز الانجراف'),
    39: ('RTL bitti → VTOL iniş', 'RTL complete → VTOL land', 'اكتمل RTL ← هبوط VTOL'), 40: ('RTL bitti → sabit kanat iniş', 'RTL complete → fixed-wing autoland', 'اكتمل RTL ← هبوط آلي'),
    41: ('Görev komutu', 'Mission command', 'أمر المهمة'), 42: ('FrSky komutu', 'FrSky command', 'أمر FrSky'),
    43: ('Sınırdan önceki moda dönüş', 'Fence: return to previous mode', 'السياج: العودة للوضع السابق'),
    44: ('RTL yerine QRTL', 'QRTL instead of RTL', 'QRTL بدل RTL'), 45: ('Auto RTL çıkışı', 'Auto RTL exit', 'الخروج من Auto RTL'),
    46: ('İrtifaya ulaşıldı → QLAND', 'Loiter altitude reached → QLAND', 'تم بلوغ الارتفاع ← QLAND'),
    47: ('VTOL\'de bekleme irtifası', 'Loiter altitude in VTOL', 'ارتفاع الانتظار في VTOL'),
    48: ('Radyo failsafe sonrası geri dönüş', 'Radio failsafe recovery', 'التعافي من طوارئ الراديو'),
    49: ('RTL yerine QLAND', 'QLAND instead of RTL', 'QLAND بدل RTL'), 50: ('Tahmini konum failsafe', 'Dead-reckoning failsafe', 'طوارئ الملاحة التقديرية'),
    51: ('Kalkış modu failsafe', 'Takeoff mode failsafe', 'طوارئ وضع الإقلاع'), 52: ('DDS komutu', 'DDS command', 'أمر DDS'),
}
FS_REASONS = {3, 4, 5, 6, 7, 10, 11, 17, 19, 23, 24, 25, 29, 50, 51}


def reason_text(r, lg):
    if r is None or r < 0: return '-'
    return tx(REASON.get(int(r), (f'Kod {r}', f'Code {r}', f'رمز {r}')), lg)


def mode_color(name):
    if name in MODE_COL: return MODE_COL[name]
    h = sum(map(ord, name)) * 47 % 360
    import colorsys
    r, g, b = colorsys.hls_to_rgb(h / 360, 0.55, 0.6)
    return '#%02X%02X%02X' % (int(r * 255), int(g * 255), int(b * 255))


def mode_desc(name, lg):
    d = MODE_DESC.get(name)
    return tx(d, lg) if d else ''


def segments(A, lg='tr'):
    """[{t0, t1, dur, num, name, reason, why, fs, col, prev}] — her mod bölümü (aynı moda yeniden giriş birleştirilir)."""
    L = A.L; end = float(L.duration or 0); out = []
    for t, n, _, r in sorted(L.modes, key=lambda e: e[0]):
        name = K.mode_name(A.vehicle, n)
        if out and out[-1]['name'] == name:
            continue
        if out: out[-1]['t1'] = float(t)
        out.append({'t0': float(t), 't1': end, 'num': int(n), 'name': name, 'reason': int(r), 'why': reason_text(r, lg),
                    'fs': int(r) in FS_REASONS, 'col': mode_color(name), 'prev': out[-1]['name'] if out else '-'})
    if out and out[0]['t0'] > 0.5:   # ilk mod kaydından önceki kısım (bilinmiyor)
        pass
    for s in out:
        s['t1'] = max(s['t1'], s['t0']); s['dur'] = s['t1'] - s['t0']
    return out


def mode_at(A, t, segs=None):
    segs = segs if segs is not None else segments(A)
    cur = None
    for s in segs:
        if s['t0'] <= t: cur = s
        else: break
    return cur


# ------------------------------------------------------------------ saat
def clock(A, t, sec=True):
    """Log zamanı t (s) → bilgisayarın yerel saatiyle gerçek saat (GPS zamanı varsa), yoksa None."""
    u = A.L.unix_at(t) if hasattr(A.L, 'unix_at') else None
    if u is None or u < 1e9: return None
    try:
        return _time.strftime('%H:%M:%S' if sec else '%H:%M', _time.localtime(u))
    except Exception:
        return None


def date_of(A):
    u = A.L.unix_at(0) if hasattr(A.L, 'unix_at') else None
    if u is None or u < 1e9: return None
    try: return _time.strftime('%Y-%m-%d', _time.localtime(u))
    except Exception: return None


def time_us(A, t):
    """Log zamanı t (s) → logdaki ham TimeUS (Mission Planner Review Log'da ara)."""
    return int(round(t * 1e6 + (A.L.t0_us or 0)))


# ------------------------------------------------------------------ kanal görevleri
# SERVOn_FUNCTION → (anahtar, TR, EN, AR, eksenler)
FN = {
    1: ('pass', 'RC geçiş', 'RC passthrough', 'تمرير RC', ''), 2: ('flap', 'Flap', 'Flap', 'القلاب', ''),
    3: ('flap', 'Otomatik flap', 'Auto flap', 'قلاب تلقائي', ''), 4: ('ail', 'Kanatçık', 'Aileron', 'الجنيح', 'R'),
    6: ('mount', 'Gimbal yatay', 'Mount pan', 'تحريك الحامل أفقياً', ''), 7: ('mount', 'Gimbal dikey', 'Mount tilt', 'إمالة الحامل', ''),
    8: ('mount', 'Gimbal yatış', 'Mount roll', 'دوران الحامل', ''), 10: ('cam', 'Kamera tetik', 'Camera trigger', 'زناد الكاميرا', ''),
    16: ('spl', 'Diferansiyel spoyler sol', 'Diff. spoiler left', 'سبويلر تفاضلي يسار', 'RY'), 17: ('spl', 'Diferansiyel spoyler sağ', 'Diff. spoiler right', 'سبويلر تفاضلي يمين', 'RY'),
    19: ('elev', 'İrtifa dümeni', 'Elevator', 'الرافع', 'P'), 21: ('rud', 'İstikamet dümeni', 'Rudder', 'الدفة', 'Y'),
    24: ('flpr', 'Flaperon sol', 'Flaperon left', 'فلابيرون يسار', 'R'), 25: ('flpr', 'Flaperon sağ', 'Flaperon right', 'فلابيرون يمين', 'R'),
    26: ('steer', 'Yer dümeni', 'Ground steering', 'توجيه أرضي', 'Y'), 27: ('para', 'Paraşüt', 'Parachute', 'المظلة', ''),
    28: ('grip', 'Tutucu', 'Gripper', 'الماسك', ''), 29: ('gear', 'İniş takımı', 'Landing gear', 'عجلات الهبوط', ''),
    30: ('eng', 'Motor çalıştırma', 'Engine run enable', 'تمكين المحرك', ''), 31: ('rsc', 'Ana rotor hız kontrolü (RSC)', 'Main rotor RSC', 'التحكم بسرعة الدوار الرئيسي', 'T'),
    32: ('trsc', 'Kuyruk rotoru hız kontrolü', 'Tail rotor RSC', 'التحكم بسرعة الدوار الخلفي', 'Y'),
    41: ('tilt', 'Motor eğme (ön)', 'Tilt motors front', 'إمالة المحركات الأمامية', ''), 45: ('tilt', 'Motor eğme (arka)', 'Tilt motors rear', 'إمالة المحركات الخلفية', ''),
    67: ('ign', 'Ateşleme', 'Ignition', 'الإشعال', ''), 69: ('start', 'Marş', 'Starter', 'بادئ التشغيل', ''),
    70: ('thr', 'Gaz', 'Throttle', 'الخانق', 'T'), 73: ('thr', 'Gaz sol', 'Throttle left', 'الخانق الأيسر', 'TY'),
    74: ('thr', 'Gaz sağ', 'Throttle right', 'الخانق الأيمن', 'TY'), 75: ('tilt', 'Motor eğme ön sol', 'Tilt front left', 'إمالة أمامي يسار', ''),
    76: ('tilt', 'Motor eğme ön sağ', 'Tilt front right', 'إمالة أمامي يمين', ''), 77: ('elvn', 'Elevon sol', 'Elevon left', 'إليفون يسار', 'RP'),
    78: ('elvn', 'Elevon sağ', 'Elevon right', 'إليفون يمين', 'RP'), 79: ('vtail', 'V kuyruk sol', 'V-tail left', 'ذيل V يسار', 'PY'),
    80: ('vtail', 'V kuyruk sağ', 'V-tail right', 'ذيل V يمين', 'PY'), 81: ('thr', 'Takviye motoru gazı', 'Boost throttle', 'خانق التعزيز', 'T'),
    86: ('spl', 'Diferansiyel spoyler sol 2', 'Diff. spoiler left 2', 'سبويلر تفاضلي يسار 2', 'RY'), 87: ('spl', 'Diferansiyel spoyler sağ 2', 'Diff. spoiler right 2', 'سبويلر تفاضلي يمين 2', 'RY'),
    110: ('abrk', 'Hava freni', 'Airbrakes', 'المكابح الهوائية', ''),
}
AX = {'R': ('Roll', 'Roll', 'الدوران'), 'P': ('Pitch', 'Pitch', 'الميلان'), 'Y': ('Yaw', 'Yaw', 'الانعراج'), 'T': ('Gaz', 'Throttle', 'الخانق')}


def servo_fn(P, n):
    f = P.get(f'SERVO{n}_FUNCTION', P.get(f'RC{n}_FUNCTION'))
    try: return int(f) if f is not None else None
    except Exception: return None


def motor_map(A):
    """[(motor_no, 'Cn')] — kaldırma motorları. Sabit kanatta yalnız SERVOn_FUNCTION 33–40/82–85 olan kanallar
    (VTOL değilse FRAME_CLASS varsayımı yapılmaz; aksi halde kanatçık/dümen kanalları motor sanılır)."""
    if A.vehicle == 'Plane':
        P = A.L.params; o = A.L.s('RCOU'); out = []
        for n in range(1, 17):
            f = servo_fn(P, n)
            if f is None: continue
            m = f - 32 if 33 <= f <= 40 else (f - 73 if 82 <= f <= 85 else None)
            if m and o.has(f'C{n}'): out.append((m, f'C{n}'))
        return sorted(out)
    try: return A.motor_channels()
    except Exception: return []


def channel_roles(A, lg='tr'):
    """[{ch: 'C1', n, fn, key, name, axes, kind: ctrl|thr|motor|other, motor}] — RCOU kanallarının görevi."""
    P = A.L.params; o = A.L.s('RCOU'); out = []
    mot = dict((c, m) for m, c in motor_map(A))
    for n in range(1, 17):
        ch = f'C{n}'
        if not o.has(ch): continue
        f = servo_fn(P, n)
        if ch in mot:
            out.append({'ch': ch, 'n': n, 'fn': f, 'key': 'motor', 'name': motor_name(A, mot[ch], lg), 'axes': 'T', 'kind': 'motor', 'motor': mot[ch]}); continue
        if f is None:
            if A.vehicle == 'Plane' and n <= 4:   # parametresiz eski log: AETR varsayılanı
                f = {1: 4, 2: 19, 3: 70, 4: 21}[n]
            else: continue
        if 51 <= f <= 66:
            out.append({'ch': ch, 'n': n, 'fn': f, 'key': 'rcin', 'name': tx(('RC giriş', 'RC input', 'إدخال RC'), lg) + f' {f - 50}', 'axes': '', 'kind': 'other'}); continue
        d = FN.get(f)
        if not d: continue
        kind = 'thr' if d[0] == 'thr' else ('ctrl' if d[4] and d[0] not in ('rsc', 'trsc') else 'other')
        out.append({'ch': ch, 'n': n, 'fn': f, 'key': d[0], 'name': d[1 + _i(lg)], 'axes': d[4], 'kind': kind})
    return out


def role_label(r, lg, A=None):
    ax = '+'.join(tx(AX[a], lg) for a in r['axes'] if a in AX and r['kind'] != 'motor')
    rev = ''
    if A is not None and A.L.params.get(f"SERVO{r['ch'][1:]}_REVERSED") in (1, 1.0):
        rev = ' [' + tx(('ters', 'reversed', 'معكوس'), lg) + ']'
    return f"{r['ch']} · {r['name']}" + (f' ({ax})' if ax else '') + rev


def rc_map(A):
    """{'roll': n, 'pitch': n, 'thr': n, 'yaw': n, 'mode': n} — kumanda giriş kanalları (RCMAP_*, FLTMODE_CH)."""
    P = A.L.params
    g = lambda k, d: int(P.get(k, d) or d)
    m = {'roll': g('RCMAP_ROLL', 1), 'pitch': g('RCMAP_PITCH', 2), 'thr': g('RCMAP_THROTTLE', 3), 'yaw': g('RCMAP_YAW', 4)}
    fc = P.get('FLTMODE_CH', P.get('MODE_CH'))
    if fc is None and A.vehicle != 'Plane': fc = 5
    if fc is None and A.vehicle == 'Plane': fc = 8
    try:
        fc = int(fc)
        if fc > 0: m['mode'] = fc
    except Exception: pass
    return m


def rc_active(A):
    """Logda gerçek kumanda girişi var mı (alıcı bağlı ve stickler hareket ediyor ya da gaz > 800 µs)."""
    r = A.L.s('RCIN'); m = rc_map(A)
    for k in ('roll', 'pitch', 'thr', 'yaw'):
        c = f"C{m[k]}"
        if not r.has(c): continue
        v = np.asarray(r[c], float); v = v[v > 800]
        if len(v) > 10 and (np.nanmax(v) - np.nanmin(v) > 25 or k == 'thr'): return True
    return False


def stick_norm(A, n, v, centred=True):
    """RCn PWM → -100..100 (centred) ya da 0..100 (gaz), RCn_MIN/MAX/TRIM/REVERSED ile."""
    P = A.L.params
    lo = float(P.get(f'RC{n}_MIN', 1100) or 1100); hi = float(P.get(f'RC{n}_MAX', 1900) or 1900)
    tr = float(P.get(f'RC{n}_TRIM', (lo + hi) / 2) or (lo + hi) / 2)
    if hi - lo < 100: lo, hi, tr = 1000.0, 2000.0, 1500.0
    v = np.asarray(v, float)
    if centred:
        out = np.where(v >= tr, (v - tr) / max(hi - tr, 1), (v - tr) / max(tr - lo, 1)) * 100
    else:
        out = (v - lo) / (hi - lo) * 100
    if P.get(f'RC{n}_REVERSED') in (1, 1.0): out = -out if centred else 100 - out
    out = np.where(v < 800, np.nan, out)    # 0 = sinyal yok
    return np.clip(out, -110 if centred else -5, 110)


# ------------------------------------------------------------------ motor yerleşimi ve isimleri
# AP_MotorsMatrix açıları (derece, 0 = ön, + saat yönü/sağ); FRAME_CLASS → FRAME_TYPE → [açılar]
LAYOUT = {
    1: {0: [90, -90, 0, 180], 1: [45, -135, -45, 135], 2: [45, -135, -45, 135], 3: [45, -135, -45, 135], 13: [45, -135, -45, 135],
        12: [45, -135, -45, 135], 14: [45, -135, -45, 135], 18: [45, -135, -45, 135], 4: [30, -150, -30, 150], 5: [45, -135, -45, 135],
        16: [45, -135, -45, 135]},
    2: {0: [0, 180, -120, 60, -60, 120], 1: [90, -90, -30, 150, 30, -150], 3: [90, -90, -30, 150, 30, -150], 13: [90, -90, -30, 150, 30, -150]},
    3: {0: [0, 180, 45, 135, -45, -135, -90, 90], 1: [22.5, -157.5, 67.5, 157.5, -22.5, -112.5, -67.5, 112.5],
        2: [0, 180, 45, 135, -45, -135, -90, 90], 3: [22.5, -157.5, 67.5, 157.5, -22.5, -112.5, -67.5, 112.5]},
    4: {0: [0, -90, 180, 90, 0, -90, 180, 90], 1: [45, -45, -135, 135, 45, -45, -135, 135]},   # OctaQuad (üst/alt)
    5: {10: [60, 60, 180, 180, -60, -60], 0: [-60, -60, 60, 60, 180, 180], 1: [-60, -60, 60, 60, 180, 180]},   # Y6
    7: {0: [60, -60, 0, 180]},   # Tri: M1, M2, (M3 yok), M4 arka; kuyruk servosu
    10: {0: [0, 180]},           # Tek/çift rotor (yaklaşık)
}
COAX = {4, 5}   # üst-alt motor çiftleri

DIR8 = [('Ön', 'Front', 'أمامي'), ('Ön sağ', 'Front right', 'أمامي أيمن'), ('Sağ', 'Right', 'أيمن'), ('Arka sağ', 'Rear right', 'خلفي أيمن'),
        ('Arka', 'Rear', 'خلفي'), ('Arka sol', 'Rear left', 'خلفي أيسر'), ('Sol', 'Left', 'أيسر'), ('Ön sol', 'Front left', 'أمامي أيسر')]


def _frame(A):
    P = A.L.params
    if A.vehicle == 'Plane':
        if not int(P.get('Q_ENABLE', 0) or 0) and not motor_map(A): return None, None
        return int(P.get('Q_FRAME_CLASS', 1) or 1), int(P.get('Q_FRAME_TYPE', 1) or 1)
    return int(P.get('FRAME_CLASS', 1) or 1), int(P.get('FRAME_TYPE', 1) or 1)


def motor_angle(A, m):
    fc, ft = _frame(A)
    if fc is None: return None
    tbl = LAYOUT.get(fc, {})
    ang = tbl.get(ft) or (next(iter(tbl.values())) if tbl else None)
    if not ang or m < 1 or m > len(ang): return None
    return ang[m - 1]


def _dir_name(a, lg):
    k = int(round(((a % 360) + 360) % 360 / 45.0)) % 8
    return tx(DIR8[k], lg)


def motor_name(A, m, lg='tr'):
    """'M4 · Arka sağ' — motor numarası ve yeri (çerçeve tipine göre)."""
    fc, ft = _frame(A)
    a = motor_angle(A, m)
    if a is None: return f'M{m}'
    nm = _dir_name(a, lg)
    if fc == 3 or (fc == 2 and a % 45):     # octa X / hexa: aynı sektöre düşen motorlarda açıyı da yaz
        nm += f' {int(round(a % 360))}°'
    if fc in COAX:
        top = (m % 2 == 1) if fc == 5 else (m <= 4)
        nm += ' ' + tx(('üst', 'top', 'علوي') if top else ('alt', 'bottom', 'سفلي'), lg)
    return f'M{m} · {nm}'


def motors(A, lg='tr'):
    """[{m, ch, name, angle, kind: lift|push|rotor|tail}] — tüm motorlar (VTOL'de kaldırma + itiş)."""
    out = []
    mc = motor_map(A)
    for m, ch in mc:
        out.append({'m': m, 'ch': ch, 'name': motor_name(A, m, lg), 'angle': motor_angle(A, m), 'kind': 'lift'})
    P = A.L.params; o = A.L.s('RCOU')
    for n in range(1, 17):
        f = servo_fn(P, n)
        if f in (70, 73, 74, 81) and o.has(f'C{n}') and (A.vehicle == 'Plane' or f != 70):
            nm = {70: ('İtiş motoru', 'Pusher motor', 'محرك الدفع'), 73: ('İtiş motoru sol', 'Pusher left', 'محرك الدفع الأيسر'),
                  74: ('İtiş motoru sağ', 'Pusher right', 'محرك الدفع الأيمن'), 81: ('Takviye motoru', 'Boost motor', 'محرك التعزيز')}[f]
            if not mc: nm = {70: ('Motor (gaz)', 'Motor (throttle)', 'المحرك (الخانق)')}.get(f, nm)
            out.append({'m': None, 'ch': f'C{n}', 'name': tx(nm, lg), 'angle': None, 'kind': 'push'})
        elif f in (31, 32) and o.has(f'C{n}'):
            out.append({'m': None, 'ch': f'C{n}', 'name': tx(FN[f][1:4], lg), 'angle': None, 'kind': 'rotor' if f == 31 else 'tail'})
    return out


def frame_text(A, lg='tr'):
    fc, ft = _frame(A)
    if fc is None: return tx(('Sabit kanat', 'Fixed wing', 'جناح ثابت'), lg)
    cls = {1: 'Quad', 2: 'Hexa', 3: 'Octa', 4: 'OctaQuad', 5: 'Y6', 6: 'Heli', 7: 'Tri', 10: 'Single', 11: 'Heli dual', 12: 'DodecaHexa',
           13: 'Heli quad', 14: 'Deca'}.get(fc, f'class {fc}')
    typ = {0: '+', 1: 'X', 2: 'V', 3: 'H', 4: 'V-tail', 5: 'A-tail', 10: 'Y6B', 11: 'Y6F', 12: 'BetaFlight X', 13: 'DJI X', 14: 'Clockwise X',
           18: 'BetaFlight X rev'}.get(ft, str(ft))
    pre = 'VTOL ' if A.vehicle == 'Plane' else ''
    return f'{pre}{cls} {typ}'


# ------------------------------------------------------------------ motor olayları
def motor_events(A, lg='tr'):
    """Her motor için: ortalama, pay, doyma/durma süreleri ve olaylar [{t, m, ch, kind: stop|sat|weak|esc, name}].
    Kural motoru (analysis.motor_fault) bulduğu olayı da ekler; asıl kök neden onunla tutarlı kalır."""
    o = A.L.s('RCOU'); M = [x for x in motors(A, lg) if x['kind'] == 'lift']
    res = {'motors': [], 'events': []}
    if not M or not o.has(M[0]['ch']): return res
    try: hi, lo_spin = A._mot_limits()
    except Exception: hi, lo_spin = 1950.0, 1150.0
    P = A.L.params; q = 'Q_M_' if A.vehicle == 'Plane' else 'MOT_'
    pmin = float(P.get(q + 'PWM_MIN', 0) or 0) or 1000.0
    t = o['t']; X = np.vstack([np.asarray(o[x['ch']], float) for x in M])
    # yalnız uçuşta ve kaldırma motorları gerçekten çalışırken
    fl = np.zeros(len(t), bool)
    for a, b in (A.flights or []):
        fl |= (t >= a) & (t <= b)
    mean = np.nanmean(X, axis=0)
    act = fl & (mean > lo_spin + 40)
    dt = float(np.median(np.diff(t))) if len(t) > 2 else 0.1
    for i, x in enumerate(M):
        v = X[i]; a = act
        sat = a & (v >= hi - 8); stop = a & (v <= pmin + 30) & (np.delete(X, i, 0).mean(axis=0) > lo_spin + 150 if len(M) > 1 else False)
        res['motors'].append({**x, 'mean': float(np.nanmean(v[a])) if a.any() else None,
                              'sat_s': float(sat.sum() * dt), 'stop_s': float(stop.sum() * dt), 'max': float(np.nanmax(v)) if len(v) else None})
        for kind, mask, need in (('sat', sat, 1.0), ('stop', stop, 0.5)):
            if not mask.any(): continue
            # en uzun kesintisiz bölüm
            idx = np.flatnonzero(mask); br = np.flatnonzero(np.diff(idx) > max(1, int(0.5 / max(dt, 1e-3))))
            starts = np.r_[idx[0], idx[br + 1]]; ends = np.r_[idx[br], idx[-1]]
            for s0, e0 in zip(starts, ends):
                if t[e0] - t[s0] >= need:
                    res['events'].append({'t': float(t[s0]), 't1': float(t[e0]), 'm': x['m'], 'ch': x['ch'], 'kind': kind, 'name': x['name']})
    if res['motors'] and all(r['mean'] for r in res['motors']):
        mu = np.mean([r['mean'] for r in res['motors']])
        for r in res['motors']: r['share'] = (r['mean'] - mu)
    mf = getattr(A, 'motor_fault', None)
    if mf and mf.get('m'):
        x = next((y for y in M if y['m'] == mf['m']), None)
        if x:
            kind = {'sat': 'sat', 'floor': 'sat', 'weak': 'weak', 'esc': 'stop'}.get(mf.get('kind'), 'sat')
            if not any(e['m'] == x['m'] and e['kind'] == kind and abs(e['t'] - mf['t']) < 3 for e in res['events']):
                res['events'].append({'t': float(mf['t']), 't1': float(mf['t']), 'm': x['m'], 'ch': x['ch'], 'kind': kind, 'name': x['name'], 'root': True})
            else:
                for e in res['events']:
                    if e['m'] == x['m'] and e['kind'] == kind: e['root'] = True
            if mf.get('o'):
                y = next((z for z in M if z['m'] == mf['o']), None)
                if y: res['opp'] = y
    res['events'].sort(key=lambda e: (not e.get('root'), e['t']))
    return res


EV_TXT = {'sat': ('tam güce kilitlendi (doyma)', 'pinned at full power (saturated)', 'علق عند القدرة القصوى (تشبع)'),
          'stop': ('durdu', 'stopped', 'توقف'), 'weak': ('zayıf: sürekli en yüksek çıkışı istiyor', 'weak: constantly needs the highest output', 'ضعيف: يحتاج باستمرار أعلى خرج')}


def event_text(A, e, lg='tr', fmt=None):
    from .analysis import fmt_t
    c = clock(A, e['t'])
    tt = fmt_t(e['t']) + (f' ({c})' if c else '')
    return f"{e['name']} ({e['ch']}) {tt} — {tx(EV_TXT[e['kind']], lg)}"


# ------------------------------------------------------------------ Mission Planner eşlemesi
MP = {
    'c_overview': (['GPS.Alt', 'GPS.Spd', 'BAT.Volt', 'VIBE.VibeZ', 'GPS.NSats', 'MODE.Mode'], []),
    'c_alt': (['GPS.Alt', 'BARO.Alt', 'CTUN.As' , 'ARSP.Airspeed', 'GPS.Spd', 'MODE.Mode'], ['AIRSPEED_MIN', 'AIRSPEED_MAX', 'AIRSPEED_CRUISE', 'ARSPD_FBW_MIN', 'ARSPD_FBW_MAX']),
    'c_att': (['ATT.Roll', 'ATT.DesRoll', 'ATT.Pitch', 'ATT.DesPitch', 'ATT.Yaw', 'ATT.DesYaw'], ['ROLL_LIMIT_DEG', 'PTCH_LIM_MAX_DEG', 'PTCH_LIM_MIN_DEG', 'ANGLE_MAX']),
    'c_sticks': (['RCIN.C1', 'RCIN.C2', 'RCIN.C3', 'RCIN.C4', 'RCIN.C5', 'RCIN.C6', 'RCIN.C7', 'RCIN.C8'], ['RCMAP_ROLL', 'RCMAP_PITCH', 'RCMAP_THROTTLE', 'RCMAP_YAW', 'FLTMODE_CH', 'MODE_CH', 'THR_FS_VALUE', 'FS_THR_VALUE', 'RC1_MIN', 'RC1_MAX', 'RC1_TRIM', 'RC3_MIN', 'RC3_MAX']),
    'c_rcou': (['RCOU.C1', 'RCOU.C2', 'RCOU.C3', 'RCOU.C4', 'CTUN.ThO', 'AETR.Ail', 'AETR.Elev', 'AETR.Thr', 'AETR.Rudd'], ['SERVO1_FUNCTION', 'SERVO2_FUNCTION', 'SERVO3_FUNCTION', 'SERVO4_FUNCTION', 'SERVO1_REVERSED', 'SERVO2_REVERSED', 'SERVO1_MIN', 'SERVO1_MAX', 'SERVO1_TRIM']),
    'c_motors': (['RCOU.C1', 'RCOU.C2', 'RCOU.C3', 'RCOU.C4', 'RCOU.C5', 'RCOU.C6', 'RCOU.C7', 'RCOU.C8', 'ESC.RPM'], ['FRAME_CLASS', 'FRAME_TYPE', 'Q_FRAME_CLASS', 'Q_FRAME_TYPE', 'MOT_PWM_MIN', 'MOT_PWM_MAX', 'MOT_SPIN_MIN', 'MOT_SPIN_MAX', 'MOT_THST_HOVER', 'Q_M_PWM_MIN', 'Q_M_PWM_MAX', 'Q_M_SPIN_MIN', 'Q_M_SPIN_MAX', 'Q_M_THST_HOVER']),
    'c_speed': (['ARSP.Airspeed', 'GPS.Spd', 'TECS.spdem', 'XKF2.VWN', 'XKF2.VWE', 'CTUN.As'], ['AIRSPEED_MIN', 'AIRSPEED_MAX', 'AIRSPEED_CRUISE', 'ARSPD_FBW_MIN', 'ARSPD_FBW_MAX', 'ARSPD_RATIO']),
    'c_tecs': (['TECS.h', 'TECS.hdem', 'TECS.sp', 'TECS.spdem', 'TECS.th', 'TECS.ph', 'CTUN.Alt', 'CTUN.DAlt', 'CTUN.CRt', 'CTUN.DCRt'], ['TECS_SPDWEIGHT', 'TECS_TIME_CONST', 'TECS_CLMB_MAX', 'TECS_SINK_MAX', 'THR_MAX', 'THR_MIN', 'TRIM_THROTTLE', 'PSC_POSZ_P', 'PSC_ACCZ_P']),
    'c_pid': (['PIDR.Tar', 'PIDR.Act', 'PIDR.P', 'PIDR.I', 'PIDR.D', 'PIDR.FF', 'PIDP.Tar', 'PIDP.Act', 'PIDY.Tar', 'PIDY.Act'], ['RLL_RATE_P', 'RLL_RATE_I', 'RLL_RATE_D', 'RLL_RATE_FF', 'PTCH_RATE_P', 'PTCH_RATE_FF', 'ATC_RAT_RLL_P', 'ATC_RAT_PIT_P', 'ATC_RAT_YAW_P', 'Q_A_RAT_RLL_P']),
    'c_nav': (['NTUN.Dist', 'NTUN.XT', 'NTUN.AltE', 'NTUN.WpDist', 'CMD.CNum'], ['NAVL1_PERIOD', 'NAVL1_DAMPING', 'WP_RADIUS', 'WPNAV_SPEED', 'WP_LOITER_RAD']),
    'c_gps': (['GPS.NSats', 'GPS.HDop', 'GPA.HAcc', 'GPA.VAcc', 'GPA.SAcc', 'GPS.Status'], ['GPS_TYPE', 'GPS_GNSS_MODE', 'EK3_SRC1_POSXY', 'GPS_AUTO_SWITCH']),
    'c_vibe': (['VIBE.VibeX', 'VIBE.VibeY', 'VIBE.VibeZ', 'VIBE.Clip'], ['INS_ACCEL_FILTER', 'INS_GYRO_FILTER']),
    'c_fft': (['IMU.AccX', 'IMU.AccY', 'IMU.AccZ', 'FTN1.PkAvg', 'ISBD'], ['INS_HNTCH_ENABLE', 'INS_HNTCH_FREQ', 'INS_HNTCH_BW', 'INS_HNTCH_REF', 'INS_HNTCH_MODE', 'INS_LOG_BAT_MASK', 'INS_FAST_SAMPLE']),
    'c_imu': (['IMU[0].AccZ', 'IMU[1].AccZ', 'IMU[0].GyrX', 'IMU[1].GyrX', 'BARO.Alt', 'GPS.Alt', 'POS.RelHomeAlt'], ['INS_USE2', 'INS_USE3', 'EK3_IMU_MASK', 'EK3_SRC1_POSZ']),
    'c_bat': (['BAT.Volt', 'BAT.Curr', 'BAT.CurrTot', 'BAT.Res', 'POWR.Vcc'], ['BATT_MONITOR', 'BATT_CAPACITY', 'BATT_LOW_VOLT', 'BATT_CRT_VOLT', 'BATT_LOW_MAH', 'BATT_CRT_MAH', 'BATT_FS_LOW_ACT', 'BATT_AMP_PERVLT', 'BATT_VOLT_MULT']),
    'c_esc': (['ESC.RPM', 'ESC.Curr', 'ESC.Temp', 'ESC.Volt'], ['SERVO_BLH_AUTO', 'SERVO_BLH_TRATE', 'SERVO_BLH_POLES', 'MOT_PWM_TYPE']),
    'c_ekf': (['XKF4.SV', 'XKF4.SP', 'XKF4.SH', 'XKF4.SM', 'XKF3.IVN', 'XKF3.IPN', 'XKF3.IPD', 'XKF3.IMX', 'XKFS.SS'], ['EK3_ENABLE', 'EK3_GPS_CHECK', 'EK3_MAG_CAL', 'FS_EKF_THRESH', 'FS_EKF_ACTION', 'EK3_AFFINITY']),
    'c_mag': (['MAG.MagX', 'MAG.MagY', 'MAG.MagZ', 'MAG[1].MagX', 'BAT.Curr', 'CTUN.ThO'], ['COMPASS_USE', 'COMPASS_USE2', 'COMPASS_MOTCT', 'COMPASS_OFS_X', 'COMPASS_ORIENT', 'COMPASS_EXTERNAL']),
    'c_health': ([], []),
    'c_timeline': (['MODE.Mode', 'MODE.Rsn', 'EV.Id', 'ERR.Subsys', 'ERR.ECode', 'MSG.Message'], ['FLTMODE_CH', 'FLTMODE1', 'FLTMODE2', 'FLTMODE3', 'FLTMODE4', 'FLTMODE5', 'FLTMODE6', 'FS_SHORT_ACTN', 'FS_LONG_ACTN']),
}


def mp_info(A, key):
    """(alanlar, [(param, değer)]) — logda bulunanlar."""
    f, p = MP.get(key, ([], []))
    L = A.L; ok = []
    for x in f:
        msg, _, fld = x.partition('.')
        base = msg.split('[')[0]
        if msg in L.msgs or base in L.msgs or any(k.startswith(base + '[') for k in L.msgs) or (base in ('MODE', 'EV', 'ERR', 'MSG', 'ISBD', 'CMD')):
            ok.append(x)
    if key in ('c_rcou', 'c_motors'):
        rl = channel_roles(A) if key == 'c_rcou' else [{'ch': m['ch']} for m in motors(A)]
        ok = [f'RCOU.{r["ch"]}' for r in rl] + [x for x in ok if not x.startswith('RCOU.')]
        pp = [f'SERVO{r["ch"][1:]}_FUNCTION' for r in rl]
        p = pp + [f'SERVO{r["ch"][1:]}_{s}' for r in rl for s in ('MIN', 'MAX', 'TRIM', 'REVERSED') if key == 'c_rcou'] + list(p)
    if key == 'c_sticks':
        m = rc_map(A); ok = [f'RCIN.C{n}' for n in m.values()]
        p = [f'RC{n}_{s}' for n in m.values() for s in ('MIN', 'MAX', 'TRIM', 'REVERSED')] + list(p)
    seen = set(); pv = []
    for k in p:
        if k in L.params and k not in seen:
            seen.add(k); pv.append((k, L.params[k]))
    return ok, pv


def mavgraphs_xml(A, lg='tr'):
    """Mission Planner / MAVExplorer grafik listesi (mavgraphs biçimi): bu logdaki tüm grafikler."""
    from .rtexts import RT
    import html as H
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<graphs>']
    for key, (f, _) in MP.items():
        flds, _p = mp_info(A, key)
        flds = [x for x in flds if '.' in x and not x.endswith('.Message')]
        if not flds: continue
        nm = RT.get(key, (key, key, key))[_i(lg)]
        out.append(f'  <graph name="Pixhawk Log Analiz/{H.escape(nm)}">')
        out.append(f'    <description>{H.escape(nm)}</description>')
        out.append(f'    <expression>{H.escape(" ".join(flds))}</expression>')
        out.append('  </graph>')
    out.append('</graphs>')
    return '\n'.join(out) + '\n'
