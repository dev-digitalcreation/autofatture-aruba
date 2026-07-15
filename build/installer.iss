; Inno Setup - installer per Reversa
; Compilare con Inno Setup (https://jrsoftware.org/isdl.php) DOPO aver creato l'exe con Flet.
; Aggiornare MyAppVersion ad ogni release (deve combaciare con version.py).

#define MyAppName "Reversa"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Digital Creation"
#define MyAppExeName "Reversa.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Reversa
DefaultGroupName=Reversa
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename=Reversa_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\assets\reversa.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; Non richiede admin se installato nella cartella utente; per {autopf} serve admin:
PrivilegesRequired=admin

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "Crea un'icona sul desktop"; GroupDescription: "Icone aggiuntive:"

[Files]
; --- Variante ONEFILE (flet pack -> dist\Reversa.exe) ---
Source: "..\dist\Reversa.exe"; DestDir: "{app}"; Flags: ignoreversion
; --- Variante ONEDIR (decommenta e usa questa se l'exe e' in una cartella) ---
; Source: "..\dist\Reversa\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Reversa"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Disinstalla Reversa"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Reversa"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Avvia Reversa"; Flags: nowait postinstall skipifsilent
