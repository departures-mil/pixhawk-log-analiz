"""Sürüm notları ("Neler yeni" + release-notes.json). Yeni sürümde EN ÜSTE eklenir; tr/en/ar zorunlu."""

NEWS = [
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
