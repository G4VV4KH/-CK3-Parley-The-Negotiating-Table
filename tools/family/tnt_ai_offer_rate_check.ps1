# Source regression gate for visible-only AI-to-player recipient cooldown.
# This checks script structure and optional exact pre-patch semantic preservation;
# it does not simulate the CK3 event queue or replace a fresh runtime smoke test.
[CmdletBinding()]
param(
    [string]$ParleyRoot = '',
    [string]$BeforeDirectory = '',
    [string]$BeforeDispatchDirectory = '',
    [string]$EffectsPath = '',
    [string]$EventsPath = ''
)
$ErrorActionPreference = 'Stop'
if (-not $ParleyRoot) { $ParleyRoot = Join-Path $PSScriptRoot '..\..' }
$script:RateFailures = 0
function Assert-Rate([bool]$Condition, [string]$Label) {
    if ($Condition) { Write-Host "PASS $Label" }
    else { Write-Host "FAIL $Label"; $script:RateFailures++ }
}
function Get-RateCode([string]$Text) {
    $withoutComments = [regex]::Replace($Text, '(?m)#.*$', '')
    return [regex]::Replace($withoutComments, '[\s\uFEFF]+', '')
}
function Get-RateBlock([string]$Code, [string]$Name) {
    # Whitespace removal can join a preceding scalar to the next identifier.
    # Match the complete assignment shape, not a word boundary on canonical code.
    $match = [regex]::Match($Code, [regex]::Escape($Name) + '=\{')
    if (-not $match.Success) { throw "Missing block $Name" }
    $depth = 1
    $cursor = $match.Index + $match.Length
    while ($cursor -lt $Code.Length -and $depth -gt 0) {
        if ($Code[$cursor] -eq '{') { $depth++ }
        elseif ($Code[$cursor] -eq '}') { $depth-- }
        $cursor++
    }
    if ($depth -ne 0) { throw "Unbalanced block $Name" }
    return $Code.Substring($match.Index, $cursor - $match.Index)
}
$rateEffectsPath = if ($EffectsPath) { $EffectsPath } else { Join-Path $ParleyRoot 'common\scripted_effects\tnt_37_ai_offer.txt' }
$rateEventsPath = if ($EventsPath) { $EventsPath } else { Join-Path $ParleyRoot 'events\tnt_ai_events.txt' }
$rateEffects = Get-RateCode ([IO.File]::ReadAllText($rateEffectsPath))
$rateEvents = Get-RateCode ([IO.File]::ReadAllText($rateEventsPath))
$rateHelperName = 'tnt_ai_offer_recipient_cooldown_effect'
$rateHelper = Get-RateBlock $rateEffects $rateHelperName
$rateExpectedHelper = Get-RateCode @'
tnt_ai_offer_recipient_cooldown_effect = {
 if = {
  limit = {
   is_ai = no
   NOT = { exists = var:tnt_envoys_refused }
   NOT = { has_game_rule = tnt_ai_offer_rate_off }
   NOT = { has_game_rule = tnt_ai_offer_rate_test }
  }
  if = {
   limit = { has_game_rule = tnt_ai_offer_rate_frequent }
   set_variable = { name = tnt_ai_offer_cooldown value = 1 months = 6 }
  }
  else_if = {
   limit = { has_game_rule = tnt_ai_offer_rate_rare }
   set_variable = { name = tnt_ai_offer_cooldown value = 1 years = 3 }
  }
  else = {
   set_variable = { name = tnt_ai_offer_cooldown value = 1 years = 1 }
  }
 }
}
'@
Assert-Rate ($rateHelper -ceq $rateExpectedHelper) 'visible rate: player only, hush/off/test no-op, frequent 6m / rare 3y / normal 1y'
$rateReservation = Get-RateCode @'
if = {
 limit = { NOT = { has_game_rule = tnt_ai_offer_rate_test } }
 set_variable = { name = tnt_ai_offer_cooldown value = 1 days = 15 }
}
'@
$rateTry = Get-RateBlock $rateEffects 'tnt_ai_offer_try_effect'
Assert-Rate (-not $rateTry.Contains('name=tnt_ai_offer_cooldown')) 'PICK writes no provisional recipient or proposer cooldown'
Assert-Rate (([regex]::Matches($rateTry, 'trigger_event=tnt_ai_offer\.0001')).Count -eq 1) 'PICK has one hidden-event call'
Assert-Rate (([regex]::Matches($rateTry, [regex]::Escape('trigger_if={limit={NOT={has_game_rule=tnt_ai_offer_rate_test}}NOT={exists=var:tnt_ai_offer_cooldown}}'))).Count -eq 4) 'all candidate/final gates retain visible-rate filtering'
Assert-Rate (-not $rateTry.Contains($rateHelperName + '=yes')) 'PICK cannot promote to long cooldown'
$rateHidden = Get-RateBlock $rateEvents 'tnt_ai_offer.0001'
Assert-Rate (-not $rateHidden.Contains('cooldown={')) 'hidden composer has no shared engine cooldown'
Assert-Rate (-not $rateHidden.Contains('on_trigger_fail={')) 'a rejected queued competitor cannot clear another live letter'
$rateNewGuards = Get-RateCode @'
NOT = { has_game_rule = tnt_ai_offer_rate_off }
trigger_if = {
 limit = { NOT = { has_game_rule = tnt_ai_offer_rate_test } }
 NOT = { exists = var:tnt_ai_offer_cooldown }
}
'@
$rateExpectedTrigger = Get-RateCode @'
trigger = {
 is_ai = no
 NOT = { has_game_rule = tnt_ai_offer_rate_off }
 trigger_if = {
  limit = { NOT = { has_game_rule = tnt_ai_offer_rate_test } }
  NOT = { exists = var:tnt_ai_offer_cooldown }
 }
 exists = scope:tnt_ai_proposer
 scope:tnt_ai_proposer = { is_alive = yes }
 NOT = { exists = var:tnt_open }
 NOT = { exists = var:tnt_partner }
 NOT = { exists = var:tnt_envoys_refused }
}
'@
Assert-Rate ((Get-RateBlock $rateHidden 'trigger') -ceq $rateExpectedTrigger) 'hidden trigger rechecks off/visible-rate/busy/envoys/live-proposer guards'
Assert-Rate (-not $rateHidden.Contains($rateHelperName + '=yes')) 'hidden composer and both abort paths cannot promote cooldown'
$rateImmediate = 'immediate={' + $rateHelperName + '=yes}'
foreach ($rateId in @('tnt_ai_offer.0002', 'tnt_ai_offer.0003')) {
    $rateVisible = Get-RateBlock $rateEvents $rateId
    $rateActualImmediate = Get-RateBlock $rateVisible 'immediate'
    Assert-Rate ($rateActualImmediate -ceq $rateImmediate) "$rateId promotes only in its visible immediate"
}
Assert-Rate (([regex]::Matches($rateEvents, [regex]::Escape($rateHelperName + '=yes'))).Count -eq 2) 'exactly two promotion callers'
$rateClear = Get-RateBlock $rateEffects 'tnt_ai_offer_clear_effect'
Assert-Rate (-not $rateClear.Contains('tnt_ai_offer_cooldown')) 'generic clear preserves visible recipient cooldown'
foreach ($ratePath in @($rateEffectsPath, $rateEventsPath)) {
    $rateBytes = [IO.File]::ReadAllBytes($ratePath)
    $rateText = [Text.Encoding]::UTF8.GetString($rateBytes)
    Assert-Rate ($rateBytes.Length -ge 3 -and $rateBytes[0] -eq 239 -and $rateBytes[1] -eq 187 -and $rateBytes[2] -eq 191 -and ([regex]::Matches($rateText, [string][char]65279)).Count -eq 1 -and -not $rateText.Contains("`r")) ("BOM exactly at byte0 / LF: " + [IO.Path]::GetFileName($ratePath))
}
# Reverse just the dispatch fix into its two-phase predecessor. The older
# BeforeDirectory argument remains supported for the original visible-rate fix.
$rateReversedDispatchEffects = $rateEffects.Replace('trigger_event=tnt_ai_offer.0001', $rateReservation + 'trigger_event=tnt_ai_offer.0001')
$rateReversedDispatchHidden = $rateHidden.Replace('hidden=yestrigger={is_ai=no' + $rateNewGuards, 'hidden=yescooldown={days=15}trigger={is_ai=no')
$rateReversedDispatchEvents = $rateEvents.Replace($rateHidden, $rateReversedDispatchHidden)
if ($BeforeDispatchDirectory) {
    $ratePriorEffects = Get-RateCode ([IO.File]::ReadAllText((Join-Path $BeforeDispatchDirectory 'tnt_37_ai_offer.txt')))
    $ratePriorEvents = Get-RateCode ([IO.File]::ReadAllText((Join-Path $BeforeDispatchDirectory 'tnt_ai_events.txt')))
    Assert-Rate ($rateReversedDispatchEffects -ceq $ratePriorEffects) 'dispatch reverse: all effects logic preserved except removal of provisional reservation'
    Assert-Rate ($rateReversedDispatchEvents -ceq $ratePriorEvents) 'dispatch reverse: all event logic preserved except engine-floor removal and entry guards'
}
if ($BeforeDirectory) {
    $rateBeforeEffects = Get-RateCode ([IO.File]::ReadAllText((Join-Path $BeforeDirectory 'tnt_37_ai_offer.txt')))
    $rateBeforeEvents = Get-RateCode ([IO.File]::ReadAllText((Join-Path $BeforeDirectory 'tnt_ai_events.txt')))
    $rateOldLadder = Get-RateCode @'
if = {
 limit = { has_game_rule = tnt_ai_offer_rate_frequent }
 set_variable = { name = tnt_ai_offer_cooldown value = 1 months = 6 }
}
else_if = {
 limit = { has_game_rule = tnt_ai_offer_rate_rare }
 set_variable = { name = tnt_ai_offer_cooldown value = 1 years = 3 }
}
else_if = {
 limit = { NOT = { has_game_rule = tnt_ai_offer_rate_test } }
 set_variable = { name = tnt_ai_offer_cooldown value = 1 years = 1 }
}
'@
    $rateReversedEffects = $rateReversedDispatchEffects.Replace($rateHelper, '').Replace($rateReservation + 'trigger_event=tnt_ai_offer.0001', $rateOldLadder + 'trigger_event=tnt_ai_offer.0001')
    $rateReversedEvents = $rateReversedDispatchEvents.Replace($rateImmediate, '')
    Assert-Rate ($rateReversedEffects -ceq $rateBeforeEffects) 'reverse patch restores all effects code exactly (no unrelated logic change)'
    Assert-Rate ($rateReversedEvents -ceq $rateBeforeEvents) 'reverse patch restores all event code exactly (proposer/fairness/triggers/options unchanged)'
}
if ($script:RateFailures -gt 0) {
    Write-Host "FAIL: $script:RateFailures source regressions"
    exit 1
}
Write-Host 'PASS: visible-only recipient rate source contract; CK3 runtime still requires validation.'
exit 0
