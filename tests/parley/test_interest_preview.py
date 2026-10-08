"""Read-only UI-preview AST checks; not a substitute for native GUI execution."""
from copy import deepcopy
from decimal import ROUND_HALF_UP
from pathlib import Path
import re
import unittest

from test_autobalance import DEFAULT_SOURCE, parse
from test_interest_advanced import CONTRACTS, TERMS, InterestWorld as AdvancedWorld
from test_interest_currency import CURRENCIES, STRENGTHS, InterestWorld as CurrencyWorld
from test_scaled_valuation import D, Scope


PREVIEW = DEFAULT_SOURCE / "common/script_values/tnt_65_interest_preview_values.txt"


class CurrencyPreviewTests(unittest.TestCase):
    def test_marginal_preview_at_all_bands_and_presets_without_a_selected_amount(self):
        for policy, strength in STRENGTHS.items():
            world = CurrencyWorld(policy)
            for currency in CURRENCIES:
                world.root.stats[f"tnt_interest_{currency}_capacity_value"] = D(100)
                for stock, receive, surrender in ((-1, 100, 100 / (1 + 3 * strength)),
                        (0, 100, 100 / (1 + 3 * strength)),
                        (25, 100, 100 / (1 + 3 * strength)),
                        (50, 100, 100 / (1 + strength)),
                        (100, 100 / (1 + strength), 100 / (1 + strength)),
                        (150, 100 / (1 + strength), 100), (200, 0, 100), (10000, 0, 100)):
                    world.partner.stats[currency] = D(stock)
                    for side, expected in (("p", receive), ("r", surrender)):
                        with self.subTest(policy=policy, currency=currency, stock=stock, side=side):
                            prefix = f"tnt_interest_{currency}_{side}"
                            actual = world.value(prefix + "_preview_percent_value")
                            self.assertAlmostEqual(actual, D(expected), places=20)
                            self.assertEqual(world.value(prefix + "_display_percent_value"), actual)
                            self.assertEqual(world.value(prefix + "_factor_value"), 1)
                            self.assertNotIn(f"tnt_{currency}_{side}", world.root.variables)

    def test_real_zero_not_missing_or_arbitrary_neutral_and_rounding_is_display_only(self):
        world = CurrencyWorld()
        world.partner.stats["gold"] = D(1000000)
        self.assertEqual(world.value("tnt_interest_gold_p_preview_percent_value"), 0)
        self.assertEqual(world.value("tnt_interest_gold_p_badge_percent_value"), 0)
        world.root.variables["tnt_gold_p"] = D(1)
        for percent in (D("49.9"), D("49.4"), D("50.1"), D(0)):
            world.root.stats["tnt_interest_gold_p_percent_value"] = percent
            self.assertEqual(world.value("tnt_interest_gold_p_display_percent_value"), percent)
            self.assertEqual(world.value("tnt_interest_gold_p_badge_percent_value"), percent.quantize(D(1), rounding=ROUND_HALF_UP))

    def test_off_absent_rule_missing_partner_and_influence_permission_guards(self):
        for policy in (None, "off", "standard"):
            world = CurrencyWorld(policy)
            if policy == "standard":
                del world.root.variables["tnt_partner"]
                world.scopes["tnt_p"] = world.partner
            for currency in CURRENCIES:
                for side in ("p", "r"):
                    self.assertEqual(world.value(f"tnt_interest_{currency}_{side}_display_percent_value"), 100)
        world = CurrencyWorld()
        world.partner.stats["government_flags"] = set()
        for side in ("p", "r"):
            self.assertEqual(world.value(f"tnt_interest_influence_{side}_preview_percent_value"), 100)

    def test_selected_display_is_original_percent_and_skips_preview_branch(self):
        for currency in CURRENCIES:
            for side in ("p", "r"):
                world = CurrencyWorld()
                world.quote(currency, side, stock=80, amount=40)
                name = f"tnt_interest_{currency}_{side}"
                actual = world.value(name + "_percent_value")
                self.assertEqual(world.value(name + "_display_percent_value"), actual)
                self.assertNotIn(name + "_preview_percent_value", world.evaluations)

    def test_preview_reacts_to_capacity_stock_and_partner_without_mutation(self):
        world = CurrencyWorld()
        world.partner.stats["gold"] = D(150)
        self.assertEqual(world.value("tnt_interest_gold_p_display_percent_value"), 50)
        world.partner.stats["yearly_character_income"] = D(100)
        before = deepcopy(world.partner.stats)
        variables_before = dict(world.root.variables)
        self.assertEqual(world.value("tnt_interest_gold_p_display_percent_value"), 100)
        self.assertEqual(world.partner.stats, before)
        self.assertEqual(world.root.variables, variables_before)
        stranger = CurrencyWorld().partner
        stranger.stats["gold"] = D(10000)
        world.scopes["tnt_p"] = world.partner
        world.root.variables["tnt_partner"] = stranger
        self.assertEqual(world.value("tnt_interest_gold_p_display_percent_value"), 0)


class AdvancedPreviewTests(unittest.TestCase):
    def test_all_empty_terms_presets_match_independent_transform_and_keep_settlement_neutral(self):
        for strength in (D(0), D(".5"), D(1), D(2)):
            world = AdvancedWorld(strength)
            for term in TERMS:
                for side in ("p", "r"):
                    with self.subTest(term=term, side=side, strength=strength):
                        prefix = f"tnt_interest_{term}_{side}"
                        raw = world.value(prefix + "_preview_raw_value")
                        expected = D(100) if not strength else 100 * raw / (strength + (1 - strength) * raw)
                        if side == "r":
                            expected = max(D(1), expected)
                        self.assertAlmostEqual(world.value(prefix + "_preview_percent_value"), expected, places=20)
                        self.assertEqual(world.value(prefix + "_display_percent_value"), world.value(prefix + "_preview_percent_value"))
                        self.assertEqual(world.value(prefix + "_selected_value"), 0)
                        self.assertEqual(world.value(prefix + "_factor_value"), 1)
                        self.assertNotIn("tnt_" + term + "_" + side, world.root.variables)

    def test_preview_domain_and_vassal_capacity_are_explicit_one_unit_context(self):
        world = AdvancedWorld()
        for term, stock, limit, expected in (("title", "domain_size", "domain_limit", D(30)),
                                           ("subject", "vassal_count", "vassal_limit", D(25))):
            world.partner.stats[stock] = world.partner.stats[limit]
            self.assertEqual(world.value(f"tnt_interest_{term}_p_preview_percent_value"), expected)
            world.partner.stats[stock] += 1
            self.assertAlmostEqual(world.value(f"tnt_interest_{term}_r_preview_percent_value"), D(90), places=20)
            # Preview is current-context, not a hidden post-draft object guess.
            world.select(term, "p", 12)
            world.select(term, "r", 12)
            self.assertEqual(world.value(f"tnt_interest_{term}_p_preview_percent_value"), expected)

    def test_unknown_artifact_axes_are_omitted_not_inferred_from_current_equipment(self):
        world = AdvancedWorld()
        world.partner.lists["equipped_artifacts"] = [Scope("sword", stats={"artifact_slot_type": "primary_armament"})]
        world.select("artifact", "p", 5)
        world.select("artifact", "r", 5)
        for artifact in world.root.lists["tnt_sel_artifact_r"]:
            artifact.stats["is_equipped"] = True
        self.assertEqual(world.value("tnt_interest_artifact_p_preview_percent_value"), 85)
        self.assertAlmostEqual(world.value("tnt_interest_artifact_r_preview_percent_value"), D(75), places=20)
        self.assertEqual(world.iterator_visits, 0)

    def test_courtier_preview_uses_one_recruit_and_real_vacancies(self):
        world = AdvancedWorld()
        self.assertEqual(world.value("tnt_interest_courtier_p_preview_percent_value"), 85)
        self.assertEqual(world.value("tnt_interest_courtier_r_preview_percent_value"), 45)
        for position in ("chancellor", "marshal", "steward", "spymaster"):
            world.partner.links["cp:councillor_" + position] = Scope(position)
        self.assertEqual(world.value("tnt_interest_courtier_p_preview_percent_value"), 50)
        self.assertAlmostEqual(world.value("tnt_interest_courtier_r_preview_percent_value"), D(70), places=20)

    def test_selected_advanced_display_is_unchanged_original_percent(self):
        world = AdvancedWorld()
        for term in TERMS:
            for side in ("p", "r"):
                world.select(term, side)
                prefix = f"tnt_interest_{term}_{side}"
                self.assertEqual(world.value(prefix + "_display_percent_value"), world.value(prefix + "_percent_value"))
                self.assertNotIn(prefix + "_preview_percent_value", world.evaluations)

    def test_signed_contract_zero_means_benefit_preview_then_actual_signed_direction(self):
        world = AdvancedWorld()
        for term in CONTRACTS:
            prefix = "tnt_interest_" + term
            self.assertEqual(world.value(prefix + "_display_percent_value"), world.value(prefix + "_p_preview_percent_value"))
            for amount, side in ((-40, "r"), (40, "p")):
                world.root.stats["tnt_val_" + term + "_value"] = D(amount)
                self.assertEqual(world.value(prefix + "_display_percent_value"), world.value(prefix + "_" + side + "_percent_value"))
            world.root.stats["tnt_val_" + term + "_value"] = D(0)
            self.assertEqual(world.value(prefix + "_display_percent_value"), world.value(prefix + "_preview_percent_value"))
            self.assertEqual(world.value(prefix + "_effective_value"), 0)

    def test_off_and_partnerless_previews_do_not_evaluate_context(self):
        for strength, partner in ((0, True), (1, False)):
            world = AdvancedWorld(strength)
            if not partner:
                del world.root.variables["tnt_partner"]
                world.scopes["tnt_p"] = world.partner
            for term in TERMS:
                for side in ("p", "r"):
                    self.assertEqual(world.value(f"tnt_interest_{term}_{side}_preview_percent_value"), 100)
            self.assertFalse(any(name.endswith("_preview_raw_value") for name in world.evaluations))
            self.assertEqual(world.iterator_visits, 0)


class PreviewIsolationTests(unittest.TestCase):
    def test_only_new_file_owns_preview_api_no_settlement_consumer(self):
        definitions = {name for name, _, _ in parse(PREVIEW.read_text(encoding="utf-8-sig"))}
        for path in (DEFAULT_SOURCE / "common").rglob("*.txt"):
            if path == PREVIEW:
                continue
            text = re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig"))
            self.assertFalse(definitions & set(re.findall(r"\btnt_interest_\w+_value\b", text)), path)

    def test_no_mutation_random_object_iteration_or_pressure_api(self):
        text = repr(parse(PREVIEW.read_text(encoding="utf-8-sig")))
        for forbidden in ("set_variable", "change_variable", "add_gold", "random", "every_in_list",
                          "tnt_threat", "tnt_usehook", "scope:tnt_p", "tnt_ai_accept_value"):
            self.assertNotIn(forbidden, text)

    def test_badge_rounding_is_the_only_rounding_layer(self):
        for name, _, body in parse(PREVIEW.read_text(encoding="utf-8-sig")):
            if name.endswith("_badge_percent_value"):
                self.assertEqual(sum(key == "round" for key, _, _ in body), 1)
            else:
                self.assertNotIn("('round',", repr(body), name)

    def test_unknown_artifact_axes_are_not_shown_as_zero_motive_rows(self):
        definitions = {name: body for name, _, body in parse(PREVIEW.read_text(encoding="utf-8-sig"))}
        for side in ("p", "r"):
            body = repr(definitions[f"tnt_interest_artifact_{side}_preview_percent_value"])
            self.assertIn("tnt_interest_bd_preview_artifact_base", body)
            self.assertNotIn("tnt_interest_bd_artifact_alternative", body)
            self.assertNotIn("tnt_interest_bd_artifact_equipped", body)

    def test_empty_currency_motives_do_not_claim_a_selected_or_surrendered_amount(self):
        preview = {name: body for name, _, body in parse(PREVIEW.read_text(encoding="utf-8-sig"))}
        selected_path = DEFAULT_SOURCE / "common/script_values/tnt_61_interest_currency_values.txt"
        selected = {name: body for name, _, body in parse(selected_path.read_text(encoding="utf-8-sig"))}
        for currency in CURRENCIES:
            for side, reason in (("p", "receiving_demand"), ("r", "surrender_reserve")):
                prefix = f"tnt_interest_{currency}_{side}"
                self.assertIn("tnt_interest_bd_preview_" + reason, repr(preview[prefix + "_preview_percent_value"]))
                self.assertNotIn("tnt_interest_bd_" + reason, repr(preview[prefix + "_preview_percent_value"]))
                self.assertIn("tnt_interest_bd_" + reason, repr(selected[prefix + "_percent_value"]))
                self.assertNotIn("tnt_interest_bd_preview_", repr(selected[prefix + "_percent_value"]))
        locales = list((DEFAULT_SOURCE / "localization").glob("*/*.yml"))
        self.assertEqual(len(locales), 9)
        for path in locales:
            content = path.read_text(encoding="utf-8-sig")
            for reason in ("receiving_demand", "surrender_reserve"):
                self.assertEqual(len(re.findall(r'^ tnt_interest_bd_preview_' + reason + r':0 "[^\n]+"', content, re.M)), 1, path)


if __name__ == "__main__":
    unittest.main()
