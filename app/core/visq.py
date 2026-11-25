"""Görselli grafik yorumlama soruları (v1.1.11).

Bir uçuş analizinden (A) cevabı ele vermeyen grafikler çizer (charts.quiz: kırım çizgisi, karar kartı, motor olay işaretleri yok)
ve üç seviyede soru üretir:
  1 · okuma   : grafikteki değeri bul (en yüksek titreşim ekseni, en düşük hücre gerilimi, en az uydu, olay zamanı…)
  2 · yorum   : uçuş nasıl bitti, hangi motor ilk doyuma gitti, değer iyi mi kötü mü
  3 · teşhis  : kök neden ne + açık uçlu yorum (öğrenci yazar; anahtar kavramlarla otomatik puan önerisi, eğitimci son kararı verir)

Hazır havuz (app/data/visq.json + app/data/visq/*.png) gerçek ve uzman etiketli kırım / normal uçuş loglarından
tools_data/build_visq.py ile üretilir. Aynı fonksiyonlar programda açık logdan da soru üretir (görsel base64 gömülür).
"""
from __future__ import annotations
import base64, io, random
import numpy as np

LANGS = ('tr', 'en', 'ar')
TOPIC = 'charts'

CAUSES = {
    'motor': ('Motor / ESC / pervane arızası (itki kaybı)', 'Motor / ESC / propeller failure (loss of thrust)', 'عطل المحرك / ESC / المروحة (فقدان الدفع)'),
    'control': ('Kontrol / ayar (PID) sorunu, salınım', 'Control / tuning (PID) problem, oscillation', 'مشكلة التحكم / الضبط (PID)، تذبذب'),
    'vibration': ('Aşırı titreşim (IMU bozulması)', 'Excessive vibration (corrupted IMU)', 'اهتزاز مفرط (تلف قراءات IMU)'),
    'power': ('Güç / batarya (gerilim çökmesi)', 'Power / battery (voltage collapse)', 'الطاقة / البطارية (انهيار الجهد)'),
    'gps': ('GPS kaybı / hatalı konum', 'GPS loss / bad position', 'فقدان GPS / موقع خاطئ'),
    'ekf': ('EKF sapması (konum/açı kestirimi bozuldu)', 'EKF divergence (state estimate failed)', 'انحراف EKF (فشل تقدير الحالة)'),
    'compass': ('Pusula hatası / manyetik parazit', 'Compass error / magnetic interference', 'خطأ البوصلة / تداخل مغناطيسي'),
    'radio': ('Kumanda (RC) bağlantı kaybı', 'Radio (RC) link loss', 'فقدان اتصال جهاز التحكم (RC)'),
    'stall': ('Hız kaybı (stall)', 'Stall (loss of airspeed)', 'انهيار السرعة (stall)'),
}
# kök nedeni en iyi gösteren grafik
CHART_FOR = {'motor': 'c_motors', 'control': 'c_att', 'vibration': 'c_vibe', 'power': 'c_bat', 'gps': 'c_gps', 'ekf': 'c_ekf',
             'compass': 'c_mag', 'radio': 'c_sticks', 'stall': 'c_speed'}
LOOK = {  # grafikte nasıl görünür (açıklama + örnek cevap)
    'motor': ('Motor çıkışlarında bir kanal aniden en yükseğe (doyma) kilitleniyor ya da düşüyor; karşı motorlar dengelemek için azalıyor. Hemen ardından açı kontrolü kayboluyor ve irtifa düşüyor. Bu itki kaybının (motor, ESC, pervane, kablo) tipik izidir.',
              'One motor output suddenly pins at maximum (saturation) or drops while the opposite motors back off to compensate. Attitude control is lost right after and altitude falls. This is the typical trace of a loss of thrust (motor, ESC, propeller, wiring).',
              'يعلق أحد مخرجات المحركات فجأة عند الحد الأقصى (تشبع) أو ينخفض بينما تخفض المحركات المقابلة قدرتها للتعويض، ثم يُفقد التحكم في الوضعية ويهبط الارتفاع. هذا هو الأثر النموذجي لفقدان الدفع (محرك، ESC، مروحة، أسلاك).'),
    'control': ('İstenen açı (Des) ile gerçek açı birbirinden ayrılıyor, büyüyen salınımlar ya da sürekli bir fark var; motorlar/servolar doymadan önce kontrol bozuluyor. Bu ayar (PID), ağırlık merkezi ya da mekanik bir kontrol sorununu gösterir.',
                'Desired (Des) and actual attitude separate, with growing oscillations or a persistent gap; control degrades before the outputs saturate. This points to a tuning (PID), centre-of-gravity or mechanical control problem.',
                'تنفصل الزاوية المطلوبة (Des) عن الزاوية الفعلية مع تذبذبات متزايدة أو فرق مستمر، ويتدهور التحكم قبل تشبع المخرجات. يدل ذلك على مشكلة في الضبط (PID) أو مركز الثقل أو التحكم الميكانيكي.'),
    'vibration': ('VIBE değerleri 30 m/s² çizgisini sık sık aşıyor, 60\'a yaklaşıyor ve Clip sayacı artıyor; IMU ölçümleri doyuyor. Kestirim (EKF) bozulur, irtifa/konum tutulamaz. Pervane dengesi ve titreşim yalıtımı kontrol edilmeli.',
                  'VIBE values often exceed the 30 m/s² line, approach 60 and the Clip counter rises; the IMU saturates. The estimate (EKF) degrades and altitude/position cannot be held. Propeller balance and vibration isolation must be checked.',
                  'تتجاوز قيم VIBE خط 30 م/ث² كثيرًا وتقترب من 60 ويزداد عداد Clip، فتتشبع قراءات IMU ويتدهور التقدير (EKF) ولا يمكن تثبيت الارتفاع/الموقع. يجب فحص توازن المراوح وعزل الاهتزاز.'),
    'power': ('Batarya gerilimi yük altında hızla çöküyor (akım arttıkça gerilim derin düşüyor), BATT_LOW/CRT çizgilerinin altına iniyor ya da aniden kesiliyor. Motorlar yeterli itki üretemiyor. Batarya kapasitesi/iç direnci ve güç bağlantıları kontrol edilmeli.',
              'Battery voltage collapses under load (it drops deeply as current rises), falls below the BATT_LOW/CRT lines or cuts out suddenly. The motors cannot produce enough thrust. Check battery capacity/internal resistance and power connections.',
              'ينهار جهد البطارية تحت الحمل (ينخفض بشدة مع زيادة التيار) وينزل تحت خطي BATT_LOW/CRT أو ينقطع فجأة، فلا تنتج المحركات دفعًا كافيًا. يجب فحص سعة البطارية ومقاومتها الداخلية ووصلات الطاقة.'),
    'gps': ('Uydu sayısı düşüyor (6\'nın altına), HDOP yükseliyor (2\'nin üstüne); konum güvenilmez hâle geliyor ve konum tutan modlarda araç sürükleniyor. GPS anteni, parazit ve GPS failsafe ayarları incelenmeli.',
            'Satellite count drops (below 6) and HDOP rises (above 2); position becomes unreliable and the vehicle drifts in position-holding modes. Inspect the GPS antenna, interference and GPS failsafe settings.',
            'ينخفض عدد الأقمار (أقل من 6) ويرتفع HDOP (فوق 2)، فيصبح الموقع غير موثوق وتنجرف المركبة في الأوضاع التي تثبت الموقع. يجب فحص هوائي GPS والتداخل وإعدادات أمان GPS.'),
    'ekf': ('EKF tutarlılık oranları (SV, SP, SH, SM) 0,8 uyarı ve 1,0 sınırını aşıyor; kestirim sensörlerle uyuşmuyor. EKF failsafe tetiklenebilir ve araç konum/irtifa tutamaz. Hangi oranın önce yükseldiği (hız, konum, irtifa, manyetik) asıl sensörü gösterir.',
            'EKF innovation ratios (SV, SP, SH, SM) exceed the 0.8 warning and 1.0 limit; the estimate disagrees with the sensors. EKF failsafe may trigger and the vehicle cannot hold position/altitude. Which ratio rises first (velocity, position, height, magnetic) points to the culprit sensor.',
            'تتجاوز نسب اتساق EKF (SV وSP وSH وSM) حد التحذير 0.8 والحد 1.0، أي أن التقدير لا يتوافق مع الحساسات. قد يعمل أمان EKF ولا تستطيع المركبة تثبيت الموقع/الارتفاع. النسبة التي ترتفع أولًا (السرعة، الموقع، الارتفاع، المغناطيسي) تدل على الحساس المسبب.'),
    'compass': ('Manyetik alan büyüklüğü (|MAG|) gaz arttıkça değişiyor ya da sıçrıyor; yön (yaw) kestirimi bozuluyor, araç dairesel sürüklenme (toilet bowl) yapıyor. Pusula güç kablolarından uzaklaştırılmalı, compassmot ve kalibrasyon yapılmalı.',
                'Magnetic field magnitude (|MAG|) changes or jumps as throttle rises; the heading (yaw) estimate degrades and the vehicle circles (toilet bowl). Move the compass away from power wiring, run compassmot and recalibrate.',
                'يتغير مقدار المجال المغناطيسي (|MAG|) أو يقفز مع زيادة الخانق، فيتدهور تقدير الاتجاه (yaw) وتدور المركبة (toilet bowl). يجب إبعاد البوصلة عن أسلاك الطاقة وإجراء compassmot والمعايرة.'),
    'radio': ('Kumanda kanalları aniden donuyor ya da gaz kanalı failsafe değerine (ör. 975 µs) düşüyor; RC failsafe tetikleniyor. Araç ayarlı failsafe eylemini uygular ya da kontrolsüz kalır. Alıcı, anten ve FS_THR/THR_FS ayarları kontrol edilmeli.',
              'RC channels suddenly freeze or the throttle channel drops to its failsafe value (e.g. 975 µs); RC failsafe triggers. The vehicle performs the configured failsafe action or is left uncontrolled. Check the receiver, antenna and FS_THR/THR_FS settings.',
              'تتجمد قنوات جهاز التحكم فجأة أو تنخفض قناة الخانق إلى قيمة الأمان (مثل 975 µs) فيعمل أمان RC، وتنفذ المركبة إجراء الأمان المضبوط أو تبقى بلا تحكم. يجب فحص المستقبل والهوائي وإعدادات FS_THR/THR_FS.'),
    'stall': ('Hava hızı minimum hızın (AIRSPEED_MIN) altına iniyor, burun yukarıdayken irtifa artık artmıyor ve uçak bir kanadına yatarak düşüyor. Hız kontrolü (TECS), yük ve dönüş açıları incelenmeli.',
              'Airspeed falls below the minimum (AIRSPEED_MIN); with the nose up altitude stops increasing and the aircraft drops a wing and falls. Inspect speed control (TECS), loading and bank angles.',
              'تنخفض السرعة الجوية تحت الحد الأدنى (AIRSPEED_MIN)، ومع ارتفاع المقدمة يتوقف الارتفاع عن الزيادة وتميل الطائرة على أحد جناحيها وتسقط. يجب فحص التحكم بالسرعة (TECS) والحمولة وزوايا الانعطاف.'),
}
# açık uçlu yorumun anahtar kavram grupları (her grup: eş anlamlılar '|' ile; puan = bulunan grup / grup sayısı)
KW = {
    'motor': ('motor|esc|pervane|itki', 'doy|maks|en yüksek|tam güç|pwm|kilit|durdu|kesil', 'açı|denge|takla|kontrol kayb|düş'),
    'control': ('pid|ayar|tune|kazanç', 'salın|osilas|titre|fark|des|istenen', 'açı|roll|pitch|yatış|yunuslama'),
    'vibration': ('titreşim|vibe', '30|60|clip|doy|sınır', 'pervane|denge|yalıtım|imu|ekf'),
    'power': ('batarya|gerilim|voltaj|volt', 'düş|çök|sag|kesil|low|crt', 'akım|yük|kapasite|iç direnç'),
    'gps': ('gps|uydu', 'hdop|sats|6|düş|kayb', 'konum|sürük|glitch|failsafe'),
    'ekf': ('ekf', 'sv|sp|sh|sm|oran|innovation|0,8|0.8|1,0|1.0', 'konum|irtifa|sensör|failsafe|kestirim'),
    'compass': ('pusula|compass|mag|manyetik', 'parazit|kablo|gaz|akım|sıçra|değiş', 'yaw|yön|daire|toilet|kalibrasyon|compassmot'),
    'radio': ('rc|kumanda|alıcı|radyo', 'failsafe|kayb|kesil|975|don', 'fs_thr|thr_fs|anten|rtl'),
    'stall': ('hız|airspeed|stall|perdövites', 'airspeed_min|minimum|düş|kayb', 'kanat|irtifa|tecs|burun'),
    'normal': ('normal|sorunsuz|sağlıklı|iyi', 'irtifa|iniş|kalkış|gerilim|titreşim|uydu', 'sınır|eşik|30|6|uygun|düzgün'),
}
KW_EN = {
    'motor': ('motor|esc|prop|thrust', 'satur|max|full|pwm|pinned|stop|cut', 'attitude|balance|flip|control loss|fall'),
    'control': ('pid|tun|gain', 'oscillat|wobble|gap|desired|des', 'attitude|roll|pitch'),
    'vibration': ('vibrat|vibe', '30|60|clip|satur|limit', 'prop|balance|isolat|imu|ekf'),
    'power': ('battery|voltage|volt', 'drop|collapse|sag|cut|low|crt', 'current|load|capacity|resistance'),
    'gps': ('gps|satellite|sats', 'hdop|6|drop|loss', 'position|drift|glitch|failsafe'),
    'ekf': ('ekf', 'sv|sp|sh|sm|ratio|innovation|0.8|1.0', 'position|height|sensor|failsafe|estimate'),
    'compass': ('compass|mag', 'interfer|wire|throttle|current|jump|change', 'yaw|heading|circle|toilet|calibrat|compassmot'),
    'radio': ('rc|radio|receiver|transmitter', 'failsafe|loss|lost|975|freez', 'fs_thr|thr_fs|antenna|rtl'),
    'stall': ('airspeed|speed|stall', 'airspeed_min|minimum|drop|loss', 'wing|altitude|tecs|nose'),
    'normal': ('normal|healthy|good|fine|no problem', 'altitude|landing|takeoff|voltage|vibration|satellite', 'limit|threshold|30|6|ok|smooth'),
}
KW_AR = {
    'motor': ('محرك|esc|مروحة|دفع', 'تشبع|أقصى|pwm|توقف|انقطع', 'وضعية|توازن|انقلاب|فقدان التحكم|سقوط'),
    'control': ('pid|ضبط|كسب', 'تذبذب|فرق|المطلوب|des', 'زاوية|roll|pitch|ميل'),
    'vibration': ('اهتزاز|vibe', '30|60|clip|تشبع|حد', 'مروحة|توازن|عزل|imu|ekf'),
    'power': ('بطارية|جهد|فولت', 'انخفاض|انهيار|هبوط|انقطاع|low|crt', 'تيار|حمل|سعة|مقاومة'),
    'gps': ('gps|أقمار|قمر', 'hdop|6|انخفاض|فقدان', 'موقع|انجراف|glitch|أمان'),
    'ekf': ('ekf', 'sv|sp|sh|sm|نسبة|0.8|1.0', 'موقع|ارتفاع|حساس|أمان|تقدير'),
    'compass': ('بوصلة|compass|مغناطيس', 'تداخل|أسلاك|خانق|تيار|قفز|تغير', 'yaw|اتجاه|دوران|معايرة|compassmot'),
    'radio': ('rc|جهاز التحكم|مستقبل|راديو', 'أمان|فقدان|انقطاع|975|تجمد', 'fs_thr|thr_fs|هوائي|rtl'),
    'stall': ('سرعة|airspeed|stall|انهيار', 'airspeed_min|الحد الأدنى|انخفاض|فقدان', 'جناح|ارتفاع|tecs|مقدمة'),
    'normal': ('طبيعي|سليم|جيد|بدون مشكلة', 'ارتفاع|هبوط|إقلاع|جهد|اهتزاز|أقمار', 'حد|عتبة|30|6|مناسب|سلس'),
}
PREVENT = {
    'motor': ('Öneri: motor, ESC, pervane ve lehim/konnektörleri kontrol edin; itki/ağırlık oranının (T/W ≥ 2) yeterli olduğunu doğrulayın.',
              'Recommendation: inspect motors, ESCs, propellers and solder joints/connectors; confirm the thrust-to-weight ratio (T/W ≥ 2) is sufficient.',
              'التوصية: افحص المحركات وESC والمراوح ونقاط اللحام/الموصلات، وتأكد من كفاية نسبة الدفع إلى الوزن (T/W ≥ 2).'),
    'control': ('Öneri: ağırlık merkezini ve mekanik boşlukları kontrol edin, ardından AutoTune ya da elle PID ayarı yapın.',
                'Recommendation: check the centre of gravity and mechanical slop, then run AutoTune or tune the PIDs manually.',
                'التوصية: افحص مركز الثقل والارتخاء الميكانيكي ثم نفّذ AutoTune أو اضبط PID يدويًا.'),
    'vibration': ('Öneri: pervaneleri dengeleyin, uçuş kontrolcüsünü titreşim sönümleyici üzerine alın, gevşek parçaları sıkın.',
                  'Recommendation: balance the propellers, soft-mount the flight controller and tighten loose parts.',
                  'التوصية: وازن المراوح وثبّت وحدة التحكم على مخمدات اهتزاز وأحكم الأجزاء المرتخية.'),
    'power': ('Öneri: daha yüksek kapasiteli / C değerli batarya kullanın, BATT_LOW/CRT failsafe eşiklerini ayarlayın, güç kablolarını kontrol edin.',
              'Recommendation: use a higher capacity / C-rating battery, set the BATT_LOW/CRT failsafe thresholds and inspect power wiring.',
              'التوصية: استخدم بطارية بسعة / معدل C أعلى واضبط حدود أمان BATT_LOW/CRT وافحص أسلاك الطاقة.'),
    'gps': ('Öneri: GPS\'i açık gökyüzü gören, parazitten uzak bir yere alın; kalkış öncesi en az 10 uydu ve HDOP < 1,5 bekleyin.',
            'Recommendation: mount the GPS with a clear sky view away from interference; wait for at least 10 satellites and HDOP < 1.5 before takeoff.',
            'التوصية: ركّب GPS في مكان يرى السماء بعيدًا عن التداخل، وانتظر 10 أقمار على الأقل وHDOP < 1.5 قبل الإقلاع.'),
    'ekf': ('Öneri: önce yükselen orana karşılık gelen sensörü (GPS, baro, pusula, IMU) inceleyin; titreşim ve pusula paraziti en sık nedendir.',
            'Recommendation: inspect the sensor matching the ratio that rose first (GPS, baro, compass, IMU); vibration and compass interference are the most common causes.',
            'التوصية: افحص الحساس المقابل للنسبة التي ارتفعت أولًا (GPS، البارومتر، البوصلة، IMU)؛ الاهتزاز وتداخل البوصلة أكثر الأسباب شيوعًا.'),
    'compass': ('Öneri: harici pusulayı güç kablolarından uzaklaştırın, compassmot yapın, kalibrasyonu yenileyin.',
                'Recommendation: move the external compass away from power wiring, run compassmot and redo the calibration.',
                'التوصية: أبعد البوصلة الخارجية عن أسلاك الطاقة ونفّذ compassmot وأعد المعايرة.'),
    'radio': ('Öneri: alıcı antenlerini ve menzili kontrol edin, RC failsafe\'i (FS_THR_ENABLE / THR_FAILSAFE) RTL olarak ayarlayın.',
              'Recommendation: check receiver antennas and range, and set RC failsafe (FS_THR_ENABLE / THR_FAILSAFE) to RTL.',
              'التوصية: افحص هوائيات المستقبل والمدى واضبط أمان RC (FS_THR_ENABLE / THR_FAILSAFE) على RTL.'),
    'stall': ('Öneri: AIRSPEED_MIN ve TECS ayarlarını gözden geçirin, dönüşlerde yatış sınırını (ROLL_LIMIT_DEG) azaltın, hava hızı sensörünü kalibre edin.',
              'Recommendation: review AIRSPEED_MIN and TECS settings, reduce the bank limit (ROLL_LIMIT_DEG) in turns, calibrate the airspeed sensor.',
              'التوصية: راجع AIRSPEED_MIN وإعدادات TECS وقلّل حد الميل (ROLL_LIMIT_DEG) في الانعطافات وعاير حساس السرعة الجوية.'),
}

T = {
    'q_outcome': ('Özet panosunda karar kartı gizlendi. Grafiklere (irtifa, hız, gerilim, titreşim, uydu) bakarak bu uçuşun nasıl bittiğine karar verin.',
                  'The verdict card is hidden on the overview. Looking at the charts (altitude, speed, voltage, vibration, satellites), decide how this flight ended.',
                  'أُخفيت بطاقة القرار في لوحة الملخص. انظر إلى الرسوم (الارتفاع، السرعة، الجهد، الاهتزاز، الأقمار) وقرّر كيف انتهت هذه الرحلة.'),
    'o_normal': ('Normal uçuş: kontrollü iniş, değerler sınırlar içinde', 'Normal flight: controlled landing, values within limits', 'رحلة طبيعية: هبوط متحكم به والقيم ضمن الحدود'),
    'o_crash': ('Kırım: uçuş kontrol dışı bir düşüş / çarpmayla bitti', 'Crash: the flight ended in an uncontrolled fall / impact', 'حادث: انتهت الرحلة بسقوط / اصطدام غير متحكم به'),
    'e_normal': ('İrtifa kontrollü biçimde sıfıra iniyor, hız ve gerilim düzgün, titreşim ve uydu sayısı kabul edilebilir sınırlarda; ani kopma yok. Bu normal bir uçuş ve iniştir.',
                 'Altitude comes down to zero in a controlled way, speed and voltage are smooth, vibration and satellites stay within acceptable limits; there is no sudden break. This is a normal flight and landing.',
                 'ينزل الارتفاع إلى الصفر بشكل متحكم به، والسرعة والجهد سلسان، والاهتزاز وعدد الأقمار ضمن الحدود المقبولة، ولا يوجد انقطاع مفاجئ. هذه رحلة وهبوط طبيعيان.'),
    'e_crash': ('Uçuşun sonunda irtifa kontrolsüz biçimde düşüyor ya da veriler aniden kesiliyor; öncesinde değerlerden en az biri bozuluyor. Kırımın ilk belirtisini bulmak için olaydan geriye doğru bakın.',
                'At the end of the flight altitude falls uncontrolled or the data stops abruptly; at least one value goes wrong before that. Look backwards from the event to find the first sign of the crash.',
                'في نهاية الرحلة يهبط الارتفاع بلا تحكم أو تنقطع البيانات فجأة، وتفسد قيمة واحدة على الأقل قبل ذلك. انظر إلى الوراء من الحدث لتجد أول علامة على الحادث.'),
    'q_cause': ('Bu uçuş kırımla bitti. Grafiğe göre en olası kök neden hangisidir?', 'This flight ended in a crash. According to the chart, what is the most likely root cause?',
                'انتهت هذه الرحلة بحادث. وفقًا للرسم، ما السبب الجذري الأرجح؟'),
    'q_cause_i': ('Bu uçuşta bir arıza yaşandı ama araç kırım yapmadan indi. Grafiğe göre sorunun kaynağı hangisidir?',
                  'A fault occurred on this flight but the vehicle landed without crashing. According to the chart, what was the source of the problem?',
                  'حدث عطل في هذه الرحلة لكن المركبة هبطت دون حادث. وفقًا للرسم، ما مصدر المشكلة؟'),
    'q_mark': ('Programın gerçek analiz grafiği: olay kırmızıyla işaretlendi. İşarete ve değerlere bakarak ilk yapılması gereken nedir?',
               'The program\'s real analysis chart: the event is marked in red. Based on the mark and the values, what should be done first?',
               'رسم التحليل الحقيقي من البرنامج: الحدث مُعلَّم بالأحمر. بالنظر إلى العلامة والقيم، ما الذي يجب فعله أولًا؟'),
    'q_chain': ('Programın kararı ve kırım çizgisi görünüyor. Kırıma giden olay zincirini grafiklerden adım adım anlatın: ilk belirti ne, sonra ne oldu, neden?',
                'The program\'s verdict and crash line are visible. Describe the chain of events leading to the crash step by step from the charts: what was the first sign, what followed, why?',
                'يظهر قرار البرنامج وخط الحادث. اشرح خطوة بخطوة من الرسوم سلسلة الأحداث التي أدت إلى الحادث: ما أول علامة، وماذا تلاها، ولماذا؟'),
    'q_whyn': ('Program bu uçuşu "Normal" buldu (karar kartı görünüyor). Bu kararı destekleyen kanıtları grafiklerden yazın.',
               'The program judged this flight "Normal" (verdict card visible). Write the evidence from the charts that supports this verdict.',
               'حكم البرنامج على هذه الرحلة بأنها "طبيعية" (بطاقة القرار ظاهرة). اكتب من الرسوم الأدلة التي تدعم هذا الحكم.'),
    'q_open': ('Grafiği yorumlayın: ne görüyorsunuz, sorun (varsa) ne zaman ve neden başladı, ne önerirsiniz? Kısa bir paragraf yazın.',
               'Interpret the chart: what do you see, when and why did the problem (if any) start, what do you recommend? Write a short paragraph.',
               'فسّر الرسم: ماذا ترى، ومتى ولماذا بدأت المشكلة (إن وجدت)، وما توصيتك؟ اكتب فقرة قصيرة.'),
    'q_open_n': ('Bu grafiğe göre uçuşun sağlığını değerlendirin: hangi değerler sınırlar içinde, dikkat edilmesi gereken bir şey var mı? Kısa bir paragraf yazın.',
                 'Assess the health of the flight from this chart: which values are within limits, is there anything to watch? Write a short paragraph.',
                 'قيّم سلامة الرحلة من هذا الرسم: ما القيم الواقعة ضمن الحدود، وهل هناك ما يستدعي الانتباه؟ اكتب فقرة قصيرة.'),
    'q_vaxis': ('Titreşim grafiğinde uçuş boyunca hangi eksen en yüksek titreşimi gösteriyor?', 'On the vibration chart, which axis shows the highest vibration during the flight?',
                'في رسم الاهتزاز، أي محور يُظهر أعلى اهتزاز أثناء الرحلة؟'),
    'e_vaxis': ('Uçuş sırasında {a} ekseninin %95 değeri ≈ {v:.0f} m/s² (diğerleri: {o}). Çok kollu araçlarda Z genelde baskındır; X/Y baskınsa pervane dengesizliği ya da gevşek bağlantı düşünülür.',
                'In flight the 95th percentile of the {a} axis ≈ {v:.0f} m/s² (others: {o}). On multirotors Z is usually dominant; if X/Y dominates, think of prop imbalance or a loose mount.',
                'أثناء الطيران كانت قيمة المئين 95 للمحور {a} ≈ {v:.0f} م/ث² (الأخرى: {o}). في متعددة المراوح يكون Z عادةً هو الأعلى؛ وإذا غلب X/Y فكّر في عدم توازن المراوح أو تثبيت مرتخٍ.'),
    'q_vlevel': ('Titreşim (en yüksek eksen, uçuşun %95\'i) hangi bölgede?', 'In which band is the vibration (highest axis, 95% of the flight)?', 'في أي نطاق يقع الاهتزاز (أعلى محور، 95% من الرحلة)؟'),
    'vb': [('İyi: 15 m/s² altı', 'Good: below 15 m/s²', 'جيد: أقل من 15 م/ث²'), ('Kabul edilebilir: 15–30 m/s²', 'Acceptable: 15–30 m/s²', 'مقبول: 15–30 م/ث²'),
           ('Sınırda: 30–60 m/s²', 'Marginal: 30–60 m/s²', 'حدّي: 30–60 م/ث²'), ('Kötü: 60 m/s² üstü', 'Bad: above 60 m/s²', 'سيئ: أكثر من 60 م/ث²')],
    'e_vlevel': ('Ölçülen değer ≈ {v:.0f} m/s². ArduPilot kılavuzu: 30 m/s² altı uygundur, 30–60 arası sınırdadır, 60 üstü konum/irtifa kestirimini bozar.',
                 'Measured value ≈ {v:.0f} m/s². ArduPilot guidance: below 30 m/s² is fine, 30–60 is marginal, above 60 corrupts the position/altitude estimate.',
                 'القيمة المقيسة ≈ {v:.0f} م/ث². إرشادات ArduPilot: أقل من 30 م/ث² مناسب، و30–60 حدّي، وأكثر من 60 يفسد تقدير الموقع/الارتفاع.'),
    'q_cell': ('Uçuşta hücre başına en düşük batarya gerilimi hangi aralıkta? (toplam gerilim ÷ hücre sayısı, {n}S)', 'In flight, in which range is the lowest battery voltage per cell? (total voltage ÷ cell count, {n}S)',
               'أثناء الطيران، في أي نطاق يقع أدنى جهد للبطارية لكل خلية؟ (الجهد الكلي ÷ عدد الخلايا، {n}S)'),
    'cb': [('3,7 V üstü', 'Above 3.7 V', 'أكثر من 3.7 فولت'), ('3,5–3,7 V', '3.5–3.7 V', '3.5–3.7 فولت'), ('3,3–3,5 V', '3.3–3.5 V', '3.3–3.5 فولت'), ('3,3 V altı', 'Below 3.3 V', 'أقل من 3.3 فولت')],
    'e_cell': ('En düşük gerilim ≈ {v:.1f} V → {n} hücre için ≈ {c:.2f} V/hücre. LiPo için yük altında 3,5 V/hücre altı batarya sınırına, 3,3 V altı hasar ve güç kaybına işaret eder.',
               'Lowest voltage ≈ {v:.1f} V → ≈ {c:.2f} V/cell for {n} cells. For LiPo, below 3.5 V/cell under load means the battery is at its limit, below 3.3 V means damage and power loss.',
               'أدنى جهد ≈ {v:.1f} فولت ← ≈ {c:.2f} فولت/خلية لعدد {n} خلايا. في LiPo، أقل من 3.5 فولت/خلية تحت الحمل يعني أن البطارية عند حدها، وأقل من 3.3 فولت يعني تلفًا وفقدان طاقة.'),
    'q_sats': ('Uçuş sırasında en az kaç uydu görüldü?', 'What was the lowest satellite count during the flight?', 'ما أدنى عدد من الأقمار أثناء الرحلة؟'),
    'sb': [('12 ve üstü', '12 or more', '12 أو أكثر'), ('8–11', '8–11', '8–11'), ('5–7', '5–7', '5–7'), ('4 ve altı', '4 or fewer', '4 أو أقل')],
    'e_sats': ('En az {v:.0f} uydu, en yüksek HDOP ≈ {h:.1f}. 6\'nın altı ya da HDOP > 2 konumu güvenilmez kılar; kalkıştan önce ≥ 10 uydu beklenmelidir.',
               'At least {v:.0f} satellites, highest HDOP ≈ {h:.1f}. Below 6 or HDOP > 2 makes position unreliable; wait for ≥ 10 satellites before takeoff.',
               'الحد الأدنى {v:.0f} أقمار وأعلى HDOP ≈ {h:.1f}. أقل من 6 أو HDOP > 2 يجعل الموقع غير موثوق؛ انتظر ≥ 10 أقمار قبل الإقلاع.'),
    'q_att': ('Yatış (Roll) grafiğinde istenen açı ile gerçek açı arasındaki en büyük fark hangi aralıkta? (kırım anından önce)',
              'On the Roll chart, in which range is the largest gap between desired and actual angle? (before the crash moment)',
              'في رسم الميل (Roll)، في أي نطاق يقع أكبر فرق بين الزاوية المطلوبة والفعلية؟ (قبل لحظة الحادث)'),
    'ab': [('5° altı', 'Below 5°', 'أقل من 5°'), ('5–15°', '5–15°', '5–15°'), ('15–45°', '15–45°', '15–45°'), ('45° üstü', 'Above 45°', 'أكثر من 45°')],
    'e_att': ('En büyük fark ≈ {v:.0f}°. İyi ayarlı bir araçta fark birkaç dereceyi geçmez; 15° üstü süreklilik kontrol kaybının ya da yetersiz itkinin işaretidir.',
              'Largest gap ≈ {v:.0f}°. On a well-tuned vehicle the gap stays within a few degrees; a sustained gap above 15° indicates loss of control or insufficient thrust.',
              'أكبر فرق ≈ {v:.0f}°. في مركبة مضبوطة جيدًا لا يتجاوز الفرق بضع درجات؛ والفرق المستمر فوق 15° علامة على فقدان التحكم أو نقص الدفع.'),
    'q_ekf': ('EKF grafiğinde oranların (SV, SP, SH, SM) ulaştığı en yüksek değer hangi aralıkta?', 'On the EKF chart, in which range is the highest value reached by the ratios (SV, SP, SH, SM)?',
              'في رسم EKF، في أي نطاق تقع أعلى قيمة بلغتها النسب (SV وSP وSH وSM)؟'),
    'eb': [('0,5 altı (iyi)', 'Below 0.5 (good)', 'أقل من 0.5 (جيد)'), ('0,5–0,8', '0.5–0.8', '0.5–0.8'), ('0,8–1,0 (uyarı)', '0.8–1.0 (warning)', '0.8–1.0 (تحذير)'), ('1,0 üstü (sınır aşıldı)', 'Above 1.0 (limit exceeded)', 'أكثر من 1.0 (تجاوز الحد)')],
    'e_ekf': ('En yüksek oran {k} ≈ {v:.2f}. 0,8 uyarı, 1,0 sınırdır; sınır aşılırsa EKF o sensörün ölçümünü reddeder ve failsafe tetiklenebilir.',
              'Highest ratio {k} ≈ {v:.2f}. 0.8 is the warning and 1.0 the limit; above the limit the EKF rejects that sensor and failsafe may trigger.',
              'أعلى نسبة {k} ≈ {v:.2f}. 0.8 تحذير و1.0 حد؛ وعند تجاوزه يرفض EKF قياس ذلك الحساس وقد يعمل الأمان.'),
    'q_mot': ('Motor çıkışları grafiğinde ilk olarak hangi motor doyuma gitti ya da durdu?', 'On the motor outputs chart, which motor saturated or stopped first?',
              'في رسم مخرجات المحركات، أي محرك وصل إلى التشبع أو توقف أولًا؟'),
    'e_mot': ('{m} ({ch}) {t} anında {k}. Bir motorun tek başına en yükseğe kilitlenmesi o köşede itkinin yetmediğini (motor/ESC/pervane) gösterir; karşı motor ise dengelemek için azalır.',
              '{m} ({ch}) {k} at {t}. One motor pinned at maximum alone shows that corner lacks thrust (motor/ESC/prop); the opposite motor backs off to compensate.',
              '{m} ({ch}) {k} عند {t}. علوق محرك واحد عند الحد الأقصى يدل على نقص الدفع في تلك الزاوية (محرك/ESC/مروحة)، بينما يخفّض المحرك المقابل قدرته للتعويض.'),
    'q_when': ('Grafiklere göre kırım (kontrol kaybı / çarpma) yaklaşık ne zaman oldu? (yatay eksen dk:sn)', 'According to the charts, roughly when did the crash (loss of control / impact) happen? (horizontal axis mm:ss)',
               'وفقًا للرسوم، متى وقع الحادث (فقدان التحكم / الاصطدام) تقريبًا؟ (المحور الأفقي دقيقة:ثانية)'),
    'e_when': ('İrtifa ve diğer değerler ≈ {t} civarında bozuluyor ve veriler orada bitiyor/kopuyor. Analizde ilk adım olay anını bulmak, sonra o andan geriye doğru ilk anormal değeri aramaktır.',
               'Altitude and other values break down around ≈ {t} and the data ends/breaks there. The first step in analysis is to find the event time, then search backwards from it for the first abnormal value.',
               'يتدهور الارتفاع والقيم الأخرى عند ≈ {t} تقريبًا وتنتهي/تنقطع البيانات هناك. الخطوة الأولى في التحليل هي تحديد لحظة الحدث ثم البحث إلى الوراء عن أول قيمة غير طبيعية.'),
    'case_real': ('Gerçek uçuş logu ({v}), uzman etiketli', 'Real flight log ({v}), expert labelled', 'سجل رحلة حقيقي ({v})، مُصنّف من خبير'),
    'case_synth': ('Eğitim senaryosu ({v}), sentetik log', 'Training scenario ({v}), synthetic log', 'سيناريو تدريبي ({v})، سجل اصطناعي'),
    'case_open': ('Açık log: {n} (program teşhisine göre — kontrol edin)', 'Open log: {n} (from the program\'s diagnosis — please check)', 'السجل المفتوح: {n} (حسب تشخيص البرنامج — يرجى التحقق)'),
    'model_n': ('Değerler sınırlar içinde: {f}. Uçuş kontrollü bir inişle bitiyor; belirgin bir arıza izi yok.',
                'Values are within limits: {f}. The flight ends with a controlled landing; there is no clear sign of a fault.',
                'القيم ضمن الحدود: {f}. تنتهي الرحلة بهبوط متحكم به ولا توجد علامة واضحة على عطل.'),
}


def tri(x):
    if isinstance(x, dict): return {k: x.get(k, '') or '' for k in LANGS}
    return {k: (x[i] if i < len(x) else '') for i, k in enumerate(LANGS)}


def fmt(tup, **kw):
    return {lg: tup[i].format(**kw) for i, lg in enumerate(LANGS)}


def kw_groups(cause):
    """Üç dilde anahtar kavram grupları: {'tr': [...], 'en': [...], 'ar': [...]}"""
    return {'tr': list(KW.get(cause, ())), 'en': list(KW_EN.get(cause, ())), 'ar': list(KW_AR.get(cause, ()))}


# ------------------------------------------------------------------ görsel
def render(A, key, lang='en', max_w=1400, quiz=True):
    """Grafik → PNG baytları (renk paleti küçültülmüş). quiz=True: cevabı ele veren süsler yok; False: programın gerçek
    işaretli grafiği (kırım çizgisi, karar kartı, motor olayı). Yoksa None."""
    from . import charts as CH
    fn = dict(CH.ALL).get(key)
    if not fn: return None
    CH.quiz(quiz)
    try:
        png = fn(A, lang)
    except Exception:
        png = None
    finally:
        CH.quiz(False)
    if not png: return None
    return shrink(png, max_w)


def shrink(raw, max_w=1400, colors=96):
    """Görseli küçültür: genişlik sınırı + uyarlanabilir palet (grafiklerde metin keskin kalır)."""
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    if im.width > max_w: im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE).save(b, format='PNG', optimize=True)
    return b.getvalue()


def data_uri(raw):
    return 'data:image/png;base64,' + base64.b64encode(raw).decode()


# ------------------------------------------------------------------ ölçümler
def _flight_mask(A, t):
    m = np.zeros(len(t), bool)
    for a, b in (A.flights or []): m |= (t >= a) & (t <= b)
    return m if m.any() else np.ones(len(t), bool)


def facts(A):
    L = A.L; f = {}
    v = L.s('VIBE')
    if v.has('VibeZ'):
        m = _flight_mask(A, v['t'])
        p = {ax: float(np.nanpercentile(v['Vibe' + ax][m], 95)) for ax in 'XYZ' if v.has('Vibe' + ax) and m.any()}
        if p: f['vibe'] = p
    b = L.s('BAT')
    if b.has('Volt'):
        m = _flight_mask(A, b['t']) & (b['Volt'] > 1)
        if m.any():
            vmin = float(np.nanpercentile(b['Volt'][m], 0.5))
            cells = ((A.health or {}).get('power') or {}).get('metrics', {}).get('cells')
            if not cells:
                vmax = float(np.nanmax(b['Volt'][m])); cells = max(1, round(vmax / 4.0)) if vmax > 5 else None
            if cells: f['bat'] = {'vmin': vmin, 'cells': int(cells), 'cell': vmin / cells}
    g = L.s('GPS')
    if g.has('NSats'):
        m = _flight_mask(A, g['t'])
        if m.any():
            f['gps'] = {'min': float(np.nanmin(g['NSats'][m])), 'hdop': float(np.nanmax(np.clip(g['HDop'][m], 0, 99))) if g.has('HDop') else 0.0}
    a = L.s('ATT')
    if a.has('DesRoll'):
        t = a['t']; m = _flight_mask(A, t)
        if A.verdict.get('kind') == 'crash' and A.flights: m &= t <= A.flights[-1][1] - 1.0
        if m.any(): f['att'] = float(np.nanmax(np.abs(a['Roll'][m] - a['DesRoll'][m])))
    x = L.s('XKF4') if L.s('XKF4').has('SV') else L.s('NKF4')
    if x.has('SV'):
        m = _flight_mask(A, x['t'])
        if m.any():
            best = max(((k, float(np.nanmax(x[k][m]))) for k in ('SV', 'SP', 'SH', 'SM') if x.has(k)), key=lambda z: z[1])
            f['ekf'] = best
    try:
        from . import viz
        ev = viz.motor_events(A, 'en')
        r = next((e for e in ev['events'] if e.get('root')), None) or next((e for e in ev['events'] if e['kind'] == 'stop'), None)
        lift = [m for m in viz.motors(A, 'en') if m['kind'] == 'lift']
        if r and len(lift) >= 3:
            names = {lg: {m['ch']: viz_name(A, m['ch'], lg) for m in lift} for lg in LANGS}
            f['mot'] = {'ch': r['ch'], 'kind': r['kind'], 't': r['t'], 'names': names, 'chs': [m['ch'] for m in lift]}
    except Exception:
        pass
    if A.verdict.get('kind') == 'crash' and A.flights: f['crash_t'] = float(A.flights[-1][1])
    f['dur'] = float(A.L.duration or 0)
    return f


def viz_name(A, ch, lg):
    from . import viz
    m = next((x for x in viz.motors(A, lg) if x['ch'] == ch), None)
    return (m['name'] if m else ch)


def _band(v, edges):
    """edges artan sınırlar → bant indeksi (0..len(edges))"""
    for i, e in enumerate(edges):
        if v < e: return i
    return len(edges)


# ------------------------------------------------------------------ soru üretimi
def _mc(qid, level, q, opts, ans, exp, img, case, src='', hint=False):
    return {'id': qid, 'topic': TOPIC, 'level': level, 'src': src, 'type': 'mc', 'q': q, 'opts': [tri(o) for o in opts], 'ans': ans,
            'exp': exp, 'wexp': None, 'img': img, 'case': dict(case, hint=hint)}


def _open(qid, level, q, model, kw, img, case, src='', hint=False):
    return {'id': qid, 'topic': TOPIC, 'level': level, 'src': src, 'type': 'open', 'q': q, 'opts': [], 'ans': -1,
            'exp': model, 'model': model, 'kw': kw, 'img': img, 'case': dict(case, hint=hint)}


def _with_note(d, note):
    return {lg: (d.get(lg, '') + ('\n— ' + note[lg] if note and note.get(lg) else '')) for lg in LANGS}


def make(A, base_id, label=None, cause=None, kind='real', lang='en', name='', images=None):
    """A için görselli sorular. label/cause verilmezse programın kendi teşhisi kullanılır.
    images: {anahtar: bayt} — çizilen görseller buraya konur; soruların 'img' alanı '@anahtar' olur (çağıran yere göre çözer).
    → soru listesi"""
    from .analysis import fmt_t
    images = {} if images is None else images
    rnd = random.Random(base_id)
    if label is None: label = 'crash' if (A.verdict or {}).get('kind') == 'crash' else 'normal'
    if label in ('crash', 'incident') and cause is None: cause = (A.root or {}).get('cause')
    if cause == 'battery': cause = 'power'
    if cause not in CAUSES: cause = None
    veh = A.vehicle or ''
    case = {'label': label, 'cause': cause, 'kind': kind, 'veh': veh}
    note = fmt(T['case_' + kind], v=veh, n=name) if kind in ('real', 'synth', 'open') else None
    F = facts(A)
    out = []

    def img(key, quiz=True):
        k = f'{base_id}-{key[2:]}' + ('' if quiz else '-h')
        if k not in images:
            r = render(A, key, lang, quiz=quiz)
            if not r: return None
            images[k] = r
        return '@' + k

    ov = img('c_overview') or img('c_alt')
    if ov and label in ('crash', 'normal'):
        opts = [T['o_crash'], T['o_normal']]; a = 0 if label == 'crash' else 1
        exp = T['e_crash'] if label == 'crash' else T['e_normal']
        if label == 'crash' and cause: exp = {lg: tri(exp)[lg] + ' ' + tri(CAUSES[cause])[lg] + '.' for lg in LANGS}
        out.append(_mc(f'{base_id}-out', 2, tri(T['q_outcome']), opts, a, _with_note(tri(exp), note), ov, case, 'Overview'))
        if label == 'crash' and F.get('crash_t') and F['dur'] > 60:
            ct = F['crash_t']; d = F['dur']
            cands = [ct]
            for frac in (0.15, 0.35, 0.55, 0.8):
                x = frac * d
                if all(abs(x - c) > max(20, d * 0.1) for c in cands): cands.append(x)
            if len(cands) >= 3:
                cands = cands[:4]; rnd.shuffle(cands)
                ops = [tri((fmt_t(c)[:-2],) * 3) for c in cands]
                out.append(_mc(f'{base_id}-when', 1, tri(T['q_when']), ops, cands.index(ct),
                               _with_note(fmt(T['e_when'], t=fmt_t(ct)[:-2]), note), ov, case, 'Overview'))
    # kök neden grafiği
    ck = CHART_FOR.get(cause) if label in ('crash', 'incident') and cause else None
    ci = img(ck) if ck else None
    if ci:
        others = [c for c in CAUSES if c != cause and not (veh != 'Plane' and c == 'stall')]
        rnd.shuffle(others); ops = [cause] + others[:3]; rnd.shuffle(ops)
        exp = {lg: tri(LOOK[cause])[lg] + ' ' + tri(PREVENT[cause])[lg] for lg in LANGS}
        out.append(_mc(f'{base_id}-cause', 3, tri(T['q_cause' if label == 'crash' else 'q_cause_i']), [CAUSES[c] for c in ops], ops.index(cause), _with_note(exp, note), ci, case, ck))
        model = {lg: tri(LOOK[cause])[lg] + ' ' + tri(PREVENT[cause])[lg] for lg in LANGS}
        out.append(_open(f'{base_id}-open', 3, tri(T['q_open']), _with_note(model, note), kw_groups(cause), ci, case, ck))
    # okuma soruları
    if F.get('vibe') and (cause == 'vibration' or label == 'normal' or rnd.random() < 0.4):
        vi = img('c_vibe')
        if vi:
            p = F['vibe']; top = max(p, key=p.get)
            if len(p) == 3 and sorted(p.values())[-1] - sorted(p.values())[-2] > 2.0:
                axes = ['X', 'Y', 'Z']
                oth = ', '.join(f'{k} ≈ {v:.0f}' for k, v in p.items() if k != top)
                out.append(_mc(f'{base_id}-vax', 1, tri(T['q_vaxis']), [(a,) * 3 for a in axes], axes.index(top),
                               _with_note(fmt(T['e_vaxis'], a=top, v=p[top], o=oth), note), vi, case, 'VIBE.VibeX/Y/Z'))
            vmax = p[top]; bi = _band(vmax, (15, 30, 60))
            if min(abs(vmax - e) for e in (15, 30, 60)) > 2.5:
                out.append(_mc(f'{base_id}-vlv', 2, tri(T['q_vlevel']), T['vb'], bi, _with_note(fmt(T['e_vlevel'], v=vmax), note), vi, case, 'VIBE'))
    if F.get('bat') and (cause == 'power' or label == 'normal' or rnd.random() < 0.4):
        bi_ = img('c_bat')
        c = F['bat']['cell']
        if bi_ and 2.8 < c < 4.4 and min(abs(c - e) for e in (3.3, 3.5, 3.7)) > 0.04:
            bi = 3 - _band(c, (3.3, 3.5, 3.7))
            out.append(_mc(f'{base_id}-cell', 2, fmt(T['q_cell'], n=F['bat']['cells']), T['cb'], bi,
                           _with_note(fmt(T['e_cell'], v=F['bat']['vmin'], n=F['bat']['cells'], c=c), note), bi_, case, 'BAT.Volt'))
    if F.get('gps') and (cause == 'gps' or label == 'normal' or rnd.random() < 0.3):
        gi = img('c_gps'); s = F['gps']['min']
        if gi and s not in (4.0, 5.0, 7.0, 8.0, 11.0, 12.0):
            bi = 3 - _band(s, (4.5, 7.5, 11.5))
            out.append(_mc(f'{base_id}-sats', 1, tri(T['q_sats']), T['sb'], bi, _with_note(fmt(T['e_sats'], v=s, h=F['gps']['hdop']), note), gi, case, 'GPS.NSats'))
    if F.get('att') is not None and (cause in ('control', 'motor') or rnd.random() < 0.3):
        ai = img('c_att'); v = F['att']
        if ai and min(abs(v - e) for e in (5, 15, 45)) > 2:
            out.append(_mc(f'{base_id}-att', 2, tri(T['q_att']), T['ab'], _band(v, (5, 15, 45)), _with_note(fmt(T['e_att'], v=v), note), ai, case, 'ATT.Roll/DesRoll'))
    if F.get('ekf') and (cause in ('ekf', 'gps', 'compass') or rnd.random() < 0.2):
        ei = img('c_ekf'); k, v = F['ekf']
        if ei and min(abs(v - e) for e in (0.5, 0.8, 1.0)) > 0.04:
            out.append(_mc(f'{base_id}-ekf', 2, tri(T['q_ekf']), T['eb'], _band(v, (0.5, 0.8, 1.0)), _with_note(fmt(T['e_ekf'], k=k, v=v), note), ei, case, 'XKF4.SV/SP/SH/SM'))
    if F.get('mot') and cause == 'motor':
        mi = img('c_motors')
        if mi:
            M = F['mot']; chs = [c for c in M['chs'] if c != M['ch']]; rnd.shuffle(chs); chs = [M['ch']] + chs[:3]; rnd.shuffle(chs)
            kn = {'sat': ('doyuma gitti (en yüksek PWM)', 'saturated (maximum PWM)', 'وصل إلى التشبع (أقصى PWM)'), 'stop': ('durdu', 'stopped', 'توقف'),
                  'weak': ('zayıf kaldı', 'was weak', 'كان ضعيفًا')}.get(M['kind'], ('doyuma gitti', 'saturated', 'تشبع'))
            ops = [{lg: f"{M['names'][lg][c]} ({c})" for lg in LANGS} for c in chs]
            exp = {lg: T['e_mot'][i].format(m=M['names'][lg][M['ch']], ch=M['ch'], t=fmt_t(M['t'])[:-2], k=kn[i]) for i, lg in enumerate(LANGS)}
            out.append(_mc(f'{base_id}-mot', 2, tri(T['q_mot']), ops, chs.index(M['ch']), _with_note(exp, note), mi, case, 'RCOU'))
    # programın gerçek (işaretli) grafikleri: ipucu görünür, öğrenci işareti yorumlar
    if ck and ci:
        hi = img(ck, quiz=False)
        if hi:
            others = [c for c in CAUSES if c != cause]; rnd.shuffle(others); ops = [cause] + others[:3]; rnd.shuffle(ops)
            exp = {lg: tri(LOOK[cause])[lg] + ' ' + tri(PREVENT[cause])[lg] for lg in LANGS}
            out.append(_mc(f'{base_id}-mark', 2, tri(T['q_mark']), [PREVENT[c] for c in ops], ops.index(cause), _with_note(exp, note), hi, case, ck, True))
    if label == 'crash' and ov:
        ho = img('c_overview', quiz=False)
        if ho:
            model = {lg: tri(T['e_crash'])[lg] + (' ' + tri(LOOK[cause])[lg] + ' ' + tri(PREVENT[cause])[lg] if cause else '') for lg in LANGS}
            out.append(_open(f'{base_id}-chain', 3, tri(T['q_chain']), _with_note(model, note), kw_groups(cause or 'motor'), ho, case, 'Overview', True))
    # normal uçuş: açık uçlu sağlık değerlendirmesi
    if label == 'normal' and ov:
        bits = {lg: [] for lg in LANGS}
        if F.get('vibe'):
            v = max(F['vibe'].values())
            for i, lg in enumerate(LANGS): bits[lg].append((('titreşim ≈ %.0f m/s²', 'vibration ≈ %.0f m/s²', 'الاهتزاز ≈ %.0f م/ث²')[i]) % v)
        if F.get('bat'):
            for i, lg in enumerate(LANGS): bits[lg].append((('en düşük %.2f V/hücre', 'lowest %.2f V/cell', 'أدنى %.2f فولت/خلية')[i]) % F['bat']['cell'])
        if F.get('gps'):
            for i, lg in enumerate(LANGS): bits[lg].append((('en az %d uydu', 'at least %d satellites', 'على الأقل %d أقمار')[i]) % F['gps']['min'])
        model = {lg: T['model_n'][i].format(f=', '.join(bits[lg]) or '-') for i, lg in enumerate(LANGS)}
        out.append(_open(f'{base_id}-openn', 2, tri(T['q_open_n']), _with_note(model, note), kw_groups('normal'), ov, case, 'Overview'))
        ho = img('c_overview', quiz=False)
        if ho and rnd.random() < 0.6:
            out.append(_open(f'{base_id}-whyn', 2, tri(T['q_whyn']), _with_note(model, note), kw_groups('normal'), ho, case, 'Overview', True))
    return out


# ------------------------------------------------------------------ açık uçlu puanlama
def _norm(s):
    from .msgsearch import norm
    return norm(s or '')


def _kw_in(w, a, toks):
    """Kavram cevapta geçiyor mu: kısa sözcük ve sayılar tam sözcük olarak (60 içinde 6 sayılmaz), diğerleri kök olarak."""
    w = _norm(w).strip()
    if not w: return False
    if len(w) <= 3 or w.isdigit(): return w in toks
    return w in a


def score_open(answer, kw, lg=None):
    """Anahtar kavram gruplarına göre 0..1 puan önerisi (tüm dillerin grupları denenir, en iyisi alınır) ve bulunan gruplar."""
    import re
    a = ' ' + _norm(answer) + ' '
    if not a.strip(): return 0.0, []
    toks = set(re.findall(r'\w+', a))
    best = (0.0, [])
    for lg_, groups in (kw or {}).items():
        if not groups: continue
        hit = [g for g in groups if any(_kw_in(w, a, toks) for w in g.split('|'))]
        sc = len(hit) / len(groups)
        if groups[0] not in hit: sc = min(sc, 0.4)   # ana kavram (karar / kök neden) yoksa en çok yarım puan
        if sc > best[0]: best = (sc, hit)
    n = len(a.split())
    if n < 8: best = (best[0] * 0.5, best[1])   # çok kısa cevap: yarım puan
    return round(best[0], 2), best[1]


def suggest_points(sc):
    """Öneri puanı: 0, 0.5 ya da 1."""
    return 1.0 if sc >= 0.66 else (0.5 if sc >= 0.33 else 0.0)
