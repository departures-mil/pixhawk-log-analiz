; Pixhawk Log Analiz — Windows kurulum paketi (Inno Setup 6)
; Kullanıcı başına kurulum (yönetici izni gerekmez) → program içinden sessiz, tek tık güncelleme.
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
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=PixhawkLogAnaliz-Setup-{#AppVersion}
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

[Languages]
Name: "tr"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"
#ifexist "compiler:Languages\Arabic.isl"
Name: "ar"; MessagesFile: "compiler:Languages\Arabic.isl"
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; Eski sürümden kalan kütüphaneler yenileriyle karışmasın (kullanıcı verisi %APPDATA%'da, silinmez)
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\PixhawkLogAnaliz\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
