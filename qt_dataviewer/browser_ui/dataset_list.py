import logging
from typing import Dict, List, Tuple

from PyQt5 import QtCore, QtWidgets
from qt_dataviewer.abstract.dataset_description import DatasetDescription

logger = logging.getLogger(__name__)


class DatasetListView(QtWidgets.QTreeWidget):
    """Widget displaying a list of datasets for the selected dates.

    Note: It's a QTreeWidget, because QListWidget does not support multiple columns.
    """

    dataset_activated = QtCore.pyqtSignal(DatasetDescription)

    def __init__(self,
                 parent: QtWidgets.QWidget,
                 column_definitions: Tuple[str, str, int],
                 label_keys: Dict[str, str],
                 sort_by_column: int):
        super().__init__(parent)

        self.setStyleSheet(
            """
            QTreeWidget::item {
            height: 22px;
            padding-right: 10px;
            }
            """
            )

        self.column_definitions = column_definitions
        self.label_keys = label_keys

        self.setColumnCount(len(column_definitions))
        self.setHeaderLabels([col[0] for col in column_definitions])
        for index, col in enumerate(column_definitions):
            if len(col) > 1:
                self.setColumnWidth(index, col[1])

        self.itemActivated.connect(self._dataset_activated)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.sortByColumn(sort_by_column, QtCore.Qt.DescendingOrder)

    @QtCore.pyqtSlot(QtCore.QPoint)
    def show_context_menu(self, position: QtCore.QPoint) -> None:
        """
        Show a context menu when the user right-clicks on an item in the tree.
        """
        # Get the index and item at the given position
        model_index = self.indexAt(position)
        item = self.itemFromIndex(model_index)

        menu = QtWidgets.QMenu()

        copy_icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton)
        copy_action = menu.addAction(copy_icon, "Copy")

        # Show menu at cursor and wait for result
        action = menu.exec_(self.mapToGlobal(position))
        if action == copy_action:
            QtWidgets.QApplication.clipboard().setText(item.text(model_index.column()))

    def add_dataset(self, ds_description: DatasetDescription) -> None:
        """Adds a new dataset to the list.

        Args:
            ds_description (DatasetDescription): description of dataset.
        """
        texts = [
            ds_description.get_text(self.label_keys[col[0]])
            for col in self.column_definitions
            ]
        item = QtWidgets.QTreeWidgetItem(texts)
        item.setData(0, QtCore.Qt.UserRole, ds_description)
        self.addTopLevelItem(item)

    def set_datasets(self, datasets: List[DatasetDescription]) -> None:
        # TODO @@@ Keep selected dataset (if possible)
        # Clear the existing items in the list
        self.clear()

        # disable sorting before inserting values to avoid performance hit
        self.setSortingEnabled(False)

        for dataset in datasets:
            self.add_dataset(dataset)

        # Re-enable sorting and resize the columns
        self.setSortingEnabled(True)
        for i, col in enumerate(self.column_definitions):
            if len(col) <= 1:
                self.resizeColumnToContents(i)

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def _dataset_activated(self, item: QtWidgets.QTreeWidgetItem, _: int) -> None:
        ds_description = item.data(0, QtCore.Qt.UserRole)
        self.dataset_activated.emit(ds_description)


