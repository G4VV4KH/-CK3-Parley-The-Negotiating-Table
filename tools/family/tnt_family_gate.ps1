# =============================================================================
# tnt_family_gate.ps1                THE MECHANICAL GATE OVER ALL THREE MOD TREES
#
# WHY THIS TOOL EXISTS. Since the V23 split the project is a FAMILY of three
# mods - the core (Parley: The Negotiating Table), the MCA addon
# (marriage_calc_assistant) and its narrow AGOT adapter
# (agot_marriage_calc_assistant) -
# but the four shipped checkers scan the core alone. Every guarantee about the
# addon trees (encodings, exact inventories, the pure-value adapter seam,
# one measured GUI exception and filename order) was verified BY HAND at ship
# time. A hand-verified invariant is one edit away from being a lie with no
# alarm attached. This tool makes every one of those guarantees mechanical and
# re-checkable in one run, over all three trees at once.
#
# THE NINE CHECKS, EACH WITH THE REASON IT EXISTS:
#
#   1  BRACE BALANCE - final depth zero and NO NEGATIVE DIP, every .txt /
#      .gui / .yml in every tree. Quoted strings are stripped BEFORE comment
#      stripping, in that order, because a '#' inside a quoted string
#      (default_format = "#low", loc markup "#high ... #!") is NOT a comment
#      and counting braces after a naive comment cut miscounts. A negative
#      dip with a zero total means a brace pair is INVERTED, which a plain
#      total cannot see. Reason: one stray brace silently truncates a script
#      database file at parse time - everything below the break just stops
#      existing, with at most one cryptic log line.
#
#   2  ENCODING BY EXTENSION - .txt and .yml start with the UTF-8 BOM
#      EF BB BF, .gui do NOT; no 0x0D byte anywhere; exactly one trailing
#      0x0A. Reason (house law 7): without the BOM CK3 silently ignores a
#      localization file and every key renders as its own name; a BOM on a
#      .gui breaks the GUI lexer; CR bytes and missing trailing newlines are
#      the classic diff-churn and last-line-swallowed hazards.
#
#   3  ASCII PURITY OF THE FOUR FENCED FILES - tnt_37_ai_offer.txt,
#      tnt_39_autobalance.txt, tnt_3b_log.txt and, since V29,
#      common\important_actions\tnt_91_alerts.txt: zero non-ASCII BYTES after
#      the three BOM bytes (house law 8). Reason, and it is MEASURED rather
#      than theoretical: the lexer decodes non-ASCII comment bytes under the
#      system codepage, and one Cyrillic comment cost the WHOLE alert file at
#      load. See this check's own header below for that measurement.
#
#   4  LOCALIZATION - THE NINE-LANGUAGE FAN, PER MOD TREE. The language
#      list is a LITERAL in this tool ($LANGS), measured from the vanilla
#      1.19 install: <VanillaRoot>\localization\* minus 'jomini' (engine
#      plumbing, not a language); if Paradox adds a language, one line
#      changes. Per english stem (derived from the shipped
#      localization\english\<stem>_l_english.yml) and per language, the
#      file localization\<lang>\<stem>_l_<lang>.yml must EXIST - a missing
#      language is a FAIL, the fan ships complete - open with the l_<lang>:
#      header, carry the UTF-8 BOM, no CR, one trailing LF, and give every
#      key line exactly one leading space and the key:0 "value" shape with
#      zero duplicate keys. KEY-SET IDENTITY: every language file carries
#      EXACTLY the english key set (missing/extra reported per language).
#      TOKEN PARITY - the check that catches a broken translation
#      mechanically: per key, the MULTISET of [..] datafunction tokens and
#      $key$ references must equal the english original's, order-free,
#      after normalization (trailing |format stripped - a translation may
#      re-case with |l; whitespace collapsed; both concept-link forms
#      reduced to concept:<canonical> via vanilla's game_concepts alias
#      table, because english [alliances|E] and a translated
#      [Concept('alliance', '...')|E] are the SAME link) - a translation
#      that dropped or mangled a token renders broken with nothing in any
#      log. And #markup balance: per value, '#' openers match '#!'
#      closers. Reason (house law 9, widened to the fan): a key missing in
#      one language renders as its own raw name there, and CK3 logs
#      nothing about it.
#
#   5  VANILLA PATH COLLISIONS - zero in Parley and the AGOT adapter; MCA's
#      sole exception is gui/interaction_marriage.gui. It is allowed only when
#      the reviewed v2.3 functional patch reconstructs it from live vanilla.
#      Every other collision is a failure.
#
#   6  EXACT ADDON INVENTORY - MCA v3.1.0 has shared candidate-benefit values and a
#      private player-owned sorting snapshot; AGOT v2.2 uses the component ABI.
#      Exact file and definition sets are asserted, including five shared
#      candidate-benefit values and their six direct, described raw/GUI blocks.
#      MCA owns eight formula-zero component slots, the two P/R aggregates and
#      alliance base 40; AGOT overrides P1, R1..R4 and alliance base 40.
#      P1/R1 share current-dragonrider potential; R2..R4 are zero. The component
#      descriptions are exact in all nine languages and the
#      GUI wrappers expose them one level deep. Old twins, fences, effects,
#      on_actions, decisions and interaction database copies are forbidden.
#
#   7  OWNERSHIP SEAM - Parley alone defines the five legacy compatibility
#      stubs and calls them 1/1/1/1/2 times. Neither addon redefines them.
#      Parley overlaps neither addon; MCA and AGOT overlap in exactly P1, four R
#      component values and the alliance base. Namespace walls, read-only
#      Parley state and zero mutations in values keep the live score pure.
#      Only five private MCA scripted GUIs may manage twelve player variables
#      and six player lists, including candidate references, with full cleanup.
#
#   8  LOAD/HOVER CONTRACT - MCA declares one derived marriage-only row
#      and never redeclares widget_character_list_item; its frozen GUI
#      instantiates the derived type three times. All four score owners and their
#      native popup children carry the exact ValueBreakdown context. Vanilla
#      and AGOT retain the character_relation seam. The only script race is
#      intentional: formula component defaults sort before the AGOT formulas.
#      Scalar-zero stubs are forbidden: the measured CK3 1.19 runtime kept the
#      zero instead of the later formula; block defaults restored the +30.
#      This source check does not replace the nonzero in-game hover test.
#
#   9  THE STORE-GUARD CHECK - every ITERATOR (`every_*` / `random_*` /
#      `ordered_*`, list or engine; `random_list` excluded as a weighted
#      choice) that MUTATES a walked member's variables must carry a `limit`
#      containing `exists = var:`, either on the walk or on an inner `if`
#      around the removals. Added 2026-08-24, and it is the only check here
#      born from a measured storm rather than from a hazard: SIX shipped
#      copies of one no-limit walk produced 576 `Error: remove_variable effect
#      [ This scope does not have variables ]` lines in a single 20-minute run.
#      WIDENED THE SAME DAY, because as first written it was scoped to
#      variable lists and therefore could not see the family's LARGEST
#      instance - an engine iterator, `every_living_character` in the core's
#      uninstall decision, projecting ~665,000 error lines from one click.
#      The rule was always about a mutation on a walked member; the kind of
#      walk was never part of it.
#      THE MECHANISM, so nobody weakens this check by re-reading the old
#      lesson: unguarded remove_variable is silent ONLY where the scope is
#      guaranteed to carry at least one variable. That is what vanilla does -
#      GAME\common\scripted_effects\00_scripted_effects.txt:61-62 leaves the
#      two GUARANTEED loan variables unguarded and wraps every OPTIONAL one
#      in its own exists = var: guard at :67-70 and :71-74 - and on a scope
#      with NO store at all the effect is an ENGINE ERROR. Vanilla ships the
#      guarded walk too: GAME\events\religion_events\holy_order_events.txt
#      :293-296 and GAME\events\death_events\death_management_events.txt
#      :145-153. A timed stamp (days = N) makes the empty case the NORMAL
#      case, not the edge case, which is why no prefix, key-set or twin check
#      could ever see this class - the names were all correct.
#      WHAT COUNTS AS A MUTATION: remove_variable / clear_variable_list /
#      change_variable, inline OR reached through a tnt_*_effect call (the
#      call form is why a naive grep missed the core's own instance - its
#      removes sit one level down, in tnt_wed_strip_effect). The mutating-
#      effect set is computed transitively over every top-level definition in
#      all three trees. set_variable and add_to_variable_list are DELIBERATELY
#      NOT mutations here: they CREATE the store, so they cannot throw on an
#      empty scope.
#      WHAT IS NOT THE MEMBER: rows inside a `scope:<name> = { }` or
#      `var:<name> ?= { }` re-scope are excluded, because a named saved scope
#      is by definition not the member being walked. That exclusion is not a
#      convenience - it is what keeps the one legitimate shipped shape clean,
#      tnt_39_autobalance.txt's lumpy rungs, which walk a TITLE list and write
#      every variable on the player they carry in by name.
#      Measured at introduction: 47 variable-list walks in the family, 10 of
#      them mutating, 10 guarded, 0 offenders.
#
# WHAT IS SCANNED: every file in each tree except the _docs\ and .git\
# subtrees (_docs is invisible to the game - CK3 reads only common/, gui/,
# events/, localization/, gfx/ and data_binding/). descriptor.mod files are
# covered by check 5 (path collision) but exempt from checks 1-2: no house
# law governs their encoding and the launcher, not the game, reads them.
#
# THIS TOOL IS READ-ONLY. It never writes a file.
#
# Exit 0 clean / 1 any failure / 2 bad arguments.
# =============================================================================
param(
    [string]$CoreRoot    = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    [string]$McaRoot     = '',
    [Alias('ForkRoot')]
    [string]$AdapterRoot    = '',
    [string]$VanillaRoot = 'D:\SteamLibrary\steamapps\common\Crusader Kings III\game',
    [string]$AgotRoot    = 'D:\SteamLibrary\steamapps\workshop\content\1158310\2962333032'
)

$CoreRoot = $CoreRoot.TrimEnd('\')
if ($McaRoot -eq '')  { $McaRoot  = Join-Path (Split-Path -Parent $CoreRoot) 'marriage_calc_assistant' }
if ($AdapterRoot -eq '') { $AdapterRoot = Join-Path (Split-Path -Parent $CoreRoot) 'agot_marriage_calc_assistant' }
$McaRoot     = $McaRoot.TrimEnd('\')
$AdapterRoot    = $AdapterRoot.TrimEnd('\')
$VanillaRoot = $VanillaRoot.TrimEnd('\')
$AgotRoot    = $AgotRoot.TrimEnd('\')

if (-not (Test-Path (Join-Path $CoreRoot 'common\scripted_effects\tnt_1f_addon_hooks.txt'))) { Write-Host "BAD CoreRoot (no addon-hooks stub file): $CoreRoot"; exit 2 }
if (-not (Test-Path (Join-Path $McaRoot 'common')))     { Write-Host "BAD McaRoot: $McaRoot";  exit 2 }
if (-not (Test-Path (Join-Path $AdapterRoot 'common')))    { Write-Host "BAD AdapterRoot: $AdapterRoot"; exit 2 }
if (-not (Test-Path (Join-Path $VanillaRoot 'common'))) { Write-Host "BAD VanillaRoot: $VanillaRoot"; exit 2 }
if (-not (Test-Path (Join-Path $AgotRoot 'gui\shared\lists.gui'))) { Write-Host "BAD AgotRoot: $AgotRoot"; exit 2 }

# The three trees, in the fixed report order.
$TREES = @(
    @{ Tag = 'CORE'; Root = $CoreRoot },
    @{ Tag = 'MCA';  Root = $McaRoot  },
    @{ Tag = 'AGOT'; Root = $AdapterRoot }
)

# --- THE FIVE SEAM HOOKS (tnt_1f_addon_hooks.txt is their single home) -------
$HOOKS    = @('tnt_ma_grade_stamp_effect', 'tnt_ma_grade_strip_p_effect', 'tnt_ma_grade_strip_r_effect', 'tnt_ma_grade_strip_all_effect', 'tnt_ma_grade_order_effect')
$STUBFILE = 'tnt_1f_addon_hooks.txt'

# --- LEGACY PUBLIC PARLEY STATE (writers remain in the core) -----------------
# MCA's marriage-only GUI no longer reads tnt_open; the full recorded set here
# protects compatibility without pretending the current scorer mutates it.
$SEAM_STATE = @('tnt_list_spouse_p', 'tnt_list_spouse_r', 'tnt_open', 'tnt_partner')

# --- CENTRALIZED MCA V3.0.1 / AGOT V2.2 ARCHITECTURE INVENTORY ---------------
# One edit here adjusts the gate if the MCA owner intentionally changes the
# shipped inventory. README.md is included because this is the exact shipped
# tree, not only the directories CK3 parses.
$LANGS = @('english', 'french', 'german', 'japanese', 'korean', 'polish', 'russian', 'simp_chinese', 'spanish')
$ADAPTER_COMPONENT_VALUES = @(
    'tnt_ma_adapter_p_c1_value', 'tnt_ma_adapter_p_c2_value',
    'tnt_ma_adapter_p_c3_value', 'tnt_ma_adapter_p_c4_value',
    'tnt_ma_adapter_r_c1_value', 'tnt_ma_adapter_r_c2_value',
    'tnt_ma_adapter_r_c3_value', 'tnt_ma_adapter_r_c4_value'
)
$MCA_ADAPTER_VALUES = @(
    $ADAPTER_COMPONENT_VALUES
    'tnt_ma_adapter_p_value'
    'tnt_ma_adapter_r_value'
    'tnt_ma_alliance_base_value'
)
$AGOT_OVERRIDE_VALUES = @(
    'tnt_ma_adapter_p_c1_value',
    'tnt_ma_adapter_r_c1_value', 'tnt_ma_adapter_r_c2_value',
    'tnt_ma_adapter_r_c3_value', 'tnt_ma_adapter_r_c4_value',
    'tnt_ma_alliance_base_value'
)
$MCA_CONTEXT_NAMES = @('tnt_gr_me', 'tnt_gr_p', 'tnt_gr_side', 'tnt_sp_one')
$AGOT_CONTEXT_NAMES = @()
$MCA_NON_NAMESPACE_NAMES = @('tnt_spouse_grade_value')
$MCA_GUI_VALUE_NAMES = @(
    'tnt_ma_grade_p_available_value', 'tnt_ma_grade_r_available_value',
    'tnt_ma_grade_p_value', 'tnt_ma_grade_p_alliance_value',
    'tnt_ma_grade_r_value', 'tnt_ma_grade_r_alliance_value'
)
$MCA_SORT_GUI_DEFS = @('tnt_ma_sort_start', 'tnt_ma_sort_collect', 'tnt_ma_sort_finalize', 'tnt_ma_sort_clear', 'tnt_ma_sort_context_valid')
$MCA_CAPTURE_VALUES = @('tnt_ma_sort_p_capture_value', 'tnt_ma_sort_p_alliance_capture_value', 'tnt_ma_sort_r_capture_value', 'tnt_ma_sort_r_alliance_capture_value')
$MCA_COMPAT_SG_VALUES = @(
    'tnt_ma_sg_r_c1_value', 'tnt_ma_sg_r_c2_value',
    'tnt_ma_sg_r_c3_value', 'tnt_ma_sg_r_c4_value',
    'tnt_ma_sg_p_c1_value', 'tnt_ma_sg_p_c2_value',
    'tnt_ma_sg_p_c3_value', 'tnt_ma_sg_p_c4_value'
)
$MCA_BENEFIT_ROWS = @(
    [pscustomobject]@{ Value = 'tnt_ma_skill_value';   Loc = 'tnt_ma_grade_skill' },
    [pscustomobject]@{ Value = 'tnt_ma_age_value';     Loc = 'tnt_ma_grade_age' },
    [pscustomobject]@{ Value = 'tnt_ma_dynasty_value'; Loc = 'tnt_ma_grade_dynasty' },
    [pscustomobject]@{ Value = 'tnt_ma_claim_value';   Loc = 'tnt_ma_grade_claim' },
    [pscustomobject]@{ Value = 'tnt_ma_genetic_value'; Loc = 'tnt_ma_grade_genetic' }
)
$MCA_BENEFIT_VALUES = @($MCA_BENEFIT_ROWS | ForEach-Object { $_.Value })
$MCA_BENEFIT_LOCS = @($MCA_BENEFIT_ROWS | ForEach-Object { $_.Loc })

$MCA_RUNTIME_FILES = @(
    'descriptor.mod',
    'README.md',
    'thumbnail.png',
    'common\script_values\tnt_ma_00_adapter_defaults.txt',
    'common\script_values\tnt_ma_52_grade.txt',
    'common\script_values\tnt_ma_sort_capture.txt',
    'common\scripted_guis\tnt_ma_sort.txt',
    'gui\interaction_marriage.gui',
    'gui\tnt_ma_character_list_item.gui'
)
$AGOT_RUNTIME_FILES = @(
    'descriptor.mod',
    'thumbnail.png',
    'common\script_values\zz_agot_ma_adapter_values.txt'
)
foreach ($lang in $LANGS) {
    $MCA_RUNTIME_FILES += "localization\$lang\tnt_ma_l_$lang.yml"
    $AGOT_RUNTIME_FILES += "localization\$lang\agot_ma_l_$lang.yml"
}

$MCA_LOC_KEYS = @(
    'tnt_ma_grade_title', 'tnt_ma_grade_help',
    'tnt_ma_grade_p_c1', 'tnt_ma_grade_p_c2', 'tnt_ma_grade_p_c3', 'tnt_ma_grade_p_c4',
    'tnt_ma_grade_r_c1', 'tnt_ma_grade_r_c2', 'tnt_ma_grade_r_c3', 'tnt_ma_grade_r_c4',
    'tnt_ma_grade_alliance'
    $MCA_BENEFIT_LOCS
    'tnt_ma_sort_score_button', 'tnt_ma_sort_native_button', 'tnt_ma_sort_help',
    'tnt_ma_sort_collecting', 'tnt_ma_sort_active', 'tnt_ma_sort_failed'
)
$AGOT_LOC_KEYS = @(
    'tnt_ma_adapter_p_c1',
    'tnt_ma_adapter_r_c1', 'tnt_ma_adapter_r_c2',
    'tnt_ma_adapter_r_c3', 'tnt_ma_adapter_r_c4'
)

$MCA_VALUE_DEFS = @(
    $MCA_ADAPTER_VALUES
    $MCA_CAPTURE_VALUES
    'tnt_ma_grade_p_available_value', 'tnt_ma_grade_r_available_value'
    $MCA_COMPAT_SG_VALUES
    'tnt_ma_ally_ratio_value', 'tnt_ma_ally_worth_value'
    $MCA_BENEFIT_VALUES
    'tnt_ma_grade_p_raw_value', 'tnt_ma_grade_r_raw_value',
    'tnt_ma_grade_p_value', 'tnt_ma_grade_p_alliance_value',
    'tnt_ma_grade_r_value', 'tnt_ma_grade_r_alliance_value',
    'tnt_spouse_grade_value'
)

# =============================================================================
# helpers
# =============================================================================

# Files of a tree, minus _docs\ and .git\ (invisible to the game).
function Get-TreeFiles([string]$root, [string[]]$exts) {
    $out = New-Object System.Collections.Generic.List[object]
    foreach ($f in (Get-ChildItem -LiteralPath $root -Recurse -File)) {
        $rel = $f.FullName.Substring($root.Length + 1)
        if ($rel -match '^(_docs|\.git)(\\|$)') { continue }
        if ($exts.Count -gt 0 -and ($exts -notcontains $f.Extension.ToLower())) { continue }
        [void]$out.Add([pscustomobject]@{ File = $f; Rel = $rel })
    }
    return ,$out
}

# Brace-counting form: quoted strings emptied FIRST, then the comment cut.
function Strip-Code([string]$line) {
    $code = [regex]::Replace($line, '"[^"]*"', '""')
    $i = $code.IndexOf('#')
    if ($i -ge 0) { $code = $code.Substring(0, $i) }
    return $code
}

# Token-scanning form: cut the comment but KEEP quoted strings, because
# .gui data functions and loc values carry live tnt_ names inside quotes.
function Strip-CommentKeepQuotes([string]$line) {
    $inq = $false
    for ($i = 0; $i -lt $line.Length; $i++) {
        $ch = $line[$i]
        if ($ch -eq '"') { $inq = -not $inq }
        elseif ($ch -eq '#' -and -not $inq) { return $line.Substring(0, $i) }
    }
    return $line
}

# First-divergence report for a pure name comparison, printed literally.
function Describe-Order([string]$a, [string]$b) {
    $n = [Math]::Min($a.Length, $b.Length)
    for ($i = 0; $i -lt $n; $i++) {
        if ($a[$i] -cne $b[$i]) {
            return ("divergence at char {0}: '{1}' 0x{2:X2} vs '{3}' 0x{4:X2}" -f ($i + 1), $a[$i], [int][char]$a[$i], $b[$i], [int][char]$b[$i])
        }
    }
    return ("strict prefix: the {0}-char name sorts first" -f $n)
}

# Top-level `name = value` assignments of every .txt under a folder, with
# sites. This deliberately accepts BOTH block and scalar script values; a
# block-only parser would miss scalar legacy values and the alliance base.
# $skipDirs: directory leaf names whose files are not collected (on_action
# MERGES across mods, so its names never race and never override).
function Get-TopLevelDefs([string]$root, [string]$subdir, [string[]]$skipDirs) {
    $defs = @{}
    $dir = Join-Path $root $subdir
    if (-not (Test-Path $dir)) { return $defs }
    foreach ($f in (Get-ChildItem -LiteralPath $dir -Recurse -File -Filter *.txt)) {
        $leaf = Split-Path -Leaf (Split-Path -Parent $f.FullName)
        if ($skipDirs -contains $leaf) { continue }
        $rel = $f.FullName.Substring($root.Length + 1)
        $depth = 0; $ln = 0
        foreach ($L in [System.IO.File]::ReadAllLines($f.FullName)) {
            $ln++
            $code = Strip-Code $L
            if ($depth -eq 0 -and $code -match '^\s*([A-Za-z0-9_]+)\s*=') {
                $n = $Matches[1]
                if (-not $defs.ContainsKey($n)) { $defs[$n] = New-Object System.Collections.Generic.List[string] }
                [void]$defs[$n].Add(("{0}:{1}" -f $rel, $ln))
            }
            $depth += ([regex]::Matches($code, '\{')).Count - ([regex]::Matches($code, '\}')).Count
        }
    }
    return $defs
}

# The same parser for one exact file, returned as a name -> sites map.
function Get-FileTopLevelDefs([string]$path, [string]$label) {
    $defs = @{}
    $depth = 0; $ln = 0
    foreach ($L in [System.IO.File]::ReadAllLines($path)) {
        $ln++
        $code = Strip-Code $L
        if ($depth -eq 0 -and $code -match '^\s*([A-Za-z0-9_]+)\s*=') {
            $n = $Matches[1]
            if (-not $defs.ContainsKey($n)) { $defs[$n] = New-Object System.Collections.Generic.List[string] }
            [void]$defs[$n].Add(("{0}:{1}" -f $label, $ln))
        }
        $depth += ([regex]::Matches($code, '\{')).Count - ([regex]::Matches($code, '\}')).Count
    }
    return $defs
}

# Canonical active code for the two tiny adapter contract files. Comments and
# whitespace are not load-bearing; token order, nesting and literals are.
function Get-CanonicalActiveCode([string]$path) {
    $parts = New-Object System.Collections.Generic.List[string]
    foreach ($L in [System.IO.File]::ReadAllLines($path)) {
        $code = Strip-CommentKeepQuotes $L
        $code = [regex]::Replace($code, '\s+', '')
        if ($code -ne '') { [void]$parts.Add($code) }
    }
    return ($parts -join '')
}

# Canonical code for one exact block-valued top-level definition. This keeps
# later shape assertions tied to the owning wrapper rather than merely finding
# the right tokens somewhere else in the same database file.
function Get-CanonicalTopLevelDefinition([string]$path, [string]$name) {
    $parts = New-Object System.Collections.Generic.List[string]
    $depth = 0
    $capture = $false
    foreach ($L in [System.IO.File]::ReadAllLines($path)) {
        $countCode = Strip-Code $L
        if (-not $capture -and $depth -eq 0 -and $countCode -match ('^\s*' + [regex]::Escape($name) + '\s*=\s*\{')) {
            $capture = $true
        }
        if ($capture) {
            $active = Strip-CommentKeepQuotes $L
            $active = [regex]::Replace($active, '\s+', '')
            if ($active -ne '') { [void]$parts.Add($active) }
        }
        $depth += ([regex]::Matches($countCode, '\{')).Count - ([regex]::Matches($countCode, '\}')).Count
        if ($capture -and $depth -eq 0) { return ($parts -join '') }
    }
    return ''
}

# Exact shipped-file inventory, excluding only .git and _docs metadata.
function Get-ShippedRelPaths([string]$root) {
    $paths = @()
    foreach ($f in (Get-ChildItem -LiteralPath $root -Recurse -File)) {
        $rel = $f.FullName.Substring($root.Length + 1)
        if ($rel -match '^(_docs|\.git)(\\|$)') { continue }
        $paths += $rel
    }
    return $paths
}

function Get-LocKeys([string]$path) {
    $keys = @()
    foreach ($L in [System.IO.File]::ReadAllLines($path)) {
        if ($L -match '^ ([A-Za-z0-9_.-]+):\d+\s+"') { $keys += $Matches[1] }
    }
    return $keys
}

function First-LineDifference([string[]]$a, [string[]]$b) {
    $n = [Math]::Min($a.Count, $b.Count)
    for ($i = 0; $i -lt $n; $i++) { if ($a[$i] -cne $b[$i]) { return ($i + 1) } }
    if ($a.Count -ne $b.Count) { return ($n + 1) }
    return 0
}

# Shared fail-closed v2.3 patch proof. This pins the reviewed upstream baseline
# and reconstructs the functional GUI from an approved patch, not from itself.
foreach ($helper in @('tnt_mca_frozen_contract.ps1', 'tnt_mca_sort_contract.ps1')) {
    $helperPath = Join-Path $PSScriptRoot $helper
    if (-not (Test-Path -LiteralPath $helperPath)) { Write-Host "Missing gate helper: $helperPath"; exit 2 }
    . $helperPath
}

$SUMMARY = New-Object System.Collections.Generic.List[object]
function Close-Check([string]$name, [int]$failCount) {
    [void]$SUMMARY.Add([pscustomobject]@{ Check = $name; Fails = $failCount })
    if ($failCount -eq 0) { Write-Host ("  => PASS") } else { Write-Host ("  => FAIL ({0} offender(s))" -f $failCount) }
    Write-Host ""
}

Write-Host "tnt_family_gate - the mechanical gate over all three trees"
Write-Host ("  CORE    : {0}" -f $CoreRoot)
Write-Host ("  MCA     : {0}" -f $McaRoot)
Write-Host ("  AGOT    : {0}" -f $AdapterRoot)
Write-Host ("  VANILLA : {0}" -f $VanillaRoot)
Write-Host ("  AGOT UP : {0}" -f $AgotRoot)
Write-Host ""

# =============================================================================
# CHECK 1 - BRACE BALANCE (quotes stripped before comments; no negative dip)
# =============================================================================
Write-Host "CHECK 1 - brace balance, every .txt/.gui/.yml in every tree"
$fails = 0
foreach ($t in $TREES) {
    $files = Get-TreeFiles $t.Root @('.txt', '.yml', '.gui')
    $bad = 0
    foreach ($e in $files) {
        $depth = 0; $dipLine = 0; $ln = 0
        foreach ($L in [System.IO.File]::ReadAllLines($e.File.FullName)) {
            $ln++
            $code = Strip-Code $L
            $depth += ([regex]::Matches($code, '\{')).Count - ([regex]::Matches($code, '\}')).Count
            if ($depth -lt 0 -and $dipLine -eq 0) { $dipLine = $ln }
        }
        if ($depth -ne 0 -or $dipLine -gt 0) {
            Write-Host ("  FAIL  {0} {1}: final depth {2}, first negative dip at line {3}" -f $t.Tag, $e.Rel, $depth, $dipLine)
            $bad++
        }
    }
    Write-Host ("  {0,-4} : {1,3} files scanned, {2} brace fault(s)" -f $t.Tag, $files.Count, $bad)
    $fails += $bad
}
Close-Check "1 brace balance" $fails

# =============================================================================
# CHECK 2 - ENCODING BY EXTENSION (BOM, CR, exactly one trailing newline)
# =============================================================================
Write-Host "CHECK 2 - encoding by extension (.txt/.yml BOM, .gui no BOM, no CR, one trailing LF)"
$fails = 0
foreach ($t in $TREES) {
    $files = Get-TreeFiles $t.Root @('.txt', '.yml', '.gui')
    $bad = 0
    foreach ($e in $files) {
        $b = [System.IO.File]::ReadAllBytes($e.File.FullName)
        $ext = $e.File.Extension.ToLower()
        $hasBom  = ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)
        $wantBom = ($ext -ne '.gui')
        $crAt = 0
        for ($i = 0; $i -lt $b.Length; $i++) { if ($b[$i] -eq 0x0D) { $crAt = $i + 1; break } }
        $endsOneNl = ($b.Length -ge 1 -and $b[$b.Length - 1] -eq 0x0A -and ($b.Length -lt 2 -or $b[$b.Length - 2] -ne 0x0A))
        # V29: a SECOND BOM is not a BOM, it is three stray bytes at the head of
        # the first token, and the old test could not see it because it stopped
        # after byte 2. Measured cost of the blind spot: tnt_91_alerts.txt was
        # written with two, which is exactly the shape that makes
        # pdx_persistent_reader report "Unexpected token: =" against the first
        # entry and drop the whole file. It arises whenever a tool writes an
        # already-BOM'd string through an encoder that adds its own.
        $doubleBom = ($b.Length -ge 6 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF -and
                      $b[3] -eq 0xEF -and $b[4] -eq 0xBB -and $b[5] -eq 0xBF)
        if ($doubleBom)           { Write-Host ("  FAIL  {0} {1}: DOUBLE UTF-8 BOM - the file will not parse; strip the second three bytes" -f $t.Tag, $e.Rel); $bad++ }
        if ($hasBom -ne $wantBom) { Write-Host ("  FAIL  {0} {1}: BOM {2}, extension {3} wants BOM {4}" -f $t.Tag, $e.Rel, $hasBom, $ext, $wantBom); $bad++ }
        if ($crAt -gt 0)          { Write-Host ("  FAIL  {0} {1}: CR byte 0x0D at offset {2}" -f $t.Tag, $e.Rel, ($crAt - 1)); $bad++ }
        if (-not $endsOneNl)      { Write-Host ("  FAIL  {0} {1}: does not end with exactly one 0x0A" -f $t.Tag, $e.Rel); $bad++ }
    }
    Write-Host ("  {0,-4} : {1,3} files scanned, {2} encoding fault(s)" -f $t.Tag, $files.Count, $bad)
    $fails += $bad
}
Close-Check "2 encoding" $fails

# =============================================================================
# CHECK 3 - ASCII PURITY OF THE FENCED FILES (house law 8)
#
# V29: the fence is FOUR files, not three, and the fourth earned its place the
# expensive way. common\important_actions\tnt_91_alerts.txt carried 26 Cyrillic
# characters in one comment and the ENTIRE FILE failed to load - one line in the
# log ("Unexpected token: =, near line: 124", pointing at the entry declaration
# rather than the comment), the alert simply did not exist in game, and a whole
# playtest was spent discovering it. The list is therefore a RELATIVE PATH list
# now: the first three live in common\scripted_effects, the fourth does not.
# =============================================================================
Write-Host "CHECK 3 - ASCII purity of the fenced files (0 non-ASCII bytes after the BOM)"
$fails = 0
foreach ($rel in @('common\scripted_effects\tnt_37_ai_offer.txt',
                   'common\scripted_effects\tnt_39_autobalance.txt',
                   'common\scripted_effects\tnt_3b_log.txt',
                   'common\important_actions\tnt_91_alerts.txt')) {
    $name = Split-Path $rel -Leaf
    $p = Join-Path $CoreRoot $rel
    if (-not (Test-Path $p)) { Write-Host ("  FAIL  CORE {0}: file missing" -f $name); $fails++; continue }
    $b = [System.IO.File]::ReadAllBytes($p)
    $bad = 0; $firstAt = -1
    for ($i = 3; $i -lt $b.Length; $i++) { if ($b[$i] -gt 0x7F) { $bad++; if ($firstAt -lt 0) { $firstAt = $i } } }
    if ($bad -gt 0) { Write-Host ("  FAIL  CORE {0}: {1} non-ASCII byte(s), first at offset {2}" -f $name, $bad, $firstAt); $fails++ }
    else            { Write-Host ("  CORE {0} : 0 non-ASCII bytes after the BOM" -f $name) }
}
Close-Check "3 ASCII fence (4 files)" $fails

# =============================================================================
# CHECK 4 - LOCALIZATION: THE NINE-LANGUAGE FAN WITHIN EACH MOD
# =============================================================================
# The language list is a LITERAL, by design. SOURCE: the shipped language
# folders under <VanillaRoot>\localization on the vanilla 1.19 install,
# minus 'jomini' (engine plumbing, not a language - it carries no
# <stem>_l_jomini.yml fan of its own). If Paradox adds a language, this one
# line changes in the centralized inventory and the whole fan follows it.

# Concept links may legitimately differ between languages in FORM while they
# must agree in SUBSTANCE: english [alliances|E] against a translated
# [Concept('alliance', '...')|E] is the SAME link - the one-argument form
# names the concept (or any of its aliases) and renders its stock name, the
# two-argument form names it and supplies translated display text. So the
# canonical key behind either form comes from vanilla's own alias table
# (common\game_concepts, the alias = { ... } blocks; 'alliances' ->
# 'alliance' is the shipped instance that motivated this). Unknown keys pass
# through unresolved - two sides using the same unknown key still compare
# equal, so an AGOT-only concept in the adapter's loc costs nothing.
$CONCEPT_ALIAS = New-Object System.Collections.Hashtable   # case-sensitive on purpose
$gcDir = Join-Path $VanillaRoot 'common\game_concepts'
if (-not (Test-Path $gcDir)) { Write-Host ("  NOTE  vanilla game_concepts folder not found at {0} - concept aliases unresolved this run" -f $gcDir) }
$gcFiles = @()
if (Test-Path $gcDir) { $gcFiles = @(Get-ChildItem -LiteralPath $gcDir -File -Filter *.txt) }
foreach ($f in $gcFiles) {
    $depth = 0; $concept = ''; $inAlias = $false
    foreach ($L in [System.IO.File]::ReadAllLines($f.FullName)) {
        $code = Strip-Code $L
        if ($depth -eq 0 -and $code -match '^([A-Za-z0-9_]+)\s*=\s*\{') {
            $concept = $Matches[1]
            if (-not $CONCEPT_ALIAS.ContainsKey($concept)) { $CONCEPT_ALIAS[$concept] = $concept }
        }
        if ($concept -ne '' -and $code -match 'alias\s*=\s*\{') { $inAlias = $true }
        if ($inAlias) {
            $seg = $code
            if ($seg -match 'alias\s*=\s*\{(.*)$') { $seg = $Matches[1] }
            $cut = $seg.IndexOf('}')
            if ($cut -ge 0) { $seg = $seg.Substring(0, $cut); $inAlias = $false }
            foreach ($m in [regex]::Matches($seg, '[A-Za-z0-9_]+')) { $CONCEPT_ALIAS[$m.Value] = $concept }
        }
        $depth += ([regex]::Matches($code, '\{')).Count - ([regex]::Matches($code, '\}')).Count
        if ($depth -le 0) { $depth = 0; $concept = ''; $inAlias = $false }
    }
}

# One [..] token, normalized for cross-language comparison: the trailing
# |format is stripped (a translation may legitimately re-case with |l or |U),
# whitespace is collapsed, and both concept-link forms reduce to
# concept:<canonical key>. Everything else keeps its full call skeleton, so a
# mistranslated datafunction argument or a dropped token still breaks parity.
function Normalize-LocToken([string]$tok) {
    $body = $tok.Substring(1, $tok.Length - 2)
    $isConceptFmt = ($body -match '\|[A-Za-z0-9%+=*\-]*[eE][A-Za-z0-9%+=*\-]*$')
    $body = $body -replace '\|[A-Za-z0-9%+=*\-]*$', ''
    $body = $body -replace '\s+', ''
    $ck = $null
    if ($body -match "^Concept\('([A-Za-z0-9_]+)'.*\)$") { $ck = $Matches[1] }
    elseif ($isConceptFmt -and $body -match '^[A-Za-z0-9_]+$') { $ck = $body }
    if ($null -ne $ck) {
        if ($CONCEPT_ALIAS.ContainsKey($ck)) { $ck = $CONCEPT_ALIAS[$ck] }
        return ('concept:' + $ck)
    }
    return $body
}

# The MULTISET of live tokens in one loc value: normalized [..] datafunction
# tokens plus $key$ references verbatim. Case-sensitive by construction.
function Get-LocTokenMultiset([string]$val) {
    $ms = New-Object System.Collections.Hashtable
    foreach ($m in [regex]::Matches($val, '\[[^\[\]]*\]')) {
        $n = Normalize-LocToken $m.Value
        if (-not $ms.ContainsKey($n)) { $ms[$n] = 0 }
        $ms[$n] = $ms[$n] + 1
    }
    foreach ($m in [regex]::Matches($val, '\$[^$]*\$')) {
        $n = $m.Value
        if (-not $ms.ContainsKey($n)) { $ms[$n] = 0 }
        $ms[$n] = $ms[$n] + 1
    }
    return $ms   # a hashtable is one pipeline object; no wrapping comma
}

# Parse one loc file: bytes (BOM / CR / one trailing LF), the l_<lang>:
# header, the strict ' key:0 "value"' line shape, duplicate keys, and the
# per-value #markup balance. Prints its own FAIL lines; returns the key map.
function Read-LocFile([string]$tag, [string]$rel, [string]$full, [string]$lang) {
    $f = 0
    $b = [System.IO.File]::ReadAllBytes($full)
    if (-not ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)) { Write-Host ("  FAIL  {0} {1}: no UTF-8 BOM - CK3 silently ignores the whole file" -f $tag, $rel); $f++ }
    $crAt = -1
    for ($i = 0; $i -lt $b.Length; $i++) { if ($b[$i] -eq 0x0D) { $crAt = $i; break } }
    if ($crAt -ge 0) { Write-Host ("  FAIL  {0} {1}: CR byte 0x0D at offset {2}" -f $tag, $rel, $crAt); $f++ }
    $endsOneNl = ($b.Length -ge 1 -and $b[$b.Length - 1] -eq 0x0A -and ($b.Length -lt 2 -or $b[$b.Length - 2] -ne 0x0A))
    if (-not $endsOneNl) { Write-Host ("  FAIL  {0} {1}: does not end with exactly one trailing 0x0A" -f $tag, $rel); $f++ }
    $map  = New-Object System.Collections.Hashtable   # key -> value (case-sensitive)
    $line = New-Object System.Collections.Hashtable   # key -> line number
    $ln = 0
    foreach ($L in [System.IO.File]::ReadAllLines($full)) {
        $ln++
        if ($ln -eq 1) {
            if ($L.Trim() -ne ("l_{0}:" -f $lang)) { Write-Host ("  FAIL  {0} {1}: header line 1 is [{2}], expected l_{3}:" -f $tag, $rel, $L.Trim(), $lang); $f++ }
            continue
        }
        if ($L.Trim() -eq '') { continue }
        if ($L.TrimStart().StartsWith('#')) { continue }
        if ($L -match '^(\s*)([A-Za-z0-9_.\-]+):(\d*)(\s+)"(.*)"(\s*)$') {
            $k = $Matches[2]; $v = $Matches[5]
            if ($Matches[1] -ne ' ')  { Write-Host ("  FAIL  {0} {1}:{2}: key {3} has {4} leading whitespace char(s), law 9 wants exactly one space" -f $tag, $rel, $ln, $k, $Matches[1].Length); $f++ }
            if ($Matches[3] -eq '')   { Write-Host ('  FAIL  {0} {1}:{2}: key {3} has no version number - the shape is key:0 "value"' -f $tag, $rel, $ln, $k); $f++ }
            if ($Matches[4] -ne ' ')  { Write-Host ("  FAIL  {0} {1}:{2}: key {3} wants exactly one space before the quoted value" -f $tag, $rel, $ln, $k); $f++ }
            if ($Matches[6] -ne '')   { Write-Host ("  FAIL  {0} {1}:{2}: key {3} has trailing whitespace after the closing quote" -f $tag, $rel, $ln, $k); $f++ }
            if ($map.ContainsKey($k)) { Write-Host ("  FAIL  {0} {1}:{2}: duplicate key {3} (first at line {4})" -f $tag, $rel, $ln, $k, $line[$k]); $f++ }
            else { $map[$k] = $v; $line[$k] = $ln }
            $closers = ([regex]::Matches($v, '#!')).Count
            $openers = ([regex]::Matches($v, '#')).Count - $closers
            if ($openers -ne $closers) { Write-Host ("  FAIL  {0} {1}:{2}: key {3} markup imbalance - {4} '#' opener(s) vs {5} '#!' closer(s)" -f $tag, $rel, $ln, $k, $openers, $closers); $f++ }
        }
        else { Write-Host ('  FAIL  {0} {1}:{2}: not the '' key:0 "value"'' shape: [{3}]' -f $tag, $rel, $ln, $L.Trim()); $f++ }
    }
    if ($ln -eq 0) { Write-Host ("  FAIL  {0} {1}: file is empty - no l_{2}: header, no keys" -f $tag, $rel, $lang); $f++ }
    return [pscustomobject]@{ Map = $map; Line = $line; Fails = $f }
}

Write-Host "CHECK 4 - localization: the nine-language fan per mod (existence, header, shape, key sets, token parity, markup)"
$fails = 0
foreach ($t in $TREES) {
    # assign FIRST, pipe the variable SECOND: piping the function call itself
    # hands Where-Object the whole wrapped List as ONE object (PS 5.1 unrolls
    # one level only) and every $_.Rel downstream becomes an Object[].
    $treeYmls = Get-TreeFiles $t.Root @('.yml')
    $ymls = @($treeYmls | Where-Object { $_.Rel -match '^localization\\' })
    $engRefs = @($ymls | Where-Object { $_.Rel -match '^localization\\english\\[^\\]+_l_english\.yml$' })
    if ($engRefs.Count -lt 1) {
        Write-Host ("  FAIL  {0}: no localization\english\<stem>_l_english.yml - no reference to derive the fan from" -f $t.Tag)
        $fails++
    }
    # the full expected fan: every english stem crossed with every language
    $expected = @{}
    foreach ($e in $engRefs) {
        $stem = (Split-Path -Leaf $e.Rel) -replace '_l_english\.yml$', ''
        foreach ($lang in $LANGS) {
            $expected[("localization\{0}\{1}_l_{0}.yml" -f $lang, $stem)] = $true
        }
    }
    foreach ($y in $ymls) {
        if (-not $expected.ContainsKey($y.Rel)) {
            Write-Host ("  FAIL  {0} {1}: unexpected loc file - not <stem>_l_<lang>.yml under a shipped english stem and a vanilla language folder" -f $t.Tag, $y.Rel)
            $fails++
        }
    }
    foreach ($e in $engRefs) {
        $stem = (Split-Path -Leaf $e.Rel) -replace '_l_english\.yml$', ''
        $eng = Read-LocFile $t.Tag $e.Rel $e.File.FullName 'english'
        $fails += $eng.Fails
        Write-Host ("  {0,-4} : {1,-34} REFERENCE - {2} keys, {3} file fault(s)" -f $t.Tag, ($stem + '_l_english.yml'), $eng.Map.Count, $eng.Fails)
        foreach ($lang in $LANGS) {
            if ($lang -eq 'english') { continue }
            $rel = "localization\{0}\{1}_l_{0}.yml" -f $lang, $stem
            $hitExact = @($ymls | Where-Object { $_.Rel -ceq $rel })
            if ($hitExact.Count -eq 0) {
                $hitCi = @($ymls | Where-Object { $_.Rel -eq $rel })
                if ($hitCi.Count -gt 0) {
                    Write-Host ("  FAIL  {0} {1}: exists only with different CASE ({2}) - the Linux build's filesystem is case-sensitive" -f $t.Tag, $rel, $hitCi[0].Rel)
                }
                else {
                    Write-Host ("  FAIL  {0} {1}: language file MISSING - the fan ships all nine vanilla languages" -f $t.Tag, $rel)
                }
                $fails++
                continue
            }
            $tr = Read-LocFile $t.Tag $rel $hitExact[0].File.FullName $lang
            $fails += $tr.Fails
            # (c) KEY-SET IDENTITY against the english reference
            $missing = @($eng.Map.Keys | Where-Object { -not $tr.Map.ContainsKey($_) } | Sort-Object)
            $extra   = @($tr.Map.Keys  | Where-Object { -not $eng.Map.ContainsKey($_) } | Sort-Object)
            foreach ($k in $missing) { Write-Host ("  FAIL  {0} {1}: key {2} MISSING (english has it at {3}:{4})" -f $t.Tag, $rel, $k, $e.Rel, $eng.Line[$k]); $fails++ }
            foreach ($k in $extra)   { Write-Host ("  FAIL  {0} {1}:{2}: key {3} EXTRA - not in the english key set" -f $t.Tag, $rel, $tr.Line[$k], $k); $fails++ }
            # (d) TOKEN PARITY per shared key, order-free multiset equality
            $tokFails = 0
            foreach ($k in @($eng.Map.Keys | Sort-Object)) {
                if (-not $tr.Map.ContainsKey($k)) { continue }
                $msE = Get-LocTokenMultiset $eng.Map[$k]
                $msT = Get-LocTokenMultiset $tr.Map[$k]
                $diff = New-Object System.Collections.Generic.List[string]
                foreach ($tok in @($msE.Keys | Sort-Object)) {
                    $c = 0; if ($msT.ContainsKey($tok)) { $c = $msT[$tok] }
                    if ($c -ne $msE[$tok]) { [void]$diff.Add(("{0} english x{1} vs x{2}" -f $tok, $msE[$tok], $c)) }
                }
                foreach ($tok in @($msT.Keys | Sort-Object)) {
                    if (-not $msE.ContainsKey($tok)) { [void]$diff.Add(("{0} english x0 vs x{1}" -f $tok, $msT[$tok])) }
                }
                if ($diff.Count -gt 0) {
                    Write-Host ("  FAIL  {0} {1}:{2}: key {3} TOKEN PARITY broken: {4}" -f $t.Tag, $rel, $tr.Line[$k], $k, ($diff -join ' ; '))
                    $tokFails++
                }
            }
            $fails += $tokFails
            Write-Host ("  {0,-4} : {1,-34} {2} keys = english {3}, {4} missing / {5} extra, {6} token fault(s), {7} file fault(s)" -f $t.Tag, ($stem + '_l_' + $lang + '.yml'), $tr.Map.Count, $eng.Map.Count, $missing.Count, $extra.Count, $tokFails, $tr.Fails)
        }
    }
}
Close-Check "4 loc nine-lang fan" $fails

# =============================================================================
# CHECK 5 - VANILLA PATH COLLISIONS: ONE MEASURED MCA GUI EXCEPTION
# =============================================================================
Write-Host "CHECK 5 - vanilla path collisions (core/AGOT zero; MCA one reviewed functional GUI patch)"
$fails = 0
$mcaCopyMeasure = Measure-McaMarriageCopy (Join-Path $McaRoot 'gui\interaction_marriage.gui') (Join-Path $VanillaRoot 'gui\interaction_marriage.gui')
$allowedMcaCollision = 'gui\interaction_marriage.gui'
$allowedSeen = 0
foreach ($t in $TREES) {
    $files = Get-TreeFiles $t.Root @()
    $bad = 0
    foreach ($e in $files) {
        if (-not (Test-Path -LiteralPath (Join-Path $VanillaRoot $e.Rel))) { continue }
        if ($t.Tag -eq 'MCA' -and $e.Rel -ceq $allowedMcaCollision) {
            $allowedSeen++
            $copyClean = ($mcaCopyMeasure.Passed -and $mcaCopyMeasure.Sites.Count -eq 3 -and $mcaCopyMeasure.Tokens -eq 3 -and $mcaCopyMeasure.FirstDiff -eq 0)
            if ($copyClean) {
                Write-Host ("  ALLOW MCA {0}: exact reviewed patch on vanilla ({1} upstream lines), 3 derived row sites" -f $e.Rel, $mcaCopyMeasure.UpCount)
            }
            else {
                Write-Host ("  FAIL  MCA {0}: named exception drifted (sites={1}, tokens={2}, firstDiff={3}, lines={4}/{5})" -f $e.Rel, $mcaCopyMeasure.Sites.Count, $mcaCopyMeasure.Tokens, $mcaCopyMeasure.FirstDiff, $mcaCopyMeasure.CopyCount, $mcaCopyMeasure.UpCount)
                foreach ($detail in $mcaCopyMeasure.Errors) { Write-Host "        $detail" }
                $bad++
            }
        }
        else {
            Write-Host ("  FAIL  {0} {1}: unapproved vanilla-relative path collision" -f $t.Tag, $e.Rel)
            $bad++
        }
    }
    Write-Host ("  {0,-4} : {1,3} files tested, {2} forbidden collision(s)" -f $t.Tag, $files.Count, $bad)
    $fails += $bad
}
if ($allowedSeen -ne 1) {
    Write-Host ("  FAIL  exact MCA collision inventory count {0}, expected 1" -f $allowedSeen)
    $fails++
}
Close-Check "5 vanilla collisions (one measured MCA exception)" $fails

# =============================================================================
# CHECK 6 - EXACT INVENTORY, DEFINITIONS, ADAPTER BODY AND LOCALIZATION
# =============================================================================
Write-Host "CHECK 6 - exact MCA/AGOT runtime inventory, value bodies and component localization"
$fails = 0

# 6a - exact shipped paths. No effects, on_actions, decisions or interaction
# database copies survive in either addon. AGOT additionally carries no GUI.
foreach ($spec in @(
    @{ Tag = 'MCA'; Root = $McaRoot; Expected = $MCA_RUNTIME_FILES },
    @{ Tag = 'AGOT'; Root = $AdapterRoot; Expected = $AGOT_RUNTIME_FILES }
)) {
    $actual = @(Get-ShippedRelPaths $spec.Root)
    $missing = @($spec.Expected | Where-Object { $actual -cnotcontains $_ } | Sort-Object)
    $extra = @($actual | Where-Object { $spec.Expected -cnotcontains $_ } | Sort-Object)
    foreach ($rel in $missing) { Write-Host ("  FAIL  6a {0} missing expected file: {1}" -f $spec.Tag, $rel); $fails++ }
    foreach ($rel in $extra)   { Write-Host ("  FAIL  6a {0} unexpected shipped file: {1}" -f $spec.Tag, $rel); $fails++ }
    Write-Host ("  6a  {0,-4} inventory: {1} actual / {2} expected; {3} missing, {4} extra" -f $spec.Tag, $actual.Count, $spec.Expected.Count, $missing.Count, $extra.Count)
}

$forbiddenDirs = @('common\character_interactions', 'common\decisions', 'common\on_action', 'common\scripted_effects')
foreach ($tree in @(@{ Tag = 'MCA'; Root = $McaRoot }, @{ Tag = 'AGOT'; Root = $AdapterRoot })) {
    foreach ($rel in $forbiddenDirs) {
        $dir = Join-Path $tree.Root $rel
        $count = 0
        if (Test-Path -LiteralPath $dir) { $count = @(Get-ChildItem -LiteralPath $dir -Recurse -File).Count }
        if ($count -gt 0) { Write-Host ("  FAIL  6a {0} forbidden runtime category {1}: {2} file(s)" -f $tree.Tag, $rel, $count); $fails++ }
    }
}
$agotGuiCount = 0
if (Test-Path -LiteralPath (Join-Path $AdapterRoot 'common\scripted_guis')) {
    $agotSgCount = @(Get-ChildItem -LiteralPath (Join-Path $AdapterRoot 'common\scripted_guis') -Recurse -File).Count
    if ($agotSgCount -gt 0) { Write-Host "  FAIL  6a AGOT adapter must not carry scripted GUIs"; $fails++ }
}
if (Test-Path -LiteralPath (Join-Path $AdapterRoot 'gui')) { $agotGuiCount = @(Get-ChildItem -LiteralPath (Join-Path $AdapterRoot 'gui') -Recurse -File).Count }
if ($agotGuiCount -gt 0) { Write-Host ("  FAIL  6a AGOT adapter carries {0} GUI file(s); expected zero" -f $agotGuiCount); $fails++ }

$legacyMarkers = 0
foreach ($tree in @(@{ Tag = 'MCA'; Root = $McaRoot }, @{ Tag = 'AGOT'; Root = $AdapterRoot })) {
    foreach ($e in (Get-TreeFiles $tree.Root @('.txt', '.gui'))) {
        $ln = 0
        foreach ($L in [System.IO.File]::ReadAllLines($e.File.FullName)) {
            $ln++
            if ($L -match 'FROZEN COPY BELOW THIS LINE|TNT-MA ADDITION (BEGIN|END)') {
                Write-Host ("  FAIL  6a {0} legacy fence marker at {1}:{2}" -f $tree.Tag, $e.Rel, $ln)
                $legacyMarkers++; $fails++
            }
        }
    }
}
if ($legacyMarkers -eq 0) { Write-Host "  6a  legacy frozen/fence markers: 0" }

# 6b - parser-safe scalar+block definition sets and exact adapter/default code.
$mcaDefs = Get-TopLevelDefs $McaRoot 'common\script_values' @()
$mcaSgDefs = Get-TopLevelDefs $McaRoot 'common\scripted_guis' @()
$agotDefs = Get-TopLevelDefs $AdapterRoot 'common\script_values' @()
foreach ($spec in @(
    @{ Tag = 'MCA'; Map = $mcaDefs; Expected = $MCA_VALUE_DEFS },
    @{ Tag = 'MCA-SG'; Map = $mcaSgDefs; Expected = $MCA_SORT_GUI_DEFS },
    @{ Tag = 'AGOT'; Map = $agotDefs; Expected = $AGOT_OVERRIDE_VALUES }
)) {
    $missing = @($spec.Expected | Where-Object { -not $spec.Map.ContainsKey($_) } | Sort-Object)
    $extra = @($spec.Map.Keys | Where-Object { $spec.Expected -cnotcontains $_ } | Sort-Object)
    foreach ($n in $missing) { Write-Host ("  FAIL  6b {0} missing top-level value {1}" -f $spec.Tag, $n); $fails++ }
    foreach ($n in $extra)   { Write-Host ("  FAIL  6b {0} unexpected top-level value {1}: {2}" -f $spec.Tag, $n, ($spec.Map[$n] -join ', ')); $fails++ }
    foreach ($n in $spec.Expected) {
        if ($spec.Map.ContainsKey($n) -and $spec.Map[$n].Count -ne 1) {
            Write-Host ("  FAIL  6b {0} defines {1} {2} times: {3}" -f $spec.Tag, $n, $spec.Map[$n].Count, ($spec.Map[$n] -join ', ')); $fails++
        }
    }
    Write-Host ("  6b  {0,-6} top-level definitions: {1} distinct, exact set={2}" -f $spec.Tag, $spec.Map.Count, (($missing.Count + $extra.Count) -eq 0))
}

$mcaDefaultsPath = Join-Path $McaRoot 'common\script_values\tnt_ma_00_adapter_defaults.txt'
$agotValuesPath = Join-Path $AdapterRoot 'common\script_values\zz_agot_ma_adapter_values.txt'
$mcaDefaultsExpected = 'tnt_ma_adapter_p_c1_value={value=0}tnt_ma_adapter_p_c2_value={value=0}tnt_ma_adapter_p_c3_value={value=0}tnt_ma_adapter_p_c4_value={value=0}tnt_ma_adapter_r_c1_value={value=0}tnt_ma_adapter_r_c2_value={value=0}tnt_ma_adapter_r_c3_value={value=0}tnt_ma_adapter_r_c4_value={value=0}tnt_ma_adapter_p_value={value=0add=tnt_ma_adapter_p_c1_valueadd=tnt_ma_adapter_p_c2_valueadd=tnt_ma_adapter_p_c3_valueadd=tnt_ma_adapter_p_c4_value}tnt_ma_adapter_r_value={value=0add=tnt_ma_adapter_r_c1_valueadd=tnt_ma_adapter_r_c2_valueadd=tnt_ma_adapter_r_c3_valueadd=tnt_ma_adapter_r_c4_value}tnt_ma_alliance_base_value=40'
$agotValuesExpected = 'tnt_ma_adapter_p_c1_value={value=tnt_ma_adapter_r_c1_value}tnt_ma_adapter_r_c1_value={value=0if={limit={is_current_dragonrider=yes}add=30}}tnt_ma_adapter_r_c2_value={value=0}tnt_ma_adapter_r_c3_value={value=0}tnt_ma_adapter_r_c4_value={value=0}tnt_ma_alliance_base_value=40'
if ((Get-CanonicalActiveCode $mcaDefaultsPath) -cne $mcaDefaultsExpected) {
    Write-Host "  FAIL  6b MCA adapter defaults are not the exact 8-formula-zero-component / core-aggregate / alliance-40 contract"
    $fails++
}
else { Write-Host "  6b  MCA defaults body: 8 formula-zero components; core P/R aggregates; alliance=40" }
if ((Get-CanonicalActiveCode $agotValuesPath) -cne $agotValuesExpected) {
    Write-Host "  FAIL  6b AGOT adapter body differs from the symmetric dragonrider-potential/zero-retired-slots/alliance contract"
    $fails++
}
else { Write-Host "  6b  AGOT body: P1 aliases R1 current-dragonrider potential +30; R2..R4 zero; alliance=40" }

# The native ValueBreakdown renderer only preserves descriptions one scripted-
# value level deep. Raw/legacy callers therefore use each core-owned aggregate
# once, while both visible wrappers (plain + alliance) expose every adapter
# component directly and suppress the zero/default rows.
$mcaGradePath = Join-Path $McaRoot 'common\script_values\tnt_ma_52_grade.txt'
$breakdownFails = 0
foreach ($side in @('p', 'r')) {
    $otherSide = if ($side -eq 'p') { 'r' } else { 'p' }
    foreach ($wrapperName in @("tnt_ma_grade_${side}_value", "tnt_ma_grade_${side}_alliance_value")) {
        $wrapperCode = Get-CanonicalTopLevelDefinition $mcaGradePath $wrapperName
        if ($wrapperCode -eq '') {
            Write-Host ("  FAIL  6b MCA visible wrapper {0} has no block body" -f $wrapperName)
            $fails++; $breakdownFails++
            continue
        }
        $actorLimitShape = if ($side -eq 'p') {
            'limit={exists=scope:actorexists=scope:tnt_gr_pscope:actor!=scope:tnt_gr_p}'
        }
        else {
            'limit={exists=scope:actorexists=matchmakermatchmaker!=scope:actor}'
        }
        $actorLimitCount = ([regex]::Matches($wrapperCode, [regex]::Escape($actorLimitShape))).Count
        $actorAliasCount = ([regex]::Matches($wrapperCode, [regex]::Escape('scope:actor={save_temporary_scope_as=tnt_gr_me'))).Count
        $legacyGuardCount = ([regex]::Matches($wrapperCode, [regex]::Escape('exists=scope:tnt_gr_me'))).Count
        if ($actorLimitCount -ne 1 -or $actorAliasCount -ne 1 -or $legacyGuardCount -ne 0) {
            Write-Host ("  FAIL  6b MCA {0}: actor limit/alias/old guard={1}/{2}/{3}, expected 1/1/0" -f $wrapperName, $actorLimitCount, $actorAliasCount, $legacyGuardCount)
            $fails++; $breakdownFails++
        }
        foreach ($slot in 1..4) {
            $valueName = "tnt_ma_adapter_${side}_c${slot}_value"
            $locName = "tnt_ma_adapter_${side}_c${slot}"
            $shape = "if={limit={$valueName!=0}add={value=$valueName" + "desc=$locName}}"
            $count = ([regex]::Matches($wrapperCode, [regex]::Escape($shape))).Count
            if ($count -ne 1) {
                Write-Host ("  FAIL  6b MCA {0} carries {1} one-level row(s) for {2}, expected 1" -f $wrapperName, $count, $valueName)
                $fails++; $breakdownFails++
            }
        }
        $aggregate = "tnt_ma_adapter_${side}_value"
        $aggregateReads = ([regex]::Matches($wrapperCode, [regex]::Escape($aggregate))).Count
        $otherSideReads = ([regex]::Matches($wrapperCode, "tnt_ma_adapter_${otherSide}_c[1-4]_value")).Count
        if ($aggregateReads -ne 0 -or $otherSideReads -ne 0) {
            Write-Host ("  FAIL  6b MCA {0}: aggregate refs={1}, opposite-side component refs={2}; expected 0/0" -f $wrapperName, $aggregateReads, $otherSideReads)
            $fails++; $breakdownFails++
        }
    }

    $rawName = "tnt_ma_grade_${side}_raw_value"
    $rawCode = Get-CanonicalTopLevelDefinition $mcaGradePath $rawName
    $aggregate = "tnt_ma_adapter_${side}_value"
    $aggregateCount = ([regex]::Matches($rawCode, [regex]::Escape("add=$aggregate"))).Count
    $directComponentCount = ([regex]::Matches($rawCode, "tnt_ma_adapter_${side}_c[1-4]_value")).Count
    if ($rawCode -eq '' -or $aggregateCount -ne 1 -or $directComponentCount -ne 0) {
        Write-Host ("  FAIL  6b MCA {0}: aggregate add={1}, direct component refs={2}; expected 1/0" -f $rawName, $aggregateCount, $directComponentCount)
        $fails++; $breakdownFails++
    }
}
$availableExpected = @{
    'tnt_ma_grade_p_available_value' = 'tnt_ma_grade_p_available_value={value=0if={limit={exists=scope:actorexists=scope:tnt_gr_pscope:actor!=scope:tnt_gr_p}value=1}}'
    'tnt_ma_grade_r_available_value' = 'tnt_ma_grade_r_available_value={value=0if={limit={exists=scope:actorexists=matchmakermatchmaker!=scope:actor}value=1}}'
}
foreach ($availableName in $availableExpected.Keys) {
    $availableCode = Get-CanonicalTopLevelDefinition $mcaGradePath $availableName
    if ($availableCode -cne $availableExpected[$availableName]) {
        Write-Host ("  FAIL  6b MCA {0} is not the exact actor-based availability wrapper" -f $availableName)
        $fails++; $breakdownFails++
    }
}
$allyRatioExpected = 'tnt_ma_ally_ratio_value={value=0if={limit={exists=scope:tnt_sp_oneexists=scope:tnt_gr_meexists=scope:tnt_gr_pexists=scope:tnt_gr_side}add={value=scope:tnt_gr_p.max_military_strengthdivide={value=scope:tnt_gr_me.current_military_strengthmin=1}min=0max=2.5}}}'
$allyWorthExpected = 'tnt_ma_ally_worth_value={value=0if={limit={exists=scope:tnt_sp_oneexists=scope:tnt_gr_meexists=scope:tnt_gr_pexists=scope:tnt_gr_side}add={value=tnt_ma_ally_ratio_valuemultiply=tnt_ma_alliance_base_valuemin=1max=100}}round=yes}'
foreach ($allySpec in @(
    [pscustomobject]@{ Name = 'tnt_ma_ally_ratio_value'; Expected = $allyRatioExpected },
    [pscustomobject]@{ Name = 'tnt_ma_ally_worth_value'; Expected = $allyWorthExpected }
)) {
    if ((Get-CanonicalTopLevelDefinition $mcaGradePath $allySpec.Name) -cne $allySpec.Expected) {
        Write-Host ("  FAIL  6b MCA {0} differs from the reviewed ratio/base-40/cap-100 alliance contract" -f $allySpec.Name)
        $fails++; $breakdownFails++
    }
}
if ($breakdownFails -eq 0) { Write-Host "  6b  actor bridge + breakdown seam: 4 reachable aliases; each side's 4 components in both wrappers; aggregates raw-only" }

# All eight retired 1.x/2.x score components remain ABI names only. Their
# definitions are exact zero blocks, and the only active-code occurrence of
# each value is its definition. The old localization stays for compatibility
# but must not describe any active score row.
$gradeActiveCode = Get-CanonicalActiveCode $mcaGradePath
$compatFails = 0
foreach ($compatName in $MCA_COMPAT_SG_VALUES) {
    $compatExpected = $compatName + '={value=0}'
    if ((Get-CanonicalTopLevelDefinition $mcaGradePath $compatName) -cne $compatExpected) {
        Write-Host ("  FAIL  6b retired compatibility component {0} is not exactly zero" -f $compatName)
        $fails++; $compatFails++
    }
    $valuePattern = [regex]::Escape($compatName)
    $valueReads = [regex]::Matches($gradeActiveCode, $valuePattern).Count
    $compatLoc = ($compatName -replace '^tnt_ma_sg_', 'tnt_ma_grade_') -replace '_value$', ''
    $locPattern = [regex]::Escape($compatLoc)
    $locReads = [regex]::Matches($gradeActiveCode, $locPattern).Count
    if ($valueReads -ne 1 -or $locReads -ne 0) {
        Write-Host ("  FAIL  6b retired {0}: active value/description occurrences={1}/{2}, expected definition-only 1/0" -f $compatName, $valueReads, $locReads)
        $fails++; $compatFails++
    }
}
if ($compatFails -eq 0) { Write-Host '  6b  retired score ABI: eight exact-zero definitions; no active calls or descriptions' }

# Pin every reviewed shared-benefit helper. These builders expose the intended
# constants and branch order without reducing the contract to an opaque hash.
$skillExpected = 'tnt_ma_skill_value={value=0if={limit={effective_age>=16is_incapable=no}'
foreach ($skill in @('diplomacy', 'martial', 'stewardship', 'intrigue', 'learning')) {
    $skillExpected += 'add={value=' + $skill + 'divide=5floor=yesmin=1}'
}
$skillExpected += '}max=30}'

$ageExpected = 'tnt_ma_age_value={value=0if={limit={effective_age>=16is_incapable=noNOR={has_trait=eunuch_1has_trait=beardless_eunuchhas_trait=celibate}}if={limit={is_female=yes}'
$femaleAgeRows = @(
    [pscustomobject]@{ Limit = 'effective_age<=25'; Value = 20 },
    [pscustomobject]@{ Limit = 'effective_age<=30'; Value = 18 },
    [pscustomobject]@{ Limit = 'effective_age<=35'; Value = 14 },
    [pscustomobject]@{ Limit = 'effective_age<=40'; Value = 10 },
    [pscustomobject]@{ Limit = 'effective_age<=45'; Value = 7 },
    [pscustomobject]@{ Limit = 'effective_age<=50has_trait=fecund'; Value = 2 }
)
for ($i = 0; $i -lt $femaleAgeRows.Count; $i++) {
    $branch = if ($i -eq 0) { 'if' } else { 'else_if' }
    $ageExpected += $branch + '={limit={' + $femaleAgeRows[$i].Limit + '}value=' + $femaleAgeRows[$i].Value + '}'
}
$ageExpected += '}else={'
$maleAgeRows = @(
    [pscustomobject]@{ Limit = 'effective_age<=35'; Value = 20 },
    [pscustomobject]@{ Limit = 'effective_age<=40'; Value = 18 },
    [pscustomobject]@{ Limit = 'effective_age<=50'; Value = 16 },
    [pscustomobject]@{ Limit = 'effective_age<=60'; Value = 14 },
    [pscustomobject]@{ Limit = 'effective_age<=70'; Value = 12 }
)
for ($i = 0; $i -lt $maleAgeRows.Count; $i++) {
    $branch = if ($i -eq 0) { 'if' } else { 'else_if' }
    $ageExpected += $branch + '={limit={' + $maleAgeRows[$i].Limit + '}value=' + $maleAgeRows[$i].Value + '}'
}
$ageExpected += 'else={value=10}}}}'

$dynastyExpected = 'tnt_ma_dynasty_value={value=-5if={limit={has_dynasty=yes}value=dynasty.dynasty_prestige_levelsubtract=1multiply=5}min=-5max=45}'

$claimExpected = 'tnt_ma_claim_value={value=0'
$claimTiers = @(
    [pscustomobject]@{ Limit = 'tier>=tier_empire'; Value = 12 },
    [pscustomobject]@{ Limit = 'tier=tier_kingdom'; Value = 8 },
    [pscustomobject]@{ Limit = 'tier=tier_duchy'; Value = 4 },
    [pscustomobject]@{ Limit = 'tier=tier_county'; Value = 2 },
    [pscustomobject]@{ Limit = 'tier=tier_barony'; Value = 1 }
)
foreach ($pressed in @('no', 'yes')) {
    $claimExpected += 'every_claim={explicit=yespressed=' + $pressed + 'min={value=0'
    for ($i = 0; $i -lt $claimTiers.Count; $i++) {
        $branch = if ($i -eq 0) { 'if' } else { 'else_if' }
        $claimExpected += $branch + '={limit={' + $claimTiers[$i].Limit + '}value=' + $claimTiers[$i].Value + '}'
    }
    if ($pressed -eq 'yes') { $claimExpected += 'multiply=2' }
    $claimExpected += '}}'
}
$claimExpected += 'max=24}'

# Genetics reads only explicit candidate traits. Pin signs, weights,
# strongest-tier branches and the absence of hidden-gene or pair-state reads.
$geneticsExpected = 'tnt_ma_genetic_value={value=0'
foreach ($family in @('intellect', 'beauty', 'physique')) {
    foreach ($quality in @('good', 'bad')) {
        foreach ($tier in @(3, 2, 1)) {
            $branch = if ($tier -eq 3) { 'if' } else { 'else_if' }
            $weight = $tier * 10
            if ($quality -eq 'bad') { $weight = -$weight }
            $geneticsExpected += "${branch}={limit={has_trait=${family}_${quality}_${tier}}add=$weight}"
        }
    }
}
foreach ($entry in @(
    @('pure_blooded', 10), @('fecund', 10), @('inbred', -50),
    @('bleeder', -30), @('infertile', -50), @('spindly', -10),
    @('wheezing', -10), @('clubfooted', -10), @('hunchbacked', -10),
    @('lisping', -5), @('stuttering', -5)
)) {
    $geneticsExpected += 'if={limit={has_trait=' + $entry[0] + '}add=' + $entry[1] + '}'
}
$geneticsExpected += '}'
$benefitFails = 0
foreach ($helperSpec in @(
    [pscustomobject]@{ Name = 'tnt_ma_skill_value'; Expected = $skillExpected },
    [pscustomobject]@{ Name = 'tnt_ma_age_value'; Expected = $ageExpected },
    [pscustomobject]@{ Name = 'tnt_ma_dynasty_value'; Expected = $dynastyExpected },
    [pscustomobject]@{ Name = 'tnt_ma_claim_value'; Expected = $claimExpected },
    [pscustomobject]@{ Name = 'tnt_ma_genetic_value'; Expected = $geneticsExpected }
)) {
    if ((Get-CanonicalTopLevelDefinition $mcaGradePath $helperSpec.Name) -cne $helperSpec.Expected) {
        Write-Host ("  FAIL  6b candidate-benefit helper {0} differs from its reviewed formula" -f $helperSpec.Name)
        $fails++; $benefitFails++
    }
}

# The exact S/F/D/C/G row block is shared by both raw totals and all four GUI
# wrappers. It is direct in candidate root: depth one in raw blocks, depth two
# inside the GUI wrapper guard. This prevents sign or scope drift by side.
$benefitBlock = ''
foreach ($row in $MCA_BENEFIT_ROWS) {
    $benefitBlock += 'add={value=' + $row.Value + 'desc=' + $row.Loc + '}'
}
foreach ($side in @('p', 'r')) {
    foreach ($consumer in @("tnt_ma_grade_${side}_raw_value", "tnt_ma_grade_${side}_value", "tnt_ma_grade_${side}_alliance_value")) {
        $consumerCode = Get-CanonicalTopLevelDefinition $mcaGradePath $consumer
        $blockCount = [regex]::Matches($consumerCode, [regex]::Escape($benefitBlock)).Count
        $blockIndex = $consumerCode.IndexOf($benefitBlock, [System.StringComparison]::Ordinal)
        $blockDepth = -1
        if ($blockIndex -ge 0) {
            $prefix = $consumerCode.Substring(0, $blockIndex)
            $blockDepth = [regex]::Matches($prefix, '\{').Count - [regex]::Matches($prefix, '\}').Count
        }
        $expectedDepth = if ($consumer -cmatch '_raw_value$') { 1 } else { 2 }
        $rowRefsOk = $true
        foreach ($row in $MCA_BENEFIT_ROWS) {
            $valuePattern = [regex]::Escape($row.Value)
            $rowShape = 'add={value=' + $row.Value + 'desc=' + $row.Loc + '}'
            if ([regex]::Matches($consumerCode, $valuePattern).Count -ne 1 -or
                [regex]::Matches($consumerCode, [regex]::Escape($rowShape)).Count -ne 1) {
                $rowRefsOk = $false
            }
        }
        $oldSgReads = [regex]::Matches($consumerCode, 'tnt_ma_sg_[pr]_c[1-4]_value').Count
        if ($blockCount -ne 1 -or $blockDepth -ne $expectedDepth -or -not $rowRefsOk -or $oldSgReads -ne 0) {
            Write-Host ("  FAIL  6b {0} S/F/D/C/G block count/depth/rows/old-SG={1}/{2}/{3}/{4}, expected 1/{5}/True/0 in candidate scope" -f $consumer, $blockCount, $blockDepth, $rowRefsOk, $oldSgReads, $expectedDepth)
            $fails++; $benefitFails++
        }
    }
}
foreach ($row in $MCA_BENEFIT_ROWS) {
    $valuePattern = [regex]::Escape($row.Value)
    $locPattern = [regex]::Escape($row.Loc)
    $rowShape = 'add={value=' + $row.Value + 'desc=' + $row.Loc + '}'
    $allReferences = [regex]::Matches($gradeActiveCode, $valuePattern).Count
    $allRows = [regex]::Matches($gradeActiveCode, [regex]::Escape($rowShape)).Count
    $allDescriptions = [regex]::Matches($gradeActiveCode, $locPattern).Count
    if ($allReferences -ne 7 -or $allRows -ne 6 -or $allDescriptions -ne 6) {
        Write-Host ("  FAIL  6b {0} total references/rows/descriptions={1}/{2}/{3}, expected 7/6/6" -f $row.Value, $allReferences, $allRows, $allDescriptions)
        $fails++; $benefitFails++
    }
}
if ($benefitFails -eq 0) { Write-Host '  6b  candidate benefits: five exact helpers; identical direct S/F/D/C/G rows in six candidate-scope consumers' }

# 6c - exact loc keys in all nine files; no MCA/AGOT shared key.
foreach ($spec in @(
    @{ Tag = 'MCA'; Root = $McaRoot; Stem = 'tnt_ma'; Expected = $MCA_LOC_KEYS },
    @{ Tag = 'AGOT'; Root = $AdapterRoot; Stem = 'agot_ma'; Expected = $AGOT_LOC_KEYS }
)) {
    foreach ($lang in $LANGS) {
        $rel = "localization\$lang\$($spec.Stem)_l_$lang.yml"
        $path = Join-Path $spec.Root $rel
        if (-not (Test-Path -LiteralPath $path)) { continue }
        $keys = @(Get-LocKeys $path)
        $missing = @($spec.Expected | Where-Object { $keys -cnotcontains $_ })
        $extra = @($keys | Where-Object { $spec.Expected -cnotcontains $_ })
        $dupes = @($keys | Group-Object | Where-Object { $_.Count -ne 1 })
        if ($missing.Count + $extra.Count + $dupes.Count -gt 0) {
            Write-Host ("  FAIL  6c {0} {1}: {2} keys; {3} missing, {4} extra, {5} duplicate groups" -f $spec.Tag, $lang, $keys.Count, $missing.Count, $extra.Count, $dupes.Count)
            $fails++
        }
    }
    Write-Host ("  6c  {0,-4} loc contract: {1} exact keys x {2} languages" -f $spec.Tag, $spec.Expected.Count, $LANGS.Count)
}
$sharedLoc = @($MCA_LOC_KEYS | Where-Object { $AGOT_LOC_KEYS -ccontains $_ })
if ($sharedLoc.Count -gt 0) { Write-Host ("  FAIL  6c MCA/AGOT loc keys overlap: {0}" -f ($sharedLoc -join ', ')); $fails += $sharedLoc.Count }
else { Write-Host "  6c  MCA/AGOT localization overlap: 0 keys" }

$mcaDescriptor = [System.IO.File]::ReadAllText((Join-Path $McaRoot 'descriptor.mod'))
$agotDescriptor = [System.IO.File]::ReadAllText((Join-Path $AdapterRoot 'descriptor.mod'))
if ($mcaDescriptor -notmatch 'version="3\.1\.0"' -or $mcaDescriptor -notmatch '"Parley: The Negotiating Table"') { Write-Host "  FAIL  6d MCA descriptor is not v3.1.0 depending on Parley"; $fails++ }
if ($agotDescriptor -notmatch 'version="2\.2\.0"' -or $agotDescriptor -notmatch '"A Game of Thrones"' -or $agotDescriptor -notmatch '"Marriage Calculation Assistant"') { Write-Host "  FAIL  6d AGOT adapter descriptor is not v2.2.0 depending on AGOT + MCA"; $fails++ }

Close-Check "6 exact MCA v3.1.0 / AGOT v2.2 inventory" $fails

# =============================================================================
# CHECK 7 - THE SEAM CHECK (stubs, calls, redefinition set, grade names, contract)
# =============================================================================
Write-Host "CHECK 7 - ownership seam (Parley stubs; pure scores; player snapshot; six AGOT overrides)"
$fails = 0
$coreDefs = Get-TopLevelDefs $CoreRoot 'common' @('on_action')
$mcaAllDefs = Get-TopLevelDefs $McaRoot 'common' @('on_action')
$agotAllDefs = Get-TopLevelDefs $AdapterRoot 'common' @('on_action')

# 7a - Parley remains the sole owner of all five compatibility stubs.
$stubDefs = Get-FileTopLevelDefs (Join-Path $CoreRoot 'common\scripted_effects\tnt_1f_addon_hooks.txt') 'common\scripted_effects\tnt_1f_addon_hooks.txt'
foreach ($h in $HOOKS) {
    $coreCount = 0; if ($coreDefs.ContainsKey($h)) { $coreCount = $coreDefs[$h].Count }
    $stubCount = 0; if ($stubDefs.ContainsKey($h)) { $stubCount = $stubDefs[$h].Count }
    if ($coreCount -ne 1 -or $stubCount -ne 1) {
        Write-Host ("  FAIL  7a {0}: core count {1}, stub-file count {2}; expected 1/1" -f $h, $coreCount, $stubCount)
        $fails++
    }
    if ($mcaAllDefs.ContainsKey($h)) { Write-Host ("  FAIL  7a MCA redefines legacy hook {0}: {1}" -f $h, ($mcaAllDefs[$h] -join ', ')); $fails++ }
    if ($agotAllDefs.ContainsKey($h)) { Write-Host ("  FAIL  7a AGOT adapter redefines legacy hook {0}: {1}" -f $h, ($agotAllDefs[$h] -join ', ')); $fails++ }
}
Write-Host "  7a  five hooks remain Parley-only; MCA/AGOT redefinitions: 0 expected"

# 7b - preserve the public call contract exactly: stamp 1, strips 1 each,
# order 2. A duplicate call is as breaking as a missing call.
$expectedHookCalls = @{
    'tnt_ma_grade_stamp_effect' = 1
    'tnt_ma_grade_strip_p_effect' = 1
    'tnt_ma_grade_strip_r_effect' = 1
    'tnt_ma_grade_strip_all_effect' = 1
    'tnt_ma_grade_order_effect' = 2
}
foreach ($h in $HOOKS) {
    $sites = @()
    foreach ($sub in @('common', 'events')) {
        $dir = Join-Path $CoreRoot $sub
        if (-not (Test-Path -LiteralPath $dir)) { continue }
        foreach ($f in (Get-ChildItem -LiteralPath $dir -Recurse -File -Filter *.txt)) {
            if ($f.Name -eq $STUBFILE) { continue }
            $rel = $f.FullName.Substring($CoreRoot.Length + 1)
            $ln = 0
            foreach ($L in [System.IO.File]::ReadAllLines($f.FullName)) {
                $ln++
                $code = Strip-CommentKeepQuotes $L
                if ($code -match ('(^|[\s{])' + [regex]::Escape($h) + '\s*=')) { $sites += ("{0}:{1}" -f $rel, $ln) }
            }
        }
    }
    if ($sites.Count -ne $expectedHookCalls[$h]) {
        Write-Host ("  FAIL  7b {0}: {1} call(s), expected {2}: {3}" -f $h, $sites.Count, $expectedHookCalls[$h], ($sites -join ', '))
        $fails++
    }
    else { Write-Host ("  7b  {0,-32} {1} call(s): {2}" -f $h, $sites.Count, ($sites -join ', ')) }
}

# 7c - database ownership. The only MCA/AGOT overlap is the intentional P1,
# R1..R4 and alliance base set; neither addon overlaps Parley.
$coreMcaOverlap = @($mcaAllDefs.Keys | Where-Object { $coreDefs.ContainsKey($_) } | Sort-Object)
$coreAgotOverlap = @($agotAllDefs.Keys | Where-Object { $coreDefs.ContainsKey($_) } | Sort-Object)
$mcaAgotOverlap = @($agotAllDefs.Keys | Where-Object { $mcaAllDefs.ContainsKey($_) } | Sort-Object)
foreach ($pair in @(
    @{ Label = 'CORE/MCA'; Actual = $coreMcaOverlap; Expected = @() },
    @{ Label = 'CORE/AGOT'; Actual = $coreAgotOverlap; Expected = @() },
    @{ Label = 'MCA/AGOT'; Actual = $mcaAgotOverlap; Expected = $AGOT_OVERRIDE_VALUES }
)) {
    $missing = @($pair.Expected | Where-Object { $pair.Actual -cnotcontains $_ })
    $extra = @($pair.Actual | Where-Object { $pair.Expected -cnotcontains $_ })
    if ($missing.Count + $extra.Count -gt 0) {
        Write-Host ("  FAIL  7c {0} overlap [{1}], expected [{2}]" -f $pair.Label, ($pair.Actual -join ', '), ($pair.Expected -join ', '))
        $fails++
    }
    else { Write-Host ("  7c  {0,-9} overlap exact: [{1}]" -f $pair.Label, ($pair.Actual -join ', ')) }
}

# 7d - the grade remains outside Parley code.
$gradeCode = 0
foreach ($e in (Get-TreeFiles $CoreRoot @('.txt', '.yml', '.gui'))) {
    $ln = 0
    foreach ($L in [System.IO.File]::ReadAllLines($e.File.FullName)) {
        $ln++
        $code = Strip-CommentKeepQuotes $L
        if (-not $L.TrimStart().StartsWith('#') -and $code -match 'tnt_(spouse_grade|stage_row_grade)') {
            Write-Host ("  FAIL  7d grade name in Parley code at {0}:{1}: {2}" -f $e.Rel, $ln, $L.Trim())
            $gradeCode++
        }
    }
}
$fails += $gradeCode
Write-Host ("  7d  grade names in Parley code: {0}" -f $gradeCode)

# 7e - namespace walls and pure-value state ownership.
$coreMaViol = 0
foreach ($e in (Get-TreeFiles $CoreRoot @('.txt', '.yml', '.gui'))) {
    if ((Split-Path -Leaf $e.Rel) -eq $STUBFILE) { continue }
    $ln = 0
    foreach ($L in [System.IO.File]::ReadAllLines($e.File.FullName)) {
        $ln++
        $code = Strip-CommentKeepQuotes $L
        foreach ($m in [regex]::Matches($code, 'tnt_ma_[a-z0-9_]+')) {
            if ($HOOKS -notcontains $m.Value) { Write-Host ("  FAIL  7e Parley names non-hook addon token {0} at {1}:{2}" -f $m.Value, $e.Rel, $ln); $coreMaViol++ }
        }
    }
}
$fails += $coreMaViol

foreach ($tree in @(@{ Tag = 'MCA'; Root = $McaRoot }, @{ Tag = 'AGOT'; Root = $AdapterRoot })) {
    $viol = 0; $mutations = 0; $census = @{}
    foreach ($e in (Get-TreeFiles $tree.Root @('.txt', '.yml', '.gui'))) {
        $ln = 0
        foreach ($L in [System.IO.File]::ReadAllLines($e.File.FullName)) {
            $ln++
            $code = Strip-CommentKeepQuotes $L
            foreach ($m in [regex]::Matches($code, 'tnt_[a-z0-9_]+')) {
                $tok = $m.Value
                if (-not $census.ContainsKey($tok)) { $census[$tok] = 0 }; $census[$tok]++
                if ($tree.Tag -eq 'MCA') {
                    $ok = $tok.StartsWith('tnt_ma_') -or ($MCA_NON_NAMESPACE_NAMES -contains $tok) -or ($MCA_CONTEXT_NAMES -contains $tok) -or ($SEAM_STATE -contains $tok)
                }
                else {
                    $ok = ($AGOT_OVERRIDE_VALUES -contains $tok) -or ($AGOT_LOC_KEYS -contains $tok) -or ($AGOT_CONTEXT_NAMES -contains $tok)
                }
                if (-not $ok) { Write-Host ("  FAIL  7e {0} token {1} outside its contract at {2}:{3}" -f $tree.Tag, $tok, $e.Rel, $ln); $viol++ }
            }
            if ($code -match ('(set_variable|remove_variable|change_variable|clear_variable_list|add_to_variable_list)\s*=\s*(' + ($SEAM_STATE -join '|') + ')\b') -or
                $code -match ('name\s*=\s*(' + ($SEAM_STATE -join '|') + ')\b')) {
                Write-Host ("  FAIL  7e {0} writes Parley-owned state at {1}:{2}: {3}" -f $tree.Tag, $e.Rel, $ln, $L.Trim()); $viol++
            }
            if ($code -match '\b(set_variable|remove_variable|change_variable|clear_variable_list|add_to_variable_list|remove_list_variable|remove_from_variable_list)\s*=' -and
                -not ($tree.Tag -eq 'MCA' -and $e.Rel -ceq 'common\scripted_guis\tnt_ma_sort.txt')) {
                Write-Host ("  FAIL  7e {0} persistent/list mutation outside the private snapshot SG at {1}:{2}: {3}" -f $tree.Tag, $e.Rel, $ln, $L.Trim()); $mutations++
            }
        }
    }
    $fails += $viol + $mutations
    Write-Host ("  7e  {0,-4} namespace: {1} distinct tnt_ tokens, {2} outside; forbidden mutations {3}" -f $tree.Tag, $census.Count, $viol, $mutations)
}
Write-Host ("  7e  Parley non-hook tnt_ma_* tokens: {0}" -f $coreMaViol)

$sortContractErrors = @(Test-McaSortContract $McaRoot)
foreach ($detail in $sortContractErrors) { Write-Host "  FAIL  7f $detail"; $fails++ }
if ($sortContractErrors.Count -eq 0) { Write-Host "  7f  player-only snapshot: exact 5 SG / 12 vars / 6 lists; pure capture values; cleanup and callback guards" }
Close-Check "7 ownership and snapshot seam" $fails

# =============================================================================
# CHECK 8 - THE RACE CHECK (pure name comparisons, printed)
# =============================================================================
Write-Host "CHECK 8 - load/hover contract (derived relation row, reviewed GUI patch, late adapter values)"
$fails = 0

function Assert-Order([string]$label, [string]$a, [string]$b) {
    $cmp = [string]::CompareOrdinal($a, $b)
    $det = Describe-Order $a $b
    if ($cmp -lt 0) { Write-Host ("  PASS  {0}: '{1}' < '{2}'   ({3})" -f $label, $a, $b, $det); return 0 }
    Write-Host ("  FAIL  {0}: '{1}' does NOT sort before '{2}'   ({3})" -f $label, $a, $b, $det)
    return 1
}

# 8a - MCA derives a new marriage-only type; it never redeclares the active
# vanilla/AGOT base row. The reviewed GUI patch instantiates it at three sites.
$derivedDecls = @(); $baseDecls = @()
foreach ($e in (Get-TreeFiles $McaRoot @('.gui'))) {
    $ln = 0
    foreach ($L in [System.IO.File]::ReadAllLines($e.File.FullName)) {
        $ln++
        $code = Strip-CommentKeepQuotes $L
        if ($code -match '^\s*type\s+tnt_ma_widget_character_list_item\s*=\s*widget_character_list_item\s*\{') { $derivedDecls += ("{0}:{1}" -f $e.Rel, $ln) }
        if ($code -match '^\s*type\s+widget_character_list_item\s*=') { $baseDecls += ("{0}:{1}" -f $e.Rel, $ln) }
    }
}
if ($derivedDecls.Count -ne 1) { Write-Host ("  FAIL  8a derived row declaration count {0}, expected 1: {1}" -f $derivedDecls.Count, ($derivedDecls -join ', ')); $fails++ }
else { Write-Host ("  8a  derived row declared once: {0}" -f $derivedDecls[0]) }
if ($baseDecls.Count -ne 0) { Write-Host ("  FAIL  8a MCA directly redeclares widget_character_list_item: {0}" -f ($baseDecls -join ', ')); $fails += $baseDecls.Count }
else { Write-Host "  8a  direct base-row redeclarations in MCA/AGOT adapter: 0" }

$derivedGuiPath = Join-Path $McaRoot 'gui\tnt_ma_character_list_item.gui'
$derivedGuiCode = (([System.IO.File]::ReadAllLines($derivedGuiPath) | ForEach-Object { Strip-CommentKeepQuotes $_ }) -join "`n")
$derivedGuiCanonical = [regex]::Replace($derivedGuiCode, '\s+', '')
# The 2026-09-29 Russian run filled the engine's 100,000-error budget with
# bare Localize calls to secondary labels whose text requires Character.
# The marriage-only row sites already bind the context.
# Require the remaining functional guards and forbid localized-label tests.
$unsafeMarriageLabelReads = ([regex]::Matches($derivedGuiCode, '\bLocalize\s*\(|\bGet(?:Actor|Recipient)SecondaryLabel\b|\btnt_open\b')).Count
$playerVisibilityGuards = ([regex]::Matches($derivedGuiCanonical, [regex]::Escape('ObjectsEqual(CharacterInteractionConfirmationWindow.GetActor,GetPlayer)'))).Count
$pPickerGuards = ([regex]::Matches($derivedGuiCode, '\bMatchmakerInteractionWindow\.IsPickingSecondaryActor\b')).Count
$rPickerGuards = ([regex]::Matches($derivedGuiCode, '\bMatchmakerInteractionWindow\.IsPickingSecondaryRecipient\b')).Count
if ($unsafeMarriageLabelReads -ne 0 -or $playerVisibilityGuards -ne 4 -or $pPickerGuards -ne 2 -or $rPickerGuards -ne 2) {
    Write-Host ("  FAIL  8a locale-safe marriage guards: unsafe/player/P/R={0}/{1}/{2}/{3}, expected 0/4/2/2" -f $unsafeMarriageLabelReads, $playerVisibilityGuards, $pPickerGuards, $rPickerGuards)
    $fails++
}
else { Write-Host "  8a  locale-safe marriage visibility: no label localization; player + P/R picker guards present" }
$extraOverrides = ([regex]::Matches($derivedGuiCode, '\bblockoverride\s+"extra_skills"\s*\{')).Count
$relationOverrides = ([regex]::Matches($derivedGuiCode, '\bblockoverride\s+"character_relation"\s*\{')).Count
$nativeRelationShape = 'name="character_relation"layoutpolicy_horizontal=expandingraw_text="|[Character.GetRelationToString(GetPlayer)]"tooltip="EXTENDED_RELATIONS_TOOLTIP"default_format="#low"autoresize=noalign=nobaselinevisible="[Character.HasRelationTo(GetPlayer)]"alwaystransparent=yes'
$nativeRelationCount = ([regex]::Matches($derivedGuiCanonical, [regex]::Escape($nativeRelationShape))).Count
$otherItemReads = ([regex]::Matches($derivedGuiCode, '\bCharacterListItem\.GetOtherCharacterItems\b')).Count
$actorCarrierReads = ([regex]::Matches($derivedGuiCode, [regex]::Escape(".AddScope('actor', GetPlayer.MakeScope)"))).Count
$legacyPlayerCarrierReads = ([regex]::Matches($derivedGuiCode, [regex]::Escape(".AddScope('tnt_gr_me', GetPlayer.MakeScope)"))).Count
$partnerCarrierReads = ([regex]::Matches($derivedGuiCode, [regex]::Escape(".AddScope('tnt_gr_p', CharacterInteractionConfirmationWindow.GetRecipient.MakeScope)"))).Count
$gradeDisplayCalls = ([regex]::Matches($derivedGuiCode, "\.ScriptValue\('tnt_ma_grade_(?:p|r)(?:_alliance)?_value'\)")).Count
$gradeAvailabilityCalls = ([regex]::Matches($derivedGuiCode, "\.ScriptValue\('tnt_ma_grade_(?:p|r)_available_value'\)")).Count
$gradeBreakdownCalls = ([regex]::Matches($derivedGuiCode, "\.GetScriptValueBreakdown\('tnt_ma_grade_(?:p|r)(?:_alliance)?_value'\)")).Count
$guiValueNames = @([regex]::Matches($derivedGuiCode, '\btnt_ma_[a-z0-9_]+_value\b') | ForEach-Object { $_.Value } | Sort-Object -Unique)
$guiValueMissing = @($MCA_GUI_VALUE_NAMES | Where-Object { $guiValueNames -cnotcontains $_ })
$guiValueExtra = @($guiValueNames | Where-Object { $MCA_GUI_VALUE_NAMES -cnotcontains $_ })
$gradeShellGeometry = ([regex]::Matches($derivedGuiCanonical, [regex]::Escape('name="tnt_ma_grade_carrier"size={12626}min_width=126max_width=126min_height=26max_height=26'))).Count
$marriageGuiPath = Join-Path $McaRoot 'gui\interaction_marriage.gui'
$marriageGuiCode = (([System.IO.File]::ReadAllLines($marriageGuiPath) | ForEach-Object { Strip-CommentKeepQuotes $_ }) -join "`n")
$scrollboxOverrides = ([regex]::Matches($marriageGuiCode, 'blockoverride\s+"scrollbox_properties"')).Count
$grid630 = ([regex]::Matches($marriageGuiCode, '\baddcolumn\s*=\s*630\b')).Count
$row630 = ([regex]::Matches($marriageGuiCode, '\bsize\s*=\s*\{\s*630\s+110\s*\}')).Count
if ($extraOverrides -ne 0 -or $relationOverrides -ne 1 -or $nativeRelationCount -ne 1) {
    Write-Host ("  FAIL  8a extra_skills/relation overrides/native relation={0}/{1}/{2}, expected 0/1/1" -f $extraOverrides, $relationOverrides, $nativeRelationCount); $fails++
}
if ($otherItemReads -ne 4) { Write-Host ("  FAIL  8a derived row GetOtherCharacterItems reads={0}, expected 4" -f $otherItemReads); $fails++ }
if ($gradeShellGeometry -ne 1) {
    Write-Host ("  FAIL  8a grade carrier exact 126x26 count={0}, expected 1" -f $gradeShellGeometry)
    $fails++
}
else { Write-Host "  8a  grade geometry: 126x26 carrier inside character_relation; native relation preserved" }
if ($scrollboxOverrides -ne 0 -or $grid630 -ne 2 -or $row630 -ne 7) {
    Write-Host ("  FAIL  8a viewport scrollbox overrides/grid630/row630={0}/{1}/{2}, expected 0/2/7 (native + sorted wrappers)" -f $scrollboxOverrides, $grid630, $row630)
    $fails++
}
else { Write-Host "  8a  viewport geometry: vanilla 630px grid/row, no window-widening override" }
if ($guiValueMissing.Count + $guiValueExtra.Count -gt 0) {
    Write-Host ("  FAIL  8a derived row GUI values [{0}], expected [{1}]" -f ($guiValueNames -join ', '), ($MCA_GUI_VALUE_NAMES -join ', ')); $fails++
}
else { Write-Host ("  8a  derived relation row: {0} alliance-state reads, exact {1}-value GUI API" -f $otherItemReads, $guiValueNames.Count) }
if ($actorCarrierReads -ne 16 -or $legacyPlayerCarrierReads -ne 0 -or $partnerCarrierReads -ne 8) {
    Write-Host ("  FAIL  8a GUI actor/tnt_gr_me/tnt_gr_p carrier reads={0}/{1}/{2}, expected 16/0/8" -f $actorCarrierReads, $legacyPlayerCarrierReads, $partnerCarrierReads)
    $fails++
}
if ($gradeDisplayCalls -ne 4 -or $gradeAvailabilityCalls -ne 4 -or $gradeBreakdownCalls -ne 8) {
    Write-Host ("  FAIL  8a GUI display/availability/breakdown calls={0}/{1}/{2}, expected 4/4/8" -f $gradeDisplayCalls, $gradeAvailabilityCalls, $gradeBreakdownCalls)
    $fails++
}
if ($actorCarrierReads -eq 16 -and $legacyPlayerCarrierReads -eq 0 -and $partnerCarrierReads -eq 8 -and
    $gradeDisplayCalls -eq 4 -and $gradeAvailabilityCalls -eq 4 -and $gradeBreakdownCalls -eq 8) {
    Write-Host "  8a  GUI carrier census: actor=16, legacy tnt_gr_me=0, P partner=8; ScriptValue=8, breakdown=8"
}

# Four score labels must own their ValueBreakdown context, and the virtualized
# native popup must receive the same context explicitly. Live CK3 proved both
# halves: owner-only opens an empty header/help popup, while popup-only leaves
# the text hitbox outside ValueBreakdown. ValueBreakdown.HasTooltip is not a
# visibility contract here (it returned false for the wrapper values), so the
# known-broken guard is forbidden rather than required.
$expectedScoreBreakdowns = [ordered]@{
    'tnt_ma_grade_p_value' =
        "[GuiScope.SetRoot(Character.MakeScope).AddScope('actor', GetPlayer.MakeScope).AddScope('tnt_gr_p', CharacterInteractionConfirmationWindow.GetRecipient.MakeScope).GetScriptValueBreakdown('tnt_ma_grade_p_value')]"
    'tnt_ma_grade_p_alliance_value' =
        "[GuiScope.SetRoot(Character.MakeScope).AddScope('actor', GetPlayer.MakeScope).AddScope('tnt_gr_p', CharacterInteractionConfirmationWindow.GetRecipient.MakeScope).GetScriptValueBreakdown('tnt_ma_grade_p_alliance_value')]"
    'tnt_ma_grade_r_value' =
        "[GuiScope.SetRoot(Character.MakeScope).AddScope('actor', GetPlayer.MakeScope).GetScriptValueBreakdown('tnt_ma_grade_r_value')]"
    'tnt_ma_grade_r_alliance_value' =
        "[GuiScope.SetRoot(Character.MakeScope).AddScope('actor', GetPlayer.MakeScope).GetScriptValueBreakdown('tnt_ma_grade_r_alliance_value')]"
}

# Parse text_single owners by brace depth. A whole-file regex cannot
# distinguish owner-level properties from the old, broken inner-only form.
$derivedGuiLines = [System.IO.File]::ReadAllLines($derivedGuiPath)
$scoreOwners = @()
for ($i = 0; $i -lt $derivedGuiLines.Count; $i++) {
    $startCode = Strip-CommentKeepQuotes $derivedGuiLines[$i]
    if ($startCode -notmatch '^\s*text_single\s*=\s*\{') { continue }

    $records = @()
    $depth = 0
    for ($j = $i; $j -lt $derivedGuiLines.Count; $j++) {
        $code = Strip-CommentKeepQuotes $derivedGuiLines[$j]
        $depthBefore = $depth
        # Braces inside quoted GUI expressions are data, not block delimiters.
        $braceCode = [regex]::Replace($code, '"(?:\\.|[^"])*"', '""')
        $depth += ([regex]::Matches($braceCode, '\{')).Count
        $depth -= ([regex]::Matches($braceCode, '\}')).Count
        $records += [pscustomobject]@{
            Line  = $j + 1
            Depth = $depthBefore
            Code  = $code
        }
        if ($j -gt $i -and $depth -eq 0) { break }
    }

    if ($depth -ne 0) {
        Write-Host ("  FAIL  8a unclosed text_single block at {0}:{1}" -f $derivedGuiPath, ($i + 1))
        $fails++
        break
    }

    $direct = @($records | Where-Object { $_.Depth -eq 1 } | ForEach-Object { $_.Code })
    $gradeHits = @(
        foreach ($line in $direct) {
            foreach ($m in [regex]::Matches($line, "\.ScriptValue\('(?<value>tnt_ma_grade_(?:p|r)(?:_alliance)?_value)'\)")) {
                $m.Groups['value'].Value
            }
        }
    )
    if ($gradeHits.Count -gt 0) {
        $scoreOwners += [pscustomobject]@{
            Line      = $i + 1
            Direct    = $direct
            Records   = $records
            GradeHits = $gradeHits
        }
    }
    $i = $j
}

if ($scoreOwners.Count -ne 4) {
    Write-Host ("  FAIL  8a score text_single owners={0}, expected exactly 4" -f $scoreOwners.Count)
    $fails++
}
$scoreOwnerGeometryOk = 0
foreach ($valueName in $expectedScoreBreakdowns.Keys) {
    $owners = @($scoreOwners | Where-Object { $_.GradeHits -ccontains $valueName })
    if ($owners.Count -ne 1) {
        Write-Host ("  FAIL  8a {0} score owners={1}, expected 1" -f $valueName, $owners.Count)
        $fails++
        continue
    }

    $owner = $owners[0]
    $ownerMin112 = @($owner.Direct | Where-Object { $_ -cmatch '^\s*min_width\s*=\s*112\s*$' }).Count
    $ownerMax112 = @($owner.Direct | Where-Object { $_ -cmatch '^\s*max_width\s*=\s*112\s*$' }).Count
    $ownerPosition = @($owner.Direct | Where-Object { $_ -cmatch '^\s*position\s*=\s*\{\s*6\s+0\s*\}\s*$' }).Count
    $ownerSize = @($owner.Direct | Where-Object { $_ -cmatch '^\s*size\s*=\s*\{\s*112\s+26\s*\}\s*$' }).Count
    $ownerMedium = @($owner.Direct | Where-Object { $_ -cmatch '^\s*using\s*=\s*Font_Size_Medium\s*$' }).Count
    if ($ownerMin112 -ne 1 -or $ownerMax112 -ne 1 -or $ownerPosition -ne 1 -or $ownerSize -ne 1 -or $ownerMedium -ne 1) {
        Write-Host ("  FAIL  8a {0} owner geometry min/max/position/size/font={1}/{2}/{3}/{4}/{5}, expected 1/1/1/1/1" -f $valueName, $ownerMin112, $ownerMax112, $ownerPosition, $ownerSize, $ownerMedium)
        $fails++
    }
    else { $scoreOwnerGeometryOk++ }
    if ($owner.GradeHits.Count -ne 1) {
        Write-Host ("  FAIL  8a score owner line {0} contains {1} grade ScriptValue calls, expected 1" -f $owner.Line, $owner.GradeHits.Count)
        $fails++
    }

    $dcPattern = '^\s*datacontext\s*=\s*"' + [regex]::Escape($expectedScoreBreakdowns[$valueName]) + '"\s*$'
    $ownerDcCount = @($owner.Records | Where-Object { $_.Depth -eq 1 -and $_.Code -cmatch $dcPattern }).Count
    $tooltipIndices = @()
    for ($k = 0; $k -lt $owner.Records.Count; $k++) {
        if ($owner.Records[$k].Depth -eq 1 -and $owner.Records[$k].Code -match '^\s*tooltipwidget\s*=\s*\{') {
            $tooltipIndices += $k
        }
    }
    $tooltipOwnerCount = $tooltipIndices.Count
    $nativeIndices = @()
    if ($tooltipOwnerCount -eq 1) {
        for ($k = $tooltipIndices[0] + 1; $k -lt $owner.Records.Count; $k++) {
            if ($owner.Records[$k].Depth -le 1) { break }
            if ($owner.Records[$k].Depth -eq 2 -and $owner.Records[$k].Code -match '^\s*widget_value_breakdown_tooltip\s*=\s*\{') {
                $nativeIndices += $k
            }
        }
    }
    $nativeWidgetCount = $nativeIndices.Count
    $popupDcCount = 0
    if ($nativeWidgetCount -eq 1) {
        for ($k = $nativeIndices[0] + 1; $k -lt $owner.Records.Count; $k++) {
            if ($owner.Records[$k].Depth -le 2) { break }
            if ($owner.Records[$k].Depth -eq 3 -and $owner.Records[$k].Code -cmatch $dcPattern) {
                $popupDcCount++
            }
        }
    }
    $badTransparency = @($owner.Direct | Where-Object { $_ -cmatch '^\s*alwaystransparent\s*=' -and $_ -cnotmatch '^\s*alwaystransparent\s*=\s*no\s*$' })
    $badHasTooltip = @($owner.Records | Where-Object { $_.Code -cmatch 'ValueBreakdown\.HasTooltip' })

    if ($ownerDcCount -ne 1 -or $tooltipOwnerCount -ne 1 -or $nativeWidgetCount -ne 1 -or $popupDcCount -ne 1) {
        Write-Host ("  FAIL  8a {0} breakdown chain owner/tooltip/native/popup={1}/{2}/{3}/{4}, expected 1/1/1/1" -f $valueName, $ownerDcCount, $tooltipOwnerCount, $nativeWidgetCount, $popupDcCount)
        $fails++
    }
    if ($badTransparency.Count -ne 0) {
        Write-Host ("  FAIL  8a {0} score owner is transparent/noninteractive at line {1}" -f $valueName, $owner.Line)
        $fails++
    }
    if ($badHasTooltip.Count -ne 0) {
        Write-Host ("  FAIL  8a {0} uses the runtime-refuted ValueBreakdown.HasTooltip visibility guard" -f $valueName)
        $fails++
    }
}
if ($scoreOwners.Count -eq 4) {
    Write-Host "  8a  four interactive score owners + native popups carry exact matching ValueBreakdown contexts"
}
if ($scoreOwnerGeometryOk -eq 4) {
    Write-Host "  8a  all four score owners overlay at x=6, 112x26, medium font, away from scrollbar"
}

if (-not $mcaCopyMeasure.Passed -or $mcaCopyMeasure.Sites.Count -ne 3 -or $mcaCopyMeasure.Tokens -ne 3 -or $mcaCopyMeasure.FirstDiff -ne 0) {
    Write-Host ("  FAIL  8a frozen GUI contract: sites={0}, tokens={1}, firstDiff={2}, lines={3}/{4}" -f $mcaCopyMeasure.Sites.Count, $mcaCopyMeasure.Tokens, $mcaCopyMeasure.FirstDiff, $mcaCopyMeasure.CopyCount, $mcaCopyMeasure.UpCount)
    $fails++
}
else { Write-Host "  8a  reviewed marriage GUI patch: exact reconstruction; 3 derived row instances" }

foreach ($upstream in @(
    @{ Tag = 'VANILLA'; Path = (Join-Path $VanillaRoot 'gui\shared\lists.gui') },
    @{ Tag = 'AGOT'; Path = (Join-Path $AgotRoot 'gui\shared\lists.gui') }
)) {
    $typeCount = 0; $relationCount = 0
    $upstreamGuiCode = (([System.IO.File]::ReadAllLines($upstream.Path) | ForEach-Object { Strip-CommentKeepQuotes $_ }) -join "`n")
    $upstreamGuiCanonical = [regex]::Replace($upstreamGuiCode, '\s+', '')
    $scrollbar12Count = ([regex]::Matches($upstreamGuiCanonical, [regex]::Escape('templateScrollbar_Vertical{scrollbar={name="vertical_scrollbar"size={1212}'))).Count
    foreach ($L in [System.IO.File]::ReadAllLines($upstream.Path)) {
        $code = Strip-CommentKeepQuotes $L
        if ($code -match '^\s*type\s+widget_character_list_item\s*=\s*widget\s*\{') { $typeCount++ }
        if ($code -match '^\s*block\s+"character_relation"\s*(\{\s*)?$') { $relationCount++ }
    }
    if ($typeCount -ne 1 -or $relationCount -lt 1 -or $scrollbar12Count -ne 1) { Write-Host ("  FAIL  8a {0} inherited row seam: base types={1}, character_relation blocks={2}, exact 12px scrollbar templates={3}" -f $upstream.Tag, $typeCount, $relationCount, $scrollbar12Count); $fails++ }
    else { Write-Host ("  8a  {0,-7} base type + character_relation seam + exact 12px scrollbar present" -f $upstream.Tag) }
}
if (Test-Path -LiteralPath (Join-Path $AgotRoot 'gui\interaction_marriage.gui')) { Write-Host "  FAIL  8a AGOT now overrides gui\interaction_marriage.gui; rebase required"; $fails++ }

# 8b - only P1, R1..R4 and alliance base race. The AGOT file
# must sort after MCA's defaults; no hook, interaction, row-type or
# localization twin race remains.
$fails += Assert-Order "8b adapter values: formula defaults before late AGOT formulas" 'tnt_ma_00_adapter_defaults.txt' 'zz_agot_ma_adapter_values.txt'

$coreNames = @()
foreach ($f in (Get-ChildItem -LiteralPath (Join-Path $CoreRoot 'common') -Recurse -File -Filter *.txt)) { $coreNames += $f.Name }
$coreNameViol = @($coreNames | Where-Object { $_ -notmatch '^tnt_[0-9a-f]{2,3}_' })
foreach ($n in $coreNameViol) { Write-Host ("  FAIL  8b Parley database filename outside tnt_[0-9a-f]{{2,3}}_*: {0}" -f $n); $fails++ }

$mcaCommonNames = @(Get-ChildItem -LiteralPath (Join-Path $McaRoot 'common') -Recurse -File -Filter *.txt | ForEach-Object { $_.Name } | Sort-Object)
$mcaExpectedNames = @('tnt_ma_00_adapter_defaults.txt', 'tnt_ma_52_grade.txt', 'tnt_ma_sort_capture.txt', 'tnt_ma_sort.txt')
$mcaNameExtra = @($mcaCommonNames | Where-Object { $mcaExpectedNames -cnotcontains $_ })
$mcaNameMissing = @($mcaExpectedNames | Where-Object { $mcaCommonNames -cnotcontains $_ })
if ($mcaNameExtra.Count + $mcaNameMissing.Count -gt 0) { Write-Host ("  FAIL  8b MCA common filenames [{0}], expected [{1}]" -f ($mcaCommonNames -join ', '), ($mcaExpectedNames -join ', ')); $fails++ }
else { Write-Host "  8b  MCA common filenames exact: defaults + grade + capture values + private snapshot SG" }

$agotCommonNames = @(Get-ChildItem -LiteralPath (Join-Path $AdapterRoot 'common') -Recurse -File -Filter *.txt | ForEach-Object { $_.Name })
if ($agotCommonNames.Count -ne 1 -or $agotCommonNames[0] -cne 'zz_agot_ma_adapter_values.txt') { Write-Host ("  FAIL  8b AGOT common filenames [{0}], expected only zz_agot_ma_adapter_values.txt" -f ($agotCommonNames -join ', ')); $fails++ }
else { Write-Host "  8b  AGOT common filename exact: one intentional-last adapter" }

# 8c - the post-smoke manual-session boundary. ESC/X underneath a modal event
# must not erase its table; every per-frame score read must be behind an ordered
# live-session trigger_if; Equalize must not manufacture title+realm packages.
$sessionFiles = @(
    'events\tnt_events.txt',
    'common\scripted_guis\tnt_20_scripted_guis.txt',
    'common\scripted_guis\tnt_22_v2.txt',
    'common\scripted_effects\tnt_30_effects.txt'
)
$pendingHits = 0
foreach ($rel in $sessionFiles) {
    foreach ($L in [System.IO.File]::ReadAllLines((Join-Path $CoreRoot $rel))) {
        $pendingHits += ([regex]::Matches((Strip-Code $L), '\btnt_confirm_pending\b')).Count
    }
}
$eventSessionCode = (([System.IO.File]::ReadAllLines((Join-Path $CoreRoot 'events\tnt_events.txt')) | ForEach-Object { Strip-CommentKeepQuotes $_ }) -join '')
$eventSessionCanonical = [regex]::Replace($eventSessionCode, '\s+', '')
$guardedScoreOptions = ([regex]::Matches($eventSessionCanonical, 'trigger_if=\{limit=\{exists=var:tnt_openexists=var:tnt_partnerexists=scope:tnt_deal_partnervar:tnt_partner\?=\{this=scope:tnt_deal_partner\}\}tnt_ai_accept_value(?:>|<=)0\}trigger_else=\{always=no\}')).Count
$sendCode = (([System.IO.File]::ReadAllLines((Join-Path $CoreRoot 'common\scripted_guis\tnt_20_scripted_guis.txt')) | ForEach-Object { Strip-CommentKeepQuotes $_ }) -join '')
$sendCanonical = [regex]::Replace($sendCode, '\s+', '')
$autoCode = (([System.IO.File]::ReadAllLines((Join-Path $CoreRoot 'common\scripted_guis\tnt_22_v2.txt')) | ForEach-Object { Strip-CommentKeepQuotes $_ }) -join '')
$autoCanonical = [regex]::Replace($autoCode, '\s+', '')
$sendDefinitionCanonical = Get-CanonicalTopLevelDefinition (Join-Path $CoreRoot 'common\scripted_guis\tnt_20_scripted_guis.txt') 'tnt_send_offer'
$itemsCountCanonical = Get-CanonicalTopLevelDefinition (Join-Path $CoreRoot 'common\script_values\tnt_50_values.txt') 'tnt_items_count_value'
$lumpyCode = (([System.IO.File]::ReadAllLines((Join-Path $CoreRoot 'common\scripted_effects\tnt_39_autobalance.txt')) | ForEach-Object { Strip-CommentKeepQuotes $_ }) -join '')
$lumpyCanonical = [regex]::Replace($lumpyCode, '\s+', '')
$windowCode = (([System.IO.File]::ReadAllLines((Join-Path $CoreRoot 'gui\tnt_diplomacy_window.gui')) | ForEach-Object { Strip-CommentKeepQuotes $_ }) -join "`n")

$pendingOk = ($pendingHits -eq 7 -and
    $sendCanonical.Contains('NOT={exists=var:tnt_confirm_pending}}tnt_close_window_effect=yes') -and
    $sendCanonical.Contains('set_variable={name=tnt_confirm_pendingvalue=1}trigger_event=tnt_diplomacy.0001'))
$sessionOptionsOk = ($guardedScoreOptions -eq 2 -and
    ([regex]::Matches($eventSessionCanonical, [regex]::Escape('name=tnt_confirm_opt_stale'))).Count -eq 1 -and
    ([regex]::Matches($eventSessionCanonical, [regex]::Escape('remove_variable=tnt_confirm_pending'))).Count -eq 4)
$preflightSendOk = (([regex]::Matches($sendCanonical, '\btnt_deal_preflight_trigger=\{PLAYER=rootPARTNER=scope:tnt_deal_partner\}')).Count -eq 1)
$autoSessionOk = ($autoCanonical.Contains('custom_description={text=tnt_err_no_partnerexists=var:tnt_openexists=var:tnt_partner}trigger_if={limit={exists=var:tnt_openexists=var:tnt_partner}') -and
    $autoCanonical.Contains('effect={if={limit={exists=var:tnt_openexists=var:tnt_partner}tnt_autobalance_effect={MARGIN=1CEILING=1}}}'))
$autoThreatSeedOk = (([regex]::Matches($autoCanonical, [regex]::Escape('custom_description={text=tnt_err_ab_emptyOR={tnt_offer_nonempty_trigger=yesAND={exists=var:tnt_threat_pvar:tnt_threat_p>0tnt_val_threat_p_value>0}}}'))).Count -eq 1)
$threatPriceCode = Get-CanonicalTopLevelDefinition (Join-Path $CoreRoot 'common\script_values\tnt_57_threat_values.txt') 'tnt_val_threat_p_value'
$threatPriceOk = ($threatPriceCode -ceq 'tnt_val_threat_p_value={value=0if={limit={exists=var:tnt_threat_pvar:tnt_threat_p>0exists=var:tnt_partnertnt_threat_points_value>=100}add=tnt_threat_points_value}}')
$threatRemoveOk = ([regex]::Replace($windowCode, '\s+', '').Contains('enabled="[Or(TntOn(''tnt_threat_p''),TntValid(''tnt_threat_p_toggle''))]"'))
if (-not $threatPriceOk -or -not $threatRemoveOk) {
    Write-Host "  FAIL  8c threat must give zero below100 and a stale selected threat must remain removable"; $fails++
}
$threatNotSendableOk = (-not $itemsCountCanonical.Contains('tnt_threat_p') -and
    ([regex]::Matches($sendDefinitionCanonical, [regex]::Escape('custom_tooltip={text=tnt_err_nothingtnt_offer_nonempty_trigger=yes}'))).Count -eq 1)
$packageOk = ($sendCanonical.Contains('text=tnt_err_title_realm_mix') -and
    $sendCanonical.Contains('tnt_count_sel_title_p_value=0tnt_count_sel_title_r_value=0') -and
    $lumpyCanonical.Contains('NOT={exists=var:tnt_vassal_r}NOT={exists=var:tnt_vassal_p}NOT={exists=var:tnt_indep_r}NOT={exists=var:tnt_indep_p}NOT={exists=var:tnt_title_p}NOT={exists=var:tnt_title_r}') -and
    $lumpyCanonical.Contains('exists=var:tnt_advancedNOT={exists=var:tnt_vassal_p}NOT={exists=var:tnt_vassal_r}NOT={exists=var:tnt_indep_p}NOT={exists=var:tnt_indep_r}has_variable_list=tnt_list_title_r'))
$windowFailClosed = (([regex]::Matches($windowCode, [regex]::Escape('visible = "[And( TntOn(''tnt_open''), TntVar(''tnt_partner'').Char.IsValid )]"'))).Count -eq 1)

if (-not ($pendingOk -and $sessionOptionsOk -and $preflightSendOk -and $autoSessionOk -and $autoThreatSeedOk -and $threatNotSendableOk -and $packageOk -and $windowFailClosed)) {
    Write-Host ("  FAIL  8c session pending/options/preflight/autobalance/threat-seed/threat-nonsend/package/window={0}/{1}/{2}/{3}/{4}/{5}/{6}/{7}; pending hits={8}, guarded score options={9}" -f $pendingOk, $sessionOptionsOk, $preflightSendOk, $autoSessionOk, $autoThreatSeedOk, $threatNotSendableOk, $packageOk, $windowFailClosed, $pendingHits, $guardedScoreOptions)
    $fails++
}
else { Write-Host "  8c  manual session: modal latch, guarded score paths, click preflight; threat seeds Equalize but cannot be sent alone" }

# 8d - strategic threat must be one bounded synchronous lane, not another queued
# pulse and not a weight added to the generic random archetype draw.
$worldEffectPath = Join-Path $CoreRoot 'common\scripted_effects\tnt_38_ai_world.txt'
$worldTriggerPath = Join-Path $CoreRoot 'common\scripted_triggers\tnt_40_triggers.txt'
$worldLogPath = Join-Path $CoreRoot 'common\scripted_effects\tnt_3b_log.txt'
$worldEffectCode = (([System.IO.File]::ReadAllLines($worldEffectPath) | ForEach-Object { Strip-CommentKeepQuotes $_ }) -join "`n")
$worldEffectCanonical = [regex]::Replace($worldEffectCode, '\s+', '')
$worldTriggerCode = (([System.IO.File]::ReadAllLines($worldTriggerPath) | ForEach-Object { Strip-CommentKeepQuotes $_ }) -join "`n")
$worldTriggerCanonical = [regex]::Replace($worldTriggerCode, '\s+', '')
$worldValueCode = (([System.IO.File]::ReadAllLines((Join-Path $CoreRoot 'common\script_values\tnt_56_ai_values.txt')) | ForEach-Object { Strip-CommentKeepQuotes $_ }) -join "`n")
$worldOnActionCode = (([System.IO.File]::ReadAllLines((Join-Path $CoreRoot 'common\on_action\tnt_72_ai_world.txt')) | ForEach-Object { Strip-CommentKeepQuotes $_ }) -join "`n")
$worldOnActionCanonical = [regex]::Replace($worldOnActionCode, '\s+', '')
$worldLogCode = (([System.IO.File]::ReadAllLines($worldLogPath) | ForEach-Object { Strip-CommentKeepQuotes $_ }) -join "`n")
$pairBlock = Get-CanonicalTopLevelDefinition $worldTriggerPath 'tnt_ai_coercive_fealty_pair_trigger'

$subStart = $worldEffectCanonical.IndexOf('tnt_ai_world_submission_pulse_effect={')
$subEnd = $worldEffectCanonical.IndexOf('tnt_ai_world_do_submission_effect={')
$doEnd = $worldEffectCanonical.IndexOf('tnt_ai_world_pulse_effect={')
$applyStart = $worldEffectCanonical.IndexOf('tnt_ai_world_apply_vassal_effect={')
$applyEnd = $worldEffectCanonical.IndexOf('tnt_ai_world_do_vassal_effect={')
$subBlock = if ($subStart -ge 0 -and $subEnd -gt $subStart) { $worldEffectCanonical.Substring($subStart, $subEnd - $subStart) } else { '' }
$doBlock = if ($subEnd -ge 0 -and $doEnd -gt $subEnd) { $worldEffectCanonical.Substring($subEnd, $doEnd - $subEnd) } else { '' }
$applyBlock = if ($applyStart -ge 0 -and $applyEnd -gt $applyStart) { $worldEffectCanonical.Substring($applyStart, $applyEnd - $applyStart) } else { '' }

$submissionDefs = ([regex]::Matches($worldEffectCode, '(?m)^\s*tnt_ai_world_submission_pulse_effect\s*=\s*\{')).Count
$submissionDoDefs = ([regex]::Matches($worldEffectCode, '(?m)^\s*tnt_ai_world_do_submission_effect\s*=\s*\{')).Count
$pairDefs = ([regex]::Matches($worldTriggerCode, '(?m)^\s*tnt_ai_coercive_fealty_pair_trigger\s*=\s*\{')).Count
$structuralPartnerDefs = ([regex]::Matches($worldTriggerCode, '(?m)^\s*tnt_ai_world_partner_structural_trigger\s*=\s*\{')).Count
$pairCalls = ([regex]::Matches($worldEffectCode, '\btnt_ai_coercive_fealty_pair_trigger\s*=\s*\{')).Count
$points100 = ([regex]::Matches($pairBlock, 'tnt_threat_points_value>=100')).Count
$ratio4 = ([regex]::Matches($pairBlock, 'tnt_threat_ratio_value>=4')).Count
$boundedPick = ([regex]::Matches($subBlock, 'random_neighboring_and_across_water_top_liege_realm_owner=\{')).Count
$unboundedWalks = ([regex]::Matches($subBlock, '(?:every_ruler|every_independent_ruler)=\{')).Count
$privateTargetSaves = ([regex]::Matches($subBlock, 'save_temporary_scope_as=tnt_submission_target')).Count
$candidateScopeSaves = ([regex]::Matches($subBlock, 'save_temporary_scope_as=tnt_submission_candidate')).Count
$candidatePairCall = ([regex]::Matches($subBlock, 'tnt_ai_coercive_fealty_pair_trigger=\{A=scope:actorB=scope:tnt_submission_candidate\}')).Count
$revalidationPairCall = ([regex]::Matches($doBlock, 'tnt_ai_coercive_fealty_pair_trigger=\{A=scope:actorB=scope:tnt_submission_target\}')).Count
$relativePairCalls = ([regex]::Matches($worldEffectCanonical, 'tnt_ai_coercive_fealty_pair_trigger=\{A=rootB=this\}')).Count
$structuralPartnerCalls = ([regex]::Matches($pairBlock, 'tnt_ai_world_partner_structural_trigger=yes')).Count
$willingPartnerCalls = ([regex]::Matches($pairBlock, 'tnt_ai_world_partner_valid_trigger=yes')).Count
$capacityFloor = ([regex]::Matches($pairBlock, 'vassal_limit_available>0')).Count + ([regex]::Matches($subBlock, 'vassal_limit_available>0')).Count
$staleCapacityFloor = ([regex]::Matches($pairBlock + $subBlock, 'vassal_limit_available>1')).Count
$privateRecipientLeak = ([regex]::Matches($subBlock, 'save_temporary_scope_as=recipient')).Count
$recipientBridge = ([regex]::Matches($doBlock, 'scope:tnt_submission_target=\{save_temporary_scope_as=recipient\}')).Count
$applyDefs = ([regex]::Matches($worldEffectCode, '(?m)^\s*tnt_ai_world_apply_vassal_effect\s*=\s*\{')).Count
$applyCalls = ([regex]::Matches($worldEffectCode, '\btnt_ai_world_apply_vassal_effect\s*=\s*yes')).Count
$vanillaVassalMutation = ([regex]::Matches($worldEffectCode, '\boffer_vassalization_interaction_effect\s*=\s*yes')).Count
$applyMutation = ([regex]::Matches($applyBlock, 'offer_vassalization_interaction_effect=yes')).Count
$applyObligationNames = @([regex]::Matches($applyBlock, 'save_scope_value_as=\{name=(?<n>[a-z_]+)value=no\}') | ForEach-Object { $_.Groups['n'].Value } | Sort-Object)
$applyObligationsOk = (($applyObligationNames -join ',') -ceq 'high_obligations,low_obligations,religious_exemption,religious_exemption_clan')
$submissionOpinion = ([regex]::Matches($doBlock, 'modifier=tnt_threat_opinion')).Count
$submissionDread = ([regex]::Matches($doBlock, 'scope:actor=\{add_dread=minor_dread_gain\}')).Count
$submissionCooldown = ([regex]::Matches($doBlock, 'tnt_ai_world_cooldown_effect=\{A=scope:actorB=scope:recipient\}')).Count
$routeShape = ($worldOnActionCanonical.Contains('highest_held_title_tier>=tier_countyis_at_war=noNOT={has_variable=tnt_ai_world_cd}') -and
    $worldOnActionCanonical.Contains('tnt_ai_world_submission_pulse_effect=yesif={limit={NOT={has_variable=tnt_ai_world_cd}}tnt_ai_world_pulse_effect=yes}'))
$submissionSafetyShape = ($worldTriggerCanonical.Contains('$A$={is_ai=yesis_alive=yesis_landed=yesis_ruler=yesis_adult=yesis_independent_ruler=yesis_at_war=nohighest_held_title_tier>=tier_kingdom') -and
    $worldTriggerCanonical.Contains('NOT={has_variable=agot_pwl_direct}') -and
    $worldTriggerCanonical.Contains('$B$={tnt_ai_world_partner_structural_trigger=yesis_independent_ruler=yesis_at_war=nois_playable_character=yes') -and
    $worldTriggerCanonical.Contains('modifier=granted_independence_opiniontarget=$A$'))
$orderShape = ($worldOnActionCanonical.IndexOf('tnt_ai_world_submission_pulse_effect=yes') -ge 0 -and
    $worldOnActionCanonical.IndexOf('tnt_ai_world_submission_pulse_effect=yes') -lt $worldOnActionCanonical.IndexOf('tnt_ai_world_pulse_effect=yes'))
$submissionEdgeDefs = ([regex]::Matches($worldValueCode, '(?m)^\s*tnt_ai_submission_tier_edge_value\s*=\s*\{')).Count
$telemetryNames = @(
    'tnt_log_wsubpulse_effect', 'tnt_log_wsubtry_effect',
    'tnt_log_wstop_submission_depleted_effect', 'tnt_log_wstop_submission_nocand_effect',
    'tnt_log_warch_submission_effect', 'tnt_log_wdone_submission_effect',
    'tnt_log_wskip_submission_revalidate_effect'
)
$telemetryContracts = [ordered]@{
    'tnt_log_wsubpulse_effect' = @{ Sets = 3; Removes = 3; Required = @('|WSUBPULSE|','|chance=','|cur=','|max='); Forbidden = @('|war=') }
    'tnt_log_wsubtry_effect' = @{ Sets = 0; Removes = 0; Required = @('|WSUBTRY|','|aid='); Forbidden = @() }
    'tnt_log_wstop_submission_depleted_effect' = @{ Sets = 2; Removes = 2; Required = @('|WSTOP|','|why=submission_actor_depleted','|cur=','|max='); Forbidden = @() }
    'tnt_log_wstop_submission_nocand_effect' = @{ Sets = 0; Removes = 0; Required = @('|WSTOP|','|why=no_submission_candidate','|aid='); Forbidden = @() }
    'tnt_log_warch_submission_effect' = @{ Sets = 4; Removes = 4; Required = @('|WARCH|','|arch=submission','|aid=','|bid=','|pts=','|ratio=','|edge='); Forbidden = @('|war=') }
    'tnt_log_wdone_submission_effect' = @{ Sets = 1; Removes = 1; Required = @('|WDONE|','|arch=submission','|aid=','|bid='); Forbidden = @('|pts=','|ratio=','|edge=','|war=') }
    'tnt_log_wskip_submission_revalidate_effect' = @{ Sets = 3; Removes = 3; Required = @('|WSKIP|','|arch=submission','|why=revalidation','|aid=','|bid=','|pts=','|edge='); Forbidden = @() }
}
$telemetryOk = $true
foreach ($name in $telemetryNames) {
    $defs = ([regex]::Matches($worldLogCode, '(?m)^\s*' + [regex]::Escape($name) + '\s*=\s*\{')).Count
    $calls = ([regex]::Matches($worldEffectCode, '\b' + [regex]::Escape($name) + '\s*=\s*yes')).Count
    $logBlock = Get-CanonicalTopLevelDefinition $worldLogPath $name
    $setCount = ([regex]::Matches($logBlock, 'set_variable=\{')).Count
    $removeCount = ([regex]::Matches($logBlock, 'remove_variable=')).Count
    $setNames = @([regex]::Matches($logBlock, 'set_variable=\{name=(?<n>tnt_log_[a-z0-9_]+?)value=') | ForEach-Object { $_.Groups['n'].Value } | Sort-Object)
    $removeNames = @([regex]::Matches($logBlock, 'remove_variable=(?<n>tnt_log_[a-z0-9_]+?)(?=remove_variable=|\})') | ForEach-Object { $_.Groups['n'].Value } | Sort-Object)
    $scratchNamesOk = (($setNames -join ',') -ceq ($removeNames -join ','))
    $errorLogCount = ([regex]::Matches($logBlock, 'error_log="')).Count
    $contract = $telemetryContracts[$name]
    $fieldsOk = $true
    foreach ($needle in $contract.Required) { if (-not $logBlock.Contains($needle)) { $fieldsOk = $false } }
    foreach ($needle in $contract.Forbidden) { if ($logBlock.Contains($needle)) { $fieldsOk = $false } }
    if ($defs -ne 1 -or $calls -ne 1 -or $setCount -ne $contract.Sets -or $removeCount -ne $contract.Removes -or
        -not $scratchNamesOk -or $errorLogCount -ne 1 -or -not $fieldsOk) { $telemetryOk = $false }
}
$submissionNotify = ([regex]::Matches($doBlock, 'tnt_ai_world_notify_effect=\{A=scope:actorB=scope:recipientTT=tnt_ai_msg_tt_submission\}')).Count
$submissionLocCodeRefs = 0
foreach ($e in (Get-TreeFiles $CoreRoot @('.txt', '.gui'))) {
    if ($e.Rel -match '^(_docs|localization)(\\|$)') { continue }
    foreach ($L in [System.IO.File]::ReadAllLines($e.File.FullName)) {
        $submissionLocCodeRefs += ([regex]::Matches((Strip-Code $L), '\btnt_ai_msg_tt_submission\b')).Count
    }
}
$submissionLocDefs = 0
foreach ($lang in $LANGS) {
    $locPath = Join-Path $CoreRoot ("localization\{0}\tnt_l_{0}.yml" -f $lang)
    foreach ($L in [System.IO.File]::ReadAllLines($locPath)) {
        if ($L -match '^\s+tnt_ai_msg_tt_submission:\d+\s+"') { $submissionLocDefs++ }
    }
}
$submissionMessageOk = ($submissionNotify -eq 1 -and $submissionLocCodeRefs -eq 1 -and $submissionLocDefs -eq 9)

$submissionShapeOk = ($submissionDefs -eq 1 -and $submissionDoDefs -eq 1 -and $pairDefs -eq 1 -and $structuralPartnerDefs -eq 1 -and $pairCalls -eq 2 -and
    $points100 -eq 1 -and $ratio4 -eq 1 -and $boundedPick -eq 1 -and $unboundedWalks -eq 0 -and
    $privateTargetSaves -eq 1 -and $candidateScopeSaves -eq 1 -and $candidatePairCall -eq 1 -and $revalidationPairCall -eq 1 -and $relativePairCalls -eq 0 -and
    $structuralPartnerCalls -eq 1 -and $willingPartnerCalls -eq 0 -and $capacityFloor -eq 2 -and $staleCapacityFloor -eq 0 -and
    $privateRecipientLeak -eq 0 -and $recipientBridge -eq 1 -and $applyDefs -eq 1 -and $applyCalls -eq 2 -and
    $vanillaVassalMutation -eq 1 -and $applyMutation -eq 1 -and $applyObligationsOk -and
    $submissionOpinion -eq 1 -and $submissionDread -eq 1 -and $submissionCooldown -eq 1 -and
    $submissionEdgeDefs -eq 1 -and $routeShape -and $submissionSafetyShape -and $orderShape -and $telemetryOk -and $submissionMessageOk)
if (-not $submissionShapeOk) {
    Write-Host ("  FAIL  8d strategic submission defs/do/pair/structDef/calls/pts/ratio/pick/walk/target/candidateSave/candidateCall/revalidateCall/relativeCall/structCall/willingCall/capacity/staleCapacity/leak/bridge/applyDefs/applyCalls/mutation/applyMutation/obligations/opinion/dread/cd/edge/route/safety/order/log/message={0}/{1}/{2}/{3}/{4}/{5}/{6}/{7}/{8}/{9}/{10}/{11}/{12}/{13}/{14}/{15}/{16}/{17}/{18}/{19}/{20}/{21}/{22}/{23}/{24}/{25}/{26}/{27}/{28}/{29}/{30}/{31}/{32}/{33}" -f $submissionDefs,$submissionDoDefs,$pairDefs,$structuralPartnerDefs,$pairCalls,$points100,$ratio4,$boundedPick,$unboundedWalks,$privateTargetSaves,$candidateScopeSaves,$candidatePairCall,$revalidationPairCall,$relativePairCalls,$structuralPartnerCalls,$willingPartnerCalls,$capacityFloor,$staleCapacityFloor,$privateRecipientLeak,$recipientBridge,$applyDefs,$applyCalls,$vanillaVassalMutation,$applyMutation,$applyObligationsOk,$submissionOpinion,$submissionDread,$submissionCooldown,$submissionEdgeDefs,$routeShape,$submissionSafetyShape,$orderShape,$telemetryOk,$submissionMessageOk)
    $fails++
}
else { Write-Host "  8d  strategic AI threat: peaceful/playable 4:1 + 100-point submission lane, dread/opinion/cooldown and telemetry locked" }

Close-Check "8 load/hover contract" $fails

# =============================================================================
# CHECK 9 - THE STORE GUARD ON VARIABLE-LIST WALKS (added 2026-08-24)
#
# THE DEFECT THIS EXISTS FOR, MEASURED. tnt_ma_mm_strip_effect walked
# tnt_ma_mm_list with no `limit` and fired twelve bare remove_variable rows per
# member. The stamps it removes carry days = 30 and every strip that can reach
# them is slower than that, so the walk arrived at candidates whose variable
# store the engine had already dropped whole - and remove_variable on a scope
# with NO store is an ENGINE ERROR, not the silent no-op three file headers
# claimed. 576 lines in one 20-minute run, from SIX byte-identical copies of
# one shape. The full mechanism and its four vanilla citations are in this
# tool's header; read them before touching this check.
#
# THE SHAPE, and why nothing else here could see it: the variable names were
# all correct, the list was correct, the walk was correct, the prefix rule was
# satisfied - so no name check, key-set check, twin check or brace check had
# anything to fire on. Only the ABSENCE of a guard distinguishes the defect.
#
# *** WIDENED 2026-08-24, THE SAME DAY IT WAS BORN, BECAUSE IT MISSED THE
# *** LARGEST INSTANCE OF ITS OWN DEFECT. As first written this check skipped
# *** any walk without a `variable =` row, so it saw only every_in_list over a
# *** variable list - and the family's biggest offender was an ENGINE iterator:
# *** tnt_86_uninstall.txt's every_living_character, nineteen bare
# *** remove_variable rows against every living character in the world. On run
# *** C's own save that is 35,447 characters, i.e. roughly 665,000 [E] lines
# *** from ONE click, against a 100,000-line engine cap - it would have
# *** destroyed the log in the very session in which the uninstall was being
# *** tested, and it fires on the last thing the mod ever does.
# *** THE LESSON IS ABOUT SCOPE OF A CHECK, NOT ABOUT THIS FILE: a check
# *** written from the shape of the ONE instance that was measured inherits
# *** that instance's accidents. The rule is about a MUTATION ON A WALKED
# *** MEMBER, and the kind of walk was never part of it. ***
#
# WHAT COUNTS AS A WALK NOW: any every_* / random_* / ordered_* iterator, list
# or engine. random_list is excluded by name - it is a weighted CHOICE, not an
# iterator, its entries run once on the current scope, and counting it would
# manufacture false positives across the two composers.
# WHAT COUNTS AS A GUARD: a `limit` carrying `exists = var:` anywhere in the
# walk's own rows - on the walk itself OR on an inner `if` around just the
# removals. The inner form is not a dodge and must stay legal: in
# tnt_86_uninstall.txt the walk MUST still visit every character, because the
# opinion and hook blocks below the removals live in their own stores and the
# characters they exist for are exactly the ones a walk-level variable guard
# would skip.
# =============================================================================
Write-Host "CHECK 9 - store guard: every mutating iterator (list or engine) carries exists = var:"
$fails = 0

# Rows inside a named re-scope belong to that scope, not to the member being
# walked. Dropping those blocks is what keeps the legitimate shape clean:
# tnt_39_autobalance's lumpy rungs walk a TITLE list and write every variable
# on `scope:tnt_ab_owner`, the player they carry in by name.
# `root` AND `this` JOINED THAT LIST WITH THE 2026-08-24 WIDENING, and they
# had to: the LEAN probe (tnt_3b_log.txt L21) walks every_vassal and
# every_neighboring_top_liege_realm_owner counting candidates with
# `root = { change_variable = { name = tnt_log_n1  add = 1 } }`. The counter
# is on ROOT, not on the vassal, and root's store is created by the probe's
# own set_variable rows a few lines above - so those two walks are correct and
# were the widening's only false positives.
# THE BLIND SPOT THIS BUYS, STATED RATHER THAN HIDDEN: a bare
# `root = { remove_variable = x }` inside an iterator is now invisible here.
# It is a real shape and it would throw once per iteration on a store-less
# root - but it is ONE scope, knowable at the call site, and the cure for it
# is the sentinel idiom the core's uninstall decision uses (set one variable
# before the sweep, remove it last), not a walk-level guard this check could
# express.
function Remove-ScopeChangeBlocks([string]$body) {
    $out = New-Object System.Collections.Generic.List[string]
    $skipAt = -1; $depth = 0
    foreach ($L in ($body -split "`n")) {
        $open  = ([regex]::Matches($L, '\{')).Count
        $close = ([regex]::Matches($L, '\}')).Count
        if ($skipAt -lt 0 -and $L -match '^\s*(scope:[A-Za-z0-9_]+|var:[A-Za-z0-9_]+|root|this)\s*\??=\s*\{') {
            $skipAt = $depth
            $depth += $open - $close
            if ($depth -le $skipAt) { $skipAt = -1 }
            continue
        }
        $depth += $open - $close
        if ($skipAt -ge 0) { if ($depth -le $skipAt) { $skipAt = -1 }; continue }
        [void]$out.Add($L)
    }
    return ($out -join "`n")
}

# set_variable and add_to_variable_list CREATE the store, so they cannot throw
# on an empty scope and are deliberately absent from this list.
$MUTATORS_RX = 'remove_variable|clear_variable_list|change_variable'

# Every top-level definition in all three trees, body kept, so a mutation
# reached through a tnt_*_effect CALL is visible too - which is the form that
# hid the core's own instance from a naive grep.
$defBodies = @{}
foreach ($t in $TREES) {
    foreach ($e in (Get-TreeFiles $t.Root @('.txt'))) {
        $lines = [System.IO.File]::ReadAllLines($e.File.FullName)
        $depth = 0; $cur = $null; $buf = $null
        foreach ($L in $lines) {
            $code = Strip-Code $L
            if ($depth -eq 0 -and $code -match '^([A-Za-z0-9_]+)\s*=\s*\{') {
                $cur = $Matches[1]; $buf = New-Object System.Text.StringBuilder
            }
            if ($cur) { [void]$buf.AppendLine($code) }
            $depth += ([regex]::Matches($code, '\{')).Count - ([regex]::Matches($code, '\}')).Count
            if ($depth -le 0) {
                $depth = 0
                if ($cur) { if (-not $defBodies.ContainsKey($cur)) { $defBodies[$cur] = $buf.ToString() }; $cur = $null }
            }
        }
    }
}
$mutEffects = New-Object System.Collections.Generic.HashSet[string]
foreach ($k in $defBodies.Keys) {
    if ((Remove-ScopeChangeBlocks $defBodies[$k]) -match ("\b({0})\s*=" -f $MUTATORS_RX)) { [void]$mutEffects.Add($k) }
}
# Transitive closure: an effect that calls a mutating effect mutates.
for ($round = 0; $round -lt 12; $round++) {
    $added = 0
    foreach ($k in @($defBodies.Keys)) {
        if ($mutEffects.Contains($k)) { continue }
        foreach ($m in [regex]::Matches((Remove-ScopeChangeBlocks $defBodies[$k]), '\b(tnt_[A-Za-z0-9_]*effect)\s*=')) {
            if ($mutEffects.Contains($m.Groups[1].Value)) { [void]$mutEffects.Add($k); $added++; break }
        }
    }
    if ($added -eq 0) { break }
}

$ITERATOR_RX = '\b((?:every|random|ordered)_[a-z_]+)\s*=\s*\{'
$walks = 0; $mutWalks = 0; $listWalks = 0; $engineWalks = 0
foreach ($t in $TREES) {
    foreach ($e in (Get-TreeFiles $t.Root @('.txt'))) {
        $lines = [System.IO.File]::ReadAllLines($e.File.FullName)
        for ($i = 0; $i -lt $lines.Count; $i++) {
            $code = Strip-Code $lines[$i]
            $mIter = [regex]::Match($code, $ITERATOR_RX)
            if (-not $mIter.Success) { continue }
            $iterName = $mIter.Groups[1].Value
            # A weighted choice, not an iterator - see the header.
            if ($iterName -eq 'random_list') { continue }
            # Brace-match the walk from its own keyword to its closing brace.
            $seg = $code.Substring($mIter.Index)
            $buf = New-Object System.Collections.Generic.List[string]
            $depth = 0; $j = $i
            while ($true) {
                [void]$buf.Add($seg)
                $depth += ([regex]::Matches($seg, '\{')).Count - ([regex]::Matches($seg, '\}')).Count
                if ($depth -le 0) { break }
                $j++
                if ($j -ge $lines.Count) { break }
                $seg = Strip-Code $lines[$j]
            }
            $raw = ($buf -join "`n")
            # Classified, NOT skipped: the 2026-08-24 widening. A variable-list
            # walk and an engine iterator obey the same store rule; only the
            # census line tells them apart.
            $isList = ($raw -match '(?m)^\s*variable\s*=')
            if ($isList) { $listWalks++ } else { $engineWalks++ }
            $walks++
            $own = Remove-ScopeChangeBlocks $raw
            $inline = ($own -match ("\b({0})\s*=" -f $MUTATORS_RX))
            $viaCall = $false
            foreach ($m in [regex]::Matches($own, '\b(tnt_[A-Za-z0-9_]*effect)\s*=')) {
                if ($mutEffects.Contains($m.Groups[1].Value)) { $viaCall = $true; break }
            }
            if (-not ($inline -or $viaCall)) { continue }
            $mutWalks++
            $guarded = ($own -match '(?m)^\s*limit\s*=\s*\{') -and ($own -match 'exists\s*=\s*var:')
            if (-not $guarded) {
                Write-Host ("  FAIL  {0} {1}:{2} - {3} mutates a member variable (inline={4}, via call={5}) with no limit carrying exists = var:" -f $t.Tag, $e.Rel, ($i + 1), $iterName, $inline, $viaCall)
                $fails++
            }
        }
    }
}
Write-Host ("  {0} mutating-effect names known; {1} iterator walk(s) - {2} over a variable list, {3} engine - {4} of them mutate a member variable" -f $mutEffects.Count, $walks, $listWalks, $engineWalks, $mutWalks)
Close-Check "9 store guard" $fails

# =============================================================================
# SUMMARY
# =============================================================================
Write-Host "================================================================"
$total = 0
foreach ($row in $SUMMARY) {
    $verdict = 'PASS'
    if ($row.Fails -gt 0) { $verdict = ("FAIL ({0})" -f $row.Fails) }
    Write-Host ("  CHECK {0,-22} {1}" -f $row.Check, $verdict)
    $total += $row.Fails
}
Write-Host "================================================================"
if ($total -eq 0) {
    Write-Host "PASS - all nine checks clean over all three trees."
    exit 0
}
Write-Host ("FAIL - {0} offender(s) across the family. Fix them or record a ruling; do not weaken the gate." -f $total)
exit 1
