from PyQt5 import QtWidgets, QtCore

from qt_dataviewer.browser_ui.main_window import DataBrowserBase

from .dataset_store import QuantifyDatasetStore


# @@@ TEST when launched from plain python console

class QuantifyDataBrowser(DataBrowserBase):
    def __init__(self, path=None, auto_scan: bool = True):
        self._quantify_data_dir = path
        self.data_store = QuantifyDatasetStore()
        self.data_store.enable_auto_scan(auto_scan)

        super().__init__(
            "Quantify",
            self.data_store,
            "Path",
            label_keys={
                "TUID": "uid",
                "Time": "time",
                "Name": "name",
                "Keywords": "keywords",
                },
            column_definitions=[
                ("TUID", 190),
                ("Time", 56),
                ("Name", ),
                ("Keywords", ),
             ],
            sort_by_column=1,
            filters=[
                "Name",
                ],
            )

    def browser_started(self):
        if self._quantify_data_dir is not None:
            self.data_store.open_dir(self._quantify_data_dir)
        else:
            self._select_data_dir()
        super().browser_started()

    def get_menu_actions(self):
        actions = []
        open_action = QtWidgets.QAction("&Open data directory", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._select_data_dir)
        actions.append(open_action)

        return actions

    @QtCore.pyqtSlot()
    def _select_data_dir(self):
        current = self._quantify_data_dir
        if current is None:
            current = ''

        data_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Dataset directory', current)

        if data_dir:
            self._quantify_data_dir = data_dir
            self.dataset_store.open_dir(data_dir)
