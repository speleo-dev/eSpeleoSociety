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
from utils import get_table_header_stylesheet, show_error_message # Pridaný import


CLUB_EDITABLE_COLUMNS = set(range(0, 9))
ORIGINAL_VALUE_ROLE = Qt.UserRole
CLUB_ID_ROLE = Qt.UserRole + 1
SORT_VALUE_ROLE = Qt.UserRole + 2


class SortableClubItem(QTableWidgetItem):
    def __lt__(self, other):
        left = self.data(SORT_VALUE_ROLE)
        right = other.data(SORT_VALUE_ROLE)
        if isinstance(left, int) and isinstance(right, int):
            return left < right
        return str(left or "").casefold() < str(right or "").casefold()


class ClubsListView(QWidget):
    navigateToMembers = pyqtSignal(int) # Signal to emit club_id - presunuté na úroveň triedy

    def __init__(self, parent=None):
        super().__init__(parent)
        # Atribút navigateToMembers je teraz dedený z triedy
        self.clubs = []
        self._clubs_by_id = {}
        self._loading = False
        self._default_sort_applied = False
        self.init_ui()

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
        btn_sort_az = QPushButton(self.tr("A-Z"))
        btn_sort_az.setToolTip(self.tr("Sort clubs by name A-Z"))
        btn_sort_az.clicked.connect(lambda: self.sort_by_club_name(Qt.AscendingOrder))
        header_layout.addWidget(btn_sort_az)
        btn_sort_za = QPushButton(self.tr("Z-A"))
        btn_sort_za.setToolTip(self.tr("Sort clubs by name Z-A"))
        btn_sort_za.clicked.connect(lambda: self.sort_by_club_name(Qt.DescendingOrder))
        header_layout.addWidget(btn_sort_za)
        btn_new_club = QPushButton(self.tr("➕ Create New Club"))
        btn_new_club.clicked.connect(self.request_new_club_creation)
        header_layout.addWidget(btn_new_club)
        layout = QVBoxLayout(self)
        layout.addWidget(header_widget)

        # Označenie reťazca pre preklad
        #header = QLabel(self.tr("Zoznam klubov"))
        #layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        layout.addWidget(self.table)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.table.itemChanged.connect(self._handle_item_changed)
        self.table.setSortingEnabled(True)

        self.load_data()

    def load_data(self):
        self._loading = True
        sort_section = self.table.horizontalHeader().sortIndicatorSection()
        sort_order = self.table.horizontalHeader().sortIndicatorOrder()
        if not self._default_sort_applied:
            sort_section = 0
            sort_order = Qt.AscendingOrder
            self._default_sort_applied = True
        self.table.setSortingEnabled(False)
        self.clubs = db.db_manager.fetch_clubs()
        self._clubs_by_id = {club.club_id: club for club in self.clubs}
        self.table.setRowCount(len(self.clubs))
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setWordWrap(False)
        self.table.setStyleSheet("QTableWidget { font-size: 10pt; }")

        self.table.setHorizontalHeaderLabels([
            self.tr("Club Name"),
            self.tr("Street"),
            self.tr("City"),
            self.tr("ZIP Code"),
            self.tr("Country"),
            self.tr("Email"),
            self.tr("Phone"),
            self.tr("Webpage"),
            self.tr("President"),
            self.tr("Member Count"),
            self.tr("Actions"),
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch) # Club Name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # Street
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # City
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # ZIP Code
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # Country
        header.setSectionResizeMode(5, QHeaderView.Interactive) # Email
        header.setSectionResizeMode(6, QHeaderView.Interactive) # Phone
        header.setSectionResizeMode(7, QHeaderView.Interactive) # Webpage
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents) # President
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents) # Member Count
        header.setSectionResizeMode(10, QHeaderView.ResizeToContents) # Actions
        self.table.setColumnWidth(5, 230)
        self.table.setColumnWidth(6, 170)
        self.table.setColumnWidth(7, 230)
        header.setStretchLastSection(False) # Posledný stĺpec vyplní zvyšok

        
        # Nastavenie tmavého štýlu pre hlavičku tabuľky
        self.table.horizontalHeader().setStyleSheet(get_table_header_stylesheet())
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.setAlternatingRowColors(True)

        for row, club in enumerate(self.clubs):
            self._set_text_item(row, 0, club.name, club_id=club.club_id)
            self._set_text_item(row, 1, club.street, club_id=club.club_id)
            self._set_text_item(row, 2, club.city, club_id=club.club_id)
            self._set_text_item(row, 3, club.zip_code, club_id=club.club_id)
            self._set_text_item(row, 4, club.country, club_id=club.club_id)
            self._set_text_item(row, 5, club.email, club_id=club.club_id)
            self._set_text_item(row, 6, club.phone, club_id=club.club_id)
            self._set_text_item(row, 7, club.webpage, club_id=club.club_id)
            self._set_text_item(row, 8, club.president_name, club_id=club.club_id)
            self._set_text_item(row, 9, str(club.member_count), editable=False, club_id=club.club_id, sort_value=int(club.member_count or 0))
            self._set_text_item(row, 10, "", editable=False, club_id=club.club_id)
            btn_view = QPushButton(self.tr("View"))
            # Uistite sa, že lambda správne viaže aktuálnu hodnotu club['id']
            btn_view.clicked.connect(lambda checked, cid=club.club_id: self.show_members_list(cid))
            self.table.setCellWidget(row, 10, btn_view)
        self.table.setSortingEnabled(True)
        if sort_section < 0 or sort_section >= self.table.columnCount():
            sort_section = 0
            sort_order = Qt.AscendingOrder
        self.table.sortItems(sort_section, sort_order)
        self._loading = False
        self.apply_filter()

    def _set_text_item(self, row: int, column: int, value, editable: bool = True, club_id=None, sort_value=None):
        text = "" if value is None else str(value)
        item = SortableClubItem(text)
        item.setToolTip(text)
        item.setData(ORIGINAL_VALUE_ROLE, text)
        item.setData(CLUB_ID_ROLE, club_id)
        item.setData(SORT_VALUE_ROLE, text if sort_value is None else sort_value)
        flags = item.flags()
        if editable and column in CLUB_EDITABLE_COLUMNS:
            item.setFlags(flags | Qt.ItemIsEditable)
        else:
            item.setFlags(flags & ~Qt.ItemIsEditable)
        self.table.setItem(row, column, item)

    def _handle_item_changed(self, item: QTableWidgetItem):
        if self._loading or item.column() not in CLUB_EDITABLE_COLUMNS:
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
            self._apply_club_edit(club, item.column(), new_value)
            db.db_manager.update_club(club)
            item.setData(ORIGINAL_VALUE_ROLE, new_value)
            item.setData(SORT_VALUE_ROLE, new_value)
            item.setToolTip(new_value)
            self.apply_filter()
        except Exception as exc:
            self._loading = True
            item.setText(old_value)
            self._loading = False
            show_error_message(self.tr("Failed to save club value: ") + str(exc))

    def _apply_club_edit(self, club, column: int, value: str):
        if column == 0:
            if not value:
                raise ValueError(self.tr("Club name cannot be empty."))
            club.name = value
        elif column == 1:
            club.street = value
        elif column == 2:
            club.city = value
        elif column == 3:
            club.zip_code = value
        elif column == 4:
            club.country = value
        elif column == 5:
            club.email = value
        elif column == 6:
            club.phone = value
        elif column == 7:
            club.webpage = value
        elif column == 8:
            club.president_name = value
            club.president_name_text = value

    def sort_by_club_name(self, order):
        self.table.sortItems(0, order)

    def _club_for_row(self, row: int):
        item = self.table.item(row, 0)
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
