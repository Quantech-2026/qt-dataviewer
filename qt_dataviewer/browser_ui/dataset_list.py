import logging

from PyQt5 import QtCore, QtWidgets, QtGui

from qt_dataviewer.abstract.dataset_description import DatasetDescription
from qt_dataviewer.resources.icons import add_icons_to_checkbox, Icons, Images


logger = logging.getLogger(__name__)


class DatasetListView(QtWidgets.QWidget):
    """Widget displaying a list of datasets for the selected dates.

    Note: It's a QTreeWidget, because QListWidget does not support multiple columns.
    """

    dataset_activated = QtCore.pyqtSignal(DatasetDescription)
    dataset_rating_changed = QtCore.pyqtSignal(DatasetDescription, int)

    def __init__(self,
                 parent: QtWidgets.QWidget,
                 column_definitions: tuple[str] | tuple[str, int] | tuple[str, int, str],
                 label_keys: dict[str, str],
                 sort_by_column: int):
        super().__init__(parent)

        self.column_definitions = column_definitions
        self.label_keys = label_keys
        self.sort_by_column = sort_by_column

        self.rating_column = None
        self.rating_options = None
        for icol, col in enumerate(column_definitions):
            if len(col) > 2 and col[2] in ['rating-star', 'rating-star-hide']:
                self.rating_column = icol
                self.rating_options = col[2]

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Create QTreeView and set a model
        tree_view = QtWidgets.QTreeView()
        self.tree_view = tree_view
        layout.addWidget(tree_view)

        model = QtGui.QStandardItemModel()
        self.model = model

        model.setHorizontalHeaderLabels([col[0] for col in column_definitions])
        tree_view.setModel(model)

        tree_view.setRootIsDecorated(False)

        tree_view.doubleClicked.connect(self._dataset_activated)
        tree_view.clicked.connect(self._dataset_modify)
        tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tree_view.customContextMenuRequested.connect(self.show_context_menu)

        tree_view.sortByColumn(sort_by_column, QtCore.Qt.DescendingOrder)
        self._resizeColumns()

        # tree_view.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)

        self.setStyleSheet(
            """
            QTreeView::item {
            height: 22px;
            padding-right: 10px;
            }
            """
            )

    @QtCore.pyqtSlot(QtCore.QPoint)
    def show_context_menu(self, position: QtCore.QPoint) -> None:
        """
        Show a context menu when the user right-clicks on an item in the tree.
        """
        # Get the index and item at the given position
        model_index = self.tree_view.indexAt(position)
        item = self.model.itemFromIndex(model_index)

        menu = QtWidgets.QMenu()

        copy_icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton)
        copy_action = menu.addAction(copy_icon, "Copy")

        # Show menu at cursor and wait for result
        action = menu.exec_(self.mapToGlobal(position))
        if action == copy_action:
            QtWidgets.QApplication.clipboard().setText(item.text())

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def _dataset_modify(self, model_index: QtCore.QModelIndex) -> None:
        if model_index.column() == self.rating_column:
            index = self.model.index(model_index.row(), 0)
            item = self.model.itemFromIndex(index)
            ds_description = item.data(QtCore.Qt.UserRole)

            globalCursorPos = QtGui.QCursor.pos()
            menu = QtWidgets.QMenu()

            if self.rating_options == 'rating-star':
                star_action = menu.addAction(Icons.starred(), "Star")
                normal_action = menu.addAction(Icons.no_star(), "Default")
                hide_action = None
            elif self.rating_options == 'rating-star-hide':
                star_action = menu.addAction(Icons.starred(), "Star")
                normal_action = menu.addAction(Icons.neutral(), "Default")
                hide_action = menu.addAction(Icons.hidden(), "Hide")

            # Show menu at cursor and wait for result
            action = menu.exec_(globalCursorPos)
            if not action:
                return
            if action == star_action:
                rating = +1
            elif action == normal_action:
                rating = 0
            elif action == hide_action:
                rating = -1

            if rating != ds_description.rating:
                self._set_rating(ds_description, rating)
                item.setData(self._get_rating_image(ds_description.rating), QtCore.Qt.DecorationRole)

    def _get_rating_image(self, rating):
        if rating == 1:
            return Images.starred()
        if rating == 0:
            if self.rating_options == 'rating-star-hide':
                return Images.neutral()
            else:
                return Images.no_star()
        if rating == -1:
            return Images.hidden()

    def add_dataset(self, ds_description: DatasetDescription) -> None:
        """Adds a new dataset to the list.

        Args:
            ds_description (DatasetDescription): description of dataset.
        """
        self.tree_view.setSortingEnabled(False)
        self._add_dataset(ds_description)
        self.tree_view.setSortingEnabled(True)

    def _add_dataset(self, ds_description: DatasetDescription) -> None:
        items = []
        for icol, col in enumerate(self.column_definitions):
            text = ds_description.get_text(self.label_keys[col[0]])
            if icol == self.rating_column:
                item = QtGui.QStandardItem("")
                item.setData(self._get_rating_image(ds_description.rating), QtCore.Qt.DecorationRole)
            else:
                item = QtGui.QStandardItem(text)
            item.setEditable(False)
            items.append(item)

        items[0].setData(ds_description, QtCore.Qt.UserRole)
        self.model.appendRow(items)

    def set_datasets(self, datasets: list[DatasetDescription]) -> None:
        # TODO @@@ Keep selected dataset (if possible)

        # Clear the existing items in the list
        self.model.clear()

        # set headers again after clearing
        self.model.setHorizontalHeaderLabels([col[0] for col in self.column_definitions])

        # disable sorting before inserting values to avoid performance hit
        self.tree_view.setSortingEnabled(False)

        for dataset in datasets:
            self._add_dataset(dataset)

        # Re-enable sorting and resize the columns
        self.tree_view.sortByColumn(self.sort_by_column, QtCore.Qt.DescendingOrder)
        self.tree_view.setSortingEnabled(True)
        self._resizeColumns()

    def _resizeColumns(self):
        for i, col in enumerate(self.column_definitions):
            if len(col) <= 1 or col[1] < 0:
                self.tree_view.resizeColumnToContents(i)
            else:
                self.tree_view.setColumnWidth(i, col[1])

    def _set_rating(self, ds_description: DatasetDescription, rating: int) -> None:
        ds_description.rating = rating
        self.dataset_rating_changed.emit(ds_description, rating)

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def _dataset_activated(self, model_index: QtCore.QModelIndex) -> None:
        index = self.model.index(model_index.row(), 0)
        item = self.model.itemFromIndex(index)
        ds_description = item.data(QtCore.Qt.UserRole)
        self.dataset_activated.emit(ds_description)


class RatingWidget(QtWidgets.QWidget):
    rating_changed = QtCore.pyqtSignal(int)

    def __init__(self, parent = None, up: bool = True, down: bool = False,
                 rating: int = 0):
        super().__init__(parent)

        self._rating = rating

        self.setAutoFillBackground(True)

        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        layout = QtWidgets.QHBoxLayout(self)
        # keep only the default margin on the left
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(0)


        if up:
            cb_up = QtWidgets.QCheckBox()
            add_icons_to_checkbox(cb_up, "thumb_up_green.png", "thumb_up_white.png", 18)
            if rating > 0:
                cb_up.setCheckState(QtCore.Qt.Checked)
            cb_up.stateChanged.connect(self._up_changed)
            self.cb_up = cb_up
            layout.addWidget(cb_up, 0)
        else:
            self.cb_up = None
        if down:
            cb_down = QtWidgets.QCheckBox()
            add_icons_to_checkbox(cb_down, "thumb_down_red.png", "thumb_down_white.png", 18)
            if rating < 0:
                cb_down.setCheckState(QtCore.Qt.Checked)
            cb_down.stateChanged.connect(self._down_changed)
            self.cb_down = cb_down
            layout.addWidget(cb_down, 0)
        else:
            self.cb_hide = None

    @QtCore.pyqtSlot(int)
    def _up_changed(self, state: QtCore.Qt.CheckState) -> None:
        if state == QtCore.Qt.Checked:
            self._rating = +1
            self.rating_changed.emit(self._rating)
            if self.cb_down:
                self.cb_down.setCheckState(QtCore.Qt.Unchecked)
        elif self._rating == +1:
            self._rating = 0
            self.rating_changed.emit(self._rating)

    @QtCore.pyqtSlot(int)
    def _down_changed(self, state: QtCore.Qt.CheckState) -> None:
        if state == QtCore.Qt.Checked:
            self._rating = -1
            if self.cb_up:
                self.cb_up.setCheckState(QtCore.Qt.Unchecked)
            self.rating_changed.emit(self._rating)
        elif self._rating == -1:
            self._rating = 0
            self.rating_changed.emit(self._rating)
