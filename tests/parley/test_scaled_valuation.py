"""Execute actual Advanced term valuation AST against explicit scope fixtures.

This constrained interpreter is not CK3. County ownership/vassal relationships
are fixture inputs; the native every_sub_realm_county iterator is modeled as a
unique county walk down that explicit graph. Prices are never fixture leaves.
Unknown executed syntax fails rather than being silently ignored. Native smoke
must still establish engine iterator/scope behavior and performance.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from pathlib import Path
import subprocess
import unittest

from test_autobalance import DEFAULT_SOURCE, one, parse

D = Decimal
SOURCE = DEFAULT_SOURCE
CLASSIC_BASELINE = "e17e147cec14975196ce6338e3e2e41afab2bcb5"
TIERS = {"tier_unlanded": D(0), "tier_barony": D(1), "tier_county": D(2),
         "tier_duchy": D(3), "tier_kingdom": D(4), "tier_empire": D(5),
         "tier_hegemony": D(6)}


class Unsupported(RuntimeError):
    pass


@dataclass(eq=False)
class Scope:
    name: str
    kind: str = "character"
    stats: dict = field(default_factory=dict)
    links: dict = field(default_factory=dict)
    variables: dict = field(default_factory=dict)
    lists: dict = field(default_factory=dict)
    counties: list = field(default_factory=list)
    vassals: list = field(default_factory=list)
    neighbors: set = field(default_factory=set)


class ValuationWorld:
    """Small, extensible strict interpreter for the production value definitions."""

    def __init__(self, source=None, rule="scaled"):
        self.defs = {}
        for path in sorted(((source or SOURCE) / "common/script_values").glob("tnt_*.txt")):
            for key, op, body in parse(path.read_text(encoding="utf-8-sig")):
                if op != "=" or not isinstance(body, list) or key in self.defs:
                    raise Unsupported(f"Unexpected/duplicate definition {key}")
                self.defs[key] = body
        self.rule = rule
        self.root = Scope("player")
        self.scopes = {"tnt_me": self.root}
        self.previous = []
        self.evaluations = {}
        self.iterator_visits = 0

    def scope(self, atom, current):
        if atom == "root":
            return self.root
        if atom == "this":
            return current
        if atom == "prev":
            return self.previous[-1] if self.previous else None
        if atom.startswith("scope:"):
            result = self.scopes.get(atom[6:].split(".")[0])
        elif atom.startswith("var:"):
            result = current.variables.get(atom[4:].split(".")[0])
        else:
            result = current.links.get(atom.split(".")[0])
        for link in atom.split(".")[1:]:
            result = result.links.get(link) if isinstance(result, Scope) else None
        return result

    def operand(self, atom, current):
        if isinstance(atom, list):
            return self.numeric(atom, current)
        if atom in TIERS:
            return TIERS[atom]
        try:
            return D(atom)
        except Exception:
            pass
        if atom in current.stats:
            return current.stats[atom]
        if atom in self.defs:
            self.evaluations[atom] = self.evaluations.get(atom, 0) + 1
            return self.numeric(self.defs[atom], current)
        if "." in atom:
            owner, field_name = atom.rsplit(".", 1)
            target = self.scope(owner, current)
            if isinstance(target, Scope):
                return self.operand(field_name, target)
        if atom.startswith("var:") and atom[4:] in current.variables:
            return current.variables[atom[4:]]
        resolved = self.scope(atom, current)
        if resolved is not None:
            return resolved
        if atom in ("yes", "no"):
            return atom == "yes"
        raise Unsupported(f"Unknown operand {atom} in {current.name}")

    @staticmethod
    def compare(left, op, right):
        if op in ("=", "?="):
            return left == right
        if op == "!=":
            return left != right
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right
        raise Unsupported(f"Comparison {op}")

    @staticmethod
    def ancestors(current):
        seen = set()
        while current is not None:
            if current in seen:
                raise Unsupported("Cyclic de jure fixture")
            seen.add(current)
            yield current
            current = current.links.get("de_jure_liege")

    def condition(self, nodes, current):
        results, index = [], 0
        while index < len(nodes):
            key, op, body = nodes[index]
            index += 1
            if results and not results[-1]:
                return False
            if key == "trigger_if":
                chain = [(key, op, body)]
                while index < len(nodes) and nodes[index][0] in ("trigger_else_if", "trigger_else"):
                    chain.append(nodes[index]); index += 1
                result = True
                for branch, _, branch_body in chain:
                    if branch == "trigger_else" or self.condition(one(branch_body, "limit", []), current):
                        result = self.condition([row for row in branch_body if row[0] != "limit"], current)
                        break
                results.append(result)
            elif key in ("AND", "OR", "NOT", "NOR"):
                rows = (self.condition([row], current) for row in body)
                if key == "AND": results.append(all(rows))
                elif key == "OR": results.append(any(rows))
                elif key == "NOT": results.append(not all(rows))
                elif key == "NOR": results.append(not any(rows))
            elif key == "exists":
                if body.startswith("var:") and "." not in body:
                    results.append(body[4:] in current.variables)
                else:
                    results.append(self.scope(body, current) is not None)
            elif key == "has_variable_list":
                results.append(body in current.lists)
            elif key == "has_game_rule":
                results.append(body == f"tnt_advanced_valuation_{self.rule}")
            elif key == "always":
                results.append(body == "yes")
            elif key == "character_is_land_realm_neighbor":
                results.append(self.scope(body, current) in current.neighbors)
            elif key == "target_is_de_jure_liege_or_above":
                results.append(self.scope(body, current) in tuple(self.ancestors(current)))
            elif key == "any_this_title_or_de_jure_above":
                results.append(any(self.condition(body, title) for title in self.ancestors(current)))
            elif isinstance(body, list):
                target = self.scope(key, current)
                if target is None and op != "?=":
                    raise Unsupported(f"Missing trigger scope {key}")
                results.append(target is not None and self.condition(body, target))
            elif op == "?=" and self.scope(key, current) is None:
                results.append(False)
            else:
                results.append(self.compare(self.operand(key, current), op,
                                            self.operand(body, current)))
        return all(results)

    def subrealm_counties(self, character):
        """Native iterator fixture: owned counties plus all descendant vassals."""
        seen_characters, seen_counties = set(), set()
        pending = [character]
        while pending:
            ruler = pending.pop()
            if ruler in seen_characters:
                raise Unsupported("Cyclic/duplicate vassal fixture")
            seen_characters.add(ruler)
            pending.extend(ruler.vassals)
            for county in ruler.counties:
                if county not in seen_counties:
                    seen_counties.add(county)
                    yield county

    def numeric(self, nodes, current, initial=D(0)):
        value, i = initial, 0
        while i < len(nodes):
            key, op, body = nodes[i]
            i += 1
            if key == "if":
                chain = [(key, op, body)]
                while i < len(nodes) and nodes[i][0] in ("else_if", "else"):
                    chain.append(nodes[i]); i += 1
                for branch, _, branch_body in chain:
                    if branch == "else" or self.condition(one(branch_body, "limit", []), current):
                        value = self.numeric(branch_body, current, value)
                        break
            elif key == "limit":
                # The branch/iterator driver explicitly evaluated this guard.
                continue
            elif key in ("value", "add", "subtract", "multiply", "divide", "min", "max"):
                number = self.operand(body, current)
                if not isinstance(number, D):
                    number = D(number)
                if key == "value": value = number
                elif key == "add": value += number
                elif key == "subtract": value -= number
                elif key == "multiply": value *= number
                elif key == "divide": value /= number
                elif key == "min": value = max(value, number)
                elif key == "max": value = min(value, number)
            elif key in ("round", "floor") and body == "yes":
                value = value.to_integral_value(rounding=ROUND_HALF_UP if key == "round" else ROUND_FLOOR)
            elif key == "save_temporary_scope_as":
                self.scopes[body] = current
            elif key in ("every_sub_realm_county", "every_in_list"):
                if key == "every_sub_realm_county":
                    targets = self.subrealm_counties(current)
                    inner = body
                else:
                    targets = current.lists[one(body, "variable")]
                    inner = [row for row in body if row[0] != "variable"]
                for target in targets:
                    self.iterator_visits += 1
                    if self.condition(one(inner, "limit", []), target):
                        self.previous.append(current)
                        try:
                            value = self.numeric(inner, target, value)
                        finally:
                            self.previous.pop()
            elif isinstance(body, list):
                target = self.scope(key, current)
                if target is None and op != "?=":
                    raise Unsupported(f"Missing numeric scope {key}")
                if target is not None:
                    self.previous.append(current)
                    try:
                        value = self.numeric(body, target, value)
                    finally:
                        self.previous.pop()
            else:
                raise Unsupported(f"Unsupported numeric operation {(key, op, body)}")
        return value

    def value(self, name, current=None):
        return self.operand(name, current or self.root)


def realm(world, name, count, development=0, tier="tier_duchy", nested=False):
    ruler = Scope(name, stats={"highest_held_title_tier": TIERS[tier], "realm_size": D(count * 3),
                               "gold": D(100000)})
    primary = Scope(name + "_primary", "title", {"tier": TIERS[tier]})
    ruler.links["primary_title"] = primary
    if nested:
        child = Scope(name + "_child")
        grandchild = Scope(name + "_grandchild")
        ruler.vassals.append(child)
        child.vassals.append(grandchild)
        holders = [ruler, child, grandchild]
    else:
        holders = [ruler]
    for index in range(count):
        owner = holders[index % len(holders)]
        county = Scope(f"{name}_county_{index}", "title",
                       {"tier": TIERS["tier_county"], "development_level": D(development)},
                       {"holder": owner})
        owner.counties.append(county)
    return ruler


def classic_ast(nodes):
    """Remove only exact new Scaled-only branches; keep every other AST token."""
    result, index = [], 0
    marker = [("tnt_scaled_valuation_enabled_value", ">", "0")]
    while index < len(nodes):
        key, op, body = nodes[index]
        index += 1
        if key in ("if", "trigger_if") and isinstance(body, list) and one(body, "limit") == marker:
            prefix = "trigger_" if key == "trigger_if" else ""
            if index < len(nodes) and nodes[index][0] == prefix + "else":
                result.extend(classic_ast(nodes[index][2])); index += 1
            elif index < len(nodes) and nodes[index][0] == prefix + "else_if":
                result.append((prefix + "if", nodes[index][1], classic_ast(nodes[index][2]))); index += 1
            continue
        result.append((key, op, classic_ast(body) if isinstance(body, list) else body))
    return result


class ScaledValuationTests(unittest.TestCase):
    def world(self, rule="scaled"):
        return ValuationWorld(rule=rule)

    def table(self, world, count=12, development=20):
        player = realm(world, "player", count, development, nested=True)
        partner = realm(world, "partner", count, development, nested=True)
        world.root = player
        world.scopes.update(tnt_me=player, tnt_p=partner, actor=player, recipient=partner)
        player.variables["tnt_partner"] = partner
        return player, partner

    def test_rule_absent_and_classic_are_not_scaled(self):
        for setting, expected in ((None, 0), ("classic", 0), ("scaled", 1)):
            self.assertEqual(self.world(setting).value("tnt_scaled_valuation_enabled_value"), expected)

    def test_nested_actual_counties_and_development_no_low_cap(self):
        for count in (1, 12, 100):
            for development in (0, 20):
                with self.subTest(count=count, development=development):
                    world = self.world()
                    ruler = realm(world, "duke", count, development, nested=True)
                    self.assertEqual(world.value("tnt_scaled_realm_land_value", ruler),
                                     count * (20 + development / 2) + 20)
                    self.assertEqual(world.iterator_visits, count)
                    self.assertEqual(world.evaluations["tnt_scaled_county_land_value"], count)

    def test_scope_does_not_include_lieges_realm_or_neighbors(self):
        world = self.world()
        ruler = realm(world, "duke", 12, 0, nested=True)
        liege = realm(world, "emperor", 100, 20, tier="tier_empire")
        liege.vassals.append(ruler)
        ruler.links["liege"] = liege
        ruler.neighbors.add(realm(world, "neighbor", 100, 20))
        self.assertEqual(world.value("tnt_scaled_realm_land_value", ruler), 260)

    def test_primary_rank_once_secondary_empty_titles_irrelevant(self):
        for tier, premium in (("tier_county", 0), ("tier_duchy", 20),
                              ("tier_kingdom", 40), ("tier_empire", 60), ("tier_hegemony", 80)):
            world = self.world()
            ruler = realm(world, "ruler", 12, 20, tier=tier, nested=True)
            before = world.value("tnt_scaled_realm_land_value", ruler)
            ruler.lists["held_titles"] = [Scope(f"empty_{i}", "title", {"tier": TIERS["tier_duchy"]})
                                          for i in range(20)]
            self.assertEqual(before, 360 + premium)
            self.assertEqual(world.value("tnt_scaled_realm_land_value", ruler), before)

    def test_county_price_does_not_include_untransferred_de_jure_land(self):
        world = self.world()
        ruler = realm(world, "duke", 12, 20, nested=True)
        county = ruler.counties[0]
        county.links["de_jure_liege"] = ruler.links["primary_title"]
        self.assertEqual(world.value("tnt_scaled_county_land_value", county), 30)
        self.assertEqual(world.value("tnt_scaled_county_land_value", ruler.links["primary_title"]), 0)

    def test_fealty_current_character_and_volunteer_direction(self):
        world = self.world()
        player, partner = self.table(world)
        player.variables.update(tnt_vassal_p=D(1), tnt_vassal_r=D(1))
        self.assertEqual(world.value("tnt_val_vassal_p_value"), 430)
        self.assertEqual(world.value("tnt_val_vassal_r_value"), 480)
        for archetype in (14, 20):
            player.variables["tnt_ai_offer_arch"] = D(archetype)
            self.assertEqual(world.value("tnt_val_vassal_r_value"), 430)
        player.variables["tnt_ai_offer_arch"] = D(1)
        self.assertEqual(world.value("tnt_val_vassal_r_value"), 480)

    def test_default_classic_fealty_caps_unchanged(self):
        for rule in (None, "classic"):
            world = self.world(rule)
            player, _ = self.table(world, count=100)
            player.variables.update(tnt_vassal_p=D(1), tnt_vassal_r=D(1))
            self.assertEqual(world.value("tnt_val_vassal_p_value"), 200)
            self.assertEqual(world.value("tnt_val_vassal_r_value"), 250)

    def test_single_and_multiselect_county_use_same_actual_value(self):
        for direction in ("p", "r"):
            world = self.world()
            player, partner = self.table(world, development=40)
            giver = player if direction == "p" else partner
            county = giver.counties[0]
            player.variables["tnt_title_" + direction] = county
            player.lists["tnt_sel_title_" + direction] = [county]
            self.assertEqual(world.value("tnt_val_title_" + direction + "_value"), 40)
            self.assertEqual(world.value("tnt_val_title_multi_" + direction + "_value"), 40)
            player.lists["tnt_sel_title_" + direction].append(giver.counties[1])
            self.assertEqual(world.value("tnt_val_title_multi_" + direction + "_value"), 80)

    def test_world_title_and_fealty_share_scaled_asset_prices(self):
        world = self.world()
        player, partner = self.table(world, development=40)
        county = partner.counties[0]
        county.links["de_jure_liege"] = player.links["primary_title"]
        world.scopes["tnt_deal_title"] = county
        self.assertEqual(world.value("tnt_ai_title_points_value"),
                         world.value("tnt_scaled_county_land_value", county))
        self.assertEqual(world.value("tnt_ai_vassal_cost_value"),
                         world.value("tnt_scaled_fealty_demand_value", partner))
        self.assertEqual(world.value("tnt_ai_vassal_gold_value"), 600 * 15)
        self.assertEqual(world.value("tnt_ai_vassal_gold_points_value"), 600)

    def test_full_classic_ast_matches_pinned_120_baseline(self):
        repo = SOURCE.parent.parent
        for filename in ("script_values/tnt_50_values.txt", "script_values/tnt_54_multiselect_values.txt",
                         "scripted_effects/tnt_39_autobalance.txt"):
            path = SOURCE / "common" / filename
            relative = path.relative_to(repo).as_posix()
            old = subprocess.check_output(["git", "show", f"{CLASSIC_BASELINE}:{relative}"], cwd=repo)
            old_ast = parse(old.decode("utf-8-sig"))
            live_ast = parse(path.read_text(encoding="utf-8-sig"))
            self.assertEqual(classic_ast(live_ast), old_ast, filename)

    def test_scaled_solver_budgets_bound_actual_county_and_fealty_prices(self):
        world = self.world()
        player, partner = self.table(world, count=100, development=100)
        county = partner.counties[0]
        player.variables.update(tnt_vassal_r=D(1), tnt_title_r=county)
        player.lists["tnt_sel_title_r"] = [county]
        # Exercise all three existing contextual multipliers simultaneously.
        county.links["de_jure_liege"] = player.links["primary_title"]
        player.links["primary_title"].links["holder"] = player
        culture = Scope("shared_culture", "culture")
        player.links["culture"] = culture
        county.links["title_province"] = Scope("province", "province", links={"culture": culture})
        player.neighbors.add(partner)
        self.assertEqual(world.value("tnt_val_title_multi_r_value"), D(147))
        self.assertEqual(world.value("tnt_scaled_ab_county_budget_value", county), D(149))
        self.assertEqual(world.value("tnt_val_vassal_r_value"), D(7120))
        self.assertEqual(world.value("tnt_scaled_ab_fealty_budget_value"), D(7122))

    def test_actual_solver_fit_gates_reject_below_and_accept_at_scaled_budget(self):
        effects = dict((key, body) for key, _, body in parse(
            (SOURCE / "common/scripted_effects/tnt_39_autobalance.txt").read_text(encoding="utf-8-sig")))

        def find_chain(nodes, required_reference):
            for index, (key, _, body) in enumerate(nodes):
                if key == "trigger_if" and required_reference in str(body):
                    end = index + 1
                    while end < len(nodes) and nodes[end][0] in ("trigger_else_if", "trigger_else"):
                        end += 1
                    return nodes[index:end]
                if isinstance(body, list):
                    found = find_chain(body, required_reference)
                    if found:
                        return found
            return None

        for effect, reference, expected_scaled, expected_classic in (
            ("tnt_ab_lumpy_vassal_r_effect", "tnt_scaled_ab_fealty_budget_value", D(482), D(252)),
            ("tnt_ab_lumpy_title_r_effect", "tnt_scaled_ab_county_budget_value", D(65), D(65)),
        ):
            chain = find_chain(effects[effect], reference)
            self.assertIsNotNone(chain)
            for rule, bound in (("scaled", expected_scaled), ("classic", expected_classic), (None, expected_classic)):
                world = self.world(rule)
                player, partner = self.table(world)
                world.scopes["tnt_picked"] = partner.counties[0]
                for offset, accepted in ((D(-1), False), (D(0), True), (D(1), True)):
                    player.variables["tnt_ab_snap"] = bound + offset
                    self.assertEqual(world.condition(chain, player), accepted,
                                     (effect, rule, bound + offset))

    def test_scaled_prices_reach_manual_and_ai_currency_solver_without_ceiling(self):
        # Couple real territorial AST output to the existing currency solver's
        # explicit noncurrency input seam. Selection/native character facts stay
        # fixtures; no constant expected price substitutes for the land formula.
        from test_autobalance import World
        for counties in (1, 12, 100):
            valuation = self.world()
            subject = realm(valuation, "subject", counties, development=10, tier="tier_duchy")
            price = valuation.value("tnt_scaled_fealty_demand_value", subject)
            for ai in (False, True):
                funded = World(SOURCE, opinion=0, traits=(), lumpy_r=price,
                               player=(100000, 0, 0, 0), partner=(0, 0, 0, 0),
                               prestige=False, piety=False)
                result = funded.press(ai=ai)
                self.assertEqual(result["score"], 1)
                self.assertEqual(result["loss"], float(price))
                self.assertGreater(result["amounts"]["gold_p"], float(price))
                if counties == 100:
                    self.assertGreater(result["amounts"]["gold_p"], 1200)
                self.assertTrue(all(amount == 0 for lane, amount in result["amounts"].items()
                                    if lane != "gold_p"))
                poor = World(SOURCE, opinion=0, traits=(), lumpy_r=price,
                             player=(0, 0, 2000, 0), partner=(0, 0, 0, 0),
                             prestige=False, piety=True)
                result = poor.press(ai=ai)
                if counties >= 12:
                    self.assertLessEqual(result["score"], 0)
                    if not ai:  # Hidden AI solver does not write the UI verdict.
                        self.assertEqual(result["state"], 3)
                self.assertEqual(result["loss"], float(price))

    def test_unknown_executed_syntax_fails(self):
        world = self.world()
        world.defs["bad"] = [("silently_ignore_me", "=", "yes")]
        with self.assertRaises(Unsupported):
            world.value("bad")
        with self.assertRaises(Unsupported):
            world.condition([("unknown_trigger", "=", "yes")], world.root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args, remaining = parser.parse_known_args()
    SOURCE = args.source.resolve()
    unittest.main(argv=[__file__, *remaining], verbosity=2)
