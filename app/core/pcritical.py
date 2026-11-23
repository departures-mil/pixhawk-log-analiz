"""Bilinmesi gereken kritik parametreler (elle hazırlanmış, TR / EN / AR) ve ek risk kuralları.

Her kayıt: kategori, parametre, geçerli araçlar (None = hepsi), neden önemli olduğu.
Parametre Merkezi'nde 🔑 "hazır anahtar" olarak gösterilir; ders kitabında ayrı bölümdür.
"""
CATS = {
    'safety': ('Güvenlik ve failsafe', 'Safety and failsafe', 'السلامة ووضع الطوارئ'),
    'arming': ('Arm etme kontrolleri', 'Arming checks', 'فحوص التسليح'),
    'battery': ('Batarya ve güç', 'Battery and power', 'البطارية والطاقة'),
    'nav': ('GPS, EKF ve pusula', 'GPS, EKF and compass', 'GPS وEKF والبوصلة'),
    'limits': ('Uçuş sınırları ve hız', 'Flight limits and speed', 'حدود الطيران والسرعة'),
    'rtl': ('Eve dönüş ve iniş', 'Return and landing', 'العودة والهبوط'),
    'rc': ('Kumanda, modlar ve servolar', 'RC, modes and servos', 'التحكم والأوضاع والمؤازرات'),
    'tuning': ('Kontrol ayarı ve titreşim', 'Control tuning and vibration', 'ضبط التحكم والاهتزاز'),
    'log': ('Kayıt (log)', 'Logging', 'التسجيل'),
}
P, C, H, R, S = 'Plane', 'Copter', 'Heli', 'Rover', 'Sub'
MC = [C, H]

CRIT = [
    # ------------------------------------------------------------- güvenlik
    ('safety', 'FS_THR_ENABLE', [C, H, R, S], ('Kumanda (RC) kaybında ne yapılacağını seçer. 0 = kapalı: sinyal kesilince araç son komutla devam eder. Mutlaka RTL/Land seçin.',
     'Selects what happens on RC loss. 0 = disabled: the vehicle keeps the last command when the signal is lost. Always choose RTL/Land.',
     'يحدد ما يحدث عند فقدان إشارة التحكم. 0 = معطل: تستمر المركبة بآخر أمر. اختر دائماً RTL أو الهبوط.')),
    ('safety', 'FS_THR_VALUE', [C, H, R], ('Alıcı failsafe olduğunda gaz kanalının düştüğü PWM eşiği. Alıcının failsafe değerinden yüksek, normal en düşük gazdan düşük olmalı.',
     'PWM threshold of the throttle channel that means receiver failsafe. Must be above the receiver failsafe value and below normal minimum throttle.',
     'عتبة PWM لقناة الخانق التي تعني طوارئ المستقبل. يجب أن تكون أعلى من قيمة طوارئ المستقبل وأقل من أدنى خانق عادي.')),
    ('safety', 'THR_FAILSAFE', [P], ('Uçakta radyo failsafe anahtarı. 0 yapılırsa kumanda kaybı algılanmaz.',
     'Radio failsafe switch on Plane. If 0, RC loss is not detected.', 'مفتاح طوارئ الراديو في الطائرة. إذا كان 0 لا يُكتشف فقدان التحكم.')),
    ('safety', 'THR_FS_VALUE', [P], ('Uçakta failsafe sayılan gaz PWM eşiği.', 'Throttle PWM threshold treated as failsafe on Plane.', 'عتبة PWM للخانق التي تُعد طوارئ في الطائرة.')),
    ('safety', 'FS_SHORT_ACTN', [P], ('Kısa süreli (1,5 sn) sinyal kaybında eylem (ör. daire çizme).', 'Action on short (1.5 s) signal loss (e.g. circle).', 'الإجراء عند فقدان قصير للإشارة (1.5 ث) مثل الدوران.')),
    ('safety', 'FS_LONG_ACTN', [P], ('Uzun sinyal kaybında eylem. 0 iken AUTO modunda görev sürer; genelde RTL seçilir.',
     'Action on long signal loss. With 0 the mission continues in AUTO; usually RTL is chosen.', 'الإجراء عند فقدان طويل للإشارة. مع 0 تستمر المهمة في AUTO؛ عادة يُختار RTL.')),
    ('safety', 'FS_LONG_TIMEOUT', [P], ('Uzun failsafe’in başlayacağı süre (sn).', 'Time before long failsafe starts (s).', 'الوقت قبل بدء الطوارئ الطويلة (ث).')),
    ('safety', 'FS_GCS_ENABL', [P, R], ('Yer kontrol istasyonu (telemetri) bağlantısı kesilince failsafe.', 'Failsafe on loss of ground station telemetry.', 'طوارئ عند فقدان اتصال المحطة الأرضية.')),
    ('safety', 'FS_GCS_ENABLE', [C, H, S], ('Telemetri/YKİ bağlantı kaybında eylem.', 'Action on ground station link loss.', 'الإجراء عند فقدان اتصال المحطة الأرضية.')),
    ('safety', 'FS_EKF_ACTION', [C, H], ('EKF (konum tahmini) bozulduğunda eylem. 0 = yok, tehlikeli.', 'Action when the EKF (position estimate) goes bad. 0 = none, dangerous.', 'الإجراء عند فساد تقدير الموقع EKF. 0 = لا شيء، وهو خطر.')),
    ('safety', 'FS_EKF_THRESH', [C, H], ('EKF failsafe eşiği; düşük değer daha hassas.', 'EKF failsafe threshold; lower is more sensitive.', 'عتبة طوارئ EKF؛ القيمة الأقل أكثر حساسية.')),
    ('safety', 'FS_CRASH_CHECK', [C, H], ('Kırım algılanınca motorları durdurur.', 'Disarms motors when a crash is detected.', 'يوقف المحركات عند اكتشاف التحطم.')),
    ('safety', 'CRASH_DETECT', [P], ('Uçakta kırım algılama ve motoru kesme.', 'Crash detection and motor cut on Plane.', 'اكتشاف التحطم وإيقاف المحرك في الطائرة.')),
    ('safety', 'FENCE_ENABLE', None, ('Coğrafi sınırı (geofence) açar. Kaçan aracı geri getirmek için önemlidir.', 'Enables the geofence. Important to bring back a fly-away vehicle.', 'يفعّل السياج الجغرافي. مهم لإعادة المركبة الهاربة.')),
    ('safety', 'FENCE_ACTION', None, ('Sınır aşıldığında yapılacak eylem (RTL, Land…).', 'Action when the fence is breached (RTL, Land…).', 'الإجراء عند خرق السياج (RTL، هبوط…).')),
    ('safety', 'FENCE_ALT_MAX', None, ('Azami irtifa sınırı (m).', 'Maximum altitude limit (m).', 'حد الارتفاع الأقصى (م).')),
    ('safety', 'FENCE_RADIUS', None, ('Eve göre azami yatay uzaklık (m).', 'Maximum horizontal distance from home (m).', 'أقصى مسافة أفقية من نقطة الإقلاع (م).')),
    # ------------------------------------------------------------- arm
    ('arming', 'ARMING_CHECK', None, ('Arm öncesi kontroller. 1 = hepsi açık (önerilen). 0 tüm güvenlik kontrollerini kapatır.',
     'Pre-arm checks. 1 = all enabled (recommended). 0 disables all safety checks.', 'فحوص ما قبل التسليح. 1 = جميعها (موصى به). 0 يعطل جميع فحوص السلامة.')),
    ('arming', 'ARMING_SKIPCHK', None, ('Yeni sürümlerde atlanacak kontrollerin bitmaskesi. 0 dışı her değer bazı kontrolleri kapatır.',
     'Bitmask of checks to skip in newer firmware. Any non-zero value disables some checks.', 'قناع بتات للفحوص المتخطاة في الإصدارات الحديثة. أي قيمة غير الصفر تعطل بعض الفحوص.')),
    ('arming', 'ARMING_REQUIRE', [P, R], ('Arm gerekli mi? 0 ise araç açılır açılmaz motor çalışabilir.', 'Is arming required? With 0 the motor may run right after power-up.', 'هل التسليح مطلوب؟ مع 0 قد يعمل المحرك فور التشغيل.')),
    ('arming', 'BRD_SAFETY_DEFLT', None, ('Güvenlik düğmesinin açılıştaki durumu.', 'Safety switch state at boot.', 'حالة مفتاح الأمان عند الإقلاع.')),
    # ------------------------------------------------------------- batarya
    ('battery', 'BATT_MONITOR', None, ('Batarya ölçüm türü. 0 = izlenmiyor; 3 = yalnız gerilim; 4 = gerilim + akım (önerilen).',
     'Battery monitor type. 0 = none; 3 = voltage only; 4 = voltage and current (recommended).', 'نوع مراقبة البطارية. 0 = لا شيء؛ 3 = الجهد فقط؛ 4 = الجهد والتيار (موصى به).')),
    ('battery', 'BATT_CAPACITY', None, ('Batarya kapasitesi (mAh). Kalan yüzde ve mAh failsafe bununla hesaplanır.', 'Battery capacity (mAh). Remaining % and mAh failsafe use it.', 'سعة البطارية (mAh). تُحسب النسبة المتبقية وطوارئ mAh بها.')),
    ('battery', 'BATT_LOW_VOLT', None, ('Düşük batarya gerilimi eşiği (hücre başına ~3,5 V × hücre sayısı).', 'Low battery voltage threshold (~3.5 V × cell count).', 'عتبة الجهد المنخفض للبطارية (~3.5 فولت × عدد الخلايا).')),
    ('battery', 'BATT_CRT_VOLT', None, ('Kritik batarya gerilimi (hücre başına ~3,3 V).', 'Critical battery voltage (~3.3 V per cell).', 'الجهد الحرج للبطارية (~3.3 فولت لكل خلية).')),
    ('battery', 'BATT_FS_LOW_ACT', None, ('Düşük bataryada eylem (RTL, Land). 0 = yalnız uyarı.', 'Action on low battery (RTL, Land). 0 = warning only.', 'الإجراء عند انخفاض البطارية (RTL، هبوط). 0 = تحذير فقط.')),
    ('battery', 'BATT_FS_CRT_ACT', None, ('Kritik bataryada eylem; genelde Land.', 'Action on critical battery; usually Land.', 'الإجراء عند البطارية الحرجة؛ عادة الهبوط.')),
    ('battery', 'BATT_LOW_MAH', None, ('Kalan mAh bu değerin altına inince düşük batarya.', 'Low battery when remaining mAh drops below this.', 'بطارية منخفضة عند نزول السعة المتبقية تحت هذه القيمة.')),
    ('battery', 'BATT_AMP_PERVLT', None, ('Akım sensörü kalibrasyonu; yanlışsa mAh hesabı yanlış olur.', 'Current sensor calibration; if wrong, mAh is wrong.', 'معايرة حساس التيار؛ إن كانت خاطئة يكون حساب mAh خاطئاً.')),
    ('battery', 'BATT_VOLT_MULT', None, ('Gerilim ölçüm çarpanı; multimetreyle doğrulayın.', 'Voltage multiplier; verify with a multimeter.', 'معامل ضرب الجهد؛ تحقق بجهاز القياس.')),
    ('battery', 'MOT_BAT_VOLT_MAX', MC, ('Gerilim düştükçe kazancı dengeleyen azami gerilim (hücre × 4,2 V).', 'Max voltage for thrust compensation (cells × 4.2 V).', 'الجهد الأقصى لتعويض الدفع (الخلايا × 4.2 فولت).')),
    ('battery', 'MOT_BAT_VOLT_MIN', MC, ('Dengeleme için asgari gerilim (hücre × 3,3 V).', 'Min voltage for compensation (cells × 3.3 V).', 'الجهد الأدنى للتعويض (الخلايا × 3.3 فولت).')),
    # ------------------------------------------------------------- konum
    ('nav', 'GPS_TYPE', None, ('GPS alıcı türü. 0 = GPS kapalı; 1 = otomatik.', 'GPS receiver type. 0 = disabled; 1 = auto.', 'نوع مستقبل GPS. 0 = معطل؛ 1 = تلقائي.')),
    ('nav', 'GPS_AUTO_SWITCH', None, ('İki GPS varsa aralarında geçiş/harmanlama.', 'Switching/blending between two GPS units.', 'التبديل/المزج بين جهازي GPS.')),
    ('nav', 'AHRS_EKF_TYPE', None, ('Kullanılan EKF sürümü; 3 (EKF3) önerilir.', 'EKF version used; 3 (EKF3) recommended.', 'إصدار EKF المستخدم؛ يُوصى بـ 3 (EKF3).')),
    ('nav', 'EK3_SRC1_POSXY', None, ('EKF3 yatay konum kaynağı (GPS, beacon, görsel odometri).', 'EKF3 horizontal position source.', 'مصدر الموقع الأفقي في EKF3.')),
    ('nav', 'EK3_SRC1_YAW', None, ('Yön (yaw) kaynağı: pusula, GPS, GSF…', 'Yaw source: compass, GPS, GSF…', 'مصدر الاتجاه: البوصلة، GPS، GSF…')),
    ('nav', 'COMPASS_USE', None, ('Birinci pusulanın kullanılması. Pusulasız uçuş için özel ayar gerekir.', 'Use of the first compass. Compass-less flight needs special setup.', 'استخدام البوصلة الأولى. الطيران دون بوصلة يحتاج إعداداً خاصاً.')),
    ('nav', 'COMPASS_ORIENT', None, ('Harici pusulanın montaj yönü. Yanlışsa araç daire çizer (toilet bowl).', 'External compass orientation. If wrong the vehicle circles (toilet bowl).', 'اتجاه تركيب البوصلة الخارجية. إن كان خاطئاً تدور المركبة.')),
    ('nav', 'AHRS_ORIENTATION', None, ('Uçuş kartının araca montaj yönü.', 'Flight controller mounting orientation.', 'اتجاه تركيب لوحة التحكم.')),
    ('nav', 'COMPASS_LEARN', None, ('Pusula sapmalarını uçuşta öğrenme.', 'In-flight compass offset learning.', 'تعلّم انحرافات البوصلة أثناء الطيران.')),
    # ------------------------------------------------------------- sınırlar
    ('limits', 'ANGLE_MAX', MC, ('Azami eğim açısı (santiderece). Büyük değer agresif uçuş demektir.', 'Maximum lean angle (centidegrees). Large values mean aggressive flight.', 'زاوية الميل القصوى (سنتي درجة). القيمة الكبيرة تعني طيراناً عنيفاً.')),
    ('limits', 'WPNAV_SPEED', MC, ('Görevde yatay hız (cm/sn).', 'Horizontal speed in missions (cm/s).', 'السرعة الأفقية في المهمات (سم/ث).')),
    ('limits', 'WPNAV_SPD', MC, ('Görevde yatay hız (m/sn, yeni sürüm).', 'Horizontal mission speed (m/s, newer firmware).', 'السرعة الأفقية في المهمة (م/ث، إصدار أحدث).')),
    ('limits', 'PILOT_SPEED_UP', MC, ('Pilotun azami tırmanma hızı.', 'Pilot maximum climb rate.', 'أقصى معدل صعود للطيار.')),
    ('limits', 'AIRSPEED_MIN', [P], ('Asgari hava hızı. Stall hızının en az %20 üstünde olmalı.', 'Minimum airspeed. Must be at least 20% above stall speed.', 'أدنى سرعة جوية. يجب أن تكون أعلى من سرعة الانهيار بـ 20% على الأقل.')),
    ('limits', 'AIRSPEED_MAX', [P], ('Azami hava hızı.', 'Maximum airspeed.', 'أقصى سرعة جوية.')),
    ('limits', 'AIRSPEED_CRUISE', [P], ('Seyir hava hızı.', 'Cruise airspeed.', 'سرعة التجوال الجوية.')),
    ('limits', 'ARSPD_TYPE', [P], ('Hava hızı sensörü türü. 0 = yok: hız tahmini GPS ve gazdan yapılır.', 'Airspeed sensor type. 0 = none: speed is estimated from GPS and throttle.', 'نوع حساس السرعة الجوية. 0 = لا يوجد: تُقدَّر السرعة من GPS والخانق.')),
    ('limits', 'ARSPD_USE', [P], ('Hava hızı sensörünün kontrol için kullanılması.', 'Use of airspeed sensor for control.', 'استخدام حساس السرعة الجوية في التحكم.')),
    ('limits', 'STALL_PREVENTION', [P], ('Düşük hızda yatışı sınırlayarak stall’u önler.', 'Prevents stall by limiting bank at low speed.', 'يمنع الانهيار بتحديد الميل عند السرعة المنخفضة.')),
    ('limits', 'ROLL_LIMIT_DEG', [P], ('Azami yatış açısı (derece).', 'Maximum bank angle (deg).', 'أقصى زاوية ميل جانبي (درجة).')),
    ('limits', 'LIM_ROLL_CD', [P], ('Azami yatış açısı (eski, santiderece).', 'Maximum bank angle (old, centidegrees).', 'أقصى زاوية ميل جانبي (قديم، سنتي درجة).')),
    ('limits', 'PTCH_LIM_MAX_DEG', [P], ('Azami burun yukarı açısı.', 'Maximum pitch up angle.', 'أقصى زاوية رفع المقدمة.')),
    ('limits', 'THR_MAX', [P], ('Azami gaz yüzdesi.', 'Maximum throttle percentage.', 'النسبة القصوى للخانق.')),
    ('limits', 'TECS_SINK_MAX', [P], ('Azami alçalma hızı (m/sn).', 'Maximum sink rate (m/s).', 'أقصى معدل هبوط (م/ث).')),
    ('limits', 'CRUISE_SPEED', [R], ('Rover seyir hızı (m/sn).', 'Rover cruise speed (m/s).', 'سرعة تجوال المركبة الأرضية (م/ث).')),
    # ------------------------------------------------------------- rtl / iniş
    ('rtl', 'RTL_ALT', MC, ('Eve dönüş irtifası (cm). Engellerin üstünde olmalı.', 'Return altitude (cm). Must clear obstacles.', 'ارتفاع العودة (سم). يجب أن يتجاوز العوائق.')),
    ('rtl', 'RTL_ALTITUDE', [P], ('Uçağın eve dönüş irtifası (m).', 'Plane return altitude (m).', 'ارتفاع عودة الطائرة (م).')),
    ('rtl', 'RTL_AUTOLAND', [P], ('Eve dönünce otomatik iniş yapılsın mı?', 'Land automatically after RTL?', 'هل تهبط تلقائياً بعد العودة؟')),
    ('rtl', 'LAND_SPEED', MC, ('Son alçalma hızı (cm/sn).', 'Final descent speed (cm/s).', 'سرعة الهبوط النهائي (سم/ث).')),
    ('rtl', 'LAND_FLARE_ALT', [P], ('İnişte burun kaldırma (flare) irtifası.', 'Flare altitude on landing.', 'ارتفاع رفع المقدمة عند الهبوط.')),
    ('rtl', 'TKOFF_ALT', None, ('Otomatik kalkış irtifası.', 'Automatic takeoff altitude.', 'ارتفاع الإقلاع الآلي.')),
    ('rtl', 'Q_RTL_MODE', [P], ('QuadPlane eve dönüşte dikey iniş davranışı.', 'QuadPlane VTOL landing behaviour on RTL.', 'سلوك الهبوط العمودي لـ QuadPlane عند العودة.')),
    # ------------------------------------------------------------- rc / mod
    ('rc', 'FLTMODE_CH', [P, R], ('Uçuş modlarını seçen kanal.', 'Channel that selects flight modes.', 'القناة التي تختار أوضاع الطيران.')),
    ('rc', 'FLTMODE1', None, ('Mod anahtarı 1. konumdaki uçuş modu.', 'Flight mode for switch position 1.', 'وضع الطيران لموضع المفتاح 1.')),
    ('rc', 'RCMAP_THROTTLE', None, ('Gaz hangi kanalda?', 'Which channel is throttle?', 'ما قناة الخانق؟')),
    ('rc', 'SERVO1_FUNCTION', None, ('1. çıkışın görevi (aileron, motor…). Yanlış eşleme kırım sebebidir.', 'Function of output 1 (aileron, motor…). Wrong mapping causes crashes.', 'وظيفة المخرج 1 (جنيح، محرك…). الربط الخاطئ يسبب التحطم.')),
    ('rc', 'SERVO1_REVERSED', None, ('Çıkış yönünü ters çevirir; ters yüzey kırıma yol açar.', 'Reverses output direction; a reversed surface leads to crashes.', 'يعكس اتجاه المخرج؛ السطح المعكوس يسبب التحطم.')),
    ('rc', 'RC_OPTIONS', None, ('Kumanda seçenekleri (bitmask).', 'RC options (bitmask).', 'خيارات التحكم (قناع بتات).')),
    ('rc', 'MOT_SPIN_ARM', MC, ('Arm edilince motorların döndüğü gaz.', 'Throttle at which motors spin when armed.', 'الخانق الذي تدور عنده المحركات عند التسليح.')),
    ('rc', 'MOT_SPIN_MIN', MC, ('Uçuşta asgari motor gazı; çok düşükse motor durabilir.', 'Minimum motor throttle in flight; too low may stall motors.', 'أدنى خانق للمحرك أثناء الطيران؛ القيمة المنخفضة جداً قد توقف المحرك.')),
    ('rc', 'MOT_THST_HOVER', MC, ('Askıda kalma gazı (öğrenilir). 0,5 üstü araç ağır demektir.', 'Hover throttle (learned). Above 0.5 means a heavy vehicle.', 'خانق التحويم (يُتعلّم). أعلى من 0.5 يعني مركبة ثقيلة.')),
    ('rc', 'FRAME_CLASS', MC, ('Çerçeve sınıfı (quad, hexa…).', 'Frame class (quad, hexa…).', 'فئة الهيكل (رباعي، سداسي…).')),
    ('rc', 'Q_ENABLE', [P], ('QuadPlane (VTOL) özelliklerini açar.', 'Enables QuadPlane (VTOL) features.', 'يفعّل ميزات QuadPlane (العمودي).')),
    # ------------------------------------------------------------- ayar
    ('tuning', 'INS_HNTCH_ENABLE', None, ('Harmonik çentik filtresi: motor titreşimini süzer.', 'Harmonic notch filter: removes motor vibration.', 'مرشح الشق التوافقي: يزيل اهتزاز المحركات.')),
    ('tuning', 'INS_GYRO_FILTER', None, ('Jiroskop alçak geçiren filtresi (Hz).', 'Gyro low-pass filter (Hz).', 'مرشح الجيروسكوب منخفض التمرير (هرتز).')),
    ('tuning', 'ATC_RAT_RLL_P', MC, ('Yatış hız döngüsü P kazancı. Yüksekse salınım, düşükse gevşeklik.', 'Roll rate P gain. Too high oscillates, too low feels sloppy.', 'كسب P لمعدل الدوران. المرتفع يسبب تذبذباً والمنخفض رخاوة.')),
    ('tuning', 'ATC_RAT_PIT_P', MC, ('Yunuslama hız döngüsü P kazancı.', 'Pitch rate P gain.', 'كسب P لمعدل الميلان.')),
    ('tuning', 'RLL_RATE_P', [P], ('Uçakta yatış hız P kazancı.', 'Plane roll rate P gain.', 'كسب P لمعدل الدوران في الطائرة.')),
    ('tuning', 'PTCH_RATE_P', [P], ('Uçakta yunuslama hız P kazancı.', 'Plane pitch rate P gain.', 'كسب P لمعدل الميلان في الطائرة.')),
    ('tuning', 'AUTOTUNE_LEVEL', [P], ('Otomatik ayarın sertliği.', 'Autotune aggressiveness.', 'شدة الضبط الآلي.')),
    ('tuning', 'AUTOTUNE_AGGR', MC, ('Copter otomatik ayar sertliği.', 'Copter autotune aggressiveness.', 'شدة الضبط الآلي في المروحيات المتعددة.')),
    ('tuning', 'SCHED_LOOP_RATE', None, ('Ana döngü hızı (Hz).', 'Main loop rate (Hz).', 'معدل الحلقة الرئيسية (هرتز).')),
    # ------------------------------------------------------------- log
    ('log', 'LOG_BITMASK', None, ('Hangi verilerin kaydedileceği. 0 = log yok: kaza sonrası analiz yapılamaz.', 'What is logged. 0 = no logs: no post-crash analysis.', 'ما يتم تسجيله. 0 = لا سجلات: لا تحليل بعد التحطم.')),
    ('log', 'LOG_DISARMED', None, ('Arm edilmeden de kayıt al (arm sorunlarını incelemek için).', 'Log while disarmed (to study arming problems).', 'التسجيل دون تسليح (لدراسة مشاكل التسليح).')),
    ('log', 'LOG_FILE_DSRMROT', None, ('Her disarm’da yeni log dosyası.', 'New log file on every disarm.', 'ملف سجل جديد عند كل نزع تسليح.')),
]


def _nz(v, P): return v == 0


RULES = [
    {'p': 'FENCE_ENABLE', 'v': None, 'sev': 0, 'test': _nz,
     'msg': ('FENCE_ENABLE = 0: Coğrafi sınır kapalı; kontrolden çıkan araç sınırlanmaz (bilgi).', 'FENCE_ENABLE = 0: geofence disabled; a runaway vehicle is not contained (info).', 'FENCE_ENABLE = 0: السياج الجغرافي معطل؛ لا تُحصر المركبة الهاربة (معلومة).')},
    {'p': 'FS_CRASH_CHECK', 'v': MC, 'sev': 1, 'test': _nz,
     'msg': ('FS_CRASH_CHECK = 0: Kırımda motorlar otomatik durmaz.', 'FS_CRASH_CHECK = 0: motors are not stopped after a crash.', 'FS_CRASH_CHECK = 0: لا تتوقف المحركات بعد التحطم.')},
    {'p': 'BATT_FS_CRT_ACT', 'v': None, 'sev': 1, 'test': lambda v, P: v == 0 and P.get('BATT_MONITOR', 0) != 0,
     'msg': ('BATT_FS_CRT_ACT = 0: Kritik bataryada bile eylem yok.', 'BATT_FS_CRT_ACT = 0: no action even at critical battery.', 'BATT_FS_CRT_ACT = 0: لا إجراء حتى عند البطارية الحرجة.')},
    {'p': 'ANGLE_MAX', 'v': MC, 'sev': 1, 'test': lambda v, P: v > 5500,
     'msg': ('ANGLE_MAX = {v}: 55°’den büyük eğim; irtifa kaybı ve kontrol zorluğu riski.', 'ANGLE_MAX = {v}: lean above 55°; risk of altitude loss and control difficulty.', 'ANGLE_MAX = {v}: ميل أكبر من 55°؛ خطر فقدان الارتفاع وصعوبة التحكم.')},
    {'p': 'RTL_ALT', 'v': MC, 'sev': 1, 'test': lambda v, P: 0 < v < 1500,
     'msg': ('RTL_ALT = {v} cm: 15 m’den alçak eve dönüş; ağaç/bina riski.', 'RTL_ALT = {v} cm: return below 15 m; risk of trees/buildings.', 'RTL_ALT = {v} سم: عودة تحت 15 م؛ خطر الأشجار/المباني.')},
    {'p': 'RTL_ALTITUDE', 'v': [P], 'sev': 1, 'test': lambda v, P: 0 < v < 30,
     'msg': ('RTL_ALTITUDE = {v} m: Uçak için çok alçak eve dönüş irtifası.', 'RTL_ALTITUDE = {v} m: very low return altitude for a plane.', 'RTL_ALTITUDE = {v} م: ارتفاع عودة منخفض جداً للطائرة.')},
    {'p': 'MOT_SPIN_MIN', 'v': MC, 'sev': 1, 'test': lambda v, P: v < 0.08,
     'msg': ('MOT_SPIN_MIN = {v}: Çok düşük; hızlı alçalmada motor durabilir (senkron kaybı).', 'MOT_SPIN_MIN = {v}: very low; motors may stop in fast descents (desync).', 'MOT_SPIN_MIN = {v}: منخفض جداً؛ قد تتوقف المحركات عند النزول السريع.')},
    {'p': 'LOG_DISARMED', 'v': None, 'sev': 0, 'test': lambda v, P: v == 1,
     'msg': ('LOG_DISARMED = 1: Yerde de kayıt alınıyor; SD kart hızla dolar (bilgi).', 'LOG_DISARMED = 1: logging on the ground too; the SD card fills quickly (info).', 'LOG_DISARMED = 1: يتم التسجيل على الأرض أيضاً؛ تمتلئ البطاقة بسرعة (معلومة).')},
    {'p': 'BRD_SAFETY_DEFLT', 'v': None, 'sev': 0, 'test': _nz,
     'msg': ('BRD_SAFETY_DEFLT = 0: Güvenlik düğmesi devre dışı (bilgi).', 'BRD_SAFETY_DEFLT = 0: safety switch disabled (info).', 'BRD_SAFETY_DEFLT = 0: مفتاح الأمان معطل (معلومة).')},
    {'p': 'ARMING_REQUIRE', 'v': [P, R], 'sev': 2, 'test': _nz,
     'msg': ('ARMING_REQUIRE = 0: Arm gerekmiyor; motor beklenmedik anda çalışabilir.', 'ARMING_REQUIRE = 0: arming not required; motor may start unexpectedly.', 'ARMING_REQUIRE = 0: التسليح غير مطلوب؛ قد يعمل المحرك فجأة.')},
    {'p': 'FS_GCS_ENABLE', 'v': [S], 'sev': 1, 'test': _nz,
     'msg': ('FS_GCS_ENABLE = 0: Sualtı aracında bağlantı kaybında eylem yok.', 'FS_GCS_ENABLE = 0: no action on tether/link loss for Sub.', 'FS_GCS_ENABLE = 0: لا إجراء عند فقدان الاتصال في المركبة تحت الماء.')},
    {'p': 'TECS_SINK_MAX', 'v': [P], 'sev': 0, 'test': lambda v, P: v > 10,
     'msg': ('TECS_SINK_MAX = {v}: Çok yüksek alçalma hızı izni (bilgi).', 'TECS_SINK_MAX = {v}: very high sink rate allowed (info).', 'TECS_SINK_MAX = {v}: معدل هبوط مرتفع جداً مسموح (معلومة).')},
]


def critical(vehicle=None):
    return [(c, p, why) for c, p, v, why in CRIT if v is None or vehicle is None or vehicle in v]


def why(name, lang='tr'):
    i = {'tr': 0, 'en': 1, 'ar': 2}.get(lang, 0)
    for c, p, v, w in CRIT:
        if p == name: return c, w[i]
    return None, None
