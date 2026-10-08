"""Project only the explicitly checked later exclusivity delta from old AST gates.

This is not the Off implementation: exclusivity applies even with interests Off.
Functional behavior is covered by test_currency_exclusivity. These strict shape
checks let older whole-file baseline tests keep checking every unrelated node.
"""
from copy import deepcopy

from test_autobalance import one, parse


def without_currency_exclusivity(nodes):
    result = deepcopy(nodes)
    for name, _, body in result:
        if name in ("tnt_cur_step_p_effect", "tnt_cur_step_r_effect"):
            side = name.removeprefix("tnt_cur_step_")[0]
            value = one(one(body, "set_variable"), "value")
            expected = parse("value = $DELTA$ if = { limit = { NOT = { "
                             f"tnt_currency_{side}_unlocked_trigger = {{ CURRENCY = $FIELD$ }}"
                             " } } max = 0 }")
            assert one(value, "add") == expected, (name, "signed lock shape")
            index = next(i for i, node in enumerate(value) if node[0] == "add")
            value[index] = ("add", "=", "$DELTA$")
        elif name in {f"tnt_cur_{kind}_{side}_effect" for kind in ("set", "frac") for side in ("p", "r")}:
            side = name.removesuffix("_effect")[-1]
            assert [key for key, _, _ in body] == ["if"], (name, "sole guarded writer")
            branch = one(body, "if")
            assert one(branch, "limit") == parse(f"tnt_currency_{side}_unlocked_trigger = {{ CURRENCY = $FIELD$ }}"), name
            body[:] = [node for node in branch if node[0] != "limit"]
        elif name == "tnt_ab_pay_currency_effect":
            limit = one(one(body, "if"), "limit")
            assert limit == parse("tnt_ab_surplus_value > 0 NOT = { AND = { exists = var:$P$ var:$P$ > 0 } }"), name
            limit[:] = parse("tnt_ab_surplus_value > 0")
        elif name == "tnt_ab_solve_effect":
            seen = []

            def restore_calls(block):
                for key, _, value in block:
                    if key == "tnt_ab_pay_currency_effect":
                        variable = one(value, "VAR")
                        assert variable in {f"tnt_{currency}_r" for currency in ("gold", "prestige", "piety", "influence")}, variable
                        assert one(value, "P") == variable[:-1] + "p", (name, variable, "opposite")
                        seen.append(variable)
                        value[:] = [node for node in value if node[0] != "P"]
                    elif isinstance(value, list):
                        restore_calls(value)

            restore_calls(body)
            assert sorted(seen) == ["tnt_gold_r", "tnt_influence_r", "tnt_piety_r", "tnt_prestige_r"], seen
        elif name == "tnt_ai_pricebalance_effect":
            assert body[:2] == parse("tnt_ab_sanitize_currencies_effect = yes tnt_ab_net_effect = yes"), name
            del body[1]
        elif name == "tnt_deal_preflight_trigger":
            players = [value for key, _, value in one(body, "trigger_if") if key == "$PLAYER$"]
            guard = ("tnt_currencies_exclusive_trigger", "=", "yes")
            matches = [player for player in players if guard in player]
            assert len(matches) == 1, (name, "one unconditional package guard")
            player = matches[0]
            index = player.index(guard)
            assert player[index - 1:index + 2] == parse("tnt_no_double_vassal_trigger = yes "
                                                     "tnt_currencies_exclusive_trigger = yes tnt_people_pair_trigger = yes"), name
            del player[index]
    return result
