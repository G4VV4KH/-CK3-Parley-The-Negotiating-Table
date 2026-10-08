"""Static guards for the revised interest UI; not rendered-layout acceptance.

All 35 badges are fixed-width. The second-line/64px layout contract applies to
the 24 normal side rows; wider contract rows and the mutual marriage action keep
their separate layouts. Native visibility, localization and hover need CK3.
"""
from collections import Counter
import re
import unittest

from test_autobalance import parse
from test_interest_ui import SOURCE, TOKEN, body_containing, text


SIDE_TERMS = ("gold", "prestige", "piety", "influence", "title", "subject",
              "courtier", "artifact", "vassal", "indep", "hostage", "hook", "marriage")
CONTRACTS = ("tax", "levy", "fort", "coin", "relig", "council", "revoke", "war", "succ")
BADGES = {f"tnt_interest_{term}_{side}" for term in SIDE_TERMS for side in ("p", "r")}
BADGES |= {"tnt_interest_ob_" + term for term in CONTRACTS}


def clean(source):
    return TOKEN.sub(lambda match: "" if match.group().startswith("#") else match.group(), source)


def blocks(source, header):
    """Extract balanced native blocks without treating quoted braces as layout."""
    result = []
    for match in re.finditer(header + r"\s*\{", source):
        opening = source.index("{", match.start())
        depth = 0
        for token in TOKEN.finditer(source, opening):
            if token.group() == "{":
                depth += 1
            elif token.group() == "}":
                depth -= 1
                if not depth:
                    result.append(source[opening + 1:token.start()])
                    break
        else:
            raise AssertionError("Unclosed GUI block " + header)
    return result


def single_block(source, header):
    result = blocks(source, header)
    if len(result) != 1:
        raise AssertionError(f"Expected one {header}, got {len(result)}")
    return result[0]


def override(source, name):
    return single_block(source, r'\bblockoverride\s+"' + re.escape(name) + '"')


def visible(source):
    return re.search(r'\bvisible\s*=\s*"([^"\n]+)"', source).group(1)


def direct_properties(source):
    """Keep only this block's surface, excluding all nested child bodies."""
    depth, cursor, pieces = 0, 0, []
    for token in TOKEN.finditer(source):
        if token.group() == "{":
            if depth == 0:
                pieces.append(source[cursor:token.start()])
            depth += 1
        elif token.group() == "}":
            depth -= 1
            if depth == 0:
                cursor = token.end()
    if depth:
        raise AssertionError("Unbalanced property body")
    return "".join(pieces) + source[cursor:]


def badge_rendering_prefix(state):
    """Color is a native widget property, never a returned rich-text prefix.

    CK3 displayed the old '[TntInterestColor(...)] [TntSV(...)]%#!' literally.
    Merely checking that the raw_text syntax parses cannot guard that failure.
    """
    raw = re.findall(r'\braw_text\s*=\s*"([^"\n]*)"', state)
    colors = re.findall(r'\bfontcolor\s*=\s*"([^"\n]*)"', state)
    if len(raw) != 1 or len(colors) != 1:
        raise AssertionError("Badge requires one bare percentage and one native fontcolor binding")
    match = re.fullmatch(r"\[TntSV\('(tnt_interest_\w+)_badge_percent_value'\)\|0\]%", raw[0])
    if not match:
        raise AssertionError("Badge raw text contains a computed formatting prefix or suffix")
    prefix = match[1]
    if colors[0] != f"[TntInterestColor('{prefix}_badge_percent_value')]":
        raise AssertionError("Badge color and displayed number must use exactly the same rounded value")
    return prefix


class InterestLayoutRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.types = clean(text(SOURCE / "gui/tnt_types.gui"))
        cls.window = clean(text(SOURCE / "gui/tnt_diplomacy_window.gui"))
        cls.contract = clean(text(SOURCE / "gui/tnt_panel_contract.gui"))
        cls.macros = clean(text(SOURCE / "data_binding/tnt_macros.txt"))
        cls.instances = blocks(cls.window + "\n" + cls.contract, r"\btnt_interest_badge\s*=")

    def test_all_35_persistent_badges_use_same_integer_for_text_and_color(self):
        self.assertEqual(len(self.instances), 35)
        observed = Counter()
        for badge in self.instances:
            value = override(badge, "tnt_interest_value")
            observed[badge_rendering_prefix(value)] += 1
            self.assertNotRegex(value, r"\bvisible\s*=")
            self.assertNotIn("tnt_interest_dash", value)
            self.assertNotIn('blockoverride "tnt_interest_selected"', badge)
            self.assertNotIn('blockoverride "tnt_interest_unselected"', badge)
        self.assertEqual(observed, Counter(BADGES))

    def test_color_threshold_is_50_and_uses_same_round_once_api(self):
        macro = next(body for body in blocks(self.macros, r"\bmacro\s*=")
                     if 'definition = "TntInterestColor(V)"' in body)
        replacement = re.search(r'replace_with\s*=\s*"([^"]+)"', macro).group(1)
        green = "FloatToCVector4f('(float)0.4','(float)0.61','(float)0.3','(float)1')"
        white = "FloatToCVector4f('(float)0.87','(float)0.84','(float)0.75','(float)1')"
        red = "FloatToCVector4f('(float)0.8','(float)0.3','(float)0.3','(float)1')"
        expected = ("Select_CVector4f(GreaterThan_CFixedPoint(GetPlayer.MakeScope.ScriptValue(V),'(CFixedPoint)50'),"
                    + green + ",Select_CVector4f(EqualTo_CFixedPoint(GetPlayer.MakeScope.ScriptValue(V),'(CFixedPoint)50')," + white + "," + red + "))")
        self.assertEqual(re.sub(r"\s+", "", replacement), expected)
        self.assertNotIn("Select_CString", replacement)
        self.assertNotIn("#", replacement)
        definitions = dict((name, body) for name, _, body in parse(text(SOURCE / "common/script_values/tnt_65_interest_preview_values.txt")))
        for prefix in BADGES:
            body = definitions[prefix + "_badge_percent_value"]
            self.assertEqual(body, [("value", "=", prefix + "_display_percent_value"),
                                    ("round", "=", "yes"), ("min", "=", "0"), ("max", "=", "100")])

    def test_badge_width_and_no_inherited_dash_or_expanding_name_competition(self):
        badge = single_block(self.types, r"\btype\s+tnt_interest_badge\s*=\s*widget")
        self.assertRegex(badge, r"(?m)^\s*size\s*=\s*\{\s*52\s+23\s*\}")
        self.assertRegex(badge, r"minimumsize\s*=\s*\{\s*52\s+23\s*\}")
        self.assertRegex(badge, r"maximumsize\s*=\s*\{\s*52\s+23\s*\}")
        self.assertNotIn("layoutpolicy_horizontal = expanding", badge)
        self.assertEqual(len(blocks(badge, r"\btext_single\s*=")), 1)
        label = body_containing(badge, "tnt_interest_value")
        self.assertRegex(label, r"min_width\s*=\s*52\b")
        self.assertRegex(label, r"max_width\s*=\s*52\b")
        self.assertIn("autoresize = no", label)
        self.assertIn('default_format = ""', label)
        self.assertNotIn('text = "tnt_interest_dash"', label)
        self.assertIn("position = { 0 0 }", label)
        self.assertIn("size = { 52 23 }", label)
        self.assertIn("parentanchor = top|left", label)
        self.assertIn("widgetanchor = top|left", label)
        self.assertIn("align = nobaseline|left", label)
        self.assertIn("alwaystransparent = yes", label)
        self.assertNotRegex(label, r"\bvisible\s*=")
        self.assertNotRegex(badge, r"\b(?:hbox|vbox|flowcontainer)\s*=")
        self.assertNotRegex(direct_properties(badge), r"\b(?:ignoreinvisible|spacing)\s*=")
        self.assertIn("using = tooltip_es", badge)
        self.assertIn("alwaystransparent = no", direct_properties(badge))

    def test_old_dynamic_prefix_and_partial_color_fix_are_explicitly_rejected(self):
        prefix = "tnt_interest_gold_p"
        bare = f"[TntSV('{prefix}_badge_percent_value')|0]%"
        color = f"[TntInterestColor('{prefix}_badge_percent_value')]"
        self.assertEqual(badge_rendering_prefix(f'fontcolor = "{color}" raw_text = "{bare}"'), prefix)
        for raw in (color + " " + bare + "#!", "#P " + bare + "#!", bare + "#!"):
            with self.subTest(raw=raw), self.assertRaises(AssertionError):
                badge_rendering_prefix(f'fontcolor = "{color}" raw_text = "{raw}"')
        with self.assertRaises(AssertionError):
            badge_rendering_prefix(f'raw_text = "{bare}"')
        with self.assertRaises(AssertionError):
            badge_rendering_prefix(f'fontcolor = "{color.replace("gold_p", "gold_r")}" raw_text = "{bare}"')

    def test_normal_side_rows_keep_64px_bounds_and_badge_on_second_line(self):
        frame = single_block(self.types, r"\btype\s+tnt_item_frame\s*=\s*hbox")
        self.assertRegex(frame, r"(?m)^\s*size\s*=\s*\{\s*0\s+64\s*\}")
        self.assertRegex(frame, r"minimumsize\s*=\s*\{\s*0\s+64\s*\}")
        self.assertRegex(frame, r"maximumsize\s*=\s*\{\s*-1\s+64\s*\}")
        name = body_containing(frame, "tnt_row_name_line")
        detail = body_containing(frame, "tnt_row_detail_line")
        for row, height in ((name, 26), (detail, 23)):
            self.assertRegex(row, r"minimumsize\s*=\s*\{\s*0\s+" + str(height) + r"\s*\}")
            self.assertRegex(row, r"maximumsize\s*=\s*\{\s*-1\s+" + str(height) + r"\s*\}")
        self.assertNotIn("tnt_row_interest", name)
        self.assertIn('block "tnt_row_interest" {}', detail)
        self.assertIn('name = "tnt_row_sub"', detail)
        self.assertIn("ignoreinvisible = yes", detail)
        self.assertIn("autoresize = no", body_containing(name, "tnt_row_name"))

    def test_badge_stays_left_via_always_visible_subtitle_width_slot(self):
        detail = body_containing(self.types, "tnt_row_detail_line")
        slot = body_containing(detail, "tnt_row_sub_slot")
        self.assertEqual(len(blocks(detail, r"\bwidget\s*=")), 1)
        self.assertIn("layoutpolicy_horizontal = expanding", direct_properties(slot))
        self.assertNotRegex(direct_properties(slot), r"\b(?:visible|ignoreinvisible|parentanchor|layoutanchor)\s*=")
        self.assertRegex(slot, r"\bsize\s*=\s*\{\s*0\s+23\s*\}")
        subtitle = body_containing(slot, "tnt_row_sub")
        self.assertIn('block "tnt_row_sub" { visible = no }', subtitle)
        self.assertIn("size = { 100% 100% }", subtitle)
        self.assertIn("align = nobaseline|left", subtitle)
        self.assertIn("autoresize = no", subtitle)
        self.assertNotIn("layoutpolicy_horizontal = expanding", direct_properties(subtitle))
        self.assertLess(detail.index('block "tnt_row_interest"'), detail.index('name = "tnt_row_sub_slot"'))
        self.assertNotRegex(detail, r"\bexpand\s*=")
        self.assertNotRegex(direct_properties(detail), r"\b(?:parentanchor|layoutanchor)\s*=")

    def test_all_35_preview_breakdowns_are_empty_only_and_keep_selected_points_separate(self):
        observed = Counter()
        for badge in self.instances:
            preview = override(badge, "tnt_interest_preview_breakdown")
            selected = override(badge, "tnt_interest_breakdown")
            annotation = override(badge, "tnt_interest_empty_state")
            points = override(badge, "tnt_interest_points")
            prefix = re.search(r"TntBreakdown\('(tnt_interest_\w+)_preview_percent_value'\)", preview).group(1)
            observed[prefix] += 1
            self.assertEqual(visible(preview), visible(annotation))
            self.assertEqual(visible(selected), visible(points))
            self.assertEqual(re.sub(r"\s+", "", visible(preview)),
                             "[Not(" + re.sub(r"\s+", "", visible(selected))[1:-1] + ")]")
            self.assertEqual(badge_rendering_prefix(override(badge, "tnt_interest_value")), prefix)
            self.assertIn(f"TntBreakdown('{prefix}_percent_value')", selected)
            self.assertIn('text = "tnt_interest_preview_', annotation)
        self.assertEqual(observed, Counter(BADGES))

    def test_zero_contract_heading_matches_benefit_preview_direction(self):
        for term in CONTRACTS:
            row = body_containing(self.contract, "tnt_contract_row_" + term)
            heading = re.sub(r"\s+", "", override(row, "tnt_interest_heading"))
            self.assertIn(f"Not(TntPos('tnt_interest_ob_{term}_selected_value'))", heading)
            self.assertIn(f"TntPos('tnt_interest_ob_{term}_base_value')", heading)
            self.assertIn("Or(", heading)
            self.assertLess(heading.index("Localize('tnt_interest_receive')"), heading.index("Localize('tnt_interest_surrender')"))

    def test_central_interest_adjustment_owns_full_row(self):
        interest = body_containing(self.types, "tnt_figure_row_interest")
        shared = body_containing(self.types, "tnt_figure_row_threat")
        self.assertEqual(interest.count("tnt_balance_figure ="), 1)
        self.assertIn('name = "tnt_figure_interest"', interest)
        self.assertNotIn("tnt_figure_interest", shared)
        self.assertIn('name = "tnt_figure_floor"', shared)
        self.assertIn('name = "tnt_figure_threat"', shared)
        self.assertIn("tnt_interest_penalty_display_value", interest)

    def test_six_normal_and_huge_plus_widgets_are_live_gated_with_failure_tooltips(self):
        plus_type = body_containing(self.types, "tnt_stepper_plus_button")
        self.assertIn('block "tnt_stepper_plus"', plus_type)
        self.assertIn('block "tnt_stepper_plus_big"', plus_type)
        self.assertIn('block "tnt_stepper_tt_plus"', plus_type)
        for currency in ("gold", "prestige", "piety"):
            for side in ("p", "r"):
                row = body_containing(self.window, f"tnt_row_{currency}_{side}")
                for suffix, block, tooltip in (("add", "tnt_stepper_plus", "tnt_stepper_tt_plus"),
                        ("add_huge", "tnt_stepper_huge_plus", "tnt_stepper_tt_huge_plus")):
                    target = f"tnt_{currency}_{side}_{suffix}"
                    button = override(row, block)
                    self.assertIn(f"TntExec('{target}')", button)
                    self.assertIn(f'enabled = "[TntValid(\'{target}\')]"', button)
                    tip = override(row, tooltip)
                    self.assertIn(f"TntValid('{target}')", tip)
                    self.assertIn(f"TntTip('{target}')", tip)
                    self.assertIn("Localize(", tip)
                self.assertIn(f"TntExec('tnt_{currency}_{side}_add_big')", override(row, "tnt_stepper_plus_big"))

    def test_six_preset_openers_and_eighteen_increasing_presets_are_gated(self):
        for currency in ("gold", "prestige", "piety"):
            for side in ("p", "r"):
                row = body_containing(self.window, f"tnt_row_{currency}_{side}")
                opener = override(row, "tnt_stepper_preset_open")
                self.assertIn(f"TntValid('tnt_{currency}_{side}_add')", opener)
                self.assertIn(f"TntTip('tnt_{currency}_{side}_add')", opener)
                menu = body_containing(self.window, f"tnt_preset_{currency}_{side}")
                for preset in ("std", "half", "max"):
                    target = f"tnt_{currency}_{side}_{preset}"
                    button = override(menu, "tnt_preset_sgui_" + preset)
                    self.assertIn(f"TntExec('{target}')", button)
                    self.assertIn(f'enabled = "[TntValid(\'{target}\')]"', button)
                    tip = override(menu, "tnt_preset_tt_" + preset)
                    tooltip_target = re.search(r"TntTip\('([^']+)'\)", tip).group(1)
                    self.assertIn(tooltip_target, (target, f"tnt_{currency}_{side}_add"))
                    self.assertIn(f"TntValid('{tooltip_target}')", tip)
                    self.assertIn("Localize(", tip)

    def test_decrement_and_clear_controls_are_never_gated_by_increase_lock(self):
        for currency in ("gold", "prestige", "piety"):
            for side in ("p", "r"):
                row = body_containing(self.window, f"tnt_row_{currency}_{side}")
                for block in ("tnt_stepper_minus", "tnt_stepper_minus_big", "tnt_stepper_huge_minus"):
                    self.assertNotIn("enabled", override(row, block))
                    self.assertNotIn("TntValid", override(row, block))
                menu = body_containing(self.window, f"tnt_preset_{currency}_{side}")
                self.assertNotIn("enabled", override(menu, "tnt_preset_sgui_none"))
                self.assertNotIn("TntValid", override(menu, "tnt_preset_sgui_none"))

    def test_new_preview_and_opposite_currency_messages_exist_in_all_nine_locales(self):
        keys = {"tnt_interest_preview_currency", "tnt_interest_preview_context", "tnt_interest_preview_contract",
                "tnt_err_currency_opposite_selected"}
        keys.update(re.findall(r"desc\s*=\s*(tnt_interest_bd_preview_\w+)", text(SOURCE / "common/script_values/tnt_65_interest_preview_values.txt")))
        locales = list((SOURCE / "localization").glob("*/*.yml"))
        self.assertEqual(len(locales), 9)
        for path in locales:
            content = text(path)
            for key in keys:
                self.assertEqual(len(re.findall(r"^ " + re.escape(key) + r':\d+ "[^\n]+"', content, re.M)), 1, (path, key))


if __name__ == "__main__":
    unittest.main()
