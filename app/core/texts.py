"""Analiz ve rapor metinleri — Türkçe / English / العربية (insan tarafından yazılmış, makine çevirisi değildir)."""
from __future__ import annotations
from . import knowledge as K

LANGS = ('tr', 'en', 'ar')

S = {
    # Alan adları
    'dom_gps': ('GPS / Konum', 'GPS / Position', 'GPS / الموقع'),
    'dom_vibration': ('Titreşim', 'Vibration', 'الاهتزاز'),
    'dom_power': ('Batarya ve güç', 'Battery & power', 'البطارية والطاقة'),
    'dom_ekf': ('EKF ve pusula', 'EKF & compass', 'EKF والبوصلة'),
    'dom_control': ('Tutum kontrolü', 'Attitude control', 'التحكم بالوضعية'),
    'dom_servo': ('Servo ve gaz', 'Servos & throttle', 'السيرفو والخانق'),
    'dom_rc': ('RC / radyo bağlantısı', 'RC / radio link', 'وصلة الراديو RC'),
    'dom_airspeed': ('Hava hızı', 'Airspeed', 'السرعة الجوية'),
    'dom_cpu': ('İşlemci ve log', 'CPU & logging', 'المعالج والتسجيل'),
    'st_good': ('İyi', 'Good', 'جيد'), 'st_warn': ('Dikkat', 'Caution', 'انتباه'), 'st_bad': ('Sorunlu', 'Problem', 'مشكلة'),
    'v_normal': ('NORMAL UÇUŞ', 'NORMAL FLIGHT', 'طيران طبيعي'),
    'v_incident': ('SORUNLU UÇUŞ (kırım yok)', 'FLIGHT WITH ISSUES (no crash)', 'طيران مع مشاكل (بدون تحطم)'),
    'v_incident_minor': ('KÜÇÜK UYARILAR (kırım yok)', 'MINOR WARNINGS (no crash)', 'تحذيرات بسيطة (بدون تحطم)'),
    'v_crash': ('KIRIM / KAZA', 'CRASH / ACCIDENT', 'تحطم / حادث'),
    'v_noflight': ('UÇUŞ YOK (yer testi)', 'NO FLIGHT (ground test)', 'لا يوجد طيران (اختبار أرضي)'),
    'v_desc_normal': ('Log uçuşun normal başlayıp normal bittiğini gösteriyor. Kritik bir arıza izi bulunmadı.', 'The log shows a flight that started and ended normally. No trace of a critical failure was found.', 'يُظهر السجل رحلة بدأت وانتهت بشكل طبيعي. لم يُعثر على أثر لعطل حرج.'),
    'v_desc_incident': ('Araç indi, ancak uçuş sırasında dikkat edilmesi gereken sorunlar ya da failsafe olayları var.', 'The vehicle landed, but there were problems or failsafe events during the flight that need attention.', 'هبطت المركبة، لكن حدثت مشاكل أو حالات طوارئ أثناء الطيران تستدعي الانتباه.'),
    'v_desc_incident_minor': ('Uçuş normal bitti; yalnız önemli olmayan bulgular var (ör. tek bir sağlık alanında sınır değer). Kaza riski görülmedi, yine de bulgulara göz atın.', 'The flight ended normally; there are only minor findings (e.g. a borderline value in one health area). No accident risk was seen, but review the findings.', 'انتهت الرحلة بشكل طبيعي؛ توجد ملاحظات بسيطة فقط (مثل قيمة حدّية في مجال صحي واحد). لم يُلاحظ خطر حادث، ومع ذلك راجع الملاحظات.'),
    'v_desc_crash': ('Log, uçuşun kontrolsüz bir şekilde ve bir çarpma/kırımla sona erdiğini gösteriyor.', 'The log shows the flight ended uncontrolled, with an impact/crash.', 'يُظهر السجل أن الرحلة انتهت بشكل غير مسيطر عليه مع اصطدام/تحطم.'),
    'v_desc_noflight': ('Bu logda havalanma tespit edilmedi; büyük olasılıkla yer testi veya kurulum kaydı.', 'No take-off was detected in this log; most likely a ground test or setup session.', 'لم يُكتشف إقلاع في هذا السجل؛ على الأرجح اختبار أرضي أو جلسة إعداد.'),
    # Aşamalar
    'ph_ground': ('Yerde', 'On ground', 'على الأرض'), 'ph_takeoff': ('Kalkış', 'Take-off', 'الإقلاع'),
    'ph_climb': ('Tırmanış', 'Climb', 'الصعود'), 'ph_cruise': ('Seyir', 'Cruise', 'الطيران المستقر'),
    'ph_descent': ('Alçalma', 'Descent', 'النزول'), 'ph_landing': ('İniş', 'Landing', 'الهبوط'),
    # Olaylar
    'ev_takeoff': ('Kalkış (havalanma)', 'Take-off (airborne)', 'الإقلاع (أصبح في الجو)'),
    'ev_landing': ('İniş / uçuş sonu', 'Landing / end of flight', 'الهبوط / نهاية الطيران'),
    # Sağlık bulguları
    'gps_bad_pct': ('Uçuş süresinin %{pct}\'inde GPS zayıftı (uydu < 6, HDOP > 2 veya 3D fix yok).', 'GPS was weak for {pct}% of the flight (sats < 6, HDOP > 2 or no 3D fix).', 'كان GPS ضعيفاً خلال {pct}% من زمن الطيران (أقمار < 6 أو HDOP > 2 أو لا يوجد تثبيت ثلاثي الأبعاد).'),
    'gps_min_sats': ('Uydu sayısı en düşük {n} oldu.', 'Satellite count dropped to {n}.', 'انخفض عدد الأقمار إلى {n}.'),
    'gps_glitch': ('{n} adet GPS hatası/glitch kaydı var.', '{n} GPS error/glitch records.', 'يوجد {n} من سجلات أخطاء/خلل GPS.'),
    'vibe_high': ('Titreşim yüksek: %95 değeri {v} m/s² (sınır 30). EKF ve irtifa tutma bozulabilir.', 'High vibration: 95th percentile {v} m/s² (limit 30). EKF and altitude hold may suffer.', 'اهتزاز مرتفع: المئين 95 يساوي {v} م/ث² (الحد 30). قد يتأثر EKF وتثبيت الارتفاع.'),
    'vibe_mid': ('Titreşim sınırda: %95 değeri {v} m/s². İzlemeye devam edin.', 'Vibration borderline: 95th percentile {v} m/s². Keep monitoring.', 'الاهتزاز على الحد: المئين 95 يساوي {v} م/ث². استمر في المراقبة.'),
    'vibe_clip': ('İvmeölçer {n} kez kırpıldı (clipping). Sensör ölçüm sınırını aştı.', 'Accelerometer clipped {n} times. The sensor exceeded its range.', 'حدث قصّ في مقياس التسارع {n} مرة. تجاوز الحساس نطاق قياسه.'),
    'bat_low_cell': ('Batarya hücre başına {v} V\'a düştü ({n}S). Bu derin deşarjdır ve güç kaybı riski taşır.', 'Battery dropped to {v} V per cell ({n}S). This is a deep discharge with risk of power loss.', 'انخفض جهد البطارية إلى {v} فولت للخلية ({n}S). هذا تفريغ عميق مع خطر فقدان الطاقة.'),
    'bat_mid_cell': ('Batarya hücre başına {v} V\'a indi ({n}S). Sınırda; iniş daha erken planlanmalı.', 'Battery reached {v} V per cell ({n}S). Borderline; plan landing earlier.', 'وصل جهد البطارية إلى {v} فولت للخلية ({n}S). على الحد؛ يجب التخطيط للهبوط مبكراً.'),
    'bat_no_current': ('Akım ölçülmüyor. Tüketilen mAh ve kapasite failsafe çalışmaz.', 'Current is not measured. Consumed mAh and capacity failsafe do not work.', 'التيار غير مقاس. لا يعمل حساب الاستهلاك وطوارئ السعة.'),
    'bat_used': ('Kapasitenin büyük kısmı kullanıldı: {used} / {cap} mAh.', 'Most of the capacity was used: {used} / {cap} mAh.', 'تم استهلاك معظم السعة: {used} / {cap} مللي أمبير ساعة.'),
    'bat_fs': ('Batarya failsafe tetiklendi.', 'Battery failsafe was triggered.', 'تم تفعيل طوارئ البطارية.'),
    'vcc_low': ('Uçuş kartı beslemesi {v} V\'a düştü (4,8 V altı riskli).', 'Flight board supply dropped to {v} V (below 4.8 V is risky).', 'انخفضت تغذية لوحة الطيران إلى {v} فولت (أقل من 4.8 فولت خطر).'),
    'ekf_bad': ('EKF {k} test oranı {v} (1\'in üstü = ölçüm reddedildi).', 'EKF {k} test ratio {v} (above 1 = measurement rejected).', 'نسبة اختبار EKF {k} تساوي {v} (فوق 1 = تم رفض القياس).'),
    'ekf_warn': ('EKF {k} test oranı {v}; sınıra yakın.', 'EKF {k} test ratio {v}; close to the limit.', 'نسبة اختبار EKF {k} تساوي {v}؛ قريبة من الحد.'),
    'mag_interf': ('Pusula gaz ile birlikte değişiyor (korelasyon {c}, değişim %{v}). Motor/kablo manyetik girişimi var.', 'Compass changes with throttle (correlation {c}, variation {v}%). Motor/wiring magnetic interference.', 'تتغير البوصلة مع الخانق (ارتباط {c}، تغير {v}%). يوجد تداخل مغناطيسي من المحرك/الأسلاك.'),
    'mag_var': ('Manyetik alan büyüklüğü %{v} değişiyor; pusula kalibrasyonu ve konumu kontrol edilmeli.', 'Magnetic field magnitude varies by {v}%; check compass calibration and placement.', 'يتغير مقدار المجال المغناطيسي بنسبة {v}%؛ يجب فحص معايرة البوصلة وموقعها.'),
    'ekf_err': ('EKF hata/failsafe kaydı var.', 'EKF error/failsafe records present.', 'توجد سجلات أخطاء/طوارئ EKF.'),
    'att_roll_err': ('Yatış takip hatası yüksek (RMS {v}°). Ayar (tuning) veya mekanik sorun.', 'High roll tracking error (RMS {v}°). Tuning or mechanical issue.', 'خطأ تتبع الدوران مرتفع (RMS {v}°). مشكلة ضبط أو ميكانيكية.'),
    'att_pitch_err': ('Yunuslama takip hatası yüksek (RMS {v}°).', 'High pitch tracking error (RMS {v}°).', 'خطأ تتبع الميلان مرتفع (RMS {v}°).'),
    'att_roll_exceed': ('Yatış {v}°\'ye ulaştı (sınır {lim}°). Kontrol kaybı veya sert manevra.', 'Roll reached {v}° (limit {lim}°). Loss of control or hard manoeuvre.', 'وصل الدوران إلى {v}° (الحد {lim}°). فقدان سيطرة أو مناورة حادة.'),
    'servo_sat': ('{ch} kanalı uçuşun %{v}\'inde sınırdaydı (doyma). Kontrol gücü yetersiz olabilir.', 'Channel {ch} was at its limit for {v}% of the flight (saturation). Control authority may be insufficient.', 'كانت القناة {ch} عند حدها خلال {v}% من الطيران (تشبع). قد تكون سلطة التحكم غير كافية.'),
    'thr_full': ('Gaz uçuşun %{v}\'inde tam açıktı. Güç yetersiz, ağırlık fazla veya hız hedefi yüksek.', 'Throttle was at full for {v}% of the flight. Underpowered, overweight, or speed target too high.', 'كان الخانق مفتوحاً بالكامل خلال {v}% من الطيران. طاقة غير كافية أو وزن زائد أو هدف سرعة مرتفع.'),
    'rc_fs': ('{n} radyo failsafe kaydı var.', '{n} radio failsafe records.', 'يوجد {n} من سجلات طوارئ الراديو.'),
    'rc_low': ('Gaz kanalı uçuşun %{v}\'inde failsafe değerinin altındaydı.', 'Throttle channel was below the failsafe value for {v}% of the flight.', 'كانت قناة الخانق تحت قيمة الطوارئ خلال {v}% من الطيران.'),
    'as_low': ('Hava hızı seyirde zamanın %{v}\'inde asgari hızın ({min} m/s) altına indi. Stall riski.', 'Airspeed was below the minimum ({min} m/s) for {v}% of cruise. Stall risk.', 'كانت السرعة الجوية تحت الحد الأدنى ({min} م/ث) خلال {v}% من الطيران المستقر. خطر الانهيار.'),
    'as_not_used': ('Hava hızı sensörü yok veya kullanılmıyor; hız tahmini kullanılıyor.', 'No airspeed sensor or not used; synthetic airspeed estimate in use.', 'لا يوجد حساس سرعة جوية أو غير مستخدم؛ يُستخدم تقدير السرعة.'),
    'cpu_high': ('İşlemci yükü %{v}\'e çıktı.', 'CPU load reached {v}%.', 'وصل حمل المعالج إلى {v}%.'),
    # Kırım kanıtları
    'cr_stat': ('Otopilot kırım bayrağını kaldırdı ({t}).', 'Autopilot raised its crash flag ({t}).', 'رفع الطيار الآلي علم التحطم ({t}).'),
    'cr_err': ('Kırım kontrolü hata kaydı ({t}).', 'Crash-check error record ({t}).', 'سجل خطأ فحص التحطم ({t}).'),
    'cr_msg': ('Otopilot mesajı: "{msg}" ({t}).', 'Autopilot message: "{msg}" ({t}).', 'رسالة الطيار الآلي: "{msg}" ({t}).'),
    'cr_sink': ('Uçuşun son saniyelerinde {v} m/s alçalma hızı (kontrolsüz düşüş).', '{v} m/s sink rate in the final seconds (uncontrolled descent).', 'معدل هبوط {v} م/ث في الثواني الأخيرة (سقوط غير مسيطر عليه).'),
    'cr_log_end': ('Log, araç {alt} m irtifadayken aniden bitti ({t}). Güç kesintisi veya çarpma.', 'Log ended abruptly with the vehicle at {alt} m ({t}). Power loss or impact.', 'انتهى السجل فجأة والمركبة على ارتفاع {alt} م ({t}). فقدان طاقة أو اصطدام.'),
    'cr_fall': ('Kontrolsüz düşüş: {t} anında araç {h} m yükseklikten saniyede ~{v} m hızla yere indi (en büyük tutum {a}°). Normal iniş bu hızda olmaz.', 'Uncontrolled fall: at {t} the vehicle came down {h} m at ~{v} m/s (max attitude {a}°). A normal landing is never this fast.', 'سقوط غير مسيطر عليه: عند {t} هبطت المركبة {h} م بسرعة ~{v} م/ث (أكبر زاوية وضع {a}°). الهبوط الطبيعي لا يكون بهذه السرعة.'),
    'cr_flip': ('Araç devrildi: {t} anında tutum {a}° oldu ve öyle kaldı (kalkışta ya da alçakta devrilme).', 'Vehicle flipped: attitude reached {a}° at {t} and stayed there (tip-over on take-off or at low altitude).', 'انقلبت المركبة: بلغت الوضعية {a}° عند {t} وبقيت كذلك (انقلاب عند الإقلاع أو على ارتفاع منخفض).'),
    'cr_log_cut': ('Araç kurulu ve uçarken log {t} anında kesildi; disarm kaydı yok. Güç kesintisi veya çarpma olası.', 'Log stopped at {t} while armed and flying, with no disarm record. Power loss or impact likely.', 'توقف السجل عند {t} والمركبة مسلحة وفي الطيران دون تسجيل فك التسليح. يحتمل فقدان الطاقة أو اصطدام.'),
    'cr_yaw': ('Son saniyelerde yön kontrolü kaybedildi: istenen ile gerçek yön arasında {v}° fark ({t}). Motor/ESC itki kaybı veya bükük kol olası.', 'Yaw control lost in the final seconds: {v}° between desired and actual heading ({t}). Motor/ESC thrust loss or a twisted arm is likely.', 'فُقد التحكم في الانعراج في الثواني الأخيرة: فرق {v}° بين الاتجاه المطلوب والفعلي ({t}). يحتمل فقدان دفع محرك/منظم سرعة أو ذراع ملتوية.'),
    'surf_rev': ('Kumanda yüzeyi ters ya da yetersiz ({s}): otopilotun istediği dönüş ile aracın gerçek dönüşü ters ilintili (r={c}). Önce yüzey yönünü kontrol edin (SERVOx_REVERSED / RCx_REVERSED); yön doğruysa yüzey yetkisi yetersizdir (servo aralığı SERVOx_MIN/MAX, mekanik hareket).', 'Control surface reversed or too weak ({s}): commanded and actual rotation are inversely correlated (r={c}). First check the surface direction (SERVOx_REVERSED / RCx_REVERSED); if it is right, the surface lacks authority (servo travel SERVOx_MIN/MAX, linkage).', 'سطح التحكم معكوس أو ضعيف ({s}): الدوران المطلوب والفعلي مترابطان عكسياً (r={c}). افحص اتجاه السطح أولاً (SERVOx_REVERSED / RCx_REVERSED)؛ إن كان صحيحاً فصلاحية السطح غير كافية (مدى السيرفو SERVOx_MIN/MAX، الوصلات).'),
    'surf_weak': ('Kumanda yüzeyi uçuşun %{p} kadarında sonuna kadar basılı ({s}): yüzey yetkisi yetersiz (servo hareket aralığı/SERVOx_MIN-MAX, yüzey boyutu) ya da araç dengesiz.', 'The control surface was at full deflection for {p}% of the flight ({s}): not enough authority (servo travel / SERVOx_MIN-MAX, surface size) or the aircraft is out of balance.', 'كان سطح التحكم عند أقصى انحراف لمدة {p}% من الرحلة ({s}): صلاحية غير كافية (مدى حركة السيرفو / SERVOx_MIN-MAX، حجم السطح) أو الطائرة غير متوازنة.'),
    'cg_nose': ('Düz uçuşta irtifa dümeni sürekli yukarıda (%{p}): burun ağır (ağırlık merkezi önde) ya da trim/yüzey ayarı bozuk.', 'In level flight the elevator is held up all the time ({p}%): nose heavy (CG forward) or bad trim/linkage.', 'في الطيران المستوي يبقى الرافع مرفوعاً باستمرار ({p}%): المقدمة ثقيلة (مركز الثقل متقدم) أو ضبط التريم/الوصلات سيئ.'),
    'cg_tail': ('Düz uçuşta irtifa dümeni sürekli aşağıda (%{p}): kuyruk ağır (ağırlık merkezi geride, kararsızlık riski) ya da trim/yüzey ayarı bozuk.', 'In level flight the elevator is held down all the time ({p}%): tail heavy (CG aft, instability risk) or bad trim/linkage.', 'في الطيران المستوي يبقى الرافع منخفضاً باستمرار ({p}%): الذيل ثقيل (مركز الثقل متأخر، خطر عدم الاستقرار) أو ضبط التريم سيئ.'),
    'aspd_ratio': ('Hava hızı / yer hızı ortalaması {r}: hava hızı sensörü kalibrasyonu şüpheli (ARSPD_RATIO, pitot hortumu, sensör yeri).', 'Mean airspeed / groundspeed is {r}: airspeed sensor calibration is suspect (ARSPD_RATIO, pitot tubing, sensor placement).', 'متوسط السرعة الجوية / الأرضية {r}: معايرة حساس السرعة الجوية مشكوك فيها (ARSPD_RATIO، أنبوب البيتو، موضع الحساس).'),
    'tw_low': ('İtki/ağırlık oranı düşük: asılı kalma gazı %{h} → itki/ağırlık ≈ {tw}. Rüzgârda ya da manevrada motorlar tavana dayanır, araç kontrolü kaybedebilir. Ağırlığı azaltın veya daha güçlü motor/pervane/batarya kullanın (hedef ≥ 2).', 'Low thrust-to-weight: hover throttle {h}% → thrust/weight ≈ {tw}. In wind or manoeuvres the motors saturate and control can be lost. Reduce weight or use stronger motors/props/battery (target ≥ 2).', 'نسبة الدفع إلى الوزن منخفضة: خانق التحليق {h}% ← الدفع/الوزن ≈ {tw}. في الرياح أو المناورات تتشبع المحركات وقد يُفقد التحكم. خفّف الوزن أو استخدم محركات/مراوح/بطارية أقوى (الهدف ≥ 2).'),
    'tw_marginal': ('İtki/ağırlık oranı sınırda: asılı kalma gazı %{h} → itki/ağırlık ≈ {tw} (önerilen ≥ 2). Yük eklemeyin; rüzgârlı havada dikkat.', 'Marginal thrust-to-weight: hover throttle {h}% → thrust/weight ≈ {tw} (recommended ≥ 2). Do not add payload; be careful in wind.', 'نسبة الدفع إلى الوزن حدّية: خانق التحليق {h}% ← الدفع/الوزن ≈ {tw} (الموصى به ≥ 2). لا تضف حمولة؛ احذر في الرياح.'),
    'fw_thr_high': ('Düz seyirde gaz %{v}: güç payı çok az (ağır, sürükleme yüksek ya da motor/pervane zayıf). Tırmanma ve rüzgâra karşı uçuşta hız kaybı riski.', 'Level cruise throttle {v}%: very little power margin (heavy, high drag or weak motor/prop). Risk of losing airspeed when climbing or flying into wind.', 'الخانق في الطيران المستوي {v}%: هامش القدرة ضئيل جداً (ثقيل، سحب عالٍ أو محرك/مروحة ضعيفة). خطر فقدان السرعة عند الصعود أو الطيران عكس الريح.'),
    'bat_ir': ('Batarya iç direnci yüksek: {r} mΩ ({n} hücre, hücre başına {c} mΩ). Batarya yaşlanmış veya yetersiz; yük altında gerilim çöker.', 'High battery internal resistance: {r} mΩ ({n} cells, {c} mΩ per cell). The pack is aged or undersized; voltage sags under load.', 'مقاومة داخلية مرتفعة للبطارية: {r} مللي أوم ({n} خلايا، {c} لكل خلية). البطارية قديمة أو غير كافية؛ ينهار الجهد تحت الحمل.'),
    'vib_peak_nonotch': ('Baskın titreşim {f} Hz civarında ve harmonik çentik filtresi kapalı. INS_HNTCH_ENABLE=1, INS_HNTCH_FREQ≈{f} ile başlayın.', 'Dominant vibration near {f} Hz and the harmonic notch is off. Start with INS_HNTCH_ENABLE=1, INS_HNTCH_FREQ≈{f}.', 'الاهتزاز السائد قرب {f} هرتز ومرشح الشق التوافقي معطل. ابدأ بـ INS_HNTCH_ENABLE=1 وINS_HNTCH_FREQ≈{f}.'),
    'vib_peak_notch': ('Baskın titreşim {f} Hz, çentik filtresi ise {n} Hz ve katlarına ayarlı: filtre bu titreşimi süzmüyor. INS_HNTCH_FREQ/REF ayarını gözden geçirin.', 'Dominant vibration at {f} Hz while the notch is set to {n} Hz and harmonics: the filter misses it. Review INS_HNTCH_FREQ/REF.', 'الاهتزاز السائد عند {f} هرتز بينما الشق مضبوط على {n} هرتز وتوافقياته: المرشح لا يلتقطه. راجع INS_HNTCH_FREQ/REF.'),
    'cr_user': ('Operatör formda kırım yaşandığını bildirdi.', 'The operator reported a crash in the flight form.', 'أفاد المشغل في النموذج بحدوث تحطم.'),
    'cr_user_weak': ('Logda kırımın izi zayıf: log, çarpmadan önce kesilmiş olabilir (güç kaybı, kart resetlenmesi).', 'Little trace of the crash in the log: logging may have stopped before impact (power loss, board reset).', 'أثر التحطم في السجل ضعيف: ربما توقف التسجيل قبل الاصطدام (فقدان طاقة، إعادة تشغيل اللوحة).'),
    'cr_user_hard': ('Operatör sert iniş / hafif hasar bildirdi.', 'The operator reported a hard landing / minor damage.', 'أفاد المشغل بهبوط عنيف / ضرر طفيف.'),
    'cr_user_no': ('Operatör kırım olmadığını bildirdi; zayıf kırım belirtileri "sorunlu uçuş" olarak değerlendirildi.', 'The operator reported no crash; weak crash signs were rated as an incident.', 'أفاد المشغل بعدم حدوث تحطم؛ قُيّمت علامات التحطم الضعيفة كحادثة.'),
    'cr_user_conflict': ('Operatör kırım olmadığını bildirdi, ama otopilot logda kırım kaydetmiş. Lütfen kontrol edin.', 'The operator reported no crash, but the autopilot logged a crash. Please check.', 'أفاد المشغل بعدم حدوث تحطم، لكن الطيار الآلي سجّل تحطماً. يرجى التحقق.'),
    'fi_ice_power': ('Benzinli/içten yanmalı motor: BAT yalnız aviyonik bataryayı gösterir, akım sensörü yokluğu ceza sayılmadı.', 'Internal-combustion engine: BAT shows only the avionics battery; a missing current sensor is not penalised.', 'محرك احتراق داخلي: BAT يعرض بطارية الإلكترونيات فقط؛ لا يُحتسب غياب حساس التيار.'),
    'cr_attitude': ('Son saniyelerde aşırı tutum: yatış {r}°, yunuslama {p}°.', 'Extreme attitude in final seconds: roll {r}°, pitch {p}°.', 'وضعية متطرفة في الثواني الأخيرة: دوران {r}°، ميلان {p}°.'),
    'cr_impact': ('Son anda {v} m/s² darbe ivmesi.', '{v} m/s² impact acceleration at the end.', 'تسارع اصطدام {v} م/ث² في النهاية.'),
    'cr_landed': ('"İniş tamamlandı" olayı kaydedilmiş.', '"Landing complete" event recorded.', 'تم تسجيل حدث "اكتمل الهبوط".'),
    # Kök nedenler
    'cause_gps': ('GPS kaybı / bozulması', 'GPS loss / degradation', 'فقدان / تدهور GPS'),
    'cause_ekf': ('EKF (konum kestirimi) bozulması', 'EKF (navigation estimate) failure', 'تدهور EKF (تقدير الملاحة)'),
    'cause_battery': ('Batarya tükenmesi', 'Battery depletion', 'نفاد البطارية'),
    'cause_radio': ('Radyo (RC) bağlantı kaybı', 'Radio (RC) link loss', 'فقدان وصلة الراديو (RC)'),
    'cause_stall': ('Hız kaybı (stall)', 'Loss of airspeed (stall)', 'فقدان السرعة (الانهيار)'),
    'cause_vibration': ('Aşırı titreşim', 'Excessive vibration', 'اهتزاز مفرط'),
    'cause_compass': ('Pusula manyetik girişimi', 'Compass magnetic interference', 'تداخل مغناطيسي في البوصلة'),
    'cause_power': ('Ani güç kesintisi / kart resetlenmesi', 'Sudden power loss / board reset', 'انقطاع مفاجئ للطاقة / إعادة تشغيل اللوحة'),
    'cause_motor': ('Motor / ESC / pervane arızası veya yanlış motor sırası', 'Motor / ESC / propeller failure or wrong motor order', 'عطل المحرك / ESC / المروحة أو ترتيب محركات خاطئ'),
    'cause_control': ('Kontrol kaybı (mekanik/ayar)', 'Loss of control (mechanical/tuning)', 'فقدان السيطرة (ميكانيكي/ضبط)'),
    'cause_unknown': ('Belirlenemedi', 'Undetermined', 'غير محدد'),
    'why_gps': ('Uydu sayısı düştü ve konum doğruluğu bozuldu. EKF güvenilir konum bulamayınca otopilot failsafe moduna geçti; konum bilgisi olmadan rota ve irtifa tutulamadı.', 'Satellite count fell and position accuracy degraded. With no reliable position the EKF triggered failsafe; without position the route and altitude could not be held.', 'انخفض عدد الأقمار وتدهورت دقة الموقع. ومع غياب موقع موثوق فعّل EKF الطوارئ؛ وبدون موقع لم يمكن الحفاظ على المسار والارتفاع.'),
    'why_ekf': ('EKF sensör ölçümlerini birbiriyle tutarsız buldu ve reddetti. Konum/yön kestirimi güvenilmez hale geldi.', 'The EKF found sensor measurements inconsistent and rejected them. Position/heading estimate became unreliable.', 'وجد EKF قياسات الحساسات غير متسقة فرفضها. أصبح تقدير الموقع/الاتجاه غير موثوق.'),
    'why_battery': ('Batarya gerilimi kritik seviyenin altına düştü. Motor yeterli itki üretemedi ve araç irtifa kaybetti.', 'Battery voltage fell below the critical level. The motor could not produce enough thrust and the vehicle lost altitude.', 'انخفض جهد البطارية تحت المستوى الحرج. لم يتمكن المحرك من إنتاج دفع كافٍ ففقدت المركبة الارتفاع.'),
    'why_radio': ('Kumanda sinyali kesildi. Radyo failsafe devreye girdi; failsafe ayarına göre araç eve dönmeye ya da inmeye çalıştı.', 'The RC signal was lost. Radio failsafe engaged; depending on its setting the vehicle tried to return or land.', 'انقطعت إشارة جهاز التحكم. تفعّلت طوارئ الراديو؛ وحسب إعدادها حاولت المركبة العودة أو الهبوط.'),
    'why_stall': ('Hava hızı asgari değerin çok altına indi, kanat taşıma kuvvetini kaybetti; uçak yatış/yunuslama kontrolünü kaybederek düştü.', 'Airspeed dropped far below the minimum, the wing lost lift; the aircraft lost roll/pitch control and fell.', 'انخفضت السرعة الجوية كثيراً تحت الحد الأدنى ففقد الجناح قوة الرفع؛ فقدت الطائرة السيطرة على الدوران والميلان وسقطت.'),
    'why_vibration': ('Titreşim ivmeölçer ölçümlerini bozdu (kırpılma). EKF dikey konumu yanlış hesapladı; irtifa ve tutum kontrolü bozuldu.', 'Vibration corrupted the accelerometer readings (clipping). The EKF mis-estimated vertical position; altitude and attitude control degraded.', 'أفسد الاهتزاز قراءات مقياس التسارع (القص). أخطأ EKF في تقدير الموقع الرأسي فتدهور التحكم بالارتفاع والوضعية.'),
    'why_compass': ('Motor akımı pusulayı etkiledi. Yön (heading) yanlış hesaplanınca araç yanlış yöne döndü, rota tutturulamadı.', 'Motor current disturbed the compass. With a wrong heading the vehicle turned the wrong way and could not hold its route.', 'أثّر تيار المحرك على البوصلة. ومع اتجاه خاطئ انعطفت المركبة في الاتجاه الخطأ ولم تستطع الحفاظ على مسارها.'),
    'why_power': ('Log araç havadayken aniden kesildi. Bu genellikle kart beslemesinin kesilmesi, batarya konnektörü, BEC arızası ya da sert çarpmadır.', 'The log stopped while airborne. This usually means the board lost power (battery connector, BEC failure) or a hard impact.', 'توقف السجل والمركبة في الجو. يعني ذلك عادة انقطاع تغذية اللوحة (موصل البطارية، عطل BEC) أو اصطداماً قوياً.'),
    'why_motor': ('Bir motorun çıkışı tavana dayandı ama araç toparlanamadı; ya da araç kalkıştan hemen sonra devrildi. Bu, motor/ESC/pervane arızasını, ters takılmış pervaneyi ya da yanlış motor sırası/yönünü gösterir.', 'One motor output hit its maximum yet the vehicle could not recover, or it flipped right after take-off. This points to a motor/ESC/propeller failure, a reversed prop, or wrong motor order/direction.', 'وصل خرج أحد المحركات إلى حده الأقصى دون أن تتعافى المركبة، أو انقلبت مباشرة بعد الإقلاع. يدل ذلك على عطل محرك/ESC/مروحة أو مروحة معكوسة أو ترتيب/اتجاه محركات خاطئ.'),
    'why_control': ('İstenen ve gerçekleşen tutum arasındaki fark çok büyüdü. Servo/bağlantı arızası, yüzey kopması veya hatalı ayar kontrolü kaybettirdi.', 'The gap between desired and actual attitude grew very large. A servo/linkage failure, lost control surface or bad tuning caused loss of control.', 'اتسع الفرق بين الوضعية المطلوبة والفعلية كثيراً. سبّب عطل سيرفو/وصلة أو فقدان سطح تحكم أو ضبط خاطئ فقدان السيطرة.'),
    'why_unknown': ('Mevcut verilerle tek bir kök neden belirlenemedi. Zaman çizelgesi ve grafikler birlikte incelenmeli.', 'A single root cause could not be determined from the available data. Review the timeline and charts together.', 'لم يمكن تحديد سبب جذري واحد من البيانات المتاحة. يجب مراجعة الخط الزمني والرسوم معاً.'),
    'prevent_gps': ('GPS anteninin gökyüzünü net görmesini sağlayın, video verici ve ESC\'lerden uzak tutun; kalkıştan önce en az 10 uydu ve HDOP < 1,5 bekleyin; ikinci GPS ve GPS failsafe eylemini (FS_EKF_ACTION) yapılandırın.', 'Give the GPS antenna a clear sky view, away from video transmitters and ESCs; wait for at least 10 satellites and HDOP < 1.5 before take-off; add a second GPS and configure the GPS/EKF failsafe action.', 'امنح هوائي GPS رؤية واضحة للسماء بعيداً عن مرسل الفيديو والـ ESC؛ انتظر 10 أقمار على الأقل وHDOP < 1.5 قبل الإقلاع؛ أضف GPS ثانياً واضبط إجراء طوارئ GPS/EKF.'),
    'prevent_ekf': ('Titreşimi azaltın, pusula ve GPS\'i kontrol edin; EKF failsafe eylemini etkinleştirin.', 'Reduce vibration, check compass and GPS; enable the EKF failsafe action.', 'قلّل الاهتزاز وافحص البوصلة وGPS؛ فعّل إجراء طوارئ EKF.'),
    'prevent_battery': ('Batarya izlemeyi (BATT_MONITOR=4) ve akım sensörünü kalibre edin; BATT_LOW_VOLT/BATT_CRT_VOLT ve BATT_FS_LOW_ACT=RTL ayarlayın; uçuş süresini kapasitenin %80\'iyle planlayın.', 'Calibrate battery monitoring (BATT_MONITOR=4) and the current sensor; set BATT_LOW_VOLT/BATT_CRT_VOLT and BATT_FS_LOW_ACT=RTL; plan flight time on 80% of capacity.', 'عاير مراقبة البطارية (BATT_MONITOR=4) وحساس التيار؛ اضبط BATT_LOW_VOLT وBATT_CRT_VOLT وBATT_FS_LOW_ACT=RTL؛ خطط زمن الطيران على 80% من السعة.'),
    'prevent_radio': ('Radyo failsafe\'i (THR_FAILSAFE / FS_THR_ENABLE) açın ve yerde test edin; anten yönünü ve menzili kontrol edin.', 'Enable radio failsafe (THR_FAILSAFE / FS_THR_ENABLE) and test it on the ground; check antenna orientation and range.', 'فعّل طوارئ الراديو (THR_FAILSAFE / FS_THR_ENABLE) واختبرها على الأرض؛ افحص اتجاه الهوائي والمدى.'),
    'prevent_stall': ('AIRSPEED_MIN\'i stall hızının en az %25 üstüne ayarlayın, STALL_PREVENTION\'ı açın, pitot\'u kalibre edin, dönüşlerde yatış sınırını düşürün.', 'Set AIRSPEED_MIN at least 25% above stall speed, enable STALL_PREVENTION, calibrate the pitot and lower the bank limit in turns.', 'اضبط AIRSPEED_MIN أعلى من سرعة الانهيار بنسبة 25% على الأقل، وفعّل STALL_PREVENTION، وعاير البيتوت، وخفّض حد الميل في الانعطافات.'),
    'prevent_vibration': ('Pervaneleri balanslayın, motor yataklarını kontrol edin, uçuş kartını titreşim sönümleyici ile monte edin.', 'Balance propellers, check motor bearings, mount the flight controller on vibration dampers.', 'وازن المراوح وافحص محامل المحرك وركّب لوحة الطيران على مخمدات اهتزاز.'),
    'prevent_compass': ('Pusulayı güç kablolarından uzaklaştırın (GPS direğine), CompassMot kalibrasyonu yapın, gerekirse iç pusulayı kapatın.', 'Move the compass away from power wiring (GPS mast), run CompassMot calibration, disable the internal compass if needed.', 'أبعد البوصلة عن أسلاك الطاقة (على سارية GPS)، وأجرِ معايرة CompassMot، وعطّل البوصلة الداخلية إذا لزم.'),
    'prevent_power': ('Batarya konnektörlerini ve güç modülünü kontrol edin, yedek BEC kullanın, kart beslemesini (Vcc) izleyin.', 'Check battery connectors and power module, use a backup BEC, monitor board supply (Vcc).', 'افحص موصلات البطارية ووحدة الطاقة، واستخدم BEC احتياطياً، وراقب تغذية اللوحة (Vcc).'),
    'prevent_motor': ('Mission Planner > Motor Test ile motor sırasını ve dönüş yönlerini doğrulayın; pervaneleri (CW/CCW) ve sıkılıklarını kontrol edin; ESC kalibrasyonu yapın; motor/ESC ısınma ve lehimlerini inceleyin.', 'Verify motor order and spin direction with Mission Planner > Motor Test; check props (CW/CCW) and tightness; calibrate ESCs; inspect motors/ESCs for heat and solder joints.', 'تحقق من ترتيب المحركات واتجاه دورانها عبر Mission Planner > Motor Test؛ افحص المراوح (CW/CCW) وإحكامها؛ عاير الـ ESC؛ افحص المحركات وESC للحرارة واللحامات.'),
    'prevent_control': ('Servo ve bağlantı çubuklarını, yüzey menteşelerini kontrol edin; yön (reverse) ayarlarını yerde doğrulayın; AUTOTUNE ile ayar yapın.', 'Inspect servos, linkages and hinges; verify reversal on the ground; tune with AUTOTUNE.', 'افحص السيرفوهات والوصلات والمفصلات؛ تحقق من اتجاه الحركة على الأرض؛ اضبط باستخدام AUTOTUNE.'),
    'prevent_unknown': ('Grafikleri ve olay zaman çizelgesini birlikte inceleyin; gerekirse çevrimiçi yapay zeka analizini çalıştırın.', 'Review charts and timeline together; run the online AI analysis if needed.', 'راجع الرسوم والخط الزمني معاً؛ وشغّل تحليل الذكاء الاصطناعي عند الحاجة.'),
    'step_mode': ('Mod değişti: {mode} ({reason})', 'Mode changed: {mode} ({reason})', 'تغيّر الوضع: {mode} ({reason})'),
    'step_end_crash': ('Kırım / çarpma', 'Crash / impact', 'تحطم / اصطدام'),
    'step_end_incident': ('Uçuş sonu', 'End of flight', 'نهاية الطيران'),
    # Parametre denetimi
    'pa_none': ('Logda parametre (PARM) kaydı yok; yapılandırma denetlenemedi.', 'No parameter (PARM) records in the log; configuration could not be audited.', 'لا توجد سجلات معاملات (PARM) في السجل؛ تعذر تدقيق التهيئة.'),
    'pa_ok': ('Kritik bir yapılandırma riski bulunmadı.', 'No critical configuration risk found.', 'لم يُعثر على خطر حرج في التهيئة.'),
    'pa_arming_off': ('ARMING_CHECK = 0: Tüm arm öncesi kontroller kapalı. Sensör arızasıyla kalkılabilir.', 'ARMING_CHECK = 0: all pre-arm checks are disabled. The vehicle can take off with a failed sensor.', 'ARMING_CHECK = 0: جميع فحوص ما قبل التسليح معطلة. قد تقلع المركبة مع حساس معطل.'),
    'pa_skipchk': ('ARMING_SKIPCHK = {v}: Bazı arm kontrolleri atlanıyor.', 'ARMING_SKIPCHK = {v}: some arming checks are skipped.', 'ARMING_SKIPCHK = {v}: يتم تخطي بعض فحوص التسليح.'),
    'pa_batt_mon_off': ('BATT_MONITOR = 0: Batarya izlenmiyor; batarya failsafe çalışmaz.', 'BATT_MONITOR = 0: battery is not monitored; battery failsafe cannot work.', 'BATT_MONITOR = 0: البطارية غير مراقبة؛ لا تعمل طوارئ البطارية.'),
    'pa_batt_volt_only': ('BATT_MONITOR = 3: Sadece gerilim ölçülüyor, akım/mAh yok.', 'BATT_MONITOR = 3: voltage only, no current/mAh.', 'BATT_MONITOR = 3: يُقاس الجهد فقط، بدون تيار/استهلاك.'),
    'pa_batt_fs_off': ('BATT_FS_LOW_ACT = 0: Düşük bataryada hiçbir eylem yapılmaz.', 'BATT_FS_LOW_ACT = 0: no action is taken on low battery.', 'BATT_FS_LOW_ACT = 0: لا يُتخذ أي إجراء عند انخفاض البطارية.'),
    'pa_batt_low_unset': ('BATT_LOW_VOLT ve BATT_LOW_MAH ayarlı değil; düşük batarya algılanmaz.', 'BATT_LOW_VOLT and BATT_LOW_MAH are not set; low battery is not detected.', 'لم يتم ضبط BATT_LOW_VOLT وBATT_LOW_MAH؛ لن يُكتشف انخفاض البطارية.'),
    'pa_batt_cap': ('BATT_CAPACITY = 0: Kalan yüzde hesaplanamaz.', 'BATT_CAPACITY = 0: remaining percentage cannot be computed.', 'BATT_CAPACITY = 0: لا يمكن حساب النسبة المتبقية.'),
    'pa_thr_fs_off': ('Radyo (gaz) failsafe kapalı: Kumanda kaybında araç son komutla uçmaya devam eder.', 'Radio (throttle) failsafe disabled: on RC loss the vehicle keeps flying the last command.', 'طوارئ الراديو (الخانق) معطلة: عند فقدان التحكم تستمر المركبة بآخر أمر.'),
    'pa_fs_long_none': ('FS_LONG_ACTN = 0: Uzun radyo kaybında eve dönüş yok (AUTO\'da göreve devam).', 'FS_LONG_ACTN = 0: no RTL on long radio loss (continues mission in AUTO).', 'FS_LONG_ACTN = 0: لا عودة عند فقدان الراديو لفترة طويلة (يستمر في المهمة في وضع AUTO).'),
    'pa_no_airspeed': ('ARSPD_TYPE = 0: Hava hızı sensörü yok; stall koruması zayıflar.', 'ARSPD_TYPE = 0: no airspeed sensor; stall protection is weaker.', 'ARSPD_TYPE = 0: لا يوجد حساس سرعة جوية؛ تضعف الحماية من الانهيار.'),
    'pa_as_min_low': ('Asgari hava hızı {v} m/s çok düşük olabilir; stall hızını kontrol edin.', 'Minimum airspeed {v} m/s may be too low; check stall speed.', 'قد يكون الحد الأدنى للسرعة الجوية {v} م/ث منخفضاً جداً؛ تحقق من سرعة الانهيار.'),
    'pa_stall_prev': ('STALL_PREVENTION = 0: Düşük hızda yatış sınırlaması kapalı.', 'STALL_PREVENTION = 0: bank limiting at low speed is disabled.', 'STALL_PREVENTION = 0: تحديد الميل عند السرعة المنخفضة معطل.'),
    'pa_thr_max': ('THR_MAX = {v}: Azami gaz düşük; tırmanma ve hız kurtarma zorlaşır.', 'THR_MAX = {v}: maximum throttle is low; climb and speed recovery suffer.', 'THR_MAX = {v}: الحد الأقصى للخانق منخفض؛ يصعب الصعود واستعادة السرعة.'),
    'pa_ekf_fs_off': ('FS_EKF_ACTION = 0: EKF bozulduğunda eylem yok.', 'FS_EKF_ACTION = 0: no action on EKF failure.', 'FS_EKF_ACTION = 0: لا إجراء عند فشل EKF.'),
    'pa_hover_high': ('MOT_THST_HOVER = {v}: Askı gazı çok yüksek; araç ağır veya güçsüz.', 'MOT_THST_HOVER = {v}: hover throttle very high; vehicle heavy or underpowered.', 'MOT_THST_HOVER = {v}: خانق التحويم مرتفع جداً؛ المركبة ثقيلة أو ضعيفة.'),
    'pa_gcs_fs_off': ('YKİ failsafe kapalı (bilgi).', 'GCS failsafe disabled (info).', 'طوارئ المحطة الأرضية معطلة (معلومة).'),
    'pa_compass_off': ('COMPASS_USE = 0: Birincil pusula kullanılmıyor.', 'COMPASS_USE = 0: primary compass not used.', 'COMPASS_USE = 0: البوصلة الأساسية غير مستخدمة.'),
    'pa_log_off': ('LOG_BITMASK = 0: Log kaydı kapalı.', 'LOG_BITMASK = 0: logging disabled.', 'LOG_BITMASK = 0: التسجيل معطل.'),
    'pa_ekf_type': ('AHRS_EKF_TYPE = {v}: Alışılmadık EKF seçimi.', 'AHRS_EKF_TYPE = {v}: unusual EKF selection.', 'AHRS_EKF_TYPE = {v}: اختيار EKF غير معتاد.'),
    'pa_gps_off': ('GPS_TYPE = 0: GPS kapalı.', 'GPS_TYPE = 0: GPS disabled.', 'GPS_TYPE = 0: GPS معطل.'),
    'pa_rtl_autoland': ('RTL_AUTOLAND = 0: Eve dönünce otomatik iniş yapılmaz, araç evin üzerinde döner (bilgi).', 'RTL_AUTOLAND = 0: no automatic landing after RTL; the plane loiters over home (info).', 'RTL_AUTOLAND = 0: لا هبوط آلي بعد العودة؛ تحوم الطائرة فوق نقطة الإقلاع (معلومة).'),
    'pa_notch_off': ('Harmonik çentik filtresi kapalı; titreşim kontrolü zayıf olabilir (bilgi).', 'Harmonic notch filter disabled; noise rejection may be weak (info).', 'مرشح الشق التوافقي معطل؛ قد يكون كبت الضجيج ضعيفاً (معلومة).'),
    # v1.0.2: profiller, anomali, rüzgâr, pilot
    'dom_motors': ('Motorlar (multikopter)', 'Motors (multicopter)', 'المحركات (متعدد المراوح)'),
    'dom_vtol': ('VTOL / geçişler', 'VTOL / transitions', 'VTOL / الانتقالات'),
    'mot_imbalance': ('Motor dengesizliği: {ch} ortalamadan {v} µs farklı (ağırlık merkezi, bükük motor kolu veya zayıf motor/ESC).', 'Motor imbalance: {ch} differs {v} µs from the average (CG, twisted arm or weak motor/ESC).', 'عدم توازن المحركات: {ch} يختلف {v} µs عن المتوسط (مركز الثقل أو ذراع ملتوية أو محرك/ESC ضعيف).'),
    'mot_headroom': ('Motor payı düşük: en yüksek motor çıkışı MOT_PWM_MAX değerine {v} µs yakın; araç ağır veya güçsüz.', 'Low motor headroom: highest motor output is within {v} µs of MOT_PWM_MAX; vehicle is heavy or underpowered.', 'هامش المحرك منخفض: أعلى خرج ضمن {v} µs من MOT_PWM_MAX؛ المركبة ثقيلة أو ضعيفة.'),
    'vtol_summary': ('{n} VTOL⇄uçak geçişi, VTOL modlarında {t} dk.', '{n} VTOL⇄plane transitions, {t} min in VTOL modes.', '{n} انتقال VTOL⇄طائرة، {t} دقيقة في أوضاع VTOL.'),
    'vtol_assist_off': ('Q_ASSIST_SPEED = 0: Düşük hızda VTOL motor desteği kapalı; stall riskine karşı açılması önerilir.', 'Q_ASSIST_SPEED = 0: VTOL assist at low airspeed is disabled; enabling it protects against stalls.', 'Q_ASSIST_SPEED = 0: دعم محركات VTOL عند السرعة المنخفضة معطل؛ يُنصح بتفعيله.'),
    'vtol_trans_short': ('Q_TRANSITION_MS = {v}: Geçiş süresi çok kısa.', 'Q_TRANSITION_MS = {v}: transition time is very short.', 'Q_TRANSITION_MS = {v}: زمن الانتقال قصير جداً.'),
    'vtol_thr_full': ('VTOL gazı uçuşun %{v} kadarında tam; kaldırma gücü sınırda.', 'VTOL throttle at maximum for {v}% of hover; lift margin is marginal.', 'خانق VTOL في الحد الأقصى {v}% من الوقت؛ هامش الرفع حرج.'),
    'wind_high': ('Logdan kestirilen ortalama rüzgâr {v} m/s (profil sınırı {lim} m/s): uçuş rüzgâr limitine yakın/üstünde yapılmış.', 'Estimated mean wind from the log {v} m/s (profile limit {lim} m/s): the flight was at/over the wind limit.', 'متوسط الرياح المقدر من السجل {v} م/ث (حد الملف {lim} م/ث).'),
    'anom_ev': ('Yapay zekâ anomali: alışılmadık {f} (puan {s})', 'AI anomaly: unusual {f} (score {s})', 'شذوذ ذكاء اصطناعي: {f} غير معتاد (الدرجة {s})'),
}


def T(key, lang='tr', **a):
    i = LANGS.index(lang) if lang in LANGS else 0
    v = S.get(key)
    if v is None:
        return key
    s = v[i]
    try:
        return s.format(**a)
    except Exception:
        return s


def render(f, lang='tr', tfmt=None):
    """Analiz bulgusunu ({'k','a'}) metne çevirir."""
    k = f['k']; a = dict(f.get('a', {}))
    if tfmt and 't' in a and isinstance(a['t'], (int, float)):
        a['t'] = tfmt(a['t'])
    if k == 'ev_mode':
        r = K.MODE_REASON.get(a.get('reason', -1))
        return f"{ {'tr': 'Mod', 'en': 'Mode', 'ar': 'الوضع'}[lang] }: {a['mode']}" + (f" — {K.tr3(r, lang)}" if r else '')
    if k == 'ev_err':
        return K.err_text(a['sub'], a['code'], lang)
    if k == 'ev_ev':
        return K.ev_text(a['id'], lang)
    if k == 'ev_msg':
        return a['msg']
    if k == 'anom_ev':
        from .anomaly import fname
        a['f'] = fname(a.get('f'), lang)
    return T(k, lang, **a)


def chain_step(c, lang, tfmt):
    st = c['step']
    if st == 'mode':
        r = K.MODE_REASON.get(c.get('reason', -1))
        return T('step_mode', lang, mode=c['mode'], reason=K.tr3(r, lang) if r else '-')
    if st.startswith('end_'):
        return T('step_' + st, lang)
    return T('cause_' + st, lang)


def vkey(verdict):
    """Karar anahtarı: 'sorunlu' kararın derecesi küçükse 'incident_minor' (ayrı etiket ve renk)."""
    v = (verdict or {}).get('kind') or 'normal'
    return 'incident_minor' if v == 'incident' and (verdict or {}).get('severity') == 'minor' else v
