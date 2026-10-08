param([Parameter(Mandatory=$true)][string]$Run)
$ErrorActionPreference = 'Stop'
# READ-ONLY with respect to processes. The coordinator alone executes this.
# It never signals CK3, CrashReporter, or any user process.
$windowRun = [IO.Path]::GetFullPath($Run)
$windowRecordPath = Join-Path $windowRun 'process-result.json'
$windowManifestPath = Join-Path $windowRun 'frozen-manifest.json'
$windowRecord = Get-Content -LiteralPath $windowRecordPath -Raw | ConvertFrom-Json
$windowManifest = Get-Content -LiteralPath $windowManifestPath -Raw | ConvertFrom-Json
if ($windowRecord.status -ne 'RUNNING') { throw 'Record is not RUNNING; preserve it unchanged.' }
if ($windowManifest.kind -ne 'PRODUCTION_WINDOW_OPEN_CRASH_DIAGNOSTIC') { throw 'Not this diagnostic harness.' }
if ([IO.Path]::GetFullPath($windowRecord.executable) -ne [IO.Path]::GetFullPath($windowManifest.executable)) { throw 'Executable record mismatch.' }
$windowExpectedProfile = [IO.Path]::GetFullPath((Join-Path $windowRun 'userdata'))
if ([IO.Path]::GetFullPath($windowRecord.profile) -ne $windowExpectedProfile) { throw 'Exact isolated profile mismatch.' }
if (Get-Process -Id $windowRecord.pid -ErrorAction SilentlyContinue) { throw 'Recorded PID still exists (possibly reused); root must resolve identity, no record changed.' }
if (Get-CimInstance Win32_Process -Filter ('ProcessId=' + $windowRecord.pid)) { throw 'Recorded PID exists in CIM; no record changed.' }
$windowArguments = @($windowRecord.arguments | Where-Object { $_ -like '-userdir=*' })
if ($windowArguments.Count -ne 1 -or $windowArguments[0] -ne ('-userdir="' + $windowRecord.profile + '"')) { throw 'Launch userdir argument mismatch.' }
$windowRecord.status = 'EXIT_CONFIRMED'
$windowRecord | Add-Member -NotePropertyName stopped_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
$windowRecord | Add-Member -NotePropertyName exit_basis -NotePropertyValue 'RECORDED_PID_ABSENT_IN_PROCESS_AND_CIM_NO_STOP_COMMAND_SENT' -Force
$windowRecord | Add-Member -NotePropertyName native_exit_code -NotePropertyValue $null -Force
$windowRecord | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $windowRecordPath -Encoding utf8
