"""ArduPilot kod tabloları (ERR alt sistemleri, EV olayları, uçuş modları) — TR / EN / AR."""

PLANE_MODES = {0: 'MANUAL', 1: 'CIRCLE', 2: 'STABILIZE', 3: 'TRAINING', 4: 'ACRO', 5: 'FBWA', 6: 'FBWB', 7: 'CRUISE',
               8: 'AUTOTUNE', 10: 'AUTO', 11: 'RTL', 12: 'LOITER', 13: 'TAKEOFF', 14: 'AVOID_ADSB', 15: 'GUIDED',
               17: 'QSTABILIZE', 18: 'QHOVER', 19: 'QLOITER', 20: 'QLAND', 21: 'QRTL', 22: 'QAUTOTUNE', 23: 'QACRO',
               24: 'THERMAL', 25: 'LOITER_ALT_QLAND', 26: 'AUTOLAND'}
COPTER_MODES = {0: 'STABILIZE', 1: 'ACRO', 2: 'ALT_HOLD', 3: 'AUTO', 4: 'GUIDED', 5: 'LOITER', 6: 'RTL', 7: 'CIRCLE',
                9: 'LAND', 11: 'DRIFT', 13: 'SPORT', 14: 'FLIP', 15: 'AUTOTUNE', 16: 'POSHOLD', 17: 'BRAKE', 18: 'THROW',
                19: 'AVOID_ADSB', 20: 'GUIDED_NOGPS', 21: 'SMART_RTL', 22: 'FLOWHOLD', 23: 'FOLLOW', 24: 'ZIGZAG',
                25: 'SYSTEMID', 26: 'AUTOROTATE', 27: 'AUTO_RTL', 28: 'TURTLE'}
AUTO_MODES = {'Plane': {10, 11, 12, 13, 15, 1, 21, 20, 26}, 'Copter': {3, 4, 6, 9, 21, 27, 5, 16}}
RTL_MODES = {'Plane': {11, 21}, 'Copter': {6, 21, 27}}
LAND_MODES = {'Plane': {20, 26}, 'Copter': {9}}


def mode_name(vehicle, num):
    tbl = COPTER_MODES if vehicle == 'Copter' else PLANE_MODES
    return tbl.get(int(num), f'MODE{int(num)}')


MODE_REASON = {
    0: ('Bilinmiyor', 'Unknown', 'غير معروف'), 1: ('RC komutu', 'RC command', 'أمر RC'), 2: ('YKİ komutu', 'GCS command', 'أمر المحطة الأرضية'),
    3: ('Radyo failsafe', 'Radio failsafe', 'طوارئ الراديو'), 4: ('Batarya failsafe', 'Battery failsafe', 'طوارئ البطارية'),
    5: ('YKİ failsafe', 'GCS failsafe', 'طوارئ المحطة الأرضية'), 6: ('EKF failsafe', 'EKF failsafe', 'طوارئ EKF'),
    7: ('GPS glitch', 'GPS glitch', 'خلل GPS'), 8: ('Görev bitti', 'Mission end', 'انتهاء المهمة'),
    9: ('Gazla iniş iptali', 'Throttle land escape', 'إلغاء الهبوط بالخانق'), 10: ('Coğrafi sınır ihlali', 'Fence breached', 'خرق السياج الجغرافي'),
    11: ('Arazi failsafe', 'Terrain failsafe', 'طوارئ التضاريس'), 12: ('Fren zaman aşımı', 'Brake timeout', 'انتهاء مهلة الفرملة'),
    13: ('Flip tamamlandı', 'Flip complete', 'اكتمال الانقلاب'), 14: ('Kaçınma', 'Avoidance', 'التجنب'),
    15: ('Kaçınmadan dönüş', 'Avoidance recovery', 'التعافي من التجنب'), 16: ('Fırlatma tamamlandı', 'Throw complete', 'اكتمال الرمي'),
    17: ('Uçuşu sonlandırma', 'Terminate', 'إنهاء الطيران'), 18: ('Oyuncak modu', 'Toy mode', 'وضع اللعبة'),
    19: ('Kırım failsafe', 'Crash failsafe', 'طوارئ التحطم'), 20: ('Süzülme (motor çalışıyor)', 'Soaring (motor running)', 'التحليق (المحرك يعمل)'),
    21: ('Termik algılandı', 'Thermal detected', 'تم اكتشاف تيار حراري'), 22: ('Termik bitti', 'Thermal ended', 'انتهى التيار الحراري'),
    23: ('VTOL hata', 'VTOL failed transition', 'فشل انتقال VTOL'), 24: ('VTOL iniş', 'VTOL failsafe', 'طوارئ VTOL'),
    25: ('Görev komutu', 'Mission command', 'أمر المهمة'), 26: ('Kalkış tamamlandı', 'Takeoff complete', 'اكتمل الإقلاع'),
    27: ('Kalkış başladı', 'Takeoff', 'الإقلاع'), 32: ('Betik (script)', 'Scripting', 'السكربت'),
    40: ('Hava hızı yok (QuadPlane)', 'Airspeed failure', 'فشل السرعة الجوية'), 45: ('Kalkış tamam', 'Auto takeoff complete', 'اكتمل الإقلاع الآلي'),
}
FAILSAFE_REASONS = {3, 4, 5, 6, 7, 10, 11, 19, 24}

ERR_SUBSYS = {
    1: ('Ana döngü', 'Main', 'الحلقة الرئيسية'), 2: ('Radyo', 'Radio', 'الراديو'), 3: ('Pusula', 'Compass', 'البوصلة'),
    4: ('Optik akış', 'Optical flow', 'التدفق البصري'), 5: ('Radyo failsafe', 'Radio failsafe', 'طوارئ الراديو'),
    6: ('Batarya failsafe', 'Battery failsafe', 'طوارئ البطارية'), 7: ('GPS failsafe', 'GPS failsafe', 'طوارئ GPS'),
    8: ('YKİ failsafe', 'GCS failsafe', 'طوارئ المحطة الأرضية'), 9: ('Coğrafi sınır failsafe', 'Fence failsafe', 'طوارئ السياج'),
    10: ('Uçuş modu', 'Flight mode', 'وضع الطيران'), 11: ('GPS', 'GPS', 'GPS'), 12: ('Kırım kontrolü', 'Crash check', 'فحص التحطم'),
    13: ('Flip', 'Flip', 'الانقلاب'), 14: ('Otomatik ayar', 'Autotune', 'الضبط الآلي'), 15: ('Paraşüt', 'Parachute', 'المظلة'),
    16: ('EKF kontrolü', 'EKF check', 'فحص EKF'), 17: ('EKF failsafe', 'EKF failsafe', 'طوارئ EKF'), 18: ('Barometre', 'Barometer', 'البارومتر'),
    19: ('CPU failsafe', 'CPU failsafe', 'طوارئ المعالج'), 20: ('ADS-B failsafe', 'ADS-B failsafe', 'طوارئ ADS-B'),
    21: ('Arazi verisi', 'Terrain data', 'بيانات التضاريس'), 22: ('Navigasyon', 'Navigation', 'الملاحة'),
    23: ('Arazi failsafe', 'Terrain failsafe', 'طوارئ التضاريس'), 24: ('EKF birincil', 'EKF primary', 'EKF الأساسي'),
    25: ('Hız sıfırlama', 'Thrust loss check', 'فحص فقدان الدفع'), 26: ('Sensör failsafe', 'Sensor failsafe', 'طوارئ الحساس'),
    27: ('Yan pervane failsafe', 'Leak failsafe', 'طوارئ التسرب'), 28: ('Pilot giriş failsafe', 'Pilot input failsafe', 'طوارئ مدخلات الطيار'),
    29: ('Titreşim failsafe', 'Vibration failsafe', 'طوارئ الاهتزاز'), 30: ('İç hata', 'Internal error', 'خطأ داخلي'),
    31: ('Deadreckon failsafe', 'Deadreckon failsafe', 'طوارئ الملاحة التقديرية'),
}

# ECode yorumu (genel): 0 = düzeldi, 1 = oluştu; bazı alt sistemlerde özel anlamlar
ERR_CODE = {
    (11, 2): ('GPS glitch (konum sıçraması)', 'GPS glitch', 'خلل في GPS (قفزة في الموقع)'),
    (16, 2): ('EKF varyansı yüksek', 'EKF variance bad', 'تباين EKF مرتفع'),
    (12, 1): ('Kırım algılandı', 'Crash detected', 'تم اكتشاف تحطم'),
    (12, 2): ('Kontrol kaybı', 'Loss of control', 'فقدان السيطرة'),
    (6, 1): ('Düşük batarya', 'Battery low', 'بطارية منخفضة'), (6, 2): ('Kritik batarya', 'Battery critical', 'بطارية حرجة'),
    (5, 1): ('Radyo kaybı başladı', 'Radio lost', 'بدء فقدان الراديو'), (5, 0): ('Radyo geri geldi', 'Radio restored', 'عودة الراديو'),
    (7, 1): ('GPS kaybı', 'GPS lost', 'فقدان GPS'), (3, 1): ('Pusula sağlıksız', 'Compass unhealthy', 'البوصلة غير سليمة'),
    (18, 4): ('Barometre sağlıksız', 'Baro unhealthy', 'البارومتر غير سليم'),
}

EV_NAMES = {
    7: ('AP durumu', 'AP state', 'حالة الطيار الآلي'), 9: ('Uçuşa hazırlık', 'Init simple bearing', 'تهيئة الاتجاه'),
    10: ('ARM edildi', 'Armed', 'تم التسليح'), 11: ('DISARM edildi', 'Disarmed', 'تم نزع التسليح'),
    15: ('Otomatik silahlanma', 'Auto armed', 'تسليح آلي'), 17: ('Kısmen indi', 'Land complete maybe', 'هبوط محتمل'),
    18: ('İniş tamamlandı', 'Land complete', 'اكتمل الهبوط'), 19: ('Kayıp araç alarmı', 'Lost copter', 'إنذار فقدان المركبة'),
    25: ('Ev konumu ayarlandı', 'Set home', 'تم ضبط نقطة الإقلاع'), 28: ('İrtifa sapması', 'Not landed', 'لم يهبط'),
    29: ('Kalkış tamamlandı', 'Auto takeoff complete', 'اكتمل الإقلاع الآلي'), 51: ('Hedef seyir noktasına varıldı', 'Waypoint reached', 'تم الوصول لنقطة المسار'),
    54: ('Paraşüt açıldı', 'Parachute released', 'تم فتح المظلة'), 56: ('Ekipman tetiklendi', 'Gripper', 'الماسك'),
    57: ('Yeni ev konumu', 'Set home (GPS)', 'نقطة إقلاع جديدة'), 60: ('EKF yükseklik sıfırlandı', 'EKF alt reset', 'إعادة ضبط ارتفاع EKF'),
    62: ('EKF yaw sıfırlandı', 'EKF yaw reset', 'إعادة ضبط اتجاه EKF'), 63: ('Görev başladı', 'Mission start', 'بدأت المهمة'),
    64: ('Görev bitti', 'Mission complete', 'اكتملت المهمة'), 70: ('Arm kontrolü başarısız', 'Arming failed', 'فشل التسليح'),
    71: ('Kendi kendine kontrol başarısız', 'Selfcheck failed', 'فشل الفحص الذاتي'), 80: ('Yer etkisi', 'Ground effect', 'تأثير الأرض'),
    85: ('Motor uyarısı', 'Motor interlock', 'قفل المحرك'), 165: ('Sabit kanattan VTOL geçişi', 'VTOL transition', 'انتقال VTOL'),
}


def tr3(tup, lang):
    i = {'tr': 0, 'en': 1, 'ar': 2}.get(lang, 0)
    return tup[i] if tup else ''


def err_text(sub, code, lang):
    s = tr3(ERR_SUBSYS.get(sub, (f'Alt sistem {sub}', f'Subsystem {sub}', f'النظام الفرعي {sub}')), lang)
    c = ERR_CODE.get((sub, code))
    if c:
        return f'{s}: {tr3(c, lang)}'
    if code == 0:
        return s + ': ' + {'tr': 'düzeldi', 'en': 'resolved', 'ar': 'تم الحل'}[lang]
    return s + f' ({ {"tr": "kod", "en": "code", "ar": "رمز"}[lang] } {code})'


def ev_text(i, lang):
    return tr3(EV_NAMES.get(i, (f'Olay {i}', f'Event {i}', f'الحدث {i}')), lang)
