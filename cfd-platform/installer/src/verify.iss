; ============================================================================
; HX CFD Verification Module
; SHA-256 verification and health check functions
; ============================================================================

// ============================================================================
// SHA-256 Hash Functions
// ============================================================================

function CalculateSHA256(const FilePath: String): String;
var
  ResultCode: Integer;
  HashOutput: String;
  PowerShellScript: String;
begin
  Result := '';
  
  // Try using ISSigTool.exe first (comes with Inno Setup)
  if FileExists(ExpandConstant('{pf32}\Inno Setup 6\ISSigTool.exe')) then
  begin
    if Exec(ExpandConstant('{pf32}\Inno Setup 6\ISSigTool.exe'), 
            '-sha256 "' + FilePath + '"',
            '', SW_HIDE, ewWaitUntilTerminated, ResultCode, HashOutput) then
    begin
      // Parse output - remove any extra text
      HashOutput := Trim(HashOutput);
      if Pos('SHA256:', HashOutput) > 0 then
        HashOutput := Trim(Copy(HashOutput, Pos(':', HashOutput) + 1, Length(HashOutput)));
      Result := HashOutput;
      Exit;
    end;
  end;
  
  // Fallback to PowerShell
  PowerShellScript := '(Get-FileHash -Path ''' + FilePath + ''' -Algorithm SHA256).Hash.ToLower()';
  
  if Exec('powershell', '-NoProfile -Command "' + PowerShellScript + '"',
          '', SW_HIDE, ewWaitUntilTerminated, ResultCode, HashOutput) then
  begin
    Result := Trim(HashOutput);
  end;
end;

function VerifyFileSHA256(const FilePath: String; const ExpectedHash: String): Boolean;
var
  ActualHash: String;
begin
  Result := False;
  
  // Normalize hashes to uppercase for comparison
  ExpectedHash := UpperCase(ExpectedHash);
  
  // Skip verification for placeholder hashes (all zeros)
  if ExpectedHash = StringOfChar('0', 64) then
  begin
    Log('Skipping SHA-256 verification for ' + ExtractFileName(FilePath) + ' (placeholder hash)');
    Result := True;
    Exit;
  end;
  
  // Calculate actual hash
  ActualHash := CalculateSHA256(FilePath);
  
  if ActualHash = '' then
  begin
    Log('Failed to calculate SHA-256 for ' + FilePath);
    Exit;
  end;
  
  ActualHash := UpperCase(ActualHash);
  
  if ActualHash <> ExpectedHash then
  begin
    Log('SHA-256 MISMATCH for ' + ExtractFileName(FilePath));
    Log('  Expected: ' + ExpectedHash);
    Log('  Actual:   ' + ActualHash);
    Result := False;
  end
  else
  begin
    Log('SHA-256 verified for ' + ExtractFileName(FilePath));
    Result := True;
  end;
end;

// ============================================================================
// File Verification
// ============================================================================

function VerifyFileExists(const FilePath: String): Boolean;
begin
  Result := FileExists(FilePath);
  if not Result then
  begin
    Log('File not found: ' + FilePath);
  end;
end;

function VerifyDirectoryExists(const DirPath: String): Boolean;
begin
  Result := DirExists(DirPath);
  if not Result then
  begin
    Log('Directory not found: ' + DirPath);
  end;
end;

function VerifyFileSize(const FilePath: String; const MinSize: Int64): Boolean;
var
  Size: Int64;
begin
  Result := False;
  
  if not FileExists(FilePath) then
  begin
    Log('Cannot verify size - file not found: ' + FilePath);
    Exit;
  end;
  
  Size := GetFileSize(FilePath);
  Result := (Size >= MinSize);
  
  if not Result then
  begin
    Log('File too small: ' + FilePath + ' (' + IntToStr(Size) + ' < ' + IntToStr(MinSize) + ')');
  end;
end;

function VerifyFileNotEmpty(const FilePath: String): Boolean;
begin
  Result := VerifyFileSize(FilePath, 1);
end;

// ============================================================================
// Health Check Functions
// ============================================================================

function RunHealthCheck(const DepID: String): Boolean;
var
  DepInfo: TDependencyInfo;
begin
  DepInfo := GetDependencyInfo(DepID);
  Result := RunHealthCheckEx(DepInfo);
end;

function RunHealthCheckEx(const DepInfo: TDependencyInfo): Boolean;
var
  Output: String;
  ResultCode: Integer;
  CheckPath: String;
begin
  Result := False;
  CheckPath := ExpandConstant('{app}');
  
  if DepInfo.HealthCheckType = 'command' then
  begin
    // Execute command and check output
    if DepInfo.HealthCheckCommand <> '' then
    begin
      if Exec(CheckPath + '\bin\' + DepInfo.HealthCheckCommand, 
              DepInfo.HealthCheckArgs, '', SW_HIDE, ewWaitUntilTerminated, ResultCode, Output) then
      begin
        Result := (Pos(DepInfo.HealthCheckExpected, Output) > 0);
        if not Result then
        begin
          Log('Health check failed for ' + DepInfo.Name + ': output does not contain "' + DepInfo.HealthCheckExpected + '"');
          Log('  Output: ' + Output);
        end;
      end
      else
      begin
        Log('Health check failed for ' + DepInfo.Name + ': command execution failed');
      end;
    end;
  end
  else if DepInfo.HealthCheckType = 'python_import' then
  begin
    // Check Python import
    if Exec('python', '-c "import ' + DepInfo.HealthCheckExpected + '; print(\'ok\')"', 
            '', SW_HIDE, ewWaitUntilTerminated, ResultCode, Output) then
    begin
      Result := (ResultCode = 0) and (Pos('ok', Output) > 0);
      if not Result then
      begin
        Log('Health check failed for ' + DepInfo.Name + ': Python import failed');
      end;
    end
    else
    begin
      Log('Health check failed for ' + DepInfo.Name + ': Python not available');
    end;
  end
  else if DepInfo.HealthCheckType = 'file_exists' then
  begin
    // Check if expected file exists
    CheckPath := CheckPath + '\' + DepInfo.InstallPath + '\' + DepInfo.HealthCheckExpected;
    Result := FileExists(CheckPath);
    if not Result then
    begin
      Log('Health check failed for ' + DepInfo.Name + ': expected file not found at ' + CheckPath);
    end;
  end
  else if DepInfo.HealthCheckType = 'directory_exists' then
  begin
    // Check if directory exists
    CheckPath := CheckPath + '\' + DepInfo.InstallPath;
    Result := DirExists(CheckPath);
    if not Result then
    begin
      Log('Health check failed for ' + DepInfo.Name + ': directory not found at ' + CheckPath);
    end;
  end;
  
  if Result then
  begin
    Log('Health check passed for ' + DepInfo.Name);
  end;
end;

// ============================================================================
// Dependency Verification
// ============================================================================

function VerifyDependencyInstallation(const DepID: String): Boolean;
var
  DepInfo: TDependencyInfo;
  InstallPath: String;
begin
  Result := False;
  DepInfo := GetDependencyInfo(DepID);
  InstallPath := ExpandConstant('{app}') + '\' + DepInfo.InstallPath;
  
  // Check directory exists
  if not DirExists(InstallPath) then
  begin
    Log('Verification failed for ' + DepInfo.Name + ': installation directory not found');
    Exit;
  end;
  
  // Run health check
  if not RunHealthCheckEx(DepInfo) then
  begin
    Log('Verification failed for ' + DepInfo.Name + ': health check failed');
    Exit;
  end;
  
  Result := True;
end;

function VerifyAllDependencies(): TStringList;
var
  I: Integer;
  FailedList: TStringList;
begin
  FailedList := TStringList.Create;
  
  for I := 0 to DependencyList.Count - 1 do
  begin
    if not VerifyDependencyInstallation(DependencyList[I]) then
    begin
      FailedList.Add(DependencyList[I]);
    end;
  end;
  
  Result := FailedList;
end;

// ============================================================================
// Bundle Verification
// ============================================================================

function VerifyBundleIntegrity(const BundlePath: String; const ExpectedHash: String): Boolean;
begin
  Result := False;
  
  if not FileExists(BundlePath) then
  begin
    Log('Bundle not found: ' + BundlePath);
    Exit;
  end;
  
  if not VerifyFileNotEmpty(BundlePath) then
  begin
    Log('Bundle is empty: ' + BundlePath);
    Exit;
  end;
  
  if ExpectedHash <> '' then
  begin
    Result := VerifyFileSHA256(BundlePath, ExpectedHash);
  end
  else
  begin
    Result := True;
  end;
end;

function VerifyAllBundles(): TStringList;
var
  I: Integer;
  DepInfo: TDependencyInfo;
  BundlePath: String;
  FailedList: TStringList;
begin
  FailedList := TStringList.Create;
  
  for I := 0 to DependencyList.Count - 1 do
  begin
    DepInfo := GetDependencyInfo(DependencyList[I]);
    BundlePath := ExpandConstant('{tmp}') + '\' + DepInfo.Filename;
    
    if not FileExists(BundlePath) then
    begin
      FailedList.Add(DepInfo.Name + ': bundle not found');
    end
    else if not VerifyBundleIntegrity(BundlePath, DepInfo.SHA256) then
    begin
      FailedList.Add(DepInfo.Name + ': bundle integrity check failed');
    end;
  end;
  
  Result := FailedList;
end;

// ============================================================================
// Signature Verification (for signed executables)
// ============================================================================

function VerifyAuthenticodeSignature(const FilePath: String): Boolean;
var
  ResultCode: Integer;
  Output: String;
begin
  Result := False;
  
  // Use PowerShell's Get-AuthenticodeSignature
  if Exec('powershell', 
          '-NoProfile -Command "(Get-AuthenticodeSignature ''' + FilePath + ''').Status -eq ''Valid''"',
          '', SW_HIDE, ewWaitUntilTerminated, ResultCode, Output) then
  begin
    Result := (Pos('True', Output) > 0);
  end;
end;

function VerifyAllExecutables(): TStringList;
var
  ExeList: TStringList;
  I: Integer;
  ExePath: String;
begin
  ExeList := TStringList.Create;
  ExeList.Add(ExpandConstant('{app}') + '\{#MyAppExeName}');
  ExeList.Add(ExpandConstant('{app}') + '\{#BACKEND_EXE}');
  
  Result := TStringList.Create;
  
  for I := 0 to ExeList.Count - 1 do
  begin
    ExePath := ExeList[I];
    if FileExists(ExePath) then
    begin
      if not VerifyAuthenticodeSignature(ExePath) then
      begin
        Result.Add(ExtractFileName(ExePath) + ': signature verification failed');
      end;
    end
    else
    begin
      Result.Add(ExtractFileName(ExePath) + ': executable not found');
    end;
  end;
  
  ExeList.Free;
end;