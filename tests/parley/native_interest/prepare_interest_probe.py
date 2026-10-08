"""Prepare an isolated complete-runtime Parley interest probe; never launch.

plan creates only fixture sources and a plan. freeze is a separate coordinator
step after authoring edits finish; it snapshots every file in mod/parley.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys

# Also supports loading this entry point by absolute filename in pure unit tests.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_configuration as configuration

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[2] / "mod/parley"
EVIDENCE = configuration.ExternalPath("evidence_root")
GAME = configuration.ExternalPath("game_root")
SETTINGS = configuration.ExternalPath("settings_source")
RELOAD_HELPER = configuration.ExternalPath("reload_helper")
add_path_arguments = configuration.add_arguments
configure_paths = configuration.configure
PRESETS = {"off": 0, "mild": .5, "standard": 1, "strict": 2}
TERMS = ("title", "subject", "courtier", "artifact", "vassal", "indep",
         "hostage", "hook", "marriage")
CONTRACTS = ("tax", "levy", "fort", "coin", "relig", "council", "revoke", "war", "succ")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(directory):
    return {p.relative_to(directory).as_posix(): sha(p)
            for p in sorted(directory.rglob("*")) if p.is_file()}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig" if path.suffix in (".txt", ".gui", ".yml") else "utf-8")


def dump(path, data):
    write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def reload_controls(close_before_load=False):
    # Reuse the reviewed native Save/Load GUI workers, not their unrelated tax
    # journal assertions. The global controller supplies the disk-stage guard.
    result = '''tniqa_reload_prepare = { scope = character effect = {
 if = { limit = { NOT = { has_variable = tniqa_reload_saved_token } }
  set_variable = { name = tniqa_reload_saved_token value = 1 }
  set_variable = { name = tniqa_reload_player value = root }
  debug_log = "TNI_RELOAD|prepared_saved_token|1"
 }
} }
tniqa_reload_log_save = { scope = character effect = {
 set_variable = { name = tniqa_reload_snapshot_ready value = yes }
 debug_log = "TNI_RELOAD|native_local_save|[GetVariableSystem.Get('tniqa_reload_save_name')]"
} }
tniqa_reload_mark_unsaved = { scope = character effect = {
 set_variable = { name = tniqa_reload_saved_token value = 2 }
 debug_log = "TNI_RELOAD|unsaved_token|2"
} }
tniqa_reload_log_load = { scope = character effect = {
 debug_log = "TNI_RELOAD|native_exact_local_load|[GetVariableSystem.Get('tniqa_reload_save_name')]"
} }
tniqa_reload_load_requested = { scope = character effect = { debug_log = "TNI_RELOAD|load_requested|yes" } }
tniqa_reload_load_parent_entered = { scope = character effect = { debug_log = "TNI_RELOAD|load_parent_entered|yes" } }
tniqa_reload_row_entered = { scope = character effect = { debug_log = "TNI_RELOAD|save_row_entered|yes" } }
tniqa_reload_row_name = { scope = character effect = { debug_log = "TNI_RELOAD|save_row_name|[GetVariableSystem.Get('tniqa_reload_row_name')]" } }
tniqa_reload_menu_observe = { scope = character effect = { debug_log = "TNI_RELOAD|load_wait_diagnostic|yes" } }
tniqa_reload_items_observe = { scope = character effect = { debug_log = "TNI_RELOAD|load_items_diagnostic|yes" } }
tniqa_reload_assert_loaded = { scope = character effect = {
 if = { limit = { var:tniqa_phase = 2 has_variable = tniqa_reload_saved_token
  var:tniqa_reload_saved_token = 1 NOT = { has_variable = tniqa_reload_proven } }
  if = { limit = { has_variable = tniqa_reload_snapshot_ready this = var:tniqa_reload_player }
   debug_log = "TNI_TEST|PASS|reload_actual_saved_state_restored"
  } else = {
   debug_log = "TNI_TEST|FAIL|reload_actual_saved_state_restored"
   set_variable = { name = tniqa_failed value = yes }
  }
  set_variable = { name = tniqa_reload_proven value = yes }
  remove_variable = tniqa_reload_request
  debug_log = "TNI_RELOAD|loaded_state_observed_before_recovery|yes"
 }
} }
'''
    if close_before_load:
        # The on-disk table remains open. Only memory is unmounted before Load,
        # allowing the normal load UI delay to dispose old portrait contexts.
        result = result.replace('debug_log = "TNI_RELOAD|unsaved_token|2"', 'remove_variable = tnt_open\n debug_log = "TNI_RELOAD|unsaved_token|2"')
    return result


def fixture(preset, rich=False, diagnostic=False):
    labels, values = [], []

    def assertion(label, condition):
        if label in labels:
            raise ValueError("Duplicate assertion " + label)
        labels.append(label)
        return (f'if = {{ limit = {{ {condition} }} debug_log = "TNI_TEST|PASS|{label}" }} '
                f'else = {{ debug_log = "TNI_TEST|FAIL|{label}" '
                'set_variable = { name = tniqa_failed value = yes } }\n')

    def delta(name, body):
        values.append(f"tniqa_{name}_value = {{ {body} }}\n")
        return f"tniqa_{name}_value"

    def reset():
        return ("tnt_reset_offer_effect = yes\n"
                "set_variable = { name = tnt_open value = yes }\n"
                "set_variable = { name = tnt_partner value = scope:tniqa_partner }\n"
                "clear_saved_scope = tnt_me\nclear_saved_scope = tnt_p\n")

    diag = {"quote": "tnt_ai_accept_value", "gain_base": "tnt_interest_gain_base_value",
            "gain_adjusted": "tnt_interest_gain_adjusted_value", "loss_base": "tnt_interest_loss_base_value",
            "loss_adjusted": "tnt_interest_loss_adjusted_value", "standing_base": "tnt_interest_gain_base_standing_value",
            "standing_adjusted": "tnt_interest_gain_adjusted_standing_value", "penalty": "tnt_interest_penalty_value",
            "deal_mod_sum": "tnt_deal_mod_sum_value", "threshold": "tnt_threshold_value",
            "owner_gold": "gold", "partner_gold": "var:tnt_partner.gold",
            "owner_income": "yearly_character_income", "partner_income": "var:tnt_partner.yearly_character_income",
            "partner_warchest": "var:tnt_partner.war_chest_gold_maximum",
            "partner_reserved": "var:tnt_partner.reserved_gold_maximum",
            "partner_domain": "var:tnt_partner.domain_size", "partner_domain_limit": "var:tnt_partner.domain_limit",
            "partner_vassals": "var:tnt_partner.vassal_count", "partner_vassal_limit": "var:tnt_partner.vassal_limit",
            "partner_council_vacancies": "tnt_interest_council_vacancies_value"}
    capacity_flags = ("has_treasury", "is_at_war", "ai_has_warlike_personality",
                      "ai_has_cautious_personality", "ai_has_conqueror_personality",
                      "ai_has_economical_boom_personality", "ai_has_pious_builder_personality",
                      "ai_should_focus_on_building_in_their_capital")
    if diagnostic:
        diag["partner_expenses"] = "var:tnt_partner.monthly_character_expenses"
        diag["gold_conversion"] = "tnt_gold_per_point_value"
        diag["strength"] = "tnt_interest_strength_value"
        diag["alliance"] = "tnt_val_alliance_p_value"
        for term in ("threat_p", "usehook_p", "usehook_r"):
            diag[term] = f"tnt_val_{term}_value"
        for flag in capacity_flags:
            diag[flag] = delta("input_" + flag,
                              f"value = 0 if = {{ limit = {{ var:tnt_partner = {{ {flag} = yes }} }} add = 1 }}")
        for currency in ("gold", "prestige", "piety", "influence"):
            for side in ("p", "r"):
                name = f"{currency}_{side}"
                diag["draft_" + name] = delta("input_" + name,
                    f"value = 0 if = {{ limit = {{ exists = var:tnt_{name} }} add = var:tnt_{name} }}")
        for component in ("equipped_share", "alternative_share", "primary_armament_retained",
                          "armor_retained", "regalia_retained", "helmet_retained"):
            diag["artifact_" + component] = f"tnt_interest_artifact_{component}_value"
    for relation in ("opinion", "faith", "culture", "kin", "relation", "dread", "war", "ally"):
        diag["rel_" + relation] = f"tnt_relmod_{relation}_value"
    for term in ("gold", "prestige", "piety", "influence") + TERMS:
        for side in ("p", "r"):
            for kind in ("base", "adjusted"):
                diag[f"{term}_{side}_{kind}"] = f"tnt_interest_{term}_{side}_{kind}_value"
            diag[f"{term}_{side}_factor"] = f"tnt_interest_{term}_{side}_factor_value"
        if term in ("gold", "prestige", "piety", "influence"):
            diag[term + "_stock"] = f"tnt_interest_{term}_stock_value"
            diag[term + "_capacity"] = f"tnt_interest_{term}_capacity_value"
        if term in ("title", "subject", "courtier", "artifact"):
            for side in ("p", "r"):
                diag[f"count_{term}_{side}"] = f"tnt_count_sel_{term}_{side}_value"
    for term in CONTRACTS:
        diag["ob_" + term + "_base"] = f"tnt_val_ob_{term}_value"
        diag["ob_" + term + "_adjusted"] = f"tnt_interest_ob_{term}_effective_value"

    def reload_oracles():
        # Independent test-only arithmetic reads captured native inputs, never
        # production capacities, weighted prices, factors or aggregate gain.
        body = ""
        for stage in ("before", "after"):
            ref = lambda key: f"var:tniqa_diag_{stage}_{key}"
            cap = delta("oracle_" + stage + "_capacity",
                f"value = 100 add = {{ value = {ref('partner_income')} min = 0 max = 25000 multiply = 2 }} "
                f"if = {{ limit = {{ {ref('has_treasury')} = 0 }} "
                f"add = {{ value = {ref('partner_warchest')} min = 0 max = 25000 add = {{ value = {ref('partner_reserved')} min = 0 max = 25000 }} }} "
                f"if = {{ limit = {{ OR = {{ {ref('ai_has_warlike_personality')} = 1 {ref('ai_has_cautious_personality')} = 1 {ref('ai_has_conqueror_personality')} = 1 }} }} add = {{ value = {ref('partner_warchest')} min = 0 max = 25000 }} }} "
                f"if = {{ limit = {{ {ref('is_at_war')} = 1 }} add = {{ value = {ref('partner_expenses')} min = 0 max = 2000 multiply = 12 }} }} }} "
                f"if = {{ limit = {{ OR = {{ {ref('ai_has_economical_boom_personality')} = 1 {ref('ai_has_pious_builder_personality')} = 1 {ref('ai_should_focus_on_building_in_their_capital')} = 1 }} }} add = {{ value = {ref('partner_income')} min = 0 max = 25000 }} }} min = 100 max = 100000")
            amount = delta("oracle_" + stage + "_amount",
                           f"value = {ref('draft_gold_p')} subtract = {ref('draft_gold_r')} min = 0")
            full = delta("oracle_" + stage + "_full",
                         f"value = {cap} subtract = {ref('gold_stock')} min = 0 max = {amount}")
            price = delta("oracle_" + stage + "_gold_points",
                f"value = {cap} multiply = 2 subtract = {ref('gold_stock')} min = 0 max = {amount} subtract = {full} min = 0 "
                f"divide = {{ value = 1 add = {ref('strength')} min = 1 }} add = {full} divide = {{ value = {ref('gold_conversion')} min = 1 }}")
            for name, expected, actual in (("capacity", cap, ref("gold_capacity")),
                                           ("gold_points", price, ref("gold_p_adjusted"))):
                error = delta("oracle_" + stage + "_" + name + "_error", f"value = {expected} subtract = {actual}")
                body += assertion("reload_" + stage + "_independent_" + name, error + " = 0")
            # This rich fixture is a net gold gift after Auto-balance; reject a
            # different branch instead of pretending this oracle covers it.
            body += assertion("reload_" + stage + "_oracle_domain",
                              f"{ref('strength')} > 0 {ref('draft_gold_p')} >= {ref('draft_gold_r')} {ref('gold_r_adjusted')} = 0")
            gain_body = f"value = {price} "
            for term in ("prestige", "piety", "influence") + TERMS:
                gain_body += f"add = {ref(term + '_p_adjusted')} "
            gain_body += f"add = {ref('alliance')} "
            for term in CONTRACTS:
                gain_body += f"add = {ref('ob_' + term + '_adjusted')} "
            gain = delta("oracle_" + stage + "_gain", gain_body + "round = yes")
            unit = delta("oracle_" + stage + "_unit", f"value = {gain} min = 0 divide = 100")
            score_body = f"value = {gain} "
            for relation in ("opinion", "faith", "culture", "kin", "relation", "war", "ally"):
                score_body += f"add = {{ value = {ref('rel_' + relation)} multiply = {unit} }} "
            score_body += f"subtract = {{ value = {ref('threshold')} multiply = {unit} }} "
            score_body += f"if = {{ limit = {{ {ref('deal_mod_sum')} < -100 }} add = {{ value = 100 add = {ref('deal_mod_sum')} multiply = -1 min = 0 multiply = {unit} }} }} "
            loss = delta("oracle_" + stage + "_loss", "value = 0 " + " ".join(
                f"add = {ref(term + '_r_adjusted')}" for term in ("gold", "prestige", "piety", "influence") + TERMS) + " round = yes")
            score_body += f"subtract = {loss} add = {ref('threat_p')} add = {ref('usehook_p')} add = {ref('usehook_r')} round = yes subtract = {ref('quote')}"
            score_error = delta("oracle_" + stage + "_score_error", score_body)
            body += assertion("reload_" + stage + "_independent_score", score_error + " = 0")
        # Only monthly expenses may change in this focused reproduction. Every
        # other captured raw field and non-gold per-term price must serialize
        # exactly. The changed expense is independently repriced above.
        allowed = {"quote", "gain_adjusted", "standing_adjusted", "penalty", "gold_capacity",
                   "gold_p_adjusted", "gold_p_factor", "partner_expenses"}
        invariant = " ".join(f"tniqa_diag_{key}_value = 0" for key in diag if key not in allowed)
        body += assertion("reload_preserves_draft_stocks_and_other_terms", invariant)
        body += assertion("reload_expense_context_and_capacity_agree",
            "OR = { AND = { tniqa_diag_partner_expenses_value = 0 tniqa_diag_gold_capacity_value = 0 } "
            "AND = { NOT = { tniqa_diag_partner_expenses_value = 0 } "
            "var:tniqa_diag_after_has_treasury = 0 var:tniqa_diag_after_is_at_war = 1 } }")
        body += 'if = { limit = { tniqa_diag_partner_expenses_value = 0 } debug_log = "TNI_CONTEXT|reload|IDENTICAL_INPUTS" } else = { debug_log = "TNI_CONTEXT|reload|NATIVE_MONTHLY_EXPENSES_CHANGED" }\n'
        return body

    def diagnostic_snapshot(stage):
        if not diagnostic:
            return ""
        body = f'debug_log = "TNI_DIAG|BEGIN|{stage}"\n'
        for key, operand in diag.items():
            body += f"set_variable = {{ name = tniqa_diag_{stage}_{key} value = {operand} }}\n"
            body += f"save_scope_value_as = {{ name = tniqa_diag_{stage}_{key} value = var:tniqa_diag_{stage}_{key} }}\n"
            if stage == "after":
                body += f"save_scope_value_as = {{ name = tniqa_diag_before_{key} value = var:tniqa_diag_before_{key} }}\n"
                difference = delta("diag_" + key, f"value = var:tniqa_diag_after_{key} subtract = var:tniqa_diag_before_{key}")
                body += (f'if = {{ limit = {{ {difference} > 0 }} debug_log = "TNI_DIFF|{key}|UP" }} '
                         f'else_if = {{ limit = {{ {difference} < 0 }} debug_log = "TNI_DIFF|{key}|DOWN" }} '
                         f'else = {{ debug_log = "TNI_DIFF|{key}|SAME" }}\n')
        # Installed native precedent: 00_test_interactions.txt:286. Numeric
        # saved scope values are logged by the engine; no invented loc getter.
        body += 'debug_log_scopes = yes\n' + f'debug_log = "TNI_DIAG|END|{stage}"\n'
        return body

    event = "namespace = tniqa\ntniqa.1 = { type = character_event hidden = yes immediate = {\n"
    event += 'debug_log = "TNI_TEST|BEGIN|interest"\nsave_scope_as = tniqa_player\n'
    event += "title:e_byzantium.holder = { save_scope_as = tniqa_partner }\n"
    event += assertion("native_participants", "is_ai = no exists = scope:tniqa_partner scope:tniqa_partner = { is_ai = yes is_alive = yes }")
    event += assertion("preset_resolver", f"tnt_interest_strength_value = {PRESETS[preset]} tnt_interests_enabled_value = {int(preset != 'off')}")
    event += reset()
    event += assertion("empty_table_zero", "tnt_ai_accept_value = 0 tnt_interest_penalty_value = 0")
    for currency in ("gold", "prestige", "piety", "influence"):
        event += reset()
        event += f"set_variable = {{ name = tnt_{currency}_p value = 100 }}\n"
        event += assertion(currency + "_receiving_bounded", f"tnt_interest_{currency}_p_factor_value >= 0 tnt_interest_{currency}_p_factor_value <= 1")
        event += f"remove_variable = tnt_{currency}_p\nset_variable = {{ name = tnt_{currency}_r value = 100 }}\n"
        event += assertion(currency + "_surrender_bounded", f"tnt_interest_{currency}_r_factor_value >= 1 tnt_interest_{currency}_r_factor_value <= 100")
        if preset == "off":
            event += assertion(currency + "_off_identity", f"tnt_interest_{currency}_p_factor_value = 1 tnt_interest_{currency}_r_factor_value = 1")
    # Native inventories, not synthetic script-value mocks.
    event += reset()
    event += "scope:tniqa_partner = { add_prestige = { value = 200000 subtract = prestige } }\n"
    event += "set_variable = { name = tnt_prestige_p value = 100 }\n"
    event += assertion("saturated_prestige", f"tnt_interest_prestige_p_factor_value = {1 if preset == 'off' else 0}")
    if preset != "off":
        event += assertion("saturated_prestige_no_relation_leak", "tnt_interest_prestige_p_adjusted_value = 0 tnt_interest_gain_adjusted_standing_value = 0")
    event += reset()
    event += "scope:tniqa_partner = { add_gold = { value = 10 subtract = gold } }\n"
    event += "set_variable = { name = tnt_gold_r value = 10 }\n"
    event += assertion("reserve_loss", "tnt_interest_gold_r_factor_value = 1" if preset == "off" else "tnt_interest_gold_r_factor_value > 1")
    event += "set_variable = { name = tniqa_before_factor value = tnt_interest_gold_r_factor_value }\n"
    event += "scope:tniqa_partner = { add_gold = 200000 }\n"
    change = delta("stock_refresh", "value = tnt_interest_gold_r_factor_value subtract = var:tniqa_before_factor")
    event += assertion("native_stock_refresh", change + (" = 0" if preset == "off" else " < 0"))
    # Native .001 fixed-point regression: preserve finite utility even when its
    # display ratio rounds to zero. Price the amount first, never base * ratio.
    event += reset()
    event += "scope:tniqa_partner = { add_gold = { value = 0 subtract = gold } }\n"
    event += "set_variable = { name = tnt_gold_p value = 100000000 }\n"
    event += assertion("huge_gold_finite_utility", "tnt_interest_gold_p_weighted_amount_value > 0 tnt_interest_gold_p_net_adjusted_points_value > 0")
    if preset != "off":
        event += assertion("huge_gold_ratio_not_price", "tnt_interest_gold_p_factor_value >= 0 tnt_interest_gold_p_factor_value < 1 tnt_interest_gold_p_net_adjusted_points_value > 0")
    event += "set_variable = { name = tniqa_huge_gold_utility value = tnt_interest_gold_p_weighted_amount_value }\n"
    event += "set_variable = { name = tnt_gold_p value = 100000001 }\n"
    monotonic = delta("huge_gold_monotonic", "value = tnt_interest_gold_p_weighted_amount_value subtract = var:tniqa_huge_gold_utility")
    event += assertion("huge_gold_monotonic", monotonic + " >= 0")
    if preset != "off":
        event += "set_variable = { name = tnt_gold_p value = 1000000 }\nset_variable = { name = tniqa_gold_plateau value = tnt_interest_gold_p_net_adjusted_points_value }\n"
        event += "set_variable = { name = tnt_gold_p value = 10000000 }\n"
        plateau = delta("gold_plateau", "value = tnt_interest_gold_p_net_adjusted_points_value subtract = var:tniqa_gold_plateau")
        event += assertion("huge_gold_finite_demand_plateau", f"{plateau} = 0 tnt_interest_gold_p_net_adjusted_points_value > 0")
    event += reset()
    event += "set_variable = { name = tnt_gold_p value = 100 }\nset_variable = { name = tnt_gold_r value = 100 }\n"
    event += assertion("equal_gross_currency_net", "tnt_interest_penalty_value = 0")
    oracle = delta("ledger_error", "value = tnt_interest_gain_adjusted_standing_value subtract = tnt_interest_loss_adjusted_value add = tnt_val_threat_p_value add = tnt_val_usehook_p_value add = tnt_val_usehook_r_value round = yes subtract = tnt_ai_accept_value")
    event += assertion("central_ledger_reconciles", oracle + " = 0")
    # Real held titles/subjects/courtiers/artifacts supply selected-object scopes.
    event += reset()
    event += "random_held_title = { limit = { tier = tier_county } save_scope_as = tniqa_title_p }\n"
    event += "scope:tniqa_partner = { random_held_title = { limit = { tier = tier_county } save_scope_as = tniqa_title_r } }\n"
    event += "random_vassal = { save_scope_as = tniqa_subject_p }\n"
    event += "scope:tniqa_partner = { random_vassal = { save_scope_as = tniqa_subject_r } }\n"
    for side, employer in (("p", "scope:tniqa_player"), ("r", "scope:tniqa_partner")):
        event += (f'create_character = {{ name = "Interest native {side}" age = 30 gender = male '
                  f'employer = {employer} culture = {employer}.culture faith = {employer}.faith '
                  f'rite = {employer}.rite dynasty = none random_traits = no '
                  f'diplomacy = 12 martial = 12 stewardship = 12 intrigue = 12 learning = 12 '
                  f'save_scope_as = tniqa_courtier_{side} }}\n')
        event += f"{employer} = {{ random_character_artifact = {{ save_scope_as = tniqa_artifact_{side} }} }}\n"
        event += (f"if = {{ limit = {{ NOT = {{ exists = scope:tniqa_artifact_{side} }} }} "
                  f"{employer} = {{ create_artifact = {{ name = artifact_sword_name "
                  "description = placeholder visuals = sword type = sword "
                  "modifier = artifact_prowess_1_modifier wealth = 1 quality = 1 "
                  f"save_scope_as = tniqa_artifact_{side} history = {{ type = created_before_history }} }} }} }}\n")
        for term in ("title", "subject", "courtier", "artifact"):
            event += assertion(f"fixture_{term}_{side}", f"exists = scope:tniqa_{term}_{side}")
            event += f"if = {{ limit = {{ exists = scope:tniqa_{term}_{side} }} add_to_variable_list = {{ name = tnt_sel_{term}_{side} target = scope:tniqa_{term}_{side} }} }}\n"
        for term in ("vassal", "indep", "hook", "marriage"):
            event += f"set_variable = {{ name = tnt_{term}_{side} value = 1 }}\n"
        event += f"set_variable = {{ name = tnt_hostage_{side} value = scope:tniqa_courtier_{side} }}\n"
    # Marriage baseline is the existing MCA cache boundary. No claim of MCA
    # selection/recalculation/settlement acceptance is made by these adapter rows.
    event += "scope:tniqa_courtier_p = { set_variable = { name = tnt_wed_partner value = scope:tniqa_courtier_r } set_variable = { name = tnt_wed_gain value = 100 } set_variable = { name = tnt_wed_loss value = 50 } }\n"
    event += "add_to_variable_list = { name = tnt_wed_list target = scope:tniqa_courtier_p }\n"
    for term in TERMS:
        for side in ("p", "r"):
            factor = f"tnt_interest_{term}_{side}_factor_value"
            event += assertion(f"advanced_{term}_{side}", f"tnt_interest_{term}_{side}_selected_value > 0 {factor} >= {0 if side == 'p' else 1} {factor} <= {1 if side == 'p' else 100}")
    # Every existing permission remains authoritative. Report inapplicable
    # contract rights explicitly, do not manufacture a selected legal base price.
    event += "remove_variable = tnt_vassal_p\nset_variable = { name = tnt_vassal_r value = 1 }\n"
    event += "scope:tniqa_partner = { change_government = feudal_government }\nclear_saved_scope = tnt_p\n"
    for term in CONTRACTS:
        event += f"set_variable = {{ name = tnt_ob_{term} value = 1 }}\n"
        event += assertion(f"contract_{term}_sign_safe", f"tniqa_contract_{term}_delta_value <= 0")
        values.append(f"tniqa_contract_{term}_delta_value = {{ value = tnt_interest_ob_{term}_effective_value subtract = tnt_val_ob_{term}_value }}\n")
        event += f"set_variable = {{ name = tniqa_ob_{term}_base value = tnt_val_ob_{term}_value }}\n"
        event += f"if = {{ limit = {{ var:tniqa_ob_{term}_base = 0 }} debug_log = \"TNI_OBSERVE|contract_{term}|INAPPLICABLE_BASE_ZERO\" }} else = {{ debug_log = \"TNI_OBSERVE|contract_{term}|APPLICABLE_NONZERO\" }}\n"
    # Taxes and levies must exercise both signed directions, not merely zero.
    for term in ("tax", "levy"):
        for level in (1, 3):
            event += f"set_variable = {{ name = tnt_ob_{term} value = {level} }}\n"
            event += assertion(f"contract_{term}_level_{level}_nonzero", f"NOT = {{ tnt_val_ob_{term}_value = 0 }} tniqa_contract_{term}_delta_value <= 0")
    # Unlock the three rights that are legitimately unavailable in the initial
    # 867 fixture using actual native innovations/faith, never mocked gates.
    event += "culture = { add_innovation = innovation_battlements add_innovation = innovation_currency_02 }\n"
    event += "scope:tniqa_partner = { set_character_faith = scope:tniqa_player.faith }\n"
    for term in ("fort", "coin", "revoke"):
        event += assertion(f"contract_{term}_unlocked_nonzero", f"NOT = {{ tnt_val_ob_{term}_value = 0 }} tniqa_contract_{term}_delta_value <= 0")
    # Pressure must neither be discounted nor become part of the interest fee.
    event += reset() + "set_variable = { name = tnt_gold_r value = 100 }\n"
    event += "set_variable = { name = tniqa_penalty_before value = tnt_interest_penalty_value }\n"
    event += "set_variable = { name = tnt_threat_p value = 1 }\n"
    pressure_delta = delta("pressure_fee", "value = tnt_interest_penalty_value subtract = var:tniqa_penalty_before")
    event += assertion("pressure_outside_interest", pressure_delta + " = 0")
    event += assertion("pressure_ledger_reconciles", oracle + " = 0")
    # The production world helper settles an actual AI-to-AI exchange. The
    # scheduler/candidate selector is outside this synchronous helper scenario.
    event += "scope:tniqa_courtier_p = { save_scope_as = actor add_gold = { value = 10000 subtract = gold } }\n"
    event += "scope:tniqa_courtier_r = { save_scope_as = recipient add_gold = { value = 0 subtract = gold } set_culture = scope:tniqa_player.culture set_character_faith = scope:tniqa_player.faith }\n"
    event += "scope:actor = { set_relation_friend = { reason = friend_court_visit target = scope:recipient } add_opinion = { modifier = tnt_treaty_favor_opinion target = scope:recipient opinion = 50 } }\n"
    event += "scope:recipient = { add_opinion = { modifier = tnt_treaty_favor_opinion target = scope:actor opinion = 50 } }\n"
    event += assertion("ai_helper_native_participants", "scope:actor = { is_ai = yes } scope:recipient = { is_ai = yes }")
    event += assertion("ai_helper_positive_quote", "OR = { tnt_ai_deal_hook_low_value > 0 tnt_ai_deal_hook_high_value > 0 }")
    event += "set_variable = { name = tniqa_ai_sum value = { value = scope:actor.gold add = scope:recipient.gold } }\n"
    event += "tnt_ai_world_do_hook_effect = yes\n"
    ai_sum = delta("ai_gold_conservation", "value = scope:actor.gold add = scope:recipient.gold subtract = var:tniqa_ai_sum")
    event += assertion("ai_helper_actual_settlement", "scope:actor = { gold < 10000 has_hook = scope:recipient } scope:recipient = { gold > 0 }")
    event += assertion("ai_helper_gold_conserved", ai_sum + " = 0")
    # Recompute after a previously useful recipient becomes saturated. The
    # helper must refuse before any native resource mutation when interests run.
    event += "scope:recipient = { add_gold = { value = 200000 subtract = gold } }\n"
    if preset != "off":
        event += "set_variable = { name = tniqa_ai_actor_gold value = scope:actor.gold }\n"
        event += "set_variable = { name = tniqa_ai_recipient_gold value = scope:recipient.gold }\n"
        event += assertion("ai_helper_saturated_refusal", "tnt_ai_deal_hook_low_value <= 0 tnt_ai_deal_hook_high_value <= 0")
        event += "tnt_ai_world_do_hook_effect = yes\n"
        ai_actor = delta("ai_actor_stale_delta", "value = scope:actor.gold subtract = var:tniqa_ai_actor_gold")
        ai_recipient = delta("ai_recipient_stale_delta", "value = scope:recipient.gold subtract = var:tniqa_ai_recipient_gold")
        event += assertion("ai_helper_stale_no_mutation", f"{ai_actor} = 0 {ai_recipient} = 0")
    else:
        event += assertion("ai_helper_off_legacy_quote", "OR = { tnt_ai_deal_hook_low_value > 0 tnt_ai_deal_hook_high_value > 0 }")
    event += "clear_saved_scope = actor\nclear_saved_scope = recipient\n"
    # Finish at a live ordinary table for the actual scripted-GUI Auto-balance.
    event += reset() + "add_gold = { value = 10000 subtract = gold }\n"
    event += "scope:tniqa_partner = { add_gold = { value = 1000 subtract = gold } }\n"
    event += "set_variable = { name = tnt_gold_p value = 100 }\n"
    if rich:
        # A deliberately object-rich, currency-unbalanced draft. New courtiers
        # have no family overlap; artifacts are real native owned objects.
        event += "remove_variable = tnt_gold_p\nset_variable = { name = tnt_gold_r value = 1000 }\n"
        for side, employer in (("p", "scope:tniqa_player"), ("r", "scope:tniqa_partner")):
            for term in ("title", "subject"):
                event += f"add_to_variable_list = {{ name = tnt_sel_{term}_{side} target = scope:tniqa_{term}_{side} }}\n"
            for number in range(8):
                event += (f'create_character = {{ name = "Interest load {side}{number}" age = 30 gender = male '
                          f'employer = {employer} culture = {employer}.culture faith = {employer}.faith '
                          f'rite = {employer}.rite dynasty = none random_traits = no '
                          f'diplomacy = 12 martial = 12 stewardship = 12 intrigue = 12 learning = 12 '
                          f'save_scope_as = tniqa_load_courtier_{side}_{number} }}\n')
                event += f"add_to_variable_list = {{ name = tnt_sel_courtier_{side} target = scope:tniqa_load_courtier_{side}_{number} }}\n"
                event += (f"{employer} = {{ create_artifact = {{ name = artifact_sword_name "
                          "description = placeholder visuals = sword type = sword "
                          "modifier = artifact_prowess_1_modifier wealth = 1 quality = 1 "
                          f"save_scope_as = tniqa_load_artifact_{side}_{number} history = {{ type = created_before_history }} }} }}\n")
                event += f"add_to_variable_list = {{ name = tnt_sel_artifact_{side} target = scope:tniqa_load_artifact_{side}_{number} }}\n"
        event += assertion("rich_native_selected_inventory", "variable_list_size = { name = tnt_sel_courtier_p value = 8 } variable_list_size = { name = tnt_sel_courtier_r value = 8 } variable_list_size = { name = tnt_sel_artifact_p value = 8 } variable_list_size = { name = tnt_sel_artifact_r value = 8 }")
    event += "set_variable = { name = tniqa_live_gold value = gold }\n"
    event += "set_variable = { name = tniqa_partner_gold value = scope:tniqa_partner.gold }\n"
    event += "set_variable = { name = tniqa_phase value = 1 }\n} }\n"
    before = "tniqa_before_autobalance = { scope = character effect = {\n"
    before += 'debug_log = "TNI_TIMING|BEGIN|quote_10"\n'
    before += "while = { count = 10 set_variable = { name = tniqa_perf_quote value = tnt_ai_accept_value } }\n"
    before += assertion("native_repeated_quote_finishes", "var:tniqa_perf_quote >= -100000000")
    before += 'debug_log = "TNI_TIMING|END|quote_10"\ndebug_log = "TNI_TIMING|BEGIN|autobalance"\n} }\n'
    after = "tniqa_after_autobalance = { scope = character effect = {\n"
    after += 'debug_log = "TNI_TIMING|END|autobalance"\n'
    after += assertion("autobalance_returns", "exists = var:tnt_ab_state")
    gold = delta("owner_gold_delta", "value = gold subtract = var:tniqa_live_gold")
    partner_gold = delta("partner_gold_delta", "value = var:tnt_partner.gold subtract = var:tniqa_partner_gold")
    after += assertion("autobalance_no_settlement", f"{gold} = 0 {partner_gold} = 0")
    after += assertion("autobalance_honest_result", "OR = { tnt_ai_accept_value > 0 var:tnt_ab_state = 3 }")
    after += "set_variable = { name = tniqa_reload_quote value = tnt_ai_accept_value }\n"
    after += diagnostic_snapshot("before")
    after += "set_variable = { name = tniqa_reload_partner value = var:tnt_partner }\n"
    after += "set_variable = { name = tniqa_reload_request value = yes }\n"
    after += "set_variable = { name = tniqa_phase value = 2 }\n} }\n"
    reload = "tniqa_check_reloaded_quote = { scope = character effect = {\n"
    reload += diagnostic_snapshot("after")
    reload += assertion("reload_partner_restored", "exists = var:tnt_partner var:tnt_partner = var:tniqa_reload_partner")
    quote = delta("reload_quote_delta", "value = tnt_ai_accept_value subtract = var:tniqa_reload_quote")
    if diagnostic:
        reload += reload_oracles()
        reload += assertion("reload_quote_identical_if_inputs_identical",
                            f"OR = {{ NOT = {{ tniqa_diag_partner_expenses_value = 0 }} {quote} = 0 }}")
        reload += assertion("reload_current_ledger_reconciles", oracle + " = 0")
    else:
        reload += assertion("reload_quote_recomputed", quote + " = 0")
    reload += "save_scope_as = tniqa_player\nvar:tnt_partner = { save_scope_as = tniqa_partner save_scope_as = tnt_deal_partner }\n"
    # Exercise the real atomic master, not a copied transfer implementation.
    reload += reset() + "add_gold = { value = 10000 subtract = gold }\n"
    reload += "scope:tniqa_partner = { add_gold = { value = 0 subtract = gold } set_culture = scope:tniqa_player.culture set_character_faith = scope:tniqa_player.faith add_opinion = { modifier = tnt_treaty_favor_opinion target = scope:tniqa_player opinion = 50 } }\n"
    reload += "set_variable = { name = tnt_gold_p value = 100 }\n"
    reload += assertion("commit_positive_ready", "tnt_ai_accept_value > 0 tnt_deal_preflight_trigger = { PLAYER = root PARTNER = scope:tniqa_partner }")
    reload += "tnt_apply_deal_effect = yes\n"
    reload += assertion("commit_actual_conservation", "gold = 9900 scope:tniqa_partner = { gold = 100 }")
    reload += reset() + "add_gold = { value = 10000 subtract = gold }\n"
    reload += "scope:tniqa_partner = { add_gold = { value = 0 subtract = gold } }\nset_variable = { name = tnt_gold_p value = 100 }\n"
    reload += assertion("commit_stale_quote_initially_positive", "tnt_ai_accept_value > 0")
    reload += "scope:tniqa_partner = { add_gold = { value = 200000 subtract = gold } }\n"
    if preset != "off":
        reload += assertion("commit_stale_economic_reprice", "tnt_ai_accept_value <= 0 tnt_deal_preflight_trigger = { PLAYER = root PARTNER = scope:tniqa_partner }")
    reload += "tnt_apply_deal_effect = yes\n"
    reload += assertion("commit_stale_economic_result", "gold = 9900 scope:tniqa_partner = { gold = 200100 }" if preset == "off" else "gold = 10000 scope:tniqa_partner = { gold = 200000 }")
    reload += reset() + "set_variable = { name = tnt_gold_p value = 100 }\nadd_gold = { value = 0 subtract = gold }\n"
    reload += "set_variable = { name = tniqa_commit_partner_gold value = scope:tniqa_partner.gold }\n"
    reload += "tnt_apply_deal_effect = yes\n"
    broke = delta("commit_broke_partner_delta", "value = scope:tniqa_partner.gold subtract = var:tniqa_commit_partner_gold")
    reload += assertion("commit_stale_affordability_no_mutation", f"gold = 0 {broke} = 0")
    reload += assertion("fixture_no_prior_failure", "NOT = { exists = var:tniqa_failed }")
    reload += "set_variable = { name = tniqa_phase value = 3 }\n"
    reload += 'debug_log = "TNI_TEST|END|interest"\n} }\n'
    # The reusable reload overlay adds its own exact required native disk-token
    # assertion. Its historical lobby on_action is deliberately not used.
    labels.append("reload_actual_saved_state_restored")
    def native_gold_assignments(body):
        # add_gold rejects a negative quantity; unlike a generic numeric add it
        # is not a legal way to set a lower balance. Use native debit/credit.
        def replace(match):
            target = match.group(1)
            return (f"if = {{ limit = {{ gold > {target} }} remove_short_term_gold = {{ value = gold subtract = {target} }} }} "
                    f"else_if = {{ limit = {{ gold < {target} }} add_gold = {{ value = {target} subtract = gold }} }}")
        return re.sub(r"add_gold = \{ value = (\d+) subtract = gold \}", replace, body)
    return native_gold_assignments(event), "".join(values), native_gold_assignments(before + after + reload), labels


def prepare_plan(run, preset, rich=False, diagnostic=False):
    run, external_inputs = configuration.validate_run(run, "reload_helper")
    run.mkdir(parents=True, exist_ok=False)
    event, values, guis, labels = fixture(preset, rich=rich, diagnostic=diagnostic)
    probe = run / "probe"
    write(probe / "events/tniqa_events.txt", event)
    write(probe / "common/script_values/tniqa_values.txt", values)
    write(probe / "common/scripted_guis/tniqa_controls.txt", guis)
    write(probe / "common/on_action/tniqa_start.txt", "on_game_start_after_lobby = { on_actions = { tniqa_start } }\ntniqa_start = { effect = { every_player = { if = { limit = { NOT = { exists = var:tniqa_initialized } } set_variable = { name = tniqa_initialized value = yes } trigger_event = tniqa.1 } } } }\n")
    spec = importlib.util.spec_from_file_location("reviewed_reload_helper", RELOAD_HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reload_dir = run / "reload-source"
    module.build(reload_dir, "GetPlayer.MakeScope.GetVariable('tca_reload_request').IsSet")
    for source in reload_dir.rglob("*"):
        if source.is_file() and source.suffix in (".txt", ".gui"):
            relative = source.relative_to(reload_dir)
            relative = Path(str(relative).replace("tca_", "tniqa_"))
            text = source.read_text(encoding="utf-8-sig").replace("tca_", "tniqa_").replace("TCA_TEST|", "TNI_TEST|").replace("TCA_RELOAD|", "TNI_RELOAD|")
            write(probe / relative, text)
    write(probe / "common/scripted_guis/tniqa_reload_probe.txt", reload_controls(close_before_load=diagnostic))
    call = lambda name: f"GetScriptedGui('{name}').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)"
    phase = lambda n: f"EqualTo_CFixedPoint(GetPlayer.MakeScope.GetVariable('tniqa_phase').GetValue,'(CFixedPoint){n}')"
    auto = module.state("tniqa_autobalance", module.both("GetPlayer.IsValid", phase(1)),
                        [call("tniqa_before_autobalance"), call("tnt_autobalance"), call("tniqa_after_autobalance")], .3)
    disk = "Or(GetVariableSystem.HasValue('tniqa_reload_stage','loading'),Not(GetVariableSystem.Exists('tniqa_reload_stage')))"
    observe = module.state("tniqa_observe_reload", module.both("GetPlayer.IsValid", phase(2),
                           "GetPlayer.MakeScope.GetVariable('tniqa_reload_saved_token').IsSet", disk),
                           [call("tniqa_reload_assert_loaded")], .5)
    done = module.state("tniqa_after_reload", module.both("GetPlayer.IsValid", phase(2),
                        "GetPlayer.MakeScope.GetVariable('tniqa_reload_proven').IsSet"),
                        [call("tniqa_check_reloaded_quote")], .3)
    write(probe / "gui/tniqa_controls.gui", "window = { name = tniqa_controls size = { 1 1 } alwaystransparent = yes\n" + auto + observe + done + "\n}\n")
    write(probe / "gui/scripted_widgets/tniqa_controls.txt", "gui/tniqa_controls.gui = tniqa_controls\n")
    plan = {"status": "PLAN_ONLY_RUNTIME_NOT_FROZEN", "preset": preset, "runtime_source": str(SOURCE),
            "external_inputs": external_inputs, "configuration_sha256": sha(Path(configuration.__file__)),
            "workload": "rich_36_objects" if rich else "ordinary_currency",
            "reload_diagnostics": diagnostic,
            "ai_enabled": True, "expected_labels": labels, "expected_count": len(labels),
            "reload_helper": str(RELOAD_HELPER), "reload_helper_sha256": sha(RELOAD_HELPER),
            "probe_sha256": inventory(probe),
            "coverage_limits": ["Native NOT_RUN until isolated execution.", "No visual or multiplayer acceptance.",
             "Marriage tests cover the existing cached-price adapter, not an MCA selection/settlement.",
             "Contract rows log APPLICABLE_NONZERO or INAPPLICABLE_BASE_ZERO; only nonzero rows prove applicable-right adjustment.",
             "Missing-rule existing-save load remains NOT_VERIFIED; preset Off is not proof of absent-rule migration.",
             "AI checks execute the production synchronous settlement helper with actual AI characters; autonomous scheduler/candidate selection remains NOT_VERIFIED.",
             "No cross-resource arbitrary split/reversal guarantee is inferred from bounded factor assertions."]}
    dump(run / "plan.json", plan)
    print(json.dumps({"run": str(run), "status": plan["status"], "expected_assertions": len(labels)}))


def freeze(run):
    run, external_inputs = configuration.validate_run(run, "reload_helper", "game_root", "settings_source")
    plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
    if (plan.get("external_inputs", {}).get("reload_helper") != external_inputs["reload_helper"]
            or plan.get("configuration_sha256") != sha(Path(configuration.__file__))):
        raise ValueError("External helper/configuration changed since plan; prepare a fresh run")
    if plan["status"] != "PLAN_ONLY_RUNTIME_NOT_FROZEN" or (run / "runtime").exists():
        raise ValueError("Run is already frozen; prepare a new run instead")
    if inventory(run / "probe") != plan["probe_sha256"]:
        raise ValueError("Probe changed since plan; re-prepare under a new run name")
    before = inventory(SOURCE)
    shutil.copytree(SOURCE, run / "runtime")
    if inventory(run / "runtime") != before or inventory(SOURCE) != before:
        raise ValueError("Runtime source drift during snapshot")
    shutil.copytree(run / "runtime", run / "merged")
    rule = run / "merged/common/game_rules/tnt_80_game_rules.txt"
    data = rule.read_bytes()
    token = b"default = tnt_interests_standard"
    if data.count(token) != 1:
        raise ValueError("Expected one current interest-rule default")
    rule.write_bytes(data.replace(token, f"default = tnt_interests_{plan['preset']}".encode()))
    overrides = {"common/game_rules/tnt_80_game_rules.txt": {
        "purpose": "Test-only preset default; all settings and policy bodies unchanged.",
        "runtime_sha256": before["common/game_rules/tnt_80_game_rules.txt"], "test_sha256": sha(rule)}}
    for source in (run / "probe").rglob("*"):
        if source.is_file():
            relative = source.relative_to(run / "probe")
            target = run / "merged" / relative
            if target.exists():
                overrides[relative.as_posix()] = {"base_sha256": sha(target), "test_sha256": sha(source)}
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    profile = run / "userdata"
    (profile / "mod").mkdir(parents=True)
    write(profile / "mod/tniqa_merged.mod", f'name="[PROBE] Parley interests {plan["preset"]}"\nsupported_version="1.20.*"\npath="{(run / "merged").as_posix()}"\n')
    dump(profile / "dlc_load.json", {"enabled_mods": ["mod/tniqa_merged.mod"], "disabled_dlcs": []})
    settings_bytes = SETTINGS.read_bytes()
    settings = settings_bytes.decode("utf-8-sig").replace('value="fullscreen"', 'value="windowed"')
    settings, count = re.subn(r'("language"=\{.*?value=)"[^"]+"', r'\1"l_english"', settings, flags=re.S)
    if count != 1:
        raise ValueError("Expected one language setting")
    settings = re.sub(r'("autosave"=\{.*?value=)"[^"]+"', r'\1"NEVER"', settings, flags=re.S)
    (profile / "pdx_settings.txt").write_text(settings, encoding="utf-8")
    executable = GAME / "binaries/ck3.exe"
    game = json.loads((GAME / "launcher/launcher-settings.json").read_text(encoding="utf-8"))
    write(run / "start_probe.ps1", f"""$ErrorActionPreference = 'Stop'
if (Get-Process -Name ck3 -ErrorAction SilentlyContinue) {{ throw 'Existing CK3 process; no launch.' }}
$interestProfile = '{profile.as_posix()}'
if (Test-Path -LiteralPath "$interestProfile/logs/debug.log") {{ throw 'Profile already ran; preserve evidence.' }}
$interestArguments = @(('-userdir="' + $interestProfile + '"'), '-debug_mode', '-skip_checksum', '-skip', '-play=e_arabia', '-bookmark=bm_867_persia', '-random_seed=4391178', '-window_title="Parley interest isolated probe"')
$interestProcess = Start-Process -FilePath '{executable.as_posix()}' -WorkingDirectory '{executable.parent.as_posix()}' -ArgumentList $interestArguments -WindowStyle Hidden -PassThru
@{{ pid=$interestProcess.Id; started_utc=$interestProcess.StartTime.ToUniversalTime().ToString('o'); launched_utc=[DateTime]::UtcNow.ToString('o'); executable='{executable.as_posix()}'; arguments=$interestArguments; profile=$interestProfile; status='RUNNING' }} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath '{(run / "process-result.json").as_posix()}' -Encoding utf8
""")
    write(run / "stop_probe.ps1", f"""$ErrorActionPreference = 'Stop'
$interestRecord = Get-Content -LiteralPath '{(run / "process-result.json").as_posix()}' -Raw | ConvertFrom-Json
$interestProcess = Get-Process -Id $interestRecord.pid -ErrorAction Stop
$interestInfo = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $interestRecord.pid)
if ([IO.Path]::GetFullPath($interestInfo.ExecutablePath) -ne [IO.Path]::GetFullPath($interestRecord.executable)) {{ throw 'Executable mismatch' }}
$interestRecordedStart = if ($interestRecord.started_utc -is [DateTime]) {{ $interestRecord.started_utc.ToUniversalTime() }} else {{ [DateTime]::Parse($interestRecord.started_utc, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime() }}
if ($interestProcess.StartTime.ToUniversalTime().Ticks -ne $interestRecordedStart.Ticks) {{ throw 'PID/start-time mismatch' }}
$interestMatch = [regex]::Match($interestInfo.CommandLine, '-userdir="([^"]+)"')
if (-not $interestMatch.Success -or [IO.Path]::GetFullPath($interestMatch.Groups[1].Value) -ne [IO.Path]::GetFullPath($interestRecord.profile)) {{ throw 'Exact isolated profile mismatch' }}
Stop-Process -Id $interestRecord.pid
$interestProcess.WaitForExit()
$interestRecord.status = 'EXIT_CONFIRMED'
$interestRecord | Add-Member -NotePropertyName stopped_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
$interestRecord | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath '{(run / "process-result.json").as_posix()}' -Encoding utf8
""")
    plan.update(status="PREPARED_NOT_RUN", runtime_sha256=before, merged_sha256=inventory(run / "merged"),
                external_inputs=external_inputs,
                overrides=overrides, game_version=game.get("rawVersion"), executable=str(executable),
                executable_sha256=sha(executable), settings_source_sha256=hashlib.sha256(settings_bytes).hexdigest(),
                prepared_settings_sha256=sha(profile / "pdx_settings.txt"), profile=str(profile))
    dump(run / "frozen-manifest.json", plan)
    print(json.dumps({"run": str(run), "status": plan["status"], "runtime_files": len(before)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--preset", choices=PRESETS, default="standard")
    parser.add_argument("--stage", choices=("plan", "freeze"), default="plan")
    parser.add_argument("--rich", action="store_true", help="Plan a 36-object draft for native quote/Auto-balance timing.")
    parser.add_argument("--diagnostic", action="store_true", help="Persist and natively dump per-term/derived inputs before and after Load; close only unsaved table before Load.")
    add_path_arguments(parser)
    args = parser.parse_args()
    configure_paths(args)
    if not re.fullmatch("[a-z0-9_-]+", args.run_name):
        parser.error("Use a lower-case run identifier")
    destination = EVIDENCE / args.run_name
    if args.stage == "plan":
        prepare_plan(destination, args.preset, rich=args.rich, diagnostic=args.diagnostic)
    else:
        freeze(destination)
