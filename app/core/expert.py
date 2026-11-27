"""Uzman tecrübeleri: ArduPilot forumunda (discuss.ardupilot.org) gerçek kırım loglarını inceleyen deneyimli üyelerin ve geliştirici
ekibinin yüzlerce konuda tekrar tekrar verdiği teşhis ve öğütlerin özeti (kendi sözlerimizle, alıntı değil).

Her ders: hangi kök nedenle ilgili olduğu, uzmanların kuralı, logda nereye bakılacağı (grafik + alanlar), çözüm ve ilgili parametreler.
Gerçek konuların hangi derslere değindiği app/data/expert_cases.json'da (tools_data/expert_tags.py üretir). Offline çalışır."""
import json, os

_D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
LI = {'tr': 0, 'en': 1, 'ar': 2}

# code: cause, chart, icon, title, rule, look, fix, params
L = {
 'thrust_loss': dict(cause='motor', chart='c_motors', icon='🌀', params=['MOT_PWM_MAX', 'MOT_SPIN_MAX'],
  title=('İtki kaybı: bir motor tepeye, karşısı dibe', 'Thrust loss: one motor at max, its opposite at min',
         'فقدان الدفع: محرك عند الأقصى والمقابل له عند الأدنى'),
  rule=('Uzmanların ilk baktığı imza: bir motor çıkışı aniden en üste (≈1900–2000) çıkarken çaprazındaki motor en alta iner ve araç o motor '
        'tarafına yatar. Otopilot o köşeyi kurtarmaya çalışıyor ama motor/ESC/pervane itki vermiyor demektir; bu bir ayar sorunu değildir.',
        'The first signature experts look for: one motor output suddenly jumps to the top (≈1900–2000) while the diagonal motor drops to the '
        'bottom and the aircraft rolls toward that motor. The autopilot is trying to save that corner but the motor/ESC/prop is not producing '
        'thrust; this is not a tuning problem.',
        'أول ما يبحث عنه الخبراء: خرج أحد المحركات يقفز فجأة إلى الأعلى (≈1900–2000) بينما ينخفض المحرك المقابل قطرياً إلى الأدنى وتميل '
        'الطائرة نحو ذلك المحرك. هذا يعني أن الطيار الآلي يحاول إنقاذ تلك الزاوية لكن المحرك/ESC/المروحة لا يعطي دفعاً؛ وليست مشكلة ضبط.'),
  look=('RCOU C1…C8 (motor çıkışları) ve ATT Roll/DesRoll: ayrılma anında hangi motor tepeye vurdu? Önce o çıkış doydu mu, yoksa açı mı bozuldu?',
        'RCOU C1…C8 (motor outputs) and ATT Roll/DesRoll: at the moment of divergence, which motor hit the top? Did the output saturate first, or the attitude?',
        'RCOU C1…C8 (مخارج المحركات) وATT Roll/DesRoll: عند لحظة الانحراف أي محرك وصل إلى الأعلى؟ هل تشبّع الخرج أولاً أم اختلّ الوضع أولاً؟'),
  fix=('O koldaki motoru, ESC\'yi, lehimleri, konnektörleri ve pervaneyi değiştirin/kontrol edin; motoru elle çevirip sürtünme ve sargı kokusu arayın.',
       'Replace/inspect that arm\'s motor, ESC, solder joints, connectors and prop; turn the motor by hand and check for grinding or burnt windings.',
       'افحص أو استبدل محرك ذلك الذراع وESC واللحامات والموصلات والمروحة؛ أدر المحرك باليد وابحث عن احتكاك أو رائحة احتراق في الملفات.')),
 'yaw_bias': dict(cause='motor', chart='c_motors', icon='↻', params=['ATC_RAT_YAW_P', 'MOT_YAW_HEADROOM'],
  title=('Sürekli yaw dengesizliği: çapraz motor çiftleri ayrışıyor', 'Constant yaw imbalance: diagonal motor pairs split apart',
         'عدم توازن الانعراج المستمر: أزواج المحركات القطرية تتباعد'),
  rule=('Havada asılıyken saat yönünde dönen motor çifti, ters yönde dönen çiftten sürekli belirgin farklıysa çerçeve kolları burkulmuş ya da motorlar '
        'eğik takılmıştır. Otopilot bu farkı kapatmak için motor payını harcar; ilk sert manevrada bir motor doyar ve araç düşer.',
        'If the clockwise motor pair is constantly and clearly different from the counter-clockwise pair in hover, the arms are twisted or the motors '
        'are mounted at an angle. The autopilot spends motor headroom to cancel this; on the first hard manoeuvre one motor saturates and it falls.',
        'إذا كان زوج المحركات الدائر مع عقارب الساعة يختلف باستمرار عن الزوج المعاكس أثناء التحويم فإن الأذرع ملتوية أو المحركات مركّبة بزاوية. '
        'يستهلك الطيار الآلي هامش المحركات لتعويض ذلك؛ وعند أول مناورة حادة يتشبّع محرك وتسقط الطائرة.'),
  look=('RCOU: askıda C1+C2 ile C3+C4 (quad) ortalamalarını karşılaştırın; 100 µs\'den büyük kalıcı fark uyarıdır. ATT DesYaw–Yaw ve RATE YOut de bakılır.',
        'RCOU: compare C1+C2 against C3+C4 averages (quad) in hover; a steady gap over 100 µs is a warning. Also check ATT DesYaw–Yaw and RATE YOut.',
        'RCOU: قارن متوسط C1+C2 مع C3+C4 (رباعي) أثناء التحويم؛ فرق ثابت أكبر من 100 ميكروثانية تحذير. افحص أيضاً ATT DesYaw–Yaw وRATE YOut.'),
  fix=('Kolları düzeltin, motorları aynı düzlemde dik takın; gerekirse motorları 1–2° yaw yönüne eğerek yardımcı olun. Pervane yönlerini doğrulayın.',
       'Straighten the arms and mount motors square on the same plane; if needed tilt motors 1–2° in the yaw direction to help. Verify prop directions.',
       'قوّم الأذرع وثبّت المحركات عمودية في مستوى واحد؛ وعند الحاجة أمِل المحركات 1–2° باتجاه الانعراج للمساعدة. تحقق من اتجاه المراوح.')),
 'esc_issue': dict(cause='motor', chart='c_esc', icon='⚡', params=['MOT_PWM_TYPE', 'SERVO_BLH_AUTO'],
  title=('ESC senkron kaybı ya da arıza', 'ESC desync or failure', 'فقدان تزامن ESC أو عطله'),
  rule=('Motor çıkışı yükselirken (otopilot daha çok gaz istiyor) aynı motorun devri düşüyorsa ESC senkronu kaybetmiştir. Ani gaz değişimleri, '
        'yüksek KV/büyük pervane ve eski firmware tetikler. Bazı ESC serilerinin bilinen sorunları vardır; forumda üretici adıyla arayın.',
        'If a motor output rises (the autopilot asks for more) while the same motor\'s RPM drops, the ESC has desynced. Sudden throttle changes, '
        'high KV/large props and old firmware trigger it. Some ESC series have known problems; search the forum by brand.',
        'إذا ارتفع خرج المحرك (الطيار الآلي يطلب المزيد) بينما تنخفض دورات المحرك نفسه فقد فقد ESC التزامن. التغيرات المفاجئة في الخانق '
        'وارتفاع KV/المراوح الكبيرة والبرامج القديمة تسببه. لبعض سلاسل ESC مشاكل معروفة؛ ابحث في المنتدى باسم الشركة.'),
  look=('ESC RPM ve RCOU aynı grafikte: çıkış ↑, devir ↓ = senkron kaybı. ESC telemetrisi yoksa yalnız itki kaybı imzası görülür.',
        'ESC RPM together with RCOU: output ↑, RPM ↓ = desync. Without ESC telemetry you only see the thrust-loss signature.',
        'ESC RPM مع RCOU معاً: الخرج ↑ والدوران ↓ = فقدان التزامن. بدون قياس ESC ترى فقط بصمة فقدان الدفع.'),
  fix=('ESC firmware\'ini güncelleyin (BLHeli: timing/demag ayarı), kalibrasyonu yenileyin, mümkünse DShot + çift yönlü telemetriye geçin.',
       'Update ESC firmware (BLHeli: timing/demag settings), recalibrate, and switch to DShot with bidirectional telemetry if possible.',
       'حدّث برنامج ESC (BLHeli: إعدادات التوقيت/demag)، وأعد المعايرة، وانتقل إلى DShot مع القياس ثنائي الاتجاه إن أمكن.')),
 'prop_loose': dict(cause='motor', chart='c_motors', icon='🪁', params=[],
  title=('Pervane gevşemesi / kopması', 'Loose or lost propeller', 'ارتخاء المروحة أو انفصالها'),
  rule=('Pervane fırladığında motor yükü bir anda azalır: çıkış tepeye gider ama devir artar. Fren yapan (aktif frenli) ESC\'lerde self-tightening '
        'somunlar gevşeyebilir. Kırımdan sonra yerde pervanenin nerede bulunduğu en güçlü kanıttır.',
        'When a prop flies off, the motor load drops instantly: the output goes to max but RPM increases. Self-tightening nuts can loosen with '
        'actively-braking ESCs. Where the prop was found after the crash is the strongest evidence.',
        'عندما تنفصل المروحة ينخفض حمل المحرك فجأة: يرتفع الخرج للأقصى لكن الدوران يزداد. قد ترتخي الصواميل ذاتية الشد مع ESC ذات الكبح '
        'النشط. مكان العثور على المروحة بعد السقوط أقوى دليل.'),
  look=('RCOU tepeye + ESC RPM yükseliyor + akım (CURR/ESC Curr) düşüyor.', 'RCOU to max + ESC RPM rising + current (CURR/ESC Curr) falling.',
        'RCOU للأقصى + ارتفاع ESC RPM + انخفاض التيار (CURR/ESC Curr).'),
  fix=('Kilitli somun/pin kullanın, her uçuş öncesi pervaneleri elle kontrol edin, pervane adaptörünü değiştirin.',
       'Use locking nuts/pins, check props by hand before every flight, replace prop adapters.',
       'استخدم صواميل/مسامير قفل، وافحص المراوح يدوياً قبل كل طيران، واستبدل محولات المراوح.')),
 'underpowered': dict(cause='power', chart='c_rcou', icon='🏋', params=['MOT_THST_HOVER', 'MOT_SPIN_MAX'],
  title=('Güçsüz / ağır araç: kontrol payı yok', 'Underpowered / overweight: no control headroom', 'طائرة ضعيفة / ثقيلة: لا هامش للتحكم'),
  rule=('Askıda motor çıkışları ≈1600–1700 µs (gaz %60–70+) ise aracın yön düzeltmek için payı kalmaz; rüzgârda, batarya düşerken ya da ani '
        'manevrada motorlar doyar. Uzmanların kuralı: askı gazı %50 civarında, itki/ağırlık en az 2:1 olmalı.',
        'If motor outputs hover around ≈1600–1700 µs (60–70%+ throttle) the aircraft has no room left to correct attitude; in wind, as the '
        'battery sags or in a sharp manoeuvre the motors saturate. Rule of thumb: hover near 50% throttle, thrust-to-weight at least 2:1.',
        'إذا كانت مخارج المحركات أثناء التحويم ≈1600–1700 ميكروثانية (خانق 60–70%+) فلا يبقى هامش لتصحيح الوضع؛ في الرياح أو مع هبوط جهد '
        'البطارية أو عند مناورة حادة تتشبّع المحركات. القاعدة: تحويم قرب 50% خانق، ونسبة دفع/وزن 2:1 على الأقل.'),
  look=('CTUN ThO (askı gazı), MOT_THST_HOVER, RCOU ortalaması; sonlara doğru tüm motorlar birlikte tepeye mi yaklaşıyor?',
        'CTUN ThO (hover throttle), MOT_THST_HOVER, mean RCOU; do all motors creep toward the top near the end?',
        'CTUN ThO (خانق التحويم)، MOT_THST_HOVER، متوسط RCOU؛ هل تقترب كل المحركات من الأعلى معاً قرب النهاية؟'),
  fix=('Ağırlığı azaltın ya da daha büyük pervane/motor/hücre sayısı kullanın; yükü itki tablosuyla (eCalc gibi) hesaplayın.',
       'Reduce weight or use bigger props/motors/more cells; check the load with a thrust calculator (such as eCalc).',
       'خفّف الوزن أو استخدم مراوح/محركات أكبر أو خلايا أكثر؛ احسب الحمل بحاسبة دفع (مثل eCalc).')),
 'vibe': dict(cause='vibration', chart='c_vibe', icon='〰', params=['INS_ACCEL_FILTER'],
  title=('Titreşim: önce onu düzeltin', 'Vibration: fix it first', 'الاهتزاز: أصلحه أولاً'),
  rule=('Forumda en sık verilen öğüt: VibeX/Y/Z 30 m/s²\'yi geçiyorsa ya da Clip sayaçları artıyorsa ayar yapmadan önce titreşimi giderin. '
        'Yüksek titreşim ivmeölçeri doyurur, EKF yüksekliği yanlış hesaplar ve araç kendiliğinden tırmanır ya da çakılır.',
        'The most frequent advice on the forum: if VibeX/Y/Z exceed 30 m/s² or the Clip counters increase, fix vibration before any tuning. '
        'High vibration saturates the accelerometer, the EKF misjudges height and the aircraft climbs away or drops by itself.',
        'أكثر نصيحة تكراراً في المنتدى: إذا تجاوز VibeX/Y/Z ‏30 م/ث² أو ازدادت عدادات Clip فأصلح الاهتزاز قبل أي ضبط. '
        'الاهتزاز العالي يشبع مقياس التسارع فيخطئ EKF في حساب الارتفاع فتصعد الطائرة أو تسقط من تلقاء نفسها.'),
  look=('VIBE VibeX/Y/Z (< 15 iyi, 30 sınır, 60 tehlike) ve Clip0/1/2 (artmamalı).', 'VIBE VibeX/Y/Z (< 15 good, 30 limit, 60 danger) and Clip0/1/2 (should not rise).',
        'VIBE VibeX/Y/Z (‏< 15 جيد، 30 حد، 60 خطر) وClip0/1/2 (يجب ألا تزداد).'),
  fix=('Pervaneleri dengeleyin, kırık/eğri pervaneyi atın, gevşek parçaları sıkın, uçuş kontrolcüsünü titreşim sönümleyici üzerine alın.',
       'Balance props, discard chipped/bent ones, tighten loose parts and mount the flight controller on vibration dampers.',
       'وازن المراوح، وتخلص من المكسورة/المنحنية، وشد الأجزاء المرتخية، وثبّت وحدة التحكم على مخمدات اهتزاز.')),
 'aliasing': dict(cause='vibration', chart='c_fft', icon='🎚', params=['INS_HNTCH_ENABLE', 'INS_HNTCH_MODE', 'INS_HNTCH_REF', 'INS_LOG_BAT_MASK'],
  title=('Harmonik çentik filtresi ve FFT', 'Harmonic notch filter and FFT', 'مرشح التوافقيات (Notch) وFFT'),
  rule=('Uzmanlar ayar öncesinde ham IMU kaydı (batch sampling) açıp FFT ile motor gürültü frekansını bulmayı ve harmonik çentik filtresini '
        'buna göre kurmayı ister. Çentik yoksa gürültü D terimini doldurur, motorlar ısınır ve salınım başlar. Örnekleme hızına yakın gürültü '
        '(aliasing) ise EKF\'yi yanıltır.',
        'Before tuning, experts ask you to enable raw IMU logging (batch sampling), find the motor noise frequency with FFT and set up the '
        'harmonic notch accordingly. Without a notch the noise fills the D-term, motors get hot and oscillation starts. Noise near the sample '
        'rate (aliasing) misleads the EKF.',
        'قبل الضبط يطلب الخبراء تفعيل تسجيل IMU الخام (batch sampling) وإيجاد تردد ضجيج المحركات بـ FFT وضبط مرشح التوافقيات وفقه. '
        'بدون المرشح يملأ الضجيج حد D فتسخن المحركات ويبدأ التذبذب. والضجيج القريب من معدل العينات (aliasing) يضلل EKF.'),
  look=('FFT grafiği (ISBD/ISBH): baskın tepe ve harmonikleri; RATE ve PIDR/PIDP D terimleri.', 'FFT chart (ISBD/ISBH): the dominant peak and its harmonics; RATE and PIDR/PIDP D terms.',
        'مخطط FFT ‏(ISBD/ISBH): القمة الغالبة وتوافقياتها؛ وحدود D في RATE وPIDR/PIDP.'),
  fix=('INS_LOG_BAT_MASK=1 ile bir askı uçuşu kaydedin, INS_HNTCH_ENABLE=1, MODE=3 (ESC devri) ya da 1 (gaz), REF/FREQ/BW değerlerini FFT\'den alın.',
       'Log a hover flight with INS_LOG_BAT_MASK=1, set INS_HNTCH_ENABLE=1, MODE=3 (ESC RPM) or 1 (throttle), take REF/FREQ/BW from the FFT.',
       'سجّل طيران تحويم مع INS_LOG_BAT_MASK=1، ثم INS_HNTCH_ENABLE=1 وMODE=3 (دوران ESC) أو 1 (الخانق)، وخذ REF/FREQ/BW من FFT.')),
 'pid_osc': dict(cause='control', chart='c_att', icon='📈', params=['ATC_RAT_RLL_P', 'ATC_RAT_RLL_D', 'ATC_RAT_PIT_P', 'ATC_RAT_PIT_D'],
  title=('Salınım: istenen ve gerçek açı ayrışıyor', 'Oscillation: desired and actual attitude diverge', 'التذبذب: الوضع المطلوب والفعلي يتباعدان'),
  rule=('Gerçek açı istenen açının etrafında giderek büyüyen dalgalar çiziyorsa kazançlar yüksek; tembelce geç takip ediyorsa düşük. Motorlar '
        'doymadan açı bozuluyorsa sorun ayardadır; önce motor doyuyorsa itki sorunudur.',
        'If the actual angle draws growing waves around the desired angle, gains are too high; if it follows lazily and late, they are too low. '
        'If attitude goes wrong before motors saturate, the problem is tuning; if a motor saturates first, it is a thrust problem.',
        'إذا رسمت الزاوية الفعلية موجات متزايدة حول المطلوبة فالمكاسب مرتفعة؛ وإذا تتبعتها ببطء وتأخر فهي منخفضة. إذا اختلّ الوضع قبل '
        'تشبّع المحركات فالمشكلة في الضبط؛ وإذا تشبّع محرك أولاً فهي مشكلة دفع.'),
  look=('ATT DesRoll/Roll, DesPitch/Pitch; RATE RDes/R; RCOU salınımı aynı frekansta mı?', 'ATT DesRoll/Roll, DesPitch/Pitch; RATE RDes/R; does RCOU oscillate at the same frequency?',
        'ATT DesRoll/Roll وDesPitch/Pitch؛ RATE RDes/R؛ هل يتذبذب RCOU بالتردد نفسه؟'),
  fix=('Kazançları %25–50 düşürüp AltHold\'da tekrar deneyin; sonra adım adım ya da AutoTune ile yükseltin.',
       'Lower gains by 25–50% and retest in AltHold; then raise step by step or with AutoTune.',
       'خفّض المكاسب 25–50% وأعد التجربة في AltHold؛ ثم ارفعها تدريجياً أو عبر AutoTune.')),
 'initial_tune': dict(cause='control', chart='c_att', icon='🧰', params=['MOT_THST_EXPO', 'INS_GYRO_FILTER', 'ATC_ACCEL_P_MAX', 'MOT_BAT_VOLT_MAX'],
  title=('Önce başlangıç parametreleri, sonra AutoTune', 'Initial parameters first, then AutoTune', 'المعاملات الأولية أولاً ثم AutoTune'),
  rule=('Uzmanların neredeyse her yeni yapıya söylediği: pervane çapı ve hücre sayısına göre başlangıç parametrelerini (Mission Planner '
        '"Initial Tune Parameters" ya da ArduPilot Methodic Configurator) uygulamadan, çentik filtresini kurmadan ve titreşimi düzeltmeden '
        'AutoTune yapmayın. Varsayılan değerler küçük bir 10" quad içindir.',
        'What experts tell almost every new build: do not run AutoTune before applying initial parameters for your prop size and cell count '
        '(Mission Planner "Initial Tune Parameters" or the ArduPilot Methodic Configurator), setting up the notch and fixing vibration. '
        'Defaults are for a small 10" quad.',
        'ما يقوله الخبراء لكل بناء جديد تقريباً: لا تشغّل AutoTune قبل تطبيق المعاملات الأولية حسب قطر المروحة وعدد الخلايا (Mission Planner '
        '"Initial Tune Parameters" أو ArduPilot Methodic Configurator) وضبط مرشح Notch وإصلاح الاهتزاز. القيم الافتراضية لطائرة رباعية صغيرة 10".'),
  look=('PARM: MOT_THST_EXPO, INS_GYRO_FILTER, ATC_ACCEL_*_MAX varsayılan mı? Program "PARM denetimi" bunu gösterir.',
        'PARM: are MOT_THST_EXPO, INS_GYRO_FILTER, ATC_ACCEL_*_MAX still default? The program\'s "PARM check" shows this.',
        'PARM: هل MOT_THST_EXPO وINS_GYRO_FILTER وATC_ACCEL_*_MAX ما زالت افتراضية؟ يبين ذلك "فحص PARM" في البرنامج.'),
  fix=('Sıra: kalibrasyonlar → başlangıç parametreleri → titreşim → çentik filtresi → AltHold\'da deneme → AutoTune (eksen eksen).',
       'Order: calibrations → initial parameters → vibration → notch filter → test in AltHold → AutoTune (axis by axis).',
       'الترتيب: المعايرات ← المعاملات الأولية ← الاهتزاز ← مرشح Notch ← تجربة في AltHold ← AutoTune (محوراً محوراً).')),
 'autotune': dict(cause='control', chart='c_pid', icon='🎛', params=['AUTOTUNE_AXES', 'AUTOTUNE_AGGR'],
  title=('AutoTune sonucu güvenilir mi?', 'Can you trust the AutoTune result?', 'هل نتيجة AutoTune موثوقة؟'),
  rule=('AutoTune rüzgârlı havada, ağır titreşimde ya da çok düşük/yüksek başlangıç kazançlarıyla saçma değerler üretebilir. Kaydetmeden önce '
        'değerleri eski ayarla karşılaştırın; bir eksende değer birkaç kat değiştiyse kaydetmeyin. AutoTune sırasında güç kesilen ya da kayıt biten '
        'loglar da forumda sık görülür.',
        'AutoTune can produce absurd values in wind, with heavy vibration or with very low/high starting gains. Compare the values with the old '
        'tune before saving; if one axis changed several-fold, do not save. Logs where power failed or logging stopped during AutoTune are common.',
        'قد ينتج AutoTune قيماً غير معقولة في الرياح أو مع اهتزاز شديد أو مع مكاسب بدء منخفضة/مرتفعة جداً. قارن القيم مع الضبط القديم قبل '
        'الحفظ؛ إذا تغير محور عدة أضعاف فلا تحفظ. السجلات التي انقطعت فيها الطاقة أو توقف التسجيل أثناء AutoTune شائعة أيضاً.'),
  look=('ATUN mesajları, PARM ATC_RAT_* önce/sonra; MSG "AutoTune: Success" ya da hata.', 'ATUN messages, PARM ATC_RAT_* before/after; MSG "AutoTune: Success" or failure.',
        'رسائل ATUN، وPARM ATC_RAT_* قبل/بعد؛ MSG ‏"AutoTune: Success" أو الفشل.'),
  fix=('Sakin havada, dolu batarya ile, AUTOTUNE_AXES ile tek eksen yapın; sonucu kaydetmeden önce AltHold\'da yumuşak manevra deneyin.',
       'Do it in calm air, on a full battery, one axis at a time with AUTOTUNE_AXES; test gentle manoeuvres in AltHold before saving.',
       'نفّذه في هواء هادئ وببطارية ممتلئة ومحوراً واحداً عبر AUTOTUNE_AXES؛ جرّب مناورات لطيفة في AltHold قبل الحفظ.')),
 'defaults': dict(cause='control', chart='c_att', icon='📦', params=[],
  title=('Varsayılan parametrelerle ilk uçuş', 'First flight on default parameters', 'أول طيران بالمعاملات الافتراضية'),
  rule=('İlk uçuşu doğrudan PosHold/Loiter/Auto ile yapan ve parametreleri hiç değiştirmeyen kullanıcılar forumdaki kırımların büyük bir kısmını '
        'oluşturur. İlk kalkış Stabilize ya da AltHold\'da, alçakta ve kısa olmalı; konum modları ancak pusula ve titreşim doğrulandıktan sonra.',
        'Users who make the first flight straight in PosHold/Loiter/Auto and never change parameters make up a large share of forum crashes. '
        'The first take-off should be in Stabilize or AltHold, low and short; position modes only after compass and vibration are verified.',
        'المستخدمون الذين يطيرون أول مرة مباشرة في PosHold/Loiter/Auto دون تغيير المعاملات يشكلون نسبة كبيرة من حوادث المنتدى. '
        'يجب أن يكون الإقلاع الأول في Stabilize أو AltHold منخفضاً وقصيراً؛ وأوضاع الموقع فقط بعد التحقق من البوصلة والاهتزاز.'),
  look=('MODE: kalkış hangi modda? PARM farkları: varsayılandan değişen kaç parametre var?', 'MODE: which mode was used for take-off? PARM: how many parameters differ from default?',
        'MODE: في أي وضع تم الإقلاع؟ PARM: كم معاملاً تغير عن الافتراضي؟'),
  fix=('Kurulum listesini sırayla bitirin (çerçeve, kalibrasyon, motor testi, failsafe), sonra kademeli modlarla uçun.',
       'Finish the setup checklist in order (frame, calibrations, motor test, failsafes), then fly with progressive modes.',
       'أكمل قائمة الإعداد بالترتيب (الهيكل، المعايرات، اختبار المحركات، الحماية)، ثم طِر بأوضاع متدرجة.')),
 'arming_check': dict(cause='control', chart='c_timeline', icon='🚫', params=['ARMING_CHECK'],
  title=('ARMING_CHECK=0: uyarıları susturmak', 'ARMING_CHECK=0: silencing the warnings', 'ARMING_CHECK=0: إسكات التحذيرات'),
  rule=('Kalkış öncesi kontrolleri kapatmak sorunu çözmez, yalnız haberi keser. Forumdaki uzmanlar ARMING_CHECK=0 gördükleri logda önce hangi '
        'kontrolün başarısız olduğunu sorar; çoğu kez pusula, ivmeölçer kalibrasyonu ya da EKF zaten hazır değildir.',
        'Disabling pre-arm checks does not fix the problem, it only hides it. When experts see ARMING_CHECK=0 they first ask which check was '
        'failing; most of the time the compass, accelerometer calibration or EKF was not ready.',
        'تعطيل فحوص ما قبل التسليح لا يحل المشكلة بل يخفيها. عندما يرى الخبراء ARMING_CHECK=0 يسألون أولاً أي فحص كان يفشل؛ وغالباً '
        'كانت البوصلة أو معايرة مقياس التسارع أو EKF غير جاهزة.'),
  look=('PARM ARMING_CHECK; MSG "PreArm:" satırları; EKF ve pusula sağlığı kalkıştan önce.', 'PARM ARMING_CHECK; MSG "PreArm:" lines; EKF and compass health before take-off.',
        'PARM ARMING_CHECK؛ أسطر MSG ‏"PreArm:"؛ صحة EKF والبوصلة قبل الإقلاع.'),
  fix=('ARMING_CHECK=1 yapın, her PreArm mesajının nedenini giderin.', 'Set ARMING_CHECK=1 and fix the cause of each PreArm message.',
       'اضبط ARMING_CHECK=1 وأصلح سبب كل رسالة PreArm.')),
 'motor_order': dict(cause='control', chart='c_motors', icon='🔢', params=['FRAME_CLASS', 'FRAME_TYPE'],
  title=('Motor sırası, dönüş yönü ve çerçeve tipi', 'Motor order, spin direction and frame type', 'ترتيب المحركات واتجاه الدوران ونوع الهيكل'),
  rule=('Kalkar kalkmaz takla atan araçlarda ilk şüpheli yanlış motor sırası, ters dönen motor, ters takılmış pervane ya da yanlış FRAME_TYPE\'tır. '
        'Böyle bir araç yerden kesildiği anda bir yöne savrulur; motor çıkışları ilk saniyede zıt köşelerde doyar.',
        'When a vehicle flips right at take-off, the first suspects are wrong motor order, a motor spinning backwards, a prop mounted upside '
        'down or the wrong FRAME_TYPE. Such a vehicle lurches to one side the moment it leaves the ground; outputs saturate on opposite corners in the first second.',
        'عندما تنقلب الطائرة فور الإقلاع فأول المشتبهين: ترتيب محركات خاطئ أو محرك يدور عكسياً أو مروحة مقلوبة أو FRAME_TYPE خاطئ. '
        'تنحرف هذه الطائرة لحظة ارتفاعها عن الأرض؛ وتتشبّع المخارج في زوايا متقابلة خلال الثانية الأولى.'),
  look=('Kalkış anı: RCOU ilk saniye ve ATT Roll/Pitch; PARM FRAME_CLASS/TYPE.', 'Take-off moment: RCOU in the first second and ATT Roll/Pitch; PARM FRAME_CLASS/TYPE.',
        'لحظة الإقلاع: RCOU في الثانية الأولى وATT Roll/Pitch؛ PARM FRAME_CLASS/TYPE.'),
  fix=('Mission Planner Motor Test ile A, B, C, D sırasını ve dönüş yönünü pervanesiz doğrulayın.', 'Verify A, B, C, D order and spin direction with Mission Planner Motor Test, props off.',
       'تحقق من ترتيب A وB وC وD واتجاه الدوران عبر Motor Test في Mission Planner دون مراوح.')),
 'pilot_stab': dict(cause='pilot', chart='c_sticks', icon='🎮', params=['FLTMODE1', 'FS_THR_ENABLE'],
  title=('Gaz kolu dipteyken Stabilize: "hızla yere dönüş"', 'Stabilize with throttle low: "rapid return to earth"', 'Stabilize والخانق في الأسفل: "عودة سريعة إلى الأرض"'),
  rule=('AltHold/Loiter\'da gaz kolu ortadayken araç yüksekliği tutar; Stabilize\'e geçildiğinde gaz kolu doğrudan motorlara gider. Kol dipteyse '
        'motorlar rölantiye iner ve araç düşer. Uzmanlar bu kırımları şakayla "Rapid Return To Earth" modu diye anar; araçta arıza yoktur.',
        'In AltHold/Loiter the aircraft holds height with the stick at mid; in Stabilize the throttle stick goes straight to the motors. If the '
        'stick is at the bottom the motors drop to idle and it falls. Experts jokingly call these crashes "Rapid Return To Earth"; nothing is broken.',
        'في AltHold/Loiter تحافظ الطائرة على الارتفاع والعصا في المنتصف؛ وفي Stabilize تذهب عصا الخانق مباشرة إلى المحركات. إذا كانت العصا في '
        'الأسفل تنخفض المحركات إلى الخمول وتسقط. يسمي الخبراء هذه الحوادث مازحين "Rapid Return To Earth"؛ ولا عطل في الطائرة.'),
  look=('MODE değişimi (Stabilize/Acro) + RCIN C3 / CTUN ThI aynı anda dipte; ardından yükseklik hızla düşüyor.',
        'MODE change (Stabilize/Acro) + RCIN C3 / CTUN ThI at the bottom at the same moment; then altitude falls fast.',
        'تغيير MODE ‏(Stabilize/Acro) + RCIN C3 / CTUN ThI في الأسفل في اللحظة نفسها؛ ثم ينخفض الارتفاع بسرعة.'),
  fix=('Acil durum anahtarı olarak Stabilize yerine AltHold/Land kullanın; Stabilize\'e geçmeden önce gaz kolunu askı noktasına getirin.',
       'Use AltHold/Land as the panic switch instead of Stabilize; bring the throttle to hover position before switching to Stabilize.',
       'استخدم AltHold/Land كمفتاح طوارئ بدلاً من Stabilize؛ وارفع الخانق إلى نقطة التحويم قبل التبديل إلى Stabilize.')),
 'battery_sag': dict(cause='battery', chart='c_bat', icon='🔋', params=['BATT_LOW_VOLT', 'BATT_CRT_VOLT', 'BATT_FS_LOW_ACT', 'MOT_BAT_VOLT_MIN'],
  title=('Batarya çökmesi ve yanlış failsafe ayarı', 'Battery sag and a misconfigured failsafe', 'هبوط جهد البطارية وإعداد حماية خاطئ'),
  rule=('Yük altında hücre başına 3,3 V\'un altına inen, iç direnci yükselmiş ya da kapasitesi yetersiz batarya araç havadayken gücü bırakır. '
        'Uzmanların ortak gözlemi: failsafe gerilimleri yük altındaki gerilime göre değil boştaki gerilime göre ayarlanmıştır ya da hiç ayarlanmamıştır.',
        'A battery that drops below 3.3 V per cell under load, has high internal resistance or too little capacity lets go of power in the air. '
        'Experts\' common observation: failsafe voltages were set for resting voltage instead of voltage under load, or not set at all.',
        'البطارية التي تنخفض تحت 3.3 فولت للخلية تحت الحمل أو التي ارتفعت مقاومتها الداخلية أو قلّت سعتها تفقد الطاقة في الجو. '
        'ملاحظة الخبراء المشتركة: ضُبطت جهود الحماية على الجهد في السكون لا تحت الحمل، أو لم تُضبط أصلاً.'),
  look=('BAT Volt ve Curr birlikte: gaz artınca gerilim ne kadar düşüyor? CurrTot (mAh) kapasiteye yakın mı? BATT_* parametreleri.',
        'BAT Volt with Curr: how much does voltage drop when throttle rises? Is CurrTot (mAh) near capacity? BATT_* parameters.',
        'BAT Volt مع Curr: كم ينخفض الجهد عند زيادة الخانق؟ هل CurrTot ‏(mAh) قريب من السعة؟ معاملات BATT_*.'),
  fix=('Güç modülünü kalibre edin (BATT_AMP_PERVLT/VOLT_MULT), BATT_LOW_VOLT ≈3,5 V/hücre, BATT_FS_LOW_ACT=RTL ya da Land; eski bataryaları ayırın.',
       'Calibrate the power module (BATT_AMP_PERVLT/VOLT_MULT), BATT_LOW_VOLT ≈3.5 V/cell, BATT_FS_LOW_ACT=RTL or Land; retire old packs.',
       'عاير وحدة الطاقة (BATT_AMP_PERVLT/VOLT_MULT)، وBATT_LOW_VOLT ≈3.5 فولت/خلية، وBATT_FS_LOW_ACT=RTL أو Land؛ واستبعد البطاريات القديمة.')),
 'brownout': dict(cause='power', chart='c_bat', icon='🔌', params=['BRD_SAFETY_DEFLT'],
  title=('Otopilot beslemesi (Vcc) ve kayıt aniden biter', 'Autopilot supply (Vcc) and the log suddenly ends', 'تغذية الطيار الآلي (Vcc) وتوقف السجل فجأة'),
  rule=('Log havada, bir hata mesajı olmadan aniden bitiyorsa en olası neden otopilotun beslemesinin kesilmesidir (brownout). Vcc\'nin 4,8 V altına '
        'inmesi, ortak BEC\'in servolarla paylaşılması, gevşek güç konnektörü ya da tek güç modülü tipik bulgulardır.',
        'If the log ends suddenly in the air without an error message, the most likely cause is the autopilot losing power (brownout). Vcc dropping '
        'below 4.8 V, a BEC shared with servos, a loose power connector or a single power module are typical findings.',
        'إذا انتهى السجل فجأة في الجو دون رسالة خطأ فالسبب الأرجح انقطاع تغذية الطيار الآلي (brownout). من النتائج المعتادة: انخفاض Vcc '
        'تحت 4.8 فولت، أو BEC مشترك مع المؤازرات، أو موصل طاقة مرتخٍ، أو وحدة طاقة واحدة.'),
  look=('POWR Vcc (≈5,0–5,3 V sabit olmalı), POWR Flags; logun son saniyesi: motorlar hâlâ yüksek mi?', 'POWR Vcc (should be steady ≈5.0–5.3 V), POWR Flags; the last second of the log: are motors still high?',
        'POWR Vcc (يجب أن يكون ثابتاً ≈5.0–5.3 فولت)، POWR Flags؛ الثانية الأخيرة من السجل: هل المحركات ما زالت مرتفعة؟'),
  fix=('Otopilota ikinci (yedek) güç kaynağı verin, servoları ayrı BEC\'ten besleyin, güç konnektörlerini değiştirin.',
       'Give the autopilot a second (redundant) power source, power servos from a separate BEC, replace power connectors.',
       'زوّد الطيار الآلي بمصدر طاقة ثانٍ احتياطي، وغذِّ المؤازرات من BEC منفصل، واستبدل موصلات الطاقة.')),
 'compass_int': dict(cause='compass', chart='c_mag', icon='🧭', params=['COMPASS_MOTCT', 'COMPASS_PRIO1_ID', 'COMPASS_USE2', 'COMPASS_ORIENT'],
  title=('Pusula paraziti: güç kabloları ve motor akımı', 'Compass interference: power wires and motor current', 'تشويش البوصلة: أسلاك الطاقة وتيار المحركات'),
  rule=('Gaz artınca manyetik alan büyüklüğü değişiyorsa pusula güç kablolarından etkileniyordur. Sonuç Loiter/Auto\'da "tuvalet kabı" gibi '
        'büyüyen daireler ve kontrolsüz kaymadır. Uzmanlar iç pusulayı kapatıp GPS direğindeki dış pusulayı öncelikli yapmayı ve compassmot yapmayı önerir.',
        'If the magnetic field strength changes with throttle, the compass is affected by power wiring. The result is "toilet-bowling" (growing '
        'circles) and drift in Loiter/Auto. Experts recommend disabling the internal compass, prioritising the external one on the GPS mast and running compassmot.',
        'إذا تغيرت شدة المجال المغناطيسي مع الخانق فالبوصلة تتأثر بأسلاك الطاقة. النتيجة دوائر متزايدة ("toilet bowl") وانجراف في '
        'Loiter/Auto. يوصي الخبراء بتعطيل البوصلة الداخلية وإعطاء الأولوية للخارجية على صاري GPS وتنفيذ compassmot.'),
  look=('MAG MagX/Y/Z büyüklüğü ile CTUN ThO / BAT Curr karşılaştırması; XKF4 SM (pusula yeniliği); iki pusula arasında yön farkı.',
        'MAG MagX/Y/Z magnitude against CTUN ThO / BAT Curr; XKF4 SM (compass innovation); heading difference between two compasses.',
        'شدة MAG MagX/Y/Z مقابل CTUN ThO / BAT Curr؛ XKF4 SM (ابتكار البوصلة)؛ فرق الاتجاه بين بوصلتين.'),
  fix=('Güç kablolarını büküp uzaklaştırın, pusulayı direğe taşıyın, sadece en iyi pusulayı kullanın, compassmot ile akım düzeltmesi yapın.',
       'Twist and move power wires away, move the compass onto a mast, use only the best compass, do a current compensation with compassmot.',
       'اجدل أسلاك الطاقة وأبعدها، وانقل البوصلة إلى صارٍ، واستخدم أفضل بوصلة فقط، ونفّذ تعويض التيار عبر compassmot.')),
 'ekf': dict(cause='ekf', chart='c_ekf', icon='🧮', params=['EK3_SRC1_POSZ', 'EK3_IMU_MASK', 'FS_EKF_THRESH'],
  title=('EKF varyansı ve şerit (lane) değişimi', 'EKF variance and lane switching', 'تباين EKF وتبديل المسار (lane)'),
  rule=('EKF hataları genellikle nedenin değil sonucun işaretidir: titreşim, pusula paraziti ya da GPS hatası önce gelir. Uzmanlar EKF uyarısından '
        'geriye doğru bakıp hangi sensörün yenilik (innovation) değerinin ilk büyüdüğünü bulur. Bir IMU\'nun sapması şerit değişimine yol açar.',
        'EKF errors are usually a symptom, not the cause: vibration, compass interference or GPS error comes first. Experts look back from the '
        'EKF warning to find which sensor\'s innovation grew first. One IMU drifting causes lane switches.',
        'أخطاء EKF غالباً عَرَض لا سبب: يسبقها الاهتزاز أو تشويش البوصلة أو خطأ GPS. ينظر الخبراء إلى الخلف من تحذير EKF ليجدوا أي حساس '
        'كبرت قيمة ابتكاره أولاً. انحراف أحد IMU يسبب تبديل المسار.'),
  look=('XKF4 SV/SP/SH/SM (vel/pos/yük./pusula testi), XKF3 yenilikler, XKF1 karşılaştırması (IMU0 ↔ IMU1), MSG "EKF primary changed".',
        'XKF4 SV/SP/SH/SM (vel/pos/height/compass test), XKF3 innovations, XKF1 comparison (IMU0 ↔ IMU1), MSG "EKF primary changed".',
        'XKF4 SV/SP/SH/SM (اختبار السرعة/الموقع/الارتفاع/البوصلة)، ابتكارات XKF3، مقارنة XKF1 ‏(IMU0 ↔ IMU1)، MSG ‏"EKF primary changed".'),
  fix=('Önce ilk bozulan sensörü düzeltin (titreşim/pusula/GPS); sorunlu IMU\'yu EK3_IMU_MASK ile dışarıda bırakın.',
       'Fix the sensor that went wrong first (vibration/compass/GPS); exclude a bad IMU with EK3_IMU_MASK.',
       'أصلح الحساس الذي اختلّ أولاً (الاهتزاز/البوصلة/GPS)؛ واستبعد IMU المعطوب عبر EK3_IMU_MASK.')),
 'gps': dict(cause='gps', chart='c_gps', icon='🛰', params=['GPS_TYPE', 'GPS_GNSS_MODE', 'FS_EKF_ACTION'],
  title=('GPS kaybı: kablo, konnektör ve parazit', 'GPS loss: wiring, connector and interference', 'فقدان GPS: الأسلاك والموصل والتشويش'),
  rule=('Uydu sayısının iyi bir değerden (ör. 17) bir anda sıfıra düşmesi gökyüzü sorunu değil bağlantı sorunudur: gevşek konnektör, kopuk kablo '
        'ya da GPS\'in sıfırlanması. Yavaş bozulma (HDop artışı, uydu azalması) ise parazit, binalar ya da video vericisinden gelir.',
        'Satellite count dropping from a good value (e.g. 17) to zero in an instant is not a sky problem but a connection problem: a loose '
        'connector, broken wire or a GPS reset. Slow degradation (HDop rising, sats falling) comes from interference, buildings or the video transmitter.',
        'انخفاض عدد الأقمار من قيمة جيدة (مثلاً 17) إلى الصفر فجأة ليس مشكلة سماء بل مشكلة اتصال: موصل مرتخٍ أو سلك مقطوع أو إعادة تشغيل '
        'GPS. أما التدهور البطيء (ارتفاع HDop ونقص الأقمار) فسببه التشويش أو المباني أو جهاز إرسال الفيديو.'),
  look=('GPS NSats, HDop, Status; GPA VAcc/SAcc; ani sıçrama mı yavaş bozulma mı?', 'GPS NSats, HDop, Status; GPA VAcc/SAcc; sudden jump or slow degradation?',
        'GPS NSats وHDop وStatus؛ GPA VAcc/SAcc؛ قفزة مفاجئة أم تدهور بطيء؟'),
  fix=('GPS kablosunu ve konnektörünü değiştirin, GPS\'i video vericisinden uzaklaştırın, AltHold\'a geçişi acil durum için hazır tutun.',
       'Replace the GPS cable and connector, move the GPS away from the video transmitter, keep AltHold ready as a fallback.',
       'استبدل كابل GPS وموصله، وأبعد GPS عن جهاز إرسال الفيديو، واجعل AltHold جاهزاً كبديل للطوارئ.')),
 'rc_failsafe': dict(cause='radio', chart='c_sticks', icon='📡', params=['FS_THR_ENABLE', 'FS_THR_VALUE', 'RC_OPTIONS'],
  title=('Kumanda kaybı ve failsafe çalışmaması', 'RC loss and a failsafe that did not trigger', 'فقدان التحكم وعدم عمل الحماية'),
  rule=('Alıcı sinyal kaybında son gaz değerini tutacak şekilde ayarlanmışsa otopilot kumandanın kaybolduğunu anlamaz; araç uçmaya devam eder. '
        'Uzmanlar alıcının "no pulses" ya da FS_THR_VALUE altına düşecek şekilde ayarlanmasını ve vericiyi kapatarak yerde test edilmesini ister.',
        'If the receiver is set to hold the last throttle on signal loss, the autopilot never learns that RC is lost; the aircraft keeps flying. '
        'Experts ask that the receiver be set to "no pulses" or below FS_THR_VALUE, and tested on the ground by switching off the transmitter.',
        'إذا ضُبط المستقبل على الاحتفاظ بآخر قيمة خانق عند فقدان الإشارة فلن يعرف الطيار الآلي أن التحكم فُقد؛ وتستمر الطائرة بالطيران. '
        'يطلب الخبراء ضبط المستقبل على "no pulses" أو تحت FS_THR_VALUE واختباره على الأرض بإطفاء جهاز الإرسال.'),
  look=('RCIN C1–C4 donuyor ya da zıplıyor mu? RSSI; ERR Subsys 2 (radyo); MODE RTL\'ye geçti mi?', 'Do RCIN C1–C4 freeze or jump? RSSI; ERR Subsys 2 (radio); did MODE switch to RTL?',
        'هل تتجمد RCIN C1–C4 أو تقفز؟ RSSI؛ ERR Subsys 2 (الراديو)؛ هل تحوّل MODE إلى RTL؟'),
  fix=('Alıcı failsafe\'ini doğru ayarlayın, FS_THR_ENABLE=1, vericiyi kapatıp yerde RTL\'ye geçişi doğrulayın; anteni gövdeden uzak tutun.',
       'Configure the receiver failsafe correctly, FS_THR_ENABLE=1, switch the transmitter off on the ground and confirm it goes to RTL; keep antennas away from the frame.',
       'اضبط حماية المستقبل بشكل صحيح، وFS_THR_ENABLE=1، وأطفئ جهاز الإرسال على الأرض وتأكد من التحول إلى RTL؛ وأبعد الهوائيات عن الهيكل.')),
 'rc_calib': dict(cause='radio', chart='c_sticks', icon='🎚', params=['RC3_MIN', 'RC3_MAX', 'RC1_TRIM'],
  title=('Kumanda kalibrasyonu ve trimler', 'Radio calibration and trims', 'معايرة جهاز التحكم والتريم'),
  rule=('Kalibre edilmemiş kumandada gaz kolu dipte iken bile %0\'ın üstünde ya da tepede iken %100\'ün altında okunur; araç beklenmedik biçimde '
        'yükselir, iner ya da failsafe tetiklenir. Vericideki trimler sıfırlanmadan yapılan kalibrasyon sürekli kaymaya yol açar.',
        'With an uncalibrated radio the throttle reads above 0% at the bottom or below 100% at the top; the aircraft climbs or sinks unexpectedly, '
        'or failsafe triggers. Calibrating without centring the transmitter trims causes constant drift.',
        'مع جهاز تحكم غير معاير تُقرأ عصا الخانق فوق 0% في الأسفل أو تحت 100% في الأعلى؛ فتصعد الطائرة أو تهبط بشكل غير متوقع أو تعمل الحماية. '
        'المعايرة دون تصفير التريم في جهاز الإرسال تسبب انجرافاً مستمراً.'),
  look=('RCIN C1–C4 en düşük/en yüksek değerleri ile PARM RCx_MIN/MAX/TRIM.', 'RCIN C1–C4 minimum/maximum against PARM RCx_MIN/MAX/TRIM.',
        'أدنى/أعلى قيم RCIN C1–C4 مقابل PARM RCx_MIN/MAX/TRIM.'),
  fix=('Vericide trimleri sıfırlayın, Mission Planner ile radyo kalibrasyonunu yapın, kolları tam uçlara götürün.',
       'Centre transmitter trims, do the radio calibration in Mission Planner, move sticks fully to the ends.',
       'صفّر التريم في جهاز الإرسال، ونفّذ معايرة الراديو في Mission Planner، وحرّك العصي إلى أقصى أطرافها.')),
 'cg': dict(cause='stall', chart='c_att', icon='⚖', params=[],
  title=('Uçakta ağırlık merkezi (CG)', 'Aircraft centre of gravity (CG)', 'مركز الثقل في الطائرة (CG)'),
  rule=('Kuyruk ağır bir uçak burnunu kaldırmaya devam eder, yunuslama yapar ve sonunda tutunma kaybıyla spirale girer; hiçbir PID bunu kurtaramaz. '
        'Uzmanların ilk sorusu CG\'nin üreticinin önerdiği noktada olup olmadığıdır; hafif burun ağırlığı her zaman daha güvenlidir.',
        'A tail-heavy aircraft keeps pitching its nose up, porpoises and finally stalls into a spiral; no PID can save it. The experts\' first '
        'question is whether the CG is at the manufacturer\'s point; slightly nose-heavy is always safer.',
        'الطائرة الثقيلة الذيل تستمر برفع أنفها وتتأرجح ثم تفقد الرفع وتدخل في دوامة؛ ولا يمكن لأي PID إنقاذها. السؤال الأول للخبراء: هل '
        'مركز الثقل في النقطة التي يوصي بها المصنّع؟ الثقل الخفيف في الأنف أكثر أماناً دائماً.'),
  look=('ATT Pitch ve DesPitch: istenen eğim aşağıyken burun yukarı mı? RCOU irtifa dümeni sürekli bir uçta mı?', 'ATT Pitch vs DesPitch: is the nose up while down is demanded? Is the elevator RCOU stuck at one end?',
        'ATT Pitch مقابل DesPitch: هل الأنف مرتفع بينما المطلوب أسفل؟ هل خرج الرافع RCOU عالق في طرف واحد؟'),
  fix=('Uçağı CG noktasından parmakla dengeleyin, bataryayı öne alın; ilk uçuşu FBWA\'da yapıp trimleri öğrenin.',
       'Balance the plane on your fingertips at the CG, move the battery forward; fly the first flight in FBWA and learn the trims.',
       'وازن الطائرة على أطراف أصابعك عند نقطة CG، وحرّك البطارية للأمام؛ واجعل أول طيران في FBWA لتتعلم التريم.')),
 'stall': dict(cause='stall', chart='c_tecs', icon='🛬', params=['AIRSPEED_MIN', 'ARSPD_USE', 'TECS_PITCH_MAX', 'LIM_ROLL_CD'],
  title=('Uçakta tutunma kaybı (stall)', 'Aircraft stall', 'فقدان الرفع (stall) في الطائرة'),
  rule=('Hava hızı AIRSPEED_MIN altına inip burun yukarıdayken bir kanat düşer; dönüşlerde ve tırmanışta daha erkendir. Hava hızı sensörü yoksa ya '
        'da yanlış kalibre edilmişse TECS gazı yanlış yönetir. Sert dönüşte (LIM_ROLL_CD yüksek) tutunma hızı artar.',
        'When airspeed falls below AIRSPEED_MIN with the nose up, one wing drops; it comes earlier in turns and climbs. Without an airspeed sensor '
        'or with a bad calibration, TECS manages throttle wrongly. In steep turns (high LIM_ROLL_CD) stall speed rises.',
        'عندما تنخفض السرعة الجوية تحت AIRSPEED_MIN والأنف مرتفع يسقط أحد الجناحين؛ ويحدث أبكر في المنعطفات والصعود. بدون حساس سرعة جوية '
        'أو مع معايرة خاطئة يدير TECS الخانق بشكل خاطئ. وفي المنعطفات الحادة (LIM_ROLL_CD مرتفع) تزداد سرعة فقدان الرفع.'),
  look=('ARSP Airspeed / CTUN As, TECS sp/sph; ATT Roll ani yatış; yükseklik kaybı.', 'ARSP Airspeed / CTUN As, TECS sp/sph; ATT Roll sudden bank; height loss.',
        'ARSP Airspeed / CTUN As، TECS sp/sph؛ ATT Roll ميل مفاجئ؛ فقدان الارتفاع.'),
  fix=('AIRSPEED_MIN\'i gerçek tutunma hızının %20–25 üstüne koyun, hava hızı sensörünü kalibre edin, LIM_ROLL_CD\'yi sınırlayın.',
       'Set AIRSPEED_MIN 20–25% above the real stall speed, calibrate the airspeed sensor, limit LIM_ROLL_CD.',
       'اضبط AIRSPEED_MIN فوق سرعة فقدان الرفع الحقيقية بـ 20–25%، وعاير حساس السرعة الجوية، وحدّ من LIM_ROLL_CD.')),
 'reversed': dict(cause='control', chart='c_rcou', icon='⇄', params=['SERVO1_REVERSED', 'SERVO2_REVERSED', 'SERVO4_REVERSED'],
  title=('Ters servo / ters kumanda yüzeyi', 'Reversed servo / control surface', 'مؤازر / سطح تحكم معكوس'),
  rule=('Otopilot sağa yatırmak istediğinde uçak sola yatıyorsa bir kanatçık ya da dümen ters çalışıyordur; elle kumanda doğru gibi görünse bile '
        'otomatik modlarda kaza kaçınılmazdır. Forumdaki uçak kırımlarının belirgin bir kısmı budur.',
        'If the aircraft rolls left when the autopilot asks for right, an aileron or rudder works in reverse; even if manual control looks right, '
        'a crash is certain in auto modes. A noticeable share of plane crashes on the forum are this.',
        'إذا مالت الطائرة لليسار عندما يطلب الطيار الآلي اليمين فإن الجنيح أو الدفة يعمل بالعكس؛ حتى لو بدا التحكم اليدوي صحيحاً فالحادث '
        'حتمي في الأوضاع الآلية. نسبة ملحوظة من حوادث الطائرات في المنتدى من هذا النوع.'),
  look=('ATT DesRoll ↑ iken Roll ↓; RCOU ilgili servo kanalı.', 'ATT DesRoll ↑ while Roll ↓; RCOU of the related servo channel.',
        'ATT DesRoll ↑ بينما Roll ↓؛ RCOU لقناة المؤازر المعنية.'),
  fix=('FBWA modunda uçağı elle yatırıp yüzeylerin düzeltme yönünde hareket ettiğini doğrulayın; gerekirse SERVOx_REVERSED.',
       'In FBWA tilt the aircraft by hand and confirm the surfaces move to correct it; set SERVOx_REVERSED if needed.',
       'في وضع FBWA أمِل الطائرة باليد وتأكد أن الأسطح تتحرك لتصحيحها؛ واضبط SERVOx_REVERSED عند الحاجة.')),
 'esc_telem': dict(cause='motor', chart='c_esc', icon='📟', params=['SERVO_BLH_BDMASK', 'MOT_PWM_TYPE', 'ESC_TLM'],
  title=('ESC telemetrisi: kanıtı kaydedin', 'ESC telemetry: record the evidence', 'قياسات ESC: سجّل الدليل'),
  rule=('Motor/ESC arızası ile ayar sorununu ayırt etmenin en güvenilir yolu her motorun devrini kaydetmektir. Uzmanlar devir verisi olmayan loglarda '
        'kesin hüküm vermekten kaçınır; çift yönlü DShot ayrıca çentik filtresini motor devrine bağlamayı sağlar.',
        'The most reliable way to separate a motor/ESC failure from a tuning problem is to log each motor\'s RPM. Experts avoid a firm verdict on '
        'logs without RPM data; bidirectional DShot also lets the notch filter follow motor RPM.',
        'أكثر طريقة موثوقة للتمييز بين عطل المحرك/ESC ومشكلة الضبط هي تسجيل دوران كل محرك. يتجنب الخبراء الحكم القاطع على سجلات بلا بيانات '
        'دوران؛ كما يتيح DShot ثنائي الاتجاه ربط مرشح Notch بدوران المحركات.'),
  look=('ESC RPM, Curr, Temp; yoksa bu logda motor/ESC kanıtı sınırlıdır.', 'ESC RPM, Curr, Temp; if absent, motor/ESC evidence in this log is limited.',
        'ESC RPM وCurr وTemp؛ وإن غابت فأدلة المحرك/ESC في هذا السجل محدودة.'),
  fix=('DShot destekli ESC kullanın, SERVO_BLH_BDMASK ile çift yönlü telemetriyi açın.', 'Use DShot-capable ESCs and enable bidirectional telemetry with SERVO_BLH_BDMASK.',
       'استخدم ESC تدعم DShot وفعّل القياس ثنائي الاتجاه عبر SERVO_BLH_BDMASK.')),
 'fc_mount': dict(cause='vibration', chart='c_vibe', icon='🧷', params=[],
  title=('Uçuş kontrolcüsü yerinden oynadı', 'The flight controller moved', 'تحركت وحدة التحكم بالطيران'),
  rule=('Çift taraflı bant ya da sönümleyici gevşediğinde otopilot gövdeye göre döner; jiroskop ve ivmeölçer yanlış ölçer, titreşim aniden artar ve '
        'araç savrulur. Kırım sonrası FC\'nin yerinden çıkmış bulunması bu nedenin güçlü işaretidir.',
        'When the double-sided tape or dampers come loose the autopilot rotates relative to the frame; gyro and accelerometer read wrong, '
        'vibration jumps and the aircraft lurches. Finding the FC displaced after a crash is a strong hint.',
        'عندما يرتخي الشريط اللاصق المزدوج أو المخمدات تدور وحدة التحكم بالنسبة للهيكل؛ فيخطئ الجيروسكوب ومقياس التسارع ويرتفع الاهتزاز '
        'فجأة وتنحرف الطائرة. العثور على وحدة التحكم مزاحة بعد الحادث مؤشر قوي.'),
  look=('VIBE ani sıçrama, IMU ivme ekseninde kalıcı kayma, ATT Roll/Pitch sabit hatası.', 'VIBE sudden jump, permanent offset on an IMU accel axis, constant ATT Roll/Pitch error.',
        'قفزة مفاجئة في VIBE، وإزاحة دائمة على محور تسارع IMU، وخطأ ثابت في ATT Roll/Pitch.'),
  fix=('Üretici sönümleyicisini ya da uygun köpük/bant kullanın; kabloların FC\'yi çekmediğinden emin olun.', 'Use the manufacturer\'s damper or suitable foam/tape; make sure cables do not pull on the FC.',
       'استخدم مخمد المصنّع أو إسفنجاً/شريطاً مناسباً؛ وتأكد أن الكابلات لا تشد وحدة التحكم.')),
 'logging': dict(cause=None, chart='c_timeline', icon='📝', params=['LOG_BITMASK', 'LOG_DISARMED', 'INS_LOG_BAT_MASK'],
  title=('Doğru kayıt ayarı: teşhisin yarısı', 'Proper logging: half of the diagnosis', 'إعداد التسجيل الصحيح: نصف التشخيص'),
  rule=('Uzmanların sık cevabı: "Bu logda gerekli mesajlar yok." Varsayılan LOG_BITMASK, ham IMU, ESC ve PID kayıtlarını içermeyebilir; '
        'telemetri (.tlog) dosyası ise çok seyrek örneklenir. Her uçuşta .BIN kaydı alın ve sorun çıktığında aynı uçuşun tüm kaydını paylaşın.',
        'A frequent expert reply: "This log does not have the messages needed." The default LOG_BITMASK may not include raw IMU, ESC and PID '
        'records; telemetry (.tlog) files are sampled too sparsely. Record a .BIN for every flight and share the full log of the same flight when trouble happens.',
        'رد متكرر من الخبراء: "هذا السجل لا يحتوي الرسائل المطلوبة." قد لا يتضمن LOG_BITMASK الافتراضي سجلات IMU الخام وESC وPID؛ '
        'وملفات القياس عن بعد (.tlog) قليلة العينات. سجّل ملف .BIN لكل طيران وشارك السجل الكامل للطيران نفسه عند حدوث مشكلة.'),
  look=('Programın "Log içeriği" listesi: VIBE, RCOU, ESC, PIDR/PIDP, ISBH var mı?', 'The program\'s "Log contents" list: are VIBE, RCOU, ESC, PIDR/PIDP, ISBH present?',
        'قائمة "محتوى السجل" في البرنامج: هل توجد VIBE وRCOU وESC وPIDR/PIDP وISBH؟'),
  fix=('Ayar uçuşlarında LOG_BITMASK\'a PID ve IMU_RAW ekleyin, LOG_DISARMED=0 bırakın; SD kartın hızlı ve boş olduğundan emin olun.',
       'Add PID and IMU_RAW to LOG_BITMASK on tuning flights, keep LOG_DISARMED=0; make sure the SD card is fast and has free space.',
       'أضف PID وIMU_RAW إلى LOG_BITMASK في رحلات الضبط، واترك LOG_DISARMED=0؛ وتأكد أن بطاقة SD سريعة وبها مساحة.')),
 'vtol': dict(cause='motor', chart='c_motors', icon='🛩', params=['Q_ASSIST_SPEED', 'Q_TRANSITION_MS', 'Q_M_THST_HOVER'],
  title=('VTOL (QuadPlane): geçiş ve dikey motorlar', 'VTOL (QuadPlane): transitions and lift motors', 'VTOL ‏(QuadPlane): الانتقال ومحركات الرفع'),
  rule=('QuadPlane kırımlarında uzmanlar önce dikey motorlardan birinin doyup doymadığına bakar (ağır yük, kanat rüzgâr yüzeyi); sonra ileri uçuşa '
        'geçişte hava hızının yeterli olup olmadığına. Q_ASSIST_SPEED ayarlı değilse tutunma kaybında dikey motorlar yardıma gelmez.',
        'In QuadPlane crashes experts first check whether one lift motor saturated (heavy load, the wing catching wind), then whether airspeed '
        'was enough during the forward transition. Without Q_ASSIST_SPEED the lift motors do not help in a stall.',
        'في حوادث QuadPlane يتحقق الخبراء أولاً من تشبّع أحد محركات الرفع (حمل ثقيل، الجناح يلتقط الرياح)، ثم من كفاية السرعة الجوية أثناء '
        'الانتقال إلى الطيران الأمامي. بدون Q_ASSIST_SPEED لا تساعد محركات الرفع عند فقدان الرفع.'),
  look=('RCOU dikey motor kanalları, QTUN, ARSP Airspeed ve MODE geçişleri.', 'RCOU lift-motor channels, QTUN, ARSP Airspeed and MODE transitions.',
        'قنوات RCOU لمحركات الرفع، وQTUN، وARSP Airspeed، وانتقالات MODE.'),
  fix=('Dikey motorlarda %30 pay bırakın, Q_ASSIST_SPEED\'i ayarlayın, geçişi rüzgâra karşı ve yeterli irtifada yapın.',
       'Leave 30% headroom on lift motors, set Q_ASSIST_SPEED, transition into wind at a safe height.',
       'اترك هامش 30% لمحركات الرفع، واضبط Q_ASSIST_SPEED، ونفّذ الانتقال عكس الرياح وعلى ارتفاع آمن.')),
 'firmware': dict(cause=None, chart='c_timeline', icon='⬆', params=[],
  title=('Güncel kararlı sürüm', 'Current stable firmware', 'البرنامج الثابت المستقر الحالي'),
  rule=('Eski firmware sürümlerinde düzeltilmiş hatalar ve eksik güvenlik özellikleri vardır. Uzmanlar sorunu incelemeden önce çoğu zaman '
        'güncel kararlı sürüme geçmeyi ister; beta sürümle kırım yaşanırsa bunu geliştiricilere bildirmek önemlidir.',
        'Old firmware has bugs that were fixed and missing safety features. Experts often ask to move to the current stable release before '
        'investigating; if a crash happens on a beta, reporting it to the developers matters.',
        'تحتوي الإصدارات القديمة على أخطاء صُححت وتفتقر لميزات أمان. كثيراً ما يطلب الخبراء الترقية إلى الإصدار المستقر الحالي قبل التحقيق؛ '
        'وإذا وقع حادث على إصدار تجريبي فمن المهم إبلاغ المطورين.'),
  look=('MSG ilk satırları: ArduCopter/ArduPlane V4.x.x ve donanım adı.', 'First MSG lines: ArduCopter/ArduPlane V4.x.x and board name.',
        'أوائل أسطر MSG: ‏ArduCopter/ArduPlane V4.x.x واسم اللوحة.'),
  fix=('Parametreleri yedekleyip güncel kararlı sürümü yükleyin; sürüm notlarındaki değişen parametreleri okuyun.', 'Back up parameters and load the current stable firmware; read changed parameters in release notes.',
       'احفظ المعاملات احتياطياً وحمّل الإصدار المستقر الحالي؛ واقرأ المعاملات المتغيرة في ملاحظات الإصدار.')),
 'heat': dict(cause='motor', chart='c_esc', icon='🌡', params=['MOT_SPIN_MAX'],
  title=('Aşırı ısınma: motor, ESC, batarya', 'Overheating: motor, ESC, battery', 'السخونة الزائدة: المحرك وESC والبطارية'),
  rule=('Uçuştan sonra eli yakan motorlar çoğu zaman D terimine giren gürültünün (çentik filtresi eksik) ya da aşırı yükün işaretidir. Isınan ESC '
        'koruma moduna girip gücü keser; sıcak havada uzun askı uçuşları bunu tetikler.',
        'Motors too hot to touch after a flight usually mean noise entering the D term (missing notch filter) or overload. An overheating ESC '
        'enters protection and cuts power; long hovers in hot weather trigger it.',
        'المحركات الساخنة جداً بعد الطيران تعني غالباً ضجيجاً يدخل حد D (غياب مرشح Notch) أو حملاً زائداً. ESC الساخن يدخل وضع الحماية '
        'ويقطع الطاقة؛ والتحويم الطويل في الطقس الحار يحفز ذلك.'),
  look=('ESC Temp; RATE/PIDR D terimi gürültüsü; uçuş sonuna doğru tek bir motorun çıkışı yükseliyor mu?', 'ESC Temp; D-term noise in RATE/PIDR; does one motor\'s output climb toward the end?',
        'ESC Temp؛ ضجيج حد D في RATE/PIDR؛ هل يرتفع خرج محرك واحد قرب نهاية الطيران؟'),
  fix=('Çentik filtresi kurun, D kazancını düşürün, ESC\'lere hava akışı verin; ağır yükte daha büyük ESC kullanın.', 'Set up the notch, lower D, give ESCs airflow; use larger ESCs for heavy loads.',
       'اضبط مرشح Notch، وخفّض D، ووفّر تهوية لـ ESC؛ واستخدم ESC أكبر للأحمال الثقيلة.')),
 'baro': dict(cause='ekf', chart='c_alt', icon='🌬', params=['EK3_SRC1_POSZ', 'GND_EFFECT_COMP'],
  title=('Barometre: pervane rüzgârı, ışık ve yer etkisi', 'Barometer: prop wash, light and ground effect', 'البارومتر: تيار المراوح والضوء وتأثير الأرض'),
  rule=('Barometre köpükle korunmazsa pervane rüzgârı ve hız değişimleri basıncı bozar; AltHold\'da araç zıplar ya da iner. İnişe yakın yer etkisi '
        'baro yüksekliğini şaşırtır. Bazı kartlarda doğrudan güneş ışığı da baroyu etkiler.',
        'Without foam over the barometer, prop wash and speed changes disturb pressure; in AltHold the aircraft bounces or sinks. Near landing, '
        'ground effect confuses baro altitude. On some boards direct sunlight affects the baro too.',
        'بدون إسفنج فوق البارومتر يشوّش تيار المراوح وتغيرات السرعة الضغط؛ فتقفز الطائرة أو تهبط في AltHold. وقرب الهبوط يربك تأثير الأرض '
        'ارتفاع البارومتر. وفي بعض اللوحات يؤثر ضوء الشمس المباشر على البارومتر أيضاً.'),
  look=('BARO Alt, CTUN DAlt/Alt/BAlt; GPS Alt ile karşılaştırma; hızlanmada ani baro sıçraması.', 'BARO Alt, CTUN DAlt/Alt/BAlt; compare with GPS Alt; sudden baro jumps when accelerating.',
        'BARO Alt وCTUN DAlt/Alt/BAlt؛ قارن مع GPS Alt؛ قفزات مفاجئة للبارومتر عند التسارع.'),
  fix=('Baroyu açık hücreli köpükle örtün, ışıktan koruyun; kalkış ve inişte GND_EFFECT_COMP=1.', 'Cover the baro with open-cell foam, shield it from light; GND_EFFECT_COMP=1 for take-off and landing.',
       'غطِّ البارومتر بإسفنج مفتوح الخلايا واحمه من الضوء؛ وGND_EFFECT_COMP=1 للإقلاع والهبوط.')),
 'heli': dict(cause='control', chart='c_rcou', icon='🚁', params=['H_RSC_MODE', 'H_RSC_RUNUP_TIME', 'H_COL_MIN', 'H_COL_MAX'],
  title=('Helikopter: rotor devri ve kolektif ayarı', 'Helicopter: rotor speed and collective setup', 'المروحية: سرعة الدوار وضبط الخطوة الجماعية'),
  rule=('Helikopterde rotor tam devre ulaşmadan (run-up) kalkış ya da konum modu, kolektif aralığının yanlış ayarı ve swashplate kalibrasyonu en sık '
        'kırım nedenleridir. Yerde sallanma (ground resonance) da forumda sık görülür.',
        'On helicopters the most common crash causes are taking off or entering a position mode before rotor run-up completes, a wrong collective '
        'range and swashplate calibration. Ground resonance (shaking on the ground) is also common on the forum.',
        'في المروحيات أكثر أسباب الحوادث: الإقلاع أو الدخول في وضع موقع قبل اكتمال تسارع الدوار، وخطأ مدى الخطوة الجماعية، ومعايرة '
        'الصحن المتأرجح. كما يشيع في المنتدى الاهتزاز على الأرض (ground resonance).'),
  look=('RSC/HELI mesajları (rotor hızı, runup tamam), RCOU swash servoları, MODE değişimi.', 'RSC/HELI messages (rotor speed, runup complete), RCOU swash servos, MODE change.',
        'رسائل RSC/HELI (سرعة الدوار، اكتمال التسارع)، ومؤازرات الصحن في RCOU، وتغيير MODE.'),
  fix=('H_RSC_RUNUP_TIME\'ı rotor gerçek süresine göre ayarlayın, ilk kalkışı Stabilize\'de yapın, kolektifi ölçerek kalibre edin.',
       'Set H_RSC_RUNUP_TIME to the real rotor spool time, make the first take-off in Stabilize, calibrate collective with a gauge.',
       'اضبط H_RSC_RUNUP_TIME حسب زمن تسارع الدوار الفعلي، واجعل أول إقلاع في Stabilize، وعاير الخطوة الجماعية بمقياس.')),
}

# Uzmanların tek cümlelik altın kuralları (öğretici sayfanın başında)
GOLDEN = [
    ('Önce titreşim, sonra çentik filtresi, en son PID.', 'Vibration first, then the notch filter, PIDs last.', 'الاهتزاز أولاً، ثم مرشح Notch، والـ PID أخيراً.'),
    ('Bir motor tepeye vurmuşsa sorun ayarda değil itkidedir.', 'If a motor hits the top, the problem is thrust, not tuning.', 'إذا وصل محرك إلى الأقصى فالمشكلة في الدفع لا في الضبط.'),
    ('EKF hatası çoğu zaman sonuçtur; ilk bozulan sensörü arayın.', 'An EKF error is usually a consequence; look for the sensor that failed first.', 'خطأ EKF غالباً نتيجة؛ ابحث عن الحساس الذي اختلّ أولاً.'),
    ('Kayıt havada aniden bitiyorsa önce güç beslemesini düşünün.', 'If the log ends suddenly in the air, think of the power supply first.', 'إذا انتهى السجل فجأة في الجو ففكر أولاً في تغذية الطاقة.'),
    ('Stabilize\'e geçmeden önce gaz kolunu askı noktasına getirin.', 'Bring the throttle to hover before switching to Stabilize.', 'ارفع الخانق إلى نقطة التحويم قبل التبديل إلى Stabilize.'),
    ('İlk uçuş: Stabilize/AltHold, alçakta, kısa; konum modları sonra.', 'First flight: Stabilize/AltHold, low and short; position modes later.', 'أول طيران: Stabilize/AltHold، منخفضاً وقصيراً؛ وأوضاع الموقع لاحقاً.'),
    ('Kontrolleri kapatmak sorunu çözmez (ARMING_CHECK=1).', 'Disabling checks does not fix problems (ARMING_CHECK=1).', 'تعطيل الفحوص لا يحل المشاكل (ARMING_CHECK=1).'),
    ('Failsafe\'i yerde, verici kapatılarak test edin.', 'Test the failsafe on the ground by switching off the transmitter.', 'اختبر الحماية على الأرض بإطفاء جهاز الإرسال.'),
    ('Askı gazı %50 civarı olmalı; %70 üstü kontrol payı bırakmaz.', 'Hover throttle should be near 50%; above 70% leaves no control headroom.', 'يجب أن يكون خانق التحويم قرب 50%؛ وفوق 70% لا يترك هامش تحكم.'),
    ('Teşhis için .BIN kaydı, ESC telemetrisi ve ham IMU kaydı en iyi kanıttır.', 'A .BIN log, ESC telemetry and raw IMU logging are the best evidence.', 'سجل ‎.BIN وقياسات ESC وتسجيل IMU الخام أفضل الأدلة.'),
]

CAUSE_ORDER = ['motor', 'control', 'vibration', 'power', 'battery', 'compass', 'ekf', 'gps', 'radio', 'stall', 'pilot', None]


def txt(code, field, lg='tr'):
    v = L[code][field]
    return v[LI.get(lg, 1)] if isinstance(v, tuple) else v


def golden(lg='tr'):
    return [g[LI.get(lg, 1)] for g in GOLDEN]


def for_cause(cause):
    """Bir kök nedenle ilgili dersler (en ilgili önce)."""
    if cause == 'battery': extra = ['brownout']
    elif cause == 'power': extra = ['battery_sag', 'brownout']
    elif cause in ('compass', 'gps'): extra = ['ekf']
    elif cause == 'ekf': extra = ['vibe', 'compass_int', 'gps']
    elif cause == 'control': extra = ['vibe']
    elif cause == 'motor': extra = ['esc_telem']
    else: extra = []
    out = [k for k, v in L.items() if v['cause'] == cause]
    return out + [k for k in extra if k not in out]


_CASES = None


def cases():
    """{konu id: {'lessons': [...], 'experts': n, 'alt': [...]}} — gerçek forum konularının dersleri."""
    global _CASES
    if _CASES is None:
        try: _CASES = json.load(open(os.path.join(_D, 'expert_cases.json'), encoding='utf-8'))
        except Exception: _CASES = {'cases': {}, 'stats': {}}
    return _CASES


def case_lessons(cid):
    return (cases().get('cases') or {}).get(str(cid)) or {}


def stats():
    """{ders kodu: kaç konuda uzmanlar bu konuya değindi}"""
    return cases().get('stats') or {}


def html_for(cause, lg='tr', n=3, rt=None):
    """Analiz raporuna eklenen 'Uzmanlar ne diyor?' bölümü (HTML)."""
    ks = for_cause(cause)[:n]
    if not ks: return ''
    st = stats()
    head = rt or ('Uzmanlar ne diyor?', 'What do the experts say?', 'ماذا يقول الخبراء؟')[LI.get(lg, 1)]
    seen = ('{n} gerçek kırım konusunda geçti', 'came up in {n} real crash threads', 'ورد في {n} موضوع حادث حقيقي')[LI.get(lg, 1)]
    h = [f'<h3>🎓 {head}</h3>']
    for k in ks:
        c = st.get(k)
        h.append(f"<p><b>{L[k]['icon']} {txt(k, 'title', lg)}</b>" + (f" <i>({seen.format(n=c)})</i>" if c else '') + '<br>'
                 + txt(k, 'rule', lg) + '<br><b>🔎</b> ' + txt(k, 'look', lg) + '<br><b>🛠</b> ' + txt(k, 'fix', lg) + '</p>')
    return '\n'.join(h)
