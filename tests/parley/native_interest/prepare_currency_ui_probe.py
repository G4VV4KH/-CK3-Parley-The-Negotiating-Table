"""Plan real-window interest-preview and one-direction currency UI regression.

No launch or production edit. Normal amount changes use shipped scripted-GUI
callbacks. A separate explicit legacy phase seeds opposing10/20 drafts to test
preflight/master rejection and real Auto-balance repair. Native stocks are never
seeded. Observations include amounts, validity and a live-input preview oracle.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

import prepare_window_open_probe as ordinary


CURRENCIES = ("gold", "prestige", "piety")
WRITERS = ("add", "add_big", "add_huge", "std", "half", "max")
CASE_LABELS = ("host_show", "empty_preview", "both_unlocked", "fine_selected",
               "selected_display", "opposite_disabled",
               *("blocked_" + writer for writer in WRITERS),
               "zero_amounts", "zero_triggers", "zero_preview", "zero_restores",
               "max_selected", "preset_display", "preset_opposite_noop",
               "clear_amounts", "clear_triggers", "clear_preview", "clear_restores", "stocks_pressure_unchanged")
LEGACY_LABELS = ("conflict_preflight_reject", "send_disabled", "master_wallets_unchanged",
                 "net_exact", "reseed_conflict", "autobalance_exclusive", "autobalance_affordable",
                 "autobalance_honest", "autobalance_no_settlement",
                 "clear_amounts", "clear_triggers", "clear_preview", "clear_restores")
ADVANCED = ("title", "subject", "courtier", "artifact", "vassal", "indep",
            "hostage", "hook", "marriage")
CONTRACTS = ("tax", "levy", "fort", "coin", "relig", "council", "revoke", "war", "succ")


def tooltip_instance(source, currency, side):
    target = f"tnt_interest_{currency}_{side}_percent_value"
    tokens = re.compile(r'"(?:\\.|[^"\\])*"|#[^\n]*|[{}]')
    for match in re.finditer(r"\btnt_interest_tooltip\s*=\s*\{", source):
        depth = 0
        for token in tokens.finditer(source, source.index("{", match.start())):
            if token.group() == "{":
                depth += 1
            elif token.group() == "}":
                depth -= 1
                if not depth:
                    instance = source[match.start():token.end()]
                    if (target in instance and f"tnt_interest_{currency}_{side}_preview_percent_value" in instance
                            and f"tnt_interest_{currency}_capacity_value" in instance):
                        return instance
                    break
        else:
            raise ValueError("Unbalanced production tooltip instance")
    raise ValueError("Current production display tooltip missing: " + target)


def oracle_values():
    """Independent marginal-band formula, no reads of production percentages."""
    blocks = []
    for currency in CURRENCIES:
        stock, capacity = (f"tnt_interest_{currency}_{kind}_value" for kind in ("stock", "capacity"))
        prefix = f"tnuq_{currency}"
        blocks += [f"{prefix}_critical = {{ value = {capacity} divide = 4 }}",
                   f"{prefix}_saturated = {{ value = {capacity} multiply = 2 }}"]
        for side in ("p", "r"):
            native_stock = f"value = {currency}" if side == "p" else f"value = 0 var:tnt_partner = {{ add = {currency} }}"
            blocks.append(f"{prefix}_{side}_max_expected = {{ {native_stock} min = 0 round = yes }}")
            if side == "p":
                branches = (f"if = {{ limit = {{ {stock} >= {prefix}_saturated }} value = 0 }}\n"
                            f"else_if = {{ limit = {{ {stock} >= {capacity} }} divide = {{ value = 1 add = tnt_interest_strength_value }} }}")
            else:
                branches = (f"if = {{ limit = {{ {stock} <= {prefix}_critical }} divide = {{ value = tnt_interest_strength_value multiply = 3 add = 1 }} }}\n"
                            f"else_if = {{ limit = {{ {stock} <= {capacity} }} divide = {{ value = 1 add = tnt_interest_strength_value }} }}")
            blocks.append(f"{prefix}_{side}_oracle = {{ value = 100 if = {{ limit = {{ tnt_interests_enabled_value > 0 exists = var:tnt_partner }} {branches} }} }}")
            blocks.append(f"{prefix}_{side}_badge_oracle = {{ value = {prefix}_{side}_oracle round = yes min = 0 max = 100 }}")
    return "\n".join(blocks) + "\n"


def prepare(run, preset="standard"):
    base = ordinary.base
    production = (base.SOURCE / ordinary.WINDOW).read_text(encoding="utf-8-sig")
    instances = {(currency, side): tooltip_instance(production, currency, side)
                 for currency in CURRENCIES for side in ("p", "r")}
    ordinary.prepare(run, preset)
    probe = run / "probe"
    plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
    labels = plan["expected_labels"]
    initial_labels = ["gui_bool_false_control", "gui_bool_true_control",
                      "preview_fixture_native_preconditions", "empty_quote_has_no_points"]
    initial_labels += [f"empty_{currency}_{side}_oracle" for currency in CURRENCIES for side in ("p", "r")]
    initial_labels += ["empty_advanced_and_contract_previews", "empty_positive_surrender_preview"]
    final_labels = ["global_clear_amounts", "global_clear_triggers", "global_clear_preview",
                    "global_clear_restores", "currency_ui_cycle_no_prior_failure"]
    declared = (labels[:] + initial_labels
                + [f"{currency}_{side}_{label}" for currency in CURRENCIES for side in ("p", "r") for label in CASE_LABELS]
                + [f"legacy_{currency}_{label}" for currency in CURRENCIES for label in LEGACY_LABELS] + final_labels)
    spec = importlib.util.spec_from_file_location("reviewed_currency_ui_timer", base.RELOAD_HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    call = lambda name: f"GetScriptedGui('{name}').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)"
    phase = lambda n: f"EqualTo_CFixedPoint(GetPlayer.MakeScope.GetVariable('tnwqa_phase').GetValue,'(CFixedPoint){n}')"
    flag = lambda name: f"GetPlayer.MakeScope.GetVariable('{name}').IsSet"
    valid = lambda command: f"GetScriptedGui('{command}').IsValid(GuiScope.SetRoot(GetPlayer.MakeScope).End)"
    observed = lambda name, expr: f"GetScriptedGui('{name}').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).AddScope('observed',MakeScopeBool({expr})).End)"
    window_ok = "var:tnt_open = 1 exists = var:tnt_partner var:tnt_partner = { is_alive = yes } is_ai = no"
    pressure_empty = "NOT = { has_variable = tnt_threat_p } NOT = { has_variable = tnt_usehook_p } NOT = { has_variable = tnt_usehook_r }"

    def empty(currency):
        return " ".join(f"OR = {{ NOT = {{ has_variable = tnt_{currency}_{side} }} var:tnt_{currency}_{side} <= 0 }}" for side in ("p", "r"))

    def preview(currency, side):
        prefix = f"tnt_interest_{currency}_{side}"
        return (f"{prefix}_display_percent_value = tnuq_{currency}_{side}_oracle "
                f"{prefix}_badge_percent_value = tnuq_{currency}_{side}_badge_oracle "
                f"{prefix}_display_percent_value >= 0 {prefix}_display_percent_value <= 100")

    def unlocked_triggers(currency):
        return (f"tnt_currency_p_unlocked_trigger = {{ CURRENCY = {currency} }} "
                f"tnt_currency_r_unlocked_trigger = {{ CURRENCY = {currency} }} "
                "tnt_currencies_exclusive_trigger = yes")

    def assertions(label, condition):
        labels.append(label)
        return (f'if = {{ limit = {{ {condition} }} debug_log = "TNGUI_TEST|PASS|{label}" }} '
                f'else = {{ debug_log = "TNGUI_TEST|FAIL|{label}" set_variable = {{ name = tnwqa_failed value = 1 }} }}\n')

    def callback(name, at, label, condition, tail="", before=""):
        return (f"tnuq_{name} = {{ scope = character effect = {{ if = {{ limit = {{ var:tnwqa_phase = {at} NOT = {{ has_variable = tnuq_{name}_done }} }}\n"
                f"set_variable = {{ name = tnuq_{name}_done value = 1 }}\n"
                + before + "\n" + assertions(label, window_ok + " " + condition) + tail + "\n} } }\n")

    controls_path = probe / "common/scripted_guis/tnwqa_controls.txt"
    controls = controls_path.read_text(encoding="utf-8-sig")
    token = 'set_variable = { name = tnwqa_phase value = 2 }\ndebug_log = "TNGUI_TEST|END|production_window"'
    if controls.count(token) != 1:
        raise ValueError("Ordinary window completion anchor changed")
    controls = controls.replace(token, 'set_variable = { name = tnwqa_phase value = 2 }')
    controls += callback("bool_false", 2, "gui_bool_false_control", "scope:observed = no NOT = { scope:observed = yes }")
    controls += callback("bool_true", 2, "gui_bool_true_control", "scope:observed = yes NOT = { scope:observed = no }")
    conditions = " ".join(f"{currency} > 20 var:tnt_partner = {{ {currency} > 20 }}" for currency in CURRENCIES)
    controls += "tnuq_initial = { scope = character effect = { if = { limit = { var:tnwqa_phase = 2 }\n"
    controls += assertions("preview_fixture_native_preconditions", window_ok + " scope:observed = yes " + conditions + " " + pressure_empty)
    controls += assertions("empty_quote_has_no_points", "tnt_interest_quote_gain_value = 0 tnt_interest_quote_loss_value = 0 tnt_interest_penalty_value = 0")
    controls += "var:tnt_partner = { save_temporary_scope_as = tnuq_partner_stock_source }\n"
    for currency in CURRENCIES:
        controls += f"set_variable = {{ name = tnuq_{currency}_actor_stock value = {currency} }}\nset_variable = {{ name = tnuq_{currency}_partner_stock value = scope:tnuq_partner_stock_source.{currency} }}\n"
        for side in ("p", "r"):
            controls += assertions(f"empty_{currency}_{side}_oracle", empty(currency) + " " + preview(currency, side))
    advanced_conditions = []
    for term in ADVANCED:
        for side in ("p", "r"):
            prefix = f"tnt_interest_{term}_{side}"
            advanced_conditions.append(f"{prefix}_selected_value = 0 {prefix}_display_percent_value = {prefix}_preview_percent_value {prefix}_display_percent_value > 0 {prefix}_display_percent_value <= 100")
    for term in CONTRACTS:
        prefix = f"tnt_interest_ob_{term}"
        advanced_conditions.append(f"{prefix}_selected_value = 0 {prefix}_display_percent_value = {prefix}_preview_percent_value {prefix}_display_percent_value > 0 {prefix}_display_percent_value <= 100")
    controls += assertions("empty_advanced_and_contract_previews", " ".join(advanced_conditions))
    controls += assertions("empty_positive_surrender_preview", "tnt_interest_gold_r_display_percent_value > 0")
    controls += "set_variable = { name = tnwqa_phase value = 3 }\n} } }\n"
    driver = 'window = { name = tnuq_driver size = { 1 1 } alwaystransparent = yes\n'
    driver += helper.state("tnuq_begin", helper.both("GetPlayer.IsValid", phase(2)),
                           [call("tnt_clear_all"), observed("tnuq_bool_false", "Not(IsGamePaused)"),
                            observed("tnuq_bool_true", "IsGamePaused"), observed("tnuq_initial", "IsGamePaused")], 1) + "\n}\n"
    base.write(probe / "gui/tnuq_driver.gui", driver)
    base.write(probe / "gui/scripted_widgets/tnuq_driver.txt", "gui/tnuq_driver.gui = tnuq_driver\n")
    stock_unchanged = " ".join(f"{currency} = var:tnuq_{currency}_actor_stock var:tnt_partner = {{ {currency} = root.var:tnuq_{currency}_partner_stock }}" for currency in CURRENCIES)
    for index, ((currency, side), instance) in enumerate(instances.items()):
        case, opposite = f"{currency}_{side}", "r" if side == "p" else "p"
        at = 3 + index * 5
        prefix, other = f"tnt_{case}", f"tnt_{currency}_{opposite}"
        amount = f"var:{prefix}"
        other_empty = f"OR = {{ NOT = {{ has_variable = {other} }} var:{other} <= 0 }}"
        positive_ten = f"{amount} = 10 " + other_empty
        max_selected = f"{amount} = tnuq_{case}_max_expected {amount} >= 10 " + other_empty
        both_unlocked = helper.both(*(valid(f"tnt_{currency}_{direction}_{writer}") for direction in ("p", "r") for writer in WRITERS))
        opposite_disabled = helper.both(*(f"Not({valid(other + '_' + writer)})" for writer in WRITERS))
        selected_display = f"tnt_interest_{case}_display_percent_value = tnt_interest_{case}_percent_value"
        previews = preview(currency, "p") + " " + preview(currency, "r")
        restored = empty(currency) + " " + unlocked_triggers(currency) + " " + previews + " scope:observed = yes"
        labels_for = lambda item: f"{case}_{item}"
        controls += callback(case + "_host", at, labels_for("host_show"), empty(currency), f"set_variable = {{ name = tnuq_{case}_host_seen value = 1 }}")
        controls += callback(case + "_empty", at, labels_for("empty_preview"), f"has_variable = tnuq_{case}_host_seen " + empty(currency) + " " + preview(currency, side))
        controls += callback(case + "_unlocked", at, labels_for("both_unlocked"), "scope:observed = yes")
        controls += callback(case + "_added", at, labels_for("fine_selected"), positive_ten, f"set_variable = {{ name = tnwqa_phase value = {at + 1} }}")
        controls += callback(case + "_selected", at + 1, labels_for("selected_display"), positive_ten + " " + selected_display)
        controls += callback(case + "_disabled", at + 1, labels_for("opposite_disabled"), "scope:observed = yes")
        for writer in WRITERS:
            controls += callback(case + "_blocked_" + writer, at + 1, labels_for("blocked_" + writer), positive_ten)
        for suffix, condition in (("amounts", empty(currency)), ("triggers", unlocked_triggers(currency)), ("preview", previews)):
            controls += callback(case + "_zero_" + suffix, at + 1, labels_for("zero_" + suffix), condition,
                                 f"set_variable = {{ name = tnwqa_phase value = {at + 2} }}" if suffix == "preview" else "")
        controls += callback(case + "_zero", at + 2, labels_for("zero_restores"), restored)
        controls += callback(case + "_max", at + 2, labels_for("max_selected"), max_selected, f"set_variable = {{ name = tnwqa_phase value = {at + 3} }}")
        controls += callback(case + "_preset", at + 3, labels_for("preset_display"), max_selected + " " + selected_display)
        controls += callback(case + "_preset_noop", at + 3, labels_for("preset_opposite_noop"), max_selected)
        for suffix, condition in (("amounts", empty(currency)), ("triggers", unlocked_triggers(currency)), ("preview", previews)):
            controls += callback(case + "_clear_" + suffix, at + 3, labels_for("clear_" + suffix), condition,
                                 f"set_variable = {{ name = tnwqa_phase value = {at + 4} }}" if suffix == "preview" else "")
        controls += callback(case + "_clear", at + 4, labels_for("clear_restores"), restored)
        controls += callback(case + "_stable", at + 4, labels_for("stocks_pressure_unchanged"), stock_unchanged + " " + pressure_empty,
                             f"set_variable = {{ name = tnwqa_phase value = {at + 5} }}")
        visible = helper.both("GetPlayer.IsValid", f"Or({phase(at)},Or({phase(at + 1)},Or({phase(at + 2)},Or({phase(at + 3)},{phase(at + 4)}))))")
        host = (f'window = {{ name = tnuq_{case}_host layer = top size = {{ 500 700 }} parentanchor = center alwaystransparent = no visible = "[{visible}]"\n'
                f'state = {{ name = _show on_start = "[{call("tnuq_" + case + "_host")}]" }}\n' + instance + "\n")
        stages = [
            [call("tnuq_" + case + "_empty"), observed("tnuq_" + case + "_unlocked", both_unlocked), call(prefix + "_add"), call("tnuq_" + case + "_added")],
            [call("tnuq_" + case + "_selected"), observed("tnuq_" + case + "_disabled", opposite_disabled)]
            + [action for writer in WRITERS for action in (call(other + "_" + writer), call("tnuq_" + case + "_blocked_" + writer))]
            + [call(prefix + "_sub"), *(call("tnuq_" + case + "_zero_" + part) for part in ("amounts", "triggers", "preview"))],
            [observed("tnuq_" + case + "_zero", both_unlocked), call(prefix + "_max"), call("tnuq_" + case + "_max")],
            [call("tnuq_" + case + "_preset"), call(other + "_max"), call("tnuq_" + case + "_preset_noop"), call(prefix + "_none"),
             *(call("tnuq_" + case + "_clear_" + part) for part in ("amounts", "triggers", "preview"))],
            [observed("tnuq_" + case + "_clear", both_unlocked), call("tnuq_" + case + "_stable")],
        ]
        for offset, actions in enumerate(stages):
            host += helper.state("tnuq_" + case + "_stage_" + str(offset),
                                 helper.both("GetPlayer.IsValid", phase(at + offset), flag("tnuq_" + case + "_host_seen")), actions, 3) + "\n"
        host += "}\n"
        base.write(probe / f"gui/tnuq_{case}_host.gui", host)
        base.write(probe / f"gui/scripted_widgets/tnuq_{case}_host.txt", f"gui/tnuq_{case}_host.gui = tnuq_{case}_host\n")
    legacy_start = 3 + len(instances) * 5
    legacy_workers = ""
    partner_scope = "var:tnt_partner = { save_scope_as = tnt_deal_partner }\n"
    preflight = "tnt_deal_preflight_trigger = { PLAYER = root PARTNER = scope:tnt_deal_partner }"
    # tnt53 returns signed need-minus-stock, not a zero-clamped shortfall.
    # A nonpositive result means affordable; exact zero wrongly rejects surplus.
    affordability = " ".join(f"{prefix}{currency}_shortfall_value <= 0"
                             for currency in (*CURRENCIES, "influence") for prefix in ("tnt_", "tnt_partner_"))
    honest = ("OR = { AND = { var:tnt_ab_state = 3 tnt_ai_accept_value <= 0 } "
              "AND = { var:tnt_ab_state = 4 tnt_ai_accept_value > 1 } "
              "AND = { OR = { var:tnt_ab_state = 1 var:tnt_ab_state = 2 } tnt_ai_accept_value > 0 tnt_ai_accept_value <= 1 } }")
    for index, currency in enumerate(CURRENCIES):
        at, name = legacy_start + index * 4, "legacy_" + currency
        seed = (f"# TEST ONLY malformed legacy draft; two affordable opposing amounts.\n"
                f"set_variable = {{ name = tnt_{currency}_p value = 10 }}\n"
                f"set_variable = {{ name = tnt_{currency}_r value = 20 }}\n")
        conflict = f"var:tnt_{currency}_p = 10 var:tnt_{currency}_r = 20 NOT = {{ tnt_currencies_exclusive_trigger = yes }}"
        controls += callback(name + "_seed", at, name + "_conflict_preflight_reject",
                             conflict + " exists = scope:tnt_deal_partner NOT = { " + preflight + " }",
                             f"set_variable = {{ name = tnwqa_phase value = {at + 1} }}", before=seed + partner_scope)
        controls += callback(name + "_send", at + 1, name + "_send_disabled", "scope:observed = yes " + conflict)
        controls += callback(name + "_apply", at + 1, name + "_master_wallets_unchanged",
                             "exists = scope:tnt_deal_partner " + conflict + " " + stock_unchanged + " " + pressure_empty,
                             before=partner_scope + "tnt_apply_deal_effect = yes\n")
        controls += callback(name + "_net", at + 1, name + "_net_exact",
                             f"var:tnt_{currency}_p = 0 var:tnt_{currency}_r = 10 tnt_currencies_exclusive_trigger = yes " + preflight,
                             before=partner_scope + "tnt_ab_net_effect = yes\n")
        controls += callback(name + "_reseed", at + 1, name + "_reseed_conflict", conflict, before=seed)
        controls += callback(name + "_balanced", at + 1, name + "_autobalance_exclusive",
                             "exists = var:tnt_ab_state tnt_currencies_exclusive_trigger = yes",
                             f"set_variable = {{ name = tnwqa_phase value = {at + 2} }}")
        controls += callback(name + "_affordable", at + 2, name + "_autobalance_affordable", affordability)
        controls += callback(name + "_honest", at + 2, name + "_autobalance_honest", honest)
        controls += callback(name + "_stable", at + 2, name + "_autobalance_no_settlement", stock_unchanged + " " + pressure_empty)
        all_empty = " ".join(empty(item) for item in CURRENCIES)
        previews = preview(currency, "p") + " " + preview(currency, "r") + " tnt_interest_quote_gain_value = 0 tnt_interest_quote_loss_value = 0"
        for suffix, condition in (("amounts", all_empty), ("triggers", unlocked_triggers(currency)), ("preview", previews)):
            controls += callback(name + "_clear_" + suffix, at + 2, name + "_clear_" + suffix, condition,
                                 f"set_variable = {{ name = tnwqa_phase value = {at + 3} }}" if suffix == "preview" else "")
        controls += callback(name + "_clear", at + 3, name + "_clear_restores",
                             all_empty + " " + unlocked_triggers(currency) + " " + previews + " scope:observed = yes",
                             f"set_variable = {{ name = tnwqa_phase value = {at + 4} }}")
        unlocked = helper.both(*(valid(f"tnt_{currency}_{side}_add") for side in ("p", "r")))
        actions = [
            [call("tnt_clear_all"), call("tnuq_" + name + "_seed")],
            [observed("tnuq_" + name + "_send", f"Not({valid('tnt_send_offer')})"),
             call("tnuq_" + name + "_apply"), call("tnuq_" + name + "_net"), call("tnuq_" + name + "_reseed"),
             call("tnt_autobalance"), call("tnuq_" + name + "_balanced")],
            [call("tnuq_" + name + "_affordable"), call("tnuq_" + name + "_honest"), call("tnuq_" + name + "_stable"),
             call("tnt_clear_all"), *(call("tnuq_" + name + "_clear_" + part) for part in ("amounts", "triggers", "preview"))],
            [observed("tnuq_" + name + "_clear", unlocked)],
        ]
        for offset, stage_actions in enumerate(actions):
            legacy_workers += helper.state("tnuq_" + name + "_stage_" + str(offset),
                                           helper.both("GetPlayer.IsValid", phase(at + offset)), stage_actions, 1) + "\n"
    finish_phase = legacy_start + len(CURRENCIES) * 4
    final_valid = helper.both(*(valid(f"tnt_gold_{side}_add") for side in ("p", "r")))
    for suffix, condition in (("amounts", empty("gold")), ("triggers", unlocked_triggers("gold")),
                              ("preview", preview("gold", "p") + " " + preview("gold", "r"))):
        controls += callback("finish_clear_" + suffix, finish_phase, "global_clear_" + suffix, condition,
                             f"set_variable = {{ name = tnwqa_phase value = {finish_phase + 1} }}" if suffix == "preview" else "")
    controls += callback("finish_clear", finish_phase + 1, "global_clear_restores", empty("gold") + " " + unlocked_triggers("gold") + " " + preview("gold", "p") + " " + preview("gold", "r") + " scope:observed = yes")
    controls += callback("finish", finish_phase + 1, "currency_ui_cycle_no_prior_failure", "NOT = { has_variable = tnwqa_failed }",
                         f'set_variable = {{ name = tnwqa_phase value = {finish_phase + 2} }}\ndebug_log = "TNGUI_TEST|END|production_window"')
    driver = (probe / "gui/tnuq_driver.gui").read_text(encoding="utf-8-sig")
    driver = driver[:-2] + legacy_workers + helper.state("tnuq_finish_mutate", helper.both("GetPlayer.IsValid", phase(finish_phase)),
        [call("tnt_gold_p_add"), call("tnt_clear_all"), *(call("tnuq_finish_clear_" + part) for part in ("amounts", "triggers", "preview"))], 1) + "\n"
    driver += helper.state("tnuq_finish", helper.both("GetPlayer.IsValid", phase(finish_phase + 1)),
                           [observed("tnuq_finish_clear", final_valid), call("tnuq_finish")], 1) + "\n}\n"
    base.write(probe / "gui/tnuq_driver.gui", driver)
    base.write(controls_path, controls)
    base.write(probe / "common/script_values/tnuq_oracle.txt", oracle_values())
    if labels != declared or len(set(labels)) != len(labels):
        raise ValueError("Declared assertion contract differs from generated observations")
    plan.update(currency_ui_preview_lock_cycle=True, forced_tooltip_materialization=True,
                expected_labels=labels, expected_count=len(labels), probe_sha256=base.inventory(probe),
                preparer=str(Path(__file__)), preparer_sha256=base.sha(Path(__file__)),
                tooltip_materialization_contract={"currencies": CURRENCIES, "directions": ["p", "r"],
                    "instance_sha256": {currency + "_" + side: hashlib.sha256(value.encode()).hexdigest() for (currency, side), value in instances.items()},
                    "instance": "Six verbatim current production actual/preview-percent/capacity tooltip instances",
                    "stock_or_formula_writes": False,
                    "test_only_legacy_amount_writes": "After normal UI cycles only: each currency p10/r20 seeded twice, before guarded master/net helper and before production Auto-balance.",
                    "clear_preview_oracle": "Independent marginal bands from live stock/capacity/strength; legitimate saturated receives may equal0.",
                    "restore_observation": "Amounts, pure scripted triggers and preview oracle asserted immediately; original combined checks plus GUI IsValid asserted in a separate subsequent timed phase (3s direction cycles,1s legacy/final).",
                    "dynamic_bool_contract": "Single AddScope('observed',MakeScopeBool(...)) per call; independent true and false controls assert exact yes/no, never mere existence. No script-side dummy assignment.",
                    "actions": "Each direction: +10, all6 blocked opposite writers, -10, maximum preset, blocked opposite max, per-currency clear; final production Clear all.",
                    "not_proven": "Physical hover, popup position, pixels/color, row clipping or arbitrary player-save identity."})
    plan["coverage_limits"] += ["Native IsGamePaused and both participants having >20 gold/prestige/piety are asserted fixture preconditions; no native resources are seeded. Only the explicitly malformed legacy phase writes selection variables.",
                                "Advanced/contract empty routing is checked against preview APIs and bounds, not a second independent contextual-motive implementation.",
                                "Influence exclusivity is deliberately unchanged and not included in these three-currency lock cycles.",
                                "Malformed legacy drafts test pure preflight rejection and guarded master no-op. Under enabled interests the economic guard may also reject; the Off run isolates the new preflight barrier from that pricing gate.",
                                "Auto-balance is invoked through its actual GUI. Exact10-unit normalization is separately checked through the production net helper; full balancing may choose different legal amounts and currencies.",
                                "Threat and called-hook flags stay absent throughout; no pressure action or pressure-price rewrite is exercised."]
    base.dump(run / "plan.json", plan)
    print(json.dumps({"run": str(run), "status": plan["status"], "expected_assertions": len(labels)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--preset", choices=ordinary.base.PRESETS, default="standard")
    ordinary.base.add_path_arguments(parser)
    args = parser.parse_args()
    ordinary.base.configure_paths(args)
    if not re.fullmatch("[a-z0-9_-]+", args.run_name):
        parser.error("Use a fresh lower-case isolated run name")
    prepare(ordinary.base.EVIDENCE / args.run_name, args.preset)
