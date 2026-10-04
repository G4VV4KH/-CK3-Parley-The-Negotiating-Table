########################################################################################
# PARLEY: THE NEGOTIATING TABLE - OFFLINE MODEL OF THE BALANCE FORMULA + TEST SUITE
# User item 22, second half: "if needed - write a sandbox system of algorithmic tests
# of the model."
#
# ======================================================================================
# 0. WHY THIS FILE IS SAFE TO PUT HERE, AND THE PROOF
# ======================================================================================
# CK3 mounts mod content by TOP-LEVEL DIRECTORY NAME. The complete set of top-level
# names the game knows is the set it ships itself, measured this session under
# <game> :
#     common  content_source  data_binding  dlc  dlc_metadata  events  fonts  gfx
#     gui  history  licenses  localization  map_data  music  notifications
#     reader_export  sound  tests  tools  tweakergui_assets
# This mod populates exactly five of them - common\, gui\, events\, localization\,
# data_binding\ - and nothing else. `_docs` is not one of the twenty names, so NOTHING
# under _docs\ is ever opened, parsed or validated by the game.
#
# NOTE THE ONE TRAP, because it is one character away from being real: vanilla DOES have
# a top-level `tools\`. Ours is `_docs\tools\`, i.e. NESTED, and the matching is on the
# top-level name only. Do not "tidy" this file up one level into a bare `tools\`.
#
# ASCII ONLY, DELIBERATELY, same rule as tnt_37_ai_offer.txt and tnt_39_autobalance.txt.
# Windows PowerShell 5.1 reads a BOM-less UTF-8 .ps1 as the system ANSI codepage, so a
# single accented character here would become mojibake or a parse error on someone
# else's machine. Keeping the file pure ASCII removes the question instead of answering
# it, and it is why this file carries NO BOM and needs none.
#
# ======================================================================================
# 1. HOW TO RUN IT
# ======================================================================================
#     powershell -NoProfile -ExecutionPolicy Bypass -File .\tnt_balance_model.ps1
# or, to load the model and poke at it by hand:
#     . .\tnt_balance_model.ps1 -NoRun
#     $s = New-TntState @{ Opinion = -100; GoldP = 1000 }
#     TntHeadline $s
#
# Exit code 0 = every test passed. Exit code 1 = at least one test FAILED, and a failure
# is a finding about the mod, not about the harness - see section 4.
#
# ======================================================================================
# 2. WHAT EACH TEST PROVES
# ======================================================================================
#   I1  An EMPTY treaty reads EXACTLY 0, for every partner in the game. This is the
#       whole point of the multiplicative model: with nothing on the table the unit is
#       zero, and zero times any relationship is zero. Swept over every combination of
#       the seven relationship rows and the threshold's three AI axes.
#   I2  Measures the bounded rounding residue between pos - neg and the once-rounded
#       headline. The two halves set the bar's magnitude, not its verdict direction.
#       I2b asks the question the player actually cares about - does the bar agree with
#       the verdict - and I2c locks the two formerly failing zero-headline examples.
#   I3  A strictly generous deal can never read below 0, at opinion -100 with every
#       modifier hostile and the threshold maxed. This is what tnt_deal_floor_value
#       exists for: contempt VOIDS gifts, it never INVERTS them.
#   I4  Monotonicity. Adding value to the table can never LOWER the headline. Swept
#       across opinion -100..+100, across four modifier stacks, and across the ally
#       glut - which is where the last I4 break lived (the deleted -15-per-ally row in
#       tnt_relmod_ally_value).
#   I5  The demands column is NOT scaled by the modifier multiplier. One gold demanded
#       is worth exactly 1/tnt_gold_per_point_value of a point whatever the partner
#       thinks of us - which is also the arithmetic tnt_ab_exact_land_effect relies on.
#       Asserted on the UNROUNDED headline, because the invariant is about SCALING;
#       I5b measures the rounding residue separately instead of confusing the two.
#   I6  Every item's price is >= 0 in its own value. Signs live in gain vs loss, never
#       inside a price. Tested hardest on the alliance, whose bias block CAN go to -110.
#   A1  tnt_ab_exact_land_effect lands the headline on EXACTLY +1, swept over a spread
#       of partner wallets - and, when the partner is too poor, leaves it above +1 with
#       his purse emptied rather than mis-landing.
#   A2  The full auto-balance button (MARGIN 1 / CEILING 1) converges to +1 from BOTH
#       directions - a deficit it must sweeten and a surplus it must collect on.
#   A3  Item 22's exploit closure: the more allies the ASKER already holds, the less an
#       alliance is worth to the partner, so the more the asker must add to buy the same
#       county. Serial alliance-selling stops paying.
#   A4  A threat cannot be repeated against the same victim while the opinion modifier
#       that records the last one is still on him.
#
# ======================================================================================
# 3. WHAT THIS MODEL CANNOT CAPTURE - READ BEFORE TRUSTING A GREEN RUN
# ======================================================================================
# Every one of these is an APPROXIMATION, and each is a real way the game could disagree
# with this file:
#   * ARITHMETIC TYPE. CK3 script values are CFixedPoint (fixed point, 5 decimal
#     places); this model uses IEEE doubles. The two diverge in the last decimal, which
#     matters only where a value sits exactly on a .5 boundary before `round = yes`.
#   * ROUNDING MODE. `round = yes` is assumed to be round-half-away-from-zero. PDX
#     documents no mode. If the engine rounds half-to-even, the I2 slop measured below
#     shifts by up to one point in the cases that land on a half.
#   * SCOPE RESOLUTION. The whole scope:tnt_me / scope:tnt_p / scope:actor prologue
#     dance is ASSUMED to succeed. If `var:tnt_partner ?= { save_temporary_scope_as }`
#     silently fails in some context, the affected row reads 0 in game and reads its
#     real number here. That is exactly the class of defect this model is blind to, and
#     it is why the mod's runtime log (tnt_3b_log.txt) exists.
#   * PER-ITEM PRICES OTHER THAN THE FOUR CURRENCIES AND THE ALLIANCE. Titles, claims,
#     artifacts, prisoners, marriages, hooks, the nine obligations and item 19's four
#     people terms are modelled as PARAMETERS (LumpyP / LumpyR / ObligationsP) rather
#     than recomputed from their own script values. The invariants are all statements
#     about the AGGREGATE, so a parameterised bucket tests them exactly - but a
#     mispriced marriage would not be caught here.
#   * THE LUMPY LADDER (tnt_39_autobalance.txt section D) is NOT modelled. The
#     auto-balance model walks currencies only. A real surplus press against a pauper
#     partner would additionally take a county; this model reports "still above +1".
#   * GAME STATE. Wallets, ally counts, dread, opinion and traits are inputs here and
#     facts there. Where the real quantity is unknowable the test sweeps a range and
#     says so.
#   * THE ENGINE MAY REJECT AN ENTRY OUTRIGHT. Defect D1 (a non-existent trigger made
#     the engine discard a whole script value, scoring culture 0 in every deal ever
#     made) is invisible to this file by construction: the model implements what the
#     script MEANS, not whether the engine accepted it.
#
# ======================================================================================
# 4. CLOSED FINDING - WHY THE BAR READS THE HEADLINE DIRECTLY
# ======================================================================================
# Before the 2026-08-27 fix, I2b and I2c exposed a real defect. Three summands that
# reach the two halves can carry no `round = yes` of their own -
#       tnt_deal_floor_value        (added to pos by V5 item 8)
#       tnt_val_threat_p_value      (its own header says "No `round` here")
#       tnt_val_usehook_r_value     (subtracted from neg)
# - while the headline is rounded once at the end. So pos - neg can be a small
#   positive fraction on a treaty whose headline rounds to exactly 0, and 0 DECLINES.
#   The old bar then sat just past 50 while the verdict icon said no. The fix keeps
#   pos + neg as the magnitude denominator but derives the signed distance from 50
#   directly from tnt_ai_accept_value. Rounding components was rejected because it
#   changed the real headline in 521 of 11,520 modelled cases and flipped acceptance
#   in three. The chosen formula changes only rendering and cannot drift in sign.
#
# I5 initially failed too and that WAS a harness artefact: it asserted the scaling
# invariant on the ROUNDED headline, so a table that straddled a half boundary read as
# a scaling break. Rewritten to assert on the unrounded arithmetic (where it holds to
# the last decimal, 0 mismatches in 336 cases) with the rounding measured separately as
# I5b. The distinction is recorded here so nobody "re-tightens" it back into a lie.
#
# ======================================================================================
# 5. IF A TEST FAILS
# ======================================================================================
# It is a finding about the mod. Do not adjust the test to pass. The model was derived
# by reading these files on disk, at these paths, in this state:
#   common\script_values\tnt_50_values.txt        gain/loss/unit/floor/threshold/headline
#   common\script_values\tnt_51_relation_values.txt   the seven relmod rows
#   common\script_values\tnt_53_currency_values.txt   3 unit prices, deficit/surplus/mult
#   common\script_values\tnt_57_threat_values.txt     the threat
#   common\script_values\tnt_59_usehook_values.txt    both hook rows + pressure
#   common\scripted_effects\tnt_39_autobalance.txt    sweeten / trim / pay / exact land
#   common\scripted_guis\tnt_22_v2.txt                the button's MARGIN / CEILING
#   common\scripted_triggers\tnt_41_gates.txt         the threat gates
########################################################################################

param(
    [switch]$NoRun,
    [switch]$Verbose2
)

$ErrorActionPreference = 'Stop'


########################################################################################
# SECTION A - THE MODEL
########################################################################################

# `round = yes`. See section 3 for why the mode is an assumption.
function TntRound {
    param([double]$X)
    return [Math]::Round($X, 0, [System.MidpointRounding]::AwayFromZero)
}

function TntClamp {
    param([double]$X, [double]$Lo, [double]$Hi)
    if ($X -lt $Lo) { return $Lo }
    if ($X -gt $Hi) { return $Hi }
    return $X
}

# ---------------------------------------------------------------------------------
# The world, the two rulers and the table, in one flat bag. Defaults describe two
# equal dukes who are strangers to each other and have nothing on the table - the
# state in which the window must read exactly 0 (I1).
# ---------------------------------------------------------------------------------
function New-TntState {
    param([hashtable]$Override)
    $s = @{
        # --- the two rulers ------------------------------------------------------
        # highest_held_title_tier: barony 1, county 2, duchy 3, kingdom 4, empire 5
        # (confirmed by tnt_prestige_per_point_value's own min: 7.5 + 1.25*(1+1) = 10)
        PlayerTier          = 3
        PartnerTier         = 3
        PlayerStrength      = 5000     # current_military_strength
        PartnerStrength     = 5000
        PlayerMaxMil        = 5000     # max_military_strength, threat only
        PartnerMaxMil       = 5000
        PlayerAllies        = 0        # non-vassal, non-liege allies
        PartnerAllies       = 0
        PlayerAtWar         = $false
        PartnerAtWar        = $false

        # --- the seven relationship rows (tnt_51_relation_values.txt) -------------
        Opinion             = 0        # -100..100, straight through as a percentage
        Faith               = 'same'   # same | different | hostile
        Culture             = 'same'   # same | heritage | foreign
        KinFamily           = $false
        KinDynasty          = $false
        Friendship          = 'none'   # best_friend | friend | none
        Lover               = $false
        Enmity              = 'none'   # nemesis | rival | none
        AlliedAlready       = $false

        # --- the threshold (tnt_threshold_value) ----------------------------------
        AiGreed             = 0        # about -100..+100
        AiBoldness          = 0
        AiRationality       = 0

        # --- partner personality riders on the three soft currencies --------------
        PartnerArrogant     = $false
        PartnerHumble       = $false
        PartnerZealous      = $false
        PartnerAmbitious    = $false
        PartnerContent      = $false

        # --- alliance -------------------------------------------------------------
        # The imported bias block (traits + claims + standing) as ONE number. It is a
        # sum of eight trait rows, two claim rows and six standing rows, all of which
        # are pure lookups on facts this model does not otherwise carry; its real range
        # is about -110..+210 and the term's own clamp is what I6 tests.
        AllianceBias        = 0

        # --- pressure -------------------------------------------------------------
        ThreatDread         = 0        # tnt_threat_dread_value: 0, 1 or 2
        PlayerPrestigeLevel = 0        # 0..5
        UseHookPStrength    = 0        # 0 none, 1 weak, 2 strong (ours on him)
        UseHookRStrength    = 0        # 0 none, 1 weak, 2 strong (his on us)
        ThreatSpent         = $false   # victim already carries tnt_threat_opinion from us

        # --- wallets --------------------------------------------------------------
        PlayerGold          = 1000
        PartnerGold         = 1000
        PlayerPrestige      = 1000
        PartnerPrestige     = 1000
        PlayerPiety         = 1000
        PartnerPiety        = 1000
        PlayerInfluence     = 0
        PartnerInfluence    = 0
        InfluenceOk         = $false   # tnt_influence_ok_value > 0: BOTH governments
        RulePrestigeOn      = $true    # tnt_trade_prestige_on
        RulePietyOn         = $true    # tnt_trade_piety_on

        # --- the table ------------------------------------------------------------
        GoldP = 0; GoldR = 0
        PrestigeP = 0; PrestigeR = 0
        PietyP = 0; PietyR = 0
        InfluenceP = 0; InfluenceR = 0
        AllianceP = $false
        ThreatP = $false
        UseHookPOn = $false
        UseHookROn = $false

        # --- everything priced in a file this model does not re-implement ---------
        # LumpyP / LumpyR are ALREADY IN POINTS and >= 0 (I6). ObligationsP is the nine
        # vassal-contract rows, pre-signed from the partner's point of view, so it is
        # the one member of the gain column that may legitimately be negative.
        LumpyP = 0
        LumpyR = 0
        ObligationsP = 0
    }
    if ($Override) {
        foreach ($k in $Override.Keys) {
            if (-not $s.ContainsKey($k)) { throw "New-TntState: unknown key '$k'" }
            $s[$k] = $Override[$k]
        }
    }
    return $s
}

function CopyTntState {
    param($S)
    $c = @{}
    foreach ($k in $S.Keys) { $c[$k] = $S[$k] }
    return $c
}


# --- THE FOUR UNIT PRICES ----------------------------------------------------------
# tnt_gold_per_point_value (tnt_50_values.txt sec 4.A): 10, +5 once the PARTNER is duke
# or above. Flat thereafter - vanilla's bribe tier multiplier saturates at duke.
function TntGoldPerPoint { param($S)
    $v = 10.0
    if ($S.PartnerTier -ge 3) { $v += 5.0 }
    if ($v -lt 1) { $v = 1.0 }
    return $v
}
# tnt_53_currency_values.txt sec 1b: base + 1.25 * (my tier + his tier), floored at the
# formula's own two-barony value.
function TntPrestigePerPoint { param($S)
    return [Math]::Max(10.0,  7.5 + 1.25 * ($S.PlayerTier + $S.PartnerTier))
}
function TntPietyPerPoint { param($S)
    return [Math]::Max(7.5,   5.0 + 1.25 * ($S.PlayerTier + $S.PartnerTier))
}
function TntInfluencePerPoint { param($S)
    return [Math]::Max(7.5,   5.0 + 1.25 * ($S.PlayerTier + $S.PartnerTier))
}

# The three soft currencies read the PARTNER'S traits on BOTH sides: he prizes what he
# is handed and minds what he gives up, by the same factor (tnt_53 sec 2).
function TntPrestigeRider { param($S)
    if ($S.PartnerArrogant) { return 1.5 }
    if ($S.PartnerHumble)   { return 0.5 }
    return 1.0
}
function TntPietyRider { param($S)
    if ($S.PartnerZealous) { return 1.5 }
    return 1.0
}
function TntInfluenceRider { param($S)
    if ($S.PartnerAmbitious) { return 1.5 }
    if ($S.PartnerContent)   { return 0.5 }
    return 1.0
}


# --- THE ALLIANCE, THE ONE ITEM PRICED IN FULL HERE --------------------------------
# tnt_power_ratio_value: player strength over partner strength, 0.2 .. 5.
function TntPowerRatio { param($S)
    $a = [Math]::Max(1.0, [double]$S.PlayerStrength)
    $b = [Math]::Max(1.0, [double]$S.PartnerStrength)
    return (TntClamp ($a / $b) 0.2 5.0)
}
# tnt_ally_glut_self_value / tnt_ally_glut_partner_value. Vanilla's MSM:181-204 shape:
# x0.5 per non-vassal non-liege ally once he has two, written as a rung ladder because
# `every_ally = { multiply }` is unproven inside this mod's script values.
#     0-1 -> 1      2 -> 0.25      3 -> 0.125      4+ -> 0.0625 (the min)
function TntAllyGlut { param([int]$N)
    $m = 1.0
    if ($N -ge 2) { $m *= 0.25 }
    if ($N -ge 3) { $m *= 0.5 }
    if ($N -ge 4) { $m *= 0.5 }
    if ($m -lt 0.0625) { $m = 0.0625 }
    return $m
}
# tnt_val_alliance_p_value. ONE mutual term, priced once, from the partner's point of
# view. There is deliberately no _r twin (tnt_val_alliance_r_value is a hard zero).
function TntValAllianceP { param($S)
    if (-not $S.AllianceP) { return 0.0 }
    $v = 40.0 * (TntPowerRatio $S)
    if ($S.PartnerAtWar) { $v *= 1.5 }
    if ($S.PlayerAtWar)  { $v *= 0.5 }
    $v *= (TntAllyGlut $S.PlayerAllies)
    $v *= (TntAllyGlut $S.PartnerAllies)
    $v += $S.AllianceBias
    return (TntClamp $v 0.0 150.0)
}


# --- THE TWO COLUMN TOTALS ---------------------------------------------------------
function TntGainTotal { param($S)
    $g = 0.0
    $g += $S.GoldP / (TntGoldPerPoint $S)
    if ($S.PrestigeP -gt 0) { $g += ($S.PrestigeP / (TntPrestigePerPoint $S)) * (TntPrestigeRider $S) }
    if ($S.PietyP    -gt 0) { $g += ($S.PietyP    / (TntPietyPerPoint    $S)) * (TntPietyRider    $S) }
    if ($S.InfluenceP -gt 0 -and $S.InfluenceOk) {
        $g += ($S.InfluenceP / (TntInfluencePerPoint $S)) * (TntInfluenceRider $S)
    }
    $g += TntValAllianceP $S
    $g += $S.LumpyP
    $g += $S.ObligationsP      # the one legitimately signed member
    return (TntRound $g)
}

function TntLossTotal { param($S)
    $l = 0.0
    $l += $S.GoldR / (TntGoldPerPoint $S)
    if ($S.PrestigeR -gt 0) { $l += ($S.PrestigeR / (TntPrestigePerPoint $S)) * (TntPrestigeRider $S) }
    if ($S.PietyR    -gt 0) { $l += ($S.PietyR    / (TntPietyPerPoint    $S)) * (TntPietyRider    $S) }
    if ($S.InfluenceR -gt 0 -and $S.InfluenceOk) {
        $l += ($S.InfluenceR / (TntInfluencePerPoint $S)) * (TntInfluenceRider $S)
    }
    # NO alliance and NO truce row here: both are single mutual terms priced once in
    # the gain column. Putting them back is the double count v3 item ADD-4 removed.
    $l += $S.LumpyR
    return (TntRound $l)
}

# tnt_gain_positive_value / tnt_gain_scale_unit_value: one per cent of the offer,
# floored at zero so that hatred can VOID a gift but never invert it.
function TntGainPositive { param($S) return [Math]::Max(0.0, [double](TntGainTotal $S)) }
function TntUnit         { param($S) return (TntGainPositive $S) / 100.0 }


# --- THE SEVEN RELATIONSHIP ROWS, EACH A PERCENTAGE OF THE OFFER --------------------
function TntRelmodOpinion { param($S) return (TntClamp ([double]$S.Opinion) -100.0 100.0) }
function TntRelmodFaith { param($S)
    if ($S.Faith -eq 'hostile')   { return -35.0 }
    if ($S.Faith -eq 'different') { return -10.0 }
    return 0.0
}
function TntRelmodCulture { param($S)
    if ($S.Culture -eq 'same')    { return 5.0 }
    if ($S.Culture -eq 'foreign') { return -10.0 }   # not even the same heritage
    return 0.0                                        # same heritage, different culture
}
function TntRelmodKin { param($S)
    $v = 0.0
    if ($S.KinFamily)  { $v += 10.0 }
    if ($S.KinDynasty) { $v += 10.0 }
    return $v
}
function TntRelmodRelation { param($S)
    $v = 0.0
    if     ($S.Friendship -eq 'best_friend') { $v += 35.0 }
    elseif ($S.Friendship -eq 'friend')      { $v += 20.0 }
    if ($S.Lover) { $v += 15.0 }
    if     ($S.Enmity -eq 'nemesis') { $v += -50.0 }
    elseif ($S.Enmity -eq 'rival')   { $v += -35.0 }
    return $v
}
function TntRelmodWar  { param($S) if ($S.PartnerAtWar)   { return 10.0 } return 0.0 }
function TntRelmodAlly { param($S) if ($S.AlliedAlready)  { return 10.0 } return 0.0 }
# THE DREAD ROW HAS NO CALLER since the threat option was added - it priced the same
# fear twice. It is deliberately absent from BOTH the headline and the panel figure,
# so it is absent here too.

function TntRelmodSum7 { param($S)
    return (TntRelmodOpinion $S) + (TntRelmodFaith $S) + (TntRelmodCulture $S) +
           (TntRelmodKin $S) + (TntRelmodRelation $S) + (TntRelmodWar $S) + (TntRelmodAlly $S)
}

# --- THE THRESHOLD, A 0..40 PERCENTAGE ----------------------------------------------
# min / max, THEN round - which is what makes the printed figure and the summed figure
# the same integer.
function TntThreshold { param($S)
    $v = 0.0
    $v += 0.10 * $S.AiGreed
    $v += 0.05 * $S.AiBoldness
    $v -= 0.05 * $S.AiRationality
    $tierEdge = $S.PlayerTier - $S.PartnerTier      # > 0 means the PLAYER is ahead
    if ($tierEdge -le -2)   { $v += 20.0 }
    elseif ($tierEdge -lt 0) { $v += 10.0 }
    $v = TntClamp $v 0.0 40.0
    return (TntRound $v)
}

# tnt_deal_mod_sum_value: the whole modifier stack in per cent.
function TntModSum { param($S) return (TntRelmodSum7 $S) - (TntThreshold $S) }
# tnt_deal_mult_value: the same thing as one multiplier, floored at 0.
function TntDealMult { param($S) return [Math]::Max(0.0, (100.0 + (TntModSum $S)) / 100.0) }
# tnt_ab_mult_floor_value: safe to divide by.
function TntMultFloor { param($S) return [Math]::Max(0.1, (TntDealMult $S)) }

# tnt_deal_floor_value: exactly the shortfall, so that offer*(100+S)/100 becomes
# offer*max(0,100+S)/100. An algebraic identity, not a new rule.
function TntDealFloor { param($S)
    $v = [Math]::Max(0.0, -(100.0 + (TntModSum $S)))
    return $v * (TntUnit $S)
}

# --- PRESSURE: OUTSIDE THE GIFT TOTAL ON PURPOSE ------------------------------------
function TntThreatEdge { param($S)
    $them = [Math]::Max(1.0, [double]$S.PartnerMaxMil)
    return (TntClamp (([double]$S.PlayerMaxMil / $them) - 1.0) 0.0 2.0)
}
function TntValThreatP { param($S)
    if (-not $S.ThreatP) { return 0.0 }
    $v = 25.0 * (TntThreatEdge $S) * $S.ThreatDread * $S.PlayerPrestigeLevel
    return (TntClamp $v 0.0 150.0)
}
function TntValUseHookP { param($S)
    if (-not $S.UseHookPOn) { return 0.0 }
    if ($S.UseHookPStrength -ge 2) { return 120.0 }
    if ($S.UseHookPStrength -ge 1) { return 45.0 }
    return 0.0
}
# NEGATIVE by construction: a debt he can call in makes him more DEMANDING.
function TntValUseHookR { param($S)
    if (-not $S.UseHookROn) { return 0.0 }
    if ($S.UseHookRStrength -ge 2) { return -120.0 }
    if ($S.UseHookRStrength -ge 1) { return -45.0 }
    return 0.0
}
function TntValPressureP { param($S) return (TntValThreatP $S) + (TntValUseHookP $S) }

# --- THE HEADLINE --------------------------------------------------------------------
#   gain - loss + 7 relmod rows x unit - threshold x unit + floor + threat + hookP + hookR
# and `> 0` means accept. Exactly 0 declines.
function TntHeadlineRaw { param($S)
    $unit = TntUnit $S
    $x  = [double](TntGainTotal $S)
    $x -= [double](TntLossTotal $S)
    $x += (TntRelmodSum7 $S) * $unit
    $x -= (TntThreshold $S) * $unit
    $x += TntDealFloor $S
    $x += TntValThreatP $S
    $x += TntValUseHookP $S
    $x += TntValUseHookR $S
    return $x
}
function TntHeadline { param($S) return (TntRound (TntHeadlineRaw $S)) }

# --- THE PANEL'S FOUR FIGURES AND THE TWO-SIDED BAR ----------------------------------
function TntRelationMod     { param($S) return (TntRound ((TntRelmodSum7 $S) * (TntUnit $S))) }
function TntThresholdDelta  { param($S) return (TntRound (-1.0 * (TntThreshold $S) * (TntUnit $S))) }

function TntAcceptPos { param($S)
    $v = [double](TntGainTotal $S)
    $rm = TntRelationMod $S
    if ($rm -gt 0) { $v += $rm }
    $v += TntValPressureP $S
    $v += TntDealFloor $S
    return $v
}
function TntAcceptNeg { param($S)
    $v = [double](TntLossTotal $S)
    $v -= TntThresholdDelta $S          # the delta is <= 0, so this ADDS magnitude
    $v -= TntValUseHookR $S             # <= 0, same reasoning
    $rm = TntRelationMod $S
    if ($rm -lt 0) { $v -= $rm }
    return $v
}
function TntVerdictRatio { param($S)
    $p = TntAcceptPos $S
    $n = TntAcceptNeg $S
    $den = [Math]::Max(1.0, $p + $n + 2.0)
    return (TntClamp (50.0 + (50.0 * (TntHeadline $S) / $den)) 0.0 100.0)
}
# 1..5 bucket for the tilting scales, on vanilla's own band edges.
function TntBalanceFrame { param($S)
    $h = TntHeadline $S
    if ($h -ge 75)  { return 5 }
    if ($h -ge 20)  { return 4 }
    if ($h -le -75) { return 1 }
    if ($h -le -20) { return 2 }
    return 3
}


########################################################################################
# SECTION B - THE AUTO-BALANCE MACHINERY (tnt_39_autobalance.txt sections C and the
# exact landing). MARGIN and CEILING travel as variables because a script value cannot
# take a parameter; here they are plain arguments.
#
# NOT MODELLED: section D, the lumpy ladder. When the partner's purse cannot cover a
# surplus the real button takes a county, a claim or his fealty; this model reports the
# treaty as still above +1. Flagged in section 3 and re-flagged at its call site.
########################################################################################

function TntDeficit { param($S, [double]$Margin)  return [Math]::Max(0.0, $Margin - (TntHeadline $S)) }
function TntSurplus { param($S, [double]$Ceiling) return [Math]::Max(0.0, (TntHeadline $S) - $Ceiling) }

# C7 - one sweeten pass: raise the PLAYER's column. Every step divides by the multiplier
# because this column is `offer`, and the headline scales offer.
function TntSweetenPass { param($S, [double]$Margin)
    $mf = TntMultFloor $S
    if ((TntDeficit $S $Margin) -gt 0 -and $S.GoldP -lt 5000 -and $S.PlayerGold -ge 1) {
        $add = (TntDeficit $S $Margin) * (TntGoldPerPoint $S) / $mf
        $S.GoldP = TntClamp (TntRound ($S.GoldP + $add)) 0 5000
        $S.GoldP = TntClamp $S.GoldP 0 $S.PlayerGold
    }
    if ($S.RulePrestigeOn -and (TntDeficit $S $Margin) -gt 0 -and $S.PrestigeP -lt 10000 -and $S.PlayerPrestige -ge 1) {
        $add = (TntDeficit $S $Margin) * (TntPrestigePerPoint $S) / $mf
        $S.PrestigeP = TntClamp (TntRound ($S.PrestigeP + $add)) 0 10000
        $S.PrestigeP = TntClamp $S.PrestigeP 0 $S.PlayerPrestige
    }
    if ($S.RulePietyOn -and (TntDeficit $S $Margin) -gt 0 -and $S.PietyP -lt 10000 -and $S.PlayerPiety -ge 1) {
        $add = (TntDeficit $S $Margin) * (TntPietyPerPoint $S) / $mf
        $S.PietyP = TntClamp (TntRound ($S.PietyP + $add)) 0 10000
        $S.PietyP = TntClamp $S.PietyP 0 $S.PlayerPiety
    }
    if ((TntDeficit $S $Margin) -gt 0 -and $S.InfluenceP -lt 1000 -and $S.InfluenceOk -and $S.PlayerInfluence -ge 1) {
        $add = (TntDeficit $S $Margin) * (TntInfluencePerPoint $S) / $mf
        $S.InfluenceP = TntClamp (TntRound ($S.InfluenceP + $add)) 0 1000
        $S.InfluenceP = TntClamp $S.InfluenceP 0 $S.PlayerInfluence
    }
}

# C8 - one trim pass: lower the PLAYER's column. No affordability clamp is needed on
# this side; an amount can only become MORE affordable as it falls.
function TntTrimPass { param($S, [double]$Ceiling)
    $mf = TntMultFloor $S
    if ((TntSurplus $S $Ceiling) -gt 0 -and $S.GoldP -gt 0) {
        $sub = (TntSurplus $S $Ceiling) * (TntGoldPerPoint $S) / $mf
        $S.GoldP = TntClamp (TntRound ($S.GoldP - $sub)) 0 5000
    }
    if ($S.RulePrestigeOn -and (TntSurplus $S $Ceiling) -gt 0 -and $S.PrestigeP -gt 0) {
        $sub = (TntSurplus $S $Ceiling) * (TntPrestigePerPoint $S) / $mf
        $S.PrestigeP = TntClamp (TntRound ($S.PrestigeP - $sub)) 0 10000
    }
    if ($S.RulePietyOn -and (TntSurplus $S $Ceiling) -gt 0 -and $S.PietyP -gt 0) {
        $sub = (TntSurplus $S $Ceiling) * (TntPietyPerPoint $S) / $mf
        $S.PietyP = TntClamp (TntRound ($S.PietyP - $sub)) 0 10000
    }
    if ((TntSurplus $S $Ceiling) -gt 0 -and $S.InfluenceP -gt 0) {
        $sub = (TntSurplus $S $Ceiling) * (TntInfluencePerPoint $S) / $mf
        $S.InfluenceP = TntClamp (TntRound ($S.InfluenceP - $sub)) 0 1000
    }
}

# C9 - one pay pass: raise the PARTNER's column. NO divide by the multiplier: the
# demands side is not scaled, and dividing it would be the mirror of the sweeten bug.
function TntPayPass { param($S, [double]$Ceiling)
    if ((TntSurplus $S $Ceiling) -gt 0 -and $S.GoldR -lt 5000 -and $S.PartnerGold -ge 1) {
        $add = (TntSurplus $S $Ceiling) * (TntGoldPerPoint $S)
        $S.GoldR = TntClamp (TntRound ($S.GoldR + $add)) 0 5000
        $S.GoldR = TntClamp $S.GoldR 0 $S.PartnerGold
    }
    if ($S.RulePrestigeOn -and (TntSurplus $S $Ceiling) -gt 0 -and $S.PrestigeR -lt 10000 -and $S.PartnerPrestige -ge 1) {
        $add = (TntSurplus $S $Ceiling) * (TntPrestigePerPoint $S)
        $S.PrestigeR = TntClamp (TntRound ($S.PrestigeR + $add)) 0 10000
        $S.PrestigeR = TntClamp $S.PrestigeR 0 $S.PartnerPrestige
    }
    if ($S.RulePietyOn -and (TntSurplus $S $Ceiling) -gt 0 -and $S.PietyR -lt 10000 -and $S.PartnerPiety -ge 1) {
        $add = (TntSurplus $S $Ceiling) * (TntPietyPerPoint $S)
        $S.PietyR = TntClamp (TntRound ($S.PietyR + $add)) 0 10000
        $S.PietyR = TntClamp $S.PietyR 0 $S.PartnerPiety
    }
    if ((TntSurplus $S $Ceiling) -gt 0 -and $S.InfluenceR -lt 1000 -and $S.InfluenceOk -and $S.PartnerInfluence -ge 1) {
        $add = (TntSurplus $S $Ceiling) * (TntInfluencePerPoint $S)
        $S.InfluenceR = TntClamp (TntRound ($S.InfluenceR + $add)) 0 1000
        $S.InfluenceR = TntClamp $S.InfluenceR 0 $S.PartnerInfluence
    }
}

# tnt_ab_exact_land_effect - THE EXACT LANDING, and the reason "+1" is literal rather
# than "about +1". Gold on the `_r` column is not scaled by anything, so one
# multiplication is exact and a 1-gold-at-a-time loop would be pure waste.
function TntExactLand { param($S)
    if ((TntHeadline $S) -gt 1 -and $S.PartnerGold -ge 1) {
        $add = ((TntHeadline $S) - 1.0) * (TntGoldPerPoint $S)
        $S.GoldR = TntClamp (TntRound ($S.GoldR + $add)) 0 5000
        $S.GoldR = TntClamp $S.GoldR 0 $S.PartnerGold      # the wallet clamp stays last
    }
}

# C1 - the player's button. tnt_22_v2.txt passes MARGIN = 1 / CEILING = 1.
function Invoke-TntAutobalance {
    param($S, [double]$Margin = 1, [double]$Ceiling = 1)
    if ((TntDeficit $S $Margin) -gt 0) {
        TntSweetenPass $S $Margin
        $n = 0
        while ($n -lt 2 -and (TntDeficit $S $Margin) -gt 0) { TntSweetenPass $S $Margin; $n++ }
    }
    elseif ((TntSurplus $S $Ceiling) -gt 0) {
        TntPayPass $S $Ceiling
        $n = 0
        while ($n -lt 3 -and (TntSurplus $S $Ceiling) -gt 0) { TntPayPass $S $Ceiling; $n++ }
        # >>> THE LUMPY LADDER (section D) WOULD RUN HERE. NOT MODELLED. <<<
        if ((TntSurplus $S $Ceiling) -gt 0) {
            TntTrimPass $S $Ceiling
            $n = 0
            while ($n -lt 2 -and (TntSurplus $S $Ceiling) -gt 0) { TntTrimPass $S $Ceiling; $n++ }
        }
        if ((TntDeficit $S $Margin) -gt 0) { TntSweetenPass $S $Margin }   # the safety top-up
    }
    TntExactLand $S
}

# C2 - the AI composer's settle-up. tnt_37_ai_offer.txt passes MARGIN 1 / CEILING 1 and
# the loops carry count = 6. It never calls the lumpy ladder, by design.
function Invoke-TntAiPricebalance {
    param($S, [double]$Margin = 1, [double]$Ceiling = 1)
    if ((TntDeficit $S $Margin) -gt 0) {
        TntSweetenPass $S $Margin
        $n = 0
        while ($n -lt 6 -and (TntDeficit $S $Margin) -gt 0) { TntSweetenPass $S $Margin; $n++ }
    }
    elseif ((TntSurplus $S $Ceiling) -gt 0) {
        TntPayPass $S $Ceiling
        $n = 0
        while ($n -lt 6 -and (TntSurplus $S $Ceiling) -gt 0) { TntPayPass $S $Ceiling; $n++ }
        if ((TntDeficit $S $Margin) -gt 0) { TntSweetenPass $S $Margin }
    }
    TntExactLand $S
}


########################################################################################
# SECTION C - THE THREAT GATE (tnt_41_gates.txt, tnt_can_threat_trigger)
########################################################################################
function TntCanThreat { param($S)
    if ($S.PlayerMaxMil -le $S.PartnerMaxMil) { return $false }   # tnt_err_threat_weak
    if ($S.PlayerPrestigeLevel -lt 1)         { return $false }   # tnt_err_threat_unknown
    if ($S.ThreatDread -lt 1)                 { return $false }   # tnt_err_threat_unafraid
    if ($S.ThreatSpent)                       { return $false }   # tnt_err_threat_recent
    return $true
}


########################################################################################
# SECTION D - THE HARNESS
########################################################################################
$script:TntPass = 0
$script:TntFail = 0
$script:TntFailLines = @()

function TntTest {
    param([string]$Name, [bool]$Ok, [string]$Detail)
    if ($Ok) {
        $script:TntPass++
        Write-Host ("  PASS  {0,-52} {1}" -f $Name, $Detail)
    } else {
        $script:TntFail++
        $script:TntFailLines += ("{0}  ::  {1}" -f $Name, $Detail)
        Write-Host ("  FAIL  {0,-52} {1}" -f $Name, $Detail) -ForegroundColor Red
    }
}
function TntSection { param([string]$T) Write-Host ""; Write-Host ("== " + $T) }


########################################################################################
# SECTION E - THE SCENARIOS THE INVARIANTS ARE SWEPT OVER
########################################################################################

# Four named modifier stacks, from "he adores you" to "he loathes you", used wherever a
# test says "across the modifier stack".
$TntStacks = @(
    @{ Name = 'devoted';  Over = @{ Opinion =  100; Faith='same';      Culture='same';     KinFamily=$true;  KinDynasty=$true;  Friendship='best_friend'; Lover=$true;  Enmity='none';    AlliedAlready=$true;  AiGreed=-100; AiBoldness=-100; AiRationality=100 } },
    @{ Name = 'warm';     Over = @{ Opinion =   40; Faith='same';      Culture='heritage'; KinFamily=$false; KinDynasty=$false; Friendship='friend';      Lover=$false; Enmity='none';    AlliedAlready=$false; AiGreed=0;    AiBoldness=0;    AiRationality=0 } },
    @{ Name = 'stranger'; Over = @{ Opinion =    0; Faith='different'; Culture='heritage'; KinFamily=$false; KinDynasty=$false; Friendship='none';        Lover=$false; Enmity='none';    AlliedAlready=$false; AiGreed=40;   AiBoldness=20;   AiRationality=0 } },
    @{ Name = 'loathing'; Over = @{ Opinion = -100; Faith='hostile';   Culture='foreign';  KinFamily=$false; KinDynasty=$false; Friendship='none';        Lover=$false; Enmity='nemesis'; AlliedAlready=$false; AiGreed=100;  AiBoldness=100;  AiRationality=-100 } }
)

function TntStackState {
    param([hashtable]$Stack, [hashtable]$Extra)
    $o = @{}
    foreach ($k in $Stack.Keys) { $o[$k] = $Stack[$k] }
    if ($Extra) { foreach ($k in $Extra.Keys) { $o[$k] = $Extra[$k] } }
    return (New-TntState $o)
}


########################################################################################
# SECTION F - THE TESTS
########################################################################################

function Run-TntSuite {

    Write-Host ""
    Write-Host "PARLEY - offline balance model, scenario suite"
    Write-Host ("run at {0}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))

    # ==================================================================================
    TntSection "I1 - an EMPTY treaty reads EXACTLY 0, for every partner"
    # ==================================================================================
    # The window opens on a stranger, a nemesis and a best friend alike and must read 0,
    # with no special case anywhere. This is the property the whole multiplicative model
    # was built to get, and it is the cheapest one to break by adding a flat row.
    $n = 0; $worst = 0.0; $worstDesc = ''
    foreach ($op in @(-100, -50, 0, 50, 100)) {
    foreach ($fa in @('same','different','hostile')) {
    foreach ($cu in @('same','heritage','foreign')) {
    foreach ($en in @('none','rival','nemesis')) {
    foreach ($fr in @('none','friend','best_friend')) {
    foreach ($ai in @(-100, 0, 100)) {
    foreach ($te in @(-2, 0, 2)) {
        $s = New-TntState @{
            Opinion = $op; Faith = $fa; Culture = $cu; Enmity = $en; Friendship = $fr
            AiGreed = $ai; AiBoldness = $ai; AiRationality = (-$ai)
            PlayerTier = (3 + $te); PartnerTier = 3
            KinFamily = $true; KinDynasty = $true; Lover = $true
            AlliedAlready = $true; PartnerAtWar = $true
        }
        $h = TntHeadline $s
        $n++
        if ([Math]::Abs($h) -gt [Math]::Abs($worst)) { $worst = $h; $worstDesc = "$op/$fa/$cu/$en/$fr/ai$ai/tier$te" }
    }}}}}}}
    TntTest "I1 empty treaty == 0" ($worst -eq 0) ("$n partner profiles swept; worst headline = $worst" + $(if ($worst -ne 0) { " at $worstDesc" } else { "" }))

    # Same claim one level down: the unit itself must be 0, or a later row could revive
    # the flat-offset behaviour without I1 noticing.
    $s = New-TntState @{ Opinion = -100; Faith = 'hostile'; AiGreed = 100 }
    TntTest "I1 unit and both column totals are 0" (((TntUnit $s) -eq 0) -and ((TntGainTotal $s) -eq 0) -and ((TntLossTotal $s) -eq 0)) `
        ("unit=" + (TntUnit $s) + " gain=" + (TntGainTotal $s) + " loss=" + (TntLossTotal $s))

    # ==================================================================================
    TntSection "I2 - bounded decomposition residue and an authoritative bar direction"
    # ==================================================================================
    # The two magnitudes no longer decide which side of 50 the bar occupies; the
    # authoritative headline does. Their difference remains a useful diagnostic for
    # accidental omissions. Independent relation/threshold rounding plus fractional
    # floor/pressure can leave a residue; the current sweep requires it to stay <= 1.
    $maxDev = 0.0; $maxDesc = ''; $over1 = 0; $cases = 0
    foreach ($st in $TntStacks) {
    foreach ($gp in @(0, 37, 150, 733, 2000)) {
    foreach ($gr in @(0, 23, 199, 1111)) {
    foreach ($pp in @(0, 313)) {
    foreach ($lp in @(0, 17, 61)) {
    foreach ($lr in @(0, 29)) {
    foreach ($ob in @(0, -23)) {
    foreach ($th in @($false, $true)) {
    foreach ($hk in @(0, 1, 2)) {
        $s = TntStackState $st.Over @{
            GoldP = $gp; GoldR = $gr; PrestigeP = $pp; LumpyP = $lp; LumpyR = $lr
            ObligationsP = $ob
            ThreatP = $th; ThreatDread = 2; PlayerPrestigeLevel = 3
            PlayerMaxMil = 12000; PartnerMaxMil = 7000
            UseHookROn = ($hk -gt 0); UseHookRStrength = $hk
        }
        $dev = ((TntAcceptPos $s) - (TntAcceptNeg $s)) - (TntHeadline $s)
        $cases++
        if ([Math]::Abs($dev) -gt 1.0000001) { $over1++ }
        if ([Math]::Abs($dev) -gt [Math]::Abs($maxDev)) {
            $maxDev = $dev
            $maxDesc = ("{0} gp={1} gr={2} pp={3} lp={4} lr={5} ob={6} threat={7} hookR={8}" -f $st.Name,$gp,$gr,$pp,$lp,$lr,$ob,$th,$hk)
        }
    }}}}}}}}}
    TntTest "I2 |pos-neg-headline| <= 1" ([Math]::Abs($maxDev) -le 1.0000001) `
        ("$cases cases; max deviation = " + [Math]::Round($maxDev,4) + "; cases over 1 = $over1" + $(if ($over1 -gt 0) { "; worst at $maxDesc" } else { "" }))

    # ------------------------------------------------------------------------------
    # I2b - THE PROPERTY THAT ACTUALLY MATTERS TO THE PLAYER.
    #
    # The two halves can carry a different rounding path from the headline, so their
    # difference is diagnostic only. TntVerdictRatio uses the headline for direction
    # and their sum for scale; therefore the halfway mark must always match acceptance.
    # ------------------------------------------------------------------------------
    $bad = 0; $cases = 0; $examples = @()
    foreach ($st in $TntStacks) {
    foreach ($gp in @(0, 50, 150, 400, 900, 2500)) {
    foreach ($gr in @(0, 100, 500, 1500)) {
        $s = TntStackState $st.Over @{ GoldP = $gp; GoldR = $gr }
        $h = TntHeadline $s
        $r = TntVerdictRatio $s
        $cases++
        if (($h -gt 0) -ne ($r -gt 50)) {
            $bad++
            if ($examples.Count -lt 4) {
                $examples += ("{0}: gold_p={1} gold_r={2} -> headline={3} (DECLINES) but pos={4} neg={5} ratio={6}" -f `
                    $st.Name, $gp, $gr, $h, [Math]::Round((TntAcceptPos $s),3), [Math]::Round((TntAcceptNeg $s),3), [Math]::Round($r,3))
            }
        }
    }}}
    TntTest "I2b bar > 50 <=> headline > 0" ($bad -eq 0) "$cases cases; disagreements = $bad"
    foreach ($e in $examples) { Write-Host ("          " + $e) }

    # Regression for both concrete marginal tables that exposed the old visual drift.
    $zeroOk = $true; $zeroDetails = @()
    foreach ($gold in @(400, 2500)) {
        $s = TntStackState $TntStacks[3].Over @{ GoldP = $gold }
        $h = TntHeadline $s
        $r = TntVerdictRatio $s
        if (($h -ne 0) -or ([Math]::Abs($r - 50.0) -gt 0.000001)) { $zeroOk = $false }
        $zeroDetails += ("gold_p=$gold headline=$h ratio=" + [Math]::Round($r,6))
    }
    TntTest "I2c zero headline renders exactly 50" $zeroOk ($zeroDetails -join '; ')

    # And how often it bites, over a wider sweep, so the size of the defect is on record.
    $bad2 = 0; $tot2 = 0
    foreach ($st in $TntStacks) {
    foreach ($k in 0..80) {
    foreach ($gr in @(0, 50, 150, 300, 600, 1000)) {
        $s = TntStackState $st.Over @{ GoldP = ($k * 25); GoldR = $gr }
        $tot2++
        if (((TntHeadline $s) -gt 0) -ne ((TntVerdictRatio $s) -gt 50)) { $bad2++ }
    }}}
    Write-Host ("          frequency over a wider sweep: {0} of {1} tables ({2}%)" -f $bad2, $tot2, [Math]::Round(100.0*$bad2/$tot2,2))

    # ==================================================================================
    TntSection "I3 - a pure gift can never read below 0"
    # ==================================================================================
    # Opinion -100, hostile faith, foreign heritage, a nemesis, and a greedy bold
    # unreasoning partner two tiers above the player - the worst modifier stack the mod
    # can produce. tnt_deal_floor_value is what keeps this at 0 instead of driving it
    # monotonically negative, which was the reported bug.
    $minH = 999999.0; $minAt = ''
    $cases = 0
    foreach ($gp in 0..200) {
        $gold = $gp * 25
        $s = TntStackState $TntStacks[3].Over @{ GoldP = $gold; PlayerTier = 1; PartnerTier = 3 }
        $h = TntHeadline $s
        $cases++
        if ($h -lt $minH) { $minH = $h; $minAt = "gold_p=$gold" }
    }
    foreach ($pp in @(0, 100, 500, 2000, 10000)) {
        $s = TntStackState $TntStacks[3].Over @{ PrestigeP = $pp; PartnerArrogant = $true; PlayerTier = 1; PartnerTier = 5 }
        $h = TntHeadline $s
        $cases++
        if ($h -lt $minH) { $minH = $h; $minAt = "prestige_p=$pp" }
    }
    TntTest "I3 pure gift headline >= 0" ($minH -ge 0) "$cases gift sizes at the worst stack; minimum headline = $minH ($minAt)"

    # And the mod's own reading of it: at S <= -100 more gold changes nothing at all.
    $s1 = TntStackState $TntStacks[3].Over @{ GoldP = 1000 }
    $s2 = TntStackState $TntStacks[3].Over @{ GoldP = 5000 }
    TntTest "I3b contempt VOIDS gifts, never inverts them" (((TntHeadline $s1) -eq 0) -and ((TntHeadline $s2) -eq 0)) `
        ("1000 gold -> " + (TntHeadline $s1) + " ; 5000 gold -> " + (TntHeadline $s2) + " ; modifier sum S = " + (TntModSum $s1))

    # ==================================================================================
    TntSection "I4 - monotonicity: adding value never LOWERS the headline"
    # ==================================================================================
    # Swept across the whole opinion range and every modifier stack. This is the
    # invariant the old gated -15-per-ally relmod row broke: ticking a box switched on a
    # penalty, so ADDING a term made the deal worse.
    $violations = 0; $worst = 0.0; $worstDesc = ''; $cases = 0
    foreach ($st in $TntStacks) {
    foreach ($op in -100..10 | Where-Object { $_ % 10 -eq 0 }) {
        $prev = $null
        foreach ($g in 0..60) {
            $gold = $g * 50
            $s = TntStackState $st.Over @{ Opinion = $op; GoldP = $gold; GoldR = 300; LumpyR = 12 }
            $h = TntHeadline $s
            $cases++
            if ($null -ne $prev -and $h -lt $prev) {
                $violations++
                $d = $prev - $h
                if ($d -gt $worst) { $worst = $d; $worstDesc = ("{0} opinion={1} gold {2}->{3}: {4}->{5}" -f $st.Name,$op,($gold-50),$gold,$prev,$h) }
            }
            $prev = $h
        }
    }}
    TntTest "I4 gold monotone (opinion sweep x 4 stacks)" ($violations -eq 0) `
        ("$cases samples; violations = $violations" + $(if ($violations -gt 0) { "; worst drop $worst at $worstDesc" } else { "" }))

    # The same, over the full +-100 opinion range and with the OTHER three currencies.
    $violations = 0; $cases = 0
    foreach ($st in $TntStacks) {
    foreach ($op in @(-100,-75,-50,-25,0,25,50,75,100)) {
    foreach ($cur in @('PrestigeP','PietyP','LumpyP')) {
        $prev = $null
        foreach ($k in 0..40) {
            $amt = $k * 25
            $extra = @{ Opinion = $op; GoldR = 200; PartnerArrogant = $true; PartnerZealous = $true }
            $extra[$cur] = $amt
            $s = TntStackState $st.Over $extra
            $h = TntHeadline $s
            $cases++
            if ($null -ne $prev -and $h -lt $prev) { $violations++ }
            $prev = $h
        }
    }}}
    TntTest "I4b prestige / piety / lumpy monotone" ($violations -eq 0) "$cases samples; violations = $violations"

    # I4 across the ally glut: ticking the alliance box must never lower the headline,
    # at any ally count on either side. This is the exact shape of the deleted bug.
    $violations = 0; $cases = 0
    foreach ($st in $TntStacks) {
    foreach ($mine in 0..6) {
    foreach ($his in 0..6) {
    foreach ($bias in @(-110, -40, 0, 60, 210)) {
        $base = TntStackState $st.Over @{ PlayerAllies = $mine; PartnerAllies = $his; AllianceBias = $bias; GoldP = 200; GoldR = 400 }
        $with = TntStackState $st.Over @{ PlayerAllies = $mine; PartnerAllies = $his; AllianceBias = $bias; GoldP = 200; GoldR = 400; AllianceP = $true }
        $cases++
        if ((TntHeadline $with) -lt (TntHeadline $base)) { $violations++ }
    }}}}
    TntTest "I4c ticking the alliance never lowers the headline" ($violations -eq 0) "$cases ally/bias combinations; violations = $violations"

    # ==================================================================================
    TntSection "I5 - the demands column is NOT scaled by the multiplier"
    # ==================================================================================
    # One gold demanded is worth exactly 1/tnt_gold_per_point_value of a point, whatever
    # he thinks of us. If this ever stops being true, tnt_ab_exact_land_effect's single
    # multiplication stops landing on +1 and the AI's letters drift again.
    #
    # THE ASSERTION IS ON THE UNROUNDED HEADLINE, AND THAT IS THE HONEST FORM OF THE
    # CLAIM. The invariant is about SCALING - "the demands column is not multiplied by
    # anything" - and it holds to the last decimal. Asserting it on the ROUNDED headline
    # instead conflates it with `round = yes`, which can move the figure by a further
    # point when the two tables land on opposite sides of a half boundary (see I5b).
    # That is a rounding fact, not a scaling one, and running the two together would
    # have reported a false break of I5.
    $bad = 0; $cases = 0; $badDesc = ''
    foreach ($st in $TntStacks) {
    foreach ($op in @(-100,-60,-20,0,20,60,100)) {
    foreach ($tier in @(2, 3, 5)) {
        $gpp = 10.0; if ($tier -ge 3) { $gpp = 15.0 }
        foreach ($pts in @(1, 5, 20, 60)) {
            $a = TntStackState $st.Over @{ Opinion = $op; PartnerTier = $tier; GoldP = 900; GoldR = 0 }
            $b = TntStackState $st.Over @{ Opinion = $op; PartnerTier = $tier; GoldP = 900; GoldR = ($pts * $gpp) }
            $drop = (TntHeadlineRaw $a) - (TntHeadlineRaw $b)
            $cases++
            if ([Math]::Abs($drop - $pts) -gt 0.000001) {
                $bad++
                if (-not $badDesc) { $badDesc = ("{0} op={1} tier={2} pts={3}: drop={4}" -f $st.Name,$op,$tier,$pts,$drop) }
            }
        }
    }}}
    TntTest "I5 a demand of N points always costs exactly N" ($bad -eq 0) `
        ("$cases cases across 4 stacks x 7 opinions x 3 tiers; mismatches = $bad" + $(if ($bad -gt 0) { "; first at $badDesc" } else { "" }))

    # I5b - the same measurement on the ROUNDED headline, recorded rather than asserted
    # away. The residue is entirely the outer `round = yes`, and it is bounded by 1.
    $maxDev = 0.0; $cases = 0
    foreach ($st in $TntStacks) {
    foreach ($op in @(-100,-60,-20,0,20,60,100)) {
    foreach ($tier in @(2, 3, 5)) {
        $gpp = 10.0; if ($tier -ge 3) { $gpp = 15.0 }
        foreach ($pts in @(1, 5, 20, 60)) {
            $a = TntStackState $st.Over @{ Opinion = $op; PartnerTier = $tier; GoldP = 900; GoldR = 0 }
            $b = TntStackState $st.Over @{ Opinion = $op; PartnerTier = $tier; GoldP = 900; GoldR = ($pts * $gpp) }
            $dev = [Math]::Abs(((TntHeadline $a) - (TntHeadline $b)) - $pts)
            $cases++
            if ($dev -gt $maxDev) { $maxDev = $dev }
        }
    }}}
    TntTest "I5b rounding adds at most 1 point to a demand" ($maxDev -le 1.0000001) `
        "$cases cases; max |printed drop - true drop| = $maxDev"

    # ==================================================================================
    TntSection "I6 - every item's price is >= 0 in its own value"
    # ==================================================================================
    # Signs live in gain vs loss, never inside a price. The alliance is the hard case:
    # its imported bias block really does reach -110, and only its own `min = 0` stops
    # the term paying the player to take an alliance back.
    $minAll = 999999.0; $maxAll = -999999.0; $cases = 0
    foreach ($mine in 0..5) {
    foreach ($his in 0..5) {
    foreach ($bias in @(-110,-60,-20,0,20,60,120,210)) {
    foreach ($ratio in @(0.2, 0.5, 1.0, 2.5, 5.0)) {
    foreach ($pw in @($true,$false)) {
    foreach ($mw in @($true,$false)) {
        $s = New-TntState @{
            AllianceP = $true; PlayerAllies = $mine; PartnerAllies = $his; AllianceBias = $bias
            PlayerStrength = [int](5000 * $ratio); PartnerStrength = 5000
            PartnerAtWar = $pw; PlayerAtWar = $mw
        }
        $v = TntValAllianceP $s
        $cases++
        if ($v -lt $minAll) { $minAll = $v }
        if ($v -gt $maxAll) { $maxAll = $v }
    }}}}}}
    TntTest "I6 alliance price stays inside [0,150]" (($minAll -ge 0) -and ($maxAll -le 150)) `
        "$cases combinations; range = [$minAll .. $maxAll]"

    $bad = 0
    foreach ($st in $TntStacks) {
        $s = TntStackState $st.Over @{ GoldP = 700; PrestigeP = 400; PietyP = 400; LumpyP = 33; GoldR = 500; PrestigeR = 300; LumpyR = 44; PartnerHumble = $true }
        if ((TntGainTotal $s) -lt 0 -or (TntLossTotal $s) -lt 0) { $bad++ }
    }
    TntTest "I6b both column totals are >= 0 with no signed obligations" ($bad -eq 0) "4 stacks; negatives = $bad"

    # ==================================================================================
    TntSection "A1 - the AI settle lands the headline on EXACTLY +1"
    # ==================================================================================
    # The partner's actual gold is the quantity the model cannot know, so it is swept.
    # Below the price of the overshoot the honest outcome is "his purse is empty and the
    # deal stays above +1" - which the test asserts rather than excuses.
    $rows = @()
    $bad = 0
    foreach ($wallet in @(0, 5, 40, 150, 400, 1200, 5000, 100000)) {
        $s = New-TntState @{
            LumpyP = 60; GoldP = 300         # a fat offer: headline lands well above +1
            PartnerGold = $wallet
            Opinion = 20
        }
        $before = TntHeadline $s
        TntExactLand $s
        $after = TntHeadline $s
        $need = ($before - 1) * (TntGoldPerPoint $s)
        $ok = $false
        if ($wallet -ge $need) { $ok = ($after -eq 1) }
        else { $ok = (($after -gt 1) -and ($s.GoldR -eq [Math]::Min($wallet, 5000))) }
        if (-not $ok) { $bad++ }
        $rows += ("wallet={0,6}  need={1,5}  headline {2} -> {3}  gold_r={4}" -f $wallet, $need, $before, $after, $s.GoldR)
    }
    TntTest "A1 exact landing over a spread of partner wallets" ($bad -eq 0) "8 wallets; failures = $bad"
    foreach ($r in $rows) { Write-Host ("          " + $r) }

    # ==================================================================================
    TntSection "A2 - the balance button converges to +1 from BOTH directions"
    # ==================================================================================
    # MARGIN 1 / CEILING 1, which is what tnt_22_v2.txt passes: get to 1 and stop, with
    # no slack in which the button could overshoot into generosity.
    $bad = 0; $rows = @(); $cases = 0
    foreach ($st in $TntStacks) {
    foreach ($seed in @(
        @{ Name='deficit';      Over = @{ GoldR = 900; LumpyR = 20; PlayerGold = 100000; PlayerPrestige = 100000; PlayerPiety = 100000 } },
        @{ Name='big surplus';  Over = @{ GoldP = 3000; LumpyP = 80; PartnerGold = 100000; PartnerPrestige = 100000; PartnerPiety = 100000 } },
        @{ Name='poor partner'; Over = @{ GoldP = 3000; LumpyP = 80; PartnerGold = 25; PartnerPrestige = 0; PartnerPiety = 0; PlayerGold = 100000 } }
    )) {
        $s = TntStackState $st.Over $seed.Over
        $h0 = TntHeadline $s
        Invoke-TntAutobalance $s 1 1
        $h1 = TntHeadline $s
        $cases++
        $ok = ($h1 -eq 1)
        # The one honest exception: a partner too poor to pay AND a player with nothing
        # left to trim. The model does not walk the lumpy ladder, so it may stop above 1.
        if (-not $ok -and $seed.Name -eq 'poor partner' -and $h1 -gt 1) { $ok = $true }
        # And the mirror: a hated partner at multiplier 0 cannot be bought at any price.
        if (-not $ok -and (TntDealMult $s) -le 0 -and $h1 -le 0) { $ok = $true }
        if (-not $ok) { $bad++ }
        $rows += ("{0,-9} {1,-13} headline {2,5} -> {3,5}   mult={4}" -f $st.Name, $seed.Name, $h0, $h1, [Math]::Round((TntDealMult $s),2))
    }}
    TntTest "A2 autobalance lands on +1" ($bad -eq 0) "$cases seeds x stacks; failures = $bad"
    foreach ($r in $rows) { Write-Host ("          " + $r) }

    # The AI's own settle-up, same target, six passes instead of two.
    $bad = 0; $cases = 0
    foreach ($st in $TntStacks) {
    foreach ($wallet in @(50, 500, 5000, 100000)) {
        $s = TntStackState $st.Over @{ LumpyP = 70; PartnerGold = $wallet; PartnerPrestige = $wallet; PartnerPiety = $wallet; PlayerGold = 100000; PlayerPrestige = 100000; PlayerPiety = 100000 }
        Invoke-TntAiPricebalance $s 1 1
        $h = TntHeadline $s
        $cases++
        if ($h -ne 1) {
            # acceptable only when the AI genuinely ran out of purse, or the multiplier
            # is 0 and no amount of anything can move the headline
            if (-not (($h -gt 1 -and $s.GoldR -ge [Math]::Min($wallet,5000)) -or ((TntDealMult $s) -le 0))) { $bad++ }
        }
    }}
    TntTest "A2b AI settle-up lands on +1 or exhausts the purse" ($bad -eq 0) "$cases wallet x stack combinations; failures = $bad"

    # ==================================================================================
    TntSection "A3 - item 22: the alliance is worth less the more allies the ASKER holds"
    # ==================================================================================
    # The exploit: an alliance costs the player nothing to hand over, so a flat price let
    # him sell the same promise to every neighbour in turn. The glut is a MULTIPLIER, the
    # one shape that cannot break I4, and it charges BOTH sides as vanilla does.
    $vals = @()
    foreach ($mine in 0..5) {
        $s = New-TntState @{ AllianceP = $true; PlayerAllies = $mine }
        $vals += (TntValAllianceP $s)
    }
    $mono = $true
    for ($i = 1; $i -lt $vals.Count; $i++) { if ($vals[$i] -gt $vals[$i-1]) { $mono = $false } }
    $strict = ($vals[2] -lt $vals[1]) -and ($vals[3] -lt $vals[2]) -and ($vals[4] -lt $vals[3])
    TntTest "A3 alliance value falls with the asker's ally count" ($mono -and $strict) `
        ("allies 0..5 -> " + ($vals -join ' , '))

    # What the player actually experiences: how much MORE he must add to buy the same
    # 45-point duchy once he is a serial allier. That is "the price rises".
    $rows = @()
    $priceRises = $true; $prevGold = -1
    foreach ($mine in 0..4) {
        $s = New-TntState @{ AllianceP = $true; PlayerAllies = $mine; LumpyR = 45; PlayerGold = 100000 }
        Invoke-TntAutobalance $s 1 1
        $rows += ("allies={0}  alliance worth {1,6}  gold the player must add = {2}" -f $mine, [Math]::Round((TntValAllianceP $s),2), $s.GoldP)
        if ($mine -gt 0 -and $s.GoldP -lt $prevGold) { $priceRises = $false }
        $prevGold = $s.GoldP
    }
    TntTest "A3b the gold needed to buy the same duchy never falls" $priceRises "5 ally counts, all balanced to +1"
    foreach ($r in $rows) { Write-Host ("          " + $r) }

    # The partner's own ally count is charged too - vanilla charges both men.
    $a = New-TntState @{ AllianceP = $true; PartnerAllies = 0 }
    $b = New-TntState @{ AllianceP = $true; PartnerAllies = 4 }
    TntTest "A3c the partner's ally count is charged as well" ((TntValAllianceP $b) -lt (TntValAllianceP $a)) `
        ("partner 0 allies -> " + (TntValAllianceP $a) + " ; 4 allies -> " + (TntValAllianceP $b))

    # ==================================================================================
    TntSection "A4 - a threat cannot be repeated against the same victim"
    # ==================================================================================
    # The lockout is a GATE, not a number, and the reason is arithmetic: the threat row
    # sits OUTSIDE the opinion multiplier, so no opinion penalty - not even -100 - can
    # stop a second threat by making it unprofitable.
    $fresh  = New-TntState @{ PlayerMaxMil = 12000; PartnerMaxMil = 6000; PlayerPrestigeLevel = 3; ThreatDread = 2; ThreatSpent = $false }
    $spent  = New-TntState @{ PlayerMaxMil = 12000; PartnerMaxMil = 6000; PlayerPrestigeLevel = 3; ThreatDread = 2; ThreatSpent = $true }
    TntTest "A4 gate open before, shut after" (((TntCanThreat $fresh) -eq $true) -and ((TntCanThreat $spent) -eq $false)) `
        ("fresh victim = " + (TntCanThreat $fresh) + " ; already threatened = " + (TntCanThreat $spent))

    # And the reason the number could never have done it: at opinion -100 the threat is
    # still worth its full 150, because it is outside the multiplier.
    $hated = TntStackState $TntStacks[3].Over @{ ThreatP = $true; PlayerMaxMil = 18000; PartnerMaxMil = 6000; PlayerPrestigeLevel = 5; ThreatDread = 2 }
    TntTest "A4b the threat keeps its full weight at opinion -100" ((TntValThreatP $hated) -eq 150) `
        ("threat row = " + (TntValThreatP $hated) + " ; headline of a bare threat = " + (TntHeadline $hated))

    # Each of the three factors at zero kills the whole product - the user's own ruling.
    $noArmy    = New-TntState @{ ThreatP = $true; PlayerMaxMil = 6000;  PartnerMaxMil = 6000; PlayerPrestigeLevel = 5; ThreatDread = 2 }
    $noFear    = New-TntState @{ ThreatP = $true; PlayerMaxMil = 18000; PartnerMaxMil = 6000; PlayerPrestigeLevel = 5; ThreatDread = 0 }
    $noRenown  = New-TntState @{ ThreatP = $true; PlayerMaxMil = 18000; PartnerMaxMil = 6000; PlayerPrestigeLevel = 0; ThreatDread = 2 }
    TntTest "A4c any one factor at zero zeroes the threat" `
        (((TntValThreatP $noArmy) -eq 0) -and ((TntValThreatP $noFear) -eq 0) -and ((TntValThreatP $noRenown) -eq 0)) `
        ("no army = " + (TntValThreatP $noArmy) + " ; no fear = " + (TntValThreatP $noFear) + " ; no renown = " + (TntValThreatP $noRenown))

    # ==================================================================================
    TntSection "X - vanilla parity anchors quoted in the mod's own headers"
    # ==================================================================================
    # Not invariants, but the numbers the CALIBRATION block promises. If one of these
    # moves, the mod has silently left vanilla's scale again - which is the whole defect
    # v3 iteration 2 existed to fix.
    $duke = New-TntState @{ PartnerTier = 3; PlayerTier = 3; GoldP = 300 }
    TntTest "X 300 gold to a duke reads +20 (SSM:568-582)" ((TntGainTotal $duke) -eq 20) ("gain = " + (TntGainTotal $duke))
    $duke2 = New-TntState @{ PartnerTier = 3; PlayerTier = 3; GoldP = 150 }
    TntTest "X 150 gold to a duke reads +10 (SSM:552-566)" ((TntGainTotal $duke2) -eq 10) ("gain = " + (TntGainTotal $duke2))
    $count = New-TntState @{ PartnerTier = 2; PlayerTier = 2; GoldP = 100 }
    TntTest "X 100 gold below duke reads +10 (SV:51-90)" ((TntGainTotal $count) -eq 10) ("gain = " + (TntGainTotal $count))
    $pres = New-TntState @{ PartnerTier = 3; PlayerTier = 3; PrestigeP = 300 }
    TntTest "X 300 prestige duke-to-duke reads +20 (SSM:647-666)" ((TntGainTotal $pres) -eq 20) ("gain = " + (TntGainTotal $pres))
    $piety = New-TntState @{ PartnerTier = 3; PlayerTier = 3; PietyP = 250 }
    TntTest "X 250 piety duke-to-duke reads +20 (SSM:740-754)" ((TntGainTotal $piety) -eq 20) ("gain = " + (TntGainTotal $piety))
    $ally = New-TntState @{ AllianceP = $true }
    TntTest "X an even-strength alliance reads +40 (MSM:139-140)" ((TntValAllianceP $ally) -eq 40) ("alliance = " + (TntValAllianceP $ally))
    $ally25 = New-TntState @{ AllianceP = $true; PlayerStrength = 12500; PartnerStrength = 5000 }
    TntTest "X a 2.5x alliance reads +100 (MSM:255-256)" ((TntValAllianceP $ally25) -eq 100) ("alliance = " + (TntValAllianceP $ally25))
    # The reference decomposition of the user's own +12: opinion +10 and a shared culture
    # on a marriage vanilla prices at +12. Modelled with a 12-point marriage as LumpyP.
    $wed = New-TntState @{ LumpyP = 12; Opinion = 10; Culture = 'same'; Faith = 'same' }
    $h = TntHeadline $wed
    TntTest "X a +12 marriage at opinion +10 reads about +13" (($h -ge 12) -and ($h -le 14)) ("headline = $h (vanilla prints +12)")

    # ==================================================================================
    Write-Host ""
    Write-Host ("RESULT   {0} passed, {1} failed" -f $script:TntPass, $script:TntFail)
    if ($script:TntFail -gt 0) {
        Write-Host ""
        Write-Host "FAILURES - each of these is a finding about the mod, not about the harness:"
        foreach ($l in $script:TntFailLines) { Write-Host ("  * " + $l) }
    }
    Write-Host ""
}

if (-not $NoRun) {
    Run-TntSuite
    if ($script:TntFail -gt 0) { exit 1 } else { exit 0 }
}
