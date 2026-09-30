[CmdletBinding()]
param(
    [string]$DevRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    [string]$VanillaRoot = 'D:/SteamLibrary/steamapps/common/Crusader Kings III/game',
    [string]$AgotRoot = 'D:/SteamLibrary/steamapps/workshop/content/1158310/2962333032',
    [string]$PythonExe = 'python',
    [string]$ReportPath = ''
)
$ErrorActionPreference = 'Stop'
$p = Join-Path $DevRoot 'parley/mod/parley'
$m = Join-Path $DevRoot 'marriage_calc_assistant/mod/marriage_calc_assistant'
$a = Join-Path $DevRoot 'agot_marriage_calc_assistant/mod/agot_marriage_calc_assistant'
$family = Join-Path $PSScriptRoot 'family'
$runs = @(
    @{ name='family'; exe='pwsh'; args=@('-NoProfile','-File',"$family/tnt_family_gate.ps1",'-CoreRoot',$p,'-McaRoot',$m,'-AdapterRoot',$a,'-VanillaRoot',$VanillaRoot,'-AgotRoot',$AgotRoot) },
    @{ name='frozen'; exe='pwsh'; args=@('-NoProfile','-File',"$family/tnt_frozen_sync_check.ps1",'-McaRoot',$m,'-AdapterRoot',$a,'-VanillaRoot',$VanillaRoot,'-AgotRoot',$AgotRoot) },
    @{ name='rules'; exe='pwsh'; args=@('-NoProfile','-File',"$family/tnt_rule_conformance.ps1",'-ModRoot',$p) },
    @{ name='dispatch_model'; exe='pwsh'; args=@('-NoProfile','-File',"$family/tnt_ai_dispatch_model.ps1",'-ParleyRoot',$p) },
    @{ name='offer_rate'; exe='pwsh'; args=@('-NoProfile','-File',"$family/tnt_ai_offer_rate_check.ps1",'-ParleyRoot',$p) },
    @{ name='mca_source'; exe='pwsh'; args=@('-NoProfile','-File',"$DevRoot/marriage_calc_assistant/tests/mca/check_source.ps1",'-McaRoot',$m,'-GameRoot',$VanillaRoot) },
    @{ name='mca_sort_model'; exe='pwsh'; args=@('-NoProfile','-File',"$DevRoot/marriage_calc_assistant/tests/mca/test_sort_math.ps1") },
    @{ name='agot_adapter'; exe=$PythonExe; args=@('-B',"$DevRoot/agot_marriage_calc_assistant/tests/agot_mca/test_adapter.py",'--mod',$a,'--core',$m,'--agot',$AgotRoot,'-v') }
)
$results = foreach ($run in $runs) {
    $output = @(& $run.exe @($run.args) 2>&1 | ForEach-Object { $_.ToString() })
    $code = $LASTEXITCODE
    Write-Host ("{0}: exit {1}" -f $run.name, $code)
    [pscustomobject]@{name=$run.name;exit_code=$code;output=($output -join "`n")}
}
if ($ReportPath) {
    $null = New-Item -ItemType Directory -Path (Split-Path -Parent $ReportPath) -Force
    [IO.File]::WriteAllText($ReportPath,($results | ConvertTo-Json -Depth 5)+"`n",[Text.UTF8Encoding]::new($false))
}
if (@($results | Where-Object exit_code -NE 0).Count) { exit 1 }
exit 0
