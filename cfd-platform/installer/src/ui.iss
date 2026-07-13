; ============================================================================
; HX CFD UI Module
; Custom wizard page creation and UI helper functions
; ============================================================================

// ============================================================================
// Global UI Variables
// ============================================================================

var
  DependencyPage: TOutputMsgMemoWizardPage;
  DependencyListBox: TNewCheckListBox;
  DependencyProgressPage: TOutputProgressWizardPage;
  DependencyStatusLabel: TNewStaticText;
  DependencyDetailLabel: TNewStaticText;
  DependencyProgressBar: TNewProgressBar;
  InstallResultsPage: TOutputMsgMemoWizardPage;
  SummaryPage: TOutputMsgMemoWizardPage;

// ============================================================================
// Page Creation Functions
// ============================================================================

procedure CreateDependencySelectionPage();
var
  I: Integer;
  DepInfo: TDependencyInfo;
begin
  DependencyPage := CreateOutputMsgMemoWizardPage(wpSelectTasks,
    'Select Dependencies',
    '{#SetupSetting("AppName")} includes several optional components. ' +
    'Select which components you want to install.',
    'Dependencies:',
    True);
    
  DependencyPage.StatusLabel := TNewStaticText.Create(DependencyPage);
  with DependencyPage.StatusLabel do
  begin
    Parent := DependencyPage.Surface;
    Caption := 'Select components to install:';
    AutoSize := True;
    Left := 0;
    Top := 0;
  end;
  
  DependencyListBox := TNewCheckListBox.Create(DependencyPage);
  with DependencyListBox do
  begin
    Parent := DependencyPage.Surface;
    Left := 0;
    Top := DependencyPage.StatusLabel.Top + DependencyPage.StatusLabel.Height + 8;
    Width := DependencyPage.SurfaceWidth;
    Height := 250;
    Color := clWindow;
    BorderStyle := bsSingle;
    TabStop := True;
    WantTabs := True;
    MultiSelect := False;
    CheckBoxes := True;
    
    // Add dependencies to list
    for I := 0 to DependencyList.Count - 1 do
    begin
      DepInfo := GetDependencyInfo(DependencyList[I]);
      AddCheckBox(DepInfo.Name + ' ' + DepInfo.Version,
                  DepInfo.Description,
                  0, True, True, True, False, nil);
    end;
  end;
  
  // Set list height based on items
  DependencyListBox.Height := Min(DependencyListBox.Count * 20, 280);
end;

procedure CreateDependencyProgressPage();
begin
  DependencyProgressPage := CreateOutputProgressWizardPage(wpInstalling,
    'Installing Dependencies',
    'Please wait while {#SetupSetting("AppName")} installs dependencies.',
    '');
    
  DependencyStatusLabel := TNewStaticText.Create(DependencyProgressPage);
  with DependencyStatusLabel do
  begin
    Parent := DependencyProgressPage.StatusLabel.Parent;
    Caption := 'Preparing...';
    AutoSize := True;
    Left := DependencyProgressPage.StatusLabel.Left;
    Top := DependencyProgressPage.StatusLabel.Top + DependencyProgressPage.StatusLabel.Height + 8;
  end;
  
  DependencyDetailLabel := TNewStaticText.Create(DependencyProgressPage);
  with DependencyDetailLabel do
  begin
    Parent := DependencyProgressPage.StatusLabel.Parent;
    Caption := '';
    AutoSize := True;
    Left := DependencyStatusLabel.Left;
    Top := DependencyStatusLabel.Top + DependencyStatusLabel.Height + 4;
    Font.Color := clGrayText;
  end;
  
  DependencyProgressBar := TNewProgressBar.Create(DependencyProgressPage);
  with DependencyProgressBar do
  begin
    Parent := DependencyProgressPage.ProgressBar.Parent;
    Left := DependencyProgressPage.ProgressBar.Left;
    Top := DependencyProgressPage.ProgressBar.Top;
    Width := DependencyProgressPage.ProgressBar.Width;
    Height := DependencyProgressPage.ProgressBar.Height;
    Min := 0;
    Max := 100;
    Position := 0;
  end;
end;

procedure CreateInstallResultsPage();
begin
  InstallResultsPage := CreateOutputMsgMemoWizardPage(wpFinished,
    'Installation Results',
    'The following shows the results of the installation.',
    '',
    True);
end;

procedure CreateSummaryPage();
begin
  SummaryPage := CreateOutputMsgMemoWizardPage(wpSelectDir,
    'Installation Summary',
    'Review the installation settings before proceeding.',
    '',
    True);
end;

// ============================================================================
// UI Update Functions
// ============================================================================

procedure UpdateDependencyProgress(const Current, Total: Integer; const Status: String);
begin
  if Assigned(DependencyProgressBar) then
  begin
    DependencyProgressBar.Position := (Current * 100) div Total;
    DependencyProgressBar.Update;
  end;
  
  if Assigned(DependencyStatusLabel) then
  begin
    DependencyStatusLabel.Caption := Status;
    DependencyStatusLabel.Update;
  end;
  
  if Assigned(DependencyDetailLabel) then
  begin
    DependencyDetailLabel.Caption := 'Progress: ' + IntToStr(Current) + ' of ' + IntToStr(Total);
    DependencyDetailLabel.Update;
  end;
end;

procedure UpdateDependencyStatus(const Status: String);
begin
  if Assigned(DependencyStatusLabel) then
  begin
    DependencyStatusLabel.Caption := Status;
    DependencyStatusLabel.Update;
  end;
end;

procedure UpdateDependencyDetail(const Detail: String);
begin
  if Assigned(DependencyDetailLabel) then
  begin
    DependencyDetailLabel.Caption := Detail;
    DependencyDetailLabel.Update;
  end;
end;

procedure SetProgressBarState(const State: Integer);
begin
  if Assigned(DependencyProgressBar) then
  begin
    // 0 = normal, 1 = error, 2 = paused, 3 = indeterminate
    // Note: Inno Setup doesn't support all states, but we try
    DependencyProgressBar.Update;
  end;
end;

// ============================================================================
// List Box Functions
// ============================================================================

function GetSelectedDependencies(): TStringList;
var
  I: Integer;
  DepInfo: TDependencyInfo;
begin
  Result := TStringList.Create;
  
  if not Assigned(DependencyListBox) then
    Exit;
    
  for I := 0 to DependencyListBox.Items.Count - 1 do
  begin
    if DependencyListBox.Checked[I] then
    begin
      Result.Add(DependencyList[I]);
    end;
  end;
end;

function GetDependencyCheckState(const Index: Integer): Boolean;
begin
  Result := False;
  if Assigned(DependencyListBox) and (Index < DependencyListBox.Items.Count) then
  begin
    Result := DependencyListBox.Checked[Index];
  end;
end;

procedure SetDependencyCheckState(const Index: Integer; const Checked: Boolean);
begin
  if Assigned(DependencyListBox) and (Index < DependencyListBox.Items.Count) then
  begin
    DependencyListBox.Checked[Index] := Checked;
  end;
end;

procedure SelectAllDependencies();
var
  I: Integer;
begin
  if not Assigned(DependencyListBox) then
    Exit;
    
  for I := 0 to DependencyListBox.Items.Count - 1 do
  begin
    DependencyListBox.Checked[I] := True;
  end;
end;

procedure DeselectAllDependencies();
var
  I: Integer;
begin
  if not Assigned(DependencyListBox) then
    Exit;
    
  for I := 0 to DependencyListBox.Items.Count - 1 do
  begin
    DependencyListBox.Checked[I] := False;
  end;
end;

// ============================================================================
// Message Display Functions
// ============================================================================

procedure ShowMessage(const Msg: String);
begin
  MsgBox(Msg, mbInformation, MB_OK);
end;

procedure ShowError(const Msg: String);
begin
  MsgBox(Msg, mbError, MB_OK);
end;

procedure ShowWarning(const Msg: String);
begin
  MsgBox(Msg, mbConfirmation, MB_OK);
end;

function ConfirmMessage(const Msg: String): Boolean;
begin
  Result := (MsgBox(Msg, mbConfirmation, MB_YESNO) = IDYES);
end;

procedure AppendToResults(const Line: String);
begin
  if Assigned(InstallResultsPage) and Assigned(InstallResultsPage.Memo) then
  begin
    InstallResultsPage.Memo.Lines.Add(Line);
    InstallResultsPage.Memo.Update;
  end;
end;

procedure ClearResults();
begin
  if Assigned(InstallResultsPage) and Assigned(InstallResultsPage.Memo) then
  begin
    InstallResultsPage.Memo.Lines.Clear;
  end;
end;

// ============================================================================
// Custom Form Elements
// ============================================================================

procedure CreateInfoPanel(const ParentPage: TWizardPage; const Title, Content: String; 
                         const Left, Top, Width, Height: Integer);
var
  Panel: TPanel;
  TitleLabel: TLabel;
  ContentLabel: TLabel;
begin
  Panel := TPanel.Create(ParentPage);
  with Panel do
  begin
    Parent := ParentPage.Surface;
    Left := Left;
    Top := Top;
    Width := Width;
    Height := Height;
    BevelOuter := bvNone;
    Color := clBtnFace;
    BorderStyle := bsSingle;
    BorderWidth := 1;
  end;
  
  TitleLabel := TLabel.Create(Panel);
  with TitleLabel do
  begin
    Parent := Panel;
    Left := 8;
    Top := 8;
    Width := Width - 16;
    Caption := Title;
    Font.Style := [fsBold];
  end;
  
  ContentLabel := TLabel.Create(Panel);
  with ContentLabel do
  begin
    Parent := Panel;
    Left := 8;
    Top := TitleLabel.Top + TitleLabel.Height + 4;
    Width := Width - 16;
    Height := Height - TitleLabel.Height - 20;
    Caption := Content;
    WordWrap := True;
    AutoSize := False;
  end;
end;

procedure CreateButton(const ParentPage: TWizardPage; const Caption: String;
                      const OnClick: TNotifyEvent; const Left, Top: Integer): TButton;
begin
  Result := TButton.Create(ParentPage);
  with Result do
  begin
    Parent := ParentPage.Surface;
    Name := Caption + 'Button';
    Caption := Caption;
    Left := Left;
    Top := Top;
    Width := 75;
    Height := 25;
    OnClick := OnClick;
  end;
end;

procedure CreateLinkLabel(const ParentPage: TWizardPage; const Caption, URL: String;
                          const Left, Top: Integer): TNewStaticText;
begin
  Result := TNewStaticText.Create(ParentPage);
  with Result do
  begin
    Parent := ParentPage.Surface;
    Caption := Caption;
    Left := Left;
    Top := Top;
    Cursor := crHand;
    Font.Color := clBlue;
    Font.Style := [fsUnderline];
    OnClick := @LaunchUrl;
  end;
end;

// ============================================================================
// URL Handler
// ============================================================================

procedure LaunchUrl(Sender: TObject);
var
  URL: String;
begin
  URL := TNewStaticText(Sender).Caption;
  if Pos('http', URL) = 0 then
    URL := 'https://' + URL;
    
  ShellExec('open', URL, '', '', SW_SHOWNORMAL, ewNoWait);
end;

// ============================================================================
// Progress Animation
// ============================================================================

procedure StartProgressAnimation();
begin
  if Assigned(DependencyProgressBar) then
  begin
    // Could add marquee style here if supported
    DependencyProgressBar.Position := 0;
  end;
end;

procedure StopProgressAnimation();
begin
  if Assigned(DependencyProgressBar) then
  begin
    DependencyProgressBar.Position := 100;
  end;
end;

procedure PulseProgress();
begin
  if Assigned(DependencyProgressBar) then
  begin
    DependencyProgressBar.Position := (DependencyProgressBar.Position + 10) mod 100;
    DependencyProgressBar.Update;
  end;
end;

// ============================================================================
// Color and Style Helpers
// ============================================================================

procedure SetPageBackgroundColor(const Page: TWizardPage; const Color: TColor);
begin
  // Note: Inno Setup wizard pages have limited styling
  // This is a placeholder for future enhancements
end;

procedure SetLabelStyle(const Label: TLabel; const Style: TFontStyles);
begin
  Label.Font.Style := Style;
  Label.Update;
end;

procedure SetLabelColor(const Label: TLabel; const Color: TColor);
begin
  Label.Font.Color := Color;
  Label.Update;
end;

// ============================================================================
// Cleanup
// ============================================================================

procedure CleanupUIPages();
begin
  if Assigned(DependencyListBox) then
    DependencyListBox.Free;
  DependencyListBox := nil;
end;