import logging
from packaging.version import Version
from sqdl_client import __version__ as sqdl_client_version
from qtpy import QtWidgets, QtCore

from qt_dataviewer.browser_ui.main_window import DataBrowserBase
from qt_dataviewer.utils.qt_utils import qt_show_error

from .dataset_store import SqdlDatasetStore


logger = logging.getLogger(__name__)


class SqdlDataBrowser(DataBrowserBase):
    def __init__(self, scope_name: str | None = None, gui_style: str | None = None):
        """
        Creates sQDL data browser.

        Args:
            scope_name: name of scope to open. If None a selection box will be shown.
            gui_style: if "dark" enables dark style for gui.
        """
        self.data_store = SqdlDatasetStore() # TODO @@@ change construction order to show pop-up notification for login..
        self.scope_name = scope_name
        if self.data_store.user_name:
            title_extra = "sQDL - " + self.data_store.user_name
        else:
            title_extra = "sQDL"
        # TODO @@@ make GUI descriptor class
        super().__init__(
            title_extra,
            self.data_store,
            "Scope",
            label_keys={
                "Rating": "rating",
                "UUID": "uid",
                "Time": "time",
                "Name": "name",
                "Variables": "variables_measured",
                "Axes": "dimensions",
                "Setup": "setup",
                "Sample": "sample",
                },
            column_definitions=[
                ("Rating", 54, "rating-star-hide"),
                ("UUID", ),
                ("Time", ),
                ("Name", ),
                ("Variables", ),
                ("Axes", ),
             ],
            sort_by_column=1,
            filters=[
                ("Setup", "list"),
                ("Sample", "list"),
                ("Rating", "rating-star-hide"),
                "Name",
                ("Variables", "list"),
                ("Axes", "list"),
                ],
            gui_style=gui_style,
            )

    def browser_started(self):
        if Version(sqdl_client_version) < Version("1.0.8"):
            qt_show_error("Upgrade sqdl-client", "Upgrade sqdl-client to version 1.0.8+")
            self.close()
            raise Exception("Upgrade sqdl-client to version 1.0.8+")
        if self.scope_name is not None:
            self.dataset_store.set_scope(self.scope_name)
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

    @QtCore.Slot()
    def _select_scope(self):
        current_scope = self.data_store.scope_name
        scopes = self.data_store.get_scopes()

        dlg = SelectScopeDialog(scopes, current_scope)

        if dlg.exec():
            logger.info(f"Select scope: {dlg.selected_scope}")
            self.scope_name = dlg.selected_scope
            self.data_store.set_scope(self.scope_name)
            self.activateWindow()

    @QtCore.Slot()
    def _logout(self):
        self.data_store.logout()
        self.close()


class SelectScopeDialog(QtWidgets.QDialog):
    def __init__(self, scopes: list[str], current_scope: str | None):
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

