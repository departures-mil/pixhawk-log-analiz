# Pixhawk Log Analiz

ArduPilot .BIN/.tlog analiz programı. PySide6 masaüstü (yalnız Windows dağıtımı), PyInstaller, Inno Setup kurulumu.
Arayüz `app/ui/*` (Türkçe/English/العربية, `app/ui/i18n*.py`), çekirdek analiz `app/core/*`, giriş `app/main.py`.

## Ortak çekirdek (v1.1.0'dan beri)
- `fccore/` = `departures-mil/ortak-cekirdek` `qt/fccore` gömülü kopyası; commit `cekirdek/VERSION`'da. Çekirdek deposunu buradan
  değiştirme. Yerel düzeltme: `fccore/updater.py` takas betiğinin `:hata` dalı eski exe'yi `--fc-update-failed` ile yeniden açar.
- Yapıştırıcı `app/ui/kabuk.py`: depo (`%APPDATA%\PixhawkLogAnaliz\fccore.json`), dil köprüsü (fccore `i18n.set` ↔ `settings['lang']`,
  dil değişince sayfalar yeniden kurulur), `klasik` şema (v1.0.x renkleri), uygulama QSS'i (`#primary`, `#h1/#h2/#muted`, `#statusbar`,
  `QProgressBar#appbar`), açık temada eski koyu HTML renk eşlemesi (`themed_html`), güncelleme (`Updater` + `UpdateController`; Inno
  kurulumu sessiz çalıştırılıp program yeniden açılır; takas betiği kurulum klasörü dışında çalışır), çökme (`app/core/crash.py`
  `send_core`: son işlemler izi eklenir), Kullanım Limitleri (`ai.gemini/anthropic/pollinations`), ilk açılış rehberi (yalnız gemini/anthropic),
  "neler yeni" (`app/news.py`).
- Ana pencere `app/ui/main_window.py` = `FcWindow` (her açılış tam ekran) + Falcon kenar çubuğu + fccore `TopBar`
  (hızlı işlemler · Eşitle · Wi-Fi · Güncelle · tema · dil | Küçült · Orta · Tam ekran · Kapat). Ayarlar: Görünüm kartı en üstte,
  … Otomatik hata raporu · Hakkında · Asistan Agent · **Admin ile iletişim EN SON** (fccore contact).
- Eşitleme: kullanıcının kendi GitHub gist'i + LAN (`app/core/sync.py`). Birleştirme `Archive.merge` → `fccore.lanmerge` kuralı:
  uzak silme yerelde arşivlenir (deleted=1, veri korunur), çakışmada kaybeden ve ezilen her değer `sync_backup` tablosuna;
  Ayarlar → Eşitleme → "Yedeği dışa aktar". Firebase yok (bulut verisi kullanıcının gist'i).

## Kurallar (Milen)
- Milen "BAŞLA" demeden yeni iş başlatma. Yazışma dili Türkçe.
- Sürüm semver `X.Y.Z` (`app/version.py`), etiket `vX.Y.Z`. Yeni sürümde `app/news.py` NEWS dizisinin EN ÜSTÜNE tr/en/ar notu
  (testler denetler; CI `tools_ci/release_notes.py` ile release-notes.json üretir).
- Yayın yalnız GitHub Releases + `latest.json` + FCD1 yama (ortak `reusable-release.yml`). Kanallar: `win-app`
  (`python -m fccore.fcpack dist/PixhawkLogAnaliz …` belirlenimci zip), `win-setup` (`PixhawkLogAnaliz_Setup_X.Y.Z.exe`),
  `win-exe` (taşınabilir `PixhawkLogAnaliz.exe`). Asset adları SABİT: v1.0.1–1.0.7 güncelleyicileri GitHub API
  `releases/latest`'te adında `setup` geçen `.exe`'yi bulup `/VERYSILENT` kurar; v1.0.0 listedeki ilk `.exe`'yi (taşınabilir) alır
  (köprü, `tests/test_kopru.py` + `tests/legacy/updater_v107.py`). Eski biçim `delta-index.json` YAYINLANMAZ (eski yama yolu kaldırıcıyı bozardı).
- Kurulum Inno Setup, kullanıcı başına (`PrivilegesRequired=lowest`, `%LOCALAPPDATA%\Programs\Pixhawk Log Analiz`), tr/en/ar.
  Kaldırıcı `{app}-uninstall` içinde (klasör takası onu silmesin, kurulu klasörün zip'i CI'dakiyle bayt bayt aynı olsun).
  `AppId` ve klasör adı DEĞİŞMEZ; kullanıcı verisi `%APPDATA%\PixhawkLogAnaliz` (değişmez). Program kurulum klasörüne yazmaz.
- CI (`.github/workflows/release.yml`): `test` (windows: selftest + test_tuning + pytest offscreen) → `build` (PyInstaller, Inno, duman
  testi: kur/yükselt/kaldır + win-app zip yeniden üretim denetimi) → `release` (yalnız main). Yayın: main'e push ya da
  `gh api -X POST repos/departures-mil/pixhawk-log-analiz/actions/workflows/release.yml/dispatches -f ref=main`.
- AI: çevrimdışı kural motoru + kullanıcının kendi Gemini/Claude anahtarı + anahtarsız Pollinations. Sahibin anahtarı gömülmez.

## Test
- `python -m pytest -q tests` (offscreen), `python tools_ci/selftest.py`, `python tools_ci/test_tuning.py`.
- Ekran görüntüsü: pencereyi offscreen kurup `w.grab().save(...)` (bkz. `tests/conftest.py` `win` fikstürü).
