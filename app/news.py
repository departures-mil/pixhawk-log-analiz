"""Sürüm notları ("Neler yeni" + release-notes.json). Yeni sürümde EN ÜSTE eklenir; tr/en/ar zorunlu."""

NEWS = [
    {'v': '1.1.7',
     'tr': 'Her değerin kaynağı: grafiklerdeki her çizgi logdaki MESAJ.ALAN adıyla (ör. RCOU.C3, ATT.Roll), eşik çizgileri parametre adı ve değeriyle (ör. Q_M_SPIN_MAX, BATT_CAPACITY) yazılı\n'
           'Her grafiğin altında kaynak şeridi: kullanılan log alanları ve bu logdaki parametre değerleri (rapora da girer)\n'
           'Yeni "Kaynak" sekmesi: her alanın ve parametrenin anlamı, değeri, varsayılanı ve Mission Planner\'da nerede bulunduğu (Review a Log / Full Parameter List)\n'
           'Tablolarda kaynak: sağlık özeti, temel bilgiler, uçuş aşamaları, mod tablosu ve motor olayları hangi alan ve parametreden okunuyor',
     'en': 'Source of every value: each chart line is labelled with its log MESSAGE.FIELD (e.g. RCOU.C3, ATT.Roll), limit lines with the parameter name and value (e.g. Q_M_SPIN_MAX, BATT_CAPACITY)\n'
           'A source strip under every chart: the log fields used and this log\'s parameter values (also in the report)\n'
           'New "Source" tab: meaning, value, default of each field and parameter and where to find it in Mission Planner (Review a Log / Full Parameter List)\n'
           'Sources in tables: health summary, key facts, flight phases, mode table and motor events show which field and parameter they come from',
     'ar': 'مصدر كل قيمة: كل خط في الرسوم موسوم باسم رسالة.حقل من السجل (مثل RCOU.C3 وATT.Roll)، وخطوط الحدود باسم المعامل وقيمته (مثل Q_M_SPIN_MAX وBATT_CAPACITY)\n'
           'شريط المصدر أسفل كل رسم: حقول السجل المستخدمة وقيم المعاملات في هذا السجل (ويظهر في التقرير أيضاً)\n'
           'تبويب "المصدر" الجديد: معنى كل حقل ومعامل وقيمته وقيمته الافتراضية ومكانه في Mission Planner (Review a Log / Full Parameter List)\n'
           'المصادر في الجداول: ملخص الصحة والمعلومات الأساسية ومراحل الطيران وجدول الأوضاع وأحداث المحركات تبيّن الحقل والمعامل المقروء منه'},
    {'v': '1.1.6',
     'tr': 'Güncelleme düzeltmesi: güncellerken açılan siyah "find" penceresi ve takılma giderildi; güncelleme arka planda sessizce biter ve program yeni sürümle açılır',
     'en': 'Update fix: the black "find" window that opened and hung during updating is gone; the update finishes silently in the background and the app reopens on the new version',
     'ar': 'إصلاح التحديث: أُزيلت نافذة "find" السوداء التي كانت تظهر وتتوقف أثناء التحديث؛ يكتمل التحديث بصمت في الخلفية ويُعاد فتح البرنامج بالإصدار الجديد'},
    {'v': '1.1.5',
     'tr': 'Uçuş modları her yerde: her mod kendi renginde bant, adı ve gerçek saatiyle; mod tablosu (başlangıç, bitiş, süre, değişim nedeni, modun ne yaptığı)\n'
           'Motor çıkışları sekmesi: motorlar yeriyle isimli (ör. M4 · Arka sağ), yerleşim çizimi, durma / tam güce kilitlenme uyarısı ve olay anı yakın çekimi\n'
           'Kanallar görevleriyle: Roll, Pitch, Yaw, Gaz (kanatçık, V kuyruk, elevon…); ters kanal işareti; kumanda stick hareketleri ve mod anahtarı grafiği\n'
           '20 grafik: özet panosu, hız ve rüzgâr, TECS, PID, navigasyon, GPS doğruluğu, titreşim spektrumu, IMU/baro, batarya mAh, ESC, EKF yenilikleri\n'
           'Grafikler etkileşimli: yakınlaştır, kaydır, PNG kaydet, imleçle harita/3B aynı ana gider, Shift+tıklama ile ölçüm cetveli\n'
           'Mission Planner sekmesi: Review Log alanları, ilgili ayarlar, önemli anların TimeUS değeri ve hazır grafik dosyası\n'
           'Harita moda göre renkli, 3B tekrarda mod renkli rota ve kumanda çubukları; raporda mod tablosu ve motor olayları',
     'en': 'Flight modes everywhere: each mode as a coloured band with its name and clock time; mode table (start, end, duration, reason, what the mode does)\n'
           'Motor outputs tab: motors named by position (e.g. M4 · Rear right), layout drawing, stopped / pinned-at-full-power warning and close-up of the event\n'
           'Channels by function: Roll, Pitch, Yaw, Throttle (aileron, V-tail, elevon…); reversed channel mark; transmitter stick movements and mode switch chart\n'
           '20 charts: summary dashboard, speed and wind, TECS, PID, navigation, GPS accuracy, vibration spectrum, IMU/baro, battery mAh, ESC, EKF innovations\n'
           'Interactive charts: zoom, pan, save PNG, cursor moves map/3D to the same moment, Shift+click measuring ruler\n'
           'Mission Planner tab: Review Log fields, related parameters, TimeUS of key moments and a preset graph file\n'
           'Map coloured by mode, 3D replay with mode-coloured track and sticks; mode table and motor events in the report',
     'ar': 'أوضاع الطيران في كل مكان: كل وضع شريط ملوّن باسمه ووقته الفعلي؛ جدول الأوضاع (البداية، النهاية، المدة، سبب التغيير، وظيفة الوضع)\n'
           'تبويب مخارج المحركات: المحركات مسماة حسب موقعها (مثل M4 · خلفي أيمن)، رسم التوزيع، تحذير التوقف أو العلوق عند القدرة القصوى ولقطة مقرّبة للحدث\n'
           'القنوات حسب الوظيفة: الدوران، الميلان، الانعراج، الخانق (الجنيح، ذيل V، الإليفون…)؛ علامة القناة المعكوسة؛ رسم حركات عصي التحكم ومفتاح الوضع\n'
           '20 رسماً: لوحة الملخص، السرعة والرياح، TECS، PID، الملاحة، دقة GPS، طيف الاهتزاز، IMU/البارومتر، mAh البطارية، ESC، ابتكارات EKF\n'
           'رسوم تفاعلية: تكبير، تحريك، حفظ PNG، المؤشر ينقل الخريطة وثلاثي الأبعاد إلى اللحظة نفسها، مسطرة قياس بـ Shift+نقر\n'
           'تبويب Mission Planner: حقول Review Log، المعاملات المرتبطة، قيمة TimeUS للحظات المهمة وملف رسوم جاهز\n'
           'الخريطة ملوّنة حسب الوضع، الإعادة ثلاثية الأبعاد بمسار ملوّن وعصي التحكم؛ جدول الأوضاع وأحداث المحركات في التقرير'},
    {'v': '1.1.4',
     'tr': 'Dört seviyeli karar: Kaza · Ciddi sorun · Küçük uyarı · Normal (küçük uyarılar artık kaza gibi gösterilmez)\n'
           'Kontrolsüz düşüş algılama (yükseklik kaybı, hız, açı) ve VTOL/çok motorlu araçta motor kaybı; motor numarası çıkış eşlemesinden\n'
           'İtki/ağırlık oranı, havada kalma gücü ve tahmini uçuş süresi; aynı aracın önceki uçuşlarıyla karşılaştırma\n'
           'Kalibre edilmiş güven yüzdesi (gerçek kazalarda ölçülen isabet); yapay zekâ yalnız log ölçümlerine dayanır\n'
           'Raporda resmî olay raporu bölümü (olay özeti, zaman çizelgesi, kök neden, öneriler, imza/onay)\n'
           'Bozuk son kayıtlı ve kurulu (armed) başlayan loglar doğru okunur',
     'en': 'Four-level verdict: Crash · Serious problem · Minor warning · Normal (minor warnings no longer look like crashes)\n'
           'Uncontrolled descent detection (height loss, speed, attitude) and motor loss on VTOL/multirotor; motor number from output mapping\n'
           'Thrust-to-weight, hover power and estimated endurance; comparison with the same aircraft\'s previous flights\n'
           'Calibrated confidence (hit rate measured on real crashes); AI explanations grounded only in log measurements\n'
           'Formal incident report section (summary, timeline, root cause, recommendations, signature/approval)\n'
           'Logs with a corrupt last record or starting already armed are read correctly',
     'ar': 'قرار بأربعة مستويات: تحطم · مشكلة خطيرة · تحذير بسيط · طبيعي (لم تعد التحذيرات البسيطة تظهر كتحطم)\n'
           'كشف الهبوط غير المتحكم به (فقدان الارتفاع، السرعة، الزاوية) وفقدان المحرك في VTOL ومتعدد المحركات؛ رقم المحرك من تعيين المخارج\n'
           'نسبة الدفع إلى الوزن وقدرة التحليق وزمن الطيران المتوقع؛ مقارنة مع الرحلات السابقة لنفس الطائرة\n'
           'نسبة ثقة معايرة (دقة مقاسة على حوادث حقيقية)؛ شروح الذكاء الاصطناعي تستند فقط إلى قياسات السجل\n'
           'قسم تقرير حادث رسمي (ملخص، تسلسل زمني، السبب الجذري، توصيات، توقيع/اعتماد)\n'
           'تُقرأ بشكل صحيح السجلات ذات السجل الأخير التالف أو التي تبدأ والطائرة مسلحة'},
    {'v': '1.1.3',
     'tr': 'Güncellemeler artık tamamen kendiliğinden: yeni sürüm arka planda sessizce indirilir, program kapanınca pencere açmadan kurulur; bir sonraki açılışta yeni sürüm gelir. Hemen kurmak için Güncelle → «Şimdi kur ve yeniden aç». Kurulum gereken güncellemeler de sessiz yapılır. Kayıtlara dokunulmaz.',
     'en': 'Updates are now fully automatic: the new version downloads quietly in the background and installs without any window when the program closes; the next start opens the new version. To install right away: Update → «Install now and reopen». Updates that need the installer also run silently. Records are not touched.',
     'ar': 'أصبحت التحديثات تلقائية بالكامل: يُنزَّل الإصدار الجديد بهدوء في الخلفية ويُثبَّت دون أي نافذة عند إغلاق البرنامج، ويُفتح الإصدار الجديد في المرة التالية. للتثبيت فوراً: تحديث ← «ثبّت الآن وأعد الفتح». التحديثات التي تحتاج إلى برنامج التثبيت تتم بصمت أيضاً. لا تُمَسّ السجلات.'},
    {'v': '1.1.2',
     'tr': 'Sürüm rozeti tam sürümü gösterir (v1.1.2)',
     'en': 'The version badge shows the full version (v1.1.2)',
     'ar': 'تعرض شارة الإصدار رقم الإصدار كاملاً (v1.1.2)'},
    {'v': '1.1.1',
     'tr': 'Daha gerçekçi teşhis: 326 gerçek kaza/uçuş loguyla ölçüldü (uzman yanıtlarıyla etiketli); doğruluk %86\n'
           '"Teşhis doğru muydu?" düğmesi: geri bildiriminiz teşhisleri geliştirir (kişisel veri gönderilmez)\n'
           'Kaçan kazalar: takla, uçuşta log kesilmesi, yön kontrolü kaybı; motor doygunluğu ve motor numarasıyla kanıt\n'
           'Sabit kanat: ters/yetersiz kumanda yüzeyi, ağırlık merkezi, hava hızı kalibrasyonu; batarya iç direnci, titreşim frekansı\n'
           'Eksik log kayıtları için uyarı ve güven yüzdesi; öğrenen ikinci görüş (ML)',
     'en': 'More realistic diagnosis: measured on 326 real crash/flight logs (expert-labelled); accuracy 86%\n'
           '"Was the diagnosis right?" button: your feedback improves diagnoses (no personal data sent)\n'
           'Missed crashes: flips, log cut in flight, yaw control loss; motor saturation with motor number as evidence\n'
           'Fixed wing: reversed/weak control surface, centre of gravity, airspeed calibration; battery internal resistance, vibration frequency\n'
           'Warning and confidence percentage for missing log data; learning second opinion (ML)',
     'ar': 'تشخيص أكثر واقعية: تم القياس على 326 سجل تحطم/طيران حقيقي (مصنفة من الخبراء)؛ الدقة 86%\n'
           'زر "هل كان التشخيص صحيحاً؟": ملاحظاتك تحسّن التشخيص (لا تُرسل بيانات شخصية)\n'
           'الحوادث الفائتة: الانقلاب، انقطاع السجل أثناء الطيران، فقدان التحكم في الانعراج؛ تشبع المحركات مع رقم المحرك كدليل\n'
           'الجناح الثابت: سطح تحكم معكوس/ضعيف، مركز الثقل، معايرة سرعة الهواء؛ المقاومة الداخلية للبطارية، تردد الاهتزاز\n'
           'تحذير ونسبة ثقة عند نقص بيانات السجل؛ رأي ثانٍ متعلم (تعلم آلي)'},
    {'v': '1.1.0',
     'tr': 'Yeni Falcon görünümü, renk şeması seçici (eski görünüm: Klasik), koyu/açık tema ve yazı boyutu\n'
           'Sağ üstte Eşitle · Wi-Fi · Güncelle · tema · dil | Küçült · Orta · Tam ekran · Kapat; program tam ekran açılır\n'
           'Güncelleme: yalnızca değişen kısımlar (yama), SHA-256 doğrulaması; yüzde, MB, kalan ve hız\n'
           'Eşitlemede hiçbir kayıt silinmez ya da ezilmez: uzak silme arşivlenir, çakışmada eski hal yedeğe alınır\n'
           'İlk açılış rehberi, "Neler yeni", Kullanım Limitleri (yapay zekâ çağrıları), otomatik hata raporu',
     'en': 'New Falcon look, colour scheme picker (previous look: Classic), dark/light theme and font size\n'
           'Top right: Sync · Wi-Fi · Update · theme · language | Minimize · Half · Full screen · Close; opens full screen\n'
           'Updates: changed parts only (patch), SHA-256 verified; percent, MB, remaining and speed\n'
           'Sync never deletes or overwrites a record: remote deletions are archived, the older side of a conflict is backed up\n'
           'First-run guide, "What\'s new", Usage limits (AI calls), automatic error reports',
     'ar': 'مظهر Falcon الجديد، منتقي أنظمة الألوان (المظهر السابق: الكلاسيكي)، سمة داكنة/فاتحة وحجم الخط\n'
           'أعلى اليمين: مزامنة · Wi-Fi · تحديث · السمة · اللغة | تصغير · نصف · ملء الشاشة · إغلاق؛ يفتح بملء الشاشة\n'
           'التحديث: الأجزاء المتغيرة فقط (رقعة) مع تحقق SHA-256؛ النسبة والميغابايت والمتبقي والسرعة\n'
           'المزامنة لا تحذف أي سجل ولا تستبدله: الحذف البعيد يُؤرشف، والنسخة الأقدم عند التعارض تُحفظ احتياطياً\n'
           'دليل التشغيل الأول، "ما الجديد"، حدود الاستخدام (استدعاءات الذكاء الاصطناعي)، تقارير الأخطاء التلقائية'},
]


def notes_for(v):
    for n in NEWS:
        if n['v'] == str(v):
            return {k: n[k] for k in ('tr', 'en', 'ar')}
    return None
