"""Interest UI integration checks. Native rendering/hover remains a separate gate."""
from pathlib import Path
import re
import unittest


SOURCE = Path(__file__).resolve().parents[2] / "mod" / "parley"
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|#[^\n]*|[{}]')
GUI_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}=]|[^\s{}=#]+')


def text(path):
    return path.read_text(encoding="utf-8-sig")


def body_containing(source, name):
    start = source.index(f'name = "{name}"')
    depth = 1
    for token in TOKEN.finditer(source, start):
        if token.group() == "{":
            depth += 1
        elif token.group() == "}":
            depth -= 1
            if depth == 0:
                return source[start:token.start()]
    raise AssertionError(f"Unclosed widget {name}")


def flow_layout_violations(source, selected_types=None):
    """Guard one native layout rule, not a substitute for GUI instantiation.

    Keep widget boundaries, flatten injection blocks, and resolve type aliases.
    The native breakdown list is a widget (game/gui/shared/value_breakdown.gui),
    so its internal vbox is legal beneath a flowcontainer's widget child.
    """
    root = {"kind": "root", "children": [], "line": 0}
    stack = [(root, [])]
    definitions = {}
    for token in GUI_TOKEN.finditer(source):
        value = token.group()
        if value.startswith("#"):
            continue
        parent, pending = stack[-1]
        if value == "{":
            definition = None
            if len(pending) >= 4 and pending[-4] == "type" and pending[-2] == "=":
                definition, kind = pending[-3], pending[-1]
            elif len(pending) >= 2 and pending[-1] == "=":
                kind = pending[-2]
            elif len(pending) >= 2:
                kind = pending[-2]
            else:
                kind = "unknown"
            node = {"kind": kind, "children": [],
                    "line": source.count("\n", 0, token.start()) + 1}
            if definition:
                definitions[definition] = node
            parent["children"].append(node)
            pending.clear()
            stack.append((node, []))
        elif value == "}":
            if len(stack) == 1:
                raise AssertionError("Unmatched GUI closing brace")
            stack.pop()
            stack[-1][1].clear()
        else:
            pending.append(value)
    if len(stack) != 1:
        raise AssertionError("Unclosed GUI block")

    def base_kind(kind):
        seen = set()
        while kind in definitions:
            if kind in seen:
                raise AssertionError(f"Cyclic GUI type inheritance: {kind}")
            seen.add(kind)
            kind = definitions[kind]["kind"]
        return {"widget_value_breakdown_list": "widget"}.get(kind, kind)

    def direct_children(node):
        for child in node["children"]:
            if child["kind"] in {"block", "blockoverride", "item"}:
                yield from direct_children(child)
            else:
                yield child

    violations, visited = [], set()

    def visit(node):
        if id(node) in visited:
            return
        visited.add(id(node))
        if base_kind(node["kind"]) in {"container", "flowcontainer"}:
            for child in direct_children(node):
                if base_kind(child["kind"]) in {"hbox", "vbox"}:
                    violations.append((node["line"], child["line"], child["kind"]))
        if node["kind"] in definitions:
            visit(definitions[node["kind"]])
        for child in node["children"]:
            visit(child)

    if selected_types is None:
        visit(root)
    else:
        for name in selected_types:
            visit(definitions[name])
    return violations


class InterestUiTests(unittest.TestCase):
    def test_layout_guard_resolves_aliases_and_injection_blocks(self):
        source = '''types Test {
            type vertical = vbox {}
            type aliased_row = vertical {}
            type parent_flow = flowcontainer {}
            type second_flow = parent_flow {}
            type tooltip = second_flow {
                block "contents" { blockoverride "nested" { aliased_row = {} } }
            }
        }'''
        violations = flow_layout_violations(source, {"tooltip"})
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0][2], "aliased_row")
        self.assertEqual(len(flow_layout_violations('container = { hbox = {} }')), 1)

    def test_layout_guard_preserves_real_widget_boundaries(self):
        source = '''types Test {
            type widget_value_breakdown_list = widget { vbox = { hbox = {} } }
            type tooltip = container {
                # vbox = { } is a comment, not a direct layout child.
                flowcontainer = {
                    text_multi = { raw_text = "Quoted vbox = { }" }
                    widget_value_breakdown_list = {}
                    widget = { vbox = {} }
                    flowcontainer = { direction = vertical text_multi = {} }
                }
            }
        }'''
        self.assertEqual(flow_layout_violations(source, {"tooltip"}), [])

    def test_interest_tooltip_has_no_direct_layout_children_under_containers(self):
        source = text(SOURCE / "gui/tnt_types.gui")
        violations = flow_layout_violations(source, {"tnt_interest_tooltip"})
        self.assertEqual(violations, [],
                         "Native containers reject direct hbox/vbox children "
                         f"(parent line, child line, child type): {violations}")

    def test_native_rule_presets_and_new_campaign_default(self):
        rules = text(SOURCE / "common/game_rules/tnt_80_game_rules.txt")
        rule = re.search(r"tnt_negotiation_interests = \{(.*?)\n\}", rules, re.S).group(1)
        self.assertRegex(rule, r"default\s*=\s*tnt_interests_standard")
        self.assertEqual(set(re.findall(r"(tnt_interests_\w+)\s*=\s*\{", rule)),
                         {"tnt_interests_off", "tnt_interests_mild",
                          "tnt_interests_standard", "tnt_interests_strict"})

    def test_interest_localization_complete_without_duplicate_new_keys(self):
        locales = list((SOURCE / "localization").glob("*/*.yml"))
        self.assertEqual(len(locales), 9)
        expected = None
        for path in locales:
            keys = re.findall(r"^ ((?:tnt_interest_|rule_tnt_negotiation_interests|setting_tnt_interests_)\w*):\d+ ", text(path), re.M)
            self.assertEqual(len(keys), len(set(keys)), path)
            expected = set(keys) if expected is None else expected
            self.assertEqual(set(keys), expected, path)
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"), path)
        descriptions = set()
        for path in (SOURCE / "common/script_values").glob("*.txt"):
            descriptions.update(re.findall(r"desc\s*=\s*(tnt_interest_\w+)", text(path)))
        self.assertLessEqual(descriptions, expected)

    def test_gui_interest_script_references_resolve(self):
        definitions = set()
        for path in (SOURCE / "common/script_values").glob("*.txt"):
            definitions.update(re.findall(r"^(tnt_\w+)\s*=\s*\{", text(path), re.M))
        for path in (SOURCE / "gui").glob("*.gui"):
            refs = set(re.findall(r"Tnt(?:SV|Pos|Breakdown)\('(tnt_interest\w+)'\)", text(path)))
            self.assertFalse(refs - definitions, f"{path}: {sorted(refs - definitions)}")

    def test_changed_gui_braces_balance(self):
        for path in (SOURCE / "gui").glob("*.gui"):
            depth = 0
            for token in TOKEN.finditer(text(path)):
                if token.group() == "{":
                    depth += 1
                elif token.group() == "}":
                    depth -= 1
                    self.assertGreaterEqual(depth, 0, path)
            self.assertEqual(depth, 0, path)

    def test_pressure_does_not_inherit_interest_badges(self):
        window = text(SOURCE / "gui/tnt_diplomacy_window.gui")
        for name in ("tnt_row_threat_p", "tnt_row_usehook_p", "tnt_row_usehook_r"):
            self.assertNotIn('blockoverride "tnt_row_interest"', body_containing(window, name))
        types = text(SOURCE / "gui/tnt_types.gui")
        self.assertIn('block "tnt_interest_state" { visible = no }', types)
        self.assertIn('visible = "[TntPos(\'tnt_interests_enabled_value\')]"', types)

    def test_native_gui_text_escapes_and_composite_interest_labels(self):
        # The native smoke rejects single-backslash newlines in GUI strings and
        # treats a percentage outside the data expression as a localization key.
        for name in ("tnt_diplomacy_window.gui", "tnt_panel_contract.gui"):
            source = text(SOURCE / "gui" / name)
            for token in TOKEN.finditer(source):
                if token.group().startswith('"'):
                    self.assertNotRegex(token.group(), r'(?<!\\)(?:\\\\)*\\[^"\\]', name)
            badges = [line for line in source.splitlines()
                      if 'blockoverride "tnt_interest_value"' in line]
            expected = 26 if name == "tnt_diplomacy_window.gui" else 9
            self.assertEqual(len(badges), expected)
            self.assertTrue(all(' raw_text = "' in line for line in badges), name)
            for field in ("effective", "base", "adjusted"):
                rows = [line for line in source.splitlines()
                        if f'blockoverride "tnt_interest_points_{field}"' in line]
                self.assertEqual(len(rows), expected)
                self.assertTrue(all(' raw_text = "' in line for line in rows), name)

    def test_badges_distinguish_receive_surrender_and_unselected_terms(self):
        window = text(SOURCE / "gui/tnt_diplomacy_window.gui")
        for term in ("gold", "prestige", "piety", "influence", "title", "artifact",
                     "hook", "vassal", "indep", "hostage", "courtier", "subject"):
            for side, direction in (("p", "receive"), ("r", "surrender")):
                row = body_containing(window, f"tnt_row_{term}_{side}")
                self.assertIn(f'text = "tnt_interest_{direction}"', row)
                self.assertIn('blockoverride "tnt_interest_value"', row)
                self.assertIn('blockoverride "tnt_interest_preview_breakdown"', row)
                self.assertIn(f"TntBreakdown('tnt_interest_{term}_{side}_percent_value')", row)

    def test_currency_hover_separates_native_resource_units_from_percent_reasons(self):
        window = text(SOURCE / "gui/tnt_diplomacy_window.gui")
        for term in ("gold", "prestige", "piety", "influence"):
            for side in ("p", "r"):
                row = body_containing(window, f"tnt_row_{term}_{side}")
                self.assertIn('blockoverride "tnt_interest_capacity_state" { visible = yes }', row)
                self.assertIn(f"TntBreakdown('tnt_interest_{term}_capacity_value')", row)
                self.assertIn(f"TntSV('tnt_interest_{term}_stock_value')", row)
                self.assertIn("Localize('tnt_interest_capacity_target')", row)
                self.assertIn("Localize('tnt_interest_current_stock')", row)
                self.assertIn(f"TntBreakdown('tnt_interest_{term}_{side}_percent_value')", row)
        self.assertEqual(window.count('blockoverride "tnt_interest_capacity_state"'), 8)
        types = text(SOURCE / "gui/tnt_types.gui")
        self.assertIn('block "tnt_interest_capacity_state" { visible = no }', types)
        self.assertIn('text = "tnt_interest_capacity_note"', types)


if __name__ == "__main__":
    unittest.main()
