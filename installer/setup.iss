; Pixhawk Log Analiz — Windows kurulum paketi (Inno Setup 6)
; Kullanıcı başına kurulum (yönetici izni gerekmez, %LOCALAPPDATA%\Programs) → program kurulum klasörüne yazabilir:
; ortak çekirdek güncelleyicisi (fccore) win-app kanalında klasörü yamayla/zip'le değiştirir, gerekirse bu kurulumu sessiz çalıştırır.
; Kaldırıcı (unins000.*) kurulum klasörünün DIŞINDA tutulur: klasör takası kaldırıcıyı silmesin ve
; istemcinin yeniden ürettiği win-app zip'i CI'dakiyle bayt bayt aynı olsun (yama tabanı).
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "Pixhawk Log Analiz"
#define AppExe "PixhawkLogAnaliz.exe"

[Setup]
AppId={{8C3F7B2E-5A1D-4E7B-9C2F-6D1A0B4E3F21}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher=departures-mil
AppPublisherURL=https://github.com/departures-mil/pixhawk-log-analiz
AppSupportURL=https://github.com/departures-mil/pixhawk-log-analiz/issues
AppUpdatesURL=https://github.com/departures-mil/pixhawk-log-analiz/releases
DefaultDirName={localappdata}\Programs\Pixhawk Log Analiz
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
DisableReadyPage=yes
PrivilegesRequired=lowest
UninstallFilesDir={app}-uninstall
OutputDir=..\dist
OutputBaseFilename=PixhawkLogAnaliz_Setup_{#AppVersion}
SetupIconFile=..\app\data\app.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion={#AppVersion}.0
ShowLanguageDialog=auto
UsePreviousAppDir=yes
UsePreviousTasks=yes
ChangesAssociations=yes

[Languages]
Name: "tr"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"
#ifexist "compiler:Languages\Arabic.isl"
Name: "ar"; MessagesFile: "compiler:Languages\Arabic.isl"
#endif

[CustomMessages]
tr.AssocTask=.BIN ve .tlog log dosyalarını çift tıklayınca bu programla aç
en.AssocTask=Open .BIN and .tlog log files with this program on double-click
#ifexist "compiler:Languages\Arabic.isl"
ar.AssocTask=فتح ملفات السجل .BIN و.tlog بهذا البرنامج عند النقر المزدوج
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "assoc"; Description: "{cm:AssocTask}"

[Registry]
Root: HKA; Subkey: "Software\Classes\PixhawkLogAnaliz.Log"; ValueType: string; ValueName: ""; ValueData: "Pixhawk / ArduPilot Log"; Flags: uninsdeletekey; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\PixhawkLogAnaliz.Log\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"",0"; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\PixhawkLogAnaliz.Log\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\.bin"; ValueType: string; ValueName: ""; ValueData: "PixhawkLogAnaliz.Log"; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\.bin\OpenWithProgids"; ValueType: none; ValueName: "PixhawkLogAnaliz.Log"; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\.tlog"; ValueType: string; ValueName: ""; ValueData: "PixhawkLogAnaliz.Log"; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\.tlog\OpenWithProgids"; ValueType: none; ValueName: "PixhawkLogAnaliz.Log"; Flags: uninsdeletevalue; Tasks: assoc

[InstallDelete]
; Eski sürümden kalan kütüphaneler yenileriyle karışmasın (kullanıcı verisi %APPDATA%'da, silinmez)
Type: filesandordirs; Name: "{app}\_internal"
; v1.0.x kaldırıcısı kurulum klasöründeydi; yenisi {app}-uninstall içinde
Type: files; Name: "{app}\unins*.*"
; yarım kalmış güncelleme takası artıkları
Type: filesandordirs; Name: "{app}.new"
Type: filesandordirs; Name: "{app}.bak"

[UninstallDelete]
; program içi güncellemeyle gelen dosyalar kaldırıcının kaydında yok: klasörü bütünüyle kaldır (kullanıcı verisi %APPDATA%'da)
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{app}.new"
Type: filesandordirs; Name: "{app}.bak"

[Files]
Source: "..\dist\PixhawkLogAnaliz\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
