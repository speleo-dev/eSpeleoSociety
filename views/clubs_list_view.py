from PyQt5.QtWidgets import ( 
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QPushButton, QMessageBox, QAbstractItemView,
    QDialog, QLineEdit
)
from PyQt5.QtGui import QShowEvent # Added import for QShowEvent
from PyQt5.QtCore import Qt, pyqtSignal
from club_filtering import club_matches_filter
import db
from dialogs.club_management_dialog import ClubManagementDialog
from table_layout import ColumnSpec
from ui_table import SortableItem, create_columns_button, install_table_features
from utils import get_table_header_stylesheet, show_error_message # Pridaný import


ORIGINAL_VALUE_ROLE = Qt.UserRole
CLUB_ID_ROLE = Qt.UserRole + 1

# Column identity is the stable key, not the position: the user may reorder or
# hide columns and the persisted layout still has to line up.
CLUB_EDITABLE_KEYS = {
    "name", "street", "city", "zip_code", "country",
    "email", "phone", "webpage", "president",
}


def club_column_specs(tr):
    """Declared columns. The address details are hidden by default so the table
    fits on screen and the Actions button is reachable without scrolling; they
    stay one click away in the Columns menu."""
    return [
        ColumnSpec("name", tr("Club Name"), width=240, essential=True, stretch=True),
        ColumnSpec("street", tr("Street"), width=180, hidden=True),
        ColumnSpec("city", tr("City"), width=140),
        ColumnSpec("zip_code", tr("ZIP Code"), width=90, hidden=True),
        ColumnSpec("country", tr("Country"), width=120, hidden=True),
        ColumnSpec("email", tr("Email"), width=220),
        ColumnSpec("phone", tr("Phone"), width=150, hidden=True),
        ColumnSpec("webpage", tr("Webpage"), width=200, hidden=True),
        ColumnSpec("president", tr("President"), width=180),
        ColumnSpec("member_count", tr("Member Count"), width=110, numeric=True),
        ColumnSpec("actions", tr("Actions"), width=90, essential=True),
    ]


class ClubsListView(QWidget):
    navigateToMembers = pyqtSignal(int) # Signal to emit club_id - presunuté na úroveň triedy

    def __init__(self, parent=None):
        super().__init__(parent)
        # Atribút navigateToMembers je teraz dedený z triedy
        self.clubs = []
        self._clubs_by_id = {}
        self._loading = False
        self.init_ui()

    def _column(self, key: str) -> int:
        return self.table_controller.index_of(key)

    def init_ui(self):
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header = QLabel(self.tr("List of SSS Clubs"))
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        header_layout.addWidget(QLabel(self.tr("Filter:")))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(self.tr("Filter clubs..."))
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self.apply_filter)
        header_layout.addWidget(self.filter_edit)
        self.filter_status_label = QLabel("")
        header_layout.addWidget(self.filter_status_label)
        btn_new_club = QPushButton(self.tr("➕ Create New Club"))
        btn_new_club.clicked.connect(self.request_new_club_creation)
        header_layout.addWidget(btn_new_club)
        layout = QVBoxLayout(self)
        layout.addWidget(header_widget)

        self.table = QTableWidget()
        self.table_controller = install_table_features(
            self.table, "clubs_list", club_column_specs(self.tr), parent=self
        )
        header_layout.insertWidget(
            header_layout.count() - 1, create_columns_button(self.table_controller, header_widget)
        )
        layout.addWidget(self.table)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.table.itemChanged.connect(self._handle_item_changed)
        self.table.setStyleSheet("QTableWidget { font-size: 10pt; }")
        self.table.horizontalHeader().setStyleSheet(get_table_header_stylesheet())

        self.load_data()

    def load_data(self):
        self._loading = True
        self.table.setSortingEnabled(False)
        self.clubs = db.db_manager.fetch_clubs()
        self._clubs_by_id = {club.club_id: club for club in self.clubs}
        self.table.setRowCount(len(self.clubs))

        for row, club in enumerate(self.clubs):
            self._set_text_item(row, "name", club.name, club_id=club.club_id)
            self._set_text_item(row, "street", club.street, club_id=club.club_id)
            self._set_text_item(row, "city", club.city, club_id=club.club_id)
            self._set_text_item(row, "zip_code", club.zip_code, club_id=club.club_id)
            self._set_text_item(row, "country", club.country, club_id=club.club_id)
            self._set_text_item(row, "email", club.email, club_id=club.club_id)
            self._set_text_item(row, "phone", club.phone, club_id=club.club_id)
            self._set_text_item(row, "webpage", club.webpage, club_id=club.club_id)
            self._set_text_item(row, "president", club.president_name, club_id=club.club_id)
            self._set_text_item(
                row, "member_count", str(club.member_count), editable=False,
                club_id=club.club_id, sort_value=int(club.member_count or 0),
            )
            self._set_text_item(row, "actions", "", editable=False, club_id=club.club_id)
            btn_view = QPushButton(self.tr("View"))
            # Uistite sa, že lambda správne viaže aktuálnu hodnotu club['id']
            btn_view.clicked.connect(lambda checked, cid=club.club_id: self.show_members_list(cid))
            self.table.setCellWidget(row, self._column("actions"), btn_view)

        self.table.setSortingEnabled(True)
        self._loading = False
        self.apply_filter()

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        # Only once the widget has a real width can the stretch column be sized
        # to fill it without leaving an empty strip on the right.
        self.table_controller.expand_to_viewport()

    def _set_text_item(self, row: int, key: str, value, editable: bool = True, club_id=None, sort_value=None):
        column = self._column(key)
        if column < 0:
            return
        text = "" if value is None else str(value)
        item = SortableItem(text, sort_value)
        item.setToolTip(text)
        item.setData(ORIGINAL_VALUE_ROLE, text)
        item.setData(CLUB_ID_ROLE, club_id)
        flags = item.flags()
        if editable and key in CLUB_EDITABLE_KEYS:
            item.setFlags(flags | Qt.ItemIsEditable)
        else:
            item.setFlags(flags & ~Qt.ItemIsEditable)
        self.table.setItem(row, column, item)

    def _key_for_column(self, column: int):
        specs = self.table_controller.specs
        if 0 <= column < len(specs):
            return specs[column].key
        return None

    def _handle_item_changed(self, item: QTableWidgetItem):
        key = self._key_for_column(item.column())
        if self._loading or key not in CLUB_EDITABLE_KEYS:
            return
        club_id = item.data(CLUB_ID_ROLE)
        club = self._clubs_by_id.get(club_id)
        if club is None:
            return

        old_value = item.data(ORIGINAL_VALUE_ROLE) or ""
        new_value = item.text().strip()
        if new_value == old_value:
            return

        try:
            self._apply_club_edit(club, key, new_value)
            db.db_manager.update_club(club)
            item.setData(ORIGINAL_VALUE_ROLE, new_value)
            item.setData(SortableItem.SORT_ROLE, new_value)
            item.setToolTip(new_value)
            self.apply_filter()
        except Exception as exc:
            self._loading = True
            item.setText(old_value)
            self._loading = False
            show_error_message(self.tr("Failed to save club value: ") + str(exc))

    def _apply_club_edit(self, club, key: str, value: str):
        if key == "name":
            if not value:
                raise ValueError(self.tr("Club name cannot be empty."))
            club.name = value
        elif key == "street":
            club.street = value
        elif key == "city":
            club.city = value
        elif key == "zip_code":
            club.zip_code = value
        elif key == "country":
            club.country = value
        elif key == "email":
            club.email = value
        elif key == "phone":
            club.phone = value
        elif key == "webpage":
            club.webpage = value
        elif key == "president":
            club.president_name = value
            club.president_name_text = value

    def sort_by_club_name(self, order):
        self.table.sortItems(self._column("name"), order)

    def _club_for_row(self, row: int):
        item = self.table.item(row, self._column("name"))
        if item is None:
            return None
        return self._clubs_by_id.get(item.data(CLUB_ID_ROLE))

    def apply_filter(self):
        filter_text = self.filter_edit.text() if hasattr(self, "filter_edit") else ""
        visible_count = 0
        for row in range(self.table.rowCount()):
            club = self._club_for_row(row)
            visible = club is not None and club_matches_filter(club, filter_text)
            self.table.setRowHidden(row, not visible)
            if visible:
                visible_count += 1
        if hasattr(self, "filter_status_label"):
            self.filter_status_label.setText(f"{visible_count}/{len(self.clubs)}")
            
    def show_members_list(self, club_id: int):
        self.navigateToMembers.emit(club_id)

    def request_new_club_creation(self):
        """Otvorí dialóg pre vytvorenie nového klubu."""
        # ClubManagementDialog s is_new=True a club=None sa postará o logiku nového klubu
        dlg = ClubManagementDialog(club=None, is_new=True, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            # Ak bol nový klub úspešne pridaný a uložený (dialóg vrátil Accepted),
            # obnovíme zoznam klubov, aby sa zobrazil nový klub.
            self.load_data()
