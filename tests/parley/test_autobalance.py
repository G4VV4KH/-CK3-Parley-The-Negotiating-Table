"""Execute the shipped balancer's script AST against deterministic world fixtures.

This is a constrained CK3-script interpreter, not a CK3 runtime replacement. It
reads the actual effects, currency valuations, aggregates and acceptance formula.
Non-currency prices and relationship inputs are explicit fixture leaves. Selection
sorting and lumpy acquisition are explicit no-op mocks (fixtures have no eligible
lumpy inventory). Unknown executed syntax raises; no blanket ignored commands.
Decimal arithmetic and half-away rounding are approximations pending engine smoke.

Run: python tests/parley/test_autobalance.py --source mod/parley --witness out.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import unittest
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR
from pathlib import Path

D = Decimal
CURRENCIES = ("gold", "prestige", "piety", "influence")
DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "mod" / "parley"
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\#[^\r\n]*|\?=|>=|<=|!=|[{}=<>]|[^\s{}=<>#]+')


def parse(text):
    tokens = [m.group() for m in TOKEN.finditer(text.lstrip("\ufeff")) if not m.group().startswith("#")]
    pos = 0

    def block(nested=False):
        nonlocal pos
        result = []
        while pos < len(tokens):
            if tokens[pos] == "}":
                if not nested:
                    raise ValueError("unmatched closing brace")
                pos += 1
                return result
            key = tokens[pos]
            pos += 1
            if pos >= len(tokens) or tokens[pos] not in ("=", "?=", ">", "<", ">=", "<=", "!="):
                result.append((key, None, None))
                continue
            op = tokens[pos]
            pos += 1
            if tokens[pos] == "{":
                pos += 1
                value = block(True)
            else:
                value = tokens[pos].strip('"')
                pos += 1
            result.append((key, op, value))
        if nested:
            raise ValueError("unclosed block")
        return result

    return block()


def one(block, name, default=None):
    values = [v for k, op, v in block if k == name]
    if len(values) > 1:
        raise ValueError(f"duplicate singleton {name}")
    return values[0] if values else default


class Unsupported(RuntimeError):
    pass


class World:
    _cache = {}

    def __init__(self, source=DEFAULT_SOURCE, *, opinion=64, lumpy_p=0, lumpy_r=130,
                 traits=("arrogant",), player=(875, 2567, 1800, 0),
                 partner=(70, 2000, 1000, 0), prestige=True, piety=True,
                 influence=False, tier_p=4, tier_r=3, threshold=0):
        self.source = Path(source)
        self.defs = {}
        self.hashes = {}
        files = [self.source / "common/scripted_effects/tnt_39_autobalance.txt"]
        files += sorted((self.source / "common/script_values").glob("tnt_*.txt"))
        signature = tuple((str(f), f.stat().st_mtime_ns, f.stat().st_size) for f in files)
        if signature in self._cache:
            self.defs, self.hashes = self._cache[signature]
        else:
            for file in files:
                self.hashes[file.relative_to(self.source).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
                for key, op, value in parse(file.read_text(encoding="utf-8-sig")):
                    if op != "=" or not isinstance(value, list):
                        raise Unsupported(f"unexpected top level {key}")
                    if key in self.defs:
                        raise Unsupported(f"duplicate definition {key}")
                    self.defs[key] = value
            self._cache[signature] = self.defs, self.hashes
        self.vars = {"tnt_partner": "r"}
        self.scopes = {"tnt_p": "r", "tnt_me": "p"}
        self.stats = {side: {c: D(str(v)) for c, v in zip(CURRENCIES, wallet)}
                      for side, wallet in (("p", player), ("r", partner))}
        self.stats["p"]["highest_held_title_tier"] = D(tier_p)
        self.stats["r"]["highest_held_title_tier"] = D(tier_r)
        self.traits = {"p": set(), "r": set(traits)}
        self.rules = {"prestige": prestige, "piety": piety}
        self.influence = influence
        self.governments = {"p": influence, "r": influence}
        if influence:
            self.vars.update(tnt_infl_ok_p=D(1), tnt_infl_ok_r=D(1))
        self.params = {}
        self.steps = 0
        self.value_evaluations = {}
        self.mock_calls = []
        self.leaves = {
            "tnt_relmod_opinion_value": D(str(opinion)),
            "tnt_relmod_faith_value": D(0), "tnt_relmod_culture_value": D(0),
            "tnt_relmod_kin_value": D(0), "tnt_relmod_relation_value": D(0),
            "tnt_relmod_war_value": D(0), "tnt_relmod_ally_value": D(0),
            "tnt_threshold_value": D(str(threshold)),
            "tnt_gold_per_point_value": D(15 if tier_r >= 3 else 10),
            "tnt_val_threat_p_value": D(0), "tnt_val_usehook_p_value": D(0),
            "tnt_val_usehook_r_value": D(0),
        }
        # Every omitted noncurrency valuation is named explicitly by a source
        # aggregate member. There is no fallback for unknown scripted values.
        for aggregate in ("tnt_gain_total_value", "tnt_loss_total_value"):
            for key, op, name in self.defs[aggregate]:
                if key == "add" and not re.fullmatch(r"tnt_val_(gold|prestige|piety|influence)_[pr]_value", name):
                    self.leaves[name] = D(0)
        self.leaves["tnt_val_vassal_p_value"] = D(str(lumpy_p))
        self.leaves["tnt_val_vassal_r_value"] = D(str(lumpy_r))
        # Pure trade delta is an independent aggregate identity. The rendered
        # breakdown repeats selection predicates unavailable in fixture worlds.
        self.leaves["tnt_balance_value"] = lambda: self.value("tnt_gain_total_value") - self.value("tnt_loss_total_value")

    def expand(self, token):
        if not isinstance(token, str):
            return token
        return re.sub(r"\$([A-Za-z0-9_]+)\$", lambda m: str(self.params[m.group(1)]), token)

    def scope(self, token, current="p"):
        token = self.expand(token)
        if token == "root":
            return "p"
        if token.startswith("scope:"):
            return self.scopes.get(token[6:])
        if token.startswith("var:"):
            value = self.vars.get(token[4:])
            return value if value in ("p", "r") else None
        return None

    def value(self, item, current="p"):
        if isinstance(item, list):
            return self.numeric(item, current)
        item = self.expand(item)
        try:
            return D(item)
        except Exception:
            pass
        if item.startswith("var:"):
            name = item[4:]
            if name not in self.vars:
                raise Unsupported(f"read absent variable {name}")
            return D(self.vars[name])
        if item in self.stats[current]:
            return self.stats[current][item]
        if "." in item:
            prefix, field = item.rsplit(".", 1)
            target = self.scope(prefix, current)
            if target and field in self.stats[target]:
                return self.stats[target][field]
        if item in self.leaves:
            leaf = self.leaves[item]
            return leaf() if callable(leaf) else leaf
        if item in self.defs:
            self.value_evaluations[item] = self.value_evaluations.get(item, 0) + 1
            return self.numeric(self.defs[item], current)
        raise Unsupported(f"numeric operand {item}")

    def branch(self, block, i, current, mode, acc=D(0)):
        while i < len(block) and block[i][0] in ("if", "else_if", "else"):
            key, op, body = block[i]
            i += 1
            if key == "else" or self.trigger(one(body, "limit", []), current):
                if mode == "numeric":
                    acc = self.numeric(body, current, acc)
                else:
                    self.effect_block(body, current)
                while i < len(block) and block[i][0] in ("else_if", "else"):
                    i += 1
                break
        return i, acc

    def numeric(self, block, current="p", acc=D(0)):
        i = 0
        while i < len(block):
            key, op, val = block[i]
            key = self.expand(key)
            if key == "if":
                i, acc = self.branch(block, i, current, "numeric", acc)
                continue
            i += 1
            if key in ("limit", "desc"):
                continue
            if key == "save_temporary_scope_as":
                self.scopes[self.expand(val)] = current
                continue
            if isinstance(val, list) and (key == "root" or key.startswith(("scope:", "var:"))):
                target = self.scope(key, current)
                if target is None:
                    if op == "?=":
                        continue
                    raise Unsupported(f"missing numeric scope {key}")
                acc = self.numeric(val, target, acc)
                continue
            if key in ("round", "floor", "ceiling"):
                if val != "yes":
                    raise Unsupported(f"{key} {val}")
                rounding = ROUND_HALF_UP if key == "round" else (ROUND_FLOOR if key == "floor" else "ROUND_CEILING")
                acc = acc.to_integral_value(rounding=rounding)
                continue
            if key not in ("value", "add", "subtract", "multiply", "divide", "min", "max"):
                raise Unsupported(f"numeric command {key}")
            v = self.value(val, current)
            if key == "value": acc = v
            elif key == "add": acc += v
            elif key == "subtract": acc -= v
            elif key == "multiply": acc *= v
            elif key == "divide": acc /= v
            elif key == "min": acc = max(acc, v)
            elif key == "max": acc = min(acc, v)
        return acc

    def exists(self, name, current):
        name = self.expand(name)
        if name.startswith("var:"):
            return name[4:] in self.vars
        if name.startswith("scope:"):
            return name[6:] in self.scopes
        raise Unsupported(f"exists operand {name}")

    def trigger(self, block, current="p"):
        return all(self.condition(k, op, v, current) for k, op, v in block)

    def condition(self, key, op, val, current):
        key = self.expand(key)
        if key == "NOT": return not self.trigger(val, current)
        if key == "OR": return any(self.condition(k, o, v, current) for k, o, v in val)
        if key == "AND": return self.trigger(val, current)
        if key == "NOR": return not any(self.condition(k, o, v, current) for k, o, v in val)
        if key == "exists": return self.exists(val, current)
        if key == "always": return val == "yes"
        if key == "has_trait": return val in self.traits[current]
        if key == "government_has_flag":
            if val != "government_has_influence": raise Unsupported(f"government flag {val}")
            return self.governments[current]
        if key in ("tnt_trade_prestige_trigger", "tnt_trade_piety_trigger"):
            return self.rules[key.split("_")[2]]
        if key == "trigger_if":
            condition = self.trigger(one(val, "limit", []), current)
            return not condition or self.trigger([x for x in val if x[0] != "limit"], current)
        if isinstance(val, list) and (key == "root" or key.startswith(("scope:", "var:"))):
            target = self.scope(key, current)
            if target is None:
                if op == "?=": return False
                raise Unsupported(f"missing trigger scope {key}")
            return self.trigger(val, target)
        if isinstance(val, list): raise Unsupported(f"trigger block {key}")
        # Nonexistent variables in a comparison fail, unlike numeric reads.
        if key.startswith("var:") and key[4:] not in self.vars:
            return False
        a, b = self.value(key, current), self.value(val, current)
        if op == "=": return a == b
        if op == "!=": return a != b
        if op == ">": return a > b
        if op == "<": return a < b
        if op == ">=": return a >= b
        if op == "<=": return a <= b
        raise Unsupported(f"trigger operator {op}")

    def effect(self, name, params=None, current="p"):
        name = self.expand(name)
        if name in ("tnt_sort_all_effect", "tnt_ab_lumpy_r_effect"):
            self.mock_calls.append(name)
            return
        if name not in self.defs: raise Unsupported(f"effect {name}")
        previous = self.params
        self.params = {**previous, **(params or {})}
        try:
            self.effect_block(self.defs[name], current)
        finally:
            self.params = previous

    def effect_block(self, block, current="p"):
        i = 0
        while i < len(block):
            self.steps += 1
            if self.steps > 1000000: raise Unsupported("execution step budget exceeded")
            key, op, val = block[i]
            key = self.expand(key)
            if key == "if":
                i, _ = self.branch(block, i, current, "effect")
                continue
            i += 1
            if key in ("limit", "count"): continue
            if key == "set_variable":
                self.vars[self.expand(one(val, "name"))] = self.value(one(val, "value"), current)
            elif key == "change_variable":
                name = self.expand(one(val, "name"))
                self.vars[name] = D(self.vars.get(name, 0)) + self.value(one(val, "add", one(val, "value")), current)
            elif key == "remove_variable": self.vars.pop(self.expand(val), None)
            elif key == "save_temporary_scope_as": self.scopes[self.expand(val)] = current
            elif key == "while":
                count = int(self.value(one(val, "count", "1000000"), current))
                if count < 0 or count > 100000: raise Unsupported(f"unsafe while count {count}")
                for _ in range(count):
                    if not self.trigger(one(val, "limit", []), current): break
                    self.effect_block(val, current)
                else:
                    if one(val, "count") is None and self.trigger(one(val, "limit", []), current):
                        raise Unsupported("unbounded while")
            elif isinstance(val, list) and (key == "root" or key.startswith(("scope:", "var:"))):
                target = self.scope(key, current)
                if target is None:
                    if op == "?=": continue
                    raise Unsupported(f"missing effect scope {key}")
                self.effect_block(val, target)
            elif key.endswith("_effect"):
                params = {k: self.expand(v) for k, o, v in val} if isinstance(val, list) else None
                self.effect(key, params, current)
            else: raise Unsupported(f"effect command {key}")

    def press(self, ai=False):
        self.effect("tnt_ai_pricebalance_effect" if ai else "tnt_autobalance_effect", {"MARGIN": 1, "CEILING": 1})
        return self.snapshot()

    def snapshot(self):
        return {"score": float(self.value("tnt_ai_accept_value")),
                "amounts": {f"{c}_{s}": float(self.vars.get(f"tnt_{c}_{s}", 0)) for c in CURRENCIES for s in ("p", "r")},
                "state": float(self.vars.get("tnt_ab_state", 0)),
                "gain": float(self.value("tnt_gain_total_value")),
                "loss": float(self.value("tnt_loss_total_value")),
                "steps": self.steps,
                "acceptance_evaluations": self.value_evaluations.get("tnt_ai_accept_value", 0)}

    def independent_score(self):
        """A separate arithmetic oracle, not any balancer code or helper value."""
        tier_sum = self.stats["p"]["highest_held_title_tier"] + self.stats["r"]["highest_held_title_tier"]
        prices = {"gold": self.leaves["tnt_gold_per_point_value"],
                  "prestige": max(D(10), D("7.5") + D("1.25") * tier_sum),
                  "piety": max(D("7.5"), D(5) + D("1.25") * tier_sum),
                  "influence": max(D("7.5"), D(5) + D("1.25") * tier_sum)}
        traits = self.traits["r"]
        riders = {"gold": D(1),
                  "prestige": D("1.5") if "arrogant" in traits else D("0.5") if "humble" in traits else D(1),
                  "piety": D("1.5") if "zealous" in traits else D(1),
                  "influence": D("1.5") if "ambitious" in traits else D("0.5") if "content" in traits else D(1)}
        def rounded(value): return value.to_integral_value(rounding=ROUND_HALF_UP)
        totals = {}
        for side in ("p", "r"):
            total = self.leaves[f"tnt_val_vassal_{side}_value"]
            for currency in CURRENCIES:
                if currency == "influence" and not (self.vars.get("tnt_infl_ok_p", 0) > 0 and self.vars.get("tnt_infl_ok_r", 0) > 0): continue
                total += D(self.vars.get(f"tnt_{currency}_{side}", 0)) / prices[currency] * riders[currency]
            totals[side] = rounded(total)
        percent = sum(self.leaves[n] for n in self.leaves if n.startswith("tnt_relmod_")) - self.leaves["tnt_threshold_value"]
        return rounded(totals["p"] - totals["r"] + max(D(0), totals["p"]) * max(D(-100), percent) / 100
                       + self.leaves["tnt_val_threat_p_value"] + self.leaves["tnt_val_usehook_p_value"]
                       + self.leaves["tnt_val_usehook_r_value"])


def witness(source):
    world = World(source)
    result = {"source": str(Path(source).resolve()), "sha256": world.hashes,
              "limits": __doc__, "fixture": {"opinion": 64, "lumpy_r": 130,
              "traits": ["arrogant"], "player": [875, 2567, 1800, 0],
              "partner": [70, 2000, 1000, 0], "tiers": [4, 3]},
              "initial": world.snapshot(), "clicks": [world.press() for _ in range(4)]}
    ai = World(source)
    result["ai_same_table"] = ai.press(ai=True)
    return result


class ScriptTests(unittest.TestCase):
    source = DEFAULT_SOURCE
    metrics = {}

    def test_unknown_executed_syntax_fails(self):
        w = World(self.source)
        with self.assertRaises(Unsupported): w.effect_block(parse("imaginary_command = yes"))
        with self.assertRaises(Unsupported): w.value("imaginary_value")

    def test_actual_formula_matches_screenshot_tables(self):
        rows = [(700, 535, 56, 0, 23), (700, 644, 56, 358, 7),
                (700, 674, 56, 456, 3), (700, 684, 56, 489, 1)]
        w = World(self.source)
        for gp, pp, gr, pr, score in rows:
            w.vars.update(tnt_gold_p=D(gp), tnt_prestige_p=D(pp), tnt_gold_r=D(gr), tnt_prestige_r=D(pr))
            self.assertEqual(w.value("tnt_ai_accept_value"), score)

    def test_fealty_single_click_has_no_return_payments_and_repeats_stably(self):
        w = World(self.source)
        first = w.press()
        self.assertEqual(first["score"], 1)
        for c in CURRENCIES:
            self.assertEqual(first["amounts"][c + "_r"], 0, c)
        second = w.press()
        self.assertEqual(second["amounts"], first["amounts"])
        self.assertEqual(second["score"], first["score"])

    def assert_invariants(self, w, result, *, caps=True):
        self.assertEqual(D(str(result["score"])), w.independent_score())
        for currency in CURRENCIES:
            p, r = (D(str(result["amounts"][currency + "_" + side])) for side in ("p", "r"))
            self.assertGreaterEqual(min(p, r), 0, currency)
            self.assertFalse(p > 0 and r > 0, f"both sides pay {currency}: {result}")
            if caps:
                for side, amount in (("p", p), ("r", r)):
                    self.assertLessEqual(amount, max(D(0), w.stats[side][currency] * D("0.8")), currency)
            if currency in w.rules and not w.rules[currency]:
                self.assertEqual(p + r, 0, f"disabled {currency}")
            if currency == "influence" and not w.influence:
                self.assertEqual(p + r, 0, "influence unavailable")
        self.assertFalse(any(name.startswith("tnt_ab_search_") for name in w.vars), "search variables leaked")
        self.assertFalse(any(name.startswith("tnt_ab_before_") for name in w.vars), "before-state variables leaked")
        self.assertNotIn("tnt_ab_margin", w.vars)
        self.assertNotIn("tnt_ab_ceiling", w.vars)

    def test_trait_wallet_rule_and_direction_matrix(self):
        traits = [(), ("arrogant",), ("humble",), ("zealous",), ("ambitious",), ("content",)]
        cases = 0
        max_acceptance = 0
        max_steps = 0
        for ai in (False, True):
            for personality in traits:
                for opinion in (-100, -50, 0, 64, 100):
                    for lane in range(4):
                        wallet = [0, 0, 0, 0]
                        wallet[lane] = 3000
                        for direction in ("deficit", "surplus"):
                            with self.subTest(ai=ai, traits=personality, opinion=opinion, lane=lane, direction=direction):
                                w = World(self.source, opinion=opinion, traits=personality,
                                          lumpy_p=80 if direction == "surplus" else 0,
                                          lumpy_r=130 if direction == "deficit" else 0,
                                          player=wallet, partner=wallet,
                                          prestige=lane == 1, piety=lane == 2, influence=lane == 3)
                                before = dict(w.leaves)
                                first = w.press(ai=ai)
                                max_acceptance = max(max_acceptance, first["acceptance_evaluations"])
                                max_steps = max(max_steps, first["steps"])
                                self.assert_invariants(w, first)
                                self.assertEqual(w.leaves, before, "selected noncurrency term changed")
                                if not ai:
                                    second = w.press()
                                    self.assertEqual(second["score"], first["score"])
                                    self.assertEqual(second["amounts"], first["amounts"])
                                cases += 1
        self.assertEqual(cases, 480)
        self.metrics["direction_trait_matrix"] = {"cases": cases, "max_acceptance_evaluations_one_press": max_acceptance,
                                                   "max_effect_statements_one_press": max_steps}

    def test_single_currency_exhaustive_minimum_oracle(self):
        # Brute force all allowed integer amounts independently of the solver's
        # search direction, convergence rules or internal target values.
        for currency in CURRENCIES:
            lane = CURRENCIES.index(currency)
            for opinion in (-100, -50, 0, 64, 100):
                for personality in ((), ("arrogant", "zealous", "ambitious"), ("humble", "content")):
                    for cost in (1, 2, 5, 15):
                        wallet = [0, 0, 0, 0]
                        wallet[lane] = 100
                        with self.subTest(currency=currency, opinion=opinion, traits=personality, cost=cost):
                            w = World(self.source, opinion=opinion, traits=personality,
                                      lumpy_r=cost, player=wallet, partner=(0, 0, 0, 0),
                                      prestige=lane == 1, piety=lane == 2, influence=lane == 3)
                            key = f"tnt_{currency}_p"
                            first_accepted = None
                            for amount in range(81):
                                w.vars[key] = D(amount)
                                if w.independent_score() >= 1:
                                    first_accepted = amount
                                    break
                            w.vars.pop(key, None)
                            result = w.press()
                            self.assert_invariants(w, result)
                            if first_accepted is not None:
                                self.assertEqual(result["amounts"][currency + "_p"], first_accepted)
                                self.assertGreaterEqual(result["score"], 1)
                            else:
                                self.assertLessEqual(result["score"], 0)
                                self.assertEqual(result["state"], 3)

    def test_existing_two_sided_currency_is_repaired(self):
        for ai in (False, True):
            for opinion in (-50, 0, 64, 100):
                with self.subTest(ai=ai, opinion=opinion):
                    w = World(self.source, opinion=opinion, player=(3000, 3000, 3000, 3000),
                              partner=(3000, 3000, 3000, 3000), influence=True)
                    for c in CURRENCIES:
                        w.vars[f"tnt_{c}_p"] = D(700)
                        w.vars[f"tnt_{c}_r"] = D(350)
                    result = w.press(ai=ai)
                    self.assert_invariants(w, result)

    def test_ai_generosity_cap_and_purchase_exception(self):
        gift = World(self.source, opinion=100, lumpy_p=50, lumpy_r=50, traits=(),
                     player=(10000, 0, 0, 0), partner=(10000, 0, 0, 0), prestige=False, piety=False)
        gift.vars["tnt_ai_offer_arch"] = D(1)
        before = gift.independent_score()
        result = gift.press(ai=True)
        self.assert_invariants(gift, result)
        self.assertGreaterEqual(result["score"], before - 25)
        self.assertGreater(result["score"], 1)
        purchase = World(self.source, opinion=100, lumpy_p=80, lumpy_r=0, traits=(),
                         player=(10000, 0, 0, 0), partner=(10000, 0, 0, 0), prestige=False, piety=False)
        purchase.vars["tnt_ai_offer_arch"] = D(8)
        result = purchase.press(ai=True)
        self.assert_invariants(purchase, result)
        self.assertEqual(result["score"], 1)

    def test_a19_arrogant_prestige_only_regression(self):
        w = World(self.source, opinion=100, lumpy_p=35, lumpy_r=0, tier_p=3, tier_r=3,
                  player=(0, 2000, 0, 0), partner=(0, 2000, 0, 0), piety=False)
        w.vars["tnt_ai_offer_arch"] = D(19)
        result = w.press(ai=True)
        self.assert_invariants(w, result)
        self.assertEqual(result["score"], 1)
        self.assertEqual(result["amounts"]["prestige_p"], 0)
        self.assertGreater(result["amounts"]["prestige_r"], 0)
        # Shared solver fixed target must be stable; this buyer has no gift cap.
        w.vars.update(tnt_ab_margin=D(1), tnt_ab_ceiling=D(1))
        w.effect("tnt_ab_solve_effect")
        w.vars.pop("tnt_ab_margin")
        w.vars.pop("tnt_ab_ceiling")
        self.assertEqual(w.snapshot()["amounts"], result["amounts"])

    def test_zero_wallets_and_signed_obligation_gain(self):
        for opinion in (-150, -100, 0, 64, 100):
            for lumpy_p in (-30, 0, 130):
                with self.subTest(opinion=opinion, lumpy_p=lumpy_p):
                    w = World(self.source, opinion=opinion, lumpy_p=lumpy_p,
                              player=(0, 0, 0, 0), partner=(0, 0, 0, 0))
                    result = w.press()
                    self.assert_invariants(w, result)
                    self.assertTrue(all(n == 0 for n in result["amounts"].values()))
                    if result["score"] <= 0: self.assertEqual(result["state"], 3)
                    elif result["score"] > 1: self.assertEqual(result["state"], 4)
                    again = w.press()
                    self.assertEqual(again["amounts"], result["amounts"])
                    self.assertEqual(again["score"], result["score"])

    def test_manual_above_reserve_is_not_increased_or_invalidated(self):
        # A manually chosen 95% of a wallet may remain; the 80% reserve limits
        # additions, not legal manual payments. Do not clamp it into refusal.
        for currency in CURRENCIES:
            lane = CURRENCIES.index(currency)
            wallet = [0, 0, 0, 0]
            wallet[lane] = 1000
            with self.subTest(currency=currency):
                w = World(self.source, opinion=0, lumpy_r=85 if currency != "gold" else 60,
                          player=wallet, partner=(0, 0, 0, 0), traits=("arrogant", "zealous", "ambitious"),
                          influence=lane == 3, prestige=lane == 1, piety=lane == 2)
                w.vars[f"tnt_{currency}_p"] = D(950)
                before = w.independent_score()
                self.assertGreater(before, 0)
                result = w.press()
                self.assert_invariants(w, result, caps=False)
                self.assertGreaterEqual(result["score"], 1)
                self.assertLessEqual(result["amounts"][currency + "_p"], 950)
                again = w.press()
                self.assertEqual(result["amounts"], again["amounts"])

    def test_accepted_fractional_manual_gold_is_preserved(self):
        # Regression: 952.5 / 15 rounds to 64, but floor(952.5) / 15 rounds
        # to 63. The old normalization made an accepted manual deal refuse,
        # then could not restore it because 80% reserve caps additions at 762.
        w = World(self.source, opinion=0, lumpy_r=63, traits=(),
                  player=(D("952.5"), 0, 0, 0), partner=(0, 0, 0, 0),
                  prestige=False, piety=False)
        w.vars["tnt_gold_p"] = D("952.5")
        self.assertEqual(w.independent_score(), 1)
        first = w.press()
        self.assert_invariants(w, first, caps=False)
        self.assertEqual(first["score"], 1)
        self.assertEqual(first["amounts"]["gold_p"], 952.5)
        second = w.press()
        self.assertEqual(second["amounts"], first["amounts"])
        self.assertEqual(second["score"], 1)
        self.assertEqual(second["state"], 2)

    def test_positive_subunit_currency_keeps_rounding_threshold(self):
        # A positive amount <1 is still part of the deal: 10.48 + .3/15
        # reaches the aggregate's 10.5 boundary. Tidy must remove only <=0.
        w = World(self.source, opinion=0, lumpy_p=D("10.48"), lumpy_r=10, traits=(),
                  player=(D("0.3"), 0, 0, 0), partner=(0, 0, 0, 0),
                  prestige=False, piety=False)
        w.vars["tnt_gold_p"] = D("0.3")
        self.assertEqual(w.independent_score(), 1)
        first = w.press()
        self.assert_invariants(w, first, caps=False)
        self.assertEqual(first["score"], 1)
        self.assertEqual(first["amounts"]["gold_p"], 0.3)
        second = w.press()
        self.assertEqual(second["amounts"], first["amounts"])
        self.assertEqual(second["score"], 1)
        self.assertEqual(second["state"], 2)

    def test_actual_influence_mirror_gate(self):
        for mirror_p in (None, 0, 1):
            for mirror_r in (None, 0, 1):
                with self.subTest(mirror_p=mirror_p, mirror_r=mirror_r):
                    w = World(self.source, opinion=0, lumpy_r=10, traits=(),
                              player=(0, 0, 0, 1000), partner=(0, 0, 0, 0),
                              prestige=False, piety=False, influence=True)
                    for side, value in (("p", mirror_p), ("r", mirror_r)):
                        w.vars.pop("tnt_infl_ok_" + side, None)
                        if value is not None: w.vars["tnt_infl_ok_" + side] = D(value)
                    enabled = mirror_p == 1 and mirror_r == 1
                    self.assertEqual(w.value("tnt_influence_ok_value"), int(enabled))
                    result = w.press()
                    self.assert_invariants(w, result)
                    if enabled:
                        self.assertGreaterEqual(result["score"], 1)
                        self.assertGreater(result["amounts"]["influence_p"], 0)
                    else:
                        self.assertEqual(result["score"], -10)
                        self.assertEqual(result["amounts"]["influence_p"], 0)
                        self.assertEqual(result["state"], 3)

    def test_seeded_random_currency_tables(self):
        rng = random.Random(20260930)
        cases = 160
        max_acceptance = 0
        max_steps = 0
        for index in range(cases):
            prestige, piety, influence = [rng.choice((False, True)) for _ in range(3)]
            personality = rng.choice(((), ("arrogant", "zealous", "ambitious"), ("humble", "content")))
            w = World(self.source, opinion=rng.choice((-150, -100, -99, -90, -50, 0, 1, 64, 100, 180)),
                      threshold=rng.choice((0, 10, 40)), traits=personality,
                      lumpy_p=rng.randint(-40, 250), lumpy_r=rng.randint(0, 250),
                      player=[rng.choice((0, 1, 10, 100, 1000, 10000)) for _ in range(4)],
                      partner=[rng.choice((0, 1, 10, 100, 1000, 10000)) for _ in range(4)],
                      prestige=prestige, piety=piety, influence=influence,
                      tier_p=rng.randint(1, 5), tier_r=rng.randint(1, 5))
            for c in CURRENCIES:
                if c in w.rules and not w.rules[c]: continue
                if c == "influence" and not influence: continue
                for side in ("p", "r"):
                    cap = int(w.stats[side][c] * D("0.8"))
                    if c == "influence": cap = min(cap, 1000)
                    w.vars[f"tnt_{c}_{side}"] = D(rng.randint(0, cap))
            with self.subTest(index=index):
                result = w.press()
                max_acceptance = max(max_acceptance, result["acceptance_evaluations"])
                max_steps = max(max_steps, result["steps"])
                self.assert_invariants(w, result)
                again = w.press()
                self.assertEqual(result["amounts"], again["amounts"])
                self.assertEqual(result["score"], again["score"])
        self.metrics["seeded_random"] = {"seed": 20260930, "cases": cases,
                                         "max_acceptance_evaluations_one_press": max_acceptance,
                                         "max_effect_statements_one_press": max_steps}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--witness", type=Path)
    parser.add_argument("--witness-only", action="store_true")
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()
    ScriptTests.source = args.source
    if args.witness:
        args.witness.parent.mkdir(parents=True, exist_ok=True)
        args.witness.write_text(json.dumps(witness(args.source), indent=2) + "\n", encoding="utf-8")
        print(f"Witness: {args.witness}")
    if not args.witness_only:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ScriptTests))
        if args.report_json:
            args.report_json.parent.mkdir(parents=True, exist_ok=True)
            report = {"tests_run": result.testsRun, "success": result.wasSuccessful(),
                      "failures": [(str(test), trace) for test, trace in result.failures],
                      "errors": [(str(test), trace) for test, trace in result.errors],
                      "metrics": ScriptTests.metrics, "source": str(args.source),
                      "source_sha256": World(args.source).hashes, "limitations": __doc__}
            args.report_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())


if __name__ == "__main__":
    main()
