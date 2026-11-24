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

## v1.1.1 — daha gerçekçi ve dakik teşhis
- **Test seti 326 gerçek loga çıktı** (210 kaza, 116 normal uçuş; her konunun uzman yanıtları elle okunarak etiketlendi). Ayrıntı: [sonuçlar](docs/kirim_test_sonuclari.md)
- **"Teşhis doğru muydu?"** düğmesi (Neden düştü? bölümü): evet/kısmen/hayır, gerçek sonuç ve neden; kişisel veri göndermez, internet yoksa sıraya alınıp sonra gönderilir
- **Kaçan kazalar**: kalkıştan/inişten sonraki takla, uçuşta log kesilmesi, iniş algılamada yanılma, son saniyelerde yön (yaw) kontrol kaybı
- **Motor/ESC**: MOT_SPIN_MAX'a göre motor doygunluğu, karşı motorun tabana düşmesi, ESC telemetrisi; motor numarasıyla kanıt
- **Sabit kanat**: ters ya da yetersiz kumanda yüzeyi, ağırlık merkezi (burun/kuyruk ağır), hava hızı sensörü kalibrasyonu
- **Batarya iç direnci** (hücre başına mΩ), **titreşim frekansı** ve çentik filtresi değerlendirmesi
- **Veri yetersizliği uyarısı**: eksik log kayıtları (RCOU, VIBE, ATT, akım, PID, ESC, GPS) listelenir, güven yüzdesi buna göre düşer
- **Öğrenen ikinci görüş (ML)**: uzman etiketli 323 logla eğitildi; leave-one-out ölçümünde doğruluk %81 → %86, özgüllük %66 → %85 (duyarlılık %89 → %87). Yalnız sınırdaki kararları düzeltir
