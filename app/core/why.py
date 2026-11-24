"""'Neden düştü?' — kırım/sorunlu uçuş için tek cümlelik net hüküm, güven yüzdesi, kanıtlar, olay zinciri,
önlem ve uçuş bilgileri formuna (motor, gövde, otopilot) göre bağlama özel notlar. Offline çalışır;
internet varsa ai_explain() kullanıcının kendi YZ anahtarıyla açıklamayı güçlendirir."""
from __future__ import annotations
from . import texts

LI = {'tr': 0, 'en': 1, 'ar': 2}
CAUSE_DOM = {'gps': 'gps', 'ekf': 'ekf', 'battery': 'power', 'radio': 'rc', 'stall': 'airspeed', 'vibration': 'vibration',
             'compass': 'ekf', 'power': 'power', 'control': 'control', 'motor': 'motors'}
HARD = ('cr_stat', 'cr_err', 'cr_msg', 'cr_flip')

W = {
    'title_crash': ('Neden düştü?', 'Why did it crash?', 'لماذا تحطمت؟'),
    'title_inc': ('Ne oldu, neden?', 'What happened and why?', 'ماذا حدث ولماذا؟'),
    'sent_crash': ('{veh} {te} anında düştü. Ana neden: {cause}; ilk belirti {tc} anında görüldü.',
                   'The {veh} crashed at {te}. Main cause: {cause}; the first sign appeared at {tc}.',
                   'تحطمت {veh} عند {te}. السبب الرئيسي: {cause}؛ ظهرت أول علامة عند {tc}.'),
    'sent_inc': ('{veh} uçuşunda sorun yaşandı. Ana neden: {cause}; ilk belirti {tc} anında görüldü.',
                 'The {veh} had a problem in flight. Main cause: {cause}; the first sign appeared at {tc}.',
                 'واجهت {veh} مشكلة أثناء الطيران. السبب الرئيسي: {cause}؛ ظهرت أول علامة عند {tc}.'),
    'sent_unknown': ('{veh} {te} anında düştü, ancak logdaki veriler tek bir nedeni kesin göstermiyor.',
                     'The {veh} crashed at {te}, but the log data does not point to a single cause with certainty.',
                     'تحطمت {veh} عند {te}، لكن بيانات السجل لا تشير إلى سبب واحد بشكل قاطع.'),
    'chain': ('Olay zinciri', 'Chain of events', 'تسلسل الأحداث'),
    'conf': ('Güven', 'Confidence', 'الثقة'),
    'lvl_hi': ('yüksek', 'high', 'عالية'), 'lvl_mid': ('orta', 'medium', 'متوسطة'), 'lvl_lo': ('düşük', 'low', 'منخفضة'),
    'evid': ('Kanıtlar', 'Evidence', 'الأدلة'), 'todo': ('Ne yapmalı?', 'What to do?', 'ماذا تفعل؟'),
    'ctx': ('Uçağınıza özel notlar', 'Notes for your aircraft', 'ملاحظات خاصة بطائرتك'),
    'veh_def': ('araç', 'vehicle', 'المركبة'),
    # bağlam notları
    'n_ice_power': ('Benzinli motor: ani güç kaybında önce motor durmasını düşünün (yakıt, ateşleme modülü, buji, karbüratör ayarı, hava filtresi). ICE_ ve RPM loglarını kontrol edin.',
                    'Petrol engine: for a sudden loss of power, first suspect an engine stop (fuel, ignition module, spark plug, carburettor setting, air filter). Check ICE_ settings and RPM logs.',
                    'محرك بنزين: عند فقدان مفاجئ للقدرة اشتبه أولاً بتوقف المحرك (الوقود، وحدة الإشعال، الشمعة، ضبط المكربن، فلتر الهواء). راجع إعدادات ICE_ وسجلات RPM.'),
    'n_ice_vibe': ('Benzinli motorda titreşim eşikleri motor hacmine göre yükseltildi ({cc}). Yine de yüksek çıktıysa: motor takozları, pervane balansı ve uçuş kontrolcüsünün titreşim sönümleyicisini kontrol edin.',
                   'Vibration thresholds were raised for the petrol engine ({cc}). If still high: check engine mounts, propeller balance and the flight controller damping.',
                   'رُفعت عتبات الاهتزاز لمحرك البنزين ({cc}). إن بقيت مرتفعة: افحص قواعد المحرك وتوازن المروحة ومخمد وحدة التحكم.'),
    'n_ice_rf': ('Benzinli motor: ateşleme sistemi kumanda/GPS/pusulayı bozabilir. Ateşleme kablosunu ve modülünü alıcı, GPS ve otopilottan uzak tutun, ekranlı buji başlığı kullanın.',
                 'Petrol engine: the ignition system can disturb RC/GPS/compass. Keep the ignition lead and module away from the receiver, GPS and autopilot; use a shielded plug cap.',
                 'محرك بنزين: نظام الإشعال قد يشوش على الاستقبال/GPS/البوصلة. أبعد كابل ووحدة الإشعال عن المستقبل وGPS والطيار الآلي، واستخدم غطاء شمعة معزولاً.'),
    'n_elec_power': ('Elektrikli ({s}): hücre başı voltajı ve voltaj çökmesini (sag) kontrol edin; batarya kapasitesi ve C değeri yeterli mi?',
                     'Electric ({s}): check per-cell voltage and voltage sag; are battery capacity and C rating sufficient?',
                     'كهربائي ({s}): افحص جهد الخلية وهبوط الجهد؛ هل سعة البطارية ومعدل C كافيان؟'),
    'n_vtail': ('V kuyruk: karıştırma (SERVOx_FUNCTION 79/80) ve servo yönleri yerde kontrol edilmeli; yanlış yön kontrol kaybına yol açar.',
                'V-tail: verify mixing (SERVOx_FUNCTION 79/80) and servo directions on the ground; a reversed direction causes loss of control.',
                'ذيل V: تحقق من الخلط (SERVOx_FUNCTION 79/80) واتجاه السيرفوهات على الأرض؛ الاتجاه المعكوس يسبب فقدان السيطرة.'),
    'n_elevon': ('Uçan kanat / elevon: elevon karıştırma (SERVOx_FUNCTION 77/78), ağırlık merkezi ve servo yönleri kritik; ağırlık merkezi arkada ise kontrol kaybı olur.',
                 'Flying wing / elevon: elevon mixing (SERVOx_FUNCTION 77/78), CG and servo directions are critical; an aft CG leads to loss of control.',
                 'جناح طائر / إيليفون: خلط الإيليفون (SERVOx_FUNCTION 77/78) ومركز الثقل واتجاه السيرفوهات حرجة؛ مركز الثقل الخلفي يسبب فقدان السيطرة.'),
    'n_vtol': ('VTOL: geçiş (transition) anlarını inceleyin; Q_ASSIST_SPEED, Q_TRANSITION_MS ve ARSPD_FBW_MIN değerleri geçiş güvenliğini belirler.',
               'VTOL: review the transition moments; Q_ASSIST_SPEED, Q_TRANSITION_MS and ARSPD_FBW_MIN set transition safety.',
               'VTOL: راجع لحظات الانتقال؛ Q_ASSIST_SPEED وQ_TRANSITION_MS وARSPD_FBW_MIN تحدد أمان الانتقال.'),
    'n_tailsit': ('Tail-sitter: kalkış/iniş ve geçişte tutum kazançları (Q_A_*) ve Q_TAILSIT_* ayarları kritik.',
                  'Tail-sitter: attitude gains (Q_A_*) and Q_TAILSIT_* settings are critical in take-off, landing and transition.',
                  'تيل سيتر: معاملات الوضعية (Q_A_*) وإعدادات Q_TAILSIT_* حرجة في الإقلاع والهبوط والانتقال.'),
    'n_multi_motor': ('Çok motorlu ({a}): Motor Test ile motor sırası ve dönüş yönlerini, pervanelerin CW/CCW takılışını doğrulayın.',
                      'Multirotor ({a}): verify motor order, spin direction and CW/CCW props with Motor Test.',
                      'متعدد المراوح ({a}): تحقق من ترتيب المحركات واتجاه الدوران وتركيب المراوح CW/CCW عبر Motor Test.'),
    'n_no_aspd_stall': ('Hava hızı sensörü yok: stall, yer hızı ve sentetik hava hızı ile tahmin edildi; rüzgârda yanılabilir. Hava hızı sensörü takılması önerilir.',
                        'No airspeed sensor: stall was estimated from ground speed and synthetic airspeed, which can be wrong in wind. Fitting an airspeed sensor is recommended.',
                        'لا يوجد حساس سرعة جوية: قُدّر الانهيار من السرعة الأرضية والسرعة التركيبية وقد يخطئ مع الرياح. يُنصح بتركيب حساس سرعة جوية.'),
    'n_board_old': ('{b}: eski kart (izolasyonsuz IMU, 5 V beslemeye hassas). Titreşim sönümleme ve temiz 5 V güç modülü şart; güç sorunlarında POWR.Vcc değerine bakın.',
                    '{b}: older board (non-isolated IMU, sensitive to 5 V supply). Vibration damping and a clean 5 V power module are essential; check POWR.Vcc for power issues.',
                    '{b}: لوحة قديمة (IMU غير معزولة وحساسة لتغذية 5V). عزل الاهتزاز ووحدة طاقة 5V نظيفة ضروريان؛ راجع POWR.Vcc في مشاكل الطاقة.'),
    'n_board_cube': ('{b}: IMU titreşim izolasyonlu ve ısıtmalı; buna rağmen titreşim yüksekse kaynak gövde/motor/pervane tarafındadır.',
                     '{b}: the IMU is vibration-isolated and heated; if vibration is still high, the source is the airframe/motor/propeller.',
                     '{b}: وحدة IMU معزولة ومدفأة؛ إن بقي الاهتزاز مرتفعاً فالمصدر هو الهيكل/المحرك/المروحة.'),
    'n_board_small': ('{b}: küçük FC, IMU izolasyonu yok; yumuşak montaj ve iyi BEC beslemesi önemli.',
                      '{b}: small flight controller without IMU isolation; soft mounting and a good BEC supply are important.',
                      '{b}: وحدة تحكم صغيرة بلا عزل IMU؛ التركيب المرن وتغذية BEC جيدة أمران مهمان.'),
    'n_user_weak': ('Kırımı siz bildirdiniz ama logda çarpma izi zayıf: log çarpmadan önce kesilmiş olabilir. Logun son saniyeleri (güç, Vcc, mesajlar) kritik.',
                    'You reported a crash but the impact is barely visible: logging may have stopped before impact. The last seconds (power, Vcc, messages) are key.',
                    'أبلغت عن تحطم لكن أثر الاصطدام ضعيف: ربما توقف التسجيل قبل الاصطدام. الثواني الأخيرة (الطاقة، Vcc، الرسائل) حاسمة.'),
    'n_maiden': ('İlk uçuş: kırımların çoğu kurulum hatasından gelir (ters servo/motor, yanlış ağırlık merkezi, kalibrasyon). Ön uçuş kontrol listesini uygulayın.',
                 'Maiden flight: most crashes come from setup errors (reversed servo/motor, wrong CG, calibration). Use a pre-flight checklist.',
                 'الرحلة الأولى: معظم الحوادث تنتج عن أخطاء الإعداد (سيرفو/محرك معكوس، مركز ثقل خاطئ، معايرة). استخدم قائمة فحص ما قبل الطيران.'),
    'n_wx_gust': ('Hava: o saatte rüzgâr {w} m/s, hamleler {g} m/s idi. Ani rüzgâr hamlesi kontrol kaybına veya hız kaybına katkıda bulunmuş olabilir.',
                  'Weather: wind {w} m/s with gusts to {g} m/s at that hour. A sudden gust may have contributed to loss of control or speed.',
                  'الطقس: رياح {w} م/ث مع هبات حتى {g} م/ث في تلك الساعة. ربما ساهمت هبة مفاجئة في فقدان السيطرة أو السرعة.'),
    'n_wx_wind': ('Hava: o saatte yerden 10 m yükseklikte rüzgâr {w} m/s idi; bu araç için yüksek. İrtifada rüzgâr daha da güçlüdür.',
                  'Weather: wind at 10 m was {w} m/s at that hour, high for this vehicle. It is stronger at altitude.',
                  'الطقس: كانت الرياح على ارتفاع 10 م {w} م/ث، وهي مرتفعة لهذه المركبة، وتكون أقوى في الارتفاع.'),
    'n_wx_logwind': ('Logdan hesaplanan rüzgâr {w} m/s’ye ulaştı; aracın sınırlarına yakın.', 'Wind estimated from the log reached {w} m/s, near the vehicle limits.',
                     'بلغت الرياح المقدرة من السجل {w} م/ث، قريبة من حدود المركبة.'),
    'n_wx_rain': ('Hava: o saatte {p} mm yağış vardı. Su; ESC, alıcı, hava hızı borusu (pitot) ve konektörlerde arızaya yol açabilir.',
                  'Weather: {p} mm of precipitation at that hour. Water can cause failures in ESCs, receiver, pitot tube and connectors.',
                  'الطقس: هطول {p} مم في تلك الساعة. قد يسبب الماء أعطالاً في ESC والمستقبل وأنبوب بيتو والموصلات.'),
    'n_wx_ice': ('Hava: {t}°C ve %{rh} nem — buzlanma riski (pervane, kanat, pitot borusu). Hava hızı okuması bozulmuş olabilir.',
                 'Weather: {t}°C and {rh}% humidity — icing risk (propeller, wing, pitot tube). Airspeed readings may have been corrupted.',
                 'الطقس: {t}°م ورطوبة {rh}% — خطر التجمد (المروحة، الجناح، أنبوب بيتو). ربما تأثرت قراءات السرعة الجوية.'),
    'n_wx_carb': ('Benzinli motor + {t}°C ve %{rh} nem: karbüratör buzlanması riski; motor tekleyip durabilir.',
                  'Petrol engine + {t}°C and {rh}% humidity: carburettor icing risk; the engine may stumble and stop.',
                  'محرك بنزين + {t}°م ورطوبة {rh}%: خطر تجمد المكربن؛ قد يتعثر المحرك ويتوقف.'),
    'n_wx_hot': ('Hava: {t}°C — yüksek sıcaklık itkiyi azaltır, ESC/motor/batarya ısınır. Sıcaklık değerlerini kontrol edin.',
                 'Weather: {t}°C — high temperature reduces thrust and heats ESC/motor/battery. Check temperatures.',
                 'الطقس: {t}°م — الحرارة المرتفعة تقلل الدفع وتسخن ESC والمحرك والبطارية. افحص درجات الحرارة.'),
    'wx_line': ('Hava ({where}, {time} UTC): {temp}°C, rüzgâr {wind} m/s, hamle {gust} m/s, nem %{rh}, yağış {precip} mm',
                'Weather ({where}, {time} UTC): {temp}°C, wind {wind} m/s, gusts {gust} m/s, humidity {rh}%, precipitation {precip} mm',
                'الطقس ({where}، {time} UTC): {temp}°م، رياح {wind} م/ث، هبات {gust} م/ث، رطوبة {rh}%، هطول {precip} مم'),
    'wx_ev': ('kırım/olay noktası', 'crash/event point', 'نقطة التحطم/الحادث'), 'wx_home': ('kalkış noktası', 'take-off point', 'نقطة الإقلاع'),
    'n_mot_sat': ('Motor {m} itki kaybetti: komutu tavana dayandı, karşısındaki motor {o} dengelemek için tabana indi. Motor {m}, ESC\'si, kablosu ve pervanesini kontrol edin.',
                  'Motor {m} lost thrust: its command hit the ceiling while the opposite motor {o} was driven to the floor to compensate. Check motor {m}, its ESC, wiring and propeller.',
                  'فقد المحرك {m} الدفع: وصل أمره إلى الحد الأعلى بينما خُفِّض المحرك المقابل {o} إلى الحد الأدنى للتعويض. افحص المحرك {m} ومنظم سرعته وأسلاكه ومروحته.'),
    'n_mot_weak': ('Motor {m} kırımdan önceki saniyelerde diğerlerinden sürekli ~{g} µs daha yüksek çalıştı: o kolda itki eksik (motor/ESC, pervane, kol bükülmesi ya da motor eğikliği). Motor {m}, pervanesi ve kolu kontrol edilmeli.',
                  'In the seconds before the crash motor {m} ran consistently ~{g} µs higher than the others: that arm is short of thrust (motor/ESC, propeller, bent arm or tilted motor). Check motor {m}, its propeller and arm.',
                  'في الثواني التي سبقت التحطم عمل المحرك {m} باستمرار أعلى من غيره بنحو {g} ميكروثانية: هذا الذراع ينقصه الدفع (المحرك/منظم السرعة، المروحة، انحناء الذراع أو ميلان المحرك). افحص المحرك {m} ومروحته وذراعه.'),
    'n_mot_esc': ('ESC telemetrisi: motor {m} diğerleri dönerken durdu (devir sıfıra indi). ESC {m} (senkron kaçırma, aşırı ısınma, besleme) ve motor {m} kontrol edilmeli.',
                  'ESC telemetry: motor {m} stopped (RPM dropped to zero) while the others kept spinning. Check ESC {m} (desync, overheating, supply) and motor {m}.',
                  'قياس منظم السرعة: توقف المحرك {m} (انخفضت السرعة إلى الصفر) بينما استمرت المحركات الأخرى. افحص منظم السرعة {m} (فقدان التزامن، السخونة، التغذية) والمحرك {m}.'),
    'n_surf_rev': ('Kumanda yüzeyi ters ya da yetersiz ({s}): otopilot bir yöne dönmek istediğinde araç ters yöne döndü. Önce burnu/kanadı elle eğip FBWA modunda yüzeyin doğru yöne gittiğini kontrol edin (SERVOx_REVERSED); yön doğruysa servo hareket aralığını (SERVOx_MIN/MAX) ve mekanik bağlantıyı büyütün.',
                   'Control surface reversed or too weak ({s}): when the autopilot asked for one direction the aircraft rotated the other way. First tilt the aircraft by hand in FBWA and check the surface moves the right way (SERVOx_REVERSED); if it does, increase servo travel (SERVOx_MIN/MAX) and linkage throw.',
                   'سطح التحكم معكوس أو ضعيف ({s}): عندما طلب الطيار الآلي اتجاهاً دارت الطائرة في الاتجاه المعاكس. أمِل الطائرة يدوياً في وضع FBWA وتحقق من اتجاه السطح (SERVOx_REVERSED)؛ إن كان صحيحاً فزد مدى السيرفو (SERVOx_MIN/MAX) وحركة الوصلة.'),
    'n_ml': ('Öğrenen model görüşü (uzman etiketli gerçek kaza loglarıyla eğitildi): bu logun kaza logu olma olasılığı %{p}.',
             'Learning-model opinion (trained on expert-labelled real crash logs): probability that this is a crash log {p}%.',
             'رأي النموذج المتعلّم (مدرّب على سجلات حوادث حقيقية صنّفها خبراء): احتمال أن يكون هذا سجل حادث {p}%.'),
    'n_gaps': ('Bu logda teşhisi sınırlayan eksikler var: {g}. Daha kesin sonuç için LOG_BITMASK varsayılan değerine alınmalı (RCOU, VIBE, PID kayıtları) ve akım sensörü/ESC telemetrisi bağlanmalı.',
               'This log lacks data that limits the diagnosis: {g}. For a more certain result set LOG_BITMASK to default (RCOU, VIBE, PID logging) and connect a current sensor / ESC telemetry.',
               'يفتقر هذا السجل إلى بيانات تحد من التشخيص: {g}. لنتيجة أدق اضبط LOG_BITMASK على القيمة الافتراضية (تسجيل RCOU وVIBE وPID) ووصّل حساس التيار / قياس منظمات السرعة.'),
    'n_tuning': ('Ayar uçuşu: AUTOTUNE/PID değişiklikleri sırasında salınım kontrol kaybına dönüşebilir; ayarı yüksek irtifada ve geri alma planıyla yapın.',
                 'Tuning flight: during AUTOTUNE/PID changes oscillation can become loss of control; tune at a safe altitude with a bail-out plan.',
                 'رحلة ضبط: أثناء AUTOTUNE/تغيير PID قد يتحول التذبذب إلى فقدان سيطرة؛ اضبط على ارتفاع آمن مع خطة تراجع.'),
}


def w(key, lang, **a):
    s = W[key][LI.get(lang, 0)]
    try: return s.format(**a)
    except Exception: return s


def _end_t(A):
    ev = A.verdict.get('evidence') or []
    ts = [e['a']['t'] for e in ev if e.get('k') in HARD and isinstance(e.get('a'), dict) and 't' in e['a']]
    if ts: return min(ts)
    if A.flights: return A.flights[-1][1]
    return A.L.duration


def build(A):
    """Dil bağımsız sonuç: anahtarlar + sayılar. render() ile metne çevrilir."""
    v = A.verdict.get('kind')
    if v not in ('crash', 'incident'): return {}
    info = getattr(A, 'info', {}) or {}
    root = A.root or {}; c = root.get('cause') or 'unknown'
    ev = A.verdict.get('evidence') or []
    hard = any(e.get('k') in HARD for e in ev)
    score = A.verdict.get('score', 0) or 0
    conf = (0.55 if v == 'crash' else 0.45) + min(0.25, score / 400.0) + (0.1 if hard else 0)
    dom = CAUSE_DOM.get(c)
    if dom and (A.health.get(dom) or {}).get('status') == 'bad': conf += 0.1
    others = root.get('others') or []
    if c == 'unknown': conf = min(conf, 0.4)
    elif len(others) >= 3: conf -= 0.08          # çok aday: ayırt etmek zor
    if info.get('crashed') == 'yes' and v == 'crash': conf += 0.05
    if any(e.get('k') == 'cr_user_conflict' for e in ev): conf -= 0.15
    conf = max(0.2, min(0.97, conf))
    notes = []
    pw = info.get('power'); af = info.get('airframe'); ap = (info.get('autopilot') or '').lower()
    if pw in ('gas', 'glow', 'hybrid'):
        if c in ('power', 'battery', 'motor', 'control') or (c == 'unknown' and v == 'crash'): notes.append(('n_ice_power', {}))
        if c == 'vibration' or (A.health.get('vibration') or {}).get('status') in ('warn', 'bad'):
            notes.append(('n_ice_vibe', {'cc': (str(info.get('gas_cc')) + ' cc') if info.get('gas_cc') else '-'}))
        if c in ('radio', 'gps', 'compass', 'ekf'): notes.append(('n_ice_rf', {}))
    if pw == 'electric' and c in ('power', 'battery'): notes.append(('n_elec_power', {'s': (str(info.get('cells')) + 'S') if info.get('cells') else '-'}))
    if af == 'vtail' and c in ('control', 'stall', 'unknown'): notes.append(('n_vtail', {}))
    if af == 'elevon' and c in ('control', 'stall', 'unknown'): notes.append(('n_elevon', {}))
    if af in ('quadplane', 'tiltrotor'): notes.append(('n_vtol', {}))
    if af == 'tailsitter': notes.append(('n_tailsit', {}))
    if af in ('quad', 'hexa', 'octa', 'x8', 'y6', 'tri') and c in ('motor', 'control', 'unknown'):
        notes.append(('n_multi_motor', {'a': af}))
    mf = root.get('motor') or {}
    if c == 'motor' and mf.get('m'):
        if mf.get('kind') == 'esc': notes.insert(0, ('n_mot_esc', {'m': mf['m']}))
        elif mf.get('kind') == 'weak': notes.insert(0, ('n_mot_weak', {'m': mf['m'], 'g': mf.get('gap', '')}))
        elif mf.get('o'): notes.insert(0, ('n_mot_sat', {'m': mf['m'], 'o': mf['o']}))
        conf += 0.05
    if getattr(A, 'surf_rev', None) and c == 'control':
        notes.insert(0, ('n_surf_rev', {'s': A.surf_rev[1]})); conf += 0.15
    gaps = list(getattr(A, 'gaps', []) or [])
    if gaps:
        notes.append(('n_gaps', {'g': gaps}))
        crit = {'motor': ('gap_rcou', 'gap_esc'), 'unknown': ('gap_rcou', 'gap_vibe', 'gap_att_rate'), 'control': ('gap_att_rate', 'gap_pid'),
                'power': ('gap_curr',), 'battery': ('gap_curr',), 'vibration': ('gap_vibe',)}.get(c, ())
        conf -= 0.06 * sum(1 for x in gaps if x in crit)
    if info.get('airspeed') == 'no' and c == 'stall': notes.append(('n_no_aspd_stall', {}))
    if ap:
        b = info.get('autopilot')
        if 'pixhawk 1' in ap or '2.4.8' in ap or 'fmuv2' in ap or 'pixracer' in ap or 'omnibus' in ap:
            if c in ('power', 'vibration', 'ekf', 'unknown'): notes.append(('n_board_old', {'b': b}))
        elif 'cube' in ap:
            if c == 'vibration': notes.append(('n_board_cube', {'b': b}))
        elif any(x in ap for x in ('matek', 'kakute', 'speedybee')):
            if c in ('vibration', 'power', 'ekf'): notes.append(('n_board_small', {'b': b}))
    if any(e.get('k') == 'cr_user_weak' for e in ev): notes.append(('n_user_weak', {}))
    # hava durumu (kırım/olay anı ve konumu; yoksa kalkış) + logdan kestirilen rüzgâr
    wx = getattr(A, 'weather_event', None) or getattr(A, 'weather', None) or {}
    th = A.th or {}; wl = float(th.get('wind_warn', 10))
    def num(k):
        try: return float(wx.get(k))
        except (TypeError, ValueError): return None
    wind, gust, temp, rh, pr = num('wind'), num('gust'), num('temp'), num('rh'), num('precip')
    lw = (getattr(A, 'wind', None) or {}).get('max')
    wx_bad = False
    if gust is not None and gust > wl * 1.3: notes.append(('n_wx_gust', {'g': round(gust, 1), 'w': round(wind or 0, 1)})); wx_bad = True
    elif wind is not None and wind > wl: notes.append(('n_wx_wind', {'w': round(wind, 1)})); wx_bad = True
    if lw and lw > wl * 1.2: notes.append(('n_wx_logwind', {'w': round(lw, 1)})); wx_bad = True
    if pr is not None and pr >= 0.5: notes.append(('n_wx_rain', {'p': round(pr, 1)})); wx_bad = True
    if temp is not None and rh is not None and temp <= 3 and rh >= 75: notes.append(('n_wx_ice', {'t': round(temp), 'rh': round(rh)})); wx_bad = True
    if pw in ('gas', 'hybrid') and temp is not None and rh is not None and -5 <= temp <= 20 and rh >= 70:
        notes.append(('n_wx_carb', {'t': round(temp), 'rh': round(rh)}))
    if temp is not None and temp >= 38: notes.append(('n_wx_hot', {'t': round(temp)})); wx_bad = True
    if c == 'unknown' and wx_bad: conf = min(0.55, conf + 0.1)
    if info.get('purpose') == 'maiden': notes.append(('n_maiden', {}))
    if info.get('purpose') == 'tuning' and c in ('control', 'vibration', 'unknown'): notes.append(('n_tuning', {}))
    # kanıtlar: kırım kanıtı + neden alanının bulguları
    ev_items = [e for e in ev if e.get('k') not in ('cr_landed',)][:6]
    if dom and A.health.get(dom):
        ev_items += list(A.health[dom].get('findings') or [])[:3]
    conf = max(0.2, min(0.97, conf))
    wxs = {k: wx.get(k) for k in ('time_utc', 'temp', 'rh', 'wind', 'gust', 'dir', 'precip', 'cloud', 't')} if wx else {}
    mlp = getattr(A, 'ml_p', None)
    if mlp is not None: notes.append(('n_ml', {'p': int(round(mlp * 100))}))
    return {'wx': wxs, 'wx_event': bool(getattr(A, 'weather_event', None)), 'kind': v, 'cause': c, 'tc': float(root.get('t', _end_t(A)) or 0), 'te': float(_end_t(A)), 'conf': round(conf, 2),
            'hard': hard, 'evidence': ev_items, 'chain': root.get('chain') or [], 'notes': notes, 'others': others}


def vehicle_name(A, lang):
    info = getattr(A, 'info', {}) or {}
    if info.get('airframe') not in (None, '', 'unknown'):
        from .flightinfo import value_label
        return value_label('airframe', info['airframe'], lang)
    try:
        from .profiles import name
        return name(A.profile, lang)
    except Exception:
        return w('veh_def', lang)


def render(A, lang, tfmt):
    """Metin: {'title','sentence','conf_text','why','chain','evidence':[...],'prevent','notes':[...]}"""
    y = getattr(A, 'why', None) or {}
    if not y: return {}
    c = y['cause']; veh = vehicle_name(A, lang)
    if c == 'unknown':
        sent = w('sent_unknown', lang, veh=veh, te=tfmt(y['te']))
    else:
        cn = texts.T('cause_' + c, lang)
        sent = w('sent_crash' if y['kind'] == 'crash' else 'sent_inc', lang, veh=veh, te=tfmt(y['te']), tc=tfmt(y['tc']), cause=cn)
    cf = y['conf']; lvl = w('lvl_hi' if cf >= 0.8 else ('lvl_mid' if cf >= 0.6 else 'lvl_lo'), lang)
    chain = ' → '.join(f"{texts.chain_step(s, lang, tfmt)} ({tfmt(s['t'])})" for s in y['chain'] if s.get('step') != 'mode')
    whyt = texts.T('why_' + c, lang) if c != 'unknown' else ''
    prev = texts.T('prevent_' + c, lang) if c != 'unknown' else ''
    return {'title': w('title_crash' if y['kind'] == 'crash' else 'title_inc', lang), 'sentence': sent,
            'conf': cf, 'conf_text': f"{w('conf', lang)}: %{int(round(cf * 100))} ({lvl})", 'why': whyt, 'chain_h': w('chain', lang),
            'chain': chain, 'evid_h': w('evid', lang), 'evidence': [texts.render(e, lang, tfmt) for e in y['evidence']],
            'weather': (w('wx_line', lang, where=w('wx_ev' if y.get('wx_event') else 'wx_home', lang), time=y['wx'].get('time_utc') or '-',
                          **{k: ('-' if y['wx'].get(k) is None else y['wx'].get(k)) for k in ('temp', 'wind', 'gust', 'rh', 'precip')})
                        if y.get('wx') else ''),
            'todo_h': w('todo', lang), 'prevent': prev, 'ctx_h': w('ctx', lang), 'notes': [w(k, lang, **_na(a, lang)) for k, a in y['notes']]}


GAP_T = {'gap_rcou': ('motor çıkışları (RCOU)', 'motor outputs (RCOU)', 'مخارج المحركات (RCOU)'),
         'gap_vibe': ('titreşim (VIBE)', 'vibration (VIBE)', 'الاهتزاز (VIBE)'),
         'gap_att': ('tutum (ATT)', 'attitude (ATT)', 'الوضعية (ATT)'),
         'gap_att_rate': ('tutum kaydı 10 Hz altında', 'attitude logged below 10 Hz', 'تسجيل الوضعية أقل من 10 هرتز'),
         'gap_curr': ('batarya akımı', 'battery current', 'تيار البطارية'),
         'gap_pid': ('PID kaydı (PIDR/PIDP/PIDY)', 'PID logging (PIDR/PIDP/PIDY)', 'تسجيل PID (PIDR/PIDP/PIDY)'),
         'gap_esc': ('ESC telemetrisi (devir)', 'ESC telemetry (RPM)', 'قياس منظمات السرعة (الدوران)'),
         'gap_gps': ('GPS', 'GPS', 'GPS'),
         'surf_elev': ('irtifa dümeni', 'elevator', 'الرافع'), 'surf_ail': ('kanatçık', 'aileron', 'الجنيح')}


def _na(a, lang):
    a = dict(a)
    li = LI.get(lang, 0)
    if isinstance(a.get('g'), list):
        a['g'] = ', '.join(GAP_T.get(x, (x, x, x))[li] for x in a['g'])
    if a.get('s') in ('elev', 'ail'):
        a['s'] = GAP_T['surf_' + a['s']][li]
    if 'a' in a:
        from .flightinfo import value_label
        a['a'] = value_label('airframe', a['a'], lang)
    return a


def ai_explain(A, settings, usage, lang, tfmt):
    """İnternet varsa kullanıcının kendi YZ anahtarıyla net 'neden düştü' açıklaması (yoksa None)."""
    from . import ai as AI
    if not AI.available(settings): return None
    r = render(A, 'en', tfmt)
    if not r: return None
    from .flightinfo import rows
    from .advisor import LANG_NAME
    ctx = {'program_verdict': r['sentence'], 'confidence': r['conf_text'], 'chain': r['chain'], 'evidence': r['evidence'],
           'notes': r['notes'], 'operator_form': dict(rows(getattr(A, 'info', {}), 'en')),
           'health': {k: {'score': h['score'], 'status': h['status']} for k, h in A.health.items()},
           'facts': {k: v for k, v in A.facts.items() if isinstance(v, (int, float, str))}}
    import json
    prompt = (f'Write in {LANG_NAME.get(lang, "Turkish")} a clear, decisive "Why did it crash?" explanation for this ArduPilot flight. '
              'Start with ONE sentence verdict (cause + time). Then 3-6 bullet points of evidence with times, then the most likely physical '
              'failure, then numbered fix steps with exact parameter names. If the data is inconclusive say so and say what to check. '
              'Max 250 words. No tables.\n' + json.dumps(ctx, ensure_ascii=False, default=str)[:12000])
    return AI.chat(settings, usage, 'You are a senior ArduPilot accident investigator.', prompt, max_tokens=1500)
