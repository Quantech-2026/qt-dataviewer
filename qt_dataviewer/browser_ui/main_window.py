import logging
from datetime import date
from typing import Dict, List, Tuple, Union

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QDesktopWidget

from qt_dataviewer import DatasetViewer
from qt_dataviewer.abstract.dataset_store import DatasetStore, Filter
from qt_dataviewer.abstract.dataset_description import DatasetDescription
from qt_dataviewer.utils.qt_utils import qt_log_exception, qt_init
from .browser_dataset_list import BrowserDatasetList
from .dataset_list import DatasetListView
from .datelist import DateListView
from .filters import TextFilterWidget, ListFilterWidget, KeywordFilterWidget
from .top_bar import TopBar

logger = logging.getLogger(__name__)


_app = None


class DataBrowserBase(QtWidgets.QMainWindow):
    """
    Base class for main window of dataset browser.
    """

    _WINDOW_TITLE: str = "QT Dataset Browser ({0})"

    def __init__(
        self,
        storage_type_name: str,
        dataset_store: DatasetStore,
        source_type_name: str,
        label_keys: Dict[str, str],
        column_definitions: Tuple[str, int],
        sort_by_column: int,
        filters: List[Union[str, Tuple[str, str]]],
    ):
        global _app
        logger.debug("Init QT data browser")

        qt_app_runing = qt_init()
        if not qt_app_runing:
            logger.info("Create Qt application")
            # note: store reference to avoid garbage collection.
            # reference is also used to restart browser 2nd time in Python console.
            _app = QtWidgets.QApplication([])

        super().__init__()

        self.dataset_store = dataset_store
        self._selected_dates: List[date] = []
        self.viewers = []
        self._filter = Filter()
        self._auto_open_plots = False # TODO Configurable.

        self.setWindowTitle(self._WINDOW_TITLE.format(storage_type_name))

        # set window size
        screen = QDesktopWidget().screenGeometry()
        self.resize(int(screen.width() * 0.6), int(screen.height() * 0.6))

        labels = dataset_store.labels

        self.uid_label_text: str = "UID"
        for key, value in label_keys.items():
            if value == "uid":
                self.uid_label_text = key

        self.top_bar = TopBar(self,
                              source_type_name,
                              dataset_store.is_dynamic,
                              uid_label_text=self.uid_label_text)
        top_bar = self.top_bar
        for f in filters:
            if isinstance(f, str):
                if f == "Name":
                    fw = TextFilterWidget("Name", label_keys["Name"])
                    fw.filter_changed.connect(self._set_filter_name)
                else:
                    raise Exception(f"Unknown filter {f}")
            elif isinstance(f, tuple):
                name = f[0]
                ftype = f[1]
                if ftype == 'list':
                    key = label_keys[name]
                    items = labels.get(key, [])
                    fw = ListFilterWidget(name, key, items)
                    fw.filter_changed.connect(self._set_filter_label_value)
                    dataset_store.labels_changed.connect(fw.set_items_from_dict)
                elif ftype == 'keywords':
                    fw = KeywordFilterWidget(name, label_keys[name])
                    fw.filter_changed.connect(self._set_filter_label_values)
                else:
                    raise Exception(f"Unknown filter {f}")

            top_bar.add_filter(fw)

        self.dataset_list_view = DatasetListView(self, column_definitions, label_keys, sort_by_column)
        self.date_list_view = DateListView(self)

        # create splitter for widgets
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.date_list_view)
        splitter.addWidget(self.dataset_list_view)
        splitter.setSizes([80, 820])

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
        self.dataset_list_view.dataset_activated.connect(self.show_dataset)
        self.date_list_view.dates_selected.connect(self.set_date_selection)
        self.top_bar.liveplotting_changed.connect(self._liveplotting_changed)
        self.top_bar.close_all_plots.connect(self.close_all_plots)
        self.top_bar.open_uid.connect(self.open_uid)
        self.dataset_store.dates_changed.connect(self.date_list_view.update_date_list)
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
            logger.info("Run Qt Application")
            _app.exec()
            logger.info("Qt Application event loop exited")

    def browser_started(self):
        logger.debug("load data")
        self.dataset_store.refresh()

    def set_data_source(self, source_name):
        self.top_bar.set_data_source(source_name)

    @QtCore.pyqtSlot(bool)
    def _liveplotting_changed(self, liveplotting: bool) -> None:
        self._auto_open_plots = liveplotting

    @QtCore.pyqtSlot(DatasetDescription)
    def show_dataset(self, ds_description: DatasetDescription) -> None:
        self.setCursor(QtCore.Qt.WaitCursor)
        self.__show_dataset(ds_description)
        self._remove_closed_viewers()
        self.setCursor(QtCore.Qt.ArrowCursor)

    @QtCore.pyqtSlot(str)
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
        if ds is not None:
            datalist = BrowserDatasetList(self.dataset_store, ds_description)
            viewer = DatasetViewer(ds, datalist=datalist)
            self.viewers.append(viewer)

    @QtCore.pyqtSlot()
    def close_all_plots(self) -> None:
        for viewer in self.viewers:
            viewer.close()
        self._remove_closed_viewers()

    def _remove_closed_viewers(self):
        for i in reversed(range(len(self.viewers))):
            if not self.viewers[i].alive:
                self.viewers.pop(i)

    @QtCore.pyqtSlot()
    def reload(self) -> None:
        self.dataset_store.refresh()

    @QtCore.pyqtSlot()
    def _refresh_view(self) -> None:
        self.set_data_source(self.data_store.get_source_name())
        # call selection changed to update list with datasets
        self.date_list_view.date_selection_changed()

    @QtCore.pyqtSlot(list)
    def set_date_selection(self, dates: List[date]) -> None:
        self._selected_dates = dates.copy()
        ds_descriptions = []
        for d in dates:
            ds_descriptions += self.dataset_store.get_dataset_descriptions(d)
        self.dataset_list_view.set_datasets(ds_descriptions)

    @QtCore.pyqtSlot(list)
    def _new_datasets(self, ds_descriptions: List[DatasetDescription]) -> None:
        for dd in ds_descriptions:
            if dd.collected_date in self._selected_dates:
                self.dataset_list_view.add_dataset(dd)
            # TODO resize columns after adding?
        if self._auto_open_plots:
            for dd in ds_descriptions:
                self.show_dataset(dd)

    @QtCore.pyqtSlot(str, str)
    def _set_filter_name(self, key: str, contains: str):
        if not contains:
            # Empty string implies no filter.
            contains = None
        self._filter.name_contains = contains
        self._filter_datasets()

    @QtCore.pyqtSlot(str, str)
    def _set_filter_label_value(self, key: str, value: str):
        if not value:
            # Empty string implies no filter.
            value = None
        self._filter.labels[key] = value
        self._filter_datasets()

    @QtCore.pyqtSlot(str, list)
    def _set_filter_label_values(self, key: str, values: str):
        self._filter.labels[key] = values
        self._filter_datasets()

    def _filter_datasets(self):
        self.dataset_store.set_filter(self._filter)
        # call selection changed to update list with datasets
        self.date_list_view.date_selection_changed()

    def closeEvent(self, event):
        self.dataset_store.dates_changed.disconnect(self.date_list_view.update_date_list)
        self.dataset_store.new_datasets.disconnect(self._new_datasets)
        self.dataset_store.close()
        self.close_all_plots()
