; Instalador da Operacao Assistida — gerado com Inno Setup.
; Build pre-requisito: pyinstaller installer/app.spec --noconfirm  (gera dist/OperacaoAssistida)
; Compilar: iscc installer/setup.iss

#define MyAppName "Operação Assistida"
#define MyAppExeName "OperacaoAssistida.exe"
#define MyAppPublisher "Operação Assistida"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

[Setup]
AppId={{B6A6F1B0-6D0B-4B6E-9A8B-7E6E5C1A6E9A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\OperacaoAssistida
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\dist_installer
OutputBaseFilename=OperacaoAssistida-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
SetupIconFile=assets\app.ico
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"
Name: "startupicon"; Description: "Iniciar automaticamente com o Windows (em segundo plano, sem abrir janela — apenas o ícone na bandeja)"; GroupDescription: "Inicialização:"

[Files]
Source: "..\dist\OperacaoAssistida\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "OperacaoAssistida"; ValueData: """{app}\{#MyAppExeName}"" --minimized"; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName} agora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\OperacaoAssistida"
Type: filesandordirs; Name: "{app}"

[Code]
var
  ConsentPage: TWizardPage;
  ConsentCheck: TNewCheckBox;
  InstallKey: String;

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  // encerra o app antes de remover arquivos, caso esteja em execução
  Exec(ExpandConstant('{cmd}'), '/C taskkill /IM {#MyAppExeName} /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  // encerra instância em execução antes de sobrescrever os arquivos (atualização)
  Exec(ExpandConstant('{cmd}'), '/C taskkill /IM {#MyAppExeName} /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

function GenerateInstallKey(): String;
var
  i: Integer;
begin
  Result := '';
  for i := 1 to 6 do
    Result := Result + IntToStr(Random(10));
end;

{ Página de identificação desta instalação: mostra máquina/usuário/chave gerada
  e exige consentimento explícito do operador antes de seguir a instalação. }
procedure InitializeWizard();
var
  Intro, HostLabel, UserLabel, KeyLabel, HostValue, UserValue, KeyValue: TNewStaticText;
begin
  InstallKey := GenerateInstallKey();

  ConsentPage := CreateCustomPage(wpSelectDir, 'Identificação desta instalação',
    'Estas informações identificam esta instalação para fins de autenticação.');

  Intro := TNewStaticText.Create(ConsentPage);
  Intro.Parent := ConsentPage.Surface;
  Intro.Top := 0;
  Intro.Width := ConsentPage.SurfaceWidth;
  Intro.AutoSize := False;
  Intro.WordWrap := True;
  Intro.Caption :=
    'A Operação Assistida usa o nome desta máquina e do usuário do Windows como ' +
    'base de autenticação ao autorizar tarefas. Uma chave de 6 dígitos também é ' +
    'gerada agora para identificar esta instalação de forma única. Essas informações ' +
    'são exibidas apenas nesta etapa e ficam registradas no arquivo de configuração ' +
    'da instalação.';

  HostLabel := TNewStaticText.Create(ConsentPage);
  HostLabel.Parent := ConsentPage.Surface;
  HostLabel.Top := Intro.Top + Intro.Height + 18;
  HostLabel.Caption := 'Nome da máquina:';

  HostValue := TNewStaticText.Create(ConsentPage);
  HostValue.Parent := ConsentPage.Surface;
  HostValue.Top := HostLabel.Top;
  HostValue.Left := 180;
  HostValue.Caption := ExpandConstant('{computername}');
  HostValue.Font.Style := [fsBold];

  UserLabel := TNewStaticText.Create(ConsentPage);
  UserLabel.Parent := ConsentPage.Surface;
  UserLabel.Top := HostLabel.Top + 22;
  UserLabel.Caption := 'Usuário do Windows:';

  UserValue := TNewStaticText.Create(ConsentPage);
  UserValue.Parent := ConsentPage.Surface;
  UserValue.Top := UserLabel.Top;
  UserValue.Left := 180;
  UserValue.Caption := ExpandConstant('{username}');
  UserValue.Font.Style := [fsBold];

  KeyLabel := TNewStaticText.Create(ConsentPage);
  KeyLabel.Parent := ConsentPage.Surface;
  KeyLabel.Top := UserLabel.Top + 22;
  KeyLabel.Caption := 'Chave desta instalação:';

  KeyValue := TNewStaticText.Create(ConsentPage);
  KeyValue.Parent := ConsentPage.Surface;
  KeyValue.Top := KeyLabel.Top;
  KeyValue.Left := 180;
  KeyValue.Caption := InstallKey;
  KeyValue.Font.Style := [fsBold];

  ConsentCheck := TNewCheckBox.Create(ConsentPage);
  ConsentCheck.Parent := ConsentPage.Surface;
  ConsentCheck.Top := KeyLabel.Top + 36;
  ConsentCheck.Width := ConsentPage.SurfaceWidth;
  ConsentCheck.Caption := 'Concordo com o uso destas informações para autenticar esta instalação.';
  ConsentCheck.Checked := False;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = ConsentPage.ID) and (not ConsentCheck.Checked) then
  begin
    MsgBox('É necessário concordar para continuar a instalação.', mbError, MB_OK);
    Result := False;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfPath: String;
  Lines: TArrayOfString;
begin
  if CurStep = ssPostInstall then
  begin
    ConfPath := ExpandConstant('{app}\instalacao.conf');
    SetArrayLength(Lines, 5);
    Lines[0] := '[instalacao]';
    Lines[1] := 'maquina=' + ExpandConstant('{computername}');
    Lines[2] := 'usuario=' + ExpandConstant('{username}');
    Lines[3] := 'chave_instalacao=' + InstallKey;
    Lines[4] := 'data_instalacao=' + GetDateTimeString('yyyy-mm-dd hh:nn:ss', #0, #0);
    SaveStringsToFile(ConfPath, Lines, False);
  end;
end;
