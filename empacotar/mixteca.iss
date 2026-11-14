; Instalador do Mixteca (Inno Setup 6). Gerado pelo workflow "Gerar programa para Windows".
#define Versao "0.4.0"

[Setup]
AppId={{8E0B6C0E-6C55-4A6B-9D2B-6D1B0C7A4F11}
AppName=Mixteca
AppVersion={#Versao}
AppPublisher=Lucas G. Rei
AppPublisherURL=https://github.com/Necsoz/mixteca
DefaultDirName={autopf}\Mixteca
DefaultGroupName=Mixteca
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Mixteca-Setup
SetupIconFile=mixteca.ico
UninstallDisplayIcon={app}\Mixteca.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Mixteca\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Mixteca"; Filename: "{app}\Mixteca.exe"
Name: "{autodesktop}\Mixteca"; Filename: "{app}\Mixteca.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Mixteca.exe"; Description: "{cm:LaunchProgram,Mixteca}"; Flags: nowait postinstall skipifsilent
