# =============================================================================
# tnt_frozen_sync_check.ps1       MCA'S ONE FROZEN GUI COPY + INHERITANCE SEAM
#
# MCA 3.1 uses the reviewed CK3 1.20 GUI contract. It copies no marriage interaction and does not
# shadow the global character-list row. It ships ONE upstream body:
#
#   MCA gui\interaction_marriage.gui
#       = the reviewed vanilla baseline plus the exact approved score-sort patch
#         and the marriage-local neutral left spouse label.
#         Three row instances inherit tnt_ma_widget_character_list_item.
#
# The derived row inherits the active playset's widget_character_list_item and
# overrides `character_relation`, retaining the native relation text. Therefore
# this tool has two jobs:
#
#   1. Pin the reviewed vanilla baseline and reviewed functional patch, rebuild
#      the expected MCA file, and compare it exactly to the supplied MCA file.
#      Both upstream drift and an unreviewed MCA edit require a fresh patch review.
#   2. Require both vanilla and AGOT to keep one base row type with the
#      `character_relation` and untouched `extra_skills` blocks, native relation
#      text, and CharacterListItem character context.
#      Also require AGOT not to acquire its own interaction_marriage.gui;
#      that would create a new compatibility race which needs a fresh ruling.
#
# The old V23 architecture is forbidden: no 00_* global-row shadow, no frozen
# common/character_interactions copy, and no FROZEN/TNT-MA fence markers.
#
# THIS TOOL IS READ-ONLY. It never writes a file.
# Exit 0 in sync / 1 drift or structural failure / 2 bad arguments.
# =============================================================================
param(
    [string]$McaRoot     = '',
    [Alias('ForkRoot')]
    [string]$AdapterRoot    = '',
    [string]$VanillaRoot = 'D:\SteamLibrary\steamapps\common\Crusader Kings III\game',
    [string]$AgotRoot    = 'D:\SteamLibrary\steamapps\workshop\content\1158310\2962333032'
)

$coreRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
if ($McaRoot -eq '')  { $McaRoot  = Join-Path (Split-Path -Parent $coreRoot) 'marriage_calc_assistant' }
if ($AdapterRoot -eq '') { $AdapterRoot = Join-Path (Split-Path -Parent $coreRoot) 'agot_marriage_calc_assistant' }
$McaRoot     = $McaRoot.TrimEnd('\')
$AdapterRoot    = $AdapterRoot.TrimEnd('\')
$VanillaRoot = $VanillaRoot.TrimEnd('\')
$AgotRoot    = $AgotRoot.TrimEnd('\')

$mcaCopy    = Join-Path $McaRoot 'gui\interaction_marriage.gui'
$mcaRow     = Join-Path $McaRoot 'gui\tnt_ma_character_list_item.gui'
$vanillaGui = Join-Path $VanillaRoot 'gui\interaction_marriage.gui'
$vanillaRow = Join-Path $VanillaRoot 'gui\shared\lists.gui'
$agotRow    = Join-Path $AgotRoot 'gui\shared\lists.gui'

foreach ($required in @(
    @{ Label = 'MCA marriage GUI';     Path = $mcaCopy },
    @{ Label = 'MCA derived row';      Path = $mcaRow },
    @{ Label = 'vanilla marriage GUI'; Path = $vanillaGui },
    @{ Label = 'vanilla base row';     Path = $vanillaRow },
    @{ Label = 'AGOT base row';        Path = $agotRow }
)) {
    if (-not (Test-Path -LiteralPath $required.Path)) {
        Write-Host ("BAD {0}: {1}" -f $required.Label, $required.Path)
        exit 2
    }
}
if (-not (Test-Path -LiteralPath $AdapterRoot)) { Write-Host "BAD AdapterRoot: $AdapterRoot"; exit 2 }

# Quoted strings are removed before the comment cut so '#' and braces inside
# GUI strings do not alter code parsing.
function Strip-Code([string]$line) {
    $code = [regex]::Replace($line, '"[^"]*"', '""')
    $i = $code.IndexOf('#')
    if ($i -ge 0) { $code = $code.Substring(0, $i) }
    return $code
}

# Comment cut that preserves quoted GUI data functions and block names.
function Strip-CommentKeepQuotes([string]$line) {
    $inQuote = $false
    for ($i = 0; $i -lt $line.Length; $i++) {
        $ch = $line[$i]
        if ($ch -eq '"') { $inQuote = -not $inQuote }
        elseif ($ch -eq '#' -and -not $inQuote) { return $line.Substring(0, $i) }
    }
    return $line
}

# Locate every `type <name> = <parent> {` declaration and extract the sole
# body's brace-matched lines. Count remains authoritative when it is not one.
function Get-TypeBodyInfo([string[]]$lines, [string]$typeName) {
    $starts = @()
    $rx = '^\s*type\s+' + [regex]::Escape($typeName) + '\s*=\s*([A-Za-z0-9_]+)\s*\{'
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $code = Strip-Code $lines[$i]
        if ($code -match $rx) {
            $starts += [pscustomobject]@{ Index = $i; Parent = $Matches[1] }
        }
    }
    if ($starts.Count -ne 1) {
        return [pscustomobject]@{ Count = $starts.Count; Parent = ''; Start = 0; End = 0; Body = @() }
    }

    $start = $starts[0].Index
    $depth = 0
    $body = @()
    $end = -1
    for ($i = $start; $i -lt $lines.Count; $i++) {
        $body += $lines[$i]
        $code = Strip-Code $lines[$i]
        $depth += ([regex]::Matches($code, '\{')).Count
        $depth -= ([regex]::Matches($code, '\}')).Count
        if ($depth -le 0) { $end = $i; break }
    }
    if ($end -lt 0) {
        return [pscustomobject]@{ Count = 1; Parent = $starts[0].Parent; Start = ($start + 1); End = 0; Body = @() }
    }
    return [pscustomobject]@{
        Count = 1
        Parent = $starts[0].Parent
        Start = ($start + 1)
        End = ($end + 1)
        Body = $body
    }
}

function First-LineDifference([string[]]$a, [string[]]$b) {
    $n = [Math]::Min($a.Count, $b.Count)
    for ($i = 0; $i -lt $n; $i++) {
        if ($a[$i] -cne $b[$i]) { return ($i + 1) }
    }
    if ($a.Count -ne $b.Count) { return ($n + 1) }
    return 0
}

$fails = 0
Write-Host "tnt_frozen_sync_check - MCA's one frozen GUI copy and inherited row seam"
Write-Host ("  MCA     : {0}" -f $McaRoot)
Write-Host ("  ADAPTER : {0}" -f $AdapterRoot)
Write-Host ("  VANILLA : {0}" -f $VanillaRoot)
Write-Host ("  AGOT    : {0}" -f $AgotRoot)
Write-Host ""

# =============================================================================
# CHECK A - exact reviewed vanilla baseline plus functional MCA patch
# =============================================================================
Write-Host "CHECK A - approved functional patch rebuilds the exact MCA marriage GUI"
$helperPath = Join-Path $PSScriptRoot 'tnt_mca_frozen_contract.ps1'
if (-not (Test-Path -LiteralPath $helperPath)) { Write-Host "BAD frozen helper: $helperPath"; exit 2 }
. $helperPath
$measure = Measure-McaMarriageCopy -copyPath $mcaCopy -upPath $vanillaGui
$upLines = [System.IO.File]::ReadAllLines($vanillaGui)
if ($measure.Passed) {
    Write-Host ("  IN-SYNC  approved patch: vanilla {0} lines -> MCA {1} lines; derived row sites {2}" -f $measure.UpCount, $measure.CopyCount, ($measure.Sites -join ', '))
    Write-Host ("  PASS  reviewed baseline {0}; functional patch {1}" -f $measure.UpstreamHash, $measure.PatchHash)
}
else {
    foreach ($errorText in $measure.Errors) { Write-Host ("  FAIL  {0}" -f $errorText); $fails++ }
}
Write-Host ""

# =============================================================================
# CHECK B - vanilla and AGOT still expose the inherited extension point
# =============================================================================
Write-Host "CHECK B - live vanilla and AGOT base rows preserve relation and skill seams"
foreach ($upstream in @(
    @{ Tag = 'VANILLA'; Path = $vanillaRow },
    @{ Tag = 'AGOT';    Path = $agotRow }
)) {
    $lines = [System.IO.File]::ReadAllLines($upstream.Path)
    $info = Get-TypeBodyInfo $lines 'widget_character_list_item'
    if ($info.Count -ne 1 -or $info.Body.Count -eq 0) {
        Write-Host ("  FAIL  {0}: expected one balanced widget_character_list_item type, found {1}" -f $upstream.Tag, $info.Count)
        $fails++
        continue
    }
    if ($info.Parent -cne 'widget') {
        Write-Host ("  FAIL  {0}: base row parent is {1}, expected widget" -f $upstream.Tag, $info.Parent)
        $fails++
    }

    $extra = 0
    $relation = 0
    $relationText = 0
    $characterContext = 0
    foreach ($line in $info.Body) {
        $active = Strip-CommentKeepQuotes $line
        if ($active -match '^\s*block\s+"extra_skills"\s*\{\s*\}\s*$') { $extra++ }
        if ($active -match '^\s*block\s+"character_relation"\s*(\{\s*)?$') { $relation++ }
        if ($active -match 'Character\.GetRelationToString\(\s*GetPlayer\s*\)') { $relationText++ }
        if ($active -match 'CharacterListItem\.GetCharacter') { $characterContext++ }
    }
    if ($extra -ne 1) {
        Write-Host ("  FAIL  {0}: extra_skills empty block count {1}, expected 1" -f $upstream.Tag, $extra)
        $fails++
    }
    elseif ($relation -ne 1 -or $relationText -lt 1) {
        Write-Host ("  FAIL  {0}: character_relation block/text counts {1}/{2}; expected 1/at least 1" -f $upstream.Tag, $relation, $relationText)
        $fails++
    }
    elseif ($characterContext -lt 1) {
        Write-Host ("  FAIL  {0}: base row lost CharacterListItem.GetCharacter context" -f $upstream.Tag)
        $fails++
    }
    else {
        Write-Host ("  PASS  {0}: type lines {1}-{2}, relation and extra_skills seams, native relation and character context present" -f $upstream.Tag, $info.Start, $info.End)
    }
}

$derivedInfo = Get-TypeBodyInfo ([System.IO.File]::ReadAllLines($mcaRow)) 'tnt_ma_widget_character_list_item'
if ($derivedInfo.Count -ne 1 -or $derivedInfo.Parent -cne 'widget_character_list_item' -or $derivedInfo.Body.Count -eq 0) {
    Write-Host "  FAIL  MCA must declare exactly one balanced derived row inheriting widget_character_list_item"
    $fails++
}
else {
    $derivedCode = (($derivedInfo.Body | ForEach-Object { Strip-CommentKeepQuotes $_ }) -join "`n")
    $derivedCanonical = [regex]::Replace($derivedCode, '\s+', '')
    $relationOverrides = [regex]::Matches($derivedCode, '\bblockoverride\s+"character_relation"\s*\{').Count
    $skillOverrides = [regex]::Matches($derivedCode, '\bblockoverride\s+"extra_skills"\s*\{').Count
    $nativeRelationText = [regex]::Matches($derivedCode, 'Character\.GetRelationToString\(\s*GetPlayer\s*\)').Count
    $nativeRelationTooltip = [regex]::Matches($derivedCode, 'tooltip\s*=\s*"EXTENDED_RELATIONS_TOOLTIP"').Count
    $carrierCount = [regex]::Matches($derivedCanonical, [regex]::Escape('name="tnt_ma_grade_carrier"size={12626}')).Count
    $ownerCount = [regex]::Matches($derivedCanonical, [regex]::Escape('size={11226}')).Count
    $ownerPositionCount = [regex]::Matches($derivedCanonical, [regex]::Escape('position={60}')).Count
    if ($relationOverrides -ne 1 -or $skillOverrides -ne 0 -or $nativeRelationText -ne 1 -or $nativeRelationTooltip -ne 1 -or $carrierCount -ne 1 -or $ownerCount -ne 4 -or $ownerPositionCount -ne 4) {
        Write-Host ("  FAIL  MCA inherited layout relation/skills/nativeText/nativeTooltip/carrier/owners/positions={0}/{1}/{2}/{3}/{4}/{5}/{6}, expected 1/0/1/1/1/4/4" -f $relationOverrides, $skillOverrides, $nativeRelationText, $nativeRelationTooltip, $carrierCount, $ownerCount, $ownerPositionCount)
        $fails++
    }
    else { Write-Host "  PASS  one derived row: relation preserved, skills untouched, 126x26 carrier with four 112x26 owners at 6,0" }
}

$otherItems = 0
foreach ($line in $upLines) {
    $otherItems += ([regex]::Matches((Strip-CommentKeepQuotes $line), 'CharacterListItem\.GetOtherCharacterItems')).Count
}
if ($otherItems -lt 1) {
    Write-Host "  FAIL  vanilla marriage GUI no longer exposes CharacterListItem.GetOtherCharacterItems"
    $fails++
}
else { Write-Host ("  PASS  vanilla marriage GUI carries GetOtherCharacterItems ({0} site(s))" -f $otherItems) }

$agotMarriage = Join-Path $AgotRoot 'gui\interaction_marriage.gui'
if (Test-Path -LiteralPath $agotMarriage) {
    Write-Host ("  FAIL  AGOT now ships {0}; MCA's vanilla-based frozen copy needs a fresh compatibility ruling" -f $agotMarriage)
    $fails++
}
else { Write-Host "  PASS  AGOT does not override gui\interaction_marriage.gui" }
Write-Host ""

# =============================================================================
# CHECK C - the retired V23 copy architecture must not return
# =============================================================================
Write-Host "CHECK C - no retired global-row/interactions twins or fence markers"
$forbiddenCategories = @('gui', 'common\character_interactions', 'common\scripted_guis', 'common\scripted_effects', 'common\on_action', 'common\decisions')
foreach ($category in $forbiddenCategories) {
    $path = Join-Path $AdapterRoot $category
    if ((Test-Path -LiteralPath $path) -and @(Get-ChildItem -LiteralPath $path -Recurse -File).Count -gt 0) {
        Write-Host ("  FAIL  AGOT adapter carries forbidden runtime category: {0}" -f $category)
        $fails++
    }
}
foreach ($file in (Get-ChildItem -LiteralPath (Join-Path $McaRoot 'gui') -Recurse -File -Filter '*.gui')) {
    foreach ($line in [System.IO.File]::ReadAllLines($file.FullName)) {
        if ((Strip-Code $line) -match '^\s*type\s+widget_character_list_item\s*=') {
            Write-Host ("  FAIL  MCA shadows the global base row in {0}" -f $file.FullName)
            $fails++
        }
    }
}
$legacyPaths = @(
    @{ Tag = 'MCA'; Root = $McaRoot; Rel = 'gui\00_tnt_ma_charlist_row.gui' },
    @{ Tag = 'MCA'; Root = $McaRoot; Rel = 'common\character_interactions\tnt_ma_20_vanilla_marriage.txt' },
    @{ Tag = 'ADAPTER'; Root = $AdapterRoot; Rel = 'gui\00_agot_ma_charlist_row.gui' },
    @{ Tag = 'ADAPTER'; Root = $AdapterRoot; Rel = 'common\character_interactions\tnt_ma_20_vanilla_marriage_agot.txt' }
)
$legacyFound = 0
foreach ($entry in $legacyPaths) {
    $p = Join-Path $entry.Root $entry.Rel
    if (Test-Path -LiteralPath $p) {
        Write-Host ("  FAIL  {0} retired file returned: {1}" -f $entry.Tag, $entry.Rel)
        $legacyFound++
    }
}
$fails += $legacyFound

$markerHits = 0
foreach ($tree in @(
    @{ Tag = 'MCA'; Root = $McaRoot },
    @{ Tag = 'ADAPTER'; Root = $AdapterRoot }
)) {
    foreach ($file in (Get-ChildItem -LiteralPath $tree.Root -Recurse -File)) {
        if ($file.Extension.ToLower() -notin @('.txt', '.gui')) { continue }
        $ln = 0
        foreach ($line in [System.IO.File]::ReadAllLines($file.FullName)) {
            $ln++
            if ($line -match 'FROZEN COPY BELOW THIS LINE|TNT-MA ADDITION (BEGIN|END)') {
                Write-Host ("  FAIL  {0} legacy marker at {1}:{2}" -f $tree.Tag, $file.FullName.Substring($tree.Root.Length + 1), $ln)
                $markerHits++
            }
        }
    }
}
$fails += $markerHits
if ($markerHits -eq 0 -and $legacyFound -eq 0) {
    Write-Host "  PASS  retired V23 copy architecture absent"
}
Write-Host ""

Write-Host "================================================================"
if ($fails -eq 0) {
    Write-Host "PASS - the approved MCA patch exactly matches its vanilla baseline; both inherited row seams are live."
    exit 0
}
Write-Host ("FAIL - {0} frozen-copy/inheritance fault(s). Rebase the measured MCA patch; do not hand-merge upstream drift." -f $fails)
exit 1
