# ui_table.py
"""Standard behaviour for every data table in the application.

Historically each view configured its own ``QHeaderView`` with a hand-picked
mix of ``ResizeToContents`` and ``Stretch`` sections. That combination makes
columns **impossible for the user to resize**, produces tables far wider than
the window (so row actions end up off-screen) and offers no way to hide the
columns a given user does not care about.

:func:`install_table_features` replaces that with what desktop users expect:

* every column is drag-resizable, and double-clicking a header divider fits it
  to its contents (standard Qt behaviour for interactive sections),
* columns can be reordered by dragging their header,
* columns can be hidden/shown from the header context menu or the "Columns"
  button,
* clicking a header sorts by that column,
* the whole arrangement is remembered per table between runs,
* long values are elided instead of blowing up the column width.

Column identity is a stable string key, so the persisted layout survives
reordering or renaming columns in code (see :mod:`table_layout`).
"""

from PyQt5.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QHeaderView,
    QMenu,
    QPushButton,
    QTableWidgetItem,
)

from table_layout import (
    MAX_COLUMN_WIDTH,
    MIN_COLUMN_WIDTH,
    ColumnSpec,
    clamp_width,
    default_layout,
    load_layout,
    save_layout,
    toggle_hidden,
)

# Fitting to contents must not reintroduce the "wider than the screen" problem.
FIT_MAX_WIDTH = 320
SAVE_DEBOUNCE_MS = 400


class SortableItem(QTableWidgetItem):
    """Table item that sorts on a dedicated value instead of its display text.

    Without it, numeric columns sort lexicographically ("10" < "9") and date
    columns sort by their formatted string.
    """

    SORT_ROLE = Qt.UserRole + 100

    def __init__(self, text="", sort_value=None):
        super().__init__(text)
        self.setData(self.SORT_ROLE, text if sort_value is None else sort_value)

    def __lt__(self, other):
        left = self.data(self.SORT_ROLE)
        right = other.data(self.SORT_ROLE) if isinstance(other, QTableWidgetItem) else None
        if isinstance(left, bool) or isinstance(right, bool):
            return bool(left) < bool(right)
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left < right
        return str("" if left is None else left).casefold() < str("" if right is None else right).casefold()


class TableController(QObject):
    """Applies and persists the layout of a single ``QTableWidget``."""

    layoutChanged = pyqtSignal()

    def __init__(self, table, table_key: str, specs, parent=None):
        super().__init__(parent or table)
        self.table = table
        self.table_key = table_key
        self.specs = list(specs)
        self._by_key = {spec.key: spec for spec in self.specs}
        self._applying = False
        self._menu = None
        self._menu_actions = {}

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(SAVE_DEBOUNCE_MS)
        self._save_timer.timeout.connect(self._save)

        self.layout = load_layout(table_key, self.specs)
        self._configure_table()
        self.apply_layout()
        self._connect_signals()

    # -- setup -------------------------------------------------------------

    def _configure_table(self):
        table = self.table
        table.setColumnCount(len(self.specs))
        table.setHorizontalHeaderLabels([spec.label for spec in self.specs])
        for index, spec in enumerate(self.specs):
            item = table.horizontalHeaderItem(index)
            if item is not None and spec.tooltip:
                item.setToolTip(spec.tooltip)

        table.setSortingEnabled(True)
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.ElideRight)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setCornerButtonEnabled(False)

        header = table.horizontalHeader()
        # Interactive is what makes columns draggable; ResizeToContents and
        # Stretch both lock the divider and were the root cause of the tables
        # being unadjustable.
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionsMovable(True)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(MIN_COLUMN_WIDTH)
        header.setTextElideMode(Qt.ElideRight)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._show_header_menu)

        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)

    def _connect_signals(self):
        header = self.table.horizontalHeader()
        header.sectionResized.connect(self._on_geometry_changed)
        header.sectionMoved.connect(self._on_geometry_changed)
        header.sortIndicatorChanged.connect(self._on_geometry_changed)

    # -- layout application -------------------------------------------------

    def apply_layout(self):
        self._applying = True
        try:
            header = self.table.horizontalHeader()
            for index, spec in enumerate(self.specs):
                self.table.setColumnWidth(index, self.layout.width_for(spec))
                self.table.setColumnHidden(index, self.layout.is_hidden(spec.key))

            for target, key in enumerate(self.layout.order):
                logical = self._logical_index(key)
                if logical is None:
                    continue
                current = header.visualIndex(logical)
                if current != -1 and current != target:
                    header.moveSection(current, target)

            if self.layout.sort_key:
                logical = self._logical_index(self.layout.sort_key)
                if logical is not None:
                    order = Qt.DescendingOrder if self.layout.sort_descending else Qt.AscendingOrder
                    header.setSortIndicator(logical, order)
                    self.table.sortItems(logical, order)
        finally:
            self._applying = False

    def _logical_index(self, key):
        for index, spec in enumerate(self.specs):
            if spec.key == key:
                return index
        return None

    def index_of(self, key: str) -> int:
        """Logical column index for a stable key (-1 when unknown).

        Views address cells by this index, so reordering columns visually never
        affects the data they write.
        """
        index = self._logical_index(key)
        return -1 if index is None else index

    # -- user actions -------------------------------------------------------

    def set_column_hidden(self, key: str, hidden: bool):
        spec = self._by_key.get(key)
        if spec is None:
            return
        toggle_hidden(self.layout, spec, hidden, self.specs)
        index = self._logical_index(key)
        if index is not None:
            self.table.setColumnHidden(index, self.layout.is_hidden(key))
            if not self.layout.is_hidden(key) and self.table.columnWidth(index) < MIN_COLUMN_WIDTH:
                self.table.setColumnWidth(index, self.layout.width_for(spec))
        self._save()

    def fit_columns_to_contents(self):
        """One-shot auto-fit that keeps the columns interactive afterwards."""
        self._applying = True
        try:
            self.table.resizeColumnsToContents()
            for index in range(self.table.columnCount()):
                if self.table.isColumnHidden(index):
                    continue
                width = min(max(self.table.columnWidth(index), MIN_COLUMN_WIDTH), FIT_MAX_WIDTH)
                self.table.setColumnWidth(index, width)
        finally:
            self._applying = False
        self._capture_geometry()
        self._save()

    def reset_layout(self):
        self.layout = default_layout(self.specs)
        self.apply_layout()
        self._save()

    def expand_to_viewport(self):
        """Grow the designated stretch column so the table fills the window.

        Only ever grows: shrinking here would silently undo a width the user
        dragged themselves.
        """
        stretch = next((spec for spec in self.specs if spec.stretch), None)
        if stretch is None or self.layout.is_hidden(stretch.key):
            return
        index = self._logical_index(stretch.key)
        if index is None:
            return

        viewport = self.table.viewport().width()
        used = sum(
            self.table.columnWidth(i)
            for i in range(self.table.columnCount())
            if not self.table.isColumnHidden(i)
        )
        slack = viewport - used
        if slack <= 0:
            return
        self._applying = True
        try:
            self.table.setColumnWidth(index, clamp_width(self.table.columnWidth(index) + slack))
        finally:
            self._applying = False
        self._capture_geometry()

    # -- persistence --------------------------------------------------------

    def _on_geometry_changed(self, *args):
        if self._applying:
            return
        self._capture_geometry()
        self._save_timer.start()

    def _capture_geometry(self):
        header = self.table.horizontalHeader()
        for index, spec in enumerate(self.specs):
            width = self.table.columnWidth(index)
            if width >= MIN_COLUMN_WIDTH:
                self.layout.widths[spec.key] = clamp_width(width)

        order = []
        for visual in range(header.count()):
            logical = header.logicalIndex(visual)
            if 0 <= logical < len(self.specs):
                order.append(self.specs[logical].key)
        if order:
            self.layout.order = order

        section = header.sortIndicatorSection()
        if 0 <= section < len(self.specs):
            self.layout.sort_key = self.specs[section].key
            self.layout.sort_descending = header.sortIndicatorOrder() == Qt.DescendingOrder

    def _save(self):
        save_layout(self.table_key, self.layout)
        self.layoutChanged.emit()

    # -- column menu --------------------------------------------------------

    def columns_menu(self, parent=None) -> QMenu:
        """Shared, lazily built column menu.

        Deliberately built once and only re-synced afterwards: rebuilding it
        while one of its own actions is being toggled would destroy the menu
        the user is currently interacting with.
        """
        if self._menu is None:
            self._menu = self._build_columns_menu(parent or self.table)
        self._sync_menu()
        return self._menu

    def _build_columns_menu(self, parent) -> QMenu:
        menu = QMenu(parent)
        menu.addSection(self.tr("Show columns"))
        self._menu_actions = {}
        for spec in self.specs:
            action = QAction(spec.label, menu)
            action.setCheckable(True)
            action.setChecked(not self.layout.is_hidden(spec.key))
            if spec.essential:
                action.setEnabled(False)
                action.setToolTip(self.tr("This column cannot be hidden."))
            action.toggled.connect(
                lambda checked, key=spec.key: self._on_column_toggled(key, checked)
            )
            self._menu_actions[spec.key] = action
            menu.addAction(action)

        menu.addSeparator()
        fit_action = QAction(self.tr("Fit columns to contents"), menu)
        fit_action.triggered.connect(self.fit_columns_to_contents)
        menu.addAction(fit_action)

        reset_action = QAction(self.tr("Reset table layout"), menu)
        reset_action.triggered.connect(self.reset_layout)
        menu.addAction(reset_action)
        return menu

    def _on_column_toggled(self, key: str, checked: bool):
        if self._applying:
            return
        self.set_column_hidden(key, not checked)
        # A column that refused to hide (last visible / essential) must not be
        # left with a checkbox that lies about the actual state.
        self._sync_menu()

    def _sync_menu(self):
        if self._menu is None:
            return
        self._applying = True
        try:
            for key, action in self._menu_actions.items():
                action.setChecked(not self.layout.is_hidden(key))
        finally:
            self._applying = False

    def _show_header_menu(self, position):
        menu = self.columns_menu()
        menu.exec_(self.table.horizontalHeader().viewport().mapToGlobal(position))


def install_table_features(table, table_key: str, specs, parent=None) -> TableController:
    """Give ``table`` the standard resizable/sortable/configurable behaviour."""
    return TableController(table, table_key, specs, parent=parent)


def create_columns_button(controller: TableController, parent=None) -> QPushButton:
    """Discoverable entry point to the column menu.

    A header right-click alone is not discoverable enough for the people who
    reported the tables as "not interactive".
    """
    button = QPushButton(controller.tr("Columns \u25be"), parent)
    button.setToolTip(
        controller.tr(
            "Show or hide columns, fit them to their contents, or reset the layout.\n"
            "Columns can also be resized by dragging and reordered by dragging their header."
        )
    )
    menu = controller.columns_menu(button)
    button.setMenu(menu)
    menu.aboutToShow.connect(controller._sync_menu)
    return button
