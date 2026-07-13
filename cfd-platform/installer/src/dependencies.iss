; ============================================================================
; HX CFD Dependencies Installation Module
; Handles installation of all 14 dependency bundles
; ============================================================================

// Dependency info structure
type
  TDependencyInfo = record
    ID: String;
    Name: String;
    Version: String;
    Filename: String;
    SHA256: String;
    InstallPath: String;
    Description: String;
    EnvVars: TArrayOfString;
    HealthCheckType: String;
    HealthCheckCommand: String;
    HealthCheckArgs: String;
    HealthCheckExpected: String;
  end;

// Global dependency cache
var
  DependencyCache: TStringList;

// ============================================================================
// Dependency Info Retrieval
// ============================================================================

function GetDependencyInfo(const DepID: String): TDependencyInfo;
begin
  // Initialize with defaults based on dependency ID
  Result.ID := DepID;
  
  if DepID = 'openfoam' then
  begin
    Result.Name := 'OpenFOAM';
    Result.Version := '10.0.0';
    Result.Filename := 'openfoam-v10-win-x64.zip';
    Result.SHA256 := '0000000000000000000000000000000000000000000000000000000000000000';
    Result.InstallPath := 'openfoam';
    Result.Description := 'OpenFOAM v10 Windows runtime with MPI support';
    Result.HealthCheckType := 'command';
    Result.HealthCheckCommand := 'openfoam.exe';
    Result.HealthCheckArgs := '--version';
    Result.HealthCheckExpected := 'OpenFOAM-10';
    SetArrayLength(Result.EnvVars, 5);
    Result.EnvVars[0] := 'FOAM_INST_DIR={INSTALL_DIR}\openfoam';
    Result.EnvVars[1] := 'WM_PROJECT_DIR={INSTALL_DIR}\openfoam';
    Result.EnvVars[2] := 'WM_PROJECT_VERSION=v10';
    Result.EnvVars[3] := 'WM_MPLIB=MSMPI';
    Result.EnvVars[4] := 'PATH={INSTALL_DIR}\openfoam\bin;{INSTALL_DIR}\openfoam\wmake;{PATH}';
  end
  else if DepID = 'gmsh' then
  begin
    Result.Name := 'Gmsh';
    Result.Version := '4.12.0';
    Result.Filename := 'gmsh-4.12.0-win-x64.zip';
    Result.SHA256 := '0000000000000000000000000000000000000000000000000000000000000000';
    Result.InstallPath := 'gmsh';
    Result.Description := 'Gmsh 4.12 mesh generator runtime';
    Result.HealthCheckType := 'command';
    Result.HealthCheckCommand := 'gmsh.exe';
    Result.HealthCheckArgs := '--version';
    Result.HealthCheckExpected := '4.12';
    SetArrayLength(Result.EnvVars, 2);
    Result.EnvVars[0] := 'GMSH_PATH={INSTALL_DIR}\gmsh';
    Result.EnvVars[1] := 'PATH={INSTALL_DIR}\gmsh;{PATH}';
  end
  else if DepID = 'freecad' then
  begin
    Result.Name := 'FreeCAD';
    Result.Version := '1.0.0';
    Result.Filename := 'freecad-1.0.0-win-x64.zip';
    Result.SHA256 := '0000000000000000000000000000000000000000000000000000000000000000';
    Result.InstallPath := 'freecad';
    Result.Description := 'FreeCAD 1.0 3D CAD modeler runtime';
    Result.HealthCheckType := 'command';
    Result.HealthCheckCommand := 'FreeCAD.exe';
    Result.HealthCheckArgs := '--version';
    Result.HealthCheckExpected := '1.0';
    SetArrayLength(Result.EnvVars, 2);
    Result.EnvVars[0] := 'FREECAD_PATH={INSTALL_DIR}\freecad';
    Result.EnvVars[1] := 'PATH={INSTALL_DIR}\freecad;{PATH}';
  end
  else if DepID = 'paraview' then
  begin
    Result.Name := 'ParaView';
    Result.Version := '5.12.0';
    Result.Filename := 'paraview-5.12.0-win-x64.zip';
    Result.SHA256 := '0000000000000000000000000000000000000000000000000000000000000000';
    Result.InstallPath := 'paraview';
    Result.Description := 'ParaView 5.12 post-processing runtime';
    Result.HealthCheckType := 'command';
    Result.HealthCheckCommand := 'paraview.exe';
    Result.HealthCheckArgs := '--version';
    Result.HealthCheckExpected := '5.12';
    SetArrayLength(Result.EnvVars, 2);
    Result.EnvVars[0] := 'PARAVIEW_PATH={INSTALL_DIR}\paraview';
    Result.EnvVars[1] := 'PATH={INSTALL_DIR}\paraview\bin;{PATH}';
  end
  else if DepID = 'meshio' then
  begin
    Result.Name := 'meshio';
    Result.Version := '5.3.5';
    Result.Filename := 'meshio-5.3.5-py3-win-x64.zip';
    Result.SHA256 := '0000000000000000000000000000000000000000000000000000000000000000';
    Result.InstallPath := 'python\site-packages';
    Result.Description := 'meshio Python package for mesh I/O';
    Result.HealthCheckType := 'python_import';
    Result.HealthCheckExpected := 'meshio';
    SetArrayLength(Result.EnvVars, 0);
  end
  else if DepID = 'openmdao' then
  begin
    Result.Name := 'OpenMDAO';
    Result.Version := '3.37.0';
    Result.Filename := 'openmdao-3.37.0-py3-win-x64.zip';
    Result.SHA256 := '0000000000000000000000000000000000000000000000000000000000000000';
    Result.InstallPath := 'python\site-packages';
    Result.Description := 'OpenMDAO optimization framework Python package';
    Result.HealthCheckType := 'python_import';
    Result.HealthCheckExpected := 'openmdao';
    SetArrayLength(Result.EnvVars, 0);
  end
  else if DepID = 'nevergrad' then
  begin
    Result.Name := 'Nevergrad';
    Result.Version := '0.7.0';
    Result.Filename := 'nevergrad-0.7.0-py3-win-x64.zip';
    Result.SHA256 := '0000000000000000000000000000000000000000000000000000000000000000';
    Result.InstallPath := 'python\site-packages';
    Result.Description := 'Nevergrad optimization library Python package';
    Result.HealthCheckType := 'python_import';
    Result.HealthCheckExpected := 'nevergrad';
    SetArrayLength(Result.EnvVars, 0);
  end
  else if DepID = 'pyvista' then
  begin
    Result.Name := 'PyVista';
    Result.Version := '0.43.0';
    Result.Filename := 'pyvista-0.43.0-py3-win-x64.zip';
    Result.SHA256 := '0000000000000000000000000000000000000000000000000000000000000000';
    Result.InstallPath := 'python\site-packages';
    Result.Description := 'PyVista 3D visualization Python package';
    Result.HealthCheckType := 'python_import';
    Result.HealthCheckExpected := 'pyvista';
    SetArrayLength(Result.EnvVars, 0);
  end
  else if DepID = 'vtk' then
  begin
    Result.Name := 'VTK';
    Result.Version := '9.3.0';
    Result.Filename := 'vtk-9.3.0-py3-win-x64.zip';
    Result.SHA256 := '0000000000000000000000000000000000000000000000000000000000000000';
    Result.InstallPath := 'python\site-packages';
    Result.Description := 'VTK visualization toolkit Python package';
    Result.HealthCheckType := 'python_import';
    Result.HealthCheckExpected := 'vtk';
    SetArrayLength(Result.EnvVars, 0);
  end
  else if DepID = 'physicsnemo' then
  begin
    Result.Name := 'PhysicsNeMo';
    Result.Version := '1.0.0';
    Result.Filename := 'physicsnemo-1.0.0-py3-win-x64.zip';
    Result.SHA256 := '0000000000000000000000000000000000000000000000000000000000000000';
    Result.InstallPath := 'python\site-packages';
    Result.Description := 'PhysicsNeMo framework';
    Result.HealthCheckType := 'python_import';
    Result.HealthCheckExpected := 'physicsnemo';
    SetArrayLength(Result.EnvVars, 0);
  end
  else if DepID = 'physicsnemo-cfd' then
  begin
    Result.Name := 'PhysicsNeMo-CFD';
    Result.Version := '1.0.0';
    Result.Filename := 'physicsnemo-cfd-1.0.0-py3-win-x64.zip';
    Result.SHA256 := '0000000000000000000000000000000000000000000000000000000000000000';
    Result.InstallPath := 'python\site-packages';
    Result.Description := 'PhysicsNeMo-CFD extension';
    Result.HealthCheckType := 'python_import';
    Result.HealthCheckExpected := 'physicsnemo_cfd';
    SetArrayLength(Result.EnvVars, 0);
  end
  else if DepID = 'threejs' then
  begin
    Result.Name := 'three.js';
    Result.Version := '0.165.0';
    Result.Filename := 'three.js-0.165.0.zip';
    Result.SHA256 := '0000000000000000000000000000000000000000000000000000000000000000';
    Result.InstallPath := 'frontend\node_modules\three';
    Result.Description := 'three.js 3D library';
    Result.HealthCheckType := 'file_exists';
    Result.HealthCheckExpected := 'build\three.module.js';
    SetArrayLength(Result.EnvVars, 0);
  end
  else if DepID = 'react-three-fiber' then
  begin
    Result.Name := 'react-three-fiber';
    Result.Version := '8.16.0';
    Result.Filename := 'react-three-fiber-8.16.0.zip';
    Result.SHA256 := '0000000000000000000000000000000000000000000000000000000000000000';
    Result.InstallPath := 'frontend\node_modules\@react-three\fiber';
    Result.Description := 'react-three-fiber React renderer for three.js';
    Result.HealthCheckType := 'file_exists';
    Result.HealthCheckExpected := 'dist\index.esm.js';
    SetArrayLength(Result.EnvVars, 0);
  end
  else if DepID = 'drei' then
  begin
    Result.Name := 'drei';
    Result.Version := '9.108.0';
    Result.Filename := 'drei-9.108.0.zip';
    Result.SHA256 := '0000000000000000000000000000000000000000000000000000000000000000';
    Result.InstallPath := 'frontend\node_modules\@react-three\drei';
    Result.Description := 'drei helper components for react-three-fiber';
    Result.HealthCheckType := 'file_exists';
    Result.HealthCheckExpected := 'dist\index.js';
    SetArrayLength(Result.EnvVars, 0);
  end;
end;

// ============================================================================
// Main Installation Function
// ============================================================================

function InstallDependency(const DepID: String; const DepInfo: TDependencyInfo; var ErrorMsg: String): Boolean;
var
  ZipPath: String;
  ExtractPath: String;
  TempPath: String;
begin
  Result := False;
  ErrorMsg := '';
  
  try
    // Mark installation as in progress
    MarkInstallationInProgress(DepID);
    
    // Set up paths
    TempPath := ExpandConstant('{tmp}');
    ZipPath := TempPath + '\' + DepInfo.Filename;
    ExtractPath := ExpandConstant('{app}');
    
    // Check if zip file exists
    if not FileExists(ZipPath) then
    begin
      // Try to download if not present
      if not DownloadDependency(DepID, ZipPath) then
      begin
        ErrorMsg := 'Dependency archive not found: ' + DepInfo.Filename;
        Exit;
      end;
    end;
    
    // Verify SHA-256 checksum
    if not VerifySHA256(ZipPath, DepInfo.SHA256) then
    begin
      ErrorMsg := 'SHA-256 verification failed for ' + DepInfo.Filename;
      Exit;
    end;
    
    // Extract the archive
    if not ExtractZip(ZipPath, ExtractPath) then
    begin
      ErrorMsg := 'Failed to extract ' + DepInfo.Filename;
      Exit;
    end;
    
    // Set up environment variables
    SetupEnvironmentVariables(DepID, DepInfo);
    
    // Verify installation
    if not VerifyInstallation(DepID, DepInfo) then
    begin
      ErrorMsg := 'Health check failed for ' + DepInfo.Name;
      Exit;
    end;
    
    // Mark as complete
    MarkInstallationComplete(DepID);
    Result := True;
    
  except
    ErrorMsg := 'Exception during installation: ' + GetExceptionMessage;
    Result := False;
  end;
end;

// ============================================================================
// Download Function (Local Payload Model)
// ============================================================================

function DownloadDependency(const DepID: String; const DestPath: String): Boolean;
var
  LocalPath: String;
  DepInfo: TDependencyInfo;
begin
  Result := False;
  
  // Get dependency info
  DepInfo := GetDependencyInfo(DepID);
  
  // Use local payload directory instead of downloading
  LocalPath := ExpandConstant('{src}\..\payload\') + DepInfo.Filename;
  
  // Check if local file exists
  if FileExists(LocalPath) then
  begin
    // Copy from local payload to destination
    if FileCopy(LocalPath, DestPath, False) then
    begin
      Log('Copied ' + DepID + ' from local payload: ' + LocalPath);
      Result := True;
    end
    else
    begin
      Log('Failed to copy ' + DepID + ' from local payload: ' + LocalPath);
    end;
  end
  else
  begin
    Log('Local payload not found for ' + DepID + ': ' + LocalPath);
    // Try alternate location: installer/payload
    LocalPath := ExpandConstant('{src}\..\..\payload\') + DepInfo.Filename;
    if FileExists(LocalPath) then
    begin
      if FileCopy(LocalPath, DestPath, False) then
      begin
        Log('Copied ' + DepID + ' from local payload: ' + LocalPath);
        Result := True;
      end;
    end;
  end;
end;

// ============================================================================
// SHA-256 Verification
// ============================================================================

function VerifySHA256(const FilePath: String; const ExpectedHash: String): Boolean;
var
  Hash: String;
begin
  // Skip verification if hash is placeholder (all zeros)
  if ExpectedHash = StringOfChar('0', 64) then
  begin
    Log('Skipping SHA-256 verification for ' + ExtractFileName(FilePath) + ' (placeholder hash)');
    Result := True;
    Exit;
  end;
  
  // Calculate actual hash
  Hash := GetSHA256(FilePath);
  
  if Hash <> ExpectedHash then
  begin
    Log('SHA-256 mismatch for ' + ExtractFileName(FilePath));
    Log('Expected: ' + ExpectedHash);
    Log('Actual:   ' + Hash);
    Result := False;
    Exit;
  end;
  
  Result := True;
end;

function GetSHA256(const FilePath: String): String;
var
  HashResult: String;
begin
  // Use ISSigTool.exe for SHA-256 calculation
  if Exec(ExpandConstant('{pf32}\Inno Setup 6\ISSigTool.exe'), '-sha256 "' + FilePath + '"', 
          '', SW_HIDE, ewWaitUntilTerminated, HashResult) then
  begin
    // Parse output - ISSigTool outputs in format: "SHA256: <hash>"
    Result := Trim(HashResult);
    if Pos('SHA256:', Result) > 0 then
      Result := Trim(Copy(Result, Pos(':', Result) + 1, Length(Result)));
  end
  else
  begin
    // Fallback: use PowerShell
    Exec('powershell', '-Command "(Get-FileHash -Path ''' + FilePath + ''' -Algorithm SHA256).Hash"', 
         '', SW_HIDE, ewWaitUntilTerminated, HashResult);
    Result := Trim(HashResult);
  end;
end;

// ============================================================================
// ZIP Extraction
// ============================================================================

function ExtractZip(const ZipPath: String; const DestPath: String): Boolean;
var
  ResultCode: Integer;
begin
  // Use 7z if available, otherwise use PowerShell
  if FileExists(ExpandConstant('{pf32}\7-Zip\7z.exe')) then
  begin
    Result := Exec(ExpandConstant('{pf32}\7-Zip\7z.exe'), 
                   'x -y -o"' + DestPath + '" "' + ZipPath + '"',
                   '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end
  else
  begin
    // Use PowerShell for extraction
    Result := Exec('powershell', 
                   '-Command "Expand-Archive -Path ''' + ZipPath + ''' -DestinationPath ''' + DestPath + ''' -Force"',
                   '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Result := (ResultCode = 0);
  end;
end;

// ============================================================================
// Environment Variables
// ============================================================================

procedure SetupEnvironmentVariables(const DepID: String; const DepInfo: TDependencyInfo);
var
  EnvVar: String;
  EnvName: String;
  EnvValue: String;
  AppPath: String;
begin
  AppPath := ExpandConstant('{app}');
  
  // Set up PATH additions for executables
  if (DepID = 'openfoam') or (DepID = 'gmsh') or (DepID = 'freecad') or (DepID = 'paraview') then
  begin
    EnvVar := 'PATH';
    // PATH is handled via registry in [Registry] section
  end;
  
  // Set up specific environment variables
  if DepID = 'openfoam' then
  begin
    SetEnvironmentVariable('OPENFOAM_DIR', AppPath + '\dependencies\openfoam');
  end
  else if DepID = 'freecad' then
  begin
    SetEnvironmentVariable('FREECAD_HOME', AppPath + '\dependencies\freecad');
  end
  else if DepID = 'paraview' then
  begin
    SetEnvironmentVariable('PARAVIEW_HOME', AppPath + '\dependencies\paraview');
  end
  else if DepID = 'vtk' then
  begin
    SetEnvironmentVariable('VTK_HOME', AppPath + '\dependencies\vtk');
  end;
end;

procedure SetEnvironmentVariable(const Name: String; const Value: String);
var
  RegKey: String;
begin
  RegKey := 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment';
  if RegKeyExists(HKLM, RegKey) then
  begin
    RegWriteStringValue(HKLM, RegKey, Name, Value);
  end;
end;

// ============================================================================
// Installation Tracking
// ============================================================================

procedure MarkInstallationInProgress(const DepID: String);
var
  FilePath: String;
  F: TextFile;
begin
  FilePath := ExpandConstant('{app}\.install_in_progress');
  try
    AssignFile(F, FilePath);
    Append(F);
    WriteLn(F, DepID + ':in_progress:' + DateTimeToStr(Now));
    CloseFile(F);
  except
    // Ignore errors
  end;
end;

procedure MarkInstallationComplete(const DepID: String);
var
  FilePath: String;
  F: TextFile;
  Content: TStringList;
  I: Integer;
  Line: String;
  NewContent: TStringList;
begin
  FilePath := ExpandConstant('{app}\.install_in_progress');
  Content := TStringList.Create;
  NewContent := TStringList.Create;
  
  try
    if FileExists(FilePath) then
      Content.LoadFromFile(FilePath);
    
    for I := 0 to Content.Count - 1 do
    begin
      Line := Content[I];
      if Pos(DepID + ':', Line) = 1 then
        NewContent.Add(DepID + ':complete:' + DateTimeToStr(Now))
      else
        NewContent.Add(Line);
    end;
    
    NewContent.SaveToFile(FilePath);
  finally
    Content.Free;
    NewContent.Free;
  end;
end;

function IsDependencyInstalled(const DepID: String): Boolean;
var
  DepInfo: TDependencyInfo;
  CheckPath: String;
begin
  DepInfo := GetDependencyInfo(DepID);
  CheckPath := ExpandConstant('{app}') + '\' + DepInfo.InstallPath;
  
  // Check if directory exists
  Result := DirExists(CheckPath);
end;

function IsDependencyHealthy(const DepID: String): Boolean;
var
  DepInfo: TDependencyInfo;
begin
  DepInfo := GetDependencyInfo(DepID);
  Result := VerifyInstallation(DepID, DepInfo);
end;

// ============================================================================
// Health Check / Verification
// ============================================================================

function VerifyInstallation(const DepID: String; const DepInfo: TDependencyInfo): Boolean;
var
  Output: String;
  ResultCode: Integer;
  CheckPath: String;
begin
  Result := False;
  
  if DepInfo.HealthCheckType = 'command' then
  begin
    // Execute command and check output
    CheckPath := ExpandConstant('{app}') + '\' + DepInfo.InstallPath;
    if Exec(CheckPath + '\bin\' + DepInfo.HealthCheckCommand, 
            DepInfo.HealthCheckArgs, '', SW_HIDE, ewWaitUntilTerminated, ResultCode, Output) then
    begin
      Result := (Pos(DepInfo.HealthCheckExpected, Output) > 0);
    end;
  end
  else if DepInfo.HealthCheckType = 'python_import' then
  begin
    // Check Python import
    CheckPath := ExpandConstant('{app}');
    if Exec('python', '-c "import ' + DepInfo.HealthCheckExpected + '"', 
            '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      Result := (ResultCode = 0);
    end;
  end
  else if DepInfo.HealthCheckType = 'file_exists' then
  begin
    // Check if expected file exists
    CheckPath := ExpandConstant('{app}') + '\' + DepInfo.InstallPath + '\' + DepInfo.HealthCheckExpected;
    Result := FileExists(CheckPath);
  end;
end;

// ============================================================================
// Remove Dependency
// ============================================================================

procedure RemoveDependency(const DepID: String);
var
  DepInfo: TDependencyInfo;
  RemovePath: String;
begin
  DepInfo := GetDependencyInfo(DepID);
  RemovePath := ExpandConstant('{app}') + '\' + DepInfo.InstallPath;
  
  if DirExists(RemovePath) then
  begin
    DelTree(RemovePath, True, True, True);
  end;
end;

// ============================================================================
// Preflight Check
// ============================================================================

function RunPreflightCheck(): Boolean;
var
  I: Integer;
  DepInfo: TDependencyInfo;
  CheckPath: String;
  MissingDeps: TStringList;
begin
  Result := True;
  MissingDeps := TStringList.Create;
  
  try
    for I := 0 to DependencyList.Count - 1 do
    begin
      DepInfo := GetDependencyInfo(DependencyList[I]);
      CheckPath := ExpandConstant('{tmp}') + '\' + DepInfo.Filename;
      
      if not FileExists(CheckPath) then
      begin
        MissingDeps.Add(DepInfo.Filename);
      end;
    end;
    
    if MissingDeps.Count > 0 then
    begin
      Log('Missing dependency files: ' + MissingDeps.Text);
      Result := False;
    end;
  finally
    MissingDeps.Free;
  end;
end;