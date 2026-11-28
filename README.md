# Pixhawk Log Analiz

Pixhawk / ArduPilot **.BIN** (DataFlash) ve **.tlog** uçuş loglarını analiz eden, öğretici kalitede Windows masaüstü programı.
Türkçe · English · العربية (sağdan sola).

## Öne çıkanlar
- **Kırım / sorunlu / normal uçuş kararı**, kanıtlarıyla birlikte
- **Kök neden motoru** (GPS, EKF, batarya, radyo, stall, titreşim, pusula, güç, kontrol, motor/ESC/pervane) ve olay zinciri, nasıl önlenir
- **0–100 sağlık puanı** ve trafik ışığı (9 alan), **uçuş aşamaları**, **PARM denetimi**
- **Antetli DOCX / PDF rapor**: grafikler, her grafiğin altında ders notları ve eşikler, QR ile doğrulama, kurum antet şablonları
- **Yapay zekâ danışman**: logun içine bakarak cevap verir ("Hangi saniyede kalkış yapıldı?"). Online: kullanıcının kendi Claude API anahtarı. Offline: yerleşik kural motoru
- **Harita** (offline karo önbelleği), **3B uçuş tekrarı**, **olay zaman çizelgesi**
- **Alıştırma modu**, **senaryo kütüphanesi** (7 eğitim senaryosu), **toplu analiz**, **arşiv ve trend**
- **Log mesajları kütüphanesi** (351 mesaj, alan açıklamaları) ve ayrı **parametre kütüphanesi** (5.700+ parametre)
- **Parametre Merkezi (tam liste)**: ArduPilot'un bütün araç sınıfları (Plane, Copter, Heli, Rover, Sub, Blimp, AntennaTracker, AP_Periph) için tüm parametreler; açıklama, birim, aralık, seçenek ve bitmask anlamları TR/EN/AR; .param dosyası/logdaki PARM inceleme (varsayılandan farklı ve riskli değerler), iki seti karşılaştırma, param arşivi (araç/tarih/not), dışa aktarma; ⭐ yıldız ve 🔑 anahtar işaretleri, kendi listeleriniz, kritik parametreler ve kartlarla öğrenme; "şu davranışı nasıl elde ederim" sorularına online/offline yapay zekâ cevabı
- **Ders kitabı (PDF)**: kütüphane, senaryolar ve alıştırmalardan otomatik, antetli eğitim kitabı (TR/EN/AR, içindekiler, cevap anahtarı)
- **Gerçek kaza logları**: ArduPilot forumundaki gerçek kırım loglarıyla teşhis doğruluğu ölçülür (bkz. [sonuçlar](docs/kirim_test_sonuclari.md)); logu indirip programda açma
- **Anlatımlı video (MP4)**: 3B tekrarı ders adımları, altyazı ve sesli anlatımla sınıfta oynatmak için dışa aktarma
- **Uçuş bilgileri formu** (log açılırken): kırım yaşandı mı, motor tipi (elektrikli hücre sayısı / benzinli cc ve zamanı), gövde tipi (normal, V-tail, elevon/uçan kanat, VTOL, tail-sitter, çok rotorlu…), otopilot marka/model (Pixhawk 1/2.4.8, Cube Black/Orange/Orange+, Pixhawk 4/5X/6C/6X, Matek, Kakute…), GPS, hava hızı sensörü vb. Logdan okunabilenler otomatik dolar, boşlar isteğe bağlı yapay zekâ ile önerilir; teşhis eşikleri cevaplara göre ayarlanır. Seçenekler Ayarlar > *Log soruları* bölümünden eklenip çıkarılır
- **"Neden düştü?"**: kırım loglarında tek cümlelik kesin hüküm, güven yüzdesi, kanıtlar, saniye saniye olay zinciri, kırım anı ve konumundaki hava durumu, ne yapılmalı
- **Problem Çözücü**: belirtileri işaretleyin ya da kendi cümlenizle yazın; 23 çapraz test (IMU'lar arası, GPS↔barometre, istenen↔gerçek tutum, frekans analizi, servo doygunluğu, ESC telemetrisi, hava…) kanıtla sıralanır, parametre bazında adım adım çözüm verilir
- **Arşivde kırım işareti** ve filtre; **üst çubukta** log bilgisi, hızlı işlemler ve dil seçimi
- **Havacılık terim sözlüğü**: arm/disarm, pre-arm, failsafe, yatış/yunuslama/sapma gibi terimler bütün TR/AR çevirilerde literatüre uygun
- **Eşitleme**: GitHub (kendi gizli gist'iniz) ve internetsiz **aynı modem (LAN)**; kayıtlar silinmeden birleştirilir
- **Uçuş öncesi .param risk kontrol listesi** (Parametre Merkezi > ✅): failsafe, batarya eşikleri (hücre sayısına göre), arm kontrolleri, pusula/ivmeölçer kalibrasyonu, servo/motor çıkışları, kumanda kalibrasyonu, mod anahtarı, eve dönüş irtifası, log; UÇUŞA HAZIR / DİKKAT / UÇMAYIN kararı, önerilen düzeltmelerle yeni .param kaydetme
- **PID / TECS ayar önerileri** (Parametre Merkezi > 🎛): logdaki PIDR/PIDP/PIDY (ya da RATE) ve TECS kayıtlarından kazanç oranı, gecikme, salınım frekansı, I terimi yükü, tırmanma/alçalma kapasitesi, düz uçuş gazı ölçülür; araç tipine göre (sabit kanat, VTOL, multikopter, helikopter) en çok ±%25'lik güvenli adımlarla somut öneri ve .param çıktısı. Kayıt hızı düşük, yerde ya da yanlış modda alınmış veriden öneri üretilmez
- **Tek tuşla güncelleme** (yüzde, MB, kalan, hız): önce **yalnızca değişen kısımlar** (yama) indirilir — her yayında son 5 sürüm için ayrı yama üretilir, CI'da eski dosyaya uygulanıp yeni sürümle birebir aynı olduğu doğrulanır, tam dosyanın %70'inden büyük yama yayınlanmaz; program yamayı SHA-256 ile doğrulayıp kurulu dosyalarla birleştirir, sorun olursa kendiliğinden tam dosyaya geçer. Ayarların sonunda **admin ile iletişim**

## İndir
[Releases](https://github.com/departures-mil/pixhawk-log-analiz/releases/latest) sayfasından `PixhawkLogAnaliz_Setup_x.y.z.exe` kurulum paketini indirip çalıştırın (yönetici izni gerekmez, kullanıcı başına `%LOCALAPPDATA%\Programs\Pixhawk Log Analiz`; Başlat menüsü ve masaüstü kısayolu oluşturulur, Denetim Masası'ndan kaldırılabilir). Sonraki sürümler sağ üstteki **Güncelle** düğmesiyle tek tıkla iner (önce yalnızca değişen kısımlar, SHA-256 doğrulamalı) ve program yeniden açılır. Kurulum istemeyenler için taşınabilir `PixhawkLogAnaliz.exe` de yayınlanır.

**Antet:** Ayarlar > *Antet ekle* bölümünden tam sayfa antet görseli (JPG/PNG) veya Word antet şablonu (.docx) yüklenir; DOCX ve PDF raporların tüm sayfalarına arka plan olarak uygulanır, üst boşluk otomatik ayarlanır. Besmele seçeneği yalnızca ilk sayfaya eklenir. Hazır antet: Savunma Bakanlığı – Sabit Kanat.

## Geliştirici
```
pip install -r requirements.txt
python run.py
python -m pytest -q tests          # offscreen Qt: pencere, üst çubuk, ayarlar, eşitleme kuralı, güncelleme, köprü
```
`app/version.py` (+ `app/news.py` en üstte notlar) artırılıp `main`e gönderildiğinde GitHub Actions: test → Windows derleme
(tek exe + klasör, Inno Setup, sessiz kur/yükselt/kaldır, win-app zip'inin kurulu klasörden bayt bayt üretilebildiği denetimi) →
ortak `reusable-release.yml` (latest.json, son 5 sürümden yamalar) ile yayın. Ayrıntı: `CLAUDE.md`.

## v1.1.0 — ortak çekirdek (fccore)
- Falcon görünümü + renk şeması seçici (eski görünüm **Klasik**), koyu/açık/otomatik, yazı boyutu; sağ üstte Eşitle · Wi-Fi · Güncelle · tema · dil | Küçült · Orta · Tam ekran · Kapat; her açılış tam ekran
- Güncelleme `latest.json` + FCD1 yama (win-app = kurulu klasörün zip'i, win-setup = Inno kurulumu, win-exe = taşınabilir exe)
- Eşitleme (GitHub gist + LAN) ortak kurala uyar: uzak silme arşivlenir, çakışmada eski hal eşitleme yedeğine (Ayarlar → Eşitleme → yedeği dışa aktar)
- İlk açılış rehberi, Neler yeni, Kullanım Limitleri (AI çağrıları), otomatik hata raporu, Admin ile iletişim (ortak gelen kutusu, en sonda)

## v1.0.7
- ✦ **Asistan Agent** (`app/ui/fc_agent.py` = ortak-cekirdek/python/fc_agent.py, bağlantı `app/ui/ajan.py`): bütün programlardaki
  çalışmayı sayılarla izler (içerik yok), çevrim dışı kurallar + kullanıcının kendi Gemini/Claude anahtarıyla öneri; bildirim + sağ altta ✦ panel;
  Ayarlar'da "Admin ile iletişim"in önünde kart. Aynı bilgisayardaki programlarla %APPDATA%/FalconCekirdek/agent üzerinden paylaşım.

## v1.1.17 — Plane normal uçuşları ve kör test
- 160 yeni Plane konusu (`planenormal`, sürüm/beta + normal uçuş aramaları; loglar `refetch.yml` ile `bench-plane` taslak sürümüne). Etiketler `labels._pn_doc`; program Copter okursa hariç.
- Kör ölçüm (v1.1.16 kodu, 125 Plane logu): doğruluk .704, duyarlılık .333 (12 kırım), özgüllük .743.
- `_refine_severity`: Plane kanıtsız olay + inişten sonra log ≥40 s → minor; tek kanıt log kesildi/bitti ve `_still_on_ground` (son 3 s GPS hızı ≤2, irtifa ≤5 m) → minor.
- 271 Plane logu (125/146): doğruluk .838, duyarlılık .824, özgüllük .849, kök neden .596. Tüm 783 log: doğruluk .854.

## v1.1.16 — Plane kök neden teşhisi
- `Analysis.airspeed_src()`: ARSP → CTUN.Aspd/As → TECS.sp → CTUN.SAs (uçuş medyanı ≥3 m/s); sağlık, stall, özet, diag2, solver, grafik bunu kullanır. Stall için kaynak yoksa GPS.Spd.
- `_vtol_sat` (QTUN akarken ≥1,2 s motor tavanda + tutum hatası ≥90°, sapma doygunluktan ≤2 s önce), `upset` (≥100° yatış → olay), Plane RC kaybı (failsafe metni, RSSI→0), öncelikler: pusula geri, RC kaybı (>5 s sonra) ve stall (`stall_t`, −3,5…+8 s) kontrolün önüne.
- Plane 146 log: kök neden 47/86 → 54/86, duyarlılık .903, özgüllük .818 değişmedi. Testler `tests/test_plane_rules.py`. Tarama: `.github/workflows/planenormal.yml` (`crashbench.py planenormal`, sürüm/beta konuları + ayar konuları → `pn_threads.json.gz`).

## v1.1.15 — Plane yanlış alarmları
- `analysis._refine_severity`: Plane'de kanıtsız 'ciddi olay' → toplam uçuş ≥400 s ise ya da `_calm_disarm` (uçuş sonundan ≥5 s sonra, GPS hızı ≤3 m/s iken disarm) varsa 'minor'. `cr_msg` artık `crash_dump` dosya mesajını saymaz.
- Etiket düzeltmeleri: 138733 (= 138573 aynı log), 144973, 122215 kırım; 108511 hariç. Ölçüm 659 log: doğruluk .873, duyarlılık .867, özgüllük .89; Plane 147: özgüllük .70 → .82, duyarlılık .90.

## v1.1.14 — Log Gezgini ve Plane ağırlıklı yeni gerçek loglar
- **Log Gezgini** (`app/ui/pages_g.py` `LogBrowserPage`, `app/core/logbrowse.py`): MP "Review a Log" benzeri; logdaki tüm mesaj/alan ağacı (çok örnekli `NAME[k]`, FMTU/UNIT/MULT birimleri, logmsgs.json açıklamaları), sol/sağ eksen, mod şeritleri, ERR/MSG/EV, parametre sınır çizgileri, hazır grafikler (`PRESETS`), sorunlu bölgeler (`problems`), uzman adımları, alıştırma (`check_guess`), veri tablosu/harita/parametre sekmeleri. Metinler `i18n13.py`.
- Yeni kurallar: `analysis._switch_disarm` (ARM.Method=2 / disarm anahtarı → `pilot`), `_impact_end` (Plane: çarpmayla kesilen logda `power` yerine `control`). `LOADER_VER=8`.
- 249 yeni etiket (`labels._more_doc`, `labels._plane_doc`; SITL/tezgâh logları `exclude`). Ölçülebilir 659 gerçek log: 505 kırım/olay, 154 normal; Plane 147 (110 kırım/olay, 37 normal).

## v1.1.13 — Gerçek Kaza Logları: sıralama ve süzgeçler
- `CrashLibPage`: başlığa tıklayınca sıralama (`sort_by`, `_skey`), süzgeçler araç · etiket · kök neden (uzman/program/biri/ikisi) · program sonucu, `clear_filters`. Metinler `i18n12.py` (`clf_*`).

## v1.1.12 — Uzman tecrübeleri: gerçek kırımlardan dersler
- `app/core/expert.py`: forumdaki gerçek kırım konularında uzmanların teşhis ve öğütlerinden 32 ders (kural · logda nereye bakılır · ne yapılır ·
  parametreler, TR/EN/AR) ve 10 altın kural. `tools_data/expert_tags.py` (+ `expert_rx.py`) uzman yanıtlarını tarayıp her konuya ders atar →
  `app/data/expert_cases.json`. Gerçek Kaza Logları sayfası iki sekmeli (Gerçek konular + Uzman tecrübeleri), analiz özetinde "Uzmanlar ne diyor?",
  Soru Bankası'nda `experts` konusu (96 soru), eğitim kitabında `experts` bölümü.
- 136 holdout logu etiketlendi (toplam 461 etiket); yeni kök neden `pilot`; `_poor_tune`, titreşim önceliği, `_refine_severity`.
  Ölçüm (454 log): doğruluk %89, duyarlılık %90, özgüllük %85, kök neden %52 (ikincillerle %72). Ek tarama: `.github/workflows/more.yml`.

## v1.1.11 — Sınav sekmesi: görselli grafik soruları, kâğıt sınav, optik okuma, telefonla sınav
- **Sınav** sekmesi (`app/ui/pages_x.py` + `pages_c.ExamPage`): Sınav hazırla (soru sayısı, kaynak/konu/seviye/tür/uçuş/ipucu süzgeci, elle ekleme ya da otomatik doldurma, açık logdan/senaryodan görselli soru üretimi) · Eğitimci (kâğıt sınav, optik okuma, telefonla okutma/sınav, yorum puanlama) · Öğrenci.
- Görselli havuz `app/data/visq.json` + `app/data/visq/*.png` (`tools_data/build_visq.py`, `app/core/visq.py`): uzman etiketli gerçek kırım/normal loglar + sentetik senaryolar; ipuçsuz grafikler `charts.quiz(True)` ile (kırım çizgisi, karar kartı ve motor olay işaretleri gizli).
- Açık uçlu (yorum) sorular: `type='open'`, `model`, `kw`; puan eğitimciden (0/0,5/1), yoksa anahtar kavram önerisi (`visq.score_open`, `exam.regrade`).
- Kâğıt sınav (`app/core/paper.py`): kodlu kitapçık, QR'ı düz metin cevap anahtarı (telefon kamerası internetsiz okur), optik form (`app/core/omr.py`, sinav-hazirlama `renderer/omr.js` düzeni ve okuma yöntemi).
- Telefon (`app/core/canli.py`, sinav-hazirlama `src/canli.js` benzeri): aynı Wi-Fi'da 47880–47885 portunda sınav ve form okutma sayfası; sonuçlar `result` kaydına `via='phone'|'omr'` ile yazılır.

## v1.1.10 — soru bankası ve sınav sistemi
- **Soru Bankası** (`app/ui/pages_q.py`, `app/core/qbank.py`, sorular `app/core/qbank_d1..d4.py`): 16 konu × 3 seviyede 126 elle yazılmış öğretici soru (TR/EN/AR, açıklamalı) + log mesajı / kritik parametre kütüphanelerinden üretilen ~400 soru.
- Tamamı görüntülenir ve düzenlenir: arama, süzgeç, ekle/düzenle/kopyala/sil/geri al, `.pxbank` dışa/içe aktarma. Değişiklikler arşivde `qbank` kaydı olarak tutulur ve GitHub/LAN ile eşitlenir.
- Alıştırma Modu: kaynak (karışık / banka / log / yanlışlarım; `settings['qbank_stats']`), konu, seviye, soru sayısı. Sınav: bankadan (isteğe bağlı logla karışık) konu/seviye seçimli 3–100 soru (`exam.bank_questions`).

## v1.1.9 — log mesajlarında açıklama araması (TR/EN/AR)
- Log Mesajları Kütüphanesi araması mesaj/alan adlarına ek olarak açıklamalarda ve alan açıklamalarında, üç dilde birden arar (`app/core/msgsearch.py`): aksan duyarsız, eş anlamlılar, çok kelime = hepsi, puanlı sıralama.
- Listede eşleşen alanlar, ayrıntıda vurgulama ve eşleşmenin bulunduğu dildeki açıklama.

## v1.1.8 — video eşleme, OSD ve kendi grafiğim
- **Video ve OSD** (`app/ui/pages_v.py`, `app/core/vidsync.py`): ana video + ikinci (FPV/DVR) video, log ile eşleme (kayıt saati / olay / ince ayar), grafik-harita-mod tablosu tıklaması videoyu o ana götürür; oynatırken imleç, harita ve 3B izler.
- Logdan çizilen OSD (öğeler seçilebilir) ve birleştirilmiş MP4 (tek / resim içinde resim / yan yana, harita + irtifa paneli; ffmpeg = imageio-ffmpeg).
- **Kendi Grafiğim** (`app/core/customchart.py`): log alanları ve güvenli formüller, parametre eşik çizgileri, görünen aralık istatistikleri ve eşik üstü/altı süre; grafikler `settings['custom_charts']`'a kaydedilir.

## v1.1.7 — her değerin kaynağı (log alanı + parametre)
- Grafik çizgileri MESAJ.ALAN adıyla, eşik çizgileri parametre adı ve değeriyle; her grafiğin altında kaynak şeridi.
- Grafikler sayfasında "Kaynak" sekmesi: alan/parametre anlamı, değer, varsayılan ve Mission Planner'da yolu (`app/core/sources.py`).
- Analiz özeti, temel bilgiler, aşamalar, mod tablosu ve motor olaylarında kaynak satırı (rapor dahil).

## v1.1.6 — güncelleme düzeltmesi
- Güncellerken açılan siyah "find" penceresi ve takılma giderildi (takas betiği gizli konsolda çalışır).

## v1.1.5 — log canavarı: modlar, isimli motorlar, stickler, 20 etkileşimli grafik
- **Uçuş modları** her grafikte renkli bant + ad + gerçek saat; mod tablosu (başlangıç/bitiş/süre/değişim nedeni/modun görevi), haritada moda göre renk
- **Motor çıkışları**: motorlar yeriyle isimli (FRAME_CLASS/TYPE, Q_FRAME_*), yerleşim çizimi, durma/doyma uyarısı ve olay anı yakın çekimi; VTOL'de kaldırma + itiş motoru
- **Görevli kanallar** (SERVOn_FUNCTION): Roll/Pitch/Yaw/Gaz, ters kanal işareti; **stick hareketleri** (RCMAP) ve mod anahtarı; 3B tekrarda canlı stick
- **Yeni grafikler**: özet panosu, hız/rüzgâr, TECS, PID, navigasyon, GPS doğruluğu, FFT, IMU/baro, batarya mAh ve kalan süre, ESC, EKF yenilikleri
- **Etkileşim**: yakınlaştırma, kaydırma, PNG, ortak imleç (harita/3B), Shift+tıklama cetvel, fareyle saat/mod/TimeUS
- **Mission Planner**: her grafik için Review Log alanları, ilgili parametreler, önemli anların TimeUS değeri, `mavgraphs` biçiminde hazır grafik dosyası

## v1.1.4 — dört seviyeli karar, fizik modeli, resmî olay raporu
- **Kaza · Ciddi sorun · Küçük uyarı · Normal**: kanıtı zayıf sorunlar "küçük uyarı" olarak ayrılır
- **Kontrolsüz düşüş** (irtifa kaybı, düşüş hızı, açı) ve **VTOL motor kaybı**; motor numarası SERVOn_FUNCTION eşlemesinden, kronik zayıf motor
- **Fizik modeli**: itki/ağırlık (askı gazından), askı gücü/akımı, tahmini uçuş süresi; sabit kanatta seyir gazı
- **Aynı aracın geçmişi**: seri numarasına göre arşivdeki uçuşlarla karşılaştırma (alışılmadık titreşim, akım, gaz…)
- **Kalibre güven**: kök neden güveni gerçek kazalardaki isabete çevrildi (ECE 0,17 → 0,02)
- **Kanıta dayalı YZ**: açıklama yalnız logdaki ölçümleri kullanır; veride olmayan zaman damgası işaretlenir
- **Resmî olay raporu** (DOCX/PDF, TR/EN/AR): olay bilgileri, zaman çizelgesi, kök neden, katkı faktörleri, öneriler, imza/onay
- Ölçüm (323 uzman etiketli log, yalnız kurallar): doğruluk %81 → %86, kaza yakalama %89 → %92, özgüllük %66 → %75. Öğrenen model kaza yakalamayı düşürdüğü için karar vermiyor, yalnız görüş gösteriyor

## v1.1.1 — daha gerçekçi ve dakik teşhis
- **Test seti 326 gerçek loga çıktı** (210 kaza, 116 normal uçuş; her konunun uzman yanıtları elle okunarak etiketlendi). Ayrıntı: [sonuçlar](docs/kirim_test_sonuclari.md)
- **"Teşhis doğru muydu?"** düğmesi (Neden düştü? bölümü): evet/kısmen/hayır, gerçek sonuç ve neden; kişisel veri göndermez, internet yoksa sıraya alınıp sonra gönderilir
- **Kaçan kazalar**: kalkıştan/inişten sonraki takla, uçuşta log kesilmesi, iniş algılamada yanılma, son saniyelerde yön (yaw) kontrol kaybı
- **Motor/ESC**: MOT_SPIN_MAX'a göre motor doygunluğu, karşı motorun tabana düşmesi, ESC telemetrisi; motor numarasıyla kanıt
- **Sabit kanat**: ters ya da yetersiz kumanda yüzeyi, ağırlık merkezi (burun/kuyruk ağır), hava hızı sensörü kalibrasyonu
- **Batarya iç direnci** (hücre başına mΩ), **titreşim frekansı** ve çentik filtresi değerlendirmesi
- **Veri yetersizliği uyarısı**: eksik log kayıtları (RCOU, VIBE, ATT, akım, PID, ESC, GPS) listelenir, güven yüzdesi buna göre düşer
- **Öğrenen ikinci görüş (ML)**: uzman etiketli 323 logla eğitildi; leave-one-out ölçümünde doğruluk %81 → %86, özgüllük %66 → %85 (duyarlılık %89 → %87). Yalnız sınırdaki kararları düzeltir
