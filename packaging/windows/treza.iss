; Inno Setup script — packages the PyInstaller onedir bundle into a single
; treza-setup.exe installer (Start-Menu shortcut, optional desktop icon,
; uninstaller). The LGPL libraries remain as separate files under {app},
; keeping them user-replaceable.
;
; Build (after `pyinstaller packaging/treza.spec`):
;   iscc /DMyAppVersion=0.1.0 packaging\windows\treza.iss

#define MyAppName "Treza"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif
#define MyAppExeName "treza.exe"
#define MyAppPublisher "Treza contributors"
#define MyAppURL "https://github.com/pltlg/treza"

[Setup]
; A stable, app-unique GUID (generated for Treza).
AppId={{9C2B6F8E-3A7D-4E5C-9B1F-7E0A2D4C6F31}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\Treza
DefaultGroupName=Treza
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\..\installer
OutputBaseFilename=treza-setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; The whole onedir bundle produced by PyInstaller.
Source: "..\..\dist\treza\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Treza"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall Treza"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Treza"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Treza"; Flags: nowait postinstall skipifsilent
