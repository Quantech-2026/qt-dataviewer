import logging
import os
from datetime import date

from qtpy import QtCore, QtWidgets

from qt_dataviewer import DatasetViewer
from qt_dataviewer.abstract.dataset_description import DatasetDescription
from qt_dataviewer.browser_ui.dataset_list_view import DatasetListView
from qt_dataviewer.browser_ui.top_bar import TopBar
from qt_dataviewer.dataset_files.dataset_list import FileBrowserDatasetList
from qt_dataviewer.dataset_files.dataset_store import FileDataStore
from qt_dataviewer.dataset_files.directory_tree_view import DirectoryTreeView
from qt_dataviewer.utils.qt_utils import (
    qt_log_exception,
    qt_init,
    qt_create_app,
    qt_run_app,
    qt_set_darkstyle,
)


logger = logging.getLogger(__name__)


_app = None


class DataFileBrowser(QtWidgets.QMainWindow):
    """
    Dataset file browser.
    """

    _WINDOW_TITLE: str = "QT Dataset File Browser"

    def __init__(
        self,
        path: str | None = None,
        gui_style: str | None = None
    ):
        """Creates DataFileBrowser

        Args:
            path: base directory. If None uses current working directory.
            gui_style: if "dark" uses dark style, otherwise normal style.
        """
        global _app
        logger.debug("Init QT data file browser")

        qt_app_runing = qt_init()
        if not qt_app_runing:
            # note: store reference to avoid garbage collection.
            # reference is also used to restart browser 2nd time in Python console.
            _app = qt_create_app()

        if gui_style == "dark":
            qt_set_darkstyle()

        super().__init__()

        if path is None:
            path = os.getcwd()
        self.dataset_store = FileDataStore(path)
        self._selected_dates: list[date] = []
        self.viewers = []

        self.setWindowTitle(self._WINDOW_TITLE)

        # set window size
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.7), int(screen.height() * 0.7))

        label_keys = {
            "UID": "uid",
            "Date": "date",
            "Time": "time",
            "Name": "name",
            "App.": "application",
            }
        column_definitions = [
            ("UID", ),
            ("Date", ),
            ("Time", ),
            ("Name", ),
            ("App.", ),
            ]
        sort_by_column = 0
        self.uid_label_text = "UID"
        for key, value in label_keys.items():
            if value == "uid":
                self.uid_label_text = key

        source_type_name = "Folder"
        self.top_bar = TopBar(self,
                              source_type_name,
                              False,
                              uid_label_text=self.uid_label_text)

        self.dataset_list_view = DatasetListView(self, column_definitions, label_keys, sort_by_column)

        self.directory_tree = DirectoryTreeView(self.dataset_store)

        # create splitter for widgets
        splitter = QtWidgets.QSplitter()

        splitter.addWidget(self.directory_tree)
        splitter.addWidget(self.dataset_list_view)
        splitter.setSizes([200, 820])

        menu_actions = self.get_menu_actions()
        if menu_actions is not None:
            menu = self.menuBar()
            file_menu = menu.addMenu("&File")

            for action in menu_actions:
                file_menu.addAction(action)

            reload_action = QtWidgets.QAction("&Reload", self)
            reload_action.setShortcut("F5")
            reload_action.triggered.connect(self.reload)
            file_menu.addAction(reload_action)

        # connect signals and slots
        self.directory_tree.path_changed.connect(self._select_path)
        self.dataset_list_view.dataset_activated.connect(self.show_dataset)
        self.top_bar.close_all_plots.connect(self.close_all_plots)
        self.top_bar.open_uid.connect(self.open_uid)

        self.dataset_store.new_datasets.connect(self._new_datasets)
        self.dataset_store.datasets_changed.connect(self._refresh_view)

        # set content as central widget
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.top_bar)
        layout.addWidget(splitter)
        layout.setStretchFactor(splitter, 1)
        content.setLayout(layout)

        self.setCentralWidget(content)
        self.show()
        self.browser_started()

        if _app is not None:
            qt_run_app(_app)

    def browser_started(self):
        logger.debug("load data")
        self.dataset_store.refresh()

    def get_menu_actions(self):
        actions = []
        open_action = QtWidgets.QAction("&Open data directory", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._select_data_dir)
        actions.append(open_action)
        return actions

    @QtCore.Slot()
    def _select_data_dir(self):
        current = self.dataset_store.base_dir
        if current is None:
            current = ''

        data_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Base directory', current)

        if data_dir:
            self.directory_tree.clear()
            self.dataset_store.set_base_dir(data_dir)

    def set_data_source(self, source_name):
        self.top_bar.set_data_source(source_name)

    @QtCore.Slot(str)
    def _select_path(self, path: str):
        if path == "":
            self.dataset_list_view.set_datasets([])
        else:
            ds_descriptions = self.dataset_store.get_dataset_descriptions(path)
            self.dataset_list_view.set_datasets(ds_descriptions)

    @QtCore.Slot(DatasetDescription)
    def show_dataset(self, ds_description: DatasetDescription) -> None:
        self.setCursor(QtCore.Qt.WaitCursor)
        self.__show_dataset(ds_description)
        self._remove_closed_viewers()
        self.setCursor(QtCore.Qt.ArrowCursor)

    @QtCore.Slot(str)
    def open_uid(self, uid):
        try:
            ds_description = self.dataset_store.get_dataset_description_for_uid(uid)
            if ds_description is None:
                self._show_error_message(
                    "Dataset not found",
                    f"Dataset '{uid}' not found")
            else:
                self.show_dataset(ds_description)
        except Exception:
            logger.error(f"Failed to open dataset {uid}", exc_info=True)
            self._show_error_message(
                "Failure opening dataset",
                f"Unexpected error opening '{uid}'. See logging.")

    def _show_error_message(self, title, message):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("QT-DataBrowser: " + title)
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg.exec_()

    @qt_log_exception
    def __show_dataset(self, ds_description: DatasetDescription) -> None:
        ds = self.dataset_store.get_dataset(ds_description)
        self.current_ds = ds
        if ds is not None:
            datalist = FileBrowserDatasetList(self.dataset_store, ds_description)
            viewer = DatasetViewer(ds, datalist=datalist)
            self.viewers.append(viewer)

    @QtCore.Slot()
    def close_all_plots(self) -> None:
        for viewer in self.viewers:
            viewer.close()
        self._remove_closed_viewers()

    def _remove_closed_viewers(self):
        for i in reversed(range(len(self.viewers))):
            viewer = self.viewers[i]
            if not viewer.alive:
                self.viewers.pop(i)

    @QtCore.Slot()
    def reload(self) -> None:
        self.dataset_store.refresh()

    @QtCore.Slot()
    def _refresh_view(self) -> None:
        self.set_data_source(self.dataset_store.source_name)
        self.directory_tree.refresh()

    @QtCore.Slot(list)
    def _new_datasets(self, ds_descriptions: list[DatasetDescription]) -> None:
        for dd in ds_descriptions:
            if dd.collected_date in self._selected_dates:
                self.dataset_list_view.add_dataset(dd)

    def closeEvent(self, event):
        self.close_all_plots()
        self.dataset_store.new_datasets.disconnect(self._new_datasets)
        self.dataset_store.close()
