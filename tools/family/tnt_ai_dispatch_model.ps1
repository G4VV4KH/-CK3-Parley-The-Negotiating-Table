# Offline regression model for the AI-to-player dispatcher, not a CK3 test.
# Read-only: source shape checks + a small, explicitly assumed event-order model.
# PASS proves neither CK3 queue ordering nor event-trigger re-evaluation.
# Calendar units below are normalized to 30-day months / 365-day years only
# inside the model; the actual script's literal duration ladder is checked too.
[CmdletBinding()]
param([string]$ParleyRoot = '')

$ErrorActionPreference = 'Stop'
if ($ParleyRoot -eq '') { $ParleyRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }

function Read-Code([string]$RelativePath) {
    $path = Join-Path $ParleyRoot $RelativePath
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing source: $path" }
    return [regex]::Replace([IO.File]::ReadAllText($path), '(?m)#.*$', '')
}
function Get-Block([string]$Code, [string]$Name) {
    $m = [regex]::Match($Code, '(?m)(?<![\w.])' + [regex]::Escape($Name) + '\s*=\s*\{')
    if (-not $m.Success) { throw "Missing source block: $Name" }
    $start = $m.Index + $m.Length
    $depth = 1
    $quoted = $false
    for ($i = $start; $i -lt $Code.Length; $i++) {
        $c = $Code[$i]
        if ($c -eq '"' -and ($i -eq 0 -or $Code[$i - 1] -ne '\')) { $quoted = -not $quoted }
        if ($quoted) { continue }
        if ($c -eq '{') { $depth++ }
        if ($c -eq '}') { $depth--; if ($depth -eq 0) { return $Code.Substring($start, $i - $start) } }
    }
    throw "Unclosed source block: $Name"
}
function Compact([string]$Code) { return [regex]::Replace($Code, '\s+', '') }

$script:Failures = New-Object 'System.Collections.Generic.List[string]'
$script:Checks = 0
function Check([bool]$Condition, [string]$Name) {
    $script:Checks++
    if (-not $Condition) { $script:Failures.Add($Name) }
}

try {
    $eventCode = Read-Code 'events\tnt_ai_events.txt'
    $offerCode = Read-Code 'common\scripted_effects\tnt_37_ai_offer.txt'
    $pulseCode = Read-Code 'common\on_action\tnt_71_ai.txt'
    $closeCode = Read-Code 'common\scripted_effects\tnt_30_effects.txt'
    $dispatcher = Get-Block $eventCode 'tnt_ai_offer.0001'
    $trigger = Compact (Get-Block $dispatcher 'trigger')
    $immediate = Get-Block $dispatcher 'immediate'
    $pick = Get-Block $offerCode 'tnt_ai_offer_try_effect'
    $recipient = Compact (Get-Block $offerCode 'tnt_ai_offer_recipient_cooldown_effect')
    $proposer = Compact (Get-Block $immediate 'scope:tnt_ai_proposer')
    $clear = Compact (Get-Block $offerCode 'tnt_ai_offer_clear_effect')
    $close = Compact (Get-Block $closeCode 'tnt_close_window_effect')

    # These are fail-closed shape assertions about the actual input files.
    # They are deliberately separate from the policy-algorithm tests below.
    $hasEngineFloor = [regex]::IsMatch($dispatcher, '(?<![\w])cooldown\s*=\s*\{')
    $hasPickReservation = [regex]::IsMatch($pick, 'name\s*=\s*tnt_ai_offer_cooldown\b')
    $guard = 'trigger_if={limit={NOT={has_game_rule=tnt_ai_offer_rate_test}}NOT={exists=var:tnt_ai_offer_cooldown}}'
    $hasRecipientGuard = $trigger.Contains($guard)
    Check (-not $hasEngineFloor) 'source: .0001 must have no engine cooldown'
    Check (-not $hasPickReservation) 'source: PICK must not reserve recipient cooldown'
    Check $hasRecipientGuard 'source: .0001 must check recipient cooldown except at test'
    foreach ($required in @('is_ai=no', 'NOT={has_game_rule=tnt_ai_offer_rate_off}',
        'exists=scope:tnt_ai_proposer', 'scope:tnt_ai_proposer={is_alive=yes}',
        'NOT={exists=var:tnt_open}', 'NOT={exists=var:tnt_partner}', 'NOT={exists=var:tnt_envoys_refused}')) {
        Check ($trigger.Contains($required)) ("source: dispatcher guard $required")
    }
    $dispatchIndex = $immediate.IndexOf('tnt_log_dispatch_effect')
    $proposerLockIndex = (Compact $immediate).IndexOf('name=tnt_ai_offer_cooldown')
    Check ($dispatchIndex -ge 0 -and $proposerLockIndex -ge 0 -and (Compact $immediate).IndexOf('tnt_log_dispatch_effect') -lt $proposerLockIndex) 'source: proposer lock follows actual DISPATCH'
    foreach ($row in @(
        'limit={has_game_rule=tnt_ai_offer_rate_test}set_variable={name=tnt_ai_offer_cooldownvalue=1days=30}',
        'limit={has_game_rule=tnt_ai_offer_rate_frequent}set_variable={name=tnt_ai_offer_cooldownvalue=1years=1}',
        'limit={has_game_rule=tnt_ai_offer_rate_rare}set_variable={name=tnt_ai_offer_cooldownvalue=1years=6}',
        'else={set_variable={name=tnt_ai_offer_cooldownvalue=1years=3}}')) {
        Check ($proposer.Contains($row)) 'source: unchanged proposer duration ladder'
    }
    foreach ($row in @(
        'NOT={exists=var:tnt_envoys_refused}', 'NOT={has_game_rule=tnt_ai_offer_rate_off}',
        'NOT={has_game_rule=tnt_ai_offer_rate_test}',
        'limit={has_game_rule=tnt_ai_offer_rate_frequent}set_variable={name=tnt_ai_offer_cooldownvalue=1months=6}',
        'limit={has_game_rule=tnt_ai_offer_rate_rare}set_variable={name=tnt_ai_offer_cooldownvalue=1years=3}',
        'else={set_variable={name=tnt_ai_offer_cooldownvalue=1years=1}}')) {
        Check ($recipient.Contains($row)) 'source: unchanged visible-recipient duration ladder'
    }
    foreach ($id in @('tnt_ai_offer.0002', 'tnt_ai_offer.0003')) {
        $visibleImmediate = Compact (Get-Block (Get-Block $eventCode $id) 'immediate')
        Check ($visibleImmediate -eq 'tnt_ai_offer_recipient_cooldown_effect=yes') "source: $id immediate owns recipient rate"
    }
    Check ([regex]::Matches($eventCode + $offerCode, 'tnt_ai_offer_recipient_cooldown_effect\s*=\s*yes\b').Count -eq 2) 'source: exactly two visible recipient-lock calls'
    $compactImmediate = Compact $immediate
    $partnerIndex = $compactImmediate.IndexOf('name=tnt_partner')
    $composeIndex = $compactImmediate.IndexOf('tnt_ai_compose_offer_effect=yes')
    Check ($partnerIndex -ge 0 -and $composeIndex -ge 0 -and $partnerIndex -lt $composeIndex) 'source: partner lock precedes composition'
    Check ([regex]::Matches($dispatcher, 'tnt_ai_offer_clear_effect\s*=\s*yes\b').Count -eq 2) 'source: both dispatcher abort paths clear draft'
    Check ($clear.Contains('tnt_close_window_effect=yes') -and $close.Contains('remove_variable=tnt_partner')) 'source: draft clear releases partner'
    Check (-not (($clear + $close).Contains('remove_variable=tnt_ai_offer_cooldown'))) 'source: clearing a draft/letter does not erase recipient rate'
    Check ([regex]::Matches($pulseCode, 'tnt_ai_offer_try_effect\s*=\s*yes\b').Count -eq 1) 'source: one pulse-to-try call'
    Check ([regex]::Matches($pulseCode, '(?m)^\s*tnt_ai_offer_pulse\s*$').Count -eq 1) 'source: one pulse registration'
    Check ((Compact (Get-Block $pulseCode 'ai_character_pulse')) -eq 'on_actions={tnt_ai_offer_pulse}') 'source: sole host is native AI character pulse'
    Check ((Compact (Get-Block (Get-Block $pulseCode 'tnt_ai_offer_pulse') 'trigger')).Contains('NOT={exists=var:tnt_ai_offer_cooldown}')) 'source: pulse respects proposer cooldown'
    Check ([regex]::Matches($eventCode + $offerCode, 'trigger_event\s*=\s*tnt_ai_offer\.0001\b').Count -eq 1) 'source: one dispatcher enqueue, no recursive event enqueue'
    Check ([regex]::Matches($pick, 'tnt_ai_offer_try_effect\s*=').Count -eq 0) 'source: try effect does not recurse'

    # A small policy model, NOT a Clausewitz/Jomini interpreter. Assumptions:
    # events execute serially; a queued event re-checks current trigger state;
    # immediate writes are visible to the next event; supplied draft outcomes
    # stand in for the unmodelled composer, threat math and game world.
    function New-State([string]$Rule = 'test') {
        return @{ Rule=$Rule; Open=$false; Partner=$false; Hush=$false;
            RecipientUntil=0; EngineUntil=0; ProposerUntil=@{}; Dispatches=0 }
    }
    function Dispatch($Policy, $State, [string]$Actor, [int]$Day, [string]$Draft = 'abort', [bool]$Alive = $true) {
        if ($State.Rule -eq 'off' -or $State.Hush -or $State.Open -or $State.Partner -or -not $Alive) { return 'guard_blocked' }
        if ($Policy.RecipientGuard -and $State.Rule -ne 'test' -and $Day -lt $State.RecipientUntil) { return 'recipient_blocked' }
        if ($Policy.EngineDays -gt 0 -and $Day -lt $State.EngineUntil) { return 'engine_blocked' }
        $State.Dispatches++
        $State.ProposerUntil[$Actor] = $Day + @{test=30; frequent=365; normal=1095; rare=2190}[$State.Rule]
        if ($Policy.EngineDays -gt 0) { $State.EngineUntil = $Day + $Policy.EngineDays }
        $State.Partner = $true
        if ($Draft -eq 'abort') { $State.Partner = $false; return 'composed_abort' }
        if ($State.Rule -ne 'test') { $State.RecipientUntil = $Day + @{frequent=180; normal=365; rare=1095}[$State.Rule] }
        return 'visible'
    }
    function Pick($Policy, $State, [string]$Actor, [int]$Day, [string]$Draft = 'abort') {
        if ($State.ProposerUntil.ContainsKey($Actor) -and $Day -lt $State.ProposerUntil[$Actor]) { return 'proposer_blocked' }
        if ($State.Rule -ne 'test' -and $Day -lt $State.RecipientUntil) { return 'recipient_blocked' }
        if ($Policy.ReservationDays -gt 0 -and $State.Rule -ne 'test') { $State.RecipientUntil = $Day + $Policy.ReservationDays }
        return (Dispatch $Policy $State $Actor $Day $Draft)
    }
    $currentPolicy = @{EngineDays=0; ReservationDays=0; RecipientGuard=$hasRecipientGuard}
    if ($hasEngineFloor) { $currentPolicy.EngineDays=15 }
    if ($hasPickReservation) { $currentPolicy.ReservationDays=15 }
    $oldPolicy = @{EngineDays=15; ReservationDays=15; RecipientGuard=$false}
    $negativeControls = 0

    foreach ($offset in @(0, 5)) {
        $newState = New-State
        $oldState = New-State
        Check ((Pick $currentPolicy $newState 'earlier_empty' 100) -eq 'composed_abort') "model: first draft aborts, offset $offset"
        $null = Pick $oldPolicy $oldState 'earlier_empty' 100
        $newResult = Pick $currentPolicy $newState 'Tekish' (100 + $offset) 'visible'
        $oldResult = Pick $oldPolicy $oldState 'Tekish' (100 + $offset) 'visible'
        Check ($newResult -eq 'visible') "model: later eligible proposer composes after empty draft, offset $offset"
        Check ($oldResult -eq 'engine_blocked' -and -not $oldState.ProposerUntil.ContainsKey('Tekish')) "negative control: old floor loses pick without charging proposer, offset $offset"
        if ($oldResult -ne $newResult) { $negativeControls++ }
    }
    foreach ($rule in @('frequent', 'normal', 'rare')) {
        foreach ($offset in @(0, 5)) {
            $emptyState = New-State $rule
            Check ((Pick $currentPolicy $emptyState 'empty' 100) -eq 'composed_abort') "model: empty $rule draft releases recipient"
            Check ((Pick $currentPolicy $emptyState 'later' (100 + $offset) 'visible') -eq 'visible') "model: $rule later candidate composes after abort, offset $offset"
        }
        $state = New-State $rule
        Check ((Pick $currentPolicy $state 'A' 100 'visible') -eq 'visible') "model: visible offer at $rule"
        Check ((Dispatch $currentPolicy $state 'B' 100 'visible') -eq 'guard_blocked') "model: queued B cannot overwrite visible A at $rule"
        $state.Partner = $false # player answers the visible letter
        Check ((Dispatch $currentPolicy $state 'B' 101 'visible') -eq 'recipient_blocked') "model: queued B still respects answered-letter rate at $rule"
        Check (-not $state.ProposerUntil.ContainsKey('B')) "model: dropped B has no proposer cooldown at $rule"
        $expiry = $state.RecipientUntil
        Check ((Dispatch $currentPolicy $state 'B' $expiry 'visible') -eq 'visible') "model: recipient can receive at modeled $rule expiry"
    }
    $state = New-State
    $null = Pick $currentPolicy $state 'A' 100 'visible'
    Check ((Dispatch $currentPolicy $state 'B' 100 'visible') -eq 'guard_blocked') 'model: test also protects unanswered visible A'
    $state.Partner = $false
    Check ((Dispatch $currentPolicy $state 'B' 100 'visible') -eq 'visible') 'model: test allows another letter after answer without a recipient rate lock'
    foreach ($flag in @('Hush', 'Open', 'Partner')) {
        $state = New-State
        $state[$flag] = $true
        Check ((Dispatch $currentPolicy $state 'A' 100 'visible') -eq 'guard_blocked' -and $state.ProposerUntil.Count -eq 0) "model: $flag blocks without charging proposer"
    }
    $state = New-State 'off'
    Check ((Dispatch $currentPolicy $state 'A' 100 'visible') -eq 'guard_blocked' -and $state.Dispatches -eq 0) 'model: off blocks dispatch'
    $state = New-State
    Check ((Dispatch $currentPolicy $state 'dead' 100 'visible' $false) -eq 'guard_blocked' -and $state.Dispatches -eq 0) 'model: dead proposer blocks dispatch'
    Check ($negativeControls -eq 2) 'model: both historical starvation controls must distinguish old policy from current'

    Write-Output 'OFFLINE ONLY: source-shape assertions and a serial-event policy model; NOT CK3 runtime validation.'
    Write-Output ("Checks: {0}; failures: {1}; old-policy starvation controls: {2}/2" -f $script:Checks, $script:Failures.Count, $negativeControls)
    if ($script:Failures.Count -gt 0) {
        foreach ($failure in $script:Failures) { Write-Output ("FAIL: " + $failure) }
        exit 1
    }
    Write-Output 'PASS: checked source contract + offline policy scenarios. Fresh engine smoke remains required.'
    exit 0
}
catch {
    Write-Output ('FAIL: ' + $_.Exception.Message)
    exit 2
}
