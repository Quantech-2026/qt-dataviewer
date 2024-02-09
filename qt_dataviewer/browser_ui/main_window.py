import logging
from datetime import date
from typing import List, Optional, Tuple, Union

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QDesktopWidget

from qt_dataviewer.abstract.dataset_store import DatasetStore, Filter
from qt_dataviewer.abstract.dataset_description import DatasetDescription
from qt_dataviewer import DatasetViewer
from .browser_dataset_list import BrowserDatasetList
from .dataset_list import DatasetListView
from .datelist import DateListView
from .filters import TextFilterWidget, ListFilterWidget, KeywordFilterWidget
from .top_bar import TopBar

logger = logging.getLogger(__name__)


class DataBrowserBase(QtWidgets.QMainWindow):
    """
    Base class for main window of dataset browser.
    """

    _WINDOW_TITLE: str = "QT Dataset Browser"

    def __init__(
        self,
        dataset_store: DatasetStore,
        source_type_name: str,
        menu_actions: Optional[List[QtWidgets.QAction]],
        column_definitions: Tuple[str, str, int],
        sort_by_column: int,
        filters: List[Union[str, Tuple[str, str]]],
    ):
        super().__init__()

        self.dataset_store = dataset_store
        labels = dataset_store.get_labels()

        self._selected_dates: Tuple[str, ...] = ()
        self.viewers = []
        self._filter = Filter()
        self._auto_open_plots = False # TODO Configurable.

        self.setWindowTitle(self._WINDOW_TITLE)

        # set window size
        screen = QDesktopWidget().screenGeometry()
        self.resize(int(screen.width() * 0.6), int(screen.height() * 0.6))

        self.top_bar = TopBar(self, source_type_name, dataset_store.is_dynamic)
        top_bar = self.top_bar
        for f in filters:
            if isinstance(f, str):
                if f == "Name":
                    fw = TextFilterWidget("Name")
                    fw.filter_changed.connect(self._set_filter_name)
                else:
                    raise Exception(f"Unknown filter {f}")
            elif isinstance(f, tuple):
                name = f[0]
                ftype = f[1]
                if ftype == 'list':
                    items = labels.get(name, [])
                    fw = ListFilterWidget(name, items)
                    fw.filter_changed.connect(self._set_filter_label_value)
                elif ftype == 'keywords':
                    fw = KeywordFilterWidget(name)
                    fw.filter_changed.connect(self._set_filter_label_values)
                else:
                    raise Exception(f"Unknown filter {f}")

            top_bar.add_filter(fw)

        self.dataset_list_view = DatasetListView(self, column_definitions, sort_by_column)
        self.date_list_view = DateListView(self)

        # create splitter for widgets
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.date_list_view)
        splitter.addWidget(self.dataset_list_view)
        splitter.setSizes([80, 820])

        if menu_actions is not None:
            menu = self.menuBar()
            file_menu = menu.addMenu("&File")

            for action in menu_actions:
                file_menu.addAction(action)

            # open_action = QtWidgets.QAction("&Open", self)
            # open_action.setShortcut("Ctrl+O")
            # open_action.triggered.connect(self.configure_datadir)
            # file_menu.addAction(open_action)

            reload_action = QtWidgets.QAction("&Reload", self)
            reload_action.setShortcut("Ctrl+R")
            reload_action.triggered.connect(self.reload)
            file_menu.addAction(reload_action)

            close_plots_action = QtWidgets.QAction("&Close all plots", self)
            close_plots_action.setShortcut("Ctrl+X")
            close_plots_action.triggered.connect(self.close_all_plots)
            file_menu.addAction(close_plots_action)

            exit_action = QtWidgets.QAction("&Exit", self)
            exit_action.setShortcut("Ctrl+Q")
            exit_action.triggered.connect(self.close)
            file_menu.addAction(exit_action)

        # connect signals and slots
        self.dataset_list_view.dataset_activated.connect(self.show_dataset)
        self.date_list_view.dates_selected.connect(self.set_date_selection)
        self.top_bar.liveplotting_changed.connect(self._liveplotting_changed)
        self.top_bar.close_all_plots.connect(self.close_all_plots)
        self.dataset_store.dates_changed.connect(self.date_list_view.update_date_list)
        self.dataset_store.new_datasets.connect(self._new_datasets)

        # set content as central widget
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.top_bar)
        layout.addWidget(splitter)
        layout.setStretchFactor(splitter, 1)
        content.setLayout(layout)

        self.setCentralWidget(content)
        self.show()
        self.dataset_store.refresh()

    def set_data_source(self, source_name):
        self.top_bar.set_data_source(source_name)

    @QtCore.pyqtSlot(bool)
    def _liveplotting_changed(self, liveplotting: bool) -> None:
        self._auto_open_plots = liveplotting

    @QtCore.pyqtSlot(DatasetDescription)
    def show_dataset(self, ds_description: DatasetDescription) -> None:
        self.setCursor(QtCore.Qt.WaitCursor)
        ds = self.dataset_store.get_dataset(ds_description)
        datalist = BrowserDatasetList(self.dataset_store, ds_description)
        viewer = DatasetViewer(ds, datalist=datalist)
        self.viewers.append(viewer)
        self._remove_closed_viewers()
        self.setCursor(QtCore.Qt.ArrowCursor)

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

    @QtCore.pyqtSlot(list)
    def set_date_selection(self, dates: List[date]) -> None:
        ds_descriptions = []
        for d in dates:
            ds_descriptions += self.dataset_store.get_dataset_descriptions(d)
        self.dataset_list_view.set_datasets(ds_descriptions)

    @QtCore.pyqtSlot(list)
    def _new_datasets(self, ds_descriptions: List[DatasetDescription]) -> None:
        for dd in ds_descriptions:
            self.dataset_list_view.add_dataset(dd)
            # TODO resize columns after adding?
        if self._auto_open_plots:
            for dd in ds_descriptions:
                self.show_dataset(dd)

    @QtCore.pyqtSlot(str, str)
    def _set_filter_name(self, name: str, contains: str):
        if not contains:
            # Empty string implies no filter.
            contains = None
        self._filter.name_contains = contains
        self._filter_datasets()

    @QtCore.pyqtSlot(str, str)
    def _set_filter_label_value(self, label_name: str, value: str):
        if not value:
            # Empty string implies no filter.
            value = None
        self._filter.labels[label_name] = value
        self._filter_datasets()

    @QtCore.pyqtSlot(str, list)
    def _set_filter_label_values(self, label_name: str, values: str):
        self._filter.labels[label_name] = values
        self._filter_datasets()

    def _filter_datasets(self):
        self.dataset_store.set_filter(self._filter)
        # call selection changed to update list with datasets
        self.date_list_view.date_selection_changed()

    def closeEvent(self, event):
        self.dataset_store.dates_changed.disconnect(self.date_list_view.update_date_list)
        self.dataset_store.new_datasets.disconnect(self._new_datasets)
        self.close_all_plots()
