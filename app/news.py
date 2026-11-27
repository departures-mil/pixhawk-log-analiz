"""Sürüm notları ("Neler yeni" + release-notes.json). Yeni sürümde EN ÜSTE eklenir; tr/en/ar zorunlu."""

NEWS = [
    {'v': '1.1.14',
     'tr': 'Yeni "Log Gezgini" sayfası (Mission Planner\'daki "Review a Log" gibi): sağda logdaki bütün mesajlar ve alt alanları ağaç halinde (ATT ▸ Roll…, IMU[0]/[1], BAT[0], ESC[n]); işaretlediğiniz alan grafiğe eklenir, sol ya da sağ eksen seçilebilir, her alanın açıklaması ve birimi görünür\n'
           'Grafikte uçuş modu renk şeritleri, hatalar, MSG mesajları, olaylar ve parametre sınır çizgileri (hız, yatış, THR_MAX, batarya, servo/RC); veri tablosu, harita ve parametreler sekmeleri\n'
           'Hazır grafikler (genel, stall, TECS, servolar, geçiş, VTOL motorları, titreşim, batarya, GPS, RC) ve "Kırım anına git"\n'
           'Programın bulduğu sorunlu bölgeler grafikte işaretlenir; tıklayınca ne olduğu ve logda nereye bakılacağı yazar. "Uzman adımları" kök nedene göre logun nasıl okunacağını adım adım gösterir; "Alıştırma" kipinde teşhisi önce siz koyarsınız\n'
           '249 yeni gerçek log uzman yorumlarına göre etiketlendi (forumun Plane/QuadPlane kategorileri ve ArduPilot GitHub kayıtları dahil); toplam 659 ölçülebilir gerçek log, bunların 147\'si Plane\n'
           'Yeni teşhis kuralları: uçarken disarm düğmesiyle motorların kesilmesi pilot hatası olarak bulunur; Plane\'de log çarpmayla kesildiyse yanlışlıkla "güç kaybı" denmez\n'
           'Gerçek Kaza Logları kütüphanesi ve uzman dersleri yeni loglarla genişledi',
     'en': 'New "Log Browser" page (like "Review a Log" in Mission Planner): every message in the log and its fields as a tree on the right (ATT ▸ Roll…, IMU[0]/[1], BAT[0], ESC[n]); tick a field to add it to the chart, choose the left or right axis, and see each field\'s description and unit\n'
           'Flight mode colour bands, errors, MSG messages, events and parameter limit lines (speed, bank, THR_MAX, battery, servo/RC) on the chart; data table, map and parameters tabs\n'
           'Ready-made charts (overview, stall, TECS, servos, transition, VTOL motors, vibration, battery, GPS, RC) and "Go to crash"\n'
           'Problem regions found by the program are marked on the chart; click one to see what happened and where to look in the log. "Expert steps" walks you through reading the log for the root cause; in "Practice" mode you make the diagnosis first\n'
           '249 new real logs labelled from expert comments (including the forum\'s Plane/QuadPlane categories and ArduPilot GitHub issues); 659 measurable real logs in total, 147 of them Plane\n'
           'New diagnosis rules: cutting the motors with the disarm switch in flight is found as pilot error; on Plane, a log cut by impact is no longer mistaken for "power loss"\n'
           'The Real Crash Logs library and expert lessons grew with the new logs',
     'ar': 'صفحة جديدة "متصفح السجل" (مثل "Review a Log" في Mission Planner): جميع رسائل السجل وحقولها على شكل شجرة في اليمين (ATT ▸ Roll…، IMU[0]/[1]، BAT[0]، ESC[n])؛ حدّد حقلًا لإضافته إلى الرسم، واختر المحور الأيسر أو الأيمن، وشاهد وصف كل حقل ووحدته\n'
           'أشرطة ألوان أوضاع الطيران والأخطاء ورسائل MSG والأحداث وخطوط حدود المعاملات (السرعة، الميل، THR_MAX، البطارية، المؤازرات/RC) على الرسم؛ وتبويبات جدول البيانات والخريطة والمعاملات\n'
           'رسوم جاهزة (عام، انهيار السرعة، TECS، المؤازرات، الانتقال، محركات VTOL، الاهتزاز، البطارية، GPS، RC) و"اذهب إلى لحظة الحادث"\n'
           'تُعلَّم المناطق المشكلة التي وجدها البرنامج على الرسم؛ انقر عليها لترى ما حدث وأين تنظر في السجل. "خطوات الخبير" ترشدك خطوة بخطوة لقراءة السجل حسب السبب الجذري؛ وفي وضع "التمرين" تضع التشخيص أولًا\n'
           'وُسم 249 سجلًا حقيقيًا جديدًا حسب تعليقات الخبراء (بما في ذلك فئات Plane/QuadPlane في المنتدى وسجلات ArduPilot على GitHub)؛ 659 سجلًا حقيقيًا قابلًا للقياس إجمالًا، منها 147 لطائرات Plane\n'
           'قواعد تشخيص جديدة: قطع المحركات بمفتاح نزع التسليح أثناء الطيران يُكتشف كخطأ طيار؛ وفي Plane لم يعد انقطاع السجل بسبب الاصطدام يُعدّ خطأً "فقدان طاقة"\n'
           'توسعت مكتبة سجلات الحوادث الحقيقية ودروس الخبراء بالسجلات الجديدة'},
    {'v': '1.1.13',
     'tr': 'Gerçek Kaza Logları: sütun başlığına tıklayınca tablo o sütuna göre sıralanır, tekrar tıklayınca sıra tersine döner (MB sayısal sıralanır, boşlar sonda)\n'
           'Yeni süzgeçler, birlikte kullanılabilir: araç (yalnız Plane, yalnız Copter…), yalnız kırım ya da yalnız normal uçuş, kök neden (uzman teşhisine, program teşhisine, ikisinden birine ya da ikisinin aynı olduğuna göre), programın doğru bildiği ya da yanıldığı konular\n'
           '"Süzgeçleri temizle" ile hepsi tek tıkla sıfırlanır; seçili satırın uzman paneli her zaman o satırla eşleşir',
     'en': 'Real Crash Logs: click a column header to sort the table by that column, click again to reverse (MB sorts numerically, empty values last)\n'
           'New filters that work together: vehicle (Plane only, Copter only…), crashes only or normal flights only, root cause (by expert diagnosis, program diagnosis, either, or both agreeing), threads the program got right or wrong\n'
           '"Clear filters" resets everything in one click; the expert panel always matches the selected row',
     'ar': 'سجلات الحوادث الحقيقية: انقر على عنوان العمود لترتيب الجدول حسبه، وانقر مرة أخرى لعكس الترتيب (يُرتَّب MB رقميًا والقيم الفارغة في الأخير)\n'
           'عوامل تصفية جديدة تعمل معًا: المركبة (Plane فقط، Copter فقط…)، الحوادث فقط أو الرحلات الطبيعية فقط، السبب الجذري (حسب تشخيص الخبراء أو البرنامج أو أيهما أو عند اتفاقهما)، المواضيع التي أصاب فيها البرنامج أو أخطأ\n'
           '"مسح عوامل التصفية" يعيد كل شيء بنقرة واحدة؛ ولوحة الخبراء تطابق دائمًا الصف المحدد'},
    {'v': '1.1.12',
     'tr': 'Uzman tecrübeleri: ArduPilot forumundaki yüzlerce gerçek kırım konusunda deneyimli üyelerin ve geliştirici ekibin verdiği teşhis ve öğütler 32 derse ve 10 altın kurala dönüştürüldü (Türkçe, İngilizce, Arapça)\n'
           'Her ders: uzmanların kuralı, logda nereye bakılacağı, ne yapılacağı ve ilgili parametreler; uzmanların bu konuya kaç gerçek konuda değindiği de yazılır\n'
           'Gerçek Kaza Logları sayfası yenilendi: bir konuyu seçince uzman teşhisi, diğer olasılıklar, programın teşhisi ve o konudan çıkan dersler yanda görünür; derse göre filtreleyip gerçek örnekleri listeleyebilirsiniz\n'
           'Analiz özetinde "Uzmanlar ne diyor?" bölümü: bulunan kök nedenle ilgili uzman kuralları ve logda nereye bakılacağı\n'
           '136 yeni gerçek log uzman yorumlarına göre etiketlendi (toplam 461); teşhis kuralları iyileşti: doğruluk %86 → %89, normal uçuşu tanıma %70 → %85\n'
           'Yeni kök neden: pilot / kullanım hatası (gaz kolu dipteyken Stabilize\'e geçiş); kanıtsız küçük olaylar artık "ciddi" sayılmıyor\n'
           'Soru Bankası\'na "Uzman tecrübeleri" konusunda 96 yeni soru; eğitim kitabına "Uzman tecrübeleri" bölümü eklendi',
     'en': 'Expert experience: the diagnoses and advice given by experienced members and the development team in hundreds of real crash threads on the ArduPilot forum were turned into 32 lessons and 10 golden rules (Turkish, English, Arabic)\n'
           'Each lesson: the experts\' rule, where to look in the log, what to do and the related parameters; it also shows in how many real threads experts raised it\n'
           'Real Crash Logs page renewed: select a thread to see the expert diagnosis, other possibilities, the program\'s diagnosis and the lessons from that thread; filter by lesson to list real examples\n'
           '"What do the experts say?" in the analysis summary: expert rules for the root cause found and where to look in the log\n'
           '136 new real logs labelled from expert comments (461 in total); diagnosis rules improved: accuracy 86% → 89%, recognising normal flights 70% → 85%\n'
           'New root cause: pilot / handling error (switching to Stabilize with the throttle low); minor incidents without evidence are no longer rated "serious"\n'
           '96 new questions under "Expert experience" in the Question Bank; an "Expert experience" chapter in the training book',
     'ar': 'خبرة الخبراء: حُوِّلت التشخيصات والنصائح التي قدّمها الأعضاء ذوو الخبرة وفريق التطوير في مئات مواضيع الحوادث الحقيقية في منتدى ArduPilot إلى 32 درسًا و10 قواعد ذهبية (بالتركية والإنجليزية والعربية)\n'
           'كل درس: قاعدة الخبراء، وأين تنظر في السجل، وماذا تفعل، والمعاملات المعنية؛ ويُذكر أيضًا في كم موضوع حقيقي أشار إليه الخبراء\n'
           'تجديد صفحة سجلات الحوادث الحقيقية: اختر موضوعًا لترى تشخيص الخبراء والاحتمالات الأخرى وتشخيص البرنامج والدروس المستفادة منه؛ ويمكنك التصفية حسب الدرس لعرض أمثلة حقيقية\n'
           'قسم "ماذا يقول الخبراء؟" في ملخص التحليل: قواعد الخبراء للسبب الجذري المكتشف وأين تنظر في السجل\n'
           'وُسم 136 سجلًا حقيقيًا جديدًا حسب تعليقات الخبراء (461 إجمالًا)؛ وتحسنت قواعد التشخيص: الدقة من 86% إلى 89%، والتعرف على الرحلات الطبيعية من 70% إلى 85%\n'
           'سبب جذري جديد: خطأ الطيار / الاستخدام (التبديل إلى Stabilize والخانق في الأسفل)؛ ولم تعد الحوادث الصغيرة بلا أدلة تُعدّ "خطيرة"\n'
           '96 سؤالًا جديدًا في موضوع "خبرة الخبراء" في بنك الأسئلة؛ وفصل "خبرة الخبراء" في كتاب التدريب'},
    {'v': '1.1.11',
     'tr': 'Yeni "Sınav" sekmesi: sınav hazırlama, eğitimci ve öğrenci bölümleri tek yerde; soru sayısını siz seçersiniz, soruları tek tek ekleyebilir ya da "Otomatik doldur" diyebilirsiniz\n'
           'Görselli grafik soruları: gerçek kırım ve normal uçuşlardan 271 grafikle 391 soru; bir kısmında cevabı ele veren işaretler gizli, bir kısmında programın gerçek işaretli grafiği var; öğrencinin grafiği yorumlayıp yazdığı açık uçlu sorular da var. Açık logdan ya da senaryodan yeni görselli soru üretilebilir\n'
           'Kâğıt sınav: sınav kodlu soru kitapçığı, telefon kamerasıyla okunan QR\'lı cevap anahtarı ve optik form PDF olarak hazırlanır\n'
           'Optik okuma: formların fotoğrafını ya da taramasını seçin veya aynı Wi-Fi\'daki telefonla çekin; anında puanlanır ve öğrenci numarasıyla sınıf listesine eşlenir\n'
           'Telefonla sınav: öğrenciler aynı Wi-Fi\'da QR\'ı okutup sınav koduyla girer; cevaplar canlı izlenir, süre bitince teslim edilir\n'
           'Yorum soruları eğitimci tarafından 0 / 0,5 / 1 puanlanır (program anahtar kavramlara göre öneri verir); Soru Bankası ve Alıştırma Modu da görselli ve yorum sorularını destekler',
     'en': 'New "Exam" tab: exam building, instructor and student sections in one place; you choose the number of questions, add questions one by one or press "Auto-fill"\n'
           'Chart questions with images: 391 questions with 271 charts from real crash and normal flights; some hide the tell-tale marks, others show the program\'s real annotated chart; there are also open questions where the student writes an interpretation. New image questions can be generated from the open log or a scenario\n'
           'Paper exam: a coded question booklet, an answer key with a QR that a phone camera reads, and an answer sheet are produced as PDFs\n'
           'Answer-sheet scanning: pick photos or scans of the sheets, or shoot them with a phone on the same Wi-Fi; each is scored at once and matched to the class list by student number\n'
           'Phone exam: students on the same Wi-Fi scan the QR and enter with the exam code; answers are followed live and submitted when time runs out\n'
           'Interpretation answers are graded 0 / 0.5 / 1 by the instructor (the program suggests a score from key concepts); the Question Bank and Practice Mode also support image and interpretation questions',
     'ar': 'تبويب جديد "الاختبار": إعداد الاختبار وقسما المدرّب والطالب في مكان واحد؛ تختار عدد الأسئلة وتضيفها واحدًا واحدًا أو تضغط "ملء تلقائي"\n'
           'أسئلة الرسوم مع صور: 391 سؤالًا مع 271 رسمًا من رحلات حقيقية انتهت بحادث أو طبيعية؛ بعضها يخفي العلامات الدالة على الجواب وبعضها يعرض رسم البرنامج الحقيقي المعلَّم؛ وهناك أسئلة مفتوحة يكتب فيها الطالب تفسيره. ويمكن توليد أسئلة جديدة من السجل المفتوح أو من سيناريو\n'
           'الاختبار الورقي: كراسة أسئلة برمز الاختبار ومفتاح إجابة برمز QR تقرؤه كاميرا الهاتف وورقة إجابة ضوئية بصيغة PDF\n'
           'قراءة أوراق الإجابة: اختر صور الأوراق أو مسوحاتها أو صوّرها بهاتف على نفس شبكة Wi-Fi؛ تُصحَّح فورًا وتُطابَق مع قائمة الصف برقم الطالب\n'
           'الاختبار بالهاتف: يمسح الطلاب على نفس شبكة Wi-Fi رمز QR ويدخلون برمز الاختبار؛ تُتابَع الإجابات مباشرة وتُسلَّم عند انتهاء الوقت\n'
           'يصحّح المدرّب أسئلة التفسير 0 / 0.5 / 1 (ويقترح البرنامج درجة حسب المفاهيم الأساسية)؛ ويدعم بنك الأسئلة ووضع التدريب أيضًا أسئلة الصور والتفسير'},
    {'v': '1.1.10', 'tr': 'Yeni "Soru Bankası" sayfası: 529 soru — 16 konuda (temel, modlar, GPS, EKF, pusula, titreşim, güç, RC, motorlar, kontrol, uçak, kopter, VTOL, failsafe, analiz yöntemi, Mission Planner) 3 seviyede 126 öğretici soru, her şıkkın neden doğru / yanlış olduğunu anlatan açıklamalarla; ayrıca log mesajı ve kritik parametre kütüphanelerinden üretilen sorular\nBankanın tamamı görülebilir ve düzenlenebilir: üç dilde arama, konu / seviye / tür süzgeci, yeni soru ekle, düzenle, kopyala, sil, hazır soruya geri dön; .pxbank olarak dışa / içe aktar; değişiklikler diğer cihazlarla eşitlenir\nAlıştırma Modu yenilendi: kaynak (karışık / soru bankası / açık log / yanlışlarımı tekrar et), konu, seviye ve soru sayısı seçilir; her sorunun konusu, seviyesi ve kaynağı gösterilir\nSınav ve Sertifika: sınavlar artık soru bankasından (isteğe bağlı açık logla karışık) konu ve seviye seçilerek 3–100 soruyla hazırlanabilir', 'en': 'New "Question Bank" page: 529 questions — 126 tutorial questions in 16 topics (basics, modes, GPS, EKF, compass, vibration, power, RC, motors, control, plane, copter, VTOL, failsafe, analysis method, Mission Planner) at 3 levels, with explanations of why each option is right or wrong; plus questions generated from the log message and critical parameter libraries\nThe whole bank can be viewed and edited: search in three languages, topic / level / type filters, add, edit, duplicate, delete, revert to the built-in question; export / import as .pxbank; changes sync to your other devices\nPractice Mode renewed: choose source (mixed / question bank / open log / review my mistakes), topic, level and number of questions; each question shows its topic, level and source\nExam & Certificate: exams can now be built from the question bank (optionally mixed with the open log) by topic and level, with 3–100 questions', 'ar': 'صفحة جديدة "بنك الأسئلة": 529 سؤالاً — 126 سؤالاً تعليمياً في 16 موضوعاً (الأساسيات، الأوضاع، GPS، EKF، البوصلة، الاهتزاز، الطاقة، RC، المحركات، التحكم، الطائرة، المروحية، VTOL، الأمان، منهجية التحليل، Mission Planner) بثلاثة مستويات مع شرح سبب صحة أو خطأ كل خيار؛ إضافة إلى أسئلة مولّدة من مكتبتي رسائل السجل والمعاملات الحرجة\nيمكن عرض البنك كاملاً وتعديله: بحث باللغات الثلاث، تصفية حسب الموضوع / المستوى / النوع، إضافة سؤال جديد وتعديله ونسخه وحذفه والعودة إلى السؤال الجاهز؛ تصدير / استيراد بصيغة .pxbank؛ وتُزامَن التغييرات مع أجهزتك الأخرى\nتجديد وضع التدريب: اختيار المصدر (مختلط / بنك الأسئلة / السجل المفتوح / مراجعة أخطائي) والموضوع والمستوى وعدد الأسئلة؛ ويُعرض موضوع كل سؤال ومستواه ومصدره\nالاختبار والشهادة: يمكن الآن إنشاء الاختبارات من بنك الأسئلة (مع السجل المفتوح اختيارياً) حسب الموضوع والمستوى بعدد 3–100 سؤال'},
    {'v': '1.1.9',
     'tr': 'Log Mesajları Kütüphanesi araması güçlendi: yalnız mesaj ve alan adlarında değil, açıklamalarda ve alan açıklamalarında da arar; Türkçe, İngilizce ve Arapça çevirilerin üçünde birden\n'
           'Harf/aksan duyarsız (titresim = titreşim) ve eş anlamlılarla (gerilim = voltaj = voltage, pusula = compass…); çok kelimeli aramada hepsini içerenler en üstte\n'
           'Listede eşleşen alanlar gösterilir (ör. VIBE ↳ VibeX, VibeY); ayrıntıda aranan kelimeler sarıyla vurgulanır, eşleşen alan satırları işaretlenir ve kelime başka dilde bulunduysa o dildeki açıklama da yazılır',
     'en': 'Stronger Log Messages Library search: it looks not only in message and field names but in descriptions and field descriptions too, in Turkish, English and Arabic at once\n'
           'Accent-insensitive (titresim = titreşim) with synonyms (voltage = gerilim = voltaj, compass = pusula…); with several words, messages containing all of them come first\n'
           'The list shows the matching fields (e.g. VIBE ↳ VibeX, VibeY); the details highlight the searched words, mark matching field rows and show the description in the language where the word was found',
     'ar': 'بحث أقوى في مكتبة رسائل السجل: لا يبحث في أسماء الرسائل والحقول فقط بل في الشروح وشروح الحقول أيضاً، باللغات التركية والإنجليزية والعربية معاً\n'
           'لا يتأثر بالتشكيل والحروف الخاصة (titresim = titreşim) ويدعم المرادفات (الجهد = voltage = gerilim، البوصلة = compass…)؛ وعند البحث بعدة كلمات تظهر الرسائل التي تحويها كلها أولاً\n'
           'تعرض القائمة الحقول المطابقة (مثل VIBE ↳ VibeX، VibeY)؛ وفي التفاصيل تُظلَّل الكلمات المبحوث عنها وتُميَّز صفوف الحقول المطابقة ويُعرض الشرح باللغة التي وُجدت فيها الكلمة'},
    {'v': '1.1.8',
     'tr': 'Yeni "Video ve OSD" sayfası: kamera / yer çekimi videosu logla eşlenir (kayıt saatinden otomatik, olay seçerek ya da ±0,1 sn ince ayarla)\n'
           'Grafiğe, haritaya ya da mod tablosuna tıklayınca video o ana gider; video oynarken grafik imleci, harita ve 3B tekrar birlikte ilerler\n'
           'İkinci video girişi (FPV gözlük / DVR, OSD\'li) ve logdan çizilen OSD: mod, irtifa, hız, batarya, yapay ufuk, GPS, stickler, uyarılar (öğeler seçilebilir)\n'
           'Birleştirilmiş MP4 kaydetme: tek video, resim içinde resim ya da yan yana; isteğe bağlı harita + irtifa paneli; tüm video, yalnız uçuş ya da kırım anı ±30 sn\n'
           'Yeni "Kendi Grafiğim" sayfası: istediğin log alanlarını ya da formülleri (ör. RCOU.C3 - RCOU.C1, BAT.Volt * BAT.Curr) çiz; mod bantları ve saat dahil; grafikler kaydedilir\n'
           'Full Parameter List\'ten istediğin parametreyi grafiğe eşik çizgisi olarak ekle; görünen aralıkta en düşük / en yüksek / ortalama ve eşiğin üstünde / altında geçen süre',
     'en': 'New "Video & OSD" page: a camera / ground video is synced to the log (automatically from its recording time, by picking an event or by ±0.1 s nudges)\n'
           'Click a chart, the map or the mode table and the video jumps there; while the video plays the chart cursor, map and 3D replay move with it\n'
           'Second video input (FPV goggles / DVR with OSD) and an OSD drawn from the log: mode, altitude, speed, battery, horizon, GPS, sticks, warnings (items selectable)\n'
           'Save a merged MP4: single video, picture-in-picture or side by side; optional map + altitude panel; whole video, flight only or crash moment ±30 s\n'
           'New "My Chart" page: plot any log fields or formulas (e.g. RCOU.C3 - RCOU.C1, BAT.Volt * BAT.Curr) with mode bands and clock time; charts are saved\n'
           'Add any Full Parameter List parameter as a limit line; min / max / mean in the visible range and time spent above / below the limit',
     'ar': 'صفحة جديدة "الفيديو و OSD": يُزامَن فيديو الكاميرا / التصوير الأرضي مع السجل (تلقائياً من وقت التسجيل أو باختيار حدث أو بضبط ±0.1 ث)\n'
           'انقر على الرسم أو الخريطة أو جدول الأوضاع فينتقل الفيديو إلى تلك اللحظة؛ وأثناء التشغيل يتحرك مؤشر الرسم والخريطة والإعادة ثلاثية الأبعاد معه\n'
           'مدخل فيديو ثانٍ (نظارة FPV / DVR مع OSD) وOSD مرسوم من السجل: الوضع والارتفاع والسرعة والبطارية والأفق الاصطناعي وGPS والعصي والتحذيرات (عناصر قابلة للاختيار)\n'
           'حفظ MP4 مدمج: فيديو واحد أو صورة داخل صورة أو جنباً إلى جنب؛ لوحة خريطة + ارتفاع اختيارية؛ الفيديو كاملاً أو الطيران فقط أو لحظة السقوط ±30 ث\n'
           'صفحة جديدة "رسمي الخاص": ارسم أي حقول من السجل أو صيغ (مثل RCOU.C3 - RCOU.C1 وBAT.Volt * BAT.Curr) مع أشرطة الأوضاع والوقت؛ تُحفظ الرسوم\n'
           'أضف أي معامل من Full Parameter List كخط حدّ؛ الأدنى / الأعلى / المتوسط في النطاق الظاهر والزمن فوق / تحت الحد'},
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
