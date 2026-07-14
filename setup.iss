; Inno Setup Script
; Compile this script using the Inno Setup Compiler (ISCC or GUI) to build the setup installer.

[Setup]
AppName=File Monitor Alert
AppVersion=1.0.0
DefaultDirName={userpf}\FileMonitorAlert
DefaultGroupName=File Monitor Alert
OutputDir=.
OutputBaseFilename=FileMonitor_Setup
Compression=lzma
SolidCompression=yes
LicenseFile=LICENSE.txt
PrivilegesRequired=lowest
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\FileMonitor.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "files\app_icon.png"; DestDir: "{app}\files"; Flags: ignoreversion

[Icons]
Name: "{group}\File Monitor Alert"; Filename: "{app}\FileMonitor.exe"
Name: "{group}\{cm:UninstallProgram,File Monitor Alert}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\File Monitor Alert"; Filename: "{app}\FileMonitor.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FileMonitor.exe"; Description: "{cm:LaunchProgram,File Monitor Alert}"; Flags: nowait postinstall skipifsilent
