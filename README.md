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
[Releases](https://github.com/departures-mil/pixhawk-log-analiz/releases/latest) sayfasından `PixhawkLogAnaliz_Setup_x.y.z.exe` kurulum paketini indirip çalıştırın (yönetici izni gerekmez; Başlat menüsü ve masaüstü kısayolu oluşturulur, Denetim Masası'ndan kaldırılabilir). Sonraki sürümler program içindeki **⬇ Güncelle** düğmesiyle tek tıkla, sessizce kurulur ve program yeniden açılır. Kurulum istemeyenler için taşınabilir `PixhawkLogAnaliz.exe` de yayınlanır.

**Antet:** Ayarlar > *Antet ekle* bölümünden tam sayfa antet görseli (JPG/PNG) veya Word antet şablonu (.docx) yüklenir; DOCX ve PDF raporların tüm sayfalarına arka plan olarak uygulanır, üst boşluk otomatik ayarlanır. Besmele seçeneği yalnızca ilk sayfaya eklenir. Hazır antet: Savunma Bakanlığı – Sabit Kanat.

## Geliştirici
```
pip install -r requirements.txt
python run.py
```
`app/version.py` içindeki sürüm artırılıp `main`e gönderildiğinde GitHub Actions exe'yi ve Inno Setup kurulum paketini derler, sessiz kurulum testini yapar ve yeni sürümü otomatik yayınlar.

## v1.0.7
- ✦ **Asistan Agent** (`app/ui/fc_agent.py` = ortak-cekirdek/python/fc_agent.py, bağlantı `app/ui/ajan.py`): bütün programlardaki
  çalışmayı sayılarla izler (içerik yok), çevrim dışı kurallar + kullanıcının kendi Gemini/Claude anahtarıyla öneri; bildirim + sağ altta ✦ panel;
  Ayarlar'da "Admin ile iletişim"in önünde kart. Aynı bilgisayardaki programlarla %APPDATA%/FalconCekirdek/agent üzerinden paylaşım.
