from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QApplication
from qt_dataviewer.utils.qt_utils import qt_log_exception

from .directory_scanner import DirectoryScanner


class DirectoryTreeView(QTreeWidget):

    path_changed = QtCore.pyqtSignal(str)

    def __init__(self, dir_scanner: DirectoryScanner):
        super().__init__()
        self._dir_scanner = dir_scanner
        self.setColumnCount(1)
        # self.setColumnWidth(0, 280)
        self.setHeaderLabels(["Path"])
        self.itemExpanded.connect(self._item_expanded)
        self.itemSelectionChanged.connect(self._item_selected)

        self.current_path = ""
        self.refresh()

    def clear(self):
        super().clear()
        self.current_path = ""

    def refresh(self):
        super().clear()
        self.select_item(self.current_path)

    def select_item(self, path):
        parts = path.split("/")
        self._select(None, parts)

    def _select(self, parent: QTreeWidgetItem | None, path_parts: list[str]):
        name = path_parts[0]
        last = len(path_parts) == 1
        if parent is None:
            n = self.topLevelItemCount()
            if n == 0:
                self._add_children(parent, "")
            if name == "":
                if self.topLevelItemCount() > 0:
                    self.topLevelItem(0).setSelected(True)
                return
            for i in range(self.topLevelItemCount()):
                item = self.topLevelItem(i)
                if item.text(0) == name:
                    if last:
                        item.setSelected(True)
                    else:
                        self._select(item, path_parts[1:])
                    return
        else:
            path, children_loaded = item.data(0, Qt.UserRole)
            if not children_loaded:
                self._add_children(item, path)
            for i in range(parent.childCount()):
                item = parent.child(i)
                if item.text() == name:
                    if last:
                        item.setSelected(True)
                    else:
                        self._select(item, path_parts[1:])
                    return
        raise Exception(f"Item {name} not found")

    @qt_log_exception
    def _item_expanded(self, item: QTreeWidgetItem):
        path, children_loaded = item.data(0, Qt.UserRole)
        if not children_loaded:
            self._add_children(item, path)

    @qt_log_exception
    def _item_selected(self):
        item: QTreeWidgetItem = self.currentItem()
        if item is None:
            self.path_changed.emit("")
            return
        path, _ = item.data(0, Qt.UserRole)
        self.current_path = path
        QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.path_changed.emit(path)
        QApplication.restoreOverrideCursor()

    def _add_children(self, parent: QTreeWidgetItem | None, path: str):
        subdir_names = self._dir_scanner.get_subdirectories(path)
        for name in subdir_names:
            item_path = (path + "/" + name) if path != "" else name
            item = QTreeWidgetItem()
            item.setText(0, name)
            item.setData(0, Qt.UserRole, (item_path, False))
            item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
            if parent:
                parent.addChild(item)
            else:
                self.addTopLevelItem(item)

        if parent:
            parent.setData(0, Qt.UserRole, (path, True))
            parent.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicatorWhenChildless)
