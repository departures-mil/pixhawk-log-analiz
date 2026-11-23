# Pixhawk Log Analiz

Pixhawk / ArduPilot **.BIN** (DataFlash) ve **.tlog** uçuş loglarını analiz eden, öğretici kalitede Windows masaüstü programı.
Türkçe · English · العربية (sağdan sola).

## Öne çıkanlar
- **Kırım / sorunlu / normal uçuş kararı**, kanıtlarıyla birlikte
- **Kök neden motoru** (GPS, EKF, batarya, radyo, stall, titreşim, pusula, güç, kontrol) ve olay zinciri, nasıl önlenir
- **0–100 sağlık puanı** ve trafik ışığı (9 alan), **uçuş aşamaları**, **PARM denetimi**
- **Antetli DOCX / PDF rapor**: grafikler, her grafiğin altında ders notları ve eşikler, QR ile doğrulama, kurum antet şablonları
- **Yapay zekâ danışman**: logun içine bakarak cevap verir ("Hangi saniyede kalkış yapıldı?"). Online: kullanıcının kendi Claude API anahtarı. Offline: yerleşik kural motoru
- **Harita** (offline karo önbelleği), **3B uçuş tekrarı**, **olay zaman çizelgesi**
- **Alıştırma modu**, **senaryo kütüphanesi** (7 eğitim senaryosu), **toplu analiz**, **arşiv ve trend**
- **Log mesajları kütüphanesi** (351 mesaj, alan açıklamaları) ve ayrı **parametre kütüphanesi** (5.700+ parametre)
- **Eşitleme**: GitHub (kendi gizli gist'iniz) ve internetsiz **aynı modem (LAN)**; kayıtlar silinmeden birleştirilir
- **Tek tuşla güncelleme** (yüzde, MB, kalan, hız), ayarların sonunda **admin ile iletişim**

## İndir
[Releases](https://github.com/departures-mil/pixhawk-log-analiz/releases/latest) sayfasından `PixhawkLogAnaliz-Setup-x.y.z.exe` kurulum paketini indirip çalıştırın (yönetici izni gerekmez; Başlat menüsü ve masaüstü kısayolu oluşturulur, Denetim Masası'ndan kaldırılabilir). Sonraki sürümler program içindeki **⬇ Güncelle** düğmesiyle tek tıkla, sessizce kurulur ve program yeniden açılır. Kurulum istemeyenler için taşınabilir `PixhawkLogAnaliz.exe` de yayınlanır.

**Antet:** Ayarlar > *Antet ekle* bölümünden tam sayfa antet görseli (JPG/PNG) veya Word antet şablonu (.docx) yüklenir; DOCX ve PDF raporların tüm sayfalarına arka plan olarak uygulanır, üst boşluk otomatik ayarlanır. Besmele seçeneği yalnızca ilk sayfaya eklenir. Hazır antet: Savunma Bakanlığı – Sabit Kanat.

## Geliştirici
```
pip install -r requirements.txt
python run.py
```
`app/version.py` içindeki sürüm artırılıp `main`e gönderildiğinde GitHub Actions exe'yi ve Inno Setup kurulum paketini derler, sessiz kurulum testini yapar ve yeni sürümü otomatik yayınlar.
