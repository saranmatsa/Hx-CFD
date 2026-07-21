; HX CFD Bootstrapper Installer
; Inno Setup Script
; Version: 1.0.0

#define MyAppName "HX CFD"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "HX CFD"
#define MyAppURL "https://hxcfd.com"
#define MyAppExeName "HX CFD.exe"
#define MyAppId "{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"

; Application constants
#define DEPENDENCIES_DIR "dependencies"
#define FRONTEND_DIR "frontend"
#define PAYLOAD_DIR "..\payload"

; Colors
#define COLOR_PRIMARY "1E3A5F"
#define COLOR_ACCENT "4A90D9"
#define COLOR_SUCCESS "2E7D32"
#define COLOR_WARNING "F57C00"
#define COLOR_ERROR "C62828"
#define COLOR_BG "F5F7FA"

[Setup]
; Basic installer info
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}\support
AppUpdatesURL={#MyAppURL}\updates
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
OutputDir=..\output
OutputBaseFilename=HXCFD-Setup-{#MyAppVersion}
SetupIconFile=..\..\cfd-platform\icons\app.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Windows Apps & Features integration
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer
VersionInfoCopyright=Copyright (C) 2024 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
UninstallDisplayVersion={#MyAppVersion}
Manufacturer={#MyAppPublisher}
InfoBeforeFile=..\..\NOTICE

; Visual settings
WizardImageFile=..\..\cfd-platform\installer\assets\wizard-image.bmp
WizardSmallImageFile=..\..\cfd-platform\installer\assets\wizard-small.bmp
SetupLogging=yes

; Resume support
AllowSuspendInstall=yes
AllowNoIcons=yes

; Sizing
MinVersion=10.0.17763
WizardSizePercent=100

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main application files
Source: "..\..\cfd-platform\target\release\cfd-platform-tauri.exe"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: ignoreversion
; The desktop manages a self-contained local Python runtime.  Shipping this
; resource tree prevents the installed application from depending on a
; developer machine's Python installation or an obsolete frozen sidecar.
Source: "..\..\cfd-platform\bin\backend-runtime\*"; DestDir: "{app}\bin\backend-runtime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\cfd-platform\icons\*"; DestDir: "{app}\icons"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; Dependency bundles (placeholders - actual files come from payload directory)
Source: "{#PAYLOAD_DIR}\openfoam-v10-win-x64.zip"; DestDir: "{tmp}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PAYLOAD_DIR}\gmsh-4.12.0-win-x64.zip"; DestDir: "{tmp}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PAYLOAD_DIR}\freecad-1.0.0-win-x64.zip"; DestDir: "{tmp}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PAYLOAD_DIR}\meshio-5.3.5-py3-win-x64.zip"; DestDir: "{tmp}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PAYLOAD_DIR}\openmdao-3.37.0-py3-win-x64.zip"; DestDir: "{tmp}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PAYLOAD_DIR}\nevergrad-0.7.0-py3-win-x64.zip"; DestDir: "{tmp}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PAYLOAD_DIR}\paraview-5.12.0-win-x64.zip"; DestDir: "{tmp}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PAYLOAD_DIR}\vtk-9.3.0-py3-win-x64.zip"; DestDir: "{tmp}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PAYLOAD_DIR}\pyvista-0.43.0-py3-win-x64.zip"; DestDir: "{tmp}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PAYLOAD_DIR}\physicsnemo-1.0.0-py3-win-x64.zip"; DestDir: "{tmp}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PAYLOAD_DIR}\physicsnemo-cfd-1.0.0-py3-win-x64.zip"; DestDir: "{tmp}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PAYLOAD_DIR}\three.js-0.165.0.zip"; DestDir: "{tmp}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PAYLOAD_DIR}\react-three-fiber-8.16.0.zip"; DestDir: "{tmp}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#PAYLOAD_DIR}\drei-9.108.0.zip"; DestDir: "{tmp}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; Application root
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

; Environment variables
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "HXCFD_HOME"; ValueData: "{app}"; Flags: preservestringtype

[Run]
; Launch app after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Cleanup on uninstall
; `/T` terminates the private backend child together with the desktop shell;
; never target `python.exe` globally because engineers may have unrelated
; local Python work running.
Filename: "taskkill"; Parameters: "/F /T /IM ""{#MyAppExeName}"""; Flags: runhidden; RunOnceId: "StopApp"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\dependencies"
Type: filesandordirs; Name: "{app}\{#FRONTEND_DIR}"
Type: dirifempty; Name: "{app}"

[Code]
// ============================================================================
// HX CFD Bootstrapper Installer - Pascal Script
// ============================================================================

// Import required units
#include "dependencies.iss"
#include "verify.iss"
#include "ui.iss"

// Global variables
var
  DependencyPage: TOutputMsgMemoWizardPage;
  ProgressPage: TOutputProgressWizardPage;
  DependencyList: TStringList;
  InstallLog: TStringList;
  TotalDependencies: Integer;
  InstalledDependencies: Integer;
  FailedDependencies: TStringList;
  IsRepairMode: Boolean;
  IsResumeMode: Boolean;

// ============================================================================
// Initialization
// ============================================================================

procedure InitializeWizard;
begin
  // Initialize logging
  InstallLog := TStringList.Create;
  DependencyList := TStringList.Create;
  FailedDependencies := TStringList.Create;
  
  // Set up custom wizard pages
  CreateDependencyPage;
  CreateProgressPage;
  
  // Check for repair/resume mode
  IsRepairMode := CheckRepairMode;
  IsResumeMode := CheckResumeMode;
  
  // Load dependency list
  LoadDependencyList;
  
  // Update wizard appearance
  WizardForm.WelcomeLabel1.Caption := 'Welcome to HX CFD Setup';
  WizardForm.WelcomeLabel2.Caption := 
    'This wizard will guide you through the installation of HX CFD and its dependencies.' + #13#10 + #13#10 +
    'Total dependencies: ' + IntToStr(TotalDependencies) + #13#10 +
    'Installation directory: ' + ExpandConstant('{app}');
    
  if IsRepairMode then
  begin
    WizardForm.WelcomeLabel2.Caption := WizardForm.WelcomeLabel2.Caption + #13#10 + #13#10 +
      'REPAIR MODE: Some components are missing or corrupted. The installer will repair them.';
  end;
  
  if IsResumeMode then
  begin
    WizardForm.WelcomeLabel2.Caption := WizardForm.WelcomeLabel2.Caption + #13#10 + #13#10 +
      'RESUME MODE: A previous installation was interrupted. Resuming from where it left off.';
  end;
end;

// ============================================================================
// Pre-installation checks
// ============================================================================

function InitializeSetup(): Boolean;
var
  ErrorCode: Integer;
begin
  Result := True;
  
  // Check Windows version
  if not CheckWindowsVersion then
  begin
    MsgBox('HX CFD requires Windows 10 version 1809 or later.', mbError, MB_OK);
    Result := False;
    Exit;
  end;
  
  // Check for admin privileges
  if not IsAdminInstallMode then
  begin
    if MsgBox('HX CFD requires administrator privileges. Click Yes to restart with admin rights, or No to cancel.', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      ShellExec('runas', ExpandConstant('{cmd}'), '/c "' + ParamStr(0) + '"', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode);
    end;
    Result := False;
    Exit;
  end;
  
  // Check disk space
  if not CheckDiskSpace then
  begin
    MsgBox('Insufficient disk space. HX CFD requires at least 5 GB of free space.', mbError, MB_OK);
    Result := False;
    Exit;
  end;
  
  // Check for conflicting applications
  if CheckConflictingApps then
  begin
    if MsgBox('Conflicting applications detected. It is recommended to close them before continuing. Continue anyway?', 
              mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
      Exit;
    end;
  end;
  
  // Pre-flight check for dependencies
  if not RunPreflightCheck then
  begin
    if MsgBox('Pre-flight check failed. Some dependencies may not install correctly. Continue anyway?', 
              mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
      Exit;
    end;
  end;
end;

// ============================================================================
// Dependency installation
// ============================================================================

procedure CurStepChanged(CurStep: TSetupStep);
var
  I: Integer;
  DepName: String;
  DepInfo: TDependencyInfo;
  Success: Boolean;
  ErrorMsg: String;
begin
  if CurStep = ssInstall then
  begin
    // Show progress page
    ProgressPage.Show;
    
    // Initialize counters
    InstalledDependencies := 0;
    TotalDependencies := DependencyList.Count;
    
    // Install each dependency
    for I := 0 to DependencyList.Count - 1 do
    begin
      DepName := DependencyList[I];
      DepInfo := GetDependencyInfo(DepName);
      
      // Update progress
      ProgressPage.SetProgress(I, TotalDependencies);
      ProgressPage.StatusText := 'Installing ' + DepInfo.Name + '...';
      
      // Check if already installed (for repair/resume mode)
      if (IsRepairMode or IsResumeMode) and IsDependencyInstalled(DepName) then
      begin
        if IsDependencyHealthy(DepName) then
        begin
          Log(DepName + ' is already installed and healthy, skipping.');
          Inc(InstalledDependencies);
          Continue;
        end
        else
        begin
          Log(DepName + ' is corrupted, reinstalling...');
          // Remove corrupted installation
          RemoveDependency(DepName);
        end;
      end;
      
      // Install the dependency
      Success := InstallDependency(DepName, DepInfo, ErrorMsg);
      
      if Success then
      begin
        Inc(InstalledDependencies);
        Log(DepName + ' installed successfully.');
      end
      else
      begin
        FailedDependencies.Add(DepName + ': ' + ErrorMsg);
        Log('Failed to install ' + DepName + ': ' + ErrorMsg);
        
        // Ask user whether to continue
        if MsgBox('Failed to install ' + DepInfo.Name + ': ' + ErrorMsg + #13#10 + #13#10 +
                  'Continue with remaining dependencies?', 
                  mbConfirmation, MB_YESNO) = IDNO then
        begin
          Break;
        end;
      end;
    end;
    
    // Finalize progress
    ProgressPage.SetProgress(TotalDependencies, TotalDependencies);
    ProgressPage.Hide;
    
    // Show results
    ShowInstallResults;
  end;
end;

// ============================================================================
// Post-installation
// ============================================================================

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
  begin
    // Update finished page with results
    if FailedDependencies.Count > 0 then
    begin
      WizardForm.FinishedLabel.Caption := 
        'Installation completed with some errors.' + #13#10 +
        'Failed dependencies: ' + IntToStr(FailedDependencies.Count) + ' of ' + IntToStr(TotalDependencies) + #13#10 +
        #13#10 +
        'You can run the installer again to repair failed components.';
    end
    else
    begin
      WizardForm.FinishedLabel.Caption := 
        'Installation completed successfully!' + #13#10 +
        'Installed dependencies: ' + IntToStr(InstalledDependencies) + ' of ' + IntToStr(TotalDependencies);
    end;
  end;
end;

// ============================================================================
// Cleanup
// ============================================================================

procedure DeinitializeSetup();
begin
  // Clean up temporary files
  CleanTempFiles;
  
  // Save install log
  SaveInstallLog;
  
  // Clean up string lists
  if Assigned(InstallLog) then InstallLog.Free;
  if Assigned(DependencyList) then DependencyList.Free;
  if Assigned(FailedDependencies) then FailedDependencies.Free;
end;

// ============================================================================
// Helper functions
// ============================================================================

function CheckWindowsVersion(): Boolean;
begin
  Result := (GetWindowsVersion >= $00060003); // Windows 10 1809
end;

function CheckDiskSpace(): Boolean;
var
  RequiredSpace: Int64;
  FreeSpace: Int64;
begin
  RequiredSpace := 5 * 1024 * 1024 * 1024; // 5 GB
  FreeSpace := DiskSpaceAvailable(ExpandConstant('{app}'));
  Result := (FreeSpace >= RequiredSpace);
end;

function CheckConflictingApps(): Boolean;
var
  Processes: TStringList;
  I: Integer;
begin
  Result := False;
  Processes := TStringList.Create;
  try
    Processes.Add('openfoam');
    Processes.Add('gmsh');
    Processes.Add('freecad');
    Processes.Add('paraview');
    
    for I := 0 to Processes.Count - 1 do
    begin
      if FindWindowByWindowName(Processes[I]) <> 0 then
      begin
        Result := True;
        Break;
      end;
    end;
  finally
    Processes.Free;
  end;
end;

function CheckRepairMode(): Boolean;
var
  AppPath: String;
begin
  AppPath := ExpandConstant('{app}');
  Result := FileExists(AppPath + '\{#MyAppExeName}') and 
            (FileExists(AppPath + '\.install.incomplete') or 
             FileExists(AppPath + '\.repair'));
end;

function CheckResumeMode(): Boolean;
var
  AppPath: String;
begin
  AppPath := ExpandConstant('{app}');
  Result := FileExists(AppPath + '\.install.incomplete');
end;

procedure LoadDependencyList();
begin
  // Load from dependencies.json or use default list
  DependencyList.Clear;
  DependencyList.Add('openfoam');
  DependencyList.Add('gmsh');
  DependencyList.Add('freecad');
  DependencyList.Add('meshio');
  DependencyList.Add('openmdao');
  DependencyList.Add('nevergrad');
  DependencyList.Add('paraview');
  DependencyList.Add('vtk');
  DependencyList.Add('pyvista');
  DependencyList.Add('physicsnemo');
  DependencyList.Add('physicsnemo-cfd');
  DependencyList.Add('threejs');
  DependencyList.Add('react-three-fiber');
  DependencyList.Add('drei');
  TotalDependencies := DependencyList.Count;
end;

procedure ShowInstallResults();
var
  Msg: String;
begin
  if FailedDependencies.Count = 0 then
  begin
    Msg := 'All dependencies installed successfully!' + #13#10 + #13#10 +
           'Installed: ' + IntToStr(InstalledDependencies) + ' of ' + IntToStr(TotalDependencies);
    MsgBox(Msg, mbInformation, MB_OK);
  end
  else if FailedDependencies.Count < TotalDependencies then
  begin
    Msg := 'Installation completed with some errors.' + #13#10 + #13#10 +
           'Installed: ' + IntToStr(InstalledDependencies) + ' of ' + IntToStr(TotalDependencies) + #13#10 +
           'Failed: ' + IntToStr(FailedDependencies.Count) + #13#10 + #13#10 +
           'You can run the installer again to repair failed components.';
    MsgBox(Msg, mbConfirmation, MB_OK);
  end
  else
  begin
    Msg := 'Installation failed for all dependencies.' + #13#10 + #13#10 +
           'Please check your internet connection and try again.';
    MsgBox(Msg, mbError, MB_OK);
  end;
end;

procedure CleanTempFiles();
var
  TempPath: String;
begin
  TempPath := ExpandConstant('{tmp}');
  // Clean up downloaded dependency files
  DelTree(TempPath + '\*.zip', True, True, True);
end;

procedure SaveInstallLog();
var
  LogPath: String;
  F: TextFile;
begin
  LogPath := ExpandConstant('{app}\logs\install.log');
  ForceDirectories(ExtractFilePath(LogPath));
  
  try
    AssignFile(F, LogPath);
    Rewrite(F);
    WriteLn(F, 'HX CFD Installation Log');
    WriteLn(F, '========================');
    WriteLn(F, 'Date: ' + DateTimeToStr(Now));
    WriteLn(F, 'Version: ' + '{#MyAppVersion}');
    WriteLn(F, '');
    WriteLn(F, InstallLog.Text);
    CloseFile(F);
  except
    Log('Failed to save install log');
  end;
end;

procedure Log(const Msg: String);
begin
  InstallLog.Add('[' + TimeToStr(Now) + '] ' + Msg);
end;
