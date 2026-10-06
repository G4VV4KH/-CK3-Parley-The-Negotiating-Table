"""Execute the shipped people-valuation AST with explicit character fixtures.

Extends the shared strict valuation interpreter, not a second pricing model.
Native hostage_value is a fixture input; CK3 itself must verify its evaluation.
Trait/kinship/claim ownership facts are fixtures. Unknown executed syntax fails.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import subprocess
import unittest

import test_scaled_valuation as shared
from test_autobalance import one, parse
from test_scaled_valuation import D, Scope, TIERS, ValuationWorld, realm


class PeopleWorld(ValuationWorld):
    RELATIONS = {"is_close_or_extended_family_of", "is_child_of", "is_heir_of",
                 "has_relation_friend", "has_relation_lover"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.native_hostage_reads = 0

    def operand(self, atom, current):
        if atom == "hostage_value":
            self.native_hostage_reads += 1
        return super().operand(atom, current)

    def condition(self, nodes, current):
        translated = []
        for key, op, body in nodes:
            if key == "has_trait":
                result = body in current.stats.get("traits", set())
            elif key in self.RELATIONS:
                result = self.scope(body, current) in current.lists.get(key, [])
            elif key == "save_temporary_scope_as":
                self.scopes[body] = current
                result = True
            elif key == "is_courtier_of":
                result = current.links.get("courtier_of") is self.scope(body, current)
            elif key == "is_target_in_variable_list":
                target = self.scope(one(body, "target"), current)
                result = target in current.lists.get(one(body, "name"), [])
            elif key in ("any_traveling_family_member", "any_in_list"):
                if key == "any_traveling_family_member":
                    targets = current.lists.get("traveling_family", [current])
                    inner = body
                else:
                    targets = current.lists.get(one(body, "variable"), [])
                    inner = [row for row in body if row[0] != "variable"]
                result = any(self.condition(inner, target) for target in targets)
            elif key == "courtier_or_guest_claim_trigger":
                receiver = self.scope(one(body, "RULER"), current)
                holder = current.links.get("holder")
                result = holder is not None
                seen = set()
                while holder is not None:
                    if holder in seen:
                        raise shared.Unsupported("Cyclic liege fixture")
                    seen.add(holder)
                    if holder is receiver:
                        result = False
                    holder = holder.links.get("liege")
            else:
                translated.append((key, op, body))
                continue
            translated.append(("always", "=", "yes" if result else "no"))
        return super().condition(translated, current)

    def numeric(self, nodes, current, initial=D(0)):
        # Let the shared interpreter own branches, arithmetic and scope changes;
        # intercept native claim/family fixture iterators, not a duplicate formula.
        value, pending = initial, []
        for key, op, body in nodes:
            if key not in ("every_claim", "every_traveling_family_member"):
                pending.append((key, op, body))
                continue
            value = super().numeric(pending, current, value)
            pending = []
            explicit, pressed = one(body, "explicit"), one(body, "pressed")
            inner = [row for row in body if row[0] not in ("explicit", "pressed")]
            targets = current.lists.get("claims", []) if key == "every_claim" else current.lists.get("traveling_family", [current])
            for title in targets:
                if explicit is not None and title.stats["claim_explicit"] != (explicit == "yes"):
                    continue
                if pressed is not None and title.stats["claim_pressed"] != (pressed == "yes"):
                    continue
                if self.condition(one(inner, "limit", []), title):
                    self.previous.append(current)
                    try:
                        value = self.numeric(inner, title, value)
                    finally:
                        self.previous.pop()
        return super().numeric(pending, current, value)


def person(name="courtier", **stats):
    defaults = {key: D(5) for key in ("diplomacy", "martial", "stewardship", "intrigue", "learning", "prowess")}
    defaults.update({"sum_of_all_skills_value": D(25), "sum_of_all_skills_threshold_good": D(75),
                     "monumentally_high_skill_rating": D(25), "extremely_high_skill_rating": D(20),
                     "very_high_skill_rating": D(18), "high_skill_rating": D(15)})
    defaults.update({key: D(value) if isinstance(value, (int, float)) else value for key, value in stats.items()})
    return Scope(name, stats=defaults)


def claim(name, tier, holder, pressed=True, explicit=True):
    return Scope(name, "title", {"tier": TIERS[tier], "claim_pressed": pressed,
                                  "claim_explicit": explicit}, {"holder": holder} if holder else {})


def classic_ast(nodes):
    result, index = [], 0
    while index < len(nodes):
        key, op, body = nodes[index]
        index += 1
        limit = one(body, "limit") if isinstance(body, list) else None
        if key in ("if", "trigger_if") and limit and len(limit) == 1 and limit[0][0] == "tnt_scaled_valuation_enabled_value":
            _, comparison, number = limit[0]
            enabled = comparison == "=" and number == "0"
            if enabled:
                result.extend(classic_ast([row for row in body if row[0] != "limit"]))
            if index < len(nodes) and nodes[index][0] in ("else", "trigger_else"):
                if not enabled:
                    result.extend(classic_ast(nodes[index][2]))
                index += 1
            continue
        result.append((key, op, classic_ast(body) if isinstance(body, list) else body))
    return result


def unlimited_ai_cooldown_ast(nodes):
    """Remove only the two verified no-op calls for the zero-frequency mode.

    This is not a general effect-name filter: scope, ordering and the refusal
    eligibility branch must match before either addition may be normalized.
    The full resulting AST is still compared against the pinned Classic tree.
    """
    result = deepcopy(nodes)
    start = ("tnt_start_threat_cooldown_effect", "=", "yes")

    def call_paths(rows, path=()):
        for key, op, body in rows:
            if key == start[0]:
                yield path, op, body
            if isinstance(body, list):
                yield from call_paths(body, path + (key,))

    assert list(call_paths(result)) == [
        (("tnt_demand_paid_effect", "scope:tnt_deal_partner"), "=", "yes"),
        (("tnt_demand_refused_effect", "if", "scope:tnt_deal_partner"), "=", "yes"),
    ]
    paid = one(result, "tnt_demand_paid_effect")
    assert paid[0] == ("scope:tnt_deal_partner", "?=", [
        ("add_dread", "=", "minor_dread_gain"), start,
    ])
    paid[0][2].pop()
    refused = one(result, "tnt_demand_refused_effect")
    assert refused[0][0:2] == ("if", "=")
    valid_refusal = refused[0][2]
    assert one(valid_refusal, "limit") == [
        ("exists", "=", "scope:tnt_deal_partner"),
        ("tnt_can_demand_trigger", "=", [("A", "=", "scope:tnt_deal_partner"), ("B", "=", "root")]),
    ]
    assert valid_refusal[-1] == ("scope:tnt_deal_partner", "=", [start])
    valid_refusal.pop()
    return result


class ScaledPeopleTests(unittest.TestCase):
    def table(self, rule="scaled", count=12):
        world = PeopleWorld(rule=rule)
        player = realm(world, "player", count, 20, nested=True)
        partner = realm(world, "partner", 1, 0, tier="tier_county")
        world.root = player
        world.scopes.update(tnt_me=player, tnt_p=partner, actor=player, recipient=partner)
        player.variables["tnt_partner"] = partner
        return world, player, partner

    def test_lowest_courtier_and_progressive_strongest_skill(self):
        world = PeopleWorld()
        self.assertEqual(world.value("tnt_scaled_courtier_intrinsic_value", person()), 1)
        for skill, extra in ((10, 2), (12, 5), (15, 10), (18, 16), (20, 24), (25, 40), (30, 60)):
            for stat in ("diplomacy", "martial", "stewardship", "intrigue", "learning"):
                candidate = person(**{stat: skill})
                self.assertEqual(world.value("tnt_scaled_courtier_intrinsic_value", candidate), 1 + extra)
        self.assertEqual(world.value("tnt_scaled_courtier_intrinsic_value", person(diplomacy=30, martial=30, learning=30)), 61)

    def test_prowess_traits_status_and_inspiration(self):
        world = PeopleWorld()
        for prowess, expected in ((5, 1), (12, 4), (15, 7), (20, 13), (25, 21), (30, 31)):
            self.assertEqual(world.value("tnt_scaled_courtier_intrinsic_value", person(prowess=prowess)), expected)
        candidate = person(traits={"intellect_good_3", "intellect_good_2", "lifestyle_physician", "physique_good_1", "beauty_good_2"})
        candidate.links.update(inspiration=Scope("inspiration", "inspiration"),
                               dynasty=Scope("dynasty", "dynasty", {"dynasty_prestige_level": D(30)}))
        self.assertEqual(world.value("tnt_scaled_courtier_intrinsic_value", candidate), 1 + 10 + 6 + 2 + 4 + 15 + 5)

    def test_strongest_explicit_claim_only_receiver_filter(self):
        world = PeopleWorld()
        receiver, outsider = Scope("receiver"), Scope("outsider")
        world.scopes["tnt_scaled_person_receiver"] = receiver
        candidate = person()
        candidate.lists["claims"] = [claim("county", "tier_county", outsider),
                                     claim("duchy", "tier_duchy", outsider),
                                     claim("empire", "tier_empire", outsider, pressed=False)]
        self.assertEqual(world.value("tnt_scaled_courtier_claim_value", candidate), 13)
        candidate.lists["claims"] += [claim(str(i), "tier_empire", outsider, explicit=False) for i in range(20)]
        candidate.lists["claims"].append(claim("destroyed", "tier_empire", None))
        candidate.lists["claims"].append(claim("own", "tier_empire", receiver))
        candidate.lists["claims"].append(claim("subordinate", "tier_empire", Scope("vassal", links={"liege": receiver})))
        self.assertEqual(world.value("tnt_scaled_courtier_claim_value", candidate), 13)
        candidate.lists["claims"].append(claim("pressed_empire", "tier_empire", outsider))
        self.assertEqual(world.value("tnt_scaled_courtier_claim_value", candidate), 26)
        world.scopes.pop("tnt_scaled_person_receiver")
        self.assertEqual(world.value("tnt_scaled_courtier_claim_value", candidate), 0)

    def test_courtier_wrappers_refresh_direction_and_lists_do_not_saturate(self):
        world, player, partner = self.table()
        candidate = person()
        candidate.lists.update(is_close_or_extended_family_of=[player], has_relation_friend=[partner], has_relation_lover=[partner])
        candidate.lists["claims"] = [claim("duchy", "tier_duchy", partner)]
        player.lists["tnt_sel_courtier_p"] = [candidate]
        player.lists["tnt_sel_courtier_r"] = [candidate]
        self.assertEqual(world.value("tnt_val_courtier_multi_p_value"), 11)  # donor kin + receiver friend, claim already receiver-owned
        self.assertEqual(world.value("tnt_val_courtier_multi_r_value"), 11)  # reverse claim now useful; neither relation bonus applies
        self.assertIs(world.scopes["tnt_scaled_person_receiver"], player)
        self.assertEqual(world.value("tnt_val_courtier_multi_p_value"), 11)
        player.lists["tnt_sel_courtier_p"] = [person(str(i)) for i in range(150)]
        self.assertEqual(world.value("tnt_val_courtier_multi_p_value"), 150)

    def test_classic_courtiers_unchanged(self):
        for setting in (None, "classic"):
            world, player, partner = self.table(setting)
            candidate = person(martial=25)
            candidate.lists["is_close_or_extended_family_of"] = [player]
            player.lists["tnt_sel_courtier_p"] = [candidate]
            self.assertEqual(world.value("tnt_val_courtier_multi_p_value"), 50)
            player.lists["tnt_sel_courtier_p"] = [person()]
            self.assertEqual(world.value("tnt_val_courtier_multi_p_value"), 10)

    def test_native_companions_are_priced_once_without_staying_relatives(self):
        world, player, partner = self.table()
        head, spouse = person("head"), person("genius spouse", traits={"intellect_good_3"})
        staying = person("relative at another court", learning=30)
        already_there = person("receiver courtier", learning=30)
        already_there.links["courtier_of"] = partner
        head.lists.update(traveling_family=[head, spouse, already_there], spouses=[spouse], children=[staying])
        player.lists["tnt_sel_courtier_p"] = [head]
        self.assertEqual(world.value("tnt_val_courtier_multi_p_value"), 12)  # 1 head + 11 companion
        self.assertEqual(world.value("tnt_scaled_courtier_intrinsic_value", head), 1)  # not an AI useful head
        player.lists["tnt_sel_courtier_r"] = [head]
        self.assertEqual(world.value("tnt_val_courtier_multi_r_value"), 61)  # correct reverse receiver, companion cap60
        head.lists["traveling_family"] = [head]
        self.assertEqual(world.value("tnt_val_courtier_multi_p_value"), 1)

    def test_companion_cap_is_per_head_not_a_selected_list_discount(self):
        world, player, partner = self.table()
        heads = [person("first"), person("second")]
        for head in heads:
            head.lists["traveling_family"] = [head, person("specialist", learning=30), person("second specialist", learning=30)]
        player.lists["tnt_sel_courtier_p"] = heads
        self.assertEqual(world.value("tnt_val_courtier_multi_p_value"), 122)
        for setting in (None, "classic"):
            world.rule = setting
            self.assertEqual(world.value("tnt_val_courtier_multi_p_value"), 20)

    def scaled_preflight_branches(self):
        path = shared.SOURCE / "common/scripted_triggers/tnt_43_preflight.txt"
        ast = parse(path.read_text(encoding="utf-8-sig").replace("$PLAYER$", "scope:player").replace("$PARTNER$", "scope:partner"))
        def find(nodes):
            for key, op, body in nodes:
                if isinstance(body, list):
                    if key == "trigger_if" and one(body, "limit") == [("tnt_scaled_valuation_enabled_value", ">", "0")]:
                        yield (key, op, body)
                    yield from find(body)
        branches = list(find(ast))
        self.assertEqual(len(branches), 1)
        return branches

    def test_scaled_preflight_rejects_shared_unselected_companion(self):
        branches = self.scaled_preflight_branches()
        for side in ("p", "r"):
            world, player, partner = self.table()
            world.scopes.update(player=player, partner=partner)
            receiver = partner if side == "p" else player
            first, second, child = person("first"), person("second"), person("shared child")
            first.lists["traveling_family"] = [first, child]
            second.lists["traveling_family"] = [second, child]
            player.lists["tnt_sel_courtier_" + side] = [first, second]
            self.assertFalse(world.condition(branches, player))
            for setting in (None, "classic"):
                world.rule = setting
                self.assertTrue(world.condition(branches, player))
            world.rule = "scaled"
            second.lists["traveling_family"] = [second, person("different child")]
            self.assertTrue(world.condition(branches, player))
            second.lists["traveling_family"] = [second, child]
            child.links["courtier_of"] = receiver
            self.assertTrue(world.condition(branches, player))
            player.lists["tnt_sel_courtier_" + side] = [first]
            child.links.clear()
            self.assertTrue(world.condition(branches, player))

    def test_scaled_preflight_rejects_moving_companion_marriage_overlap(self):
        branches = self.scaled_preflight_branches()
        for side in ("p", "r"):
            for endpoint in ("player", "partner"):
                with self.subTest(side=side, marriage_endpoint=endpoint):
                    world, player, partner = self.table()
                    world.scopes.update(player=player, partner=partner)
                    receiver = partner if side == "p" else player
                    head, dependent, other = person("head"), person("dependent"), person("other spouse")
                    head.lists["traveling_family"] = [head, dependent]
                    player.lists["tnt_sel_courtier_" + side] = [head]
                    first, second = (dependent, other) if endpoint == "player" else (other, dependent)
                    first.variables["tnt_wed_partner"] = second
                    player.lists["tnt_wed_list"] = [first]
                    self.assertFalse(world.condition(branches, player))

                    # Classic/absent-rule behavior remains untouched.
                    for setting in (None, "classic"):
                        world.rule = setting
                        self.assertTrue(world.condition(branches, player))
                    world.rule = "scaled"

                    # The new rule concerns an actual priced move, not kinship.
                    dependent.links["courtier_of"] = receiver
                    self.assertTrue(world.condition(branches, player))
                    dependent.links.clear()
                    head.lists["traveling_family"] = [head]
                    self.assertTrue(world.condition(branches, player))

                    # Unrelated marriages and an absent/empty pair list pass.
                    head.lists["traveling_family"] = [head, person("different dependent")]
                    self.assertTrue(world.condition(branches, player))
                    head.lists["traveling_family"] = [head, dependent]
                    player.lists["tnt_wed_list"] = []
                    self.assertTrue(world.condition(branches, player))
                    del player.lists["tnt_wed_list"]
                    self.assertTrue(world.condition(branches, player))

    def test_hostage_native_once_and_bounded_leverage(self):
        for native in (-20, 80, 140):
            for relation, cap in (("is_heir_of", 60), ("is_child_of", 30), ("is_close_or_extended_family_of", 15), (None, 0)):
                world, player, partner = self.table(count=200)
                hostage = person(hostage_value=native)
                if relation:
                    hostage.lists[relation] = [player]
                player.variables["tnt_hostage_p"] = hostage
                self.assertEqual(world.value("tnt_val_hostage_p_value"), max(10, native) + cap)
                self.assertEqual(world.native_hostage_reads, 1)
                self.assertIs(world.scopes["home_court"], player)
                self.assertIs(world.scopes["warden"], partner)

    def test_hostage_small_realm_and_reverse_refresh(self):
        world, player, partner = self.table(count=1)
        hostage = person(hostage_value=80)
        hostage.lists["is_heir_of"] = [partner]
        player.variables["tnt_hostage_r"] = hostage
        self.assertEqual(world.value("tnt_val_hostage_r_value"), 82)
        self.assertIs(world.scopes["home_court"], partner)
        self.assertIs(world.scopes["warden"], player)
        world.rule = "classic"
        self.assertEqual(world.value("tnt_val_hostage_r_value"), 80)

    def test_transfer_and_independence_uncapped_correct_realm(self):
        world, player, partner = self.table(count=100)
        subject = realm(world, "subject", 12, 20, nested=True)
        player.lists["tnt_sel_subject_p"] = [subject]
        player.lists["tnt_sel_subject_r"] = [subject]
        self.assertEqual(world.value("tnt_val_subject_multi_p_value"), 420)
        subject.links["primary_title"].links.update(de_jure_liege=partner.links["primary_title"])
        partner.links["primary_title"].links["holder"] = partner
        self.assertEqual(world.value("tnt_val_subject_multi_p_value"), 588)
        self.assertEqual(world.value("tnt_val_subject_multi_r_value"), 420)
        player.variables.update(tnt_indep_p=D(1), tnt_indep_r=D(1))
        self.assertEqual(world.value("tnt_val_indep_p_value"), 120)
        self.assertEqual(world.value("tnt_val_indep_r_value"), 3120)
        for setting in (None, "classic"):
            world.rule = setting
            self.assertEqual(world.value("tnt_val_subject_multi_p_value"), 200)
            self.assertEqual(world.value("tnt_val_indep_r_value"), 250)

    def test_a19_entry_pick_and_motive_share_actual_scaled_predicate(self):
        world = PeopleWorld()
        receiver = Scope("ai")
        world.scopes["tnt_ai"] = receiver
        ast = parse((shared.SOURCE / "common/scripted_effects/tnt_37_ai_offer.txt").read_text(encoding="utf-8-sig"))
        def find(nodes):
            for key, _, body in nodes:
                if isinstance(body, list):
                    if key == "trigger_if" and ("tnt_scaled_courtier_intrinsic_value", ">=", "10") in body:
                        yield body
                    yield from find(body)
        branches = list(find(ast))
        self.assertEqual(len(branches), 3)
        claimant = person()
        claimant.lists["claims"] = [claim("claim", "tier_duchy", Scope("foreign"))]
        for body in branches:
            active = [row for row in body if row[0] != "limit"]
            for candidate, expected in ((person(), False), (person(learning=15), True), (claimant, True)):
                world.scopes["tnt_scaled_person_receiver"] = Scope("stale")
                self.assertEqual(world.condition(active, candidate), expected)
                self.assertIs(world.scopes["tnt_scaled_person_receiver"], receiver)

    def test_full_classic_ast_matches_pinned_people_and_composer(self):
        repo = shared.SOURCE.parent.parent
        for relative in ("common/script_values/tnt_58_person_values.txt", "common/scripted_effects/tnt_37_ai_offer.txt", "common/scripted_triggers/tnt_43_preflight.txt"):
            path = shared.SOURCE / relative
            previous = subprocess.check_output(["git", "show", f"{shared.CLASSIC_BASELINE}:{path.relative_to(repo).as_posix()}"], cwd=repo)
            current = classic_ast(parse(path.read_text(encoding="utf-8-sig")))
            if relative == "common/scripted_effects/tnt_37_ai_offer.txt":
                current = unlimited_ai_cooldown_ast(current)
            self.assertEqual(current, parse(previous.decode("utf-8-sig")))

    def test_classic_normalization_rejects_misplaced_or_extra_cooldown_calls(self):
        path = shared.SOURCE / "common/scripted_effects/tnt_37_ai_offer.txt"
        current = classic_ast(parse(path.read_text(encoding="utf-8-sig")))
        for mutation in ("wrong_aggressor", "extra_start", "outside_eligibility", "renamed_effect"):
            with self.subTest(mutation=mutation):
                changed = deepcopy(current)
                paid = one(changed, "tnt_demand_paid_effect")
                refused = one(changed, "tnt_demand_refused_effect")
                if mutation == "wrong_aggressor":
                    paid[0] = ("root", "?=", paid[0][2])
                elif mutation == "extra_start":
                    paid[0][2].append(paid[0][2][-1])
                elif mutation == "outside_eligibility":
                    refused.append(refused[0][2].pop())
                else:
                    paid[0][2][-1] = ("arbitrary_cooldown_effect", "=", "yes")
                with self.assertRaises(AssertionError):
                    unlimited_ai_cooldown_ast(changed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=shared.SOURCE)
    args, remaining = parser.parse_known_args()
    shared.SOURCE = args.source.resolve()
    unittest.main(argv=[__file__, *remaining], verbosity=2)
