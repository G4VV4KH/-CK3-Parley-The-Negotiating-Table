# =============================================================================
# tnt_incode_citation_check.ps1 - THE EIGHTH TOOL, added 2026-08-24.
#
# WHAT IT CHECKS, AND WHY IT IS NOT tnt_citation_check.ps1 AGAIN.
# tnt_citation_check.ps1 reads CLAUDE.md AND NOTHING ELSE, by design, and that
# design was never wrong - it was just half the surface. Every file:line
# citation written INSIDE a shipped script or .gui file had NO automated guard
# at all, and the cost of that is measured rather than feared:
#
#   * 2026-08-24, a full re-measure of the 69 in-code citations pointing into
#     common\script_values\tnt_50_values.txt found exactly ONE that resolved
#     cleanly. The rest were stale by -689 to +2142 lines, IN BOTH DIRECTIONS,
#     so no single offset could ever have repaired them.
#   * The same day, three separate in-code comments were found citing ONE
#     retired, commented-out effect at THREE MUTUALLY INCONSISTENT ranges, one
#     of them minted that very round.
#   * This was the FIFTH citation-rot repair round of a single session.
#
# The project's own doctrine says what to do about that: a class of defect that
# has shipped four times needs a machine check rather than more care.
#
# WHY A ROTTED CITATION IS WORSE THAN A MISSING ONE. It still lands in the right
# FILE, usually inside a comment tens or hundreds of lines from the thing the
# prose names. It therefore reads as plausible, and a session that follows it
# spends its bearings before it notices. The worst measured case in this project
# was an OPEN defect anchored 545 lines away, inside a different archetype.
#
# =============================================================================
# THE THREE VERDICT CLASSES, and only the first two are failures
# =============================================================================
#   FAIL  DEAD    - the cited file is not in any of the three mod trees, or the
#                   cited line is past its end. Nothing to argue about.
#   FAIL  OFF     - the citing comment NAMES a top-level definition that exists
#                   in the cited file, and the cited line is NOT inside that
#                   definition's span (nor within 3 lines above its header).
#                   This is the rot class.
#   NOTE  LOOSE   - no definition of the cited file is named within 3 lines of
#                   the citation, so there is nothing to anchor against. These
#                   are counted and printed as a census, never failed: plenty of
#                   honest citations point at a comment, a tombstone or a block
#                   of prose that carries no definition name at all.
#
# WHY "INSIDE THE SPAN" AND NOT "WITHIN 3 LINES OF THE HEADER". A citation very
# often names a ROW inside a body on purpose - "the base rate the row
# tnt_gold_per_point_value opens with", "the min = 0 clamp of
# tnt_val_alliance_p_value". Demanding the header would fail those honest
# pointers and the tool would be ignored within a round, which is the failure
# mode this project has already recorded for a gate that is always red.
# The 3-line grace ABOVE a header exists because a definition's own comment
# block is the thing prose usually means when it cites a value.
#
# WHAT IS DELIBERATELY OUT OF SCOPE
#   * VANILLA citations (GAME\..., <vanilla>\..., D:\SteamLibrary\...). House
#     law 1 covers those by hand, and the vanilla tree is not ours to police.
#   * CLAUDE.md - tnt_citation_check.ps1 owns it. Running both is the point.
#   * .yml targets - a localization key cannot rot the way a line number does,
#     and the loc files grow every round; cite keys by NAME, never by line.
#     A .yml:N citation is reported as LOOSE so it is visible without failing.
#
# ENCODING: this file is ASCII-only, like every .ps1 in this folder - a
# typographic apostrophe acts as a string delimiter in PowerShell 5.1 and has
# broken a tool in this project before.
# =============================================================================

param(
    [string]$ModRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
)

$ErrorActionPreference = 'Stop'

$TREES = @(
    @{ Tag = 'CORE'; Root = (Join-Path $ModRoot 'parley') },
    @{ Tag = 'MCA';  Root = (Join-Path $ModRoot 'marriage_calc_assistant') },
    @{ Tag = 'FORK'; Root = (Join-Path $ModRoot 'agot_marriage_calc_assistant') }
)

# Tolerate being pointed straight at the parley folder instead of the mod root.
if (-not (Test-Path $TREES[0].Root)) {
    $parent = Split-Path -Parent $ModRoot
    $TREES = @(
        @{ Tag = 'CORE'; Root = $ModRoot },
        @{ Tag = 'MCA';  Root = (Join-Path $parent 'marriage_calc_assistant') },
        @{ Tag = 'FORK'; Root = (Join-Path $parent 'agot_marriage_calc_assistant') }
    )
}

$SCAN_DIRS = @('common', 'events', 'gui', 'data_binding')
$SCAN_EXT  = @('.txt', '.gui')

Write-Host "tnt_incode_citation_check - in-code file:line citations across the family"
Write-Host "================================================================"

# -----------------------------------------------------------------------------
# PASS 1 - index every shipped file by basename, and every top-level definition
#          in it by name, with the span its braces actually cover.
# -----------------------------------------------------------------------------
$fileByName = @{}   # basename -> full path (first tree wins; names are unique)
$defsByFile = @{}   # full path -> @{ name -> @{ Start; End } }
$linesByFile = @{}  # full path -> line count

function Strip-Comment([string]$line) {
    $i = $line.IndexOf('#')
    if ($i -lt 0) { return $line }
    return $line.Substring(0, $i)
}

foreach ($t in $TREES) {
    if (-not (Test-Path $t.Root)) { continue }
    foreach ($d in $SCAN_DIRS) {
        $dir = Join-Path $t.Root $d
        if (-not (Test-Path $dir)) { continue }
        Get-ChildItem $dir -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
            if ($SCAN_EXT -notcontains $_.Extension.ToLower()) { return }
            $bn = $_.Name
            if (-not $fileByName.ContainsKey($bn)) { $fileByName[$bn] = $_.FullName }
            if ($defsByFile.ContainsKey($_.FullName)) { return }

            $arr = [System.IO.File]::ReadAllLines($_.FullName, [System.Text.Encoding]::UTF8)
            $linesByFile[$_.FullName] = $arr.Count
            $map = @{}
            $depth = 0; $curName = $null; $curStart = 0
            for ($i = 0; $i -lt $arr.Count; $i++) {
                $code = Strip-Comment $arr[$i]
                if ($depth -eq 0 -and $code -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{') {
                    $curName = $Matches[1]; $curStart = $i + 1
                }
                $depth += ([regex]::Matches($code, '\{')).Count
                $depth -= ([regex]::Matches($code, '\}')).Count
                if ($depth -le 0) {
                    $depth = 0
                    if ($curName) {
                        if (-not $map.ContainsKey($curName)) {
                            $map[$curName] = @{ Start = $curStart; End = $i + 1 }
                        }
                        $curName = $null
                    }
                }
            }
            $defsByFile[$_.FullName] = $map
        }
    }
}
Write-Host ("  indexed {0} shipped file name(s); {1} carry parsed definitions" -f $fileByName.Count, $defsByFile.Count)

# -----------------------------------------------------------------------------
# PASS 2 - walk every citation and classify it.
# -----------------------------------------------------------------------------
# A citation preceded by a vanilla path marker on the same line is skipped.
$VANILLA_RX = '(?i)(GAME\\|<vanilla>|SteamLibrary|steamapps|\\game\\)'
# The optional third group is a RANGE end. A citation may legitimately span two
# adjacent definitions on purpose - tnt_power_ratio_value and its _inv twin are
# cited as one :372-385 block - so a range is judged by INTERVAL OVERLAP with the
# named region, not by its first number alone. Without that, every deliberate
# two-construct range reads as rot.
$CITE_RX    = '\b(tnt_[A-Za-z0-9_]+\.(?:txt|gui|yml))\s*:\s*(\d+)(?:\s*-\s*(\d+))?'

$fails = 0; $loose = 0; $ok = 0; $total = 0
$looseByTarget = @{}

foreach ($t in $TREES) {
    if (-not (Test-Path $t.Root)) { continue }
    foreach ($d in $SCAN_DIRS) {
        $dir = Join-Path $t.Root $d
        if (-not (Test-Path $dir)) { continue }
        Get-ChildItem $dir -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
            if ($SCAN_EXT -notcontains $_.Extension.ToLower()) { return }
            $rel = $_.FullName.Replace($t.Root + '\', '')
            $arr = [System.IO.File]::ReadAllLines($_.FullName, [System.Text.Encoding]::UTF8)

            for ($i = 0; $i -lt $arr.Count; $i++) {
                $line = $arr[$i]
                if ($line -match $VANILLA_RX) { continue }
                foreach ($m in [regex]::Matches($line, $CITE_RX)) {
                    $tgtName = $m.Groups[1].Value
                    $n       = [int]$m.Groups[2].Value
                    $nEnd    = $n
                    if ($m.Groups[3].Success) {
                        $e2 = [int]$m.Groups[3].Value
                        if ($e2 -gt $n) { $nEnd = $e2 }
                    }
                    $total++

                    # .yml FIRST, before the existence test: localization is not in
                    # $SCAN_DIRS, so a .yml target would otherwise be reported DEAD
                    # for the wrong reason. Cite loc keys by NAME, never by line -
                    # those files grow every round and the number cannot hold.
                    if ($tgtName.ToLower().EndsWith('.yml')) {
                        $loose++
                        if (-not $looseByTarget.ContainsKey($tgtName)) { $looseByTarget[$tgtName] = 0 }
                        $looseByTarget[$tgtName]++
                        continue
                    }

                    if (-not $fileByName.ContainsKey($tgtName)) {
                        Write-Host ("  FAIL DEAD   {0} {1}:{2} -> {3}:{4} - no such file in any mod tree" -f $t.Tag, $rel, ($i + 1), $tgtName, $n)
                        $fails++
                        continue
                    }
                    $tgtPath = $fileByName[$tgtName]

                    if ($linesByFile.ContainsKey($tgtPath) -and $n -gt $linesByFile[$tgtPath]) {
                        Write-Host ("  FAIL DEAD   {0} {1}:{2} -> {3}:{4} - past end of file ({5} lines)" -f $t.Tag, $rel, ($i + 1), $tgtName, $n, $linesByFile[$tgtPath])
                        $fails++
                        continue
                    }

                    # =========================================================
                    # PAIRING A NUMBER TO A NAME - the precision that decides
                    # whether this tool is read or ignored.
                    # =========================================================
                    # The first cut of this check took a +-3 LINE window and
                    # asked whether ANY definition named anywhere in it contained
                    # the number. That is too loose, and it produced a specific,
                    # repeatable false positive: a comment sentence very often
                    # carries SEVERAL names and SEVERAL numbers -
                    #   "tnt_val_gold_p_value (:592) and tnt_gold_per_point_value
                    #    (:343)"
                    # - and the loose rule happily paired :592 with
                    # tnt_gold_per_point_value and called a correct citation rot.
                    # On the first repaired tree that was 20 of 23 reports.
                    #
                    # THE RULE THAT SURVIVES: pair a number ONLY with a name on
                    # its OWN LINE, and among those with the NEAREST name to its
                    # LEFT - which is how these comments are actually written,
                    # name first and number in parentheses after it. If no name
                    # sits on the line, the citation is LOOSE: unanchorable, not
                    # wrong. A checker that cannot tell which name a number
                    # belongs to must say so rather than guess.
                    $map = $defsByFile[$tgtPath]
                    $named = @()
                    $bestPos = -1
                    foreach ($k in $map.Keys) {
                        # 8 characters keeps generic words (value, add, limit) out.
                        if ($k.Length -lt 8) { continue }
                        $km = [regex]::Match($line, '\b' + [regex]::Escape($k) + '\b')
                        while ($km.Success) {
                            if ($km.Index -lt $m.Index -and $km.Index -gt $bestPos) {
                                $bestPos = $km.Index; $named = @($k)
                            } elseif ($km.Index -lt $m.Index -and $km.Index -eq $bestPos) {
                                $named = @($named) + @($k)
                            }
                            $km = $km.NextMatch()
                        }
                    }
                    $named = @($named)

                    if ($named.Count -eq 0) {
                        $loose++
                        if (-not $looseByTarget.ContainsKey($tgtName)) { $looseByTarget[$tgtName] = 0 }
                        $looseByTarget[$tgtName]++
                        continue
                    }

                    # THE ACCEPTED WINDOW IS THE DEFINITION'S WHOLE REGION, header
                    # comment included: from one line past the END of the previous
                    # definition down to this one's closing brace. A citation very
                    # often means the E-block comment that introduces a value, which
                    # can sit twenty lines above the `name = {` line, and failing
                    # those would make this tool noise. What it still catches is the
                    # rot that matters: a number landing inside a DIFFERENT
                    # definition's region, or in no region at all.
                    $hit = $false
                    foreach ($k in $named) {
                        $s = [int]$map[$k].Start; $e = [int]$map[$k].End
                        $regionStart = 1
                        foreach ($k2 in $map.Keys) {
                            $e2 = [int]$map[$k2].End
                            if ($e2 -lt $s -and ($e2 + 1) -gt $regionStart) { $regionStart = $e2 + 1 }
                        }
                        # Interval overlap, so a deliberate two-construct range passes.
                        if ($n -le $e -and $nEnd -ge $regionStart) { $hit = $true; break }
                    }
                    if ($hit) { $ok++; continue }

                    $srt = @($named | Sort-Object { [Math]::Abs([int]$map[$_].Start - $n) })
                    $near = [string]$srt[0]
                    Write-Host ("  FAIL OFF    {0} {1}:{2} -> {3}:{4} - names {5}, which spans :{6}-{7}" -f $t.Tag, $rel, ($i + 1), $tgtName, $n, $near, $map[$near].Start, $map[$near].End)
                    $fails++
                }
            }
        }
    }
}

Write-Host "================================================================"
Write-Host ("  {0} in-code citation(s) into mod files: {1} anchored, {2} LOOSE (no definition named nearby), {3} FAIL" -f $total, $ok, $loose, $fails)
if ($looseByTarget.Count -gt 0) {
    Write-Host "  LOOSE by target (census only, never a failure):"
    foreach ($k in ($looseByTarget.Keys | Sort-Object { -$looseByTarget[$_] })) {
        Write-Host ("    {0,-40} {1}" -f $k, $looseByTarget[$k])
    }
}
Write-Host "================================================================"
if ($fails -eq 0) {
    Write-Host "PASS - every anchored in-code citation resolves to the construct its prose names."
    exit 0
}
Write-Host ("FAIL - {0} rotted in-code citation(s). Re-anchor them AGAINST THE REAL CONSTRUCT." -f $fails)
Write-Host "       Never repair one by adding a delta: a wrong number stamped as freshly"
Write-Host "       checked is the worse failure, and this file's header records why."
exit 1
