# =============================================================================
# tnt_rule_conformance.ps1 — cross-path game-rule source checks.
#
# FAIL checks cover window visibility, AI composer entries, balancer writers,
# and threat calibration/single-source invariants. Structural noncurrency rows
# use the existing cached bridge. Prestige/piety instead require four live
# directional GUI bindings and their exact scripted call chains (check 1b).
# Cheap faith/fame predicates may be evaluated live; never cache one direction
# as permission for the opposite direction.
#
# Scripted-GUI writers and apply helpers are also listed for review. Currency
# writers now have execution guards; atomic whole-deal preflight validates both
# transfer directions before any effects, rather than rechecking midway through
# a treaty. test_currency_trade_rules.py exercises those source contracts and
# the real currency-trigger AST, including the shared manual/AI balancer.
# Informational notes are not substitutes for that behavioral test.
#
# AI-world rules are relevant too; the prestige transfer helper uses the same
# canonical predicate. Penalties for refusing threats are not currency trades.
# Historical blanket claims of safe-by-unreachability or an open stale-letter
# ruling are obsolete. All other resource and advanced-term policies remain.
#
# Exit 0 clean / 1 offender(s) / 2 bad arguments.
# =============================================================================
param(
    [string]$ModRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
)

if (-not (Test-Path (Join-Path $ModRoot 'common\game_rules'))) { Write-Host "BAD ModRoot: $ModRoot"; exit 2 }
if (-not (Test-Path (Join-Path $ModRoot 'gui')))               { Write-Host "BAD ModRoot: $ModRoot"; exit 2 }

# --- THE MAP. rule -> bridge variable -> the term stems it gates -------------
# Verified 2026-08-19 against tnt_80_game_rules.txt and the read sites.
# V26 added the fifth irreversible family: `subject`, the transferred vassal.
# A vassal handed across a realm border comes back by war or not at all - there
# is no interaction of any kind that undoes it - so it belongs under
# tnt_advanced_terms with betrothal, the ceded county, sworn fealty and release
# from vassalage. It has NO composer archetype and NO balancer rung yet, so
# checks 2 and 3 have nothing to say about it today; if an archetype is ever
# written for it, its entry MUST carry has_game_rule = tnt_advanced_terms_on in
# the same commit or this tool goes red - which is the whole reason the tool
# exists.
# MidRung = $true means the rule has a setting BETWEEN off and on. Only those
# rules can forbid a term the player has already staged, which is the whole of
# why NOTE C's unreachability argument no longer covers their apply legs.
$RULES = @(
    @{ Rule = 'tnt_advanced_terms'; Bridge = 'tnt_advanced';        MidRung = $false; Terms = @('title','vassal','indep','marriage','subject') },
    @{ Rule = 'tnt_trade_prestige'; Bridge = 'tnt_trade_prest_on';  MidRung = $true;  Terms = @('prestige') },
    @{ Rule = 'tnt_trade_piety';    Bridge = 'tnt_trade_pty_on';    MidRung = $true;  Terms = @('piety') },
    # DOCUMENTATION-ONLY ROW, 2026-08-24. Bridge '<none>' and Terms @() are both
    # deliberate - see THE NAMED EXEMPTION in the header. This row exists so the
    # rule appears in "rules checked" and so the next author finds the exemption
    # written down instead of re-deriving it. POSITION D is its real check.
    @{ Rule = 'tnt_threat_scale';   Bridge = '<none>';              MidRung = $false; Terms = @() }
)

$COMPOSER   = Join-Path $ModRoot 'common\scripted_effects\tnt_37_ai_offer.txt'
$SANDBOX    = Join-Path $ModRoot 'common\scripted_effects\tnt_38_ai_world.txt'
$BALANCER   = Join-Path $ModRoot 'common\scripted_effects\tnt_39_autobalance.txt'
$APPLY      = Join-Path $ModRoot 'common\scripted_effects\tnt_32_apply.txt'
# The currency legs (E30 prestige, E31 piety) are NOT in tnt_32_apply.txt. They
# are the only legs a middle rung can reach, so NOTE C must scan this file too.
$CURRENCY   = Join-Path $ModRoot 'common\scripted_effects\tnt_33_currency_apply.txt'
$SGUIDIR    = Join-Path $ModRoot 'common\scripted_guis'

$fails = @()
$notes = @()

function Strip-Comment([string]$s) {
    $i = $s.IndexOf('#')
    if ($i -ge 0) { return $s.Substring(0, $i) }
    return $s
}

# Does a code line WRITE this term? Covers set_variable / add_to_variable /
# change_variable in both block form (`name = tnt_x`) and shorthand.
function Writes-Term([string]$code, [string]$stem) {
    if ($code -match ('name\s*=\s*tnt_(sel_)?' + $stem + '_')) { return $true }
    if ($code -match ('(set|add_to|change)_variable\s*=\s*tnt_(sel_)?' + $stem + '_')) { return $true }
    return $false
}

# Does a code line READ this rule, in any of the three legal shapes?
function Reads-Rule([string]$code, $r) {
    if ($code -match ('has_game_rule\s*=\s*' + $r.Rule + '_')) { return $true }
    if ($code -match ($r.Rule + '_trigger'))                   { return $true }
    # These lightweight wrappers are proven directional in check 1b below.
    if ($r.Rule -match '^tnt_trade_(prestige|piety)$') {
        if ($code -match ('tnt_show_' + $Matches[1] + '_[pr]_trigger')) { return $true }
    }
    if ($code -match ('var:' + $r.Bridge + '\b'))              { return $true }
    if ($code -match ("TntOn\(\s*'" + $r.Bridge + "'\s*\)"))   { return $true }
    return $false
}

# A block's body is carried as a list of "<lineno>`t<code>" strings. PowerShell
# 5.1 refuses `$hashtable.ArrayMember += ,@(...)`, so use a typed List and split
# on the tab at the read site - see Body-Lines / Body-Nums below.
function New-Block($name, $start) {
    return @{ Name = $name; Start = $start; End = 0; Weight = 0; Body = (New-Object System.Collections.Generic.List[string]) }
}
function Body-Code([string]$row) { return $row.Substring($row.IndexOf("`t") + 1) }
function Body-Num([string]$row)  { return [int]$row.Substring(0, $row.IndexOf("`t")) }

# Split a file into top-level `name = {` blocks.
function Get-TopLevelBlocks([string]$path) {
    $out = New-Object System.Collections.Generic.List[object]
    if (-not (Test-Path $path)) { return $out }
    $lines = [System.IO.File]::ReadAllLines($path)
    $depth = 0; $cur = $null
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $code = Strip-Comment $lines[$i]
        if ($depth -eq 0 -and $code -match '^([A-Za-z0-9_]+)\s*=\s*\{') {
            $cur = New-Block $Matches[1] ($i + 1)
        }
        if ($cur -ne $null) { [void]$cur.Body.Add(("{0}`t{1}" -f ($i + 1), $code)) }
        $depth += ([regex]::Matches($code, '\{')).Count - ([regex]::Matches($code, '\}')).Count
        if ($depth -le 0) {
            $depth = 0
            if ($cur -ne $null) { $cur.End = $i + 1; [void]$out.Add($cur); $cur = $null }
        }
    }
    return $out
}

# Split the composer's ONE random_list into its weighted entries.
function Get-DrawEntries([string]$path) {
    $out = New-Object System.Collections.Generic.List[object]
    if (-not (Test-Path $path)) { return $out }
    $lines = [System.IO.File]::ReadAllLines($path)
    $inList = $false; $listDepth = 0; $depth = 0; $cur = $null
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $code = Strip-Comment $lines[$i]
        $o = ([regex]::Matches($code, '\{')).Count
        $c = ([regex]::Matches($code, '\}')).Count
        if (-not $inList -and $code -match 'random_list\s*=\s*\{') {
            $inList = $true; $listDepth = $depth
            $depth += $o - $c
            continue
        }
        if ($inList) {
            if ($cur -eq $null -and $depth -eq ($listDepth + 1) -and $code -match '^\s*(\d+)\s*=\s*\{') {
                $cur = New-Block 'entry' ($i + 1)
                $cur.Weight = [int]$Matches[1]
            }
            if ($cur -ne $null) { [void]$cur.Body.Add(("{0}`t{1}" -f ($i + 1), $code)) }
            $newDepth = $depth + $o - $c
            if ($cur -ne $null -and $newDepth -le ($listDepth + 1) -and $c -gt 0) {
                $cur.End = $i + 1; [void]$out.Add($cur); $cur = $null
            }
            if ($newDepth -le $listDepth) { $inList = $false }
            $depth = $newDepth
            continue
        }
        $depth += $o - $c
        if ($depth -lt 0) { $depth = 0 }
    }
    return $out
}

# =========================== FAIL 1 - THE WINDOW ROWS ========================
# Every .gui row that shows a gated term must carry the bridge conjunct.
foreach ($f in Get-ChildItem (Join-Path $ModRoot 'gui') -Recurse -Include *.gui) {
    $ln = 0
    foreach ($line in [System.IO.File]::ReadAllLines($f.FullName)) {
        $ln++
        if ($line.TrimStart().StartsWith('#')) { continue }
        if ($line -notmatch "TntRow\(\s*'tnt_show_([A-Za-z0-9_]+)'\s*\)") { continue }
        $gate = $Matches[1]
        foreach ($r in $RULES) {
            foreach ($t in $r.Terms) {
                if ($gate -notmatch ('^' + $t + '_(p|r)$')) { continue }
                if (-not (Reads-Rule $line $r)) {
                    $fails += [pscustomobject]@{
                        Pos = '1 WINDOW'; Rule = $r.Rule; Term = $t
                        Where = ("{0}:{1}" -f $f.Name, $ln)
                        What = ("row tnt_show_{0} has no TntOn('{1}') conjunct - the rule blocks the term without hiding it" -f $gate, $r.Bridge)
                    }
                }
            }
        }
    }
}

# ================== FAIL 1b - LIVE DIRECTIONAL CURRENCY ROWS =================
# Require the live binding as well as both levels of its script call chain.
# A cached bridge is insufficient: faith/fame can change while the window waits.
$currencyWindow = Join-Path $ModRoot 'gui/tnt_diplomacy_window.gui'
$currencyGui = Join-Path $SGUIDIR 'tnt_22_v2.txt'
$currencyGates = Join-Path $ModRoot 'common/scripted_triggers/tnt_41_gates.txt'
$windowCode = ([IO.File]::ReadAllLines($currencyWindow) | ForEach-Object { Strip-Comment $_ }) -join "`n"
$guiBlocks = @(Get-TopLevelBlocks $currencyGui)
$gateBlocks = @(Get-TopLevelBlocks $currencyGates)
foreach ($tradeCurrency in @('prestige', 'piety')) {
    foreach ($side in @('p', 'r')) {
        $name = "tnt_trade_${tradeCurrency}_${side}_available"
        $wrapper = "tnt_show_${tradeCurrency}_${side}_trigger"
        $binding = 'visible = "[TntValid(''' + $name + ''')]"'
        # Associate the predicate with its owning row, not just an occurrence
        # somewhere in the window: swapping P/R must fail this check.
        $rowPattern = 'tnt_item_row_currency\s*=\s*\{\s*name\s*=\s*"tnt_row_' +
            $tradeCurrency + '_' + $side + '"\s*layoutpolicy_horizontal\s*=\s*expanding\s*' +
            [regex]::Escape($binding)
        $bindingCount = [regex]::Matches($windowCode, $rowPattern).Count
        $sg = @($guiBlocks | Where-Object { $_.Name -eq $name })
        $gate = @($gateBlocks | Where-Object { $_.Name -eq $wrapper })
        $sgCode = (($sg | ForEach-Object { $_.Body } | ForEach-Object { Body-Code $_ }) -join '') -replace '\s+', ''
        $gateCode = (($gate | ForEach-Object { $_.Body } | ForEach-Object { Body-Code $_ }) -join '') -replace '\s+', ''
        $pair = if ($side -eq 'p') { 'A=rootB=$OTHER$' } else { 'A=$OTHER$B=root' }
        $expected = 'tnt_trade_' + $tradeCurrency + '_trigger={' + $pair + '}'
        if ($bindingCount -ne 1 -or $sg.Count -ne 1 -or $gate.Count -ne 1 -or
            -not $sgCode.Contains('is_valid={custom_tooltip={text=tnt_err_' + $tradeCurrency + '_trade_rule' + $wrapper + '={OTHER=var:tnt_partner}}}') -or
            -not $sgCode.Contains('effect={}') -or -not $gateCode.Contains($expected)) {
            $fails += [pscustomobject]@{
                Pos = '1b LIVE'; Rule = "tnt_trade_$tradeCurrency"; Term = "${tradeCurrency}_$side"
                Where = 'window / scripted_gui / directional gate'
                What = "Expected one live row binding and read-only $name -> $wrapper -> actual giver/receiver permission; bindings=$bindingCount"
            }
        }
    }
}

# ====================== FAIL 2 - THE COMPOSER ARCHETYPES =====================
# Any draw entry that stages a gated term must read that term's rule.
$entries = Get-DrawEntries $COMPOSER
foreach ($e in $entries) {
    foreach ($r in $RULES) {
        foreach ($t in $r.Terms) {
            $writes = $false; $reads = $false; $writeAt = 0
            foreach ($row in $e.Body) {
                $code = Body-Code $row
                if (-not $writes -and (Writes-Term $code $t)) { $writes = $true; $writeAt = Body-Num $row }
                if (Reads-Rule $code $r) { $reads = $true }
            }
            if ($writes -and -not $reads) {
                $fails += [pscustomobject]@{
                    Pos = '2 COMPOSER'; Rule = $r.Rule; Term = $t
                    Where = ("tnt_37_ai_offer.txt:{0} (entry weight {1}, lines {0}-{2})" -f $e.Start, $e.Weight, $e.End)
                    What = ("stages tnt_{0}_* at :{1} but never reads {2} - with the rule off the AI still offers it" -f $t, $writeAt, $r.Rule)
                }
            }
        }
    }
}
if ($entries.Count -eq 0) { Write-Host "WARNING: no draw entries parsed from tnt_37_ai_offer.txt - check 2 did not run." }

# ====================== FAIL 3 - THE AUTO-BALANCE RUNGS ======================
foreach ($b in (Get-TopLevelBlocks $BALANCER)) {
    foreach ($r in $RULES) {
        foreach ($t in $r.Terms) {
            $writes = $false; $reads = $false; $writeAt = 0
            foreach ($row in $b.Body) {
                $code = Body-Code $row
                if (-not $writes -and (Writes-Term $code $t)) { $writes = $true; $writeAt = Body-Num $row }
                if (Reads-Rule $code $r) { $reads = $true }
            }
            if ($writes -and -not $reads) {
                $fails += [pscustomobject]@{
                    Pos = '3 BALANCER'; Rule = $r.Rule; Term = $t
                    Where = ("tnt_39_autobalance.txt:{0} ({1})" -f $b.Start, $b.Name)
                    What = ("writes tnt_{0}_* at :{1} but never reads {2}" -f $t, $writeAt, $r.Rule)
                }
            }
        }
    }
}

# ============================ NOTE A - SCRIPTED GUIS =========================
if (Test-Path $SGUIDIR) {
    foreach ($f in Get-ChildItem $SGUIDIR -Filter *.txt) {
        foreach ($b in (Get-TopLevelBlocks $f.FullName)) {
            foreach ($r in $RULES) {
                foreach ($t in $r.Terms) {
                    if ($b.Name -notmatch ('tnt_(sel_)?' + $t + '_')) { continue }
                    $reads = $false
                    foreach ($row in $b.Body) { if (Reads-Rule (Body-Code $row) $r) { $reads = $true } }
                    if (-not $reads) {
                        $notes += ("A  {0,-22} {1,-18} {2}:{3}  ({4})" -f $r.Rule, $t, $f.Name, $b.Start, $b.Name)
                    }
                }
            }
        }
    }
}

# ============================== NOTE B - SANDBOX =============================
# The sandbox cannot be checked term-by-term the way the composer can: it does
# NOT stage the deal variables at all. Measured 2026-08-19 - the whole of
# tnt_38_ai_world.txt writes exactly two tnt_* variables (tnt_ai_world_cd and
# tnt_truce_negotiated, the latter a vanilla effect's `name` argument), because
# an AI-to-AI treaty is applied directly with vanilla effects rather than
# assembled on a window. So the only question this position can honestly ask is
# the blunt one, and the answer is a single number.
if (Test-Path $SANDBOX) {
    $sandboxReads = 0
    foreach ($line in [System.IO.File]::ReadAllLines($SANDBOX)) {
        $code = Strip-Comment $line
        if ($code -match 'has_game_rule\s*=\s*tnt_|tnt_trade_(prestige|piety)_trigger\s*=') { $sandboxReads++ }
    }
    if ($sandboxReads -eq 0) {
        $notes += "B  tnt_38_ai_world.txt reads ZERO tnt_ game rules. No lobby switch reaches the AI-to-AI layer at all."
        $notes += "B  It stages no deal variables either (2 tnt_* writes in the whole file), so this position cannot be"
        $notes += "B  checked term-by-term. Whether a switch SHOULD govern treaties the player never sees is a design"
        $notes += "B  question that has never been put to the user - see CLAUDE.md section 4."
    }
    else {
        $notes += ("B  AI-world has {0} direct/canonical rule reads; the prestige-transfer helper and penalty distinction are covered by test_currency_trade_rules.py." -f $sandboxReads)
    }
}

# ============================= NOTE C - APPLY LEGS ===========================
# BOTH apply files. See the NOTE C paragraph in the header: a MidRung rule can
# forbid a term the player already staged, so its leg is NOT safe by
# unreachability and prints as C! rather than C.
foreach ($apath in @($APPLY, $CURRENCY)) {
    if (-not (Test-Path $apath)) {
        $notes += ("C  MISSING apply file {0} - check C did not run over it." -f $apath)
        continue
    }
    $aname = Split-Path -Leaf $apath
    foreach ($b in (Get-TopLevelBlocks $apath)) {
        foreach ($r in $RULES) {
            foreach ($t in $r.Terms) {
                $touches = $false; $reads = $false
                foreach ($row in $b.Body) {
                    $code = Body-Code $row
                    if ($code -match ('var:tnt_(sel_)?' + $t + '_')) { $touches = $true }
                    if (Reads-Rule $code $r) { $reads = $true }
                }
                if (-not $touches -or $reads) { continue }
                if ($r.MidRung) {
                    $notes += ("C  {0,-22} {1,-18} {2}:{3}  ({4})  per-leg gate intentionally absent; whole-deal atomic preflight and both directions are covered by test_currency_trade_rules.py" -f $r.Rule, $t, $aname, $b.Start, $b.Name)
                }
                else {
                    $notes += ("C  {0,-22} {1,-18} {2}:{3}  ({4})  end-rung only - safe by unreachability" -f $r.Rule, $t, $aname, $b.Start, $b.Name)
                }
            }
        }
    }
}

# ==================== FAIL D - THE SINGLE-READ ASSERTION =====================
# See the POSITION D paragraph in the header. One rule, one read site, inside
# the one value every consumer of the mechanic already calls.
$D_FILE  = 'tnt_57_threat_values.txt'
$D_BLOCK = 'tnt_threat_scale_value'
$dHits = @()
$dRoot = Join-Path $ModRoot 'common'
if (Test-Path $dRoot) {
    foreach ($f in (Get-ChildItem $dRoot -Recurse -File -Include *.txt, *.gui)) {
        $ln = 0
        foreach ($line in [System.IO.File]::ReadAllLines($f.FullName)) {
            $ln++
            if ((Strip-Comment $line) -match 'has_game_rule\s*=\s*tnt_threat_scale_') {
                $dHits += [pscustomobject]@{ File = $f.Name; Path = $f.FullName; Line = $ln }
            }
        }
    }
}
if ($dHits.Count -eq 0) {
    $fails += [pscustomobject]@{
        Pos = 'D 1READ'; Rule = 'tnt_threat_scale'; Term = '<none>'
        Where = 'common\'
        What  = 'the rule is NEVER read - N falls back to its literal default and the lobby setting does nothing at all'
    }
}
foreach ($h in @($dHits | Where-Object { $_.File -ne $D_FILE })) {
    $fails += [pscustomobject]@{
        Pos = 'D 1READ'; Rule = 'tnt_threat_scale'; Term = '<none>'
        Where = ("{0}:{1}" -f $h.File, $h.Line)
        What  = ("a SECOND read site. This rule is read only inside {0} of {1}; two sites can disagree, which is house law 9." -f $D_BLOCK, $D_FILE)
    }
}
$dIn = @($dHits | Where-Object { $_.File -eq $D_FILE })
if ($dIn.Count -gt 0) {
    $dBlocks = Get-TopLevelBlocks $dIn[0].Path
    foreach ($h in $dIn) {
        $owner = '<top level>'
        foreach ($b in $dBlocks) { if ($h.Line -ge $b.Start -and $h.Line -le $b.End) { $owner = $b.Name } }
        if ($owner -ne $D_BLOCK) {
            $fails += [pscustomobject]@{
                Pos = 'D 1READ'; Rule = 'tnt_threat_scale'; Term = '<none>'
                Where = ("{0}:{1}" -f $h.File, $h.Line)
                What  = ("read from {0} instead of {1} - the rule must have exactly one read site" -f $owner, $D_BLOCK)
            }
        }
    }
}
$notes += ("D  tnt_threat_scale : {0} read site(s) under common\, all inside {1} ({2}) - the chokepoint holds." -f $dHits.Count, $D_BLOCK, $D_FILE)

# The 2026-09-30 access ruling retains scale 2.5/5/7.5/10 but requires100
# in six ordinary gate/probe consumers, one strategic gate and the selected
# price guard. Strategic fealty retains its raw ratio4 and shared relation
# helper. Lock them together so a later edit cannot weaken only the GUI, generic
# AI, or submission AI.
$dBarHits = @()
$dRatioHits = @()
$dRelationHits = @()
foreach ($f in (Get-ChildItem $dRoot -Recurse -File -Include *.txt, *.gui)) {
    $ln = 0
    foreach ($line in [System.IO.File]::ReadAllLines($f.FullName)) {
        $ln++
        $code = Strip-Comment $line
        foreach ($m in [regex]::Matches($code, '\btnt_threat_points_value\s*>=\s*(?<bar>[0-9]+(?:\.[0-9]+)?)')) {
            $dBarHits += [pscustomobject]@{ File = $f.Name; Line = $ln; Bar = $m.Groups['bar'].Value }
        }
        foreach ($m in [regex]::Matches($code, '\btnt_threat_ratio_value\s*>=\s*(?<bar>[0-9]+(?:\.[0-9]+)?)')) {
            $dRatioHits += [pscustomobject]@{ File = $f.Name; Line = $ln; Bar = $m.Groups['bar'].Value }
        }
        if ($code -match '\btnt_threat_target_allowed_trigger\s*=') {
            $dRelationHits += [pscustomobject]@{ File = $f.Name; Line = $ln }
        }
    }
}
$dBaseBars = @($dBarHits | Where-Object { $_.Bar -eq '100' -and $_.File -notin @('tnt_40_triggers.txt', 'tnt_57_threat_values.txt') })
$dStrategicBars = @($dBarHits | Where-Object { $_.Bar -eq '100' -and $_.File -eq 'tnt_40_triggers.txt' })
$dPriceBars = @($dBarHits | Where-Object { $_.Bar -eq '100' -and $_.File -eq 'tnt_57_threat_values.txt' })
$dOtherBars = @($dBarHits | Where-Object { $_.Bar -ne '100' })
$dStrategicOwnerOk = $false
$dStrategicRatioOk = $false
if ($dStrategicBars.Count -eq 1 -and $dStrategicBars[0].File -eq 'tnt_40_triggers.txt' -and
    $dRatioHits.Count -eq 1 -and $dRatioHits[0].File -eq 'tnt_40_triggers.txt' -and $dRatioHits[0].Bar -eq '4') {
    $dStrategicPath = Join-Path $dRoot 'scripted_triggers\tnt_40_triggers.txt'
    $dStrategicBlocks = Get-TopLevelBlocks $dStrategicPath
    foreach ($b in $dStrategicBlocks) {
        if ($dStrategicBars[0].Line -ge $b.Start -and $dStrategicBars[0].Line -le $b.End) {
            $dStrategicOwnerOk = ($b.Name -eq 'tnt_ai_coercive_fealty_pair_trigger')
        }
        if ($dRatioHits[0].Line -ge $b.Start -and $dRatioHits[0].Line -le $b.End) {
            $dStrategicRatioOk = ($b.Name -eq 'tnt_ai_coercive_fealty_pair_trigger')
        }
    }
}
if ($dBarHits.Count -ne 8 -or $dBaseBars.Count -ne 6 -or $dStrategicBars.Count -ne 1 -or $dPriceBars.Count -ne 1 -or $dOtherBars.Count -ne 0 -or -not $dStrategicOwnerOk -or -not $dStrategicRatioOk) {
    $fails += [pscustomobject]@{
        Pos = 'D BAR'; Rule = 'tnt_threat_scale'; Term = 'threat'
        Where = 'common\'
        What = ("100-point sites={0}, ordinary={1}, strategic={2}, price={3}, other={4}, strategic-owner={5}, ratio4-owner={6}; expected 8 total: six ordinary, one strategic and one price guard; strategic ratio >= 4 remains" -f $dBarHits.Count, $dBaseBars.Count, $dStrategicBars.Count, $dPriceBars.Count, $dOtherBars.Count, $dStrategicOwnerOk, $dStrategicRatioOk)
    }
}

$dScalePath = Join-Path $dRoot 'script_values\tnt_57_threat_values.txt'
$dScaleBlocks = @(Get-TopLevelBlocks $dScalePath | Where-Object { $_.Name -eq $D_BLOCK })
$dScaleValues = @()
if ($dScaleBlocks.Count -eq 1) {
    $dScaleLines = [System.IO.File]::ReadAllLines($dScalePath)
    $dScaleCode = (($dScaleLines[($dScaleBlocks[0].Start - 1)..($dScaleBlocks[0].End - 1)] | ForEach-Object { Strip-Comment $_ }) -join "`n")
    $dScaleValues = @([regex]::Matches($dScaleCode, '\bvalue\s*=\s*(?<n>[0-9]+(?:\.[0-9]+)?)') | ForEach-Object { $_.Groups['n'].Value })
}
if (($dScaleValues -join ',') -ne '5,2.5,7.5,10') {
    $fails += [pscustomobject]@{
        Pos = 'D SCALE'; Rule = 'tnt_threat_scale'; Term = 'threat'
        Where = 'tnt_57_threat_values.txt'
        What = ("scale values [{0}], expected [5,2.5,7.5,10] in fallback/rare/frequent/constant order" -f ($dScaleValues -join ','))
    }
}

$dGatePath = Join-Path $dRoot 'scripted_triggers\tnt_41_gates.txt'
$dGateBlocks = @(Get-TopLevelBlocks $dGatePath | Where-Object { $_.Name -eq 'tnt_threat_target_allowed_trigger' })
$dRelationShapeOk = $false
if ($dGateBlocks.Count -eq 1) {
    $dGateLines = [System.IO.File]::ReadAllLines($dGatePath)
    $dGateCode = (($dGateLines[($dGateBlocks[0].Start - 1)..($dGateBlocks[0].End - 1)] | ForEach-Object { Strip-Comment $_ }) -join '')
    $dGateCanonical = [regex]::Replace($dGateCode, '\s+', '')
    $dRelationShapeOk =
        $dGateCanonical.Contains('$B$={is_independent_ruler=yesNOT={is_allied_to=$A$}}') -and
        $dGateCanonical.Contains('$A$={any_warden_hostage={home_court?=$B$}}') -and
        $dGateCanonical.Contains('$B$={any_warden_hostage={home_court?=$A$}}')
}
if ($dRelationHits.Count -ne 4 -or -not $dRelationShapeOk) {
    $fails += [pscustomobject]@{
        Pos = 'D REL'; Rule = 'tnt_threat_scale'; Term = 'threat'
        Where = 'tnt_41_gates.txt / tnt_20_scripted_guis.txt'
        What = ("relation helper definitions+calls={0}, shape={1}; expected one definition + two central-gate calls + one GUI reason, with independent/non-allied/two-way-hostage rows" -f $dRelationHits.Count, $dRelationShapeOk)
    }
}
if ($dBarHits.Count -eq 8 -and $dBaseBars.Count -eq 6 -and $dStrategicBars.Count -eq 1 -and $dPriceBars.Count -eq 1 -and $dOtherBars.Count -eq 0 -and $dStrategicOwnerOk -and $dStrategicRatioOk -and ($dScaleValues -join ',') -eq '5,2.5,7.5,10' -and $dRelationHits.Count -eq 4 -and $dRelationShapeOk) {
    $notes += 'D  threat calibration : scale [2.5,5,7.5,10], all 8 comparisons >= 100, submission raw ratio=4, shared independent/non-allied/no-hostage relation gate - locked.'
}

# ================================= REPORT ====================================
Write-Host ("rules checked : {0}" -f $RULES.Count)
Write-Host ("terms gated   : {0}" -f (($RULES | ForEach-Object { $_.Terms }) -join ', '))
Write-Host ("draw entries  : {0}" -f $entries.Count)
Write-Host ""
Write-Host ("NOTE - reported, never fatal (see the header for why each is a note) : {0}" -f $notes.Count)
$notes | Sort-Object | ForEach-Object { Write-Host "      $_" }
Write-Host ""

if ($fails.Count -eq 0) {
    Write-Host "PASS - every gated term reads its rule in the window, the composer and the balancer."
    exit 0
}
$fails | Sort-Object Pos, Rule, Term | ForEach-Object {
    Write-Host ("FAIL  {0,-11} {1,-20} term={2,-10} {3}" -f $_.Pos, $_.Rule, $_.Term, $_.Where)
    Write-Host ("        {0}" -f $_.What)
}
Write-Host ""
Write-Host ("OFFENDERS: {0}" -f $fails.Count)
exit 1
