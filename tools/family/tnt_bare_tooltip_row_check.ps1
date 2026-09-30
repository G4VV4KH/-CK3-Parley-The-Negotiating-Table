# =============================================================================
# tnt_bare_tooltip_row_check.ps1                     CLAUDE.md check 6.11
#
# THE CHECK WHOSE ABSENCE LET THE "has no localization" REPORT SHIP FIVE TIMES.
#
# WHAT THE DEFECT IS. A greyed control in the negotiation window renders, in
# italic magenta with a red (!) glyph, the literal words
#     <something> has no localization
# instead of the sentence that should explain why it is greyed. The words are an
# ENGINE format string, "%s has no localization", present in ck3.exe exactly
# twice as a standalone message (jomini_trigger_localization.cpp and
# jomini_effect_localization.cpp) and nowhere in this mod or its _docs.
#
# IT IS RENDERED AND NEVER LOGGED. Proven from the binary: the format string
# lives at file offset 72140768 / RVA 0x044CE1E0; its single code xref at file
# 0x3377E89 is followed 48 bytes later by a lea to the loc key
# "JOMINI_DEBUG_FORMAT", and that code site carries NO __FILE__ string - unlike
# the neighbouring "Trigger loc for '%s' is missing" at 72140792, whose xref
# does. So it is a render, not a log line. That is why FIVE rounds of reading
# error.log found nothing: a 6.08 MB playtest log contains zero occurrences of
# "has no localization", zero "Trigger loc", and zero non-TNTLOG tnt_ lines
# while the message is on screen. Never look for this in a log. Ask for a
# screenshot: the rendered message contains the offending name.
#
# -----------------------------------------------------------------------------
# *** ROUND 8, 2026-08-23 - THE ROUND-7 EXPERIMENT CONCLUDED AND THIS SCRIPT
# *** GREW ITS FOURTH FAIL CLASS. READ THIS BEFORE THE ARCHAEOLOGY BELOW.
#
# THE ROUND-7 RESULT. The row was renamed tnt_err_threat_unafraid ->
# tnt_err_threat_nofear with a byte-identical value and the message FOLLOWED the
# rename. That exonerates the key NAME and indicts the row or the construct. Two
# controls were measured on the same run (VANILLA RUN A, 831,868 lines): zero
# "has no localization" lines and zero tnt_ duplicate-key lines in error.log -
# law 10's "rendered, never logged", confirmed - and the key resolves ordinally
# in the script and in all nine .yml with no markup, no [..] and no $nested$, so
# PASS C is clean. The message is NOT a report that the named key is missing.
#
# THE MEASUREMENT THAT MADE THE CENSUS SHARP, AND IT CORRECTS THIS SCRIPT'S OWN
# NUMBERS. The old PASS D printed 90 entry-less-leaf occurrences and called them
# one undifferentiated pile. They are not one pile. Broken out by FORM:
#     72  scalar leaves           exists x30, always x14, script values, ...
#     16  culture = { has_variable = ... }   NOT a leaf at all - a SCOPE CHANGE
#                                            this script used to misread
#      2  modifier / target       NOT leaves - the parameter FIELDS of
#                                 has_opinion_modifier, which HAS an entry; the
#                                 walker used to descend into entried blocks and
#                                 census their arguments
#      1  has_dread_level_towards = { target level }   <- the real outlier
# So the mod had exactly ONE block-form, parameter-bearing, entry-less engine
# trigger on the whole BuildTooltip surface: 1 of 90 rows, 1 of 45 reached keys,
# and it sat inside the one key that has ever printed the message. Both
# misreadings are fixed below ($SCOPELINK, and "descend into an entried block
# only if it is an any_* iterator"), so the sharp number is reproducible.
#
# VANILLA EVIDENCE GATHERED THIS ROUND (all under
# D:\SteamLibrary\steamapps\common\Crusader Kings III\game):
#   * has_dread_level_towards has ZERO trigger_localization entries - 1636
#     entries over 51 files, it is not among them. Controls that DO have one and
#     that this same tooltip reaches: dread 00_character_triggers.txt:817,
#     ai_boldness 00_debug_triggers.txt:33, prestige_level :753,
#     has_opinion_modifier :231, max_military_strength 00_war_triggers.txt:146,
#     target_is_liege_or_above 00_character_relation_triggers.txt:26.
#   * 285 has_dread_level_towards sites under common\ and events\. All but THREE
#     sit in ai_accept / ai_chance modifier blocks (which carry their own
#     `desc = INTIMIDATED_REASON` / `COWED_REASON`), in script values, in event
#     option triggers or in scripted modifiers - none of them a described
#     surface. The three exceptions are
#     10_tgp_japan_interactions.txt:1656 (custom_tooltip on an interaction
#     is_valid), fp3_misc_decision_events.txt:1093 (custom_tooltip in an event
#     option trigger) and 00_legal_triggers.txt:12, vanilla's own
#     opposes_succession_law_change_trigger, whose custom_description names
#     `law_change_approval_is_cowed` - A KEY THAT EXISTS IN NEITHER
#     localization\english NOR localization\russian. Vanilla ships this shape
#     only where nothing ever describes it.
#   * `level >= 1` is NOT the fault: vanilla ships `level >= 2`
#     (10_tgp_japan_interactions.txt:1657-1660) and `level < 2`
#     (00_legal_triggers.txt:12-15).
#
# WHAT SHIPPED. tnt_threat_feared_trigger's branch 1 is no longer the engine's
# dread level; it is `dread >= 30` on a man who is `target_is_liege_or_above` of
# the threatener - two entried leaves. The behaviour delta is measured and
# argued in that trigger's header. THE MOD NOW HAS NO ENTRY-LESS BLOCK-FORM LEAF
# ON ANY DESCRIBED PATH, which is what makes the next hover a control rather than
# another hopeful patch:
#   * a SENTENCE -> the leaf was the mechanism and law 10b is proven.
#   * the message AGAIN -> the leaf hypothesis is dead (there is no such leaf
#     left) and hypothesis (f) below is confirmed; all 45 reason keys must be
#     REPLACED, not patched. Do not hunt another leaf.
#
# WHY THE 72 SCALAR SIBLINGS DO NOT PRINT - answered honestly, because the answer
# decides whether this is one fix or a class of fixes:
#   1. THE MEASURED HALF. They are a different SHAPE. A scalar row is a plain or
#      value-comparison trigger, which the engine can render generically from the
#      comparator and the number (_trigger_localization.info, "Value Comparison
#      Triggers": $COMPARATOR$ and $NUM$ are available whether or not an entry
#      exists). A block-form parameterised trigger has no generic rendering -
#      there is nothing to substitute - and vanilla, as measured above, never
#      asks for one.
#   2. THE UNMEASURED HALF, STATED SO NOBODY MISTAKES IT FOR PROOF. A
#      custom_description row is described ONLY WHEN IT FAILS, and most of the 72
#      sit in rows that pass in ordinary play. The mod has never once been
#      OBSERVED rendering a custom_description sentence on this surface (the
#      ledger below: renders 0, message 1, never observed 44). The only asymmetry
#      evidence is negative: the mod shows ~20 greyed rows, several of which fail
#      as routinely as this one (tnt_err_nothing on every empty table,
#      tnt_err_usehook_none in the default state, tnt_err_no_spouse_p/_r until a
#      pair is picked), and across seven rounds the user has reported the message
#      on ONE of them. That points the same way as the 1-of-1 census. It is not a
#      measurement and this file must not promote it to one.
# So: ONE fix, not a class - and the rows that would be at risk if hypothesis (f)
# is the truth are ALL FORTY-FIVE, which is precisely what the next hover settles.
# -----------------------------------------------------------------------------
# *** RETIRED IN THIS REVISION: THE OLD DIAGNOSIS AND ITS THREE ANCHORS. ***
#
# Every earlier revision of this script believed the offending node was a BARE
# row - a call to one of the mod's own scripted triggers, or an engine leaf,
# with no `common\trigger_localization\` entry, sitting inside an is_valid that
# [TntTip()] reaches. It reported THREE FAIL rows on the tree of 2026-08-17
# (tnt_20_scripted_guis.txt:511, :909, :942 - the report itself was made four
# separate times, hence "four reports, three anchors"; do not read either
# number as the other). V17 inlined those three, this script went to exit 0, and
# THE SYMPTOM STAYED ON SCREEN. That is the fifth report.
#
# THE OLD HYPOTHESIS AT THE HEAD OF THIS FILE - "if the symptom returns with
# this at exit 0, the next suspect is a LEAF, not a wrapper" - IS IN SERIOUS
# DOUBT, and so is CLAUDE.md law 10b's premise. Read what follows at its real
# strength: it is the RIGHT SURFACE but the WRONG CONSTRUCT (ledger item 5
# below), because vanilla's two BuildTooltip is_valid blocks contain no
# custom_description at all. Earlier revisions of this header wrote "REFUTED";
# that overclaimed, and overclaiming here is what let round 6 ship a fix with no
# control. This is the measurement no earlier round made:
#
#   VANILLA HAS EXACTLY TWO `ScriptedGui.BuildTooltip` CALL SITES IN ITS WHOLE
#   gui\ TREE - <vanilla>\gui\window_faith.gui:902 and :915. Both resolve to
#   <vanilla>\common\scripted_guis\00_religion.txt:309 create_head_of_faith and
#   :325 recreate_head_of_faith, and EACH is_valid IS ONE SINGLE BARE ROW:
#       is_valid = { can_create_head_of_faith_title_trigger = { FAITH = scope:faith } }
#   That trigger has ZERO trigger_localization entries. Its body
#   (<vanilla>\common\scripted_triggers\00_religious_triggers.txt:1537) calls
#   three more bare scripted triggers that ALSO have zero entries -
#   can_create_spiritual_head_of_faith_title_trigger (:1484),
#   can_create_temporal_head_of_faith_title_trigger,
#   can_afford_create_head_of_faith_title_cost_trigger (:1501) - and inside
#   those sits a BARE `exists = religious_head` (:1495), `exists` itself having
#   zero entries. Not one custom_description anywhere in that subtree.
#
#   *** RETRACTED, 2026-08-19. "Vanilla's Create Head of Faith button renders
#   its tooltip perfectly" stood on this line as a statement of fact, and NOBODY
#   HAS EVER HOVERED IT. The project held both beliefs at once: this file said it
#   renders, while common\scripted_guis\tnt_20_scripted_guis.txt:1000 said
#   "Vanilla's own two buttons print this message." Two shipped files, opposite
#   claims about the same button, zero observations behind either. Round 7's
#   PROBE E settles it for nothing: open the faith window and hover that button.
#   It is visible only on your OWN faith, only when the faith has a head-of-faith
#   doctrine, and only when the head title is absent
#   (<vanilla>\gui\window_faith.gui:897) or exists with no holder (:910), so it
#   may simply not be there - take it if it is.
#   Vanilla's own comment at 00_religious_triggers.txt:1552 - "We shouldn't hit
#   this point, but if we do use the following as error messages" - shows vanilla
#   EXPECTING bare rows to be described here. That is an intention, not a
#   measurement, and this file must stop quoting it as one.
#
# So on the one surface that matters, vanilla SHIPS a bare entry-less scripted
# trigger nested three deep and a bare entry-less engine leaf, and ships them in
# the confident expectation that they describe. What nobody has done is WATCH one
# do it. Read the claim at its real strength: "a missing trigger_localization
# entry is not what prints the message" is strongly indicated by vanilla shipping
# the shape at all, and it is NOT yet observed. PROBE E is the observation, and
# until it is taken this paragraph is an inference like all the others.
#
# TWO COROLLARIES A FUTURE ROUND MUST NOT RE-DERIVE.
#  (1) `custom_description` suppressing its subtree is ALSO not the mechanism,
#      and adding a trigger_localization entry for an entry-less leaf inside one
#      cannot fix anything - such an entry is never consulted. A file
#      common\trigger_localization\tnt_95_trigger_loc.txt declaring
#      has_dread_level_towards was specified and DELIBERATELY NOT SHIPPED for
#      exactly this reason. Its shape was safe (zero vanilla entries for that
#      name, no filename collision, vanilla declares 1636 entry names with zero
#      duplicates) - it was simply inert.
#      THE COUNT: 1636, re-measured 2026-08-19 over the 51 files of
#      <vanilla>\common\trigger_localization\ with this script's own tokenizer,
#      and it agrees with CLAUDE.md law 10. The figure 1609 also circulates in
#      this project's notes; 1636 is the one that has been reproduced.
#  (2) The vanilla call site this script used to cite for the legal shape,
#      00_religion.txt:18-59 toggle_great_holy_war_pledge, IS NOT ON A
#      BuildTooltip PATH AT ALL. <vanilla>\gui\window_ghw.gui:1279 gives it
#      `tooltip = "[GreatHolyWarWindow.GetPledgeTooltip(...)]"`, a bespoke data
#      function, not ScriptedGui.BuildTooltip. It is still fine evidence that
#      trigger_if may enclose custom_description rows; it is NOT evidence about
#      this surface. Earlier rounds treated it as the latter.
#
# -----------------------------------------------------------------------------
# WHAT THE EVIDENCE DOES SINGLE OUT, AND WHAT THIS SCRIPT NOW CHECKS.
#
# The one variable that correlates 1/1 and 44/44 with the symptom is the loc
# VALUE of the key the custom_description NAMES - not the trigger rows inside
# it. Of the custom_description keys reachable from the 17 [TntTip()] is_valid
# blocks, exactly two ever carried `#tag text#!` format markup:
#     tnt_err_threat_unafraid   BOTH languages   (#high 75#! , #high 40#!)
#     tnt_err_grand_no_dlc      ENGLISH only     (#high Tours & Tournaments#!)
# The one screenshot on record (parley\temp\screen5.png, a RUSSIAN session,
# Atabeg Karadzha 23 Feb 1185) shows the greyed threat checkbox rendering ONE
# line - `tnt_err_threat_unafraid has no localization`. In a Russian session
# tnt_err_threat_unafraid was the ONLY reachable key whose Russian value carried
# `#...#!`, and it is the only key that has ever printed the message.
#
# *** RETRACTED, 2026-08-19: "while the other three reason rows of that same
# tooltip rendered their sentences." THAT IS FALSE, AND IT IS THE COSTLIEST LINE
# THIS FILE EVER CARRIED. Screen5 shows ONE line in the box. Rows 1, 2 and 4 of
# that is_valid PASSED, and the description walker describes only FAILING rows -
# so those three were never described and nothing rendered beside the message.
# Read as a control it invented a negative side for a table that has none.
#
# *** RETRACTED with it: "The em-dash is EXONERATED by a same-path control that
# renders: tnt_err_no_influence_gov (tnt_l_russian.yml:892) carries one." That
# key sits on tnt_send_offer and is described only if the player stages influence
# while lacking an administrative government; CLAUDE.md section 3 records
# influence at 0 end-to-end and no administrative government on either side, so
# IT HAS NEVER BEEN DESCRIBED. The em dash is UNDETERMINED, not cleared - which
# is exactly what PASS E now prints, every run, as a NOTE.
#
# THE LEDGER, WRITTEN DOWN SO NO ROUND EIGHT RE-INFERS IT.
#     observed renders 0  |  observed message 1  |  never observed 44.
# The mod has never once been seen RENDERING a custom_description sentence on the
# BuildTooltip path. Every "control" rounds 5 and 6 leaned on was an inference
# from absence. All seven, with the file:line of each, because four of the six
# failed rounds shipped a fix and a hypothesis together and learned nothing:
#   1. THIS FILE, the retraction above - "the other three rows rendered". FALSE:
#      they passed, so they were never described.
#   2. tnt_20_scripted_guis.txt:985-986 - the message appeared "UNDER the
#      correctly-rendered tnt_err_advanced_off row above". IMPOSSIBLE, not merely
#      unobserved: that row is `exists = var:tnt_advanced` (:967), true by
#      default, so it passes and is never described; and with advanced terms off
#      the row is hidden by its own `visible` conjunct. A fabricated detail
#      written down as an observation.
#   3. Round 5 leg 1 - "vanilla ships 2,985 entry-less leaves inside
#      custom_description on described surfaces". WRONG SURFACE: measured over
#      character_interactions + decisions + scripted_guis, and CLAUDE.md law 10a
#      already records that the interaction/decision path behaves DIFFERENTLY.
#      It is not a control for BuildTooltip. PASS D still prints the figure, now
#      labelled as the wrong-surface number it is.
#   4. Round 5 leg 2 - "the same-surface vanilla site 00_religion.txt:43-50
#      renders". Retracted by this file's own corollary (2) above, and dead
#      independently: all seven of that file's custom_description keys are ABSENT
#      from vanilla localization, so it cannot be observed rendering a sentence.
#   5. Round 5 leg 3 - "vanilla's two BuildTooltip surfaces render a bare
#      entry-less trigger". Right surface, WRONG CONSTRUCT: create_head_of_faith
#      and recreate_head_of_faith contain ZERO custom_description
#      (<vanilla>\common\scripted_guis\00_religion.txt:317-319 and :333-335). It
#      is evidence that BARE rows work there; it says nothing about
#      custom_description. And the render itself is unobserved - see the
#      retraction further up this header.
#   6. Round 5 leg 4 - "our own tnt_err_nothing fails on every empty window
#      without ever printing". VACUOUS: nobody has ever hovered the Propose
#      button. Worse, screen5 IS that state - an empty table - so one more hover
#      in that one session would have doubled the entire ledger. That hover is
#      round 7's PROBE C.
#   7. Round 6's em-dash exoneration - the retraction above. NEVER OBSERVED.
#
# THE HYPOTHESIS THE VANILLA CENSUS CREATES, AND THE REASON PROBES A-D EXIST.
# (f) `custom_description` inside a scripted_gui `is_valid` reached by
# ScriptedGui.BuildTooltip may simply not be supported by the engine's
# description walker - in which case ALL 45 reached keys would print the message
# and the mod's whole reason-tooltip design must be replaced, not patched.
# VANILLA SHIPS ZERO INSTANCES OF THE CONSTRUCT: BuildTooltip occurs exactly
# twice in the whole vanilla gui tree (window_faith.gui:902 and :915), both
# resolving to an is_valid that is ONE bare parameterised call with no
# custom_description in it. The vanilla scripted_guis that DO use
# custom_description are reached by other means - 00_religion.txt through the
# bespoke GreatHolyWarWindow.GetPledgeTooltip (<vanilla>\gui\window_ghw.gui:1279)
# and ep2_activities.txt:27/:49 from no .gui file at all. So the mod is the only
# thing in the game doing this, the observed render rate on this surface is 0 of
# 1, and six rounds of edits INSIDE the construct changed nothing - which is what
# you expect if the construct itself is the fault. FOUR FREE HOVERS DISCRIMINATE
# IT, and each one describes a key never described before in this project:
#   PROBE A  "Threaten him" against a partner whose army is BIGGER than yours ->
#            row 1, tnt_err_threat_weak (tnt_20_scripted_guis.txt:552), a plain
#            value whose only leaf max_military_strength HAS a vanilla entry.
#            Renders -> (f) and (h) both die. Prints -> (f) is confirmed for
#            practical purposes and the 45-key design must be redesigned.
#   PROBE B  "Use a hook" with no hook on the partner - the DEFAULT state ->
#            tnt_err_usehook_none (tnt_23_usehook.txt:27), a plain value over ONE
#            SIMPLE leaf that is entry-less by construction
#            (tnt_usehook_strength_value >= 1 is a script value, and zero of
#            vanilla's entries is a script value). Renders -> (d') is badly
#            damaged and (f) dies. Prints -> (d') strongly confirmed and (a), (b)
#            and (g) all die in one observation.
#   PROBE C  "Propose" with an empty table - also screen5's own state ->
#            tnt_err_nothing (tnt_20_scripted_guis.txt:1423). B's independent
#            replicate through one more level of scripted-trigger recursion, and
#            the direct test of vacuous control 6.
#   PROBE D  "Sworn fealty" while AT WAR with the partner ->
#            tnt_err_vassal_mutual_war (tnt_20_scripted_guis.txt:1028, mirrored
#            for the _r side at :1153); both leaves have vanilla entries and the
#            value is plain. Renders -> independent confirmation of A on a SECOND
#            gui. Prints -> (f) confirmed on a second gui with a fully-entried
#            plain key. Decisive either way.
# Report EVERY line in each box, verbatim. A line that reads as a sentence is a
# RENDER; a line reading `<key> has no localization` in italic magenta with a red
# (!) is a MESSAGE. Rows that PASS are never described, so a one-line box is the
# normal shape and is not itself evidence of anything.
# `#high` is legitimate markup in general - it is `format = { name = high
# format = "color_white" }` at <vanilla>\gui\preload\textformatting.gui:121-124,
# and vanilla's english loc uses `#high`
# 924 times - but vanilla's scripted_gui surface carries only 10
# custom_description/custom_tooltip mentions in two files, and NONE of their
# keys carries format markup. So this surface is untested by vanilla, which is
# precisely where CLAUDE.md law 10a already says the rules differ.
#
# ONE FALSE LEAD TO SAVE THE NEXT ROUND A GREP. The only vanilla scripted_gui
# custom_tooltip key that resolves at all is tournament_not_competing_tt
# (<vanilla>\common\scripted_guis\ep2_activities.txt:27 and :49), and its value
# DOES carry two [..] tokens - "[THIS.Char.GetShortUIName|U] will not compete in
# any [contests|E]". That is NOT a refutation of law 10a: neither scripted_gui in
# that file is referenced from <vanilla>\gui\ at all (0 hits) and neither is on a
# BuildTooltip path, so vanilla never renders those tokens through the
# description subsystem. It also carries no `#...#!`, so it is not a counter-
# example to the markup finding either.
#
# THE MESSAGE MOST LIKELY NAMES THE CUSTOM_DESCRIPTION'S TEXT KEY, and fires
# when that key fails to resolve. Independent support, on this same surface:
# vanilla's toggle_great_holy_war_pledge names five custom_description keys -
# pledge_ghw_no_war_after_start, _liege_condition, _indep_or_faith_condition,
# _recently_unpledged, _papal_hooked_pledge - and NOT ONE of the five exists
# anywhere under <vanilla>\localization (verified by recursive scan, 0 hits), so
# vanilla itself ships a live instance of this message keyed on a
# custom_description's own text key. That is why check 3 below exists.
#
# -----------------------------------------------------------------------------
# WHAT THIS SCRIPT DOES, IN EIGHT PASSES. Exit 0 clean / 1 offender / 2 bad args.
# A, B, C, G and H can FAIL. D, E and F are instruments: they print a measurement
# every run and never fail, because a gate hung on an unproven hypothesis is a gate
# that goes permanently red and stops being read. E has one switch for the day its
# hypothesis is proven; D and F have none by design.
# G IS THE ROUND-8 ADDITION AND IT IS DELIBERATELY A FAIL, not a note: the shape it
# catches existed exactly once, this script SAW it for two rounds, classified it as
# a NOTE, and the note is why the defect shipped twice more.
#
# PASS A (kept verbatim from the previous revision, still a FAIL class).
#   The bare-row discipline of law 10b: inside a reached is_valid, every row the
#   engine must describe stays inside a reason wrapper.
#   The premise is refuted above, but the DISCIPLINE is kept: it costs nothing,
#   it is vanilla-shaped, and it is at exit 0. Do NOT make custom_description
#   stop suppressing here - that change emits ~90 rows on the shipped tree,
#   almost all false by the vanilla base rate below, and a gate that is
#   permanently red is a gate nobody reads.
#
# PASS B - RECURSION THROUGH THE MOD'S OWN SCRIPTED TRIGGERS (tokenized).
#   The previous revision used the mod's trigger names only to label a `{ }` as
#   ARGS and skip it, so it could not see inside a called trigger at all, and
#   six reachable custom_description keys were invisible to every pass it had.
#   It was also line-oriented and therefore blind to a second statement on one
#   line: `root = { max_military_strength > var:tnt_partner.max_military_strength }`
#   at tnt_20_scripted_guis.txt:553 was never seen. Both are fixed by a real
#   brace-balanced tokenizer (quoted strings consumed BEFORE `#` comments, so a
#   `#` inside a string cannot eat the rest of a line).
#
# PASS C - THE NEW FAIL CLASSES, REPORTED PER LANGUAGE.
#   For every custom_description key reachable from a reached is_valid:
#     MARKUP_xx     the value carries `#tag text#!` format markup   <- the defect
#     TOKEN_xx      the value carries `[`  (law 10a: no data function / concept)
#     NESTED_xx     the value carries `$`  (a nested loc key)
#     UNRESOLVED_xx the key is absent from that language's .yml
#   PER LANGUAGE is the point: the two live instances differ by language, and an
#   averaged verdict would have hidden tnt_err_grand_no_dlc entirely.
#
# PASS D - THE ENTRY-LESS SCALAR-LEAF CENSUS, A NOTE AND NEVER A FAILURE.
#   Which reached custom_description keys have a SCALAR leaf in their condition
#   subtree with no trigger_localization entry. Since round 8 the BLOCK-form half
#   of this census is split out into PASS G, which FAILS, and the two walker
#   misreadings that used to inflate this number ($SCOPELINK and the descent into
#   entried non-iterator blocks) are fixed, so the figure is now the honest one.
#   THE NUMBER PRINTED BESIDE IT IS THE WRONG-SURFACE NUMBER AND IS LABELLED AS
#   SUCH. "Vanilla ships 2,985 entry-less leaves inside custom_description" was
#   measured over character_interactions + decisions + scripted_guis, and
#   CLAUDE.md law 10a already records that the interaction/decision path behaves
#   DIFFERENTLY from this one - so it bounds how common the shape is in vanilla
#   and it is NOT a control for BuildTooltip. The same applies to the shape
#   citation <vanilla>\common\scripted_guis\00_religion.txt:43-50, which corollary
#   (2) above shows is not on a BuildTooltip path at all. Round 5 used both as
#   refutations; they are context, and (d') is UNTESTED rather than refuted.
#
# PASS G - ENTRY-LESS BLOCK-FORM LEAF INSIDE A REACHED REASON WRAPPER. FAIL.
#   The round-8 rule, stated as narrowly as the evidence supports it: a BLOCK-form
#   engine trigger whose name has no common\trigger_localization\ entry must not be
#   reachable by the description walker from a [TntTip()] is_valid. Express it with
#   entried leaves, or move it off the described path. Scalar leaves are NOT in this
#   class and must not be added to it - see the round-8 section of this header for
#   the measured reason and for the half of that reason that is not measured.
#
# PASS H - BUILDTOOLTIP REASON-WRAPPER KIND. FAIL.
#   Every reason wrapper reached through ScriptedGui.BuildTooltip must be
#   custom_tooltip. custom_description and custom_description_no_bullet still count
#   as structural suppression for passes A-G, so their contents are audited too,
#   but H rejects the wrapper itself. Added with the 2026-08-27 full sweep: the
#   preserved pre-sweep tree produces 73 H offenders; the current tree produces 0.
#
# PASS E - THE EM-DASH CENSUS. NOTE today, FAIL on -FailOnEmDash. Hypothesis (a).
# PASS F - THE CROSSOVER STATE PROBE. Prints which loc key sits on which
#   custom_description row of tnt_threat_p_toggle, and whether round 7's KEY/ROW
#   crossover is armed or not. It exists because the crossover is COSMETICALLY
#   WRONG while it is live and MUST be reverted after the hover is read, and
#   because a session must never have to guess whether a previous round armed it.
#
# CURRENT ACCEPTANCE (2026-08-27). The live tree must contain 76 reached reason
# wrappers, all custom_tooltip, and exit 0. Replacing the five converted files with
# the preserved pre-sweep versions must report 73 WRAPPER_NOT_CUSTOM_TOOLTIP
# offenders and exit 1. A fresh in-game hover is still required for runtime release
# acceptance, but no intentionally broken negative control remains in the mod.
# =============================================================================
param(
    [string]$ModRoot     = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    [string]$VanillaRoot = "D:\SteamLibrary\steamapps\common\Crusader Kings III\game",
    # PASS E's ONE SWITCH, and it must stay OFF until a hover proves hypothesis (a).
    # Turning an UNPROVEN hypothesis into a FAIL would block the launch gate on a
    # guess - which is the round-6 mistake wearing a tool as a costume. Off: the
    # em-dash census prints as a NOTE. On: every em-dash-carrying reached key
    # becomes an EMDASH_xx offender and the script exits 1. See PASS E.
    [switch]$FailOnEmDash
)

if (-not (Test-Path (Join-Path $ModRoot 'common\scripted_guis'))) { Write-Host "BAD ModRoot: $ModRoot"; exit 2 }
if (-not (Test-Path (Join-Path $VanillaRoot 'common\trigger_localization'))) { Write-Host "BAD VanillaRoot: $VanillaRoot"; exit 2 }

# nodes the description walker handles structurally
$PASSTHROUGH = @('trigger_if','trigger_else','trigger_else_if')
$SUPPRESS    = @('custom_description','custom_description_no_bullet','custom_tooltip')
$SKIP        = @('limit')          # evaluated, never described
$CDFIELD     = @('text','subject','object','tooltip')   # fields OF a custom_description
$LOGICKW     = @('and','or','not','nand','nor','all_false','any_false','calc_true_if')
# SCOPE LINKS. In BLOCK form `<link> = { ... }` is a SCOPE CHANGE and its children
# ARE rows; in scalar form `<link> = <handle>` it is a scope-comparison trigger and
# is censused like any other leaf. Only the BLOCK form is listed here.
# THIS LIST EXISTS BECAUSE ITS ABSENCE COST A MEASUREMENT: `culture = { has_variable
# = ... }` (tnt_40_triggers.txt:697-702, reached from four scripted_guis) was counted
# as sixteen entry-less LEAVES, which is 16 of the old PASS D's 90 and enough noise to
# hide the one row that mattered.
# AN UNKNOWN BLOCK-FORM NAME IS TREATED AS AN ENGINE TRIGGER, i.e. it lands in the
# FAIL class if it has no entry. That is the safe direction: a scope link this list
# does not know fails LOUD and is fixed by adding it here with a vanilla citation,
# whereas the opposite default would silently swallow the very defect this script
# exists to catch.
$SCOPELINK   = @(
    'culture','faith','religion','house','dynasty','dynast','house_head',
    'liege','top_liege','employer','host','home_court','court_owner',
    'mother','father','real_father','spouse','primary_spouse','betrothed',
    'killer','imprisoner','matchmaker','designated_heir','player_heir',
    'capital_county','capital_province','capital_barony','primary_title',
    'location','county','duchy','kingdom','empire','holder','title_province',
    'religious_head','liege_or_court_owner','primary_heir','head_of_house'
)
# NOTE (PowerShell 5.1 variable names are CASE-INSENSITIVE): never name an array
# $CD and then take a [string]$cd parameter anywhere - the parameter silently
# shadows the array and `$CD -contains $x` becomes an always-false string
# compare. That bug cost a whole measurement pass and reported a clean 0.
$CDKW        = $SUPPRESS

# ---------------------------------------------------------------------------
# tokenizer: quoted strings first, then comments, then braces/operators/words
# ---------------------------------------------------------------------------
$TOKRX = [regex]'"[^"]*"|#[^\r\n]*|\{|\}|>=|<=|!=|\?=|==|=|<|>|[^\s{}=<>!?"#]+'
$OPS   = @('=','==','>=','<=','<','>','!=','?=')

function Get-Tokens([string]$text) {
    $out = New-Object System.Collections.ArrayList
    $line = 1; $pos = 0
    foreach ($m in $TOKRX.Matches($text)) {
        for ($k = $pos; $k -lt $m.Index; $k++) { if ($text[$k] -eq "`n") { $line++ } }
        $pos = $m.Index
        $s = $m.Value
        if (-not $s.StartsWith('#')) { [void]$out.Add([pscustomobject]@{ T = $s; L = $line }) }
        for ($k = $m.Index; $k -lt $m.Index + $m.Length; $k++) { if ($text[$k] -eq "`n") { $line++ } }
        $pos = $m.Index + $m.Length
    }
    return $out
}

$script:TK = $null
$script:TI = 0

function Get-Tree {
    $nodes = New-Object System.Collections.ArrayList
    while ($script:TI -lt $script:TK.Count) {
        $t = $script:TK[$script:TI]
        if ($t.T -eq '}') { $script:TI++; return $nodes }
        if ($t.T -eq '{') {
            $script:TI++
            $kids = Get-Tree
            [void]$nodes.Add([pscustomobject]@{ Name=''; Op=''; Value=''; Line=$t.L; IsBlock=$true; Children=$kids })
            continue
        }
        $name = $t.T; $ln = $t.L; $script:TI++
        $op = ''
        if ($script:TI -lt $script:TK.Count -and ($OPS -contains $script:TK[$script:TI].T)) { $op = $script:TK[$script:TI].T; $script:TI++ }
        if ($script:TI -lt $script:TK.Count -and $script:TK[$script:TI].T -eq '{') {
            $script:TI++
            $kids = Get-Tree
            [void]$nodes.Add([pscustomobject]@{ Name=$name; Op=$op; Value=''; Line=$ln; IsBlock=$true; Children=$kids })
        }
        else {
            $val = ''
            if ($script:TI -lt $script:TK.Count -and $script:TK[$script:TI].T -ne '{' -and $script:TK[$script:TI].T -ne '}') {
                $val = $script:TK[$script:TI].T; $script:TI++
            }
            [void]$nodes.Add([pscustomobject]@{ Name=$name; Op=$op; Value=$val; Line=$ln; IsBlock=$false; Children=$null })
        }
    }
    return $nodes
}

function Get-FileTree([string]$path) {
    $script:TK = Get-Tokens ([System.IO.File]::ReadAllText($path))
    $script:TI = 0
    return Get-Tree
}

# --- trigger_localization index (vanilla + the mod's own, if it ever ships one)
$trigloc = New-Object System.Collections.Generic.HashSet[string]
foreach ($base in @($VanillaRoot, $ModRoot)) {
    $dir = Join-Path $base 'common\trigger_localization'
    if (-not (Test-Path $dir)) { continue }
    foreach ($f in Get-ChildItem $dir -Filter *.txt) {
        $d = 0
        foreach ($line in [System.IO.File]::ReadAllLines($f.FullName)) {
            $l = $line; $c = $l.IndexOf('#'); if ($c -ge 0) { $l = $l.Substring(0,$c) }
            if ($d -eq 0 -and $l -match '^\s*([A-Za-z0-9_\.]+)\s*=\s*\{') { [void]$trigloc.Add($Matches[1].ToLower()) }
            $d += ([regex]::Matches($l,'\{')).Count - ([regex]::Matches($l,'\}')).Count
            if ($d -lt 0) { $d = 0 }
        }
    }
}

function Test-ScopeHandle([string]$s) {
    if ($s -match '^\$[A-Za-z0-9_]+\$$')            { return $true }
    if ($s.StartsWith('scope:'))                    { return $true }
    if ($s.StartsWith('var:'))                      { return $true }
    if ($s.StartsWith('local_var:'))                { return $true }
    if (@('root','this','prev','from','fromfrom','fromfromfrom') -contains $s) { return $true }
    if ($s -match '^(root|this|prev|from)\.')       { return $true }
    return $false
}

function Test-HasEntry([string]$name, [string]$op) {
    $bare = ($name -split '\.')[-1]
    $spec = ''
    if     ($op -eq '='  -or $op -eq '==' -or $op -eq '?=') { $spec = $bare + '_equal' }
    elseif ($op -eq '>')                                    { $spec = $bare + '_greater_than' }
    elseif ($op -eq '>=')                                   { $spec = $bare + '_greater_or_equal' }
    elseif ($op -eq '<')                                    { $spec = $bare + '_less_than' }
    elseif ($op -eq '<=')                                   { $spec = $bare + '_less_or_equal' }
    if ($spec -ne '' -and $trigloc.Contains($spec)) { return $true }
    if ($trigloc.Contains($bare))                   { return $true }
    return $false
}

# --- the mod's own scripted triggers: name -> body, for PASS B recursion ------
$modTrigBody  = @{}
$modTrigNames = New-Object System.Collections.Generic.HashSet[string]
$dirT = Join-Path $ModRoot 'common\scripted_triggers'
if (Test-Path $dirT) {
    foreach ($f in Get-ChildItem $dirT -Filter *.txt) {
        foreach ($n in (Get-FileTree $f.FullName)) {
            if ($n.Name -eq '' -or -not $n.IsBlock) { continue }
            $nm = $n.Name.ToLower()
            [void]$modTrigNames.Add($nm)
            if (-not $modTrigBody.ContainsKey($nm)) { $modTrigBody[$nm] = [pscustomobject]@{ File = $f.Name; Nodes = $n.Children } }
        }
    }
}

# --- which scripted_guis are on the BuildTooltip path? ----------------------
$reached = New-Object System.Collections.Generic.HashSet[string]
foreach ($f in Get-ChildItem (Join-Path $ModRoot 'gui') -Recurse -Include *.gui) {
    foreach ($line in [System.IO.File]::ReadAllLines($f.FullName)) {
        $t = $line.TrimStart()
        if ($t.StartsWith('#')) { continue }                      # commented-out binding
        foreach ($m in [regex]::Matches($line, "TntTip\(\s*'([A-Za-z0-9_]+)'\s*\)")) { [void]$reached.Add($m.Groups[1].Value) }
        foreach ($m in [regex]::Matches($line, "GetScriptedGui\(\s*'([A-Za-z0-9_]+)'\s*\)\.BuildTooltip")) { [void]$reached.Add($m.Groups[1].Value) }
    }
}

# ===========================================================================
# PASS B/D - tokenized walk: collect reason-wrapper sites and entry-less leaves
# ===========================================================================
$script:cdSites = New-Object System.Collections.ArrayList
$script:census  = New-Object System.Collections.ArrayList

function Walk-Rows([object]$Nodes, [string]$Gui, [string]$SrcFile, [string]$CdKey, [bool]$InCD, [int]$Depth, [object]$Seen) {
    if ($Depth -gt 12) { return }
    foreach ($n in $Nodes) {
        if ($n.Name -eq '') {
            if ($n.IsBlock) { Walk-Rows $n.Children $Gui $SrcFile $CdKey $InCD $Depth $Seen }
            continue
        }
        $low = $n.Name.ToLower()

        if ($CDKW -contains $low) {
            $k = ''
            foreach ($c in $n.Children) { if ($c.Name.ToLower() -eq 'text') { $k = $c.Value.Trim('"') } }
            [void]$script:cdSites.Add([pscustomobject]@{ Gui=$Gui; Key=$k; File=$SrcFile; Line=$n.Line; Wrapper=$low })
            Walk-Rows $n.Children $Gui $SrcFile $k $true $Depth $Seen
            continue
        }
        if ($SKIP    -contains $low) { continue }
        if ($CDFIELD -contains $low -and $InCD) { continue }
        if (($PASSTHROUGH -contains $low) -or ($LOGICKW -contains $low)) {
            if ($n.IsBlock) { Walk-Rows $n.Children $Gui $SrcFile $CdKey $InCD $Depth $Seen }
            continue
        }
        if ($modTrigBody.ContainsKey($low)) {
            if ($Seen -contains $low) { continue }                 # cycle guard
            $b = $modTrigBody[$low]
            Walk-Rows $b.Nodes $Gui $b.File $CdKey $InCD ($Depth + 1) ($Seen + @($low))
            continue
        }
        if (Test-ScopeHandle $low) {
            if ($n.IsBlock) { Walk-Rows $n.Children $Gui $SrcFile $CdKey $InCD $Depth $Seen }
            continue
        }
        # a NAMED scope link in BLOCK form is a scope change, not a leaf
        if ($n.IsBlock -and ($SCOPELINK -contains $low)) {
            Walk-Rows $n.Children $Gui $SrcFile $CdKey $InCD $Depth $Seen
            continue
        }

        # a real engine node
        $has = Test-HasEntry $low $n.Op
        if (-not $has) {
            $form = 'scalar'
            $fields = ''
            if ($n.IsBlock) {
                $form = 'BLOCK'
                $fields = ((@($n.Children | Where-Object { $_.Name -ne '' } | ForEach-Object { $_.Name }) | Select-Object -Unique) -join ',')
            }
            [void]$script:census.Add([pscustomobject]@{ Gui=$Gui; CdKey=$CdKey; Leaf=$n.Name; Form=$form; Fields=$fields; File=$SrcFile; Line=$n.Line; InCD=$InCD })
        }
        # DESCEND ONLY INTO AN any_* ITERATOR. Its children really are rows the
        # engine must describe one by one. Any OTHER entry-bearing block form -
        # has_opinion_modifier = { modifier target }, has_dread_level_towards =
        # { target level } - carries ARGUMENTS, not rows: the entry describes the
        # whole node and its fields are never described on their own. The previous
        # revision descended into every entried block and reported the two argument
        # names of has_opinion_modifier as entry-less leaves; that is 2 of the old
        # PASS D's 90 and it is a walker artifact, not a finding.
        if ($n.IsBlock -and $has -and $low.StartsWith('any_')) { Walk-Rows $n.Children $Gui $SrcFile $CdKey $InCD $Depth $Seen }
    }
}

foreach ($f in Get-ChildItem (Join-Path $ModRoot 'common\scripted_guis') -Filter *.txt) {
    foreach ($g in (Get-FileTree $f.FullName)) {
        if ($g.Name -eq '' -or -not $g.IsBlock) { continue }
        if (-not $reached.Contains($g.Name)) { continue }
        foreach ($c in $g.Children) {
            if ($c.Name.ToLower() -eq 'is_valid' -and $c.IsBlock) {
                Walk-Rows $c.Children $g.Name $f.Name '' $false 0 @()
            }
        }
    }
}

# ===========================================================================
# PASS C - the loc VALUE of every reached custom_description key
# ===========================================================================
function Get-LocMap([string]$path) {
    $h = @{}
    if (-not (Test-Path $path)) { return $h }
    $L = [System.IO.File]::ReadAllLines($path)
    for ($i = 0; $i -lt $L.Count; $i++) {
        if ($L[$i] -match '^\s*([A-Za-z0-9_]+):\d+\s+"(.*)"\s*$') {
            if (-not $h.ContainsKey($Matches[1])) { $h[$Matches[1]] = [pscustomobject]@{ Line = $i + 1; Value = $Matches[2] } }
        }
    }
    return $h
}
$LOC = @{
    EN = Get-LocMap (Join-Path $ModRoot 'localization\english\tnt_l_english.yml')
    RU = Get-LocMap (Join-Path $ModRoot 'localization\russian\tnt_l_russian.yml')
}
$YML = @{ EN = 'tnt_l_english.yml'; RU = 'tnt_l_russian.yml' }

# a key the mod deliberately borrows from vanilla is NOT ours to police - look
# it up only when it is missing from our own files, so the common case is fast
function Test-VanillaKey([string]$key, [string]$lang) {
    $sub = 'english'
    if ($lang -eq 'RU') { $sub = 'russian' }
    $dir = Join-Path $VanillaRoot ('localization\' + $sub)
    if (-not (Test-Path $dir)) { return $false }
    $hit = Get-ChildItem $dir -Recurse -Include *.yml |
           Select-String -Pattern ('^\s*' + [regex]::Escape($key) + ':') -List |
           Select-Object -First 1
    if ($hit) { return $true }
    return $false
}

$MARKUPRX = [regex]'#[A-Za-z_;]+[ :]'
# U+2014 EM DASH, built from its codepoint on purpose: this script is ASCII-only
# after its BOM, and a literal em dash pasted here would be the very byte the
# census is meant to count. Never search for it with a character-level replace.
$EMDASH   = [string][char]0x2014
# *** THE COLLECTION IS $emRows AND NOT $emdash, AND THIS IS NOT A STYLE CHOICE. ***
# PowerShell 5.1 variable names are CASE-INSENSITIVE, so `$emdash = @()` would BE
# an assignment to $EMDASH. The needle then converts to '' , String.Contains('')
# is TRUE for every value, and [regex]::Escape('') matches at every position - so
# the census reported dash-free keys with a count of (value length + 1) and missed
# every key that really carries one. Measured while writing this pass: it named
# tnt_err_advanced_off x51 on a 50-character value with no dash in it, and did not
# name tnt_err_threat_unafraid, which carries one. The script header already
# warned about this trap for $CD/$cd; it cost a measurement a second time here.
$offenders = @()
$vanillaKeys = @()
$emRows      = @()

$legacyWrappers = @($script:cdSites | Where-Object { $_.Wrapper -ne 'custom_tooltip' })
foreach ($site in $legacyWrappers) {
    $offenders += [pscustomobject]@{
        Gui = $site.Gui; Kind = 'WRAPPER_NOT_CUSTOM_TOOLTIP'; Key = $site.Key
        Where = ("{0}:{1}" -f $site.File, $site.Line); Cd = $site.Wrapper
        Detail = ("BuildTooltip reason wrapper must be custom_tooltip (law 10d); found {0}" -f $site.Wrapper)
    }
}

$cdKeys = @($script:cdSites | Where-Object { $_.Key -ne '' } | Select-Object -ExpandProperty Key -Unique | Sort-Object)
foreach ($key in $cdKeys) {
    $site = @($script:cdSites | Where-Object { $_.Key -eq $key })[0]
    foreach ($lang in @('EN','RU')) {
        if (-not $LOC[$lang].ContainsKey($key)) {
            if (Test-VanillaKey $key $lang) { $vanillaKeys += ("{0}  {1}  [vanilla key - not ours to police]" -f $key, $lang); continue }
            $offenders += [pscustomobject]@{
                Gui = $site.Gui; Kind = ('UNRESOLVED_' + $lang); Key = $key
                Where = $YML[$lang]; Cd = ("{0}:{1}" -f $site.File, $site.Line); Detail = 'key absent from this language'
            }
            continue
        }
        $e = $LOC[$lang][$key]
        $v = $e.Value
        if ($MARKUPRX.IsMatch($v) -and $v.Contains('#!')) {
            $frag = @()
            foreach ($mm in [regex]::Matches($v, '#[A-Za-z_;]+[ :][^#]*#!')) { $frag += $mm.Value }
            $offenders += [pscustomobject]@{
                Gui = $site.Gui; Kind = ('MARKUP_' + $lang); Key = $key
                Where = ("{0}:{1}" -f $YML[$lang], $e.Line); Cd = ("{0}:{1}" -f $site.File, $site.Line)
                Detail = ($frag -join ' , ')
            }
        }
        if ($v.Contains('[')) {
            $offenders += [pscustomobject]@{
                Gui = $site.Gui; Kind = ('TOKEN_' + $lang); Key = $key
                Where = ("{0}:{1}" -f $YML[$lang], $e.Line); Cd = ("{0}:{1}" -f $site.File, $site.Line)
                Detail = 'carries a [..] token (law 10a)'
            }
        }
        if ($v.Contains('$')) {
            $offenders += [pscustomobject]@{
                Gui = $site.Gui; Kind = ('NESTED_' + $lang); Key = $key
                Where = ("{0}:{1}" -f $YML[$lang], $e.Line); Cd = ("{0}:{1}" -f $site.File, $site.Line)
                Detail = 'carries a $...$ nested key'
            }
        }
        # PASS E's raw material. Collected here because this loop already holds the
        # key, the language, the value and the .yml line; reported separately below
        # so the census prints even on a clean tree, which is the whole point of it.
        if ($v.Contains($EMDASH)) {
            $emRows += [pscustomobject]@{
                Gui = $site.Gui; Lang = $lang; Key = $key
                Where = ("{0}:{1}" -f $YML[$lang], $e.Line); Cd = ("{0}:{1}" -f $site.File, $site.Line)
                Count = ([regex]::Matches($v, [regex]::Escape($EMDASH))).Count
            }
        }
    }
}
if ($FailOnEmDash) {
    foreach ($x in $emRows) {
        $offenders += [pscustomobject]@{
            Gui = $x.Gui; Kind = ('EMDASH_' + $x.Lang); Key = $x.Key
            Where = $x.Where; Cd = $x.Cd
            Detail = ("carries U+2014 EM DASH x{0} - restructure the clause so no dash is needed; a hyphen where Russian requires an em dash is a fresh error, not a fix" -f $x.Count)
        }
    }
}

# ===========================================================================
# PASS A - the bare-row discipline, kept verbatim from the previous revision
# ===========================================================================
$bare = @()
foreach ($f in Get-ChildItem (Join-Path $ModRoot 'common\scripted_guis') -Filter *.txt) {
    $lines = [System.IO.File]::ReadAllLines($f.FullName)
    $depth = 0; $gui = ''; $ivDepth = -1; $stack = @()
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $l = $lines[$i]; $c = $l.IndexOf('#'); if ($c -ge 0) { $l = $l.Substring(0,$c) }

        if ($depth -eq 0 -and $l -match '^([A-Za-z0-9_]+)\s*=\s*\{') { $gui = $Matches[1] }

        $enteringIsValid = ($ivDepth -lt 0 -and $depth -eq 1 -and $l -match '^\s*is_valid\s*=\s*\{' -and $reached.Contains($gui))

        if ($ivDepth -ge 0) {
            if ($l -match '^\s*([A-Za-z0-9_\$]+)\s*(=|<=|>=|<|>|!=|\?=)') {
                $key = $Matches[1]; $klow = $key.ToLower()
                $inSuppressed = ($stack -contains 'SUPPRESSED')
                if (-not $inSuppressed -and -not ($stack -contains 'SKIP') -and -not ($stack -contains 'ARGS')) {
                    if ($SUPPRESS -contains $klow)      { }
                    elseif ($SKIP -contains $klow)      { }
                    elseif ($PASSTHROUGH -contains $klow) { }
                    else {
                        $why = 'NO_TRIGGER_LOC_ENTRY'
                        if ($trigloc.Contains($klow)) { $why = 'HAS_ENTRY_BUT_BARE' }
                        $bare += [pscustomobject]@{
                            Gui = $gui; Key = $key; Kind = $why
                            File = $f.Name; Line = $i + 1; Text = $lines[$i].Trim()
                        }
                    }
                }
            }
        }

        $open  = ([regex]::Matches($l,'\{')).Count
        $close = ([regex]::Matches($l,'\}')).Count
        if ($ivDepth -ge 0 -or $enteringIsValid) {
            $label = 'PLAIN'
            if ($l -match '^\s*([A-Za-z0-9_\$]+)\s*=') {
                $k2 = $Matches[1].ToLower()
                if ($SUPPRESS -contains $k2) { $label = 'SUPPRESSED' }
                elseif ($SKIP -contains $k2) { $label = 'SKIP' }
                elseif ($modTrigNames.Contains($k2)) { $label = 'ARGS' }
            }
            for ($o = 0; $o -lt $open;  $o++) { $stack += $label }
            for ($o = 0; $o -lt $close; $o++) { if ($stack.Count) { $stack = $stack[0..($stack.Count-2)] } }
        }

        if ($enteringIsValid) { $ivDepth = $depth; $stack = @('PLAIN') }
        elseif ($ivDepth -ge 0) {
            $newDepth = $depth + $open - $close
            if ($newDepth -le $ivDepth) { $ivDepth = -1; $stack = @() }
        }
        $depth += $open - $close
        if ($depth -lt 0) { $depth = 0 }
    }
}
foreach ($b in $bare) {
    $offenders += [pscustomobject]@{
        Gui = $b.Gui; Kind = ('BARE_ROW/' + $b.Kind); Key = $b.Key
        Where = ("{0}:{1}" -f $b.File, $b.Line); Cd = '-'; Detail = $b.Text
    }
}

# ===========================================================================
# REPORT
# ===========================================================================
Write-Host "scripted_guis on the BuildTooltip path : $($reached.Count)"
Write-Host ($reached | Sort-Object) -Separator ', '
Write-Host ""
Write-Host "reason wrapper sites reached : $($script:cdSites.Count)   distinct keys : $($cdKeys.Count)"
$wrapperCensus = @($script:cdSites | Group-Object Wrapper | Sort-Object Name | ForEach-Object { "{0}={1}" -f $_.Name, $_.Count })
Write-Host ("wrapper kinds                : {0}" -f ($wrapperCensus -join ', '))
Write-Host "mod scripted triggers indexed for recursion : $($modTrigBody.Count)"
if ($vanillaKeys.Count -gt 0) {
    Write-Host ""
    Write-Host "NOTE - reached keys that resolve against VANILLA localization, not ours : $($vanillaKeys.Count)"
    $vanillaKeys | ForEach-Object { Write-Host "      $_" }
}

Write-Host ""
Write-Host ("PASS H - BUILDTOOLTIP REASON WRAPPERS NOT custom_tooltip : {0}" -f $legacyWrappers.Count)
if ($legacyWrappers.Count -eq 0) {
    Write-Host "      none - every reached reason wrapper uses custom_tooltip."
} else {
    $legacyWrappers | ForEach-Object {
        Write-Host ("      FAIL {0}  {1}  {2}:{3}  [{4}]" -f $_.Wrapper, $_.Key, $_.File, $_.Line, $_.Gui)
    }
}

# ---------------------------------------------------------------------------
# PASS D - THE ENTRY-LESS-LEAF CENSUS, NOW SPLIT BY FORM.
#   BLOCK form  -> PASS G, a FAIL class since round 8 (see the header).
#   scalar form -> still a NOTE, and it must stay one: turning the 72 scalar rows
#                  red would put this gate permanently in the red on a shape the
#                  engine demonstrably tolerates somewhere, and a red gate is not
#                  read. If the next hover confirms hypothesis (f) the answer is
#                  not to redden them either - it is to replace the construct.
# ---------------------------------------------------------------------------
$inCD    = @($script:census | Where-Object { $_.InCD })
$inCDblk = @($inCD | Where-Object { $_.Form -eq 'BLOCK' })
$inCDsc  = @($inCD | Where-Object { $_.Form -ne 'BLOCK' })
$pairs = @($inCDsc | ForEach-Object { $_.Leaf.ToLower() + ' @ ' + $_.CdKey } | Sort-Object -Unique)
$keysAffected = @($inCDsc | Select-Object -ExpandProperty CdKey -Unique | Where-Object { $_ -ne '' })
Write-Host ""
Write-Host "NOTE - ENTRY-LESS SCALAR-LEAF CENSUS (NOT a failure - read the round-8 section of the header)"
Write-Host ("      inside a reason wrapper     : {0} occurrences, {1} distinct leaf+key pairs, {2} of {3} reached keys affected" -f $inCDsc.Count, $pairs.Count, $keysAffected.Count, $cdKeys.Count)
Write-Host ("      guis affected               : {0}" -f (@($inCDsc | Select-Object -ExpandProperty Gui -Unique).Count))
Write-Host  '      WHY SCALAR IS NOT A FAILURE: a scalar row is a plain or value-comparison trigger and'
Write-Host  '      the engine can render one generically from $COMPARATOR$ and $NUM$ without any entry'
Write-Host  "      (<vanilla>\common\trigger_localization\_trigger_localization.info, 'Value Comparison"
Write-Host  "      Triggers'). A BLOCK-form parameterised trigger has nothing to substitute, and vanilla"
Write-Host  "      never asks for one: of 285 has_dread_level_towards sites, all but three sit where"
Write-Host  "      nothing describes them, and the one that does not - vanilla's own"
Write-Host  "      00_legal_triggers.txt:12 - names a custom_description key that exists in NEITHER"
Write-Host  "      english NOR russian localization. Context, not a control: vanilla ships 2,985"
Write-Host  "      entry-less leaf occurrences inside custom_description on the INTERACTION/DECISION"
Write-Host  "      path, which CLAUDE.md law 10a records as behaving differently from this one."
$top = $inCDsc | Group-Object { $_.Leaf.ToLower() } | Sort-Object Count -Descending | Select-Object -First 8
Write-Host  "      most common entry-less scalar leaves:"
$top | ForEach-Object { Write-Host ("        {0,-32} x{1}" -f $_.Name, $_.Count) }

# ---------------------------------------------------------------------------
# PASS G - THE ROUND-8 FAIL CLASS.
# A BLOCK-form engine trigger with no common\trigger_localization\ entry, reached
# inside a reason wrapper from a [TntTip()] is_valid. Exactly one such row has
# ever existed in this mod - has_dread_level_towards = { target level } inside
# tnt_threat_feared_trigger - and it sat inside the only key that has ever printed
# "<key> has no localization". It is gone as of round 8 and it must never come
# back silently, which is what this class is for. It was a NOTE for two rounds and
# a NOTE is what let it ship.
# ---------------------------------------------------------------------------
foreach ($b in $inCDblk) {
    $offenders += [pscustomobject]@{
        Gui = $b.Gui; Kind = 'BLOCK_LEAF_NO_ENTRY'; Key = $b.CdKey
        Where = ("{0}:{1}" -f $b.File, $b.Line); Cd = $b.Leaf
        Detail = ('block-form engine trigger {0} = {{ {1} }} has no trigger_localization entry and is reached inside a described reason wrapper - express it with entried leaves, or move it off the described path' -f $b.Leaf, $b.Fields)
    }
}
Write-Host ""
Write-Host ("PASS G - ENTRY-LESS BLOCK-FORM LEAVES INSIDE A REACHED REASON WRAPPER : {0}" -f $inCDblk.Count)
if ($inCDblk.Count -eq 0) {
    Write-Host "      none - the mod ships no undescribable block-form leaf on any described path."
} else {
    $inCDblk | ForEach-Object { Write-Host ("      FAIL {0} = {{ {1} }}  key {2}  {3}:{4}  [{5}]" -f $_.Leaf, $_.Fields, $_.CdKey, $_.File, $_.Line, $_.Gui) }
}

# ---------------------------------------------------------------------------
# PASS E - THE EM-DASH CENSUS. A NOTE TODAY, A FAIL ON ONE SWITCH.
#
# WHY IT IS A CENSUS AND NOT A GATE. Hypothesis (a) is that U+2014 in the VALUE
# of the described key is what makes the render fail. It is 1-of-1 observed
# against 0-of-0, i.e. undetermined: the one key ever seen printing the message
# (tnt_err_threat_unafraid, RUSSIAN session) carries one, and no reached key has
# ever been seen RENDERING at all, so there is no negative side to the table.
# Mechanically the hypothesis is weak - "%s has no localization" is a KEY
# resolution failure and a character inside the VALUE cannot make the key lookup
# fail - but round 6's exoneration of it was vacuous (see the ledger above), so
# it is not cleared either.
#
# THEREFORE: print the census every run so the ratio is on the record and nobody
# has to re-derive it, and keep -FailOnEmDash off until a hover settles it. The
# day a hover shows an em-dash key printing the message while a dash-free key on
# the same surface renders, flip the switch in the caller and the census becomes
# the gate. The day a hover shows an em-dash key RENDERING, delete this pass.
#
# REPLACEMENT DISCIPLINE, if the switch is ever thrown: restructure the clause so
# that no dash is needed at all. Russian orthography requires an em dash in
# several of these constructions and a hyphen substituted for one is a FRESH
# error, not a fix. The two Russian rewrites and the one English rewrite are
# already composed, at the foot of localization\russian\tnt_l_russian.yml and
# localization\english\tnt_l_english.yml, so nobody has to write Russian prose
# under time pressure. NEVER run a character-level replace over these values.
# ---------------------------------------------------------------------------
$emByLang = @{ EN = @($emRows | Where-Object { $_.Lang -eq 'EN' }); RU = @($emRows | Where-Object { $_.Lang -eq 'RU' }) }
Write-Host ""
if ($FailOnEmDash) {
    Write-Host "PASS E - EM-DASH CENSUS  *** -FailOnEmDash IS ON: every row below is a FAIL ***"
} else {
    Write-Host "NOTE - EM-DASH CENSUS (U+2014 in a reached reason-wrapper value; NOT a failure today)"
}
foreach ($lang in @('EN','RU')) {
    $n = @($emByLang[$lang]).Count
    Write-Host ("      {0}: {1} of {2} reached keys carry U+2014, {3} do not" -f $lang, $n, $cdKeys.Count, ($cdKeys.Count - $n))
}
if ($emRows.Count -eq 0) {
    Write-Host "      (none - hypothesis (a) has nothing left to stand on in either language)"
} else {
    foreach ($x in ($emRows | Sort-Object Lang, Key)) {
        Write-Host ("      {0}  {1,-28} {2,-24} x{3}  cd {4}  [{5}]" -f $x.Lang, $x.Key, $x.Where, $x.Count, $x.Cd, $x.Gui)
    }
}
Write-Host  "      READ IT AS A BASE RATE: screen5 is a RUSSIAN session, so the RU row governs. If the"
Write-Host  "      one observed key is one of N em-dash keys out of the reached total, the chance a"
Write-Host  "      single random failure lands on an em-dash key is N/total under the null hypothesis."

# ---------------------------------------------------------------------------
# PASS F - THE THREAT-ROW ROSTER. A NOTE, AND THE EXPERIMENT-STATE ALARM.
#
# ROUND 7's key/row crossover and its rename are BOTH CONCLUDED. What this pass
# guards now is the shipped roster, and the retired instrument key gone from the
# .yml. It exists because two rounds of this project left an experiment armed on a
# shipped tree, and because a session must never have to guess whether a previous
# round did.
# *** THE ROSTER MOVED 2026-08-25, AND IT IS THE RATIO RULING THAT MOVED IT. *** The
# four-rule ladder collapsed into one comparison. The 2026-08-28 relation gate adds
# one more named reason, so the toggle now surfaces THREE tnt_err_threat_* rows -
# relation (independent/non-allied/no-hostage pair), weak (the whole formula against
# the bar) and recent (the 15-year lock) - inside four custom_tooltip wrappers with
# tnt_err_no_partner in the
# trigger_else. tnt_err_threat_unknown and tnt_err_threat_nofear are PINNED ORPHANS:
# VERIFIED ON DISK THIS ROUND - defined in all nine languages, ZERO rows anywhere
# under common\. Leaving the old four in $SHIP below would have left this alarm
# permanently red on a correct tree, and a red gate is not read.
# THE ROW ORDER IS AN INVARIANT, NOT A PREFERENCE: row-for-row parity with
# tnt_can_threat_trigger (common\scripted_triggers\tnt_41_gates.txt) is stated at
# tnt_20_scripted_guis.txt - the same relation gate, number and lock, in the same order.
# Edit both or neither.
# ---------------------------------------------------------------------------
$THREATGUI = 'tnt_threat_p_toggle'
$trows = @($script:cdSites | Where-Object { $_.Gui -eq $THREATGUI } | Sort-Object Line)
Write-Host ""
Write-Host ("NOTE - THREAT-ROW ROSTER: {0}.is_valid, reason wrappers in file order (they are custom_tooltip since the 10d slice)" -f $THREATGUI)
if ($trows.Count -eq 0) {
    Write-Host ("      {0} is NOT on the BuildTooltip path on this tree - the probe has nothing to read." -f $THREATGUI)
} else {
    $i = 0
    foreach ($r in $trows) {
        $i++
        Write-Host ("      row {0}  {1,-28} {2}:{3}" -f $i, $r.Key, $r.File, $r.Line)
    }
    $tk    = @($trows | Where-Object { $_.Key -like 'tnt_err_threat_*' } | Select-Object -ExpandProperty Key)
    $SHIP  = 'tnt_err_threat_relation|tnt_err_threat_weak|tnt_err_threat_recent'
    $have  = ($tk -join '|')
    if ($have -eq $SHIP) {
        Write-Host "      STATE: SHIPPED ROSTER - no experiment is armed, nothing to revert."
    } else {
        Write-Host "      STATE: *** THE THREAT ROWS ARE NOT THE SHIPPED ROSTER. ***"
        Write-Host ("      expected : {0}" -f $SHIP)
        Write-Host ("      found    : {0}" -f $have)
        Write-Host "      Either an experiment is armed and must be reverted, or the row order drifted"
        Write-Host "      out of parity with tnt_can_threat_trigger. Read the verdict block at the row"
        Write-Host "      itself and the foot of both authored .yml before changing anything."
    }
    $retired = @()
    foreach ($lang in @('EN','RU')) { if ($LOC[$lang].ContainsKey('tnt_err_threat_unafraid')) { $retired += $lang } }
    if ($retired.Count -eq 0) {
        Write-Host "      tnt_err_threat_unafraid: retired and absent from both authored .yml - correct."
    } else {
        Write-Host ("      NOTE: tnt_err_threat_unafraid is still defined in {0}. It was retired in round 8;" -f ($retired -join '+'))
        Write-Host "      if it has been revived on purpose it must exist in ALL NINE languages (law 9)."
    }
}

# --- interaction-described surfaces, unchanged, still NOTES ------------------
# The scan above walks common\scripted_guis only, because that is the surface
# [TntTip(S)] reaches. The engine also describes an interaction's
# is_valid_showing_failures_only and has_valid_target_showing_failures_only.
# Reported as NOTES on purpose: the mod has one bare row among them and it is
# safe because that trigger's body is four custom_description blocks. Making it
# FAIL would turn this gate permanently red, and a red gate is not read.
$notes = @()
$iaDir = Join-Path $ModRoot 'common\character_interactions'
if (Test-Path $iaDir) {
    foreach ($f in Get-ChildItem $iaDir -Filter *.txt) {
        $lines = [System.IO.File]::ReadAllLines($f.FullName)
        $depth = 0; $blkDepth = -1; $stack = @()
        for ($i = 0; $i -lt $lines.Count; $i++) {
            $l = $lines[$i]; $c = $l.IndexOf('#'); if ($c -ge 0) { $l = $l.Substring(0, $c) }
            $opensBlock = $l -match '\{\s*$'

            if ($blkDepth -lt 0) {
                if ($l -match '^\s*(is_valid_showing_failures_only|has_valid_target_showing_failures_only)\s*=\s*\{') { $blkDepth = $depth; $stack = @() }
            }
            elseif ($l -match '^\s*([A-Za-z0-9_\$]+)\s*(=|<=|>=|<|>|!=|\?=)') {
                $key = $Matches[1]; $klow = $key.ToLower()
                $muted = ($stack -contains 'SUPPRESSED') -or ($stack -contains 'ARGS')
                if (-not $muted -and -not ($SUPPRESS -contains $klow) -and -not ($SKIP -contains $klow) -and -not ($PASSTHROUGH -contains $klow)) {
                    $notes += ("{0}:{1}  {2}" -f $f.Name, ($i + 1), $l.Trim())
                }
                if ($opensBlock) {
                    if ($SUPPRESS -contains $klow)                                   { $stack += 'SUPPRESSED' }
                    elseif ($klow -like 'tnt_*trigger' -or $klow -like 'tnt_*effect') { $stack += 'ARGS' }
                    else                                                             { $stack += 'PLAIN' }
                }
            }
            elseif ($blkDepth -ge 0 -and $opensBlock) { $stack += 'PLAIN' }

            $o = ([regex]::Matches($l, '\{')).Count; $cl = ([regex]::Matches($l, '\}')).Count
            if ($blkDepth -ge 0) { for ($k = 0; $k -lt $cl; $k++) { if ($stack.Count -gt 0) { $stack = $stack[0..($stack.Count - 2)] } } }
            $depth += $o - $cl; if ($depth -lt 0) { $depth = 0 }
            if ($blkDepth -ge 0 -and $depth -le $blkDepth) { $blkDepth = -1; $stack = @() }
        }
    }
}
Write-Host ""
Write-Host "NOTE - rows on the interaction-described surfaces (not failures) : $($notes.Count)"
$notes | ForEach-Object { Write-Host "      $_" }

Write-Host ""
if ($offenders.Count -eq 0) {
    Write-Host "PASS - every BuildTooltip reason wrapper is custom_tooltip; no reached key carries"
    Write-Host "       format markup, a [..] token, a nested key or an unresolved language; and"
    Write-Host "       no bare described row remains."
    exit 0
}
$offenders | Sort-Object Kind, Key | ForEach-Object {
    Write-Host ("FAIL  {0,-22} {1,-14} {2,-26} {3,-24} cd {4}" -f $_.Gui, $_.Kind, $_.Key, $_.Where, $_.Cd)
    Write-Host ("        {0}" -f $_.Detail)
}
Write-Host ""
Write-Host "OFFENDERS: $($offenders.Count)"
exit 1
