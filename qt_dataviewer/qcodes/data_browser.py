from PyQt5 import QtCore, QtWidgets

from qt_dataviewer.browser_ui.main_window import DataBrowserBase

from .dataset_store import QCoDeSDatasetStore


class QCoDeSDataBrowser(DataBrowserBase):
    def __init__(self, db_path: str | None = None, gui_style: str | None = None): # @@@ Path, PathLike
        self.data_store = QCoDeSDatasetStore(db_path)
        super().__init__(
            "QCoDeS",
            self.data_store,
            "Database",
            label_keys={
                "Experiment": "experiment",
                "Sample": "sample",
                "Rating": "rating",
                "UUID": "uid",
                "Time": "time",
                "Name": "name",
                "Variables": "vars",
                "Axes": "axes",
                },
            column_definitions=[
                ("UUID", ),
                ("Time", ),
                ("Name", ),
                ("Variables", ),
                ("Axes", ),
             ],
            sort_by_column=1,
            filters=[
                ("Sample", "list"),
                ("Experiment", "list"),
                "Name",
                ("Variables", "list"),
                ("Axes", "list"),
                ],
            gui_style=gui_style,
            )

    def get_menu_actions(self):
        actions = []
        open_action = QtWidgets.QAction("&Open database", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._select_db)
        actions.append(open_action)
        return actions

    def browser_started(self):
        if self.data_store.db_path is None:
            self._select_db()

        if self.data_store.db_path is not None:
            self.data_store.refresh()
        super().browser_started()

    @QtCore.pyqtSlot()
    def _select_db(self):
        current = self.data_store.db_path
        if current is None:
            current = ""

        db_path, _filter = QtWidgets.QFileDialog.getOpenFileName(self, "QCoDeS Database", current, filter="DB (*.db)")

        print(db_path)

        if db_path:
            self.dataset_store.db_path = db_path
