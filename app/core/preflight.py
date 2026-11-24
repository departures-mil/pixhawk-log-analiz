"""Uçuş öncesi .param risk kontrol listesi (TR / EN / AR).

Her madde: kategori, başlık, durum (pass / warn / fail / na), açıklama ve varsa önerilen düzeltme
(parametre = değer). Sonuç: 'go' (uçuşa hazır), 'caution' (dikkat) ya da 'nogo' (uçmayın).
Parametre Merkezi'ndeki risk denetimiyle (pcenter.risks) birlikte çalışır: oradaki aralık dışı / tanımsız
değerler de listeye 'Tanım dışı değerler' maddesi olarak eklenir.
"""
from __future__ import annotations
import re

LI = {'tr': 0, 'en': 1, 'ar': 2}
P_, C_, H_, R_, S_ = 'Plane', 'Copter', 'Heli', 'Rover', 'Sub'
MC = (C_, H_)

CATS = {
    'fs': ('Failsafe ve güvenlik', 'Failsafe and safety', 'الطوارئ والسلامة'),
    'bat': ('Batarya', 'Battery', 'البطارية'),
    'arm': ('Arm etme', 'Arming', 'التسليح'),
    'sens': ('Sensör kalibrasyonu', 'Sensor calibration', 'معايرة الحساسات'),
    'ctl': ('Kumanda, modlar ve çıkışlar', 'RC, modes and outputs', 'التحكم والأوضاع والمخارج'),
    'lim': ('Uçuş sınırları ve ayar', 'Flight limits and tuning', 'حدود الطيران والضبط'),
    'rtl': ('Eve dönüş', 'Return to launch', 'العودة للإقلاع'),
    'log': ('Kayıt', 'Logging', 'التسجيل'),
    'def': ('Tanım dışı değerler', 'Out-of-definition values', 'قيم خارج التعريف'),
}

S = {
    'title': ('Uçuş öncesi .param risk kontrol listesi', 'Pre-flight .param risk checklist', 'قائمة فحص مخاطر .param قبل الطيران'),
    'go': ('UÇUŞA HAZIR — kritik sorun bulunmadı.', 'READY TO FLY — no critical issue found.', 'جاهز للطيران — لم يُعثر على مشكلة حرجة.'),
    'caution': ('DİKKAT — uçuştan önce uyarıları gözden geçirin.', 'CAUTION — review the warnings before flight.', 'تنبيه — راجع التحذيرات قبل الطيران.'),
    'nogo': ('UÇMAYIN — kritik sorunlar düzeltilmeden uçuş güvenli değil.', 'DO NOT FLY — unsafe until the critical issues are fixed.', 'لا تطِر — الطيران غير آمن حتى تُصلح المشكلات الحرجة.'),
    'counts': ('{f} kritik · {w} uyarı · {p} geçti · {n} uygulanamaz', '{f} critical · {w} warnings · {p} passed · {n} n/a', '{f} حرجة · {w} تحذيرات · {p} ناجحة · {n} غير منطبقة'),
    'missing': ('{p} parametresi dosyada yok.', '{p} is not in the file.', 'المعامل {p} غير موجود في الملف.'),
    # ---- maddeler: (başlık, geçti, sorun)
    'rc_fs': (('Kumanda (RC) kaybı failsafe', 'RC loss failsafe', 'طوارئ فقدان التحكم'),
              ('Açık ({p} = {v}); eşik {tv} < en düşük gaz {mn}.', 'Enabled ({p} = {v}); threshold {tv} < minimum throttle {mn}.', 'مفعّل ({p} = {v})؛ العتبة {tv} < أدنى خانق {mn}.'),
              ('{p} = {v}: kumanda sinyali kesilince araç son komutla uçmaya devam eder.', '{p} = {v}: when the RC signal is lost the vehicle keeps the last command.', '{p} = {v}: عند فقدان إشارة التحكم تستمر المركبة بآخر أمر.')),
    'rc_fs_val': (('Failsafe gaz eşiği', 'Failsafe throttle threshold', 'عتبة خانق الطوارئ'),
                  ('{p} = {v} uygun.', '{p} = {v} is fine.', '{p} = {v} مناسب.'),
                  ('{p} = {v} en düşük gaz PWM değerine ({mn}) çok yakın ya da üstünde: failsafe yanlışlıkla tetiklenebilir ya da hiç tetiklenmeyebilir. Alıcı failsafe değerinin ~10 µs üstüne ayarlayın.',
                   '{p} = {v} is too close to or above the minimum throttle PWM ({mn}): failsafe may trigger falsely or never. Set it ~10 µs above the receiver failsafe value.',
                   '{p} = {v} قريب جداً من أدنى PWM للخانق ({mn}) أو أعلى منه: قد يعمل الطوارئ خطأً أو لا يعمل أبداً. اضبطه أعلى بنحو 10 µs من قيمة طوارئ المستقبل.')),
    'long_fs': (('Uzun sinyal kaybı eylemi', 'Long signal-loss action', 'إجراء فقدان الإشارة الطويل'),
                ('FS_LONG_ACTN = {v} (eve dönüş / süzülme).', 'FS_LONG_ACTN = {v} (RTL / glide).', 'FS_LONG_ACTN = {v} (عودة / انزلاق).'),
                ('FS_LONG_ACTN = 0: AUTO modundaysa görev sürer; görev dışında RTL yapılır. Görev uçuşlarında 1 (RTL) önerilir.',
                 'FS_LONG_ACTN = 0: in AUTO the mission continues; outside AUTO it does RTL. 1 (RTL) is recommended for missions.',
                 'FS_LONG_ACTN = 0: في AUTO تستمر المهمة؛ خارجها يعود. يوصى بـ 1 (RTL) للمهام.')),
    'gcs_fs': (('Telemetri (YKİ) kaybı failsafe', 'Ground station link failsafe', 'طوارئ فقدان المحطة الأرضية'),
               ('{p} = {v}.', '{p} = {v}.', '{p} = {v}.'),
               ('{p} = 0: telemetriyle (otomatik görev / uzak menzil) uçuyorsanız açın.', '{p} = 0: enable it if you fly with telemetry (auto missions / long range).', '{p} = 0: فعّله إن كنت تطير بالقياس عن بعد (مهام آلية / مدى بعيد).')),
    'ekf_fs': (('EKF failsafe', 'EKF failsafe', 'طوارئ EKF'),
               ('FS_EKF_ACTION = {v}.', 'FS_EKF_ACTION = {v}.', 'FS_EKF_ACTION = {v}.'),
               ('FS_EKF_ACTION = 0: konum tahmini bozulduğunda hiçbir şey yapılmaz (kaçma riski).', 'FS_EKF_ACTION = 0: nothing happens when the position estimate fails (fly-away risk).', 'FS_EKF_ACTION = 0: لا يحدث شيء عند فساد تقدير الموقع (خطر الهروب).')),
    'crash': (('Kırımda motor durdurma', 'Motor stop on crash', 'إيقاف المحرك عند التحطم'),
              ('{p} = {v}.', '{p} = {v}.', '{p} = {v}.'),
              ('{p} = 0: kırımdan sonra motorlar dönmeye devam eder (yangın / yaralanma riski).', '{p} = 0: motors keep spinning after a crash (fire / injury risk).', '{p} = 0: تستمر المحركات بالدوران بعد التحطم (خطر حريق / إصابة).')),
    'fence': (('Coğrafi sınır (geofence)', 'Geofence', 'السياج الجغرافي'),
              ('Açık; eylem {a}.', 'Enabled; action {a}.', 'مفعّل؛ الإجراء {a}.'),
              ('Kapalı ya da eylemsiz: kontrolden çıkan araç sınırlanmaz. FENCE_ENABLE = 1 ve FENCE_ACTION = 1 (RTL) önerilir.',
               'Disabled or without an action: a runaway vehicle is not contained. FENCE_ENABLE = 1 and FENCE_ACTION = 1 (RTL) recommended.',
               'معطل أو دون إجراء: لا تُحصر المركبة الهاربة. يوصى بـ FENCE_ENABLE = 1 وFENCE_ACTION = 1 (RTL).')),
    'bmon': (('Batarya ölçümü', 'Battery monitor', 'مراقبة البطارية'),
             ('BATT_MONITOR = {v} (gerilim + akım).', 'BATT_MONITOR = {v} (voltage + current).', 'BATT_MONITOR = {v} (جهد + تيار).'),
             ('BATT_MONITOR = {v}: {x}', 'BATT_MONITOR = {v}: {x}', 'BATT_MONITOR = {v}: {x}')),
    'bmon_none': ('batarya hiç izlenmiyor; düşük batarya failsafe çalışmaz.', 'the battery is not monitored at all; low-battery failsafe cannot work.', 'البطارية غير مراقبة إطلاقاً؛ لا يعمل طوارئ البطارية.'),
    'bmon_v': ('yalnız gerilim ölçülüyor; harcanan mAh ve kalan yüzde bilinmez.', 'voltage only; consumed mAh and remaining % are unknown.', 'الجهد فقط؛ السعة المستهلكة والنسبة المتبقية غير معروفة.'),
    'bvolt': (('Batarya gerilim eşikleri', 'Battery voltage thresholds', 'عتبات جهد البطارية'),
              ('Düşük {lo} V ({lc} V/hücre), kritik {cr} V ({cc} V/hücre) · {n}S.', 'Low {lo} V ({lc} V/cell), critical {cr} V ({cc} V/cell) · {n}S.', 'منخفض {lo} ف ({lc} ف/خلية)، حرج {cr} ف ({cc} ف/خلية) · {n}S.'),
              ('{x}', '{x}', '{x}')),
    'bv_zero': ('BATT_LOW_VOLT / BATT_CRT_VOLT = 0: gerilim failsafe kapalı.', 'BATT_LOW_VOLT / BATT_CRT_VOLT = 0: voltage failsafe disabled.', 'BATT_LOW_VOLT / BATT_CRT_VOLT = 0: طوارئ الجهد معطل.'),
    'bv_order': ('Kritik eşik ({cr} V) düşük eşikten ({lo} V) küçük olmalı.', 'The critical threshold ({cr} V) must be below the low threshold ({lo} V).', 'يجب أن تكون العتبة الحرجة ({cr} ف) أقل من المنخفضة ({lo} ف).'),
    'bv_cell': ('{n}S için hücre başına düşük {lc} V / kritik {cc} V; önerilen ~3,5 / ~3,3 V (Li-ion: ~3,3 / ~3,0 V).',
                'For {n}S: low {lc} V / critical {cc} V per cell; recommended ~3.5 / ~3.3 V (Li-ion: ~3.3 / ~3.0 V).',
                'لـ {n}S: منخفض {lc} ف / حرج {cc} ف لكل خلية؛ الموصى به ~3.5 / ~3.3 ف (ليثيوم أيون: ~3.3 / ~3.0 ف).'),
    'bfs': (('Batarya failsafe eylemleri', 'Battery failsafe actions', 'إجراءات طوارئ البطارية'),
            ('Düşük: {lo}, kritik: {cr}.', 'Low: {lo}, critical: {cr}.', 'منخفض: {lo}، حرج: {cr}.'),
            ('{x}', '{x}', '{x}')),
    'bfs_crt': ('BATT_FS_CRT_ACT = 0: kritik bataryada bile eylem yok (araç düşer).', 'BATT_FS_CRT_ACT = 0: no action even at critical battery (the vehicle falls).', 'BATT_FS_CRT_ACT = 0: لا إجراء حتى عند البطارية الحرجة (تسقط المركبة).'),
    'bfs_low': ('BATT_FS_LOW_ACT = 0: düşük bataryada yalnız uyarı verilir.', 'BATT_FS_LOW_ACT = 0: only a warning at low battery.', 'BATT_FS_LOW_ACT = 0: تحذير فقط عند انخفاض البطارية.'),
    'bcap': (('Batarya kapasitesi', 'Battery capacity', 'سعة البطارية'),
             ('BATT_CAPACITY = {v} mAh.', 'BATT_CAPACITY = {v} mAh.', 'BATT_CAPACITY = {v} mAh.'),
             ('BATT_CAPACITY = {v}: kalan yüzde ve mAh failsafe yanlış hesaplanır. Bataryanın gerçek kapasitesini girin.',
              'BATT_CAPACITY = {v}: remaining % and mAh failsafe are computed wrongly. Enter the real battery capacity.',
              'BATT_CAPACITY = {v}: تُحسب النسبة المتبقية وطوارئ mAh بشكل خاطئ. أدخل السعة الحقيقية.')),
    'armchk': (('Arm öncesi kontroller', 'Pre-arm checks', 'فحوص ما قبل التسليح'),
               ('Tüm kontroller açık.', 'All checks enabled.', 'جميع الفحوص مفعّلة.'),
               ('{x}', '{x}', '{x}')),
    'arm_off': ('ARMING_CHECK = 0: bütün güvenlik kontrolleri kapalı (GPS, pusula, ivmeölçer, batarya…).', 'ARMING_CHECK = 0: all safety checks disabled (GPS, compass, accel, battery…).', 'ARMING_CHECK = 0: جميع فحوص السلامة معطلة (GPS، البوصلة، التسارع، البطارية…).'),
    'arm_part': ('Bazı kontroller kapalı ({p} = {v}). Yalnız bilerek kapattıklarınız kalsın.', 'Some checks disabled ({p} = {v}). Keep only those you disabled deliberately.', 'بعض الفحوص معطلة ({p} = {v}). أبقِ فقط ما عطلته عن قصد.'),
    'armreq': (('Arm zorunluluğu', 'Arming required', 'التسليح مطلوب'),
               ('ARMING_REQUIRE = {v}.', 'ARMING_REQUIRE = {v}.', 'ARMING_REQUIRE = {v}.'),
               ('ARMING_REQUIRE = 0: arm etmeden motor çalışabilir — yerde pervane yaralanma riski.', 'ARMING_REQUIRE = 0: the motor can run without arming — propeller injury risk on the ground.', 'ARMING_REQUIRE = 0: قد يعمل المحرك دون تسليح — خطر إصابة بالمروحة على الأرض.')),
    'compass': (('Pusula kalibrasyonu', 'Compass calibration', 'معايرة البوصلة'),
                ('Ofsetler kalibre edilmiş (|ofset| = {m}).', 'Offsets calibrated (|offset| = {m}).', 'الإزاحات معايرة (|الإزاحة| = {m}).'),
                ('{x}', '{x}', '{x}')),
    'cmp_zero': ('Pusula ofsetlerinin hepsi 0: pusula kalibre edilmemiş.', 'All compass offsets are 0: the compass is not calibrated.', 'جميع إزاحات البوصلة 0: البوصلة غير معايرة.'),
    'cmp_big': ('Pusula ofseti çok büyük ({m}): manyetik parazit ya da kötü kalibrasyon. Pusulayı güç kablolarından uzaklaştırıp yeniden kalibre edin.',
                'Compass offset too large ({m}): magnetic interference or bad calibration. Move the compass away from power wires and recalibrate.',
                'إزاحة البوصلة كبيرة جداً ({m}): تداخل مغناطيسي أو معايرة سيئة. أبعد البوصلة عن أسلاك الطاقة وأعد المعايرة.'),
    'cmp_off': ('COMPASS_USE = 0: pusula kullanılmıyor (yalnız GPS yönü).', 'COMPASS_USE = 0: compass not used (GPS heading only).', 'COMPASS_USE = 0: البوصلة غير مستخدمة (اتجاه GPS فقط).'),
    'accel': (('İvmeölçer kalibrasyonu', 'Accelerometer calibration', 'معايرة مقياس التسارع'),
              ('Kalibre edilmiş.', 'Calibrated.', 'معاير.'),
              ('INS_ACCOFFS / INS_ACCSCAL varsayılan değerde: ivmeölçer kalibre edilmemiş (ufuk yanlış olabilir).', 'INS_ACCOFFS / INS_ACCSCAL at defaults: accelerometer not calibrated (horizon may be wrong).', 'INS_ACCOFFS / INS_ACCSCAL على الافتراضي: مقياس التسارع غير معاير (قد يكون الأفق خاطئاً).')),
    'gps': (('GPS', 'GPS', 'GPS'),
            ('{p} = {v}.', '{p} = {v}.', '{p} = {v}.'),
            ('{p} = 0: GPS devre dışı; RTL, AUTO, LOITER çalışmaz.', '{p} = 0: GPS disabled; RTL, AUTO, LOITER cannot work.', '{p} = 0: GPS معطل؛ لا تعمل RTL وAUTO وLOITER.')),
    'arspd': (('Hava hızı sensörü', 'Airspeed sensor', 'حساس السرعة الجوية'),
              ('{p} = {v}, kullanımda.', '{p} = {v}, in use.', '{p} = {v}، مستخدم.'),
              ('Hava hızı sensörü yok ya da kullanılmıyor: TECS sentetik hızla çalışır; stall koruması zayıflar. Uygunsa sensör takın ve {p2} = 1 yapın.',
               'No airspeed sensor or not used: TECS runs on synthetic airspeed; stall protection is weaker. Fit one if possible and set {p2} = 1.',
               'لا يوجد حساس سرعة جوية أو غير مستخدم: يعمل TECS بسرعة تقديرية؛ تضعف الحماية من الانهيار. ركّب حساساً إن أمكن واضبط {p2} = 1.')),
    'spd': (('Hız sınırları', 'Airspeed limits', 'حدود السرعة الجوية'),
            ('En düşük {mn} < seyir {cr} < en yüksek {mx} m/s.', 'Minimum {mn} < cruise {cr} < maximum {mx} m/s.', 'الأدنى {mn} < التطواف {cr} < الأقصى {mx} م/ث.'),
            ('Hız sınırları tutarsız: en düşük {mn}, seyir {cr}, en yüksek {mx} m/s. En düşük < seyir < en yüksek olmalı; en düşük hız stall hızının ~%20 üstünde olmalı.',
             'Airspeed limits are inconsistent: min {mn}, cruise {cr}, max {mx} m/s. Must be min < cruise < max; min should be ~20% above stall speed.',
             'حدود السرعة غير متسقة: الأدنى {mn}، التطواف {cr}، الأقصى {mx} م/ث. يجب أن يكون الأدنى < التطواف < الأقصى؛ والأدنى أعلى من سرعة الانهيار بنحو 20%.')),
    'roll': (('Yatış ve yunuslama sınırları', 'Bank and pitch limits', 'حدود الدوران والميلان'),
             ('Yatış {r}°, burun yukarı {pu}°, aşağı {pd}°.', 'Bank {r}°, pitch up {pu}°, down {pd}°.', 'الدوران {r}°، الميلان للأعلى {pu}° وللأسفل {pd}°.'),
             ('Yatış {r}°, burun yukarı {pu}°, aşağı {pd}°: {x}', 'Bank {r}°, pitch up {pu}°, down {pd}°: {x}', 'الدوران {r}°، الميلان للأعلى {pu}° وللأسفل {pd}°: {x}')),
    'roll_x': ('65°’den büyük yatış ya da 25°’den büyük burun yukarı açısı stall / spin riskini artırır.', 'Bank above 65° or pitch-up above 25° increases stall / spin risk.', 'دوران أكبر من 65° أو ميلان للأعلى أكبر من 25° يزيد خطر الانهيار / الدوران اللولبي.'),
    'thr': (('Gaz sınırları', 'Throttle limits', 'حدود الخانق'),
            ('THR_MIN {mn} … THR_MAX {mx} %.', 'THR_MIN {mn} … THR_MAX {mx} %.', 'THR_MIN {mn} … THR_MAX {mx} %.'),
            ('THR_MIN {mn} / THR_MAX {mx}: {x}', 'THR_MIN {mn} / THR_MAX {mx}: {x}', 'THR_MIN {mn} / THR_MAX {mx}: {x}')),
    'thr_x': ('THR_MAX ≤ THR_MIN ya da çok düşük azami gaz; negatif THR_MIN yalnız ters itkide kullanılır.', 'THR_MAX ≤ THR_MIN or very low max throttle; negative THR_MIN is only for reverse thrust.', 'THR_MAX ≤ THR_MIN أو خانق أقصى منخفض جداً؛ THR_MIN السالب للدفع العكسي فقط.'),
    'spin': (('Motor dönüş eşikleri', 'Motor spin thresholds', 'عتبات دوران المحركات'),
             ('MOT_SPIN_ARM {a} < MOT_SPIN_MIN {m}.', 'MOT_SPIN_ARM {a} < MOT_SPIN_MIN {m}.', 'MOT_SPIN_ARM {a} < MOT_SPIN_MIN {m}.'),
             ('MOT_SPIN_ARM {a} / MOT_SPIN_MIN {m}: SPIN_ARM, SPIN_MIN’den küçük olmalı; SPIN_MIN genelde 0,08–0,15 (çok düşükse hızlı alçalmada motor durabilir).',
              'MOT_SPIN_ARM {a} / MOT_SPIN_MIN {m}: SPIN_ARM must be below SPIN_MIN; SPIN_MIN is usually 0.08–0.15 (too low → motors may stop in fast descents).',
              'MOT_SPIN_ARM {a} / MOT_SPIN_MIN {m}: يجب أن يكون SPIN_ARM أقل من SPIN_MIN؛ وSPIN_MIN عادة 0.08–0.15 (إن كان منخفضاً جداً قد تتوقف المحركات عند النزول السريع).')),
    'hover': (('Hover gazı', 'Hover throttle', 'خانق التحويم'),
              ('MOT_THST_HOVER = {v}.', 'MOT_THST_HOVER = {v}.', 'MOT_THST_HOVER = {v}.'),
              ('MOT_THST_HOVER = {v}: {x}', 'MOT_THST_HOVER = {v}: {x}', 'MOT_THST_HOVER = {v}: {x}')),
    'hover_hi': ('0,5’ten büyük: araç ağır ya da itki yetersiz; manevra payı az.', 'above 0.5: the vehicle is heavy or underpowered; little control margin.', 'أكبر من 0.5: المركبة ثقيلة أو الدفع غير كافٍ؛ هامش تحكم قليل.'),
    'hover_lo': ('0,15’ten küçük: araç aşırı güçlü; ayar hassasiyeti düşer.', 'below 0.15: overpowered vehicle; tuning resolution suffers.', 'أقل من 0.15: المركبة قوية جداً؛ تقل دقة الضبط.'),
    'angle': (('Azami eğim açısı', 'Maximum lean angle', 'أقصى زاوية ميل'),
              ('ANGLE_MAX = {v}°.', 'ANGLE_MAX = {v}°.', 'ANGLE_MAX = {v}°.'),
              ('ANGLE_MAX = {v}°: 45°’den büyük eğim irtifa kaybına yol açabilir.', 'ANGLE_MAX = {v}°: lean above 45° can cause altitude loss.', 'ANGLE_MAX = {v}°: ميل أكبر من 45° قد يسبب فقدان الارتفاع.')),
    'notch': (('Titreşim çentik filtresi', 'Harmonic notch filter', 'مرشح الشق التوافقي'),
              ('INS_HNTCH_ENABLE = 1.', 'INS_HNTCH_ENABLE = 1.', 'INS_HNTCH_ENABLE = 1.'),
              ('INS_HNTCH_ENABLE = 0: motor titreşimi filtrelenmiyor; ayar ve konum tutma kötüleşebilir.', 'INS_HNTCH_ENABLE = 0: motor noise is not filtered; tuning and position hold may suffer.', 'INS_HNTCH_ENABLE = 0: لا يُرشَّح ضجيج المحركات؛ قد يسوء الضبط وتثبيت الموقع.')),
    'outputs': (('Servo / motor çıkışları', 'Servo / motor outputs', 'مخارج المؤازرات / المحركات'),
                ('Gerekli çıkışlar atanmış: {x}.', 'Required outputs assigned: {x}.', 'المخارج المطلوبة معيّنة: {x}.'),
                ('Eksik çıkış: {x}. SERVOx_FUNCTION atamalarını kontrol edin.', 'Missing output: {x}. Check the SERVOx_FUNCTION assignments.', 'مخرج مفقود: {x}. افحص تعيينات SERVOx_FUNCTION.')),
    'servo_rng': (('Servo uç değerleri', 'Servo end points', 'نقاط نهاية المؤازرات'),
                  ('Tüm SERVOx MIN < TRIM < MAX.', 'All SERVOx MIN < TRIM < MAX.', 'جميع SERVOx MIN < TRIM < MAX.'),
                  ('{x}: TRIM, MIN ile MAX arasında olmalı.', '{x}: TRIM must lie between MIN and MAX.', '{x}: يجب أن يكون TRIM بين MIN وMAX.')),
    'rc_cal': (('Kumanda kalibrasyonu', 'RC calibration', 'معايرة جهاز التحكم'),
               ('Kanal 1–4 kalibre edilmiş.', 'Channels 1–4 calibrated.', 'القنوات 1–4 معايرة.'),
               ('{x}', '{x}', '{x}')),
    'rc_bad': ('RC{c}: MIN {mn} / TRIM {tr} / MAX {mx} tutarsız.', 'RC{c}: MIN {mn} / TRIM {tr} / MAX {mx} inconsistent.', 'RC{c}: MIN {mn} / TRIM {tr} / MAX {mx} غير متسقة.'),
    'rc_def': ('Kanal 1–4 tam varsayılan (1100/1500/1900): kumanda kalibrasyonu yapılmamış olabilir.', 'Channels 1–4 exactly at defaults (1100/1500/1900): RC calibration may not have been done.', 'القنوات 1–4 على القيم الافتراضية تماماً (1100/1500/1900): ربما لم تُجرَ معايرة التحكم.'),
    'modes': (('Uçuş modu anahtarı', 'Flight mode switch', 'مفتاح أوضاع الطيران'),
              ('Kurtarma modu var: {x}.', 'Recovery mode available: {x}.', 'وضع إنقاذ متاح: {x}.'),
              ('FLTMODE1–6 arasında RTL / el ile kurtarma modu yok. Bir konuma RTL atayın.', 'No RTL / manual recovery mode among FLTMODE1–6. Assign RTL to one position.', 'لا يوجد وضع RTL / إنقاذ يدوي بين FLTMODE1–6. عيّن RTL لأحد المواضع.')),
    'rtl': (('Eve dönüş irtifası', 'RTL altitude', 'ارتفاع العودة'),
            ('{p} = {v} {u}.', '{p} = {v} {u}.', '{p} = {v} {u}.'),
            ('{p} = {v} {u}: engellerin (ağaç, bina, direk) üstünden geçmek için çok alçak. En az {m} {u} önerilir.',
             '{p} = {v} {u}: too low to clear obstacles (trees, buildings, masts). At least {m} {u} recommended.',
             '{p} = {v} {u}: منخفض جداً لتجاوز العوائق (أشجار، مبانٍ، صوارٍ). يوصى بـ {m} {u} على الأقل.')),
    'qassist': (('VTOL yardım hızı', 'VTOL assist speed', 'سرعة مساعدة VTOL'),
                ('Q_ASSIST_SPEED = {v} m/s.', 'Q_ASSIST_SPEED = {v} m/s.', 'Q_ASSIST_SPEED = {v} م/ث.'),
                ('Q_ASSIST_SPEED = {v}: hız düşünce VTOL motorları yardım etmez. Stall hızının biraz üstüne ayarlayın.',
                 'Q_ASSIST_SPEED = {v}: VTOL motors do not help when airspeed drops. Set it slightly above stall speed.',
                 'Q_ASSIST_SPEED = {v}: لا تساعد محركات VTOL عند انخفاض السرعة. اضبطه أعلى قليلاً من سرعة الانهيار.')),
    'rsc': (('Rotor hız kontrolü', 'Rotor speed control', 'التحكم في سرعة الدوار'),
            ('H_RSC_MODE = {v}.', 'H_RSC_MODE = {v}.', 'H_RSC_MODE = {v}.'),
            ('H_RSC_MODE = 0: rotor hız kontrolü tanımsız.', 'H_RSC_MODE = 0: rotor speed control undefined.', 'H_RSC_MODE = 0: التحكم في سرعة الدوار غير معرّف.')),
    'logbm': (('Log kaydı', 'Logging', 'التسجيل'),
              ('LOG_BITMASK = {v}; ayar analizi için PID/TECS kayıtları {x}.', 'LOG_BITMASK = {v}; PID/TECS logging for tuning analysis {x}.', 'LOG_BITMASK = {v}؛ تسجيل PID/TECS لتحليل الضبط {x}.'),
              ('LOG_BITMASK = 0: hiç log alınmıyor; kaza olursa sebep bulunamaz.', 'LOG_BITMASK = 0: nothing is logged; a crash cannot be investigated.', 'LOG_BITMASK = 0: لا يُسجَّل شيء؛ لا يمكن التحقيق في التحطم.')),
    'on': ('açık', 'on', 'مفعّل'), 'off': ('kapalı olabilir', 'may be off', 'قد يكون معطلاً'),
    'def_items': (('Tanım dışı değerler', 'Out-of-definition values', 'قيم خارج التعريف'),
                  ('Tüm değerler tanımlı aralıklarda.', 'All values are within their defined ranges.', 'جميع القيم ضمن نطاقاتها المعرّفة.'),
                  ('{n} parametre önerilen aralığın / seçeneklerin dışında: {x}', '{n} parameters outside their recommended range / options: {x}', '{n} معاملات خارج النطاق / الخيارات الموصى بها: {x}')),
    'rover_fs': (('Rover failsafe eylemi', 'Rover failsafe action', 'إجراء طوارئ المركبة الأرضية'),
                 ('FS_ACTION = {v}.', 'FS_ACTION = {v}.', 'FS_ACTION = {v}.'),
                 ('FS_ACTION = 0: failsafe’te araç durmaz / dönmez.', 'FS_ACTION = 0: the vehicle does not stop / return on failsafe.', 'FS_ACTION = 0: لا تتوقف المركبة / لا تعود عند الطوارئ.')),
}


def s(k, lang, **kw):
    v = S[k][LI.get(lang, 0)]
    return v.format(**kw) if kw else v


def _g(P, *names, d=None):
    for n in names:
        if n in P: return P[n], n
    return d, (names[0] if names else '')


def _f(v):
    try:
        v = float(v)
        return str(int(v)) if v == int(v) else f'{v:.3g}'
    except Exception:
        return str(v)


class _C:
    def __init__(self, lang): self.lang = lang; self.items = []

    def add(self, key, cat, st, fix=None, text=None, **kw):
        tt = S[key]
        title = tt[0][LI.get(self.lang, 0)]
        if text is None:
            text = tt[1 if st == 'pass' else 2][LI.get(self.lang, 0)].format(**kw) if st != 'na' else ''
        self.items.append({'id': key, 'cat': cat, 'cat_t': CATS[cat][LI.get(self.lang, 0)], 'title': title, 'st': st,
                           'text': text, 'fix': fix or []})


def _cells(P, ctx):
    c = (ctx or {}).get('cells')
    try:
        c = int(c)
        if c > 0: return c
    except Exception:
        pass
    lo = P.get('BATT_LOW_VOLT', 0) or P.get('BATT_ARM_VOLT', 0) or P.get('BATT_CRT_VOLT', 0)
    if lo:
        for n in range(1, 25):
            if 3.0 * n <= lo <= 3.9 * n: return n
    return None


def checklist(params, vehicle='Plane', lang='tr', ctx=None):
    """params: {ad: değer}; vehicle: Plane/Copter/Heli/Rover/Sub; ctx: {'cells', 'profile'} (isteğe bağlı).
    Döner: {'status','summary','counts','items':[{id,cat,cat_t,title,st,text,fix:[(param,değer)]}]}"""
    P = params or {}; lg = lang; C = _C(lg); ctx = ctx or {}
    v = vehicle if vehicle in (P_, C_, H_, R_, S_) else P_
    mc = v in MC
    vtol = v == P_ and P.get('Q_ENABLE', 0) >= 1
    thr_ch = int(P.get('RCMAP_THROTTLE', 3) or 3)
    rc_min = P.get(f'RC{thr_ch}_MIN', 1100)
    # ------------------------------------------------ failsafe
    if v == P_:
        en, pn = _g(P, 'THR_FAILSAFE', d=None)
        val, pv = _g(P, 'THR_FS_VALUE', d=950)
    elif v in (C_, H_, R_):
        en, pn = _g(P, 'FS_THR_ENABLE', d=None)
        val, pv = _g(P, 'FS_THR_VALUE', d=975)
    else:
        en = None
    if en is not None:
        if en == 0:
            C.add('rc_fs', 'fs', 'fail', [(pn, 1)], p=pn, v=_f(en))
        else:
            C.add('rc_fs', 'fs', 'pass', p=pn, v=_f(en), tv=_f(val), mn=_f(rc_min))
            if val >= rc_min - 5 or val < 850:
                C.add('rc_fs_val', 'fs', 'warn', [(pv, int(min(rc_min - 30, 975)))], p=pv, v=_f(val), mn=_f(rc_min))
            else:
                C.add('rc_fs_val', 'fs', 'pass', p=pv, v=_f(val))
    if v == P_ and 'FS_LONG_ACTN' in P:
        a = P['FS_LONG_ACTN']
        C.add('long_fs', 'fs', 'warn' if a == 0 else 'pass', [('FS_LONG_ACTN', 1)] if a == 0 else None, v=_f(a))
    gk = 'FS_GCS_ENABL' if v in (P_, R_) else 'FS_GCS_ENABLE'
    if gk in P:
        C.add('gcs_fs', 'fs', 'warn' if P[gk] == 0 else 'pass', None, p=gk, v=_f(P[gk]))
    if mc and 'FS_EKF_ACTION' in P:
        C.add('ekf_fs', 'fs', 'fail' if P['FS_EKF_ACTION'] == 0 else 'pass', [('FS_EKF_ACTION', 1)] if P['FS_EKF_ACTION'] == 0 else None, v=_f(P['FS_EKF_ACTION']))
    ck = 'FS_CRASH_CHECK' if mc else 'CRASH_DETECT' if v == P_ else None
    if ck and ck in P:
        st = 'pass' if P[ck] else ('warn' if mc else 'na')
        if v == P_ and not P[ck]: st = 'warn'
        C.add('crash', 'fs', st, [(ck, 1)] if not P[ck] else None, p=ck, v=_f(P[ck]))
    if v == R_ and 'FS_ACTION' in P:
        C.add('rover_fs', 'fs', 'fail' if P['FS_ACTION'] == 0 else 'pass', [('FS_ACTION', 2)] if P['FS_ACTION'] == 0 else None, v=_f(P['FS_ACTION']))
    if 'FENCE_ENABLE' in P:
        fe = P.get('FENCE_ENABLE', 0); fa = P.get('FENCE_ACTION', 0)
        ok = fe and fa
        C.add('fence', 'fs', 'pass' if ok else 'warn', None if ok else [('FENCE_ENABLE', 1), ('FENCE_ACTION', 1)], a=_f(fa))
    # ------------------------------------------------ batarya
    bm = P.get('BATT_MONITOR')
    if bm is not None:
        if bm == 0:
            C.add('bmon', 'bat', 'fail', [('BATT_MONITOR', 4)], v=_f(bm), x=s('bmon_none', lg))
        elif bm == 3:
            C.add('bmon', 'bat', 'warn', [('BATT_MONITOR', 4)], v=_f(bm), x=s('bmon_v', lg))
        else:
            C.add('bmon', 'bat', 'pass', v=_f(bm))
    if bm:
        lo = float(P.get('BATT_LOW_VOLT', 0) or 0); cr = float(P.get('BATT_CRT_VOLT', 0) or 0)
        n = _cells(P, ctx)
        if lo == 0 and cr == 0:
            fx = [('BATT_LOW_VOLT', round(3.5 * n, 1)), ('BATT_CRT_VOLT', round(3.3 * n, 1))] if n else None
            C.add('bvolt', 'bat', 'fail', fx, x=s('bv_zero', lg))
        elif lo == 0 or cr == 0:
            fx = [('BATT_LOW_VOLT', round(3.5 * n, 1))] if (n and lo == 0) else [('BATT_CRT_VOLT', round(3.3 * n, 1))] if n else None
            C.add('bvolt', 'bat', 'warn', fx, x=s('bv_zero', lg))
        elif cr and lo and cr >= lo:
            C.add('bvolt', 'bat', 'fail', None, x=s('bv_order', lg, cr=_f(cr), lo=_f(lo)))
        elif n:
            lc, cc = lo / n, cr / n
            liion = (ctx.get('chem') == 'liion')
            ok = (3.2 if liion else 3.4) <= lc <= 3.8 and (2.9 if liion else 3.15) <= cc <= 3.6
            if ok:
                C.add('bvolt', 'bat', 'pass', lo=_f(lo), lc=f'{lc:.2f}', cr=_f(cr), cc=f'{cc:.2f}', n=n)
            else:
                C.add('bvolt', 'bat', 'warn', [('BATT_LOW_VOLT', round(3.5 * n, 1)), ('BATT_CRT_VOLT', round(3.3 * n, 1))],
                      x=s('bv_cell', lg, n=n, lc=f'{lc:.2f}', cc=f'{cc:.2f}'))
        fl, fc = P.get('BATT_FS_LOW_ACT'), P.get('BATT_FS_CRT_ACT')
        if fl is not None or fc is not None:
            if fc == 0:
                C.add('bfs', 'bat', 'fail', [('BATT_FS_CRT_ACT', 1 if mc else 1)], x=s('bfs_crt', lg))
            elif fl == 0:
                C.add('bfs', 'bat', 'warn', [('BATT_FS_LOW_ACT', 2 if mc else 1)], x=s('bfs_low', lg))
            else:
                C.add('bfs', 'bat', 'pass', lo=_f(fl), cr=_f(fc))
        if bm >= 4 and 'BATT_CAPACITY' in P:
            cap = P['BATT_CAPACITY']
            C.add('bcap', 'bat', 'pass' if cap >= 300 else 'warn', None, v=_f(cap))
    # ------------------------------------------------ arm
    if 'ARMING_CHECK' in P or 'ARMING_SKIPCHK' in P:
        ac = P.get('ARMING_CHECK'); sk = P.get('ARMING_SKIPCHK', 0)
        if ac == 0:
            C.add('armchk', 'arm', 'fail', [('ARMING_CHECK', 1)], x=s('arm_off', lg))
        elif (ac is not None and not (int(ac) & 1)) or sk:
            pn_, vv = ('ARMING_SKIPCHK', sk) if sk else ('ARMING_CHECK', ac)
            C.add('armchk', 'arm', 'warn', None, x=s('arm_part', lg, p=pn_, v=_f(vv)))
        else:
            C.add('armchk', 'arm', 'pass')
    if v in (P_, R_) and 'ARMING_REQUIRE' in P:
        C.add('armreq', 'arm', 'fail' if P['ARMING_REQUIRE'] == 0 else 'pass', [('ARMING_REQUIRE', 1)] if P['ARMING_REQUIRE'] == 0 else None, v=_f(P['ARMING_REQUIRE']))
    # ------------------------------------------------ sensörler
    if 'COMPASS_USE' in P or 'COMPASS_OFS_X' in P:
        if P.get('COMPASS_USE', 1) == 0:
            C.add('compass', 'sens', 'warn' if v != R_ else 'na', None, x=s('cmp_off', lg))
        else:
            o = [P.get(f'COMPASS_OFS_{a}', 0) for a in 'XYZ']
            m = (sum(x * x for x in o)) ** 0.5
            if all(x == 0 for x in o):
                C.add('compass', 'sens', 'fail', None, x=s('cmp_zero', lg))
            elif m > 600:
                C.add('compass', 'sens', 'warn', None, x=s('cmp_big', lg, m=int(m)))
            else:
                C.add('compass', 'sens', 'pass', m=int(m))
    if 'INS_ACCOFFS_X' in P:
        off = [P.get(f'INS_ACCOFFS_{a}', 0) for a in 'XYZ']; sc = [P.get(f'INS_ACCSCAL_{a}', 1) for a in 'XYZ']
        C.add('accel', 'sens', 'warn' if all(x == 0 for x in off) and all(x == 1 for x in sc) else 'pass')
    gv, gp = _g(P, 'GPS1_TYPE', 'GPS_TYPE')
    if gv is not None:
        C.add('gps', 'sens', 'fail' if gv == 0 and v != S_ else 'pass', [(gp, 1)] if gv == 0 and v != S_ else None, p=gp, v=_f(gv))
    if v == P_:
        at, ap = _g(P, 'ARSPD_TYPE', 'ARSPD1_TYPE')
        au, aup = _g(P, 'ARSPD_USE', 'ARSPD1_USE')
        if at is not None:
            ok = bool(at) and bool(au if au is not None else 1)
            C.add('arspd', 'sens', 'pass' if ok else 'warn', None, p=ap, v=_f(at), p2=aup)
        mn, _ = _g(P, 'AIRSPEED_MIN', 'ARSPD_FBW_MIN'); mx, _ = _g(P, 'AIRSPEED_MAX', 'ARSPD_FBW_MAX')
        cr, crn = _g(P, 'AIRSPEED_CRUISE', 'TRIM_ARSPD_CM')
        if cr is not None and crn == 'TRIM_ARSPD_CM': cr = cr / 100.0
        if mn is not None and mx is not None:
            ok = mn < mx and (cr is None or mn <= cr <= mx)
            C.add('spd', 'lim', 'pass' if ok else 'warn', None, mn=_f(mn), cr=_f(cr) if cr is not None else '-', mx=_f(mx))
        r, _ = _g(P, 'ROLL_LIMIT_DEG', 'LIM_ROLL_CD'); pu, pun = _g(P, 'PTCH_LIM_MAX_DEG', 'LIM_PITCH_MAX'); pd, pdn = _g(P, 'PTCH_LIM_MIN_DEG', 'LIM_PITCH_MIN')
        if r is not None:
            if r > 180: r = r / 100.0
            pu = (pu / 100.0 if pu and abs(pu) > 180 else pu) or 0; pd = (pd / 100.0 if pd and abs(pd) > 180 else pd) or 0
            bad = r > 65 or pu > 25
            C.add('roll', 'lim', 'warn' if bad else 'pass', None, r=_f(r), pu=_f(pu), pd=_f(pd), x=s('roll_x', lg))
        if 'THR_MAX' in P:
            mn_, mx_ = P.get('THR_MIN', 0), P['THR_MAX']
            bad = mx_ <= mn_ or mx_ < 50 or (mn_ < 0 and not P.get('USE_REV_THRUST', 0))
            C.add('thr', 'lim', 'warn' if bad else 'pass', None, mn=_f(mn_), mx=_f(mx_), x=s('thr_x', lg))
        if vtol and 'Q_ASSIST_SPEED' in P:
            qa = P['Q_ASSIST_SPEED']
            C.add('qassist', 'lim', 'warn' if qa <= 0 else 'pass', None, v=_f(qa))
    if mc:
        if 'MOT_SPIN_MIN' in P:
            a, m = P.get('MOT_SPIN_ARM', 0.1), P['MOT_SPIN_MIN']
            bad = a >= m or m < 0.05 or m > 0.3
            C.add('spin', 'lim', 'warn' if bad else 'pass', None, a=_f(a), m=_f(m))
        if 'MOT_THST_HOVER' in P:
            h = P['MOT_THST_HOVER']
            st = 'warn' if h > 0.5 or h < 0.15 else 'pass'
            C.add('hover', 'lim', st, None, v=_f(h), x=s('hover_hi' if h > 0.5 else 'hover_lo', lg))
        if 'ANGLE_MAX' in P:
            am = P['ANGLE_MAX'] / 100.0
            C.add('angle', 'lim', 'warn' if am > 45 else 'pass', [('ANGLE_MAX', 3500)] if am > 45 else None, v=_f(am))
        if 'INS_HNTCH_ENABLE' in P and v == C_:
            C.add('notch', 'lim', 'warn' if not P['INS_HNTCH_ENABLE'] else 'pass')
    if v == H_ and 'H_RSC_MODE' in P:
        C.add('rsc', 'lim', 'fail' if P['H_RSC_MODE'] == 0 else 'pass', None, v=_f(P['H_RSC_MODE']))
    # ------------------------------------------------ çıkışlar
    fun = {P[k] for k in P if k.startswith('SERVO') and k.endswith('_FUNCTION')}
    if fun:
        need = []
        if v == P_:
            if 70 not in fun and not vtol and not P.get('Q_TAILSIT_ENABLE'): need.append(('throttle', 'SERVOx_FUNCTION=70'))
            has_roll = bool(fun & {4, 77, 78}); has_pitch = bool(fun & {19, 77, 78, 79, 80})
            if not has_roll and not (fun & {79, 80}): need.append(('aileron/elevon', '4 / 77,78'))
            if not has_pitch: need.append(('elevator/V-tail', '19 / 79,80'))
        elif v == C_:
            frm = int(P.get('FRAME_CLASS', 1) or 1); n_m = {1: 4, 2: 6, 3: 8, 4: 3, 5: 6, 7: 3, 10: 1, 12: 4, 14: 4, 15: 4}.get(frm, 4)
            got = len(fun & set(range(33, 41)) | fun & set(range(82, 86)))
            if got < n_m: need.append((f'motor ({got}/{n_m})', '33…40'))
        names = {70: 'throttle', 4: 'aileron', 19: 'elevator', 21: 'rudder', 77: 'elevon', 78: 'elevon', 79: 'V-tail', 80: 'V-tail'}
        okx = ', '.join(sorted({names[f] for f in fun if f in names})) or ', '.join(f'motor{int(f) - 32}' for f in sorted(fun) if 33 <= f <= 40)
        C.add('outputs', 'ctl', 'fail' if need else 'pass', None, x=', '.join(f'{a} ({b})' for a, b in need) if need else okx)
        bad = []
        for i in range(1, 17):
            f_ = P.get(f'SERVO{i}_FUNCTION', 0)
            if not f_: continue
            mn, tr, mx = P.get(f'SERVO{i}_MIN'), P.get(f'SERVO{i}_TRIM'), P.get(f'SERVO{i}_MAX')
            if None in (mn, tr, mx): continue
            if not (mn <= tr <= mx) or mn >= mx: bad.append(f'SERVO{i}')
        C.add('servo_rng', 'ctl', 'warn' if bad else 'pass', None, x=', '.join(bad))
    rc = [(P.get(f'RC{c}_MIN'), P.get(f'RC{c}_TRIM'), P.get(f'RC{c}_MAX')) for c in range(1, 5)]
    if all(None not in x for x in rc):
        bad = [(c + 1, x) for c, x in enumerate(rc) if not (800 <= x[0] < x[2] <= 2200) or not (x[0] <= x[1] <= x[2])]
        if bad:
            c, x = bad[0]
            C.add('rc_cal', 'ctl', 'fail', None, x=s('rc_bad', lg, c=c, mn=_f(x[0]), tr=_f(x[1]), mx=_f(x[2])))
        elif all(x[0] == 1100 and x[2] == 1900 for x in rc):
            C.add('rc_cal', 'ctl', 'warn', None, x=s('rc_def', lg))
        else:
            C.add('rc_cal', 'ctl', 'pass')
    fm = [P.get(f'FLTMODE{i}') for i in range(1, 7)] if v != R_ else [P.get(f'MODE{i}') for i in range(1, 7)]
    if any(x is not None for x in fm):
        rec = {P_: {11: 'RTL', 0: 'MANUAL', 2: 'STABILIZE', 5: 'FBWA', 21: 'QRTL', 17: 'QSTABILIZE', 19: 'QLOITER'},
               C_: {6: 'RTL', 0: 'STABILIZE', 2: 'ALT_HOLD', 9: 'LAND', 21: 'SMART_RTL'},
               H_: {6: 'RTL', 0: 'STABILIZE', 2: 'ALT_HOLD', 9: 'LAND'}, R_: {11: 'RTL', 0: 'MANUAL', 4: 'HOLD', 12: 'SMART_RTL'},
               S_: {19: 'MANUAL', 0: 'STABILIZE', 9: 'SURFACE'}}.get(v, {})
        have = sorted({rec[int(x)] for x in fm if x is not None and int(x) in rec})
        rtl_ok = any(h in ('RTL', 'QRTL', 'SMART_RTL', 'SURFACE') for h in have)
        C.add('modes', 'ctl', 'pass' if rtl_ok else 'warn', None, x=', '.join(have) or '-')
    # ------------------------------------------------ eve dönüş
    if mc and 'RTL_ALT' in P:
        ra = P['RTL_ALT']
        C.add('rtl', 'rtl', 'warn' if 0 < ra < 1500 else 'pass', [('RTL_ALT', 3000)] if 0 < ra < 1500 else None, p='RTL_ALT', v=_f(ra), u='cm', m=1500)
    elif v == P_:
        ra, rn = _g(P, 'RTL_ALTITUDE', 'ALT_HOLD_RTL')
        if ra is not None:
            u = 'm' if rn == 'RTL_ALTITUDE' else 'cm'; mn = 30 if u == 'm' else 3000
            low = 0 < ra < mn
            C.add('rtl', 'rtl', 'warn' if low else 'pass', [(rn, 60 if u == 'm' else 6000)] if low else None, p=rn, v=_f(ra), u=u, m=mn)
    # ------------------------------------------------ log
    if 'LOG_BITMASK' in P:
        lb = int(P['LOG_BITMASK'])
        if lb == 0:
            C.add('logbm', 'log', 'fail', [('LOG_BITMASK', 65535 if v == P_ else 180222)])
        else:
            pid_bit = ((lb & 0b11) and (lb & (1 << 11))) if v == P_ else (lb & (1 << 12))   # Plane: ATTITUDE (0/1) + TECS (11); Copter: PID (12)
            C.add('logbm', 'log', 'pass', v=lb, x=s('on' if pid_bit else 'off', lg))
    # ------------------------------------------------ tanım dışı değerler (Parametre Merkezi veritabanı)
    try:
        from . import pcenter as PC
        db = PC.PDB.get(); bad = []
        for k, val in P.items():
            m = db.meta(k, v)
            c = PC.check_value(val, m) if m else None
            if c in ('range', 'enum'):
                if val == 0 and re.search(r'(ACC|GYR)\d?(SCAL|OFFS)|OFS\d|_FF$|FLTE$|_DEV_ID', k): continue   # kullanılmayan sensör / kapalı özellik
                bad.append(f'{k}={_f(val)}')
        if bad:
            C.add('def_items', 'def', 'warn', None, n=len(bad), x=', '.join(bad[:12]) + (' …' if len(bad) > 12 else ''))
        elif P:
            C.add('def_items', 'def', 'pass')
    except Exception:
        pass
    items = C.items
    cnt = {k: sum(1 for i in items if i['st'] == k) for k in ('fail', 'warn', 'pass', 'na')}
    status = 'nogo' if cnt['fail'] else 'caution' if cnt['warn'] else 'go'
    order = {'fail': 0, 'warn': 1, 'pass': 2, 'na': 3}
    items.sort(key=lambda i: (order[i['st']], list(CATS).index(i['cat'])))
    return {'status': status, 'summary': s(status, lg), 'counts': cnt,
            'counts_t': s('counts', lg, f=cnt['fail'], w=cnt['warn'], p=cnt['pass'], n=cnt['na']),
            'title': s('title', lg), 'items': items, 'vehicle': v}


def apply_fixes(params, res, ids=None):
    """Önerilen düzeltmeleri (yalnız seçilen maddeler) parametre kopyasına uygular."""
    out = dict(params)
    for it in res['items']:
        if ids is not None and it['id'] not in ids: continue
        for k, val in it.get('fix') or []:
            out[k] = float(val)
    return out


def to_text(res):
    mark = {'fail': '⛔', 'warn': '⚠', 'pass': '✔', 'na': '–'}
    L = [res['title'], res['summary'], res['counts_t'], '']
    for it in res['items']:
        L.append(f"{mark[it['st']]} [{it['cat_t']}] {it['title']}: {it['text']}")
        for k, val in it.get('fix') or []:
            L.append(f'      → {k} = {_f(val)}')
    return '\n'.join(L) + '\n'
