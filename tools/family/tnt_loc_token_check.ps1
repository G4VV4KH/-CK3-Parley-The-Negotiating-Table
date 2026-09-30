# =====================================================================================
# tnt_loc_token_check.ps1 - THE CHECK THAT CATCHES A RAW KEY IN A BLOCKED-CONTROL HOVER
#
# WHY THIS EXISTS. User item 3 was reported three times and closed wrongly twice, because
# every audit asked "is the loc key declared" - and it always was. The rule it should have
# asked about is:
#
#   A LOC STRING NAMED BY A custom_description / custom_tooltip THAT IS REACHED THROUGH A
#   scripted_gui's BuildTooltip MUST NOT CONTAIN A [ ... ] TOKEN. Not a game concept
#   ([hook|E], [Concept('hook','крючок')|E]), not a concept icon alias ([prestige_i],
#   [gold_i]), not a scope data function. In that one rendering path the token does not
#   expand and CK3 prints the RAW KEY instead of the sentence.
#
# WHAT IS STILL ALLOWED in those strings, proven in-context by tnt_ob_req_succ - same file,
# same is_valid shape, same contract panel as the two tnt_ob_req_* keys that DO fail:
#   * nested loc keys        $confederate_partition_succession_law$
#   * text formatting        #high ... #!   #weak ... #!   #N ... #!
#
# The interaction / decision path is NOT affected: vanilla ships 404 token-carrying
# custom_description strings there. Keys used only from common\character_interactions or
# common\decisions are therefore reported as NOTE, not as failures.
#
# USAGE:
#   powershell -ExecutionPolicy Bypass -File _docs\tools\tnt_loc_token_check.ps1
#   powershell ... -ModRoot <path> -VanillaRoot <path to ...\Crusader Kings III\game>
# Exit 0 = clean, 1 = at least one offender on the BuildTooltip path, 2 = bad arguments.
# =====================================================================================
param(
    [string]$ModRoot     = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent),
    [string]$VanillaRoot = 'D:\SteamLibrary\steamapps\common\Crusader Kings III\game'
)
$ErrorActionPreference = 'Stop'

if (-not (Test-Path (Join-Path $ModRoot 'descriptor.mod'))) {
    Write-Host "ERROR: -ModRoot '$ModRoot' has no descriptor.mod - not the mod root."; exit 2
}

function Read-LocDir([string]$dir) {
    $tbl = New-Object 'System.Collections.Generic.Dictionary[string,psobject]' ([System.StringComparer]::OrdinalIgnoreCase)
    if (-not (Test-Path $dir)) { return $tbl }
    $rxLoc = [regex]'^\s*([A-Za-z0-9_.\-]+):\s*\d*\s*"(.*)"'
    foreach ($f in (Get-ChildItem $dir -Recurse -Filter *.yml -File)) {
        $n = 0
        foreach ($line in [System.IO.File]::ReadAllLines($f.FullName, [System.Text.Encoding]::UTF8)) {
            $n++
            $m = $rxLoc.Match($line)
            if ($m.Success -and -not $tbl.ContainsKey($m.Groups[1].Value)) {
                $tbl.Add($m.Groups[1].Value, [pscustomobject]@{ text=$m.Groups[2].Value; line=$n; file=$f.Name })
            }
        }
    }
    return $tbl
}

# ---- 1. every custom_description / custom_tooltip text key in the shipped script ----
$rxText = [regex]'\btext\s*=\s*"?([A-Za-z0-9_.\-]+)"?'
$sites  = New-Object System.Collections.ArrayList
$scriptDirs = @('common','events') | ForEach-Object { Join-Path $ModRoot $_ } | Where-Object { Test-Path $_ }
foreach ($f in (Get-ChildItem $scriptDirs -Recurse -Filter *.txt -File)) {
    $clean = ((([System.IO.File]::ReadAllText($f.FullName)) -split "`n") |
              ForEach-Object { $_ -replace '#.*$','' }) -join "`n"
    foreach ($kw in @('custom_description','custom_description_no_bullet','custom_tooltip')) {
        foreach ($m in ([regex]("\b" + $kw + "\s*=\s*\{")).Matches($clean)) {
            $i = $m.Index + $m.Length; $depth = 1     # brace-match: triggers nest inside
            while ($i -lt $clean.Length -and $depth -gt 0) {
                if ($clean[$i] -eq '{') { $depth++ } elseif ($clean[$i] -eq '}') { $depth-- }
                $i++
            }
            $body = $clean.Substring($m.Index+$m.Length, [Math]::Max(0,$i-1-($m.Index+$m.Length)))
            $t = $rxText.Match($body); if (-not $t.Success) { continue }
            $rel = $f.FullName.Substring($ModRoot.Length+1)
            [void]$sites.Add([pscustomobject]@{
                key=$t.Groups[1].Value; kw=$kw; file=$rel
                line=($clean.Substring(0,$m.Index) -split "`n").Count
                # a scripted_gui is_valid, or a scripted_trigger that one may call,
                # is the path where the token does not expand.
                tipPath = ($rel -like 'common\scripted_guis\*' -or $rel -like 'common\scripted_triggers\*')
            })
        }
    }
}

# ---- 2. loc tables: the mod's own languages, with vanilla as fallback for borrowed keys ----
$modLangs = @{}
foreach ($d in (Get-ChildItem (Join-Path $ModRoot 'localization') -Directory)) { $modLangs[$d.Name] = Read-LocDir $d.FullName }
$vanLangs = @{}
foreach ($lang in $modLangs.Keys) {
    $vd = Join-Path $VanillaRoot "localization\$lang"
    $vanLangs[$lang] = Read-LocDir $vd
}

# ---- 3. classify ----
$rxTok = [regex]'\[([^\]]*)\]'
$fail = New-Object System.Collections.ArrayList
$note = New-Object System.Collections.ArrayList
$miss = New-Object System.Collections.ArrayList
foreach ($g in ($sites | Group-Object key | Sort-Object Name)) {
    $key   = $g.Name
    $onTip = @($g.Group | Where-Object { $_.tipPath }).Count -gt 0
    $usedAt = (($g.Group | ForEach-Object { "$($_.file):$($_.line)" }) -join ', ')
    foreach ($lang in ($modLangs.Keys | Sort-Object)) {
        $src = 'mod'; $e = $null
        if ($modLangs[$lang].ContainsKey($key))      { $e = $modLangs[$lang][$key] }
        elseif ($vanLangs[$lang].ContainsKey($key))  { $e = $vanLangs[$lang][$key]; $src = 'vanilla' }
        if (-not $e) { [void]$miss.Add("$key ($lang) - used at $usedAt"); continue }
        $toks = @($rxTok.Matches($e.text) | ForEach-Object { $_.Groups[1].Value })
        if (-not $toks.Count) { continue }
        $row = [pscustomobject]@{ key=$key; lang=$lang; src=$src; locline=$e.line
                                  tokens=($toks -join ' ; '); usedAt=$usedAt }
        if ($onTip) { [void]$fail.Add($row) } else { [void]$note.Add($row) }
    }
}

Write-Host ("keys checked : {0}   languages : {1}" -f (@($sites|Group-Object key)).Count, (($modLangs.Keys|Sort-Object) -join ', '))
Write-Host ("FAIL  (token, on the scripted_gui BuildTooltip path) : {0}" -f $fail.Count)
Write-Host ("NOTE  (token, interaction/decision path - allowed)   : {0}" -f $note.Count)
Write-Host ("UNDECLARED in mod and in vanilla                     : {0}" -f $miss.Count)
if ($miss.Count) { Write-Host ""; Write-Host "UNDECLARED (prints a raw key for a different reason):"
                   $miss | Sort-Object -Unique | ForEach-Object { Write-Host "  $_" } }
if ($note.Count) { Write-Host ""; Write-Host "NOTE - token present but the render path expands it:"
                   foreach ($n in ($note|Sort-Object key,lang)) { Write-Host ("  {0,-32} {1,-8} [{2}] {3}" -f $n.key,$n.lang,$n.src,$n.tokens) } }
if ($fail.Count) {
    Write-Host ""
    foreach ($b in ($fail | Sort-Object key, lang)) {
        Write-Host ("  {0,-30} {1,-8} yml L{2,-5} tokens: {3}" -f $b.key,$b.lang,$b.locline,$b.tokens)
        Write-Host ("  {0,-30} used at {1}" -f '', $b.usedAt)
    }
    Write-Host ""
    Write-Host "FAIL: strip every [..] token from the strings above. Keep the concept's own word"
    Write-Host "      as plain text. Nested `$vanilla_key`$ and #high ...#! may stay."
    exit 1
}
Write-Host ""; Write-Host "PASS: no BuildTooltip-path custom_description string carries a [..] token."
exit 0
