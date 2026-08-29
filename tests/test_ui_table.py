import os
import shutil
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QTableWidget

import table_layout
from table_layout import (
    ColumnSpec,
    TableLayout,
    clamp_width,
    decode_layout,
    default_layout,
    encode_layout,
    sanitize_layout,
    toggle_hidden,
    visible_specs,
)

SPECS = [
    ColumnSpec("name", "Name", width=200, essential=True, stretch=True),
    ColumnSpec("city", "City", width=120),
    ColumnSpec("zip", "ZIP", width=80, hidden=True),
    ColumnSpec("count", "Count", width=90, numeric=True),
    ColumnSpec("actions", "Actions", width=90, essential=True),
]

_app = QApplication.instance() or QApplication([])


class ColumnSpecTest(unittest.TestCase):
    def test_essential_column_can_never_start_hidden(self):
        spec = ColumnSpec("actions", "Actions", hidden=True, essential=True)
        self.assertFalse(spec.hidden)

    def test_empty_key_is_rejected(self):
        with self.assertRaises(ValueError):
            ColumnSpec("", "Nameless")

    def test_width_is_clamped_on_construction(self):
        self.assertEqual(ColumnSpec("a", "A", width=-5).width, table_layout.MIN_COLUMN_WIDTH)
        self.assertEqual(ColumnSpec("a", "A", width=99999).width, table_layout.MAX_COLUMN_WIDTH)

    def test_clamp_width_survives_garbage(self):
        self.assertEqual(clamp_width("wide"), table_layout.DEFAULT_COLUMN_WIDTH)
        self.assertEqual(clamp_width(None), table_layout.DEFAULT_COLUMN_WIDTH)


class SanitizeLayoutTest(unittest.TestCase):
    def test_unknown_columns_are_dropped(self):
        layout = sanitize_layout(
            {"widths": {"removed": 500, "city": 300}, "order": ["removed", "city"]}, SPECS
        )
        self.assertNotIn("removed", layout.widths)
        self.assertEqual(layout.widths["city"], 300)
        self.assertNotIn("removed", layout.order)

    def test_newly_added_columns_are_appended_to_the_order(self):
        layout = sanitize_layout({"order": ["actions", "name"]}, SPECS)
        self.assertEqual(layout.order[:2], ["actions", "name"])
        self.assertEqual(sorted(layout.order), sorted(s.key for s in SPECS))

    def test_essential_columns_cannot_be_hidden_by_a_stored_layout(self):
        layout = sanitize_layout({"hidden": ["name", "actions", "city"]}, SPECS)
        self.assertNotIn("name", layout.hidden)
        self.assertNotIn("actions", layout.hidden)
        self.assertIn("city", layout.hidden)

    def test_a_layout_hiding_everything_keeps_one_column_visible(self):
        specs = [ColumnSpec("a", "A"), ColumnSpec("b", "B")]
        layout = sanitize_layout({"hidden": ["a", "b"]}, specs)
        self.assertEqual(len(layout.hidden), 1)

    def test_widths_from_a_stored_layout_are_clamped(self):
        layout = sanitize_layout({"widths": {"city": 99999, "count": 1}}, SPECS)
        self.assertEqual(layout.widths["city"], table_layout.MAX_COLUMN_WIDTH)
        self.assertEqual(layout.widths["count"], table_layout.MIN_COLUMN_WIDTH)

    def test_sort_key_for_a_removed_column_is_discarded(self):
        self.assertEqual(sanitize_layout({"sort_key": "gone"}, SPECS).sort_key, "")

    def test_non_dict_input_falls_back_to_defaults(self):
        self.assertEqual(sanitize_layout("garbage", SPECS).hidden, ["zip"])


class EncodeDecodeTest(unittest.TestCase):
    def test_round_trip(self):
        layout = TableLayout(
            widths={"name": 210}, hidden=["zip"], order=["actions", "name", "city", "zip", "count"],
            sort_key="count", sort_descending=True,
        )
        restored = decode_layout(encode_layout(layout), SPECS)
        self.assertEqual(restored.widths["name"], 210)
        self.assertEqual(restored.hidden, ["zip"])
        self.assertEqual(restored.order[0], "actions")
        self.assertEqual(restored.sort_key, "count")
        self.assertTrue(restored.sort_descending)

    def test_corrupted_layout_never_raises(self):
        for junk in ["", "not json", "[1,2,3]", None]:
            layout = decode_layout(junk, SPECS)
            self.assertEqual(sorted(layout.order), sorted(s.key for s in SPECS))


class VisibleSpecsTest(unittest.TestCase):
    def test_respects_order_and_hiding(self):
        layout = TableLayout(order=["actions", "name", "city", "zip", "count"], hidden=["zip", "count"])
        self.assertEqual([s.key for s in visible_specs(SPECS, layout)], ["actions", "name", "city"])


class ToggleHiddenTest(unittest.TestCase):
    def test_essential_column_refuses_to_hide(self):
        layout = default_layout(SPECS)
        toggle_hidden(layout, SPECS[0], True, SPECS)
        self.assertNotIn("name", layout.hidden)

    def test_show_and_hide_a_normal_column(self):
        layout = default_layout(SPECS)
        toggle_hidden(layout, SPECS[1], True, SPECS)
        self.assertIn("city", layout.hidden)
        toggle_hidden(layout, SPECS[1], False, SPECS)
        self.assertNotIn("city", layout.hidden)

    def test_hiding_the_last_visible_column_is_refused(self):
        specs = [ColumnSpec("a", "A"), ColumnSpec("b", "B", hidden=True)]
        layout = default_layout(specs)
        toggle_hidden(layout, specs[0], True, specs)
        self.assertLess(len(layout.hidden), len(specs))


class LayoutStoreTest(unittest.TestCase):
    def setUp(self):
        import app_paths

        self.app_paths = app_paths
        self.temp_dir = tempfile.mkdtemp()
        self._original = app_paths.CONFIG_DIR
        app_paths.CONFIG_DIR = os.path.join(self.temp_dir, "config")

    def tearDown(self):
        self.app_paths.CONFIG_DIR = self._original
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_missing_store_returns_defaults(self):
        layout = table_layout.load_layout("clubs_list", SPECS)
        self.assertEqual(layout.hidden, ["zip"])

    def test_saved_layout_is_restored(self):
        layout = default_layout(SPECS)
        layout.widths["city"] = 321
        layout.sort_key = "count"
        self.assertTrue(table_layout.save_layout("clubs_list", layout))

        restored = table_layout.load_layout("clubs_list", SPECS)
        self.assertEqual(restored.widths["city"], 321)
        self.assertEqual(restored.sort_key, "count")

    def test_tables_do_not_overwrite_each_others_layout(self):
        first = default_layout(SPECS)
        first.widths["city"] = 111
        table_layout.save_layout("clubs_list", first)
        second = default_layout(SPECS)
        second.widths["city"] = 222
        table_layout.save_layout("members_list", second)

        self.assertEqual(table_layout.load_layout("clubs_list", SPECS).widths["city"], 111)
        self.assertEqual(table_layout.load_layout("members_list", SPECS).widths["city"], 222)

    def test_a_corrupted_store_does_not_break_loading(self):
        self.app_paths.ensure_config_dir()
        with open(self.app_paths.config_path(table_layout.LAYOUT_STORE_FILENAME), "w") as handle:
            handle.write("{ this is not json")
        self.assertEqual(table_layout.load_layout("clubs_list", SPECS).hidden, ["zip"])

    def test_clear_layout_restores_defaults(self):
        layout = default_layout(SPECS)
        layout.widths["city"] = 321
        table_layout.save_layout("clubs_list", layout)
        self.assertTrue(table_layout.clear_layout("clubs_list"))
        self.assertEqual(table_layout.load_layout("clubs_list", SPECS).widths["city"], 120)


class TableControllerTest(unittest.TestCase):
    """The behaviour the user actually reported as missing."""

    def setUp(self):
        import app_paths

        self.app_paths = app_paths
        self.temp_dir = tempfile.mkdtemp()
        self._original = app_paths.CONFIG_DIR
        app_paths.CONFIG_DIR = os.path.join(self.temp_dir, "config")

        from ui_table import install_table_features

        self.table = QTableWidget()
        self.controller = install_table_features(self.table, "test_table", SPECS)

    def tearDown(self):
        self.app_paths.CONFIG_DIR = self._original
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_every_column_is_user_resizable(self):
        from PyQt5.QtWidgets import QHeaderView

        header = self.table.horizontalHeader()
        for index in range(self.table.columnCount()):
            self.assertEqual(
                header.sectionResizeMode(index),
                QHeaderView.Interactive,
                f"column {index} is not draggable",
            )

    def test_columns_are_movable_and_sortable(self):
        header = self.table.horizontalHeader()
        self.assertTrue(header.sectionsMovable())
        self.assertTrue(header.sectionsClickable())
        self.assertTrue(self.table.isSortingEnabled())

    def test_header_offers_a_context_menu(self):
        self.assertEqual(
            self.table.horizontalHeader().contextMenuPolicy(), Qt.CustomContextMenu
        )

    def test_default_hidden_columns_are_hidden(self):
        self.assertTrue(self.table.isColumnHidden(self.controller.index_of("zip")))
        self.assertFalse(self.table.isColumnHidden(self.controller.index_of("name")))

    def test_hiding_and_showing_a_column_persists(self):
        self.controller.set_column_hidden("city", True)
        self.assertTrue(self.table.isColumnHidden(self.controller.index_of("city")))

        restored = table_layout.load_layout("test_table", SPECS)
        self.assertIn("city", restored.hidden)

        self.controller.set_column_hidden("city", False)
        self.assertFalse(self.table.isColumnHidden(self.controller.index_of("city")))
        self.assertNotIn("city", table_layout.load_layout("test_table", SPECS).hidden)

    def test_essential_column_cannot_be_hidden_through_the_controller(self):
        self.controller.set_column_hidden("actions", True)
        self.assertFalse(self.table.isColumnHidden(self.controller.index_of("actions")))

    def test_column_width_survives_a_new_controller(self):
        self.table.setColumnWidth(self.controller.index_of("city"), 275)
        self.controller._capture_geometry()
        self.controller._save()

        from ui_table import install_table_features

        table = QTableWidget()
        controller = install_table_features(table, "test_table", SPECS)
        self.assertEqual(table.columnWidth(controller.index_of("city")), 275)

    def test_reordering_survives_a_new_controller(self):
        header = self.table.horizontalHeader()
        header.moveSection(header.visualIndex(self.controller.index_of("actions")), 0)
        self.controller._capture_geometry()
        self.controller._save()

        from ui_table import install_table_features

        table = QTableWidget()
        controller = install_table_features(table, "test_table", SPECS)
        self.assertEqual(
            table.horizontalHeader().logicalIndex(0), controller.index_of("actions")
        )

    def test_index_of_is_stable_regardless_of_visual_order(self):
        header = self.table.horizontalHeader()
        name_index = self.controller.index_of("name")
        header.moveSection(header.visualIndex(name_index), 3)
        self.assertEqual(self.controller.index_of("name"), name_index)

    def test_index_of_unknown_key(self):
        self.assertEqual(self.controller.index_of("nope"), -1)

    def test_fit_to_contents_keeps_columns_within_a_sane_width(self):
        from ui_table import FIT_MAX_WIDTH, SortableItem

        self.table.setRowCount(1)
        self.table.setItem(0, 0, SortableItem("x" * 500))
        self.controller.fit_columns_to_contents()
        self.assertLessEqual(self.table.columnWidth(0), FIT_MAX_WIDTH)

    def test_fit_to_contents_leaves_columns_resizable(self):
        from PyQt5.QtWidgets import QHeaderView

        self.controller.fit_columns_to_contents()
        header = self.table.horizontalHeader()
        for index in range(self.table.columnCount()):
            self.assertEqual(header.sectionResizeMode(index), QHeaderView.Interactive)

    def test_reset_layout_restores_the_declared_defaults(self):
        self.controller.set_column_hidden("city", True)
        self.table.setColumnWidth(self.controller.index_of("name"), 400)
        self.controller.reset_layout()

        self.assertFalse(self.table.isColumnHidden(self.controller.index_of("city")))
        self.assertEqual(self.table.columnWidth(self.controller.index_of("name")), 200)

    def test_columns_menu_lists_every_column(self):
        menu = self.controller.columns_menu()
        labels = {action.text() for action in menu.actions() if action.isCheckable()}
        self.assertEqual(labels, {spec.label for spec in SPECS})

    def test_essential_entries_in_the_menu_are_disabled(self):
        menu = self.controller.columns_menu()
        for action in menu.actions():
            if action.text() == "Actions":
                self.assertFalse(action.isEnabled())

    def test_menu_checkboxes_reflect_the_current_state(self):
        self.controller.set_column_hidden("city", True)
        menu = self.controller.columns_menu()
        city = next(a for a in menu.actions() if a.text() == "City")
        self.assertFalse(city.isChecked())

    def test_toggling_from_the_menu_hides_the_column(self):
        menu = self.controller.columns_menu()
        city = next(a for a in menu.actions() if a.text() == "City")
        city.setChecked(False)
        self.assertTrue(self.table.isColumnHidden(self.controller.index_of("city")))


class SortableItemTest(unittest.TestCase):
    def test_numbers_sort_numerically_not_as_text(self):
        from ui_table import SortableItem

        self.assertTrue(SortableItem("9", 9) < SortableItem("10", 10))
        self.assertFalse(SortableItem("10", 10) < SortableItem("9", 9))

    def test_text_sorting_ignores_case_and_none(self):
        from ui_table import SortableItem

        self.assertTrue(SortableItem("apple") < SortableItem("Banana"))
        self.assertTrue(SortableItem("", None) < SortableItem("a"))

    def test_defaults_to_the_display_text(self):
        from ui_table import SortableItem

        self.assertTrue(SortableItem("aaa") < SortableItem("bbb"))


if __name__ == "__main__":
    unittest.main()
