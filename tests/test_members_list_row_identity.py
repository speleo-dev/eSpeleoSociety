"""Rows are not a stable identity once a table can be sorted.

Regression guard for a bug found while making the tables sortable: editing a
cell or running a bulk action after sorting used ``self.members[row]`` and so
wrote to the wrong member.
"""

import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


def make_member(mid, first, last, status="active"):
    return SimpleNamespace(
        member_id=mid, first_name=first, last_name=last, status=status,
        title_prefix="", title_suffix="", birth_date=None, street="Ulica",
        city="Mesto", zip_code="01001", country="SK", phone="", email=f"{first}@x.sk",
        is_president=False, ecp_hash=None, primary_club_id=1, primary_club_name="Klub",
        paid_fee_calls=0,
    )


class MembersListRowIdentityTest(unittest.TestCase):
    def setUp(self):
        import app_paths

        self.app_paths = app_paths
        self.temp_dir = tempfile.mkdtemp()
        self._original = app_paths.CONFIG_DIR
        app_paths.CONFIG_DIR = os.path.join(self.temp_dir, "config")

        self.members = [
            make_member(1, "Zuzana", "Zelena"),
            make_member(2, "Adam", "Adamec"),
            make_member(3, "Michal", "Maly"),
        ]
        self.club = SimpleNamespace(
            club_id=1, name="Klub", street="", city="", zip_code="", country="",
            email="", phone="", webpage="", president_name="", logo_url=None,
        )

        import db

        self._original_db = getattr(db, "db_manager", None)
        db.db_manager = SimpleNamespace(
            fetch_members=lambda cid: self.members,
            datetime=__import__("datetime"),
        )
        self.db = db

        import views.members_list_view as mlv

        self.mlv = mlv
        # get_state_pixmap needs configured secrets/images; the icon is
        # irrelevant to row identity.
        self._original_pixmap = mlv.get_state_pixmap
        mlv.get_state_pixmap = lambda m, c: __import__(
            "PyQt5.QtGui", fromlist=["QPixmap"]
        ).QPixmap(1, 1)

        self.view = mlv.MembersListView()
        self.view.load_data_for_club(self.club)

    def tearDown(self):
        self.mlv.get_state_pixmap = self._original_pixmap
        self.db.db_manager = self._original_db
        self.app_paths.CONFIG_DIR = self._original
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _row_of(self, last_name):
        table = self.view.table
        for row in range(table.rowCount()):
            item = table.item(row, 3)
            if item is not None and last_name in item.text():
                return row
        raise AssertionError(f"{last_name} not found in the table")

    def test_table_is_populated(self):
        self.assertEqual(self.view.table.rowCount(), 3)

    def test_member_for_row_is_correct_before_sorting(self):
        row = self._row_of("Zelena")
        self.assertEqual(self.view._member_for_row(row).member_id, 1)

    def test_member_for_row_follows_the_data_after_sorting(self):
        self.view.table.sortItems(3, Qt.AscendingOrder)
        # Sorted by full name: Adam, Michal, Zuzana
        self.assertEqual(self.view._member_for_row(0).first_name, "Adam")
        self.assertEqual(self.view._member_for_row(2).first_name, "Zuzana")

    def test_editing_a_cell_after_sorting_updates_the_right_member(self):
        table = self.view.table
        table.sortItems(3, Qt.AscendingOrder)
        row = self._row_of("Adamec")

        applied = {}
        self.view._apply_member_edit = lambda member, column, value: (
            applied.update(member=member, value=value) or False
        )

        table.item(row, 8).setText("novy@email.sk")

        self.assertIn("member", applied, "the edit was ignored")
        self.assertEqual(applied["member"].member_id, 2)
        self.assertEqual(applied["value"], "novy@email.sk")

    def test_selection_after_sorting_resolves_to_the_right_members(self):
        table = self.view.table
        table.sortItems(3, Qt.DescendingOrder)
        table.selectRow(0)

        selected = self.view._selected_members()
        self.assertEqual(len(selected), 1)
        expected = table.item(0, 3).text()
        self.assertIn(selected[0].last_name, expected)

    def test_selected_members_is_empty_without_a_selection(self):
        self.view.table.clearSelection()
        self.assertEqual(self.view._selected_members(), [])

    def test_every_cell_carries_the_member_id(self):
        table = self.view.table
        for row in range(table.rowCount()):
            ids = {
                table.item(row, col).data(self.mlv.MEMBER_ID_ROLE)
                for col in range(table.columnCount())
                if table.item(row, col) is not None
            }
            self.assertEqual(len(ids), 1, f"row {row} mixes member ids: {ids}")
            self.assertIsNotNone(ids.pop())

    def test_clearing_the_club_empties_the_identity_map(self):
        self.view.load_data_for_club(None)
        self.assertEqual(self.view._members_by_id, {})
        self.assertEqual(self.view.table.rowCount(), 0)


if __name__ == "__main__":
    unittest.main()
