import logging
from typing import List, Optional
from PyQt5 import QtWidgets, QtCore

from qt_dataviewer.browser_ui.main_window import DataBrowserBase

from .dataset_store import SqdlDatasetStore


logger = logging.getLogger(__name__)


class SqdlDataBrowser(DataBrowserBase):
    def __init__(self, scope_name: str = None):
        self.data_store = SqdlDatasetStore() # TODO @@@ change construction order to show pop-up notification for login..
        self.scope_name = scope_name
        if self.data_store.user_name:
            title_extra = "sQDL - " + self.data_store.user_name
        else:
            title_extra = "sQDL"
        super().__init__(
            title_extra,
            self.data_store,
            "Scope",
            label_keys={
                "Starred": "rating",
                "UUID": "uid",
                "Time": "time",
                "Name": "name",
                "Variables": "variables_measured",
                "Axes": "dimensions",
                "Setup": "setup",
                "Sample": "sample",
                },
            column_definitions=[
                ("Starred", 44),
                ("UUID", 140),
                ("Time", 56),
                ("Name", ),
                ("Variables", ),
                ("Axes", ),
             ],
            sort_by_column=1,
            filters=[
                ("Setup", "list"),
                ("Sample", "list"),
                # TODO rating
                # "Rating",
                "Name",
                ("Variables", "list"),
                ("Axes", "list"),
                ],
            )

    def browser_started(self):
        if self.scope_name is not None:
            self.set_scope(self.scope_name)
        else:
            self._select_scope()
        super().browser_started()

    def get_menu_actions(self):
        actions = []
        open_action = QtWidgets.QAction("&Select scope", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._select_scope)
        actions.append(open_action)

        logout_action = QtWidgets.QAction("&Log out && exit", self)
        logout_action.triggered.connect(self._logout)
        actions.append(logout_action)

        return actions

    @QtCore.pyqtSlot(str)
    def set_scope(self, scope_name):
        self.scope_name = scope_name
        self.dataset_store.set_scope(scope_name)

    @QtCore.pyqtSlot()
    def _select_scope(self):
        current_scope = self.data_store.scope_name
        scopes = self.data_store.get_scopes()

        dlg = SelectScopeDialog(scopes, current_scope)

        if dlg.exec():
            logger.info(f"Select scope: {dlg.selected_scope}")
            self.data_store.set_scope(dlg.selected_scope)
            self.activateWindow()

    @QtCore.pyqtSlot()
    def _logout(self):
        self.data_store.logout()
        self.close()

class SelectScopeDialog(QtWidgets.QDialog):
    def __init__(self, scopes: List[str], current_scope: Optional[str]):
        super().__init__()
        self.setWindowTitle("Select scope")
        buttons = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        self.button_box = QtWidgets.QDialogButtonBox(buttons)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout = QtWidgets.QVBoxLayout()
        message = QtWidgets.QLabel("Select scope")
        self.list = QtWidgets.QListWidget()
        self.list.addItems(scopes)
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        if current_scope:
            index = scopes.index(current_scope)
            self.list.setCurrentRow(index)
        self.list.doubleClicked.connect(self.accept)
        self.layout.addWidget(message)
        self.layout.addWidget(self.list)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

    @property
    def selected_scope(self):
        item = self.list.currentItem()
        if item is None:
            return None
        return item.text()

