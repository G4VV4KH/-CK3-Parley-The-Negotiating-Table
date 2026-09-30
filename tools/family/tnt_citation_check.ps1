# =====================================================================================
# tnt_citation_check.ps1 - THE CHECK THAT CATCHES A ROTTED file:line IN CLAUDE.md
#
# WHY THIS EXISTS. CLAUDE.md is the authoritative document and its whole value is that
# a session can be sent straight to a line. On 2026-08-19 a read-only audit of it found
# NINETEEN rotted citations in that one file (and three more in in-code comments), and
# fixing them surfaced a twentieth - tnt_40_triggers.txt:295 for a row that is at :294.
# None of them was a typo; they were the two expensive shapes:
#
#   D3/D5  THE ANCHOR DRIFTED. The named thing moved and the number stayed. Every one
#          of them still landed inside the right FILE, usually inside a comment 3 to 900
#          lines away, so it read as plausible and cost a session its bearings.
#          Worst measured case: an OPEN defect the doc asks a future session to fix was
#          anchored 545 lines away, inside a different archetype.
#   D6     THE NUMBER WAS PRE-FIX. The fix shipped, the line moved, nobody re-measured.
#
# Neither shape is visible to any other tool in this folder, and neither leaves a trace
# in error.log, because a wrong line number is not a script defect - it is a defect in
# the map. This script is the map's checker.
#
# WHAT IT ASSERTS, three things, in this order:
#   1. THE FILE EXISTS. Every citation of the form <tnt_file>.txt:<n> / .gui:<n> /
#      .yml:<n> resolves to a real shipped file. If the citation carries a folder
#      prefix, that prefix must be where the file actually lives.
#   2. THE LINE EXISTS. 1 <= start <= end <= the file's line count.
#   3. THE ANCHOR STILL NAMES THE THING. Where the prose around the citation names a
#      tnt_ identifier or quotes a line of script, at least one of those needles must
#      appear within 3 lines of the cited line (for a range, within 3 lines of either
#      end). This is the row that catches drift: `tnt_stress_deal_effect`
#      (`tnt_3c_stress.txt:98`) passes rows 1 and 2 and fails row 3, which is exactly
#      the defect - the effect is at :130 and :98 is a line of the file's header prose.
#
# HOW STRONG ROW 3 IS, STATED HONESTLY, because a tool that overclaims gets ignored.
# It is a heuristic and it is deliberately generous: the needle set is everything code-
# shaped on the citation's own line AND on the line above it, and ANY single match
# passes. That generosity is what keeps it free of false alarms on prose like "X is slot
# 4 of Y (Y_file:line_of_X)", where the citation belongs to the identifier that is NOT
# nearest to it - eight correct citations failed a stricter draft of this row.
#
# MEASURED 2026-08-19 against a throwaway fixture holding the pre-fix lines verbatim:
# it FAILS 12 of the 15 rotted citations the audit found. The three it lets through, and
# why, because each is a real blind spot and none of them is fixable by tightening:
#   * tnt_32_apply.txt:1127 - line 1128 is a COMMENT quoting `take_baronies = no`
#     verbatim, so the needle was satisfied by prose ABOUT the code instead of the code.
#     No text search can tell those two apart.
#   * tnt_34_marriage.txt:209-282 - the stale RANGE still overlaps the real body
#     (233-312), so the named effect is inside the window. A wide range is forgiving.
#   * `:3246-3253` - a bare ref whose file was last named four lines earlier, so it is
#     counted as unanchored and skipped (see the inheritance rule below).
# It is a ratchet, not a proof. A citation whose two doc lines name nothing code-shaped
# is checked for rows 1 and 2 only, and that is the honest limit of the thing.
#
# BARE CONTINUATION REFS (`:270`, `:1511`) inherit the last file named before them.
#   * Same doc line  -> the inheritance is certain, so a fault there is a FAIL.
#   * Line above     -> the inheritance is a guess, so a fault there is a NOTE. Real
#                       example of why the guess is not trusted: the PRICE CENSUS used
#                       to write `tnt_types.gui:1906` on one line and `:1702`/`:1706` on
#                       the next, and those two belonged to tnt_50_values.txt, named two
#                       lines earlier. THE FIX FOR A NOTE IS TO NAME THE FILE - that is
#                       why the shipped document now spells both of those out.
#   * Neither        -> counted as unanchored and not checked.
#
# NOT CHECKED, on purpose: citations into the vanilla tree or any other non-tnt_ file
# (this script has no read-only truth to check them against - house law 1 covers those
# by hand), .md and .ps1 citations, and stem-only references like `tnt_80:76`.
#
# USAGE:
#   powershell -ExecutionPolicy Bypass -File _docs\tools\tnt_citation_check.ps1
#   powershell ... -ModRoot <path> -Doc <path to a .md to check>
# Exit 0 = clean, 1 = at least one rotted citation, 2 = bad arguments.
# =====================================================================================
param(
    [string]$ModRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent),
    [string]$Doc     = ''
)
$ErrorActionPreference = 'Stop'

if (-not (Test-Path (Join-Path $ModRoot 'descriptor.mod'))) {
    Write-Host "ERROR: -ModRoot '$ModRoot' has no descriptor.mod - not the mod root."; exit 2
}
if (-not $Doc) { $Doc = Join-Path $ModRoot 'CLAUDE.md' }
if (-not (Test-Path $Doc)) { Write-Host "ERROR: no document at '$Doc'."; exit 2 }

# -------------------------------------------------------------------------------------
# KNOWN-GOOD EXCEPTIONS TO ROW 3 ONLY. One entry per line, '<basename>:<start>' plus a
# reason. Row 1 and row 2 have no exception list and never will: a missing file or an
# out-of-range line is always wrong. Keep this list short and keep the reason.
# -------------------------------------------------------------------------------------
$IgnoreAttribution = @{
    # (empty on the shipped tree - added only with a reason)
}

# ---- 1. the shipped tree: basename -> relative paths, and the stem set ---------------
$byBase = @{}
$stems  = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
foreach ($d in @('common','events','gui','localization','data_binding','gfx','music','history')) {
    $p = Join-Path $ModRoot $d
    if (-not (Test-Path $p)) { continue }
    foreach ($f in (Get-ChildItem $p -Recurse -File)) {
        $b = $f.Name.ToLowerInvariant()
        if (-not $byBase.ContainsKey($b)) { $byBase[$b] = New-Object System.Collections.ArrayList }
        [void]$byBase[$b].Add($f.FullName.Substring($ModRoot.Length + 1))
        [void]$stems.Add([System.IO.Path]::GetFileNameWithoutExtension($f.Name))
    }
}
$lineCache = @{}
function Get-LineCount([string]$full) {
    if (-not $lineCache.ContainsKey($full)) {
        $lineCache[$full] = [System.IO.File]::ReadAllLines($full)
    }
    return $lineCache[$full].Count
}
function Get-Window([string]$full, [int]$a, [int]$b) {
    if (-not $lineCache.ContainsKey($full)) {
        $lineCache[$full] = [System.IO.File]::ReadAllLines($full)
    }
    $ls = $lineCache[$full]
    $lo = $a - 3; if ($lo -lt 1) { $lo = 1 }
    $hi = $b + 3; if ($hi -gt $ls.Count) { $hi = $ls.Count }
    $out = ''
    for ($i = $lo; $i -le $hi; $i++) { $out = $out + $ls[$i-1] + "`n" }
    return $out
}

# ---- 2. pull every citation out of the document -------------------------------------
$rxCite = [regex]'(?<path>(?:[<>A-Za-z0-9_.\-]+[\\/])*(?<base>[A-Za-z0-9_.\-]+\.(?:txt|gui|yml))):(?<a>\d+)(?:-(?<b>\d+))?'
$rxBare = [regex]'`:(?<a>\d+)(?:-(?<b>\d+))?`'
$rxIdent = [regex]'tnt_[A-Za-z0-9_]+'
$rxExt   = [regex]'^\.(txt|gui|yml|md|ps1)'
$rxTick  = [regex]'`([^`]+)`'

$docLines = [System.IO.File]::ReadAllLines($Doc)

# WHAT COUNTS AS A NEEDLE ON ONE DOC LINE. Two kinds, because CLAUDE.md cites two kinds
# of thing and a checker that only knew about the first produced eight false alarms on
# citations that were perfectly correct:
#   * a tnt_ IDENTIFIER of 8 characters or more, with file names filtered out - the
#     shape "`tnt_x_effect` (`tnt_y.txt:N`)", where the cited line declares or calls it.
#     Shorter than 8 is rejected because `tnt_ai` matches half the composer;
#   * a BACKTICKED CODE FRAGMENT of 6 characters or more that either carries an `=` or
#     carries no whitespace - the shape "is `tier = tier_county`, not `tier >= tier_county`
#     (`tnt_40_triggers.txt:294`)", where the cited line is a ROW and the identifier that
#     owns it is 20 lines up. File paths in backticks are rejected: they name the file
#     the citation already names, so they would pass everything.
# Whitespace inside a fragment is matched as \s+ so tabs and column padding do not
# matter. ANY ONE needle matching is a pass; see the honesty note in the header.
function Get-Candidates([int]$n) {
    if ($n -lt 1 -or $n -gt $docLines.Count) { return @() }
    $line = $docLines[$n-1]
    $out = New-Object System.Collections.ArrayList
    foreach ($m in $rxIdent.Matches($line)) {
        $tok  = $m.Value
        $tail = $line.Substring($m.Index + $m.Length)
        if ($tok.Length -lt 8)     { continue }          # too generic to mean anything
        if ($rxExt.IsMatch($tail)) { continue }          # ...tnt_x.txt - a file, not an identifier
        if ($stems.Contains($tok)) { continue }          # bare file stem
        if ($out -notcontains $tok) { [void]$out.Add($tok) }
    }
    foreach ($m in $rxTick.Matches($line)) {
        $frag = $m.Groups[1].Value.Trim()
        if ($frag.Length -lt 6)                          { continue }
        if ($rxCite.IsMatch($frag))                      { continue }   # the citation itself
        if ($frag -match '^:\d')                         { continue }   # a bare continuation ref
        if ($frag -match '\.(txt|gui|yml|md|ps1)$')      { continue }   # a file name or path
        if (-not ($frag.Contains('=') -or ($frag -notmatch '\s'))) { continue }   # ordinary prose
        if ($out -notcontains $frag) { [void]$out.Add($frag) }
    }
    return $out
}

# a needle matches the window if it is there modulo whitespace runs
function Test-Needle([string]$needle, [string]$window) {
    $parts = @($needle -split '\s+' | Where-Object { $_ -ne '' } | ForEach-Object { [regex]::Escape($_) })
    if ($parts.Count -eq 0) { return $false }
    return ($window -match ($parts -join '\s+'))
}

$cites   = New-Object System.Collections.ArrayList
$extern  = New-Object System.Collections.ArrayList
$unanch  = 0
for ($n = 1; $n -le $docLines.Count; $n++) {
    $line  = $docLines[$n-1]
    $named = New-Object System.Collections.ArrayList     # (index, base, path) on THIS line
    foreach ($m in $rxCite.Matches($line)) {
        $base = $m.Groups['base'].Value
        $rec  = [pscustomobject]@{
            doc   = $n
            col   = $m.Index
            base  = $base
            path  = $m.Groups['path'].Value
            a     = [int]$m.Groups['a'].Value
            b     = $(if ($m.Groups['b'].Success) { [int]$m.Groups['b'].Value } else { [int]$m.Groups['a'].Value })
            kind  = 'named'
            conf  = 'certain'
            raw   = $m.Value
        }
        if ($base -like 'tnt_*') {
            [void]$cites.Add($rec)
            [void]$named.Add($rec)
        } else {
            [void]$extern.Add("$($m.Value)   (CLAUDE.md:$n)")
        }
    }
    # bare continuation refs, resolved against the nearest file named before them
    foreach ($m in $rxBare.Matches($line)) {
        $hostCite = $null; $conf = ''
        foreach ($c in $named) { if ($c.col -lt $m.Index) { $hostCite = $c; $conf = 'certain' } }
        if ((-not $hostCite) -and $n -gt 1) {
            $prev = New-Object System.Collections.ArrayList
            foreach ($pm in $rxCite.Matches($docLines[$n-2])) {
                if ($pm.Groups['base'].Value -like 'tnt_*') { [void]$prev.Add($pm) }
            }
            if ($prev.Count -gt 0) {
                $pm = $prev[$prev.Count-1]
                $hostCite = [pscustomobject]@{ base = $pm.Groups['base'].Value; path = $pm.Groups['path'].Value }
                $conf = 'guessed'
            }
        }
        if (-not $hostCite) { $unanch++; continue }
        [void]$cites.Add([pscustomobject]@{
            doc  = $n
            col  = $m.Index
            base = $hostCite.base
            path = $hostCite.path
            a    = [int]$m.Groups['a'].Value
            b    = $(if ($m.Groups['b'].Success) { [int]$m.Groups['b'].Value } else { [int]$m.Groups['a'].Value })
            kind = 'bare'
            conf = $conf
            raw  = $m.Value
        })
    }
}

# ---- 3. check each one ---------------------------------------------------------------
$doc_name = Split-Path $Doc -Leaf
$fail = New-Object System.Collections.ArrayList
$note = New-Object System.Collections.ArrayList
$okN  = 0
foreach ($c in $cites) {
    $why  = $null
    $base = $c.base.ToLowerInvariant()
    $full = $null

    if (-not $byBase.ContainsKey($base)) {
        $why = "file does not exist anywhere in the shipped tree"
    } elseif ($byBase[$base].Count -gt 1) {
        $why = "ambiguous basename - shipped at " + (($byBase[$base]) -join ' and ')
    } else {
        $rel  = $byBase[$base][0]
        $full = Join-Path $ModRoot $rel
        # a folder prefix in the citation must match where the file really lives
        $dir = Split-Path ($c.path -replace '/','\') -Parent
        if ($dir -and ($dir -notmatch '^<') -and -not ($rel -replace '/','\').ToLowerInvariant().EndsWith(($dir + '\' + $base).ToLowerInvariant())) {
            $why = "cited under '$dir' but the file lives at '$rel'"
        }
    }

    if (-not $why) {
        $total = Get-LineCount $full
        if ($c.a -lt 1 -or $c.b -lt $c.a) {
            $why = "malformed range"
        } elseif ($c.b -gt $total) {
            $why = "line $($c.b) is past the end of the file ($total lines)"
        }
    }

    if (-not $why) {
        # THE CITATION'S OWN LINE *AND* THE ONE ABOVE IT, ALWAYS BOTH. CLAUDE.md wraps at
        # 100 columns, so the identifier a citation belongs to is as often on the previous
        # line as on its own ("...are their own rows of\n`tnt_ai_accept_value` (`file:N`)").
        # Taking only one of the two produced eight false alarms on correct citations.
        $cand = New-Object System.Collections.ArrayList
        foreach ($t in (Get-Candidates $c.doc))       { if ($cand -notcontains $t) { [void]$cand.Add($t) } }
        foreach ($t in (Get-Candidates ($c.doc - 1))) { if ($cand -notcontains $t) { [void]$cand.Add($t) } }
        if (@($cand).Count -gt 0) {
            $win = Get-Window $full $c.a $c.b
            $hit = $null
            foreach ($t in $cand) { if (Test-Needle $t $win) { $hit = $t; break } }
            if (-not $hit) {
                $key = $base + ':' + $c.a
                if ($IgnoreAttribution.ContainsKey($key)) {
                    [void]$note.Add(("{0}:{1}  {2}  attribution waived - {3}" -f $doc_name, $c.doc, $c.raw, $IgnoreAttribution[$key]))
                } else {
                    $why = "none of [" + (($cand) -join ', ') + "] appears within 3 lines of $($c.a)"
                }
            }
        }
    }

    if (-not $why) { $okN++; continue }

    $row = ("{0}:{1}  {2,-46}  {3}" -f $doc_name, $c.doc, $c.raw, $why)
    if ($c.kind -eq 'bare' -and $c.conf -eq 'guessed') {
        [void]$note.Add(("{0}   [bare ref, host file guessed from the line above - verify by hand]" -f $row))
    } else {
        [void]$fail.Add($row)
    }
}

# ---- 4. report ----------------------------------------------------------------------
Write-Host ("document        : {0}   ({1} lines)" -f $doc_name, $docLines.Count)
Write-Host ("tnt_ citations  : {0} checked   ({1} named, {2} bare continuation refs)" -f $cites.Count,
            (@($cites | Where-Object { $_.kind -eq 'named' })).Count,
            (@($cites | Where-Object { $_.kind -eq 'bare'  })).Count)
Write-Host ("  clean         : {0}" -f $okN)
Write-Host ("FAIL  (missing file / line out of range / anchor no longer names the thing) : {0}" -f $fail.Count)
Write-Host ("NOTE  (guessed host file, or a waived attribution - not failures)           : {0}" -f $note.Count)
Write-Host ("SKIPPED (vanilla or other non-tnt_ file, checked by hand under house law 1) : {0}" -f $extern.Count)
Write-Host ("SKIPPED (bare continuation ref with no file named on it or the line above)  : {0}" -f $unanch)

if ($note.Count) {
    Write-Host ""; Write-Host "NOTE:"
    foreach ($x in $note) { Write-Host "  $x" }
}
if ($fail.Count) {
    Write-Host ""; Write-Host "FAIL:"
    foreach ($x in $fail) { Write-Host "  $x" }
    Write-Host ""
    Write-Host "FAIL: re-read the cited file and move the number to the line that actually carries"
    Write-Host "      the named thing. Do NOT delete the sentence to silence this - the sentence is"
    Write-Host "      the map. If the prose is what is wrong, fix the prose."
    exit 1
}
Write-Host ""; Write-Host "PASS: every tnt_ citation resolves, is in range, and still names its thing."
exit 0
