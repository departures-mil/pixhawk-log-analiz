"""Problem Çözücü — belirtiye göre hedefli, derin log incelemesi.

Kullanıcı belirtiyi seçer ya da kendi cümlesiyle yazar ("kalkışta devriliyor", "daire çiziyor"…). Program o belirtiyle
ilgili bütün testleri logun tam çözünürlüklü verisi üzerinde çalıştırır; sensörleri birbiriyle çapraz kontrol eder
(birden fazla IMU / pusula / GPS–barometre), her bulguyu zamanı, değeri ve eşiğiyle verir ve adım adım çözüm, ilgili
parametreleri (mevcut değerleriyle) önerir. Veri yetmiyorsa tahmin yürütmez, "logda bu ölçüm yok" der.
Offline çalışır; internet ve kullanıcının kendi YZ anahtarı varsa ai_solve() sonuçları uzman diliyle birleştirir.
"""
from __future__ import annotations
import math, re
import numpy as np
from . import texts
from .analysis import fmt_t

LI = {'tr': 0, 'en': 1, 'ar': 2}


def _l(x, lang):
    return x if isinstance(x, str) else x[LI.get(lang, 0)]


# ----------------------------------------------------------------- belirtiler
SYMPTOMS = [
    ('crash', ('Düştü / kırım oldu, nedenini bilmiyorum', 'It crashed and I do not know why', 'تحطمت ولا أعرف السبب'),
     ['düş', 'kırım', 'kaza', 'çakıl', 'crash', 'fell', 'تحطم', 'سقط'],
     ['crash', 'flip', 'power', 'ice', 'vibration', 'imu_x', 'gps', 'gps_baro', 'compass', 'ekf', 'rc', 'modes', 'att', 'osc', 'motors', 'servo', 'airspeed', 'wind', 'cpu', 'params']),
    ('takeoff_flip', ('Kalkışta devriliyor / takla atıyor', 'Flips over on take-off', 'تنقلب عند الإقلاع'),
     ['devril', 'takla', 'kalkışta', 'flip', 'tip over', 'انقلب'], ['flip', 'motors', 'att', 'imu_x', 'compass', 'params']),
    ('drift', ('Daire çiziyor / sürükleniyor (toilet bowl)', 'Circles / drifts (toilet bowl)', 'تدور / تنجرف'),
     ['daire', 'sürüklen', 'kayıyor', 'drift', 'toilet', 'circl', 'تنجرف', 'تدور'], ['compass', 'gps', 'ekf', 'vibration', 'wind', 'params']),
    ('osc', ('Sallanıyor / salınım yapıyor', 'Oscillates / wobbles', 'تتذبذب / تهتز'),
     ['sallan', 'salınım', 'titri', 'osilasyon', 'wobble', 'oscillat', 'تذبذب'], ['osc', 'att', 'vibration', 'motors', 'servo', 'params']),
    ('alt', ('İrtifa tutamıyor / irtifa kaybediyor', 'Cannot hold / loses altitude', 'لا تحافظ على الارتفاع'),
     ['irtifa', 'yükseklik', 'alçal', 'altitude', 'sink', 'الارتفاع'], ['alt', 'gps_baro', 'vibration', 'power', 'motors', 'airspeed', 'wind', 'params']),
    ('vibe', ('Titreşim yüksek', 'High vibration', 'اهتزاز مرتفع'), ['titreş', 'vibra', 'اهتزاز'],
     ['vibration', 'imu_x', 'ice', 'motors', 'params']),
    ('gps', ('GPS kayboluyor / konum sıçrıyor', 'GPS loss / position jumps', 'فقدان GPS / قفزات الموقع'),
     ['gps', 'konum', 'uydu', 'glitch', 'position', 'satellit', 'موقع'], ['gps', 'gps_baro', 'ekf', 'ice', 'params']),
    ('ekf', ('EKF hatası / EKF variance', 'EKF error / EKF variance', 'خطأ EKF'), ['ekf', 'variance', 'varyans'],
     ['ekf', 'compass', 'gps', 'vibration', 'imu_x', 'params']),
    ('compass', ('Pusula hatası / yön kayması', 'Compass error / heading drift', 'خطأ البوصلة'), ['pusula', 'compass', 'mag', 'yön', 'بوصلة'],
     ['compass', 'ekf', 'power', 'params']),
    ('rc', ('Kumanda bağlantısı koptu / failsafe', 'Lost RC link / failsafe', 'فقدان إشارة التحكم'),
     ['kumanda', 'radyo', 'alıcı', 'failsafe', 'rc', 'radio', 'link', 'التحكم'], ['rc', 'modes', 'ice', 'power', 'params']),
    ('mode', ('Kendi kendine mod değiştirdi / RTL\'ye geçti', 'Changed mode by itself / went to RTL', 'غيّرت الوضع وحدها'),
     ['mod', 'rtl', 'eve dön', 'mode', 'return', 'وضع'], ['modes', 'rc', 'power', 'gps', 'ekf', 'params']),
    ('power', ('Güç kesildi / motor durdu', 'Lost power / motor stopped', 'انقطاع الطاقة / توقف المحرك'),
     ['güç', 'motor dur', 'kesildi', 'power', 'engine stop', 'brownout', 'الطاقة'], ['power', 'ice', 'motors', 'crash', 'cpu', 'params']),
    ('battery', ('Uçuş süresi kısa / batarya çabuk bitiyor', 'Short flight time / battery drains fast', 'زمن طيران قصير'),
     ['batarya', 'pil', 'süre', 'battery', 'flight time', 'بطارية'], ['power', 'motors', 'alt', 'wind', 'params']),
    ('yaw', ('Kendi etrafında dönüyor / yaw tutmuyor', 'Spins / poor yaw hold', 'تدور حول نفسها'),
     ['etrafında', 'dönüyor', 'yaw', 'sapma', 'spin', 'انعراج'], ['yaw', 'motors', 'compass', 'params']),
    ('stall', ('Hız kaybedip düştü (stall)', 'Lost speed and fell (stall)', 'فقدت السرعة (انهيار)'),
     ['stall', 'hız kayb', 'perdövites', 'speed', 'انهيار'], ['airspeed', 'alt', 'att', 'wind', 'power', 'ice', 'params']),
    ('arm', ('Arm olmuyor (arm öncesi kontrol hataları)', 'Will not arm (pre-arm failures)', 'لا تتسلح (فحوصات ما قبل التسليح)'),
     ['arm', 'prearm', 'pre-arm', 'kurulmuyor', 'تسليح'], ['prearm', 'imu_x', 'compass', 'gps', 'power', 'params']),
    ('landing', ('Sert iniş / iniş sorunu', 'Hard landing / landing problem', 'هبوط عنيف'), ['iniş', 'land', 'flare', 'هبوط'],
     ['alt', 'gps_baro', 'airspeed', 'att', 'wind', 'params']),
    ('servo', ('Kumanda yüzeyi / servo tepki vermiyor', 'Control surface / servo not responding', 'السيرفو لا يستجيب'),
     ['servo', 'yüzey', 'kanatçık', 'dümen', 'aileron', 'elevator', 'rudder'], ['servo', 'att', 'power', 'params']),
    ('log', ('Log eksik / kayıt kesik', 'Log incomplete / gaps', 'السجل ناقص'), ['log', 'kayıt', 'eksik', 'gap', 'سجل'],
     ['cpu', 'power', 'params']),
]
SYM = {s[0]: s for s in SYMPTOMS}
ALL_CHECKS = ['crash', 'flip', 'prearm', 'vibration', 'imu_x', 'gps', 'gps_baro', 'compass', 'ekf', 'power', 'ice', 'rc', 'modes',
              'att', 'osc', 'alt', 'motors', 'yaw', 'servo', 'airspeed', 'wind', 'cpu', 'params']


def symptom_label(sid, lang):
    return _l(SYM[sid][1], lang)


def match_text(q):
    """Serbest metinden belirtiler."""
    q = (q or '').lower(); out = []
    for sid, lab, kws, _c in SYMPTOMS:
        if any(k in q for k in kws): out.append(sid)
    return out


# ----------------------------------------------------------------- metinler
S = {
    'n_crash': ('Kırım kararı', 'Crash verdict', 'قرار التحطم'),
    'n_flip': ('Kalkışta devrilme', 'Tip-over on take-off', 'الانقلاب عند الإقلاع'),
    'n_prearm': ('Arm öncesi kontroller', 'Pre-arm checks', 'فحوصات ما قبل التسليح'),
    'n_vibration': ('Titreşim ve clipping', 'Vibration and clipping', 'الاهتزاز والتشبع'),
    'n_imu_x': ('IMU’ların birbirini tutması (çapraz kontrol)', 'IMU agreement (cross-check)', 'تطابق وحدات IMU (فحص متقاطع)'),
    'n_gps': ('GPS kalitesi', 'GPS quality', 'جودة GPS'),
    'n_gps_baro': ('GPS ↔ barometre irtifa uyumu (çapraz kontrol)', 'GPS ↔ barometer altitude agreement (cross-check)', 'تطابق ارتفاع GPS والبارومتر'),
    'n_compass': ('Pusula ve manyetik parazit', 'Compass and magnetic interference', 'البوصلة والتداخل المغناطيسي'),
    'n_ekf': ('EKF (konum/tutum kestirimi)', 'EKF (state estimation)', 'EKF (تقدير الحالة)'),
    'n_power': ('Güç: batarya, voltaj çökmesi, kart beslemesi (Vcc)', 'Power: battery, sag, board supply (Vcc)', 'الطاقة: البطارية، هبوط الجهد، تغذية اللوحة'),
    'n_ice': ('İçten yanmalı motor (devir / ateşleme)', 'Combustion engine (RPM / ignition)', 'محرك الاحتراق (الدوران / الإشعال)'),
    'n_rc': ('Kumanda bağlantısı (RC)', 'RC link', 'وصلة التحكم (RC)'),
    'n_modes': ('Mod değişimleri ve nedenleri', 'Mode changes and reasons', 'تغييرات الوضع وأسبابها'),
    'n_att': ('Tutum takibi (istenen ↔ gerçekleşen)', 'Attitude tracking (desired ↔ actual)', 'تتبع الوضعية (المطلوب ↔ الفعلي)'),
    'n_osc': ('Salınım analizi (frekans)', 'Oscillation analysis (frequency)', 'تحليل التذبذب (التردد)'),
    'n_alt': ('İrtifa takibi ve gaz payı', 'Altitude tracking and throttle margin', 'تتبع الارتفاع وهامش الخانق'),
    'n_motors': ('Motor çıkışları (denge / tavan payı)', 'Motor outputs (balance / headroom)', 'مخرجات المحركات (التوازن / الهامش)'),
    'n_yaw': ('Sapma (yaw) takibi', 'Yaw tracking', 'تتبع الانعراج'),
    'n_servo': ('Servo doygunluğu', 'Servo saturation', 'تشبع السيرفو'),
    'n_airspeed': ('Hava hızı ve stall payı', 'Airspeed and stall margin', 'السرعة الجوية وهامش الانهيار'),
    'n_wind': ('Rüzgâr ve hava durumu', 'Wind and weather', 'الرياح والطقس'),
    'n_cpu': ('İşlemci yükü ve log kaybı', 'CPU load and log drops', 'حمل المعالج وفقدان السجل'),
    'n_params': ('Parametre denetimi', 'Parameter audit', 'تدقيق المعلمات'),
    'nodata': ('Logda bu ölçüm yok ({m}); bu konuda kesin yargı verilemez.', 'This measurement is not in the log ({m}); no firm conclusion possible.', 'هذا القياس غير موجود في السجل ({m})؛ لا يمكن الجزم.'),
    'ok': ('Sorun görülmedi.', 'No problem found.', 'لم تظهر مشكلة.'),
    # bulgular
    'crash_v': ('Karar: {v} (puan {s}). {sent}', 'Verdict: {v} (score {s}). {sent}', 'القرار: {v} (الدرجة {s}). {sent}'),
    'flip_f': ('{t} anında tutum {a}° oldu ve araç öyle kaldı; kalkıştan {d} s sonra.', 'Attitude reached {a}° at {t} and stayed; {d} s after take-off.', 'بلغت الوضعية {a}° عند {t} وبقيت؛ بعد {d} ث من الإقلاع.'),
    'prearm_f': ('{n} farklı arm öncesi hata: {msgs}', '{n} distinct pre-arm failures: {msgs}', '{n} أخطاء مختلفة قبل التسليح: {msgs}'),
    'vibe_f': ('Uçuşta titreşim %95 = {p} m/s² (uyarı {w}, kötü {b}); en yüksek {m} m/s² ({t}); clipping {c}.', 'In-flight vibration p95 = {p} m/s² (warn {w}, bad {b}); max {m} m/s² ({t}); clipping {c}.', 'اهتزاز أثناء الطيران p95 = {p} م/ث² (تحذير {w}، سيئ {b})؛ الأقصى {m} ({t})؛ تشبع {c}.'),
    'imu_f': ('{n} IMU karşılaştırıldı: ivme farkı en fazla {da} m/s², jiroskop farkı en fazla {dg}°/s ({t}).', '{n} IMUs compared: max accel difference {da} m/s², max gyro difference {dg}°/s ({t}).', 'قورنت {n} وحدات IMU: أقصى فرق تسارع {da} م/ث²، أقصى فرق جيروسكوب {dg}°/ث ({t}).'),
    'imu_one': ('Logda tek IMU var; çapraz kontrol yapılamadı.', 'Only one IMU in the log; no cross-check possible.', 'وحدة IMU واحدة فقط؛ لا يمكن الفحص المتقاطع.'),
    'gps_f': ('Uydu en az {s}, HDOP en fazla {h}, kötü kalite süresi %{p}, glitch {g}; ilk sorun {t}.', 'Min satellites {s}, max HDOP {h}, poor quality {p}% of flight, glitches {g}; first problem {t}.', 'أدنى عدد أقمار {s}، أقصى HDOP {h}، جودة سيئة {p}%، أعطال {g}؛ أول مشكلة {t}.'),
    'gb_f': ('GPS ve barometre irtifa değişimleri arasındaki fark en fazla {d} m ({t}); ortalama sapma {m} m.', 'Max difference between GPS and barometer altitude change {d} m ({t}); mean drift {m} m.', 'أقصى فرق بين تغير ارتفاع GPS والبارومتر {d} م ({t})؛ متوسط الانحراف {m} م.'),
    'mag_f': ('Manyetik alan değişimi %{v}; gaz ile ilişki r = {c}; {n} pusula. {x}', 'Magnetic field variation {v}%; correlation with throttle r = {c}; {n} compass(es). {x}', 'تغير المجال المغناطيسي {v}%؛ الارتباط بالخانق r = {c}؛ {n} بوصلة. {x}'),
    'mag_x': ('Pusulalar arası yön farkı en fazla {d}° ({t}).', 'Max heading difference between compasses {d}° ({t}).', 'أقصى فرق اتجاه بين البوصلات {d}° ({t}).'),
    'ekf_f': ('En yüksek EKF varyansları: {v}; şerit değişimi {l}, yaw sıfırlama {y}.', 'Highest EKF variances: {v}; lane switches {l}, yaw resets {y}.', 'أعلى تباينات EKF: {v}؛ تبديل المسارات {l}، إعادة ضبط الانعراج {y}.'),
    'pw_f': ('Hücre başı en düşük {c} V ({t}), voltaj çökmesi {s} V, en yüksek akım {a} A; kart beslemesi Vcc {v1}–{v2} V.', 'Min per-cell {c} V ({t}), sag {s} V, max current {a} A; board Vcc {v1}–{v2} V.', 'أدنى جهد للخلية {c} ف ({t})، هبوط {s} ف، أقصى تيار {a} أ؛ تغذية اللوحة {v1}–{v2} ف.'),
    'vcc_f': ('Kart beslemesi (Vcc) {d} V dalgalandı ({t}); 0,15 V üzeri dalgalanma servo/BEC kaynaklı güç sorununu gösterir.', 'Board supply (Vcc) varied {d} V ({t}); more than 0.15 V points to a servo/BEC power problem.', 'تذبذبت تغذية اللوحة {d} ف ({t})؛ أكثر من 0.15 ف يدل على مشكلة طاقة من السيرفو/BEC.'),
    'ice_f': ('Motor devri: uçuşta en düşük {r} rpm ({t}); devir sıfıra düştü mü: {z}.', 'Engine RPM: in-flight min {r} rpm ({t}); dropped to zero: {z}.', 'دوران المحرك: الأدنى أثناء الطيران {r} ({t})؛ هبط إلى الصفر: {z}.'),
    'ice_norpm': ('Benzinli motor seçildi ama logda devir (RPM) ölçümü yok. RPM sensörü takılması (RPM1_TYPE) motor durmasını kesin gösterir.', 'Petrol engine selected but no RPM data in the log. An RPM sensor (RPM1_TYPE) would prove an engine stop.', 'تم اختيار محرك بنزين لكن لا توجد بيانات RPM. حساس RPM (RPM1_TYPE) يثبت توقف المحرك.'),
    'rc_f': ('Radyo failsafe {n}; gaz kanalı failsafe eşiğinin altında %{l}; RSSI en düşük {r}.', 'Radio failsafes {n}; throttle below failsafe level {l}%; min RSSI {r}.', 'حالات طوارئ الراديو {n}؛ الخانق تحت حد الطوارئ {l}%؛ أدنى RSSI {r}.'),
    'mode_f': ('{t}: {m} ({r})', '{t}: {m} ({r})', '{t}: {m} ({r})'),
    'att_f': ('Yatış hatası RMS {r}°, yunuslama hatası RMS {p}°; en büyük hata {e}° ({t}).', 'Roll error RMS {r}°, pitch error RMS {p}°; largest error {e}° ({t}).', 'خطأ الدحرجة RMS {r}°، خطأ الميل RMS {p}°؛ أكبر خطأ {e}° ({t}).'),
    'osc_f': ('{ax} ekseninde {f} Hz’de baskın salınım, genlik ±{a}°.{k}', 'Dominant oscillation on {ax} at {f} Hz, amplitude ±{a}°.{k}', 'تذبذب سائد على محور {ax} عند {f} هرتز، السعة ±{a}°.{k}'),
    'osc_hi': (' Yüksek frekans: kazanç (P/D) fazla veya titreşim filtresi yetersiz.', ' High frequency: gains (P/D) too high or filtering insufficient.', ' تردد عالٍ: الكسب (P/D) مرتفع أو الترشيح غير كافٍ.'),
    'osc_lo': (' Düşük frekans: dış döngü (açı P) veya navigasyon ayarı yumuşak/aşırı.', ' Low frequency: outer loop (angle P) or navigation tuning.', ' تردد منخفض: الحلقة الخارجية (زاوية P) أو ضبط الملاحة.'),
    'alt_f': ('İstenen ↔ gerçek irtifa farkı RMS {r} m, en fazla {m} m ({t}); gaz %{s} süre tavanda.', 'Desired ↔ actual altitude error RMS {r} m, max {m} m ({t}); throttle at max {s}% of time.', 'خطأ الارتفاع RMS {r} م، الأقصى {m} م ({t})؛ الخانق عند الحد الأقصى {s}% من الوقت.'),
    'mot_f': ('Motor dengesizliği {d} µs ({ch}); tavan payı {h} µs.', 'Motor imbalance {d} µs ({ch}); headroom {h} µs.', 'عدم توازن المحركات {d} µs ({ch})؛ الهامش {h} µs.'),
    'yaw_f': ('Yaw hatası RMS {r}°, en fazla {m}° ({t}).', 'Yaw error RMS {r}°, max {m}° ({t}).', 'خطأ الانعراج RMS {r}°، الأقصى {m}° ({t}).'),
    'servo_f': ('En çok doygunluğa giren kanal {ch}: süre %{v}.', 'Most saturated channel {ch}: {v}% of time.', 'القناة الأكثر تشبعاً {ch}: {v}% من الوقت.'),
    'as_f': ('Hava hızı en düşük {a} m/s ({t}); ARSPD_FBW_MIN = {m}; stall payı {k} m/s.', 'Min airspeed {a} m/s ({t}); ARSPD_FBW_MIN = {m}; stall margin {k} m/s.', 'أدنى سرعة جوية {a} م/ث ({t})؛ ARSPD_FBW_MIN = {m}؛ هامش الانهيار {k} م/ث.'),
    'wind_f': ('Logdan kestirilen rüzgâr ort. {m} m/s, en fazla {x} m/s. {wx}', 'Wind estimated from log mean {m} m/s, max {x} m/s. {wx}', 'الرياح المقدرة من السجل متوسط {m} م/ث، الأقصى {x} م/ث. {wx}'),
    'cpu_f': ('İşlemci yükü en fazla %{l}; uzun döngü {n}; kaybolan log mesajı {d}.', 'Max CPU load {l}%; long loops {n}; dropped log messages {d}.', 'أقصى حمل للمعالج {l}%؛ حلقات طويلة {n}؛ رسائل سجل مفقودة {d}.'),
    'par_f': ('{n} parametre uyarısı.', '{n} parameter warnings.', '{n} تحذيرات معلمات.'),
    'yes': ('evet', 'yes', 'نعم'), 'no': ('hayır', 'no', 'لا'),
    # çözüm adımları
    'fx_flip': ('Mission Planner > Kurulum > Motor Test ile motor sırasını (A,B,C,D…) ve dönüş yönlerini kontrol edin; pervanelerin CW/CCW takılışını ve FRAME_CLASS/FRAME_TYPE ayarını doğrulayın; ivmeölçer ve kumanda kalibrasyonunu tekrarlayın.',
                'Use Mission Planner > Setup > Motor Test to check motor order (A,B,C,D…) and spin direction; verify CW/CCW props and FRAME_CLASS/FRAME_TYPE; redo accelerometer and RC calibration.',
                'استخدم Mission Planner > Motor Test للتحقق من ترتيب المحركات واتجاه دورانها؛ تحقق من المراوح CW/CCW ومن FRAME_CLASS/FRAME_TYPE؛ أعد معايرة مقياس التسارع والتحكم.'),
    'fx_vibe': ('Pervaneleri balanslayın, motor/şase vidalarını sıkın, uçuş kontrolcüsünü titreşim sönümleyici üzerine yumuşak monte edin; harmonik çentik filtresini (INS_HNTCH_*) etkinleştirin.',
                'Balance props, tighten motor/frame screws, soft-mount the flight controller; enable the harmonic notch filter (INS_HNTCH_*).',
                'وازن المراوح، شد براغي المحركات والهيكل، ركّب وحدة التحكم على مخمد اهتزاز؛ فعّل مرشح الشق التوافقي (INS_HNTCH_*).'),
    'fx_imu': ('IMU’lar birbirini tutmuyor: kartı yeniden kalibre edin (ivmeölçer + sıcaklık kalibrasyonu), kart montajını ve kartın kendisini kontrol edin; sorun sürerse kart arızalı olabilir.',
               'IMUs disagree: recalibrate (accelerometer + temperature calibration), check board mounting; if it persists the board may be faulty.',
               'وحدات IMU غير متطابقة: أعد المعايرة (التسارع + الحرارة)، افحص تثبيت اللوحة؛ إن استمر فقد تكون اللوحة معطوبة.'),
    'fx_gps': ('GPS’i gökyüzünü açık görecek şekilde, telemetri/video vericisi ve ateşleme sisteminden uzağa yerleştirin; kalkıştan önce 10+ uydu ve HDOP < 1,5 bekleyin; GPS_GNSS_MODE ile çoklu takımyıldız kullanın.',
               'Mount the GPS with a clear sky view, away from telemetry/video transmitters and ignition; wait for 10+ satellites and HDOP < 1.5 before take-off; enable multi-constellation (GPS_GNSS_MODE).',
               'ركّب GPS برؤية واضحة للسماء بعيداً عن أجهزة الإرسال ونظام الإشعال؛ انتظر 10+ أقمار وHDOP < 1.5 قبل الإقلاع؛ فعّل تعدد الأنظمة (GPS_GNSS_MODE).'),
    'fx_baro': ('Barometreyi hava akımı ve ışıktan koruyun (köpük); pervane hava akımı basınç hatası yapıyor olabilir. GPS irtifası ile uyumsuzluk sürerse EK3_SRC1_POSZ kaynağını gözden geçirin.',
                'Shield the barometer from airflow and light (foam); prop wash may cause pressure errors. If disagreement persists review EK3_SRC1_POSZ.',
                'احمِ البارومتر من تيار الهواء والضوء (إسفنج)؛ قد يسبب تيار المراوح أخطاء ضغط. إن استمر عدم التطابق راجع EK3_SRC1_POSZ.'),
    'fx_mag': ('Pusulayı güç kablolarından ve ESC’lerden uzaklaştırın (GPS direğine), CompassMot ile gaz/akım etkisini ölçün, pusula kalibrasyonunu açık alanda tekrarlayın; sorunlu pusulayı COMPASS_USEx = 0 ile kapatın.',
                'Move the compass away from power wires and ESCs (on a GPS mast), run CompassMot, recalibrate in an open area; disable a bad compass with COMPASS_USEx = 0.',
                'أبعد البوصلة عن كابلات الطاقة وESC (على سارية GPS)، شغّل CompassMot، أعد المعايرة في مكان مفتوح؛ عطّل البوصلة السيئة بـ COMPASS_USEx = 0.'),
    'fx_ekf': ('EKF hataları genellikle GPS, pusula veya titreşim kaynaklıdır: önce bu bölümlerdeki bulguları giderin. Kalkıştan önce EKF’nin oturmasını bekleyin.',
               'EKF errors usually come from GPS, compass or vibration: fix those findings first. Wait for the EKF to settle before take-off.',
               'أخطاء EKF غالباً من GPS أو البوصلة أو الاهتزاز: عالج تلك النتائج أولاً. انتظر استقرار EKF قبل الإقلاع.'),
    'fx_power': ('Bataryanın kapasitesini/C değerini ve hücre dengesini kontrol edin; BATT_LOW_VOLT, BATT_CRT_VOLT ve failsafe eylemlerini ayarlayın; akım sensörünü (BATT_AMP_PERVLT) kalibre edin.',
                 'Check battery capacity/C rating and cell balance; set BATT_LOW_VOLT, BATT_CRT_VOLT and failsafe actions; calibrate the current sensor (BATT_AMP_PERVLT).',
                 'افحص سعة البطارية ومعدل C وتوازن الخلايا؛ اضبط BATT_LOW_VOLT وBATT_CRT_VOLT وإجراءات الطوارئ؛ عاير حساس التيار (BATT_AMP_PERVLT).'),
    'fx_vcc': ('Kartı ayrı ve temiz bir 5 V güç modülünden besleyin; servoları kartın servo rayından değil ayrı BEC’ten besleyin; güç konektörlerini kontrol edin.',
               'Power the board from a separate clean 5 V module; feed servos from a separate BEC, not the board rail; check power connectors.',
               'غذِّ اللوحة من وحدة 5 ف نظيفة منفصلة؛ غذِّ السيرفوهات من BEC منفصل؛ افحص موصلات الطاقة.'),
    'fx_ice': ('Benzinli motor: yakıt hattı ve filtre, buji ve ateşleme modülü, karbüratör ayarı (rölanti/yüksek devir) ve hava filtresini kontrol edin; ICE_ENABLE, ICE_RPM_THRESH ve ICE_START_CHAN ayarlarını gözden geçirin.',
               'Petrol engine: check fuel line and filter, spark plug and ignition module, carburettor setting (idle/high) and air filter; review ICE_ENABLE, ICE_RPM_THRESH and ICE_START_CHAN.',
               'محرك بنزين: افحص خط الوقود والفلتر، الشمعة ووحدة الإشعال، ضبط المكربن وفلتر الهواء؛ راجع ICE_ENABLE وICE_RPM_THRESH وICE_START_CHAN.'),
    'fx_rc': ('Alıcı antenlerini 90° açıyla ve gövdeden uzağa yerleştirin; menzil testi yapın; FS_THR_ENABLE / THR_FAILSAFE ve FS_THR_VALUE değerlerini doğrulayın (failsafe’te gaz bu değerin altına düşmeli).',
              'Place receiver antennas at 90° and away from the airframe; do a range test; verify FS_THR_ENABLE / THR_FAILSAFE and FS_THR_VALUE (throttle must fall below it on failsafe).',
              'ضع هوائيات المستقبل بزاوية 90° بعيداً عن الهيكل؛ اختبر المدى؛ تحقق من FS_THR_ENABLE / THR_FAILSAFE وFS_THR_VALUE.'),
    'fx_tune': ('Ayarı AUTOTUNE ile yapın; salınım yüksek frekanslıysa ATC_RAT_*_P/D (uçakta *2SRV_P/D) kazançlarını %20 düşürün, düşük frekanslıysa ATC_ANG_*_P / NAVL1_PERIOD ayarlarını gözden geçirin.',
                'Tune with AUTOTUNE; for high-frequency oscillation reduce ATC_RAT_*_P/D (plane: *2SRV_P/D) by 20%; for low-frequency review ATC_ANG_*_P / NAVL1_PERIOD.',
                'اضبط بـ AUTOTUNE؛ للتذبذب عالي التردد خفّض ATC_RAT_*_P/D (للطائرة *2SRV_P/D) بنسبة 20%؛ للتذبذب المنخفض راجع ATC_ANG_*_P / NAVL1_PERIOD.'),
    'fx_alt': ('Gaz sık sık tavanda: araç ağır ya da itki yetersiz (pervane/motor/batarya). Ağırlığı azaltın veya itkiyi artırın; MOT_THST_HOVER / TRIM_THROTTLE ve TECS ayarlarını kontrol edin.',
               'Throttle often at max: vehicle too heavy or underpowered. Reduce weight or increase thrust; check MOT_THST_HOVER / TRIM_THROTTLE and TECS settings.',
               'الخانق كثيراً عند الحد الأقصى: المركبة ثقيلة أو الدفع غير كافٍ. خفّف الوزن أو زد الدفع؛ راجع MOT_THST_HOVER / TRIM_THROTTLE وإعدادات TECS.'),
    'fx_motor': ('Dengesiz motor: o koldaki motor/ESC/pervaneyi kontrol edin, kolun bükülmediğinden ve motorun düz durduğundan emin olun; ağırlık merkezini ortalayın.',
                 'Imbalanced motor: check the motor/ESC/prop on that arm, make sure the arm is not twisted and the motor is level; centre the CG.',
                 'محرك غير متوازن: افحص المحرك/ESC/المروحة على ذلك الذراع، وتأكد من استقامة الذراع والمحرك؛ وسّط مركز الثقل.'),
    'fx_servo': ('Servo doygunluğu: kumanda yüzeyi yetersiz ya da trim kaymış; servo kolu ve hareket aralığını büyütün, SERVOx_MIN/MAX/TRIM değerlerini ve mekanik bağlantıları kontrol edin.',
                 'Servo saturation: control surface too small or trim off; increase throw, check SERVOx_MIN/MAX/TRIM and linkages.',
                 'تشبع السيرفو: سطح التحكم صغير أو التريم منحرف؛ زد مدى الحركة وافحص SERVOx_MIN/MAX/TRIM والوصلات.'),
    'fx_as': ('Hava hızı stall’a yaklaşmış: ARSPD_FBW_MIN değerini stall hızının %20–25 üzerine ayarlayın, hava hızı sensörünü kalibre edin (ARSPD_RATIO), dönüşlerde yatış sınırını (ROLL_LIMIT_DEG) azaltın.',
              'Airspeed close to stall: set ARSPD_FBW_MIN 20–25% above stall speed, calibrate the airspeed sensor (ARSPD_RATIO), reduce ROLL_LIMIT_DEG in turns.',
              'السرعة الجوية قريبة من الانهيار: اضبط ARSPD_FBW_MIN أعلى بـ 20–25% من سرعة الانهيار، عاير الحساس (ARSPD_RATIO)، خفّض ROLL_LIMIT_DEG.'),
    'fx_wind': ('Rüzgâr aracın sınırlarına yakın: daha sakin havada uçun; uçakta ARSPD_FBW_MIN’i rüzgâra göre artırın, kopterde ANGLE_MAX ve WPNAV hızlarını gözden geçirin.',
                'Wind near vehicle limits: fly in calmer weather; raise ARSPD_FBW_MIN for planes, review ANGLE_MAX and WPNAV speeds for copters.',
                'الرياح قريبة من حدود المركبة: طِر في طقس أهدأ؛ ارفع ARSPD_FBW_MIN للطائرة وراجع ANGLE_MAX وسرعات WPNAV للكوبتر.'),
    'fx_cpu': ('İşlemci/kayıt yükü yüksek: LOG_BITMASK’ta gereksiz mesajları kapatın, SD kartı hızlı bir kartla değiştirin, SCHED_LOOP_RATE’i kart kapasitesine uygun tutun.',
               'High CPU/logging load: disable unneeded LOG_BITMASK items, use a fast SD card, keep SCHED_LOOP_RATE within board capacity.',
               'حمل المعالج/التسجيل مرتفع: عطّل الرسائل غير اللازمة في LOG_BITMASK، استخدم بطاقة SD سريعة، أبقِ SCHED_LOOP_RATE ضمن قدرة اللوحة.'),
    'fx_prearm': ('Her arm öncesi mesajını sırayla giderin; sebebi anlamadan ARMING_CHECK’i kapatmayın.', 'Fix each pre-arm message in turn; do not disable ARMING_CHECK without understanding the cause.', 'عالج كل رسالة قبل التسليح بالترتيب؛ لا تعطّل ARMING_CHECK دون فهم السبب.'),
    'h_diag': ('Teşhis', 'Diagnosis', 'التشخيص'), 'h_steps': ('Adım adım çözüm', 'Step-by-step fix', 'الحل خطوة بخطوة'),
    'h_params': ('İlgili parametreler (mevcut değer)', 'Related parameters (current value)', 'المعلمات ذات الصلة (القيمة الحالية)'),
    'h_checks': ('Yapılan testler', 'Checks performed', 'الفحوصات المنفذة'),
    'h_none': ('Seçilen belirti için logda belirgin bir sorun bulunamadı. Sorun logda görünmüyor olabilir (log kesik, ilgili mesaj kapalı) — LOG_BITMASK’ı kontrol edin.',
               'No clear problem found in the log for this symptom. It may not be visible (log cut, message disabled) — check LOG_BITMASK.',
               'لم يُعثر على مشكلة واضحة لهذا العرض. ربما لا تظهر في السجل (سجل مقطوع أو رسالة معطلة) — راجع LOG_BITMASK.'),
    'most': ('En olası neden', 'Most likely cause', 'السبب الأرجح'), 'also': ('Katkıda bulunanlar', 'Contributing', 'عوامل مساهمة'),
}

PARAMS = {'flip': ['FRAME_CLASS', 'FRAME_TYPE', 'MOT_SPIN_ARM', 'MOT_SPIN_MIN'], 'vibration': ['INS_HNTCH_ENABLE', 'INS_HNTCH_FREQ', 'INS_GYRO_FILTER', 'INS_ACCEL_FILTER'],
          'imu_x': ['INS_USE', 'INS_USE2', 'INS_USE3', 'INS_TCAL1_ENABLE'], 'gps': ['GPS_TYPE', 'GPS_GNSS_MODE', 'GPS_HDOP_GOOD', 'AHRS_GPS_MINSATS'],
          'gps_baro': ['EK3_SRC1_POSZ', 'EK3_ALT_M_NSE', 'BARO_PRIMARY'], 'compass': ['COMPASS_USE', 'COMPASS_USE2', 'COMPASS_USE3', 'COMPASS_ORIENT', 'COMPASS_MOTCT', 'COMPASS_LEARN'],
          'ekf': ['AHRS_EKF_TYPE', 'EK3_ENABLE', 'EK3_MAG_CAL', 'FS_EKF_ACTION', 'FS_EKF_THRESH'],
          'power': ['BATT_MONITOR', 'BATT_CAPACITY', 'BATT_LOW_VOLT', 'BATT_CRT_VOLT', 'BATT_FS_LOW_ACT', 'BATT_FS_CRT_ACT', 'BATT_AMP_PERVLT'],
          'ice': ['ICE_ENABLE', 'ICE_RPM_THRESH', 'ICE_START_CHAN', 'RPM1_TYPE'], 'rc': ['FS_THR_ENABLE', 'THR_FAILSAFE', 'FS_THR_VALUE', 'THR_FS_VALUE', 'RC_OPTIONS'],
          'modes': ['FLTMODE1', 'FLTMODE_CH', 'FS_OPTIONS', 'FS_SHORT_ACTN', 'FS_LONG_ACTN'],
          'att': ['ATC_RAT_RLL_P', 'ATC_RAT_PIT_P', 'RLL2SRV_P', 'PTCH2SRV_P', 'ANGLE_MAX'], 'osc': ['ATC_RAT_RLL_P', 'ATC_RAT_RLL_D', 'ATC_RAT_PIT_P', 'ATC_RAT_PIT_D', 'RLL_RATE_P', 'PTCH_RATE_P', 'RLL2SRV_P', 'PTCH2SRV_P'],
          'alt': ['MOT_THST_HOVER', 'PSC_POSZ_P', 'TRIM_THROTTLE', 'THR_MAX', 'TECS_CLMB_MAX'], 'motors': ['MOT_PWM_MIN', 'MOT_PWM_MAX', 'MOT_SPIN_MIN', 'MOT_THST_EXPO'],
          'yaw': ['ATC_RAT_YAW_P', 'ATC_RAT_YAW_I', 'MOT_YAW_HEADROOM'], 'servo': ['SERVO1_MIN', 'SERVO1_MAX', 'SERVO1_TRIM', 'SERVO2_TRIM'],
          'airspeed': ['ARSPD_TYPE', 'ARSPD_USE', 'ARSPD_RATIO', 'ARSPD_FBW_MIN', 'ROLL_LIMIT_DEG', 'STALL_PREVENTION'],
          'wind': ['ARSPD_FBW_MIN', 'ANGLE_MAX', 'WPNAV_SPEED'], 'cpu': ['LOG_BITMASK', 'SCHED_LOOP_RATE', 'LOG_FILE_BUFSIZE'], 'prearm': ['ARMING_CHECK']}


def s3(key, lang, **a):
    x = S[key][LI.get(lang, 0)]
    try: return x.format(**a)
    except Exception: return x


def _r(v, n=1):
    try: return round(float(v), n)
    except Exception: return '-'


def _inst(L, base):
    out = []
    for k in (base, base + '[1]', base + '[2]', base + '2', base + '3'):
        s = L.s(k)
        if len(s.get('t', [])) > 10 and all(s is not o for o in out): out.append(s)
    return out


# ------------------------------------------------------------------ testler
# her test: (A, lang) -> dict(st, txt, t, fix) ya da None (uygulanamaz)
def c_crash(A, lg):
    v = A.verdict.get('kind', 'normal')
    from .why import render
    y = render(A, lg, fmt_t) or {}
    st = 'bad' if v == 'crash' else ('warn' if v == 'incident' else 'ok')
    return dict(st=st, txt=s3('crash_v', lg, v=texts.T('v_' + v, lg), s=A.verdict.get('score', 0), sent=y.get('sentence', '')),
                t=(A.why or {}).get('te'), fix=[])


def c_flip(A, lg):
    f = getattr(A, 'flip', None)
    if not f: return dict(st='ok', txt=s3('ok', lg))
    d = f[0] - (A.flights[-1][0] if A.flights else f[0])
    return dict(st='bad', txt=s3('flip_f', lg, t=fmt_t(f[0]), a=round(f[1]), d=_r(d)), t=f[0], fix=['fx_flip'])


def c_prearm(A, lg):
    ms = {}
    for t, x in A.L.texts:
        if x.lower().startswith(('prearm', 'pre-arm', 'arm:')) or 'prearm' in x.lower():
            ms.setdefault(x.split(':', 1)[-1].strip(), t)
    if not ms: return dict(st='ok', txt=s3('ok', lg))
    return dict(st='warn', txt=s3('prearm_f', lg, n=len(ms), msgs=' · '.join(list(ms)[:8])), t=min(ms.values()), fix=['fx_prearm'])


def c_vibration(A, lg):
    h = A.health.get('vibration')
    if not h: return dict(st='na', txt=s3('nodata', lg, m='VIBE'))
    m = h['metrics']; v = A.L.s('VIBE'); tmax = None
    try:
        mm = A.in_flight(v['t']) if A.flights else np.ones(len(v['t']), bool)
        a = np.nanmax(np.vstack([v['VibeX'], v['VibeY'], v['VibeZ']]), axis=0); a = np.where(mm, a, np.nan)
        tmax = float(v['t'][int(np.nanargmax(a))])
    except Exception: pass
    st = h['status']
    return dict(st=st, txt=s3('vibe_f', lg, p=_r(m.get('p95')), w=_r(A.th['vibe_warn']), b=_r(A.th['vibe_bad']), m=_r(m.get('max')),
                                t=fmt_t(tmax) if tmax else '-', c=int(m.get('clip') or 0)), t=tmax, fix=['fx_vibe'] if st != 'good' else [])


def _steady(A, t):
    """Uçuşta ve kırım/iniş anının 3 s öncesine kadar (çarpma anındaki doğal farkları dışarıda bırakır)."""
    m = np.zeros(len(t), bool)
    for a, b in (A.flights or []):
        m |= (t >= a + 2) & (t <= b - 3)
    if not A.flights: m[:] = True
    return m


def c_imu_x(A, lg):
    I = _inst(A.L, 'IMU')
    if len(I) < 2: return dict(st='na', txt=s3('imu_one', lg))
    a0 = I[0]; da = dg = 0.0; tw = None
    for b in I[1:]:
        tt = a0['t']
        for ax in ('X', 'Y', 'Z'):
            if not (a0.has('Acc' + ax) and b.has('Acc' + ax)): continue
            # 1 s kayan ortalama ile karşılaştır (gürültü değil, sistematik fark)
            k = max(1, int(len(tt) / max(1.0, tt[-1] - tt[0])))
            ka = np.convolve(a0['Acc' + ax], np.ones(k) / k, 'same'); kb = np.convolve(np.interp(tt, b['t'], b['Acc' + ax]), np.ones(k) / k, 'same')
            d = np.abs(ka - kb); d = np.where(_steady(A, tt), d, 0); i = int(np.nanargmax(d))
            if d[i] > da: da = float(d[i]); tw = float(tt[i])
            if a0.has('Gyr' + ax) and b.has('Gyr' + ax):
                g = np.abs(np.convolve(a0['Gyr' + ax] - np.interp(tt, b['t'], b['Gyr' + ax]), np.ones(k) / k, 'same')); g = np.where(_steady(A, tt), g, 0)
                dg = max(dg, float(np.degrees(np.nanmax(g))))
    st = 'bad' if da > 3.0 or dg > 10 else ('warn' if da > 1.5 or dg > 5 else 'good')
    return dict(st=st, txt=s3('imu_f', lg, n=len(I), da=_r(da, 2), dg=_r(dg), t=fmt_t(tw) if tw else '-'), t=tw, fix=['fx_imu'] if st != 'good' else [])


def c_gps(A, lg):
    h = A.health.get('gps')
    if not h: return dict(st='na', txt=s3('nodata', lg, m='GPS'))
    m = h['metrics']
    tf = next((t for t, s, c in A.L.errors if s in (7, 11) and c != 0), None)
    return dict(st=h['status'], txt=s3('gps_f', lg, s=_r(m.get('min_sats'), 0), h=_r(m.get('max_hdop'), 2), p=_r(m.get('bad_pct')),
                                     g=m.get('glitches', 0), t=fmt_t(tf) if tf else '-'), t=tf, fix=['fx_gps'] if h['status'] != 'good' else [])


def c_gps_baro(A, lg):
    g = A.L.s('GPS'); b = A.L.s('BARO')
    if not (g.has('Alt') and b.has('Alt')): return dict(st='na', txt=s3('nodata', lg, m='GPS.Alt / BARO.Alt'))
    m = A.in_flight(b['t']) if A.flights else np.ones(len(b['t']), bool)
    if m.sum() < 20: return dict(st='na', txt=s3('nodata', lg, m='flight'))
    bt = b['t'][m]; ba = b['Alt'][m] - b['Alt'][m][0]
    ok = g['Status'] >= 3 if g.has('Status') else np.ones(len(g['t']), bool)
    if ok.sum() < 10: return dict(st='na', txt=s3('nodata', lg, m='GPS fix'))
    ga = np.interp(bt, g['t'][ok], g['Alt'][ok]); ga = ga - ga[0]
    d = np.abs(ba - ga); i = int(np.nanargmax(d)); mx = float(d[i]); mean = float(np.nanmean(ba - ga))
    st = 'bad' if mx > 25 else ('warn' if mx > 12 else 'good')
    return dict(st=st, txt=s3('gb_f', lg, d=_r(mx), t=fmt_t(float(bt[i])), m=_r(mean)), t=float(bt[i]), fix=['fx_baro'] if st != 'good' else [])


def c_compass(A, lg):
    h = A.health.get('ekf') or {}; met = h.get('metrics') or {}
    M = _inst(A.L, 'MAG')
    if not M and 'mag_var_pct' not in met: return dict(st='na', txt=s3('nodata', lg, m='MAG'))
    x = ''; worst = 0.0; tw = None
    if len(M) >= 2 and all(s.has('MagX') for s in M[:2]):
        a, b = M[0], M[1]
        h0 = np.degrees(np.arctan2(a['MagY'], a['MagX'])); h1 = np.degrees(np.arctan2(np.interp(a['t'], b['t'], b['MagY']), np.interp(a['t'], b['t'], b['MagX'])))
        d = np.abs((h0 - h1 + 180) % 360 - 180)
        mm = A.in_flight(a['t']) if A.flights else np.ones(len(d), bool)
        if mm.any():
            d = np.where(mm, d, 0); i = int(np.argmax(d)); worst = float(d[i]); tw = float(a['t'][i])
            x = s3('mag_x', lg, d=_r(worst), t=fmt_t(tw))
    var = met.get('mag_var_pct'); cor = met.get('mag_thr_corr')
    bad = any(f['k'] in ('mag_interf',) for f in h.get('findings', [])) or worst > 45
    warn = any(f['k'] in ('mag_var',) for f in h.get('findings', [])) or worst > 20
    st = 'bad' if bad else ('warn' if warn else 'good')
    return dict(st=st, txt=s3('mag_f', lg, v=_r(var), c=_r(cor, 2), n=max(1, len(M)), x=x), t=tw, fix=['fx_mag'] if st != 'good' else [])


def c_ekf(A, lg):
    h = A.health.get('ekf')
    if not h: return dict(st='na', txt=s3('nodata', lg, m='XKF4/NKF4'))
    met = {k: v for k, v in h['metrics'].items() if k in ('SV', 'SP', 'SH', 'SM', 'SVT')}
    ln = sum(1 for _, x in A.L.texts if 'lane switch' in x.lower() or 'primary changed' in x.lower())
    yr = sum(1 for _, x in A.L.texts if 'yaw reset' in x.lower() or 'yaw re-aligned' in x.lower())
    vs = ', '.join(f'{k}={_r(v, 2)}' for k, v in sorted(met.items(), key=lambda x: -x[1])[:4]) or '-'
    st = h['status']
    if ln >= 3 and st == 'good': st = 'warn'
    return dict(st=st, txt=s3('ekf_f', lg, v=vs, l=ln, y=yr), fix=['fx_ekf'] if st != 'good' else [])


def c_power(A, lg):
    h = A.health.get('power')
    if not h: return dict(st='na', txt=s3('nodata', lg, m='BAT'))
    m = h['metrics']; b = A.L.s('BAT'); tmin = None; sag = None
    try:
        k = int(np.nanargmin(np.where(b['Volt'] > 1, b['Volt'], np.nan))); tmin = float(b['t'][k])
        if m.get('current_sensor'): i = int(np.nanargmax(b['Curr'])); sag = float(np.nanmax(b['Volt']) - b['Volt'][i])
    except Exception: pass
    pw = A.L.s('POWR'); v1 = v2 = None; fx = []
    out = dict(st=h['status'], t=tmin)
    txt = s3('pw_f', lg, c=_r(m.get('per_cell_min'), 2), t=fmt_t(tmin) if tmin else '-', s=_r(sag, 2) if sag is not None else '-',
             a=_r(m.get('max_curr')) if m.get('max_curr') else '-', v1=_r(np.nanmin(pw['Vcc']), 2) if pw.has('Vcc') else '-',
             v2=_r(np.nanmax(pw['Vcc']), 2) if pw.has('Vcc') else '-')
    if h['status'] != 'good': fx.append('fx_power')
    if pw.has('Vcc'):
        mm = A.in_flight(pw['t']) if A.flights else np.ones(len(pw['t']), bool)
        vv = pw['Vcc'][mm] if mm.any() else pw['Vcc']
        d = float(np.nanmax(vv) - np.nanmin(vv))
        if d > 0.2:
            i = int(np.nanargmin(vv)); tt = (pw['t'][mm] if mm.any() else pw['t'])[i]
            txt += ' ' + s3('vcc_f', lg, d=_r(d, 2), t=fmt_t(float(tt))); fx.append('fx_vcc')
            if out['st'] == 'good': out['st'] = 'warn'
            if d > 0.4 or np.nanmin(vv) < 4.6: out['st'] = 'bad'
    out.update(txt=txt, fix=fx); return out


def c_ice(A, lg):
    info = getattr(A, 'info', {}) or {}
    ice = info.get('power') in ('gas', 'glow', 'hybrid') or float(A.L.params.get('ICE_ENABLE', 0) or 0) >= 1
    if not ice: return None
    r = A.L.s('RPM') if A.L.s('RPM').has('rpm1') else A.L.s('EFI')
    f = 'rpm1' if r.has('rpm1') else ('RPM' if r.has('RPM') else None)
    if not f: return dict(st='warn', txt=s3('ice_norpm', lg), fix=['fx_ice'])
    m = A.in_flight(r['t']) if A.flights else np.ones(len(r['t']), bool)
    if not m.any(): return dict(st='na', txt=s3('nodata', lg, m='RPM (flight)'))
    v = r[f][m]; tt = r['t'][m]; i = int(np.nanargmin(v)); z = bool(np.nanmin(v) < 100)
    st = 'bad' if z else 'good'
    return dict(st=st, txt=s3('ice_f', lg, r=int(np.nanmin(v)), t=fmt_t(float(tt[i])), z=s3('yes' if z else 'no', lg)), t=float(tt[i]),
                fix=['fx_ice'] if z else [])


def c_rc(A, lg):
    h = A.health.get('rc')
    if not h: return dict(st='na', txt=s3('nodata', lg, m='RCIN'))
    m = h['metrics']; tf = next((t for t, s, c in A.L.errors if s in (2, 5) and c != 0), None)
    return dict(st=h['status'], txt=s3('rc_f', lg, n=m.get('radio_failsafes', 0), l=_r(m.get('below_fs_pct', 0)), r=_r(m.get('rssi_min')) if m.get('rssi_min') is not None else '-'),
                t=tf, fix=['fx_rc'] if h['status'] != 'good' else [])


def c_modes(A, lg):
    from . import knowledge as K
    rows = []; bad = False
    for t, n, _, rsn in A.L.modes:
        r = K.MODE_REASON.get(rsn)
        if rsn in K.FAILSAFE_REASONS: bad = True
        rows.append(s3('mode_f', lg, t=fmt_t(t), m=K.mode_name(A.vehicle, n), r=K.tr3(r, lg) if r else '-'))
    if not rows: return dict(st='na', txt=s3('nodata', lg, m='MODE'))
    return dict(st='warn' if bad else 'good', txt=' · '.join(rows[:12]) + (' …' if len(rows) > 12 else ''), fix=['fx_rc'] if bad else [])


def c_att(A, lg):
    h = A.health.get('control')
    if not h: return dict(st='na', txt=s3('nodata', lg, m='ATT'))
    a = A.L.s('ATT'); m = h['metrics']; te = None; e = None
    try:
        mm = _steady(A, a['t'])
        err = np.maximum(np.abs(a['DesRoll'] - a['Roll']), np.abs(a['DesPitch'] - a['Pitch'])); err = np.where(mm, err, 0)
        i = int(np.argmax(err)); te = float(a['t'][i]); e = float(err[i])
    except Exception: pass
    return dict(st=h['status'], txt=s3('att_f', lg, r=_r(m.get('roll_rms')), p=_r(m.get('pitch_rms')), e=_r(e), t=fmt_t(te) if te else '-'),
                t=te, fix=['fx_tune'] if h['status'] != 'good' else [])


def c_osc(A, lg):
    a = A.L.s('RATE') if A.L.s('RATE').has('R') else None
    src = []
    if a is not None: src = [('roll', a['t'], a['R'] - a['RDes']), ('pitch', a['t'], a['P'] - a['PDes'])]
    else:
        at = A.L.s('ATT')
        if not at.has('Roll'): return dict(st='na', txt=s3('nodata', lg, m='RATE / ATT'))
        src = [('roll', at['t'], at['Roll'] - at['DesRoll']), ('pitch', at['t'], at['Pitch'] - at['DesPitch'])]
    best = None
    for ax, t, e in src:
        mm = A.in_flight(t) if A.flights else np.ones(len(t), bool)
        if mm.sum() < 256: continue
        t2 = t[mm]; e2 = np.nan_to_num(e[mm] - np.nanmean(e[mm]))
        fs = len(t2) / max(1e-3, t2[-1] - t2[0])
        if fs < 8: continue
        n = 1 << int(math.log2(min(len(e2), 16384)))
        # en büyük RMS'li pencerede spektrum
        w = max(range(0, len(e2) - n + 1, max(1, n // 2)), key=lambda i: float(np.std(e2[i:i + n])), default=0)
        seg = e2[w:w + n] * np.hanning(n)
        sp = np.abs(np.fft.rfft(seg)); fr = np.fft.rfftfreq(n, 1 / fs); sp[fr < 0.8] = 0
        k = int(np.argmax(sp))
        # salınım genliği: baskın frekans çevresindeki bant (manevra kaynaklı yavaş farkı saymaz)
        f0 = fr[k]; band = (fr > f0 * 0.7) & (fr < f0 * 1.3)
        amp = float(np.sqrt(2 * np.sum(sp[band] ** 2)) / np.sum(np.hanning(n)) * 2)
        if best is None or amp > best[2]: best = (ax, float(fr[k]), amp, float(t2[w]))
    if not best: return dict(st='na', txt=s3('nodata', lg, m='RATE/ATT'))
    ax, f, amp, tw = best
    st = 'bad' if amp > 5 else ('warn' if amp > 2 else 'good')
    axn = texts.T('ax_' + ax, lg) if texts.S.get('ax_' + ax) else ax
    kk = s3('osc_hi' if f >= 4 else 'osc_lo', lg) if st != 'good' else ''
    return dict(st=st, txt=s3('osc_f', lg, ax=axn, f=_r(f), a=_r(amp), k=kk), t=tw, fix=['fx_tune'] if st != 'good' else [])


def c_alt(A, lg):
    c = A.L.s('CTUN')
    if not c.has('Alt'):
        return dict(st='na', txt=s3('nodata', lg, m='CTUN.Alt'))
    dk = 'DAlt' if c.has('DAlt') else ('TAlt' if c.has('TAlt') else None)
    mm = A.in_flight(c['t']) if A.flights else np.ones(len(c['t']), bool)
    if not mm.any(): return dict(st='na', txt=s3('nodata', lg, m='flight'))
    r = mx = None; tw = None
    if dk:
        e = (c[dk] - c['Alt'])[mm]; ok = np.isfinite(e)
        if ok.sum() > 10:
            r = float(np.sqrt(np.nanmean(e[ok] ** 2))); i = int(np.nanargmax(np.abs(np.where(ok, e, 0)))); mx = float(abs(e[i])); tw = float(c['t'][mm][i])
    tk = 'ThO' if c.has('ThO') else ('ThrOut' if c.has('ThrOut') else None)
    sat = 0.0
    if tk:
        th = c[tk][mm]; top = 0.95 if np.nanmax(th) <= 1.5 else 95
        sat = float((th >= top).mean() * 100)
    st = 'bad' if (mx or 0) > 15 or sat > 25 else ('warn' if (mx or 0) > 6 or sat > 8 else 'good')
    return dict(st=st, txt=s3('alt_f', lg, r=_r(r), m=_r(mx), t=fmt_t(tw) if tw else '-', s=_r(sat)), t=tw,
                fix=(['fx_alt'] if sat > 8 else []) + (['fx_baro'] if (mx or 0) > 6 and sat <= 8 else []))


def c_motors(A, lg):
    h = A.health.get('motors')
    if not h: return None
    m = h['metrics']; ch = '-'
    for f in h['findings']:
        if f['k'] == 'mot_imbalance': ch = f['a'].get('ch', '-')
    return dict(st=h['status'], txt=s3('mot_f', lg, d=_r(m.get('motor_imbalance_us'), 0), ch=ch, h=_r(m.get('motor_headroom_us'), 0)),
                fix=['fx_motor'] if h['status'] != 'good' else [])


def c_yaw(A, lg):
    a = A.L.s('ATT')
    if not (a.has('Yaw') and a.has('DesYaw')): return dict(st='na', txt=s3('nodata', lg, m='ATT.DesYaw'))
    mm = A.in_flight(a['t']) if A.flights else np.ones(len(a['t']), bool)
    if not mm.any(): return dict(st='na', txt=s3('nodata', lg, m='flight'))
    e = np.abs((a['DesYaw'] - a['Yaw'] + 180) % 360 - 180)[mm]; i = int(np.nanargmax(e))
    r = float(np.sqrt(np.nanmean(e ** 2))); mx = float(e[i])
    st = 'bad' if r > 15 else ('warn' if r > 6 else 'good')
    return dict(st=st, txt=s3('yaw_f', lg, r=_r(r), m=_r(mx), t=fmt_t(float(a['t'][mm][i]))), t=float(a['t'][mm][i]),
                fix=(['fx_motor', 'fx_mag'] if st != 'good' else []))


def c_servo(A, lg):
    h = A.health.get('servo')
    if not h: return None
    m = {k: v for k, v in h['metrics'].items() if isinstance(v, (int, float))}
    if not m: return dict(st=h['status'], txt=s3('ok', lg))
    ch = max(m, key=m.get)
    return dict(st=h['status'], txt=s3('servo_f', lg, ch=ch, v=_r(m[ch])), fix=['fx_servo'] if h['status'] != 'good' else [])


def c_airspeed(A, lg):
    if A.profile not in ('plane', 'vtol'): return None
    h = A.health.get('airspeed')
    f = A.facts
    src = A.L.s('ARSP') if A.L.s('ARSP').has('Airspeed') else A.L.s('CTUN')
    k = 'Airspeed' if src.has('Airspeed') else ('As' if src.has('As') else None)
    if not k: return dict(st='na', txt=s3('nodata', lg, m='ARSP / CTUN.As'))
    tt = src['t']
    # kalkış koşusu / el atışı (ilk 6 s) ve iniş-çarpma anı (son 5 s) dışarıda: o anlarda düşük hava hızı doğaldır
    mm = np.zeros(len(tt), bool)
    for a, b in (A.flights or []): mm |= (tt >= a + 6) & (tt <= b - 5)
    if not A.flights: mm[:] = True
    if not mm.any(): return dict(st='na', txt=s3('nodata', lg, m='flight'))
    raw = np.asarray(src[k], float); kk = max(1, int(len(tt) / max(1.0, tt[-1] - tt[0])))
    sm = np.convolve(raw, np.ones(kk) / kk, 'same') if len(raw) > kk else raw   # 1 s ortalama (tek örnek sıçramaları değil)
    v = sm[mm]; i = int(np.nanargmin(v)); amin = float(v[i]); fbw = float(A.L.params.get('ARSPD_FBW_MIN', A.L.params.get('AIRSPEED_MIN', 0)) or 0)
    margin = amin - fbw * 0.85 if fbw else None
    st = h['status'] if h else 'good'
    if margin is not None and margin < 0: st = 'bad'
    elif margin is not None and margin < 2 and st == 'good': st = 'warn'
    return dict(st=st, txt=s3('as_f', lg, a=_r(amin), t=fmt_t(float(src['t'][mm][i])), m=_r(fbw), k=_r(margin) if margin is not None else '-'),
                t=float(src['t'][mm][i]), fix=['fx_as'] if st != 'good' else [])


def c_wind(A, lg):
    w = getattr(A, 'wind', None) or {}
    wx = getattr(A, 'weather_event', None) or getattr(A, 'weather', None)
    if not w and not wx: return dict(st='na', txt=s3('nodata', lg, m='wind'))
    wl = A.th.get('wind_warn', 10)
    wxs = ''
    if wx:
        from .why import w as ww
        wxs = ww('wx_line', lg, where=ww('wx_ev' if getattr(A, 'weather_event', None) else 'wx_home', lg), time=wx.get('time_utc', '-'),
                 **{k: ('-' if wx.get(k) is None else wx.get(k)) for k in ('temp', 'wind', 'gust', 'rh', 'precip')})
    mx = max(float(w.get('max') or 0), float((wx or {}).get('gust') or 0) * 0.8)
    st = 'bad' if mx > wl * 1.4 else ('warn' if mx > wl else 'good')
    return dict(st=st, txt=s3('wind_f', lg, m=_r(w.get('mean')), x=_r(w.get('max')), wx=wxs), fix=['fx_wind'] if st != 'good' else [])


def c_cpu(A, lg):
    h = A.health.get('cpu'); d = A.L.s('DSF')
    dp = int(np.nanmax(d['Dp'])) if d.has('Dp') else None
    if not h and dp is None: return dict(st='na', txt=s3('nodata', lg, m='PM / DSF'))
    m = (h or {}).get('metrics', {})
    st = (h or {}).get('status', 'good')
    if dp and dp > 100 and st == 'good': st = 'warn'
    return dict(st=st, txt=s3('cpu_f', lg, l=_r(m.get('load_max')), n=int(m['long_loops']) if isinstance(m.get('long_loops'), (int, float)) else '-', d=dp if dp is not None else '-'),
                fix=['fx_cpu'] if st != 'good' else [])


def c_params(A, lg):
    pf = [x for x in A.param_findings if x['sev'] > 0]
    if not pf: return dict(st='good', txt=s3('ok', lg))
    st = 'bad' if any(x['sev'] >= 2 for x in pf) else 'warn'
    return dict(st=st, txt=s3('par_f', lg, n=len(pf)) + ' ' + ' · '.join(texts.render(x['text'], lg, fmt_t) for x in pf[:6]), fix=[],
                params=[x.get('param') for x in pf if x.get('param')])


ROOT2CHECK = {'gps': ['gps'], 'ekf': ['ekf', 'compass', 'gps'], 'battery': ['power'], 'power': ['power', 'ice'], 'radio': ['rc'],
              'stall': ['airspeed'], 'vibration': ['vibration'], 'compass': ['compass'], 'control': ['att', 'servo', 'motors', 'osc'],
              'motor': ['flip', 'motors', 'ice']}
CHECKS = {k: globals()['c_' + k] for k in ALL_CHECKS}
SEV = {'bad': 0, 'warn': 1, 'good': 2, 'ok': 2, 'na': 3}


def solve(A, symptoms=None, text='', lang='tr'):
    """Belirtilere göre testleri çalıştırır. Dönüş: {'symptoms','checks':[...],'main','also','steps','params'}"""
    sy = list(dict.fromkeys(list(symptoms or []) + match_text(text)))
    ids = []
    for s_ in sy: ids += SYM[s_][3]
    if not ids: ids = list(ALL_CHECKS)
    ids = list(dict.fromkeys(ids))
    res = []
    for cid in ids:
        try: r = CHECKS[cid](A, lang)
        except Exception as e:
            r = dict(st='na', txt=s3('nodata', lang, m=str(e)[:60]))
        if r is None: continue
        r['id'] = cid; r['name'] = s3('n_' + cid, lang); r.setdefault('fix', []); r.setdefault('t', None)
        res.append(r)
    probs = sorted([r for r in res if r['st'] in ('bad', 'warn') and r['id'] not in ('crash', 'params', 'modes')],
                   key=lambda r: (SEV[r['st']], r['t'] if r['t'] is not None else 1e12))
    rc = ((A.why or {}).get('cause') if getattr(A, 'why', None) else None) or (A.root or {}).get('cause')
    pref = ROOT2CHECK.get(rc, [])
    pr = [r for r in probs if r['id'] in pref]
    if pr: probs = pr + [r for r in probs if r not in pr]
    fl = [r for r in probs if r['id'] == 'flip' and r['st'] == 'bad']
    if fl: probs = fl + [r for r in probs if r is not fl[0]]
    main = probs[0] if probs else None
    steps = []
    for r in probs + [r for r in res if r['id'] in ('params', 'modes') and r['st'] in ('bad', 'warn')]:
        for f in r['fix']:
            x = s3(f, lang)
            if x not in steps: steps.append(x)
    pn = []
    for r in probs: pn += PARAMS.get(r['id'], [])
    for r in res:
        if r['id'] == 'params': pn += r.get('params', [])
    P = A.L.params
    params = [(p, P.get(p)) for p in dict.fromkeys(pn) if p in P][:30]
    return {'symptoms': sy, 'checks': sorted(res, key=lambda r: SEV[r['st']]), 'main': main, 'also': probs[1:4], 'steps': steps, 'params': params}


def to_markdown(R, lang):
    st_ic = {'bad': '🔴', 'warn': '🟠', 'good': '🟢', 'ok': '🟢', 'na': '⚪'}
    L = []
    if R['symptoms']: L.append('**' + ' · '.join(symptom_label(s, lang) for s in R['symptoms']) + '**\n')
    L.append('## ' + s3('h_diag', lang))
    if R['main']:
        m = R['main']
        L.append(f"**{s3('most', lang)}:** {m['name']} — {m['txt']}")
        if R['also']: L.append(f"\n**{s3('also', lang)}:** " + '; '.join(r['name'] for r in R['also']))
    else:
        L.append(s3('h_none', lang))
    if R['steps']:
        L.append('\n## ' + s3('h_steps', lang))
        for i, x in enumerate(R['steps'], 1): L.append(f'{i}. {x}')
    if R['params']:
        L.append('\n## ' + s3('h_params', lang))
        L.append(', '.join(f'`{p}` = {v:g}' if isinstance(v, (int, float)) else f'`{p}` = {v}' for p, v in R['params']))
    L.append('\n## ' + s3('h_checks', lang))
    for r in R['checks']:
        tm = f" ({fmt_t(r['t'])})" if r.get('t') is not None else ''
        L.append(f"- {st_ic.get(r['st'], '')} **{r['name']}**{tm}: {r['txt']}")
    return '\n'.join(L)


def ai_solve(A, R, settings, usage, lang, user_text=''):
    """İnternet + kullanıcının kendi YZ anahtarı varsa: test sonuçlarını uzman diliyle tek bir çözüm raporuna dönüştürür."""
    from . import ai as AI
    from .advisor import LANG_NAME
    if not AI.available(settings): return None
    import json
    from .flightinfo import rows
    ctx = {'symptoms': [symptom_label(s, 'en') for s in R['symptoms']], 'user_description': user_text,
           'operator_form': dict(rows(getattr(A, 'info', {}) or {}, 'en')),
           'checks': [{'check': r['id'], 'status': r['st'], 'result': r['txt'], 'time': fmt_t(r['t']) if r.get('t') is not None else None} for r in solve(A, R['symptoms'], user_text, 'en')['checks']],
           'params': dict(R['params']), 'vehicle': A.vehicle, 'firmware': A.L.version}
    prompt = (f'Reply in {LANG_NAME.get(lang, "Turkish")}. You get the results of targeted log checks for a reported problem. '
              'Give: 1) the most likely root cause in one decisive sentence, with the time; 2) why (evidence with numbers and times); '
              '3) numbered fix steps with exact ArduPilot parameter names and suggested values where justified; 4) what to verify on the next flight. '
              'Do not invent data. If checks are inconclusive say what extra logging (LOG_BITMASK, RPM, ESC telemetry…) is needed. Max 400 words.\n'
              + json.dumps(ctx, ensure_ascii=False, default=str)[:15000])
    return AI.chat(settings, usage, 'You are a senior ArduPilot troubleshooting engineer.', prompt, max_tokens=2500)
