"""Execute advanced-interest production AST against explicit native-state facts.

This is a strict arithmetic/scope regression suite, not CK3 acceptance. Council
positions, wars, equipped inventory, faith and selected objects are fixture
facts. Existing signed contract base prices are inputs; all new interest
definitions and existing selection counters execute their real AST.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import unittest

from test_autobalance import DEFAULT_SOURCE, one, parse
from test_scaled_valuation import D, Scope, ValuationWorld

SOURCE = DEFAULT_SOURCE
TERMS = ("title", "subject", "courtier", "artifact", "vassal", "indep",
         "hostage", "hook", "marriage", "ob_tax", "ob_levy", "ob_fort",
         "ob_coin", "ob_relig", "ob_council", "ob_revoke", "ob_war", "ob_succ")
CONTRACTS = tuple(term for term in TERMS if term.startswith("ob_"))
SLOTS = ("primary_armament", "armor", "regalia", "helmet")


class InterestWorld(ValuationWorld):
    def __init__(self, strength=1):
        super().__init__(source=SOURCE)
        self.partner = Scope("partner")
        self.root.variables["tnt_partner"] = self.partner
        for character in (self.root, self.partner):
            character.stats.update(
                tnt_interests_enabled_value=D(int(strength > 0)),
                tnt_interest_strength_value=D(str(strength)),
                domain_size=D(3), domain_limit=D(5), vassal_count=D(4),
                vassal_limit=D(10), vassal_limit_available=D(6),
                is_at_war=False, is_ruler=True, is_councillor=False,
                gold=D(100), dread=D(0))
        for term in CONTRACTS:
            self.root.stats["tnt_val_" + term + "_value"] = D(0)

    def scope(self, atom, current):
        if "." in atom:
            first, *links = atom.split(".")
            result = self.scope(first, current)
            for link in links:
                if not isinstance(result, Scope):
                    return None
                result = (result.variables.get(link[4:]) if link.startswith("var:")
                          else result.links.get(link))
            return result
        return super().scope(atom, current)

    def operand(self, atom, current):
        if isinstance(atom, str) and atom in SLOTS:
            return atom
        return super().operand(atom, current)

    def condition(self, nodes, current):
        converted = []
        for key, op, body in nodes:
            if key == "variable_list_size":
                operation, target = next((o, b) for k, o, b in body if k == "value")
                answer = self.compare(D(len(current.lists.get(one(body, "name"), []))),
                                      operation, self.operand(target, current))
                converted.append(("always", "=", "yes" if answer else "no"))
            elif key == "any_equipped_character_artifact":
                answer = any(self.condition(body, artifact)
                             for artifact in current.lists.get("equipped_artifacts", []))
                converted.append(("always", "=", "yes" if answer else "no"))
            else:
                converted.append((key, op, body))
        return super().condition(converted, current)

    def numeric(self, nodes, current, initial=D(0)):
        # desc controls native tooltip text only; every numeric operation runs.
        return super().numeric([row for row in nodes if row[0] != "desc"], current, initial)

    def select(self, term, side, count=1):
        if term in ("title", "subject", "courtier", "artifact"):
            self.root.lists[f"tnt_sel_{term}_{side}"] = [
                Scope(str(i), stats={"tier": D(2), "is_equipped": False,
                                     "artifact_slot_type": "primary_armament"})
                for i in range(count)]
        elif term in CONTRACTS:
            self.root.stats["tnt_val_" + term + "_value"] = D(40)
        elif term == "marriage":
            self.root.variables["tnt_marriage_" + side] = D(1)
            self.root.lists["tnt_wed_list"] = [Scope("spouse")]
        elif term == "hostage":
            self.root.variables["tnt_hostage_" + side] = Scope("hostage")
        else:
            self.root.variables["tnt_" + term + "_" + side] = D(1)

    def factor(self, term, side):
        return self.value(f"tnt_interest_{term}_{side}_factor_value")


class AdvancedInterestTests(unittest.TestCase):
    def test_all_terms_presets_directions_and_exact_percent_reconciliation(self):
        for term in TERMS:
            for side in ("p", "r"):
                factors = []
                for strength in (0, .5, 1, 2):
                    with self.subTest(term=term, side=side, strength=strength):
                        world = InterestWorld(strength)
                        world.select(term, side)
                        factor = world.factor(term, side)
                        percent = world.value(f"tnt_interest_{term}_{side}_percent_value")
                        expected = factor * 100 if side == "p" else 100 / factor
                        self.assertAlmostEqual(percent, expected, places=20)
                        self.assertGreaterEqual(factor, 0 if side == "p" else 1)
                        self.assertLessEqual(factor, 1 if side == "p" else 100)
                        if strength == 0:
                            self.assertEqual(factor, 1)
                        factors.append(factor)
                self.assertEqual(factors, sorted(factors, reverse=(side == "p")))

    def test_empty_and_partnerless_are_neutral_and_do_not_read_context(self):
        for term in TERMS:
            for side in ("p", "r"):
                world = InterestWorld()
                self.assertEqual(world.factor(term, side), 1)
                self.assertEqual(world.value(f"tnt_interest_{term}_{side}_selected_value"), 0)
                world.select(term, side)
                del world.root.variables["tnt_partner"]
                world.scopes["tnt_p"] = world.partner  # deliberately stale
                self.assertEqual(world.factor(term, side), 1)
                self.assertEqual(world.iterator_visits, 0)

    def test_off_does_not_evaluate_new_raw_motives(self):
        world = InterestWorld(0)
        for term in TERMS:
            for side in ("p", "r"):
                world.select(term, side)
                self.assertEqual(world.factor(term, side), 1)
                self.assertEqual(world.value(f"tnt_interest_{term}_{side}_percent_value"), 100)
        self.assertFalse(any(key.endswith("_raw_value") for key in world.evaluations))
        self.assertEqual(world.iterator_visits, 0)

    def test_zero_receive_and_finite_surrender_floor_in_every_enabled_mode(self):
        for strength in (.5, 1, 2):
            world = InterestWorld(strength)
            world.select("title", "p")
            world.select("title", "r")
            # Boundary inputs exercise production transforms independently of
            # the currently calibrated title motives.
            world.root.stats["tnt_interest_title_p_raw_value"] = D(0)
            world.root.stats["tnt_interest_title_r_raw_value"] = D(".001")
            self.assertEqual(world.factor("title", "p"), 0)
            self.assertEqual(world.factor("title", "r"), 100)
            self.assertEqual(world.value("tnt_interest_title_p_percent_value"), 0)
            self.assertEqual(world.value("tnt_interest_title_r_percent_value"), 1)

    def test_receiving_land_accounts_for_opposite_transfer_and_current_partner(self):
        world = InterestWorld()
        world.partner.stats["domain_size"] = D(5)
        world.select("title", "p", 2)
        self.assertEqual(world.factor("title", "p"), D(".3"))
        world.select("title", "r", 2)
        self.assertEqual(world.factor("title", "p"), D(".9"))
        stranger = Scope("stale", stats={"domain_size": D(100), "domain_limit": D(0)})
        world.scopes["tnt_p"] = stranger
        self.assertEqual(world.factor("title", "p"), D(".9"))
        world.root.variables["tnt_partner"] = stranger
        self.assertEqual(world.factor("title", "p"), D(".3"))

    def test_capacity_uses_fraction_of_incoming_domain_and_vassals(self):
        world = InterestWorld()
        world.partner.stats.update(domain_size=D(4), vassal_count=D(9))
        world.select("title", "p", 2)
        world.select("subject", "p", 2)
        self.assertEqual(world.factor("title", "p"), D(".6"))
        self.assertEqual(world.factor("subject", "p"), D(".55"))
        world.root.lists["tnt_sel_title_p"].reverse()
        self.assertEqual(world.factor("title", "p"), D(".6"))

    def test_domain_and_vassal_relief_increases_willingness_without_discounting_cost(self):
        world = InterestWorld()
        for term, field in (("title", "domain_size"), ("subject", "vassal_count")):
            world.select(term, "r", 2)
            before = world.factor(term, "r")
            world.partner.stats[field] = D(30)
            after = world.factor(term, "r")
            self.assertLess(after, before)
            self.assertGreaterEqual(after, 1)

    def test_court_demand_tracks_vacancies_and_offer_volume_not_skill_price(self):
        world = InterestWorld()
        world.select("courtier", "p")
        self.assertEqual(world.factor("courtier", "p"), D(".85"))
        world.select("courtier", "p", 8)
        self.assertEqual(world.factor("courtier", "p"), D(".675"))
        for position in ("chancellor", "marshal", "steward", "spymaster"):
            world.partner.links["cp:councillor_" + position] = Scope(position)
        self.assertEqual(world.factor("courtier", "p"), D(".5"))

    def test_artifact_selected_slots_and_equipped_loss_are_directional(self):
        world = InterestWorld()
        world.select("artifact", "p", 2)
        world.select("artifact", "r")
        before = world.factor("artifact", "p")
        world.partner.lists["equipped_artifacts"] = [
            Scope("sword", stats={"artifact_slot_type": "primary_armament"})]
        self.assertEqual(before, D(".725"))  # two swords compete for one slot
        self.assertEqual(world.factor("artifact", "p"), D(".6"))
        self.assertEqual(world.factor("artifact", "r"), D(1) / D(".75"))
        world.root.lists["tnt_sel_artifact_r"][0].stats["is_equipped"] = True
        self.assertEqual(world.factor("artifact", "r"), D("2.5"))
        # A simultaneously surrendered equipped sword is no retained alternative.
        self.assertEqual(world.factor("artifact", "p"), D(".725"))

    def test_war_changes_autonomy_protection_marriage_and_military_contracts(self):
        world = InterestWorld()
        expected = (("vassal", "r", False), ("indep", "p", False),
                    ("indep", "r", True), ("marriage", "p", True),
                    ("marriage", "r", True), ("ob_levy", "p", True))
        for term, side, increase in expected:
            world.select(term, side)
            world.partner.stats["is_at_war"] = False
            peaceful = world.factor(term, side)
            world.partner.stats["is_at_war"] = True
            wartime = world.factor(term, side)
            self.assertEqual(wartime > peaceful, increase, (term, side))

    def test_signed_obligations_never_make_negative_burden_cheaper(self):
        for term in CONTRACTS:
            for strength in (0, .5, 1, 2):
                world = InterestWorld(strength)
                for amount in (-40, 0, 40):
                    world.root.stats["tnt_val_" + term + "_value"] = D(amount)
                    adjusted = world.value(f"tnt_interest_{term}_effective_value")
                    self.assertLessEqual(adjusted, amount)
                    if amount == 0 or strength == 0:
                        self.assertEqual(adjusted, amount)
                    side = "r" if amount < 0 else "p"
                    self.assertEqual(world.value(f"tnt_interest_{term}_percent_value"),
                                     world.value(f"tnt_interest_{term}_{side}_percent_value"))

    def test_debt_faith_council_and_heir_are_native_context_not_flat_defaults(self):
        world = InterestWorld()
        world.select("ob_tax", "p")
        self.assertEqual(world.factor("ob_tax", "p"), D(".8"))
        world.partner.stats["gold"] = D(-1)
        self.assertEqual(world.factor("ob_tax", "p"), 1)
        world.select("ob_relig", "p")
        faith = Scope("faith", "faith")
        world.root.links["faith"] = faith
        world.partner.links["faith"] = faith
        self.assertEqual(world.factor("ob_relig", "p"), D(".5"))
        world.select("ob_succ", "r")
        before = world.factor("ob_succ", "r")
        world.partner.links["player_heir"] = Scope("heir")
        self.assertGreater(world.factor("ob_succ", "r"), before)

    def test_excludes_pressure_retired_terms_and_repriced_intrinsic_traits(self):
        path = SOURCE / "common/script_values/tnt_62_interest_advanced_values.txt"
        ast = parse(path.read_text(encoding="utf-8-sig"))
        text = repr(ast)
        for forbidden in ("tnt_threat", "tnt_usehook", "tnt_sel_claim", "tnt_prisoner",
                          "ai_greed", "ai_rationality", "ai_boldness",
                          "is_close_or_extended_family_of", "de_jure", "prowess",
                          "can_equip_artifact", "can_benefit_from_artifact"):
            self.assertNotIn(forbidden, text)
        for term in TERMS:
            for side in ("p", "r"):
                percent = dict((key, body) for key, _, body in ast)[
                    f"tnt_interest_{term}_{side}_percent_value"]
                self.assertIn("tnt_interest_bd_base", repr(percent))
                self.assertIn("tnt_interest_bd_rule", repr(percent))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    args, remaining = parser.parse_known_args()
    SOURCE = args.source.resolve()
    unittest.main(argv=[__file__, *remaining], verbosity=2)
