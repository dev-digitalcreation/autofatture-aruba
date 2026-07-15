; Inno Setup - installer per Autofatture Aruba
; Compilare con Inno Setup (https://jrsoftware.org/isdl.php) DOPO aver creato l'exe con Flet.
; Aggiornare MyAppVersion ad ogni release (deve combaciare con version.py).

#define MyAppName "Autofatture Aruba"
#define MyAppVersion "1.0.0-beta.1"
#define MyAppPublisher "Digital Creation"
#define MyAppExeName "AutofattureAruba.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\AutofattureAruba
DefaultGroupName=Autofatture Aruba
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename=AutofattureAruba_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
; Non richiede admin se installato nella cartella utente; per {autopf} serve admin:
PrivilegesRequired=admin

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "Crea un'icona sul desktop"; GroupDescription: "Icone aggiuntive:"

[Files]
; --- Variante ONEFILE (flet pack -> dist\AutofattureAruba.exe) ---
Source: "..\dist\AutofattureAruba.exe"; DestDir: "{app}"; Flags: ignoreversion
; --- Variante ONEDIR (decommenta e usa questa se l'exe e' in una cartella) ---
; Source: "..\dist\AutofattureAruba\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Autofatture Aruba"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Disinstalla Autofatture Aruba"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Autofatture Aruba"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Avvia Autofatture Aruba"; Flags: nowait postinstall skipifsilent
