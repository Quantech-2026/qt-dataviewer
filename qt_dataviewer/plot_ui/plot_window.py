import json
import logging
import time

from abc import abstractmethod
from datetime import datetime
from functools import partial
from typing import Any

from PyQt5 import QtCore, QtGui, QtWidgets

from qt_dataviewer.model.plot_model import PlotModel
from qt_dataviewer.utils.qt_utils import qt_log_exception
from qt_dataviewer.resources.icons import add_icons_to_checkbox

from .info_widget import InfoWidget
from .plot_settings_panel import PlotSettings
from .pulses_widget import PulsesWidget


logger = logging.getLogger(__name__)


class EventHandler:
    @abstractmethod
    def variable_selection_changed(self, index: int, hidden: bool) -> None:
        pass

    @abstractmethod
    def variable_hidden_changed(self, index: int, hidden: bool) -> None:
        pass


N_PLOT_COLUMNS = 4


class PlotWindow:
    def setup_ui(self, main_window, event_handler: EventHandler,
                 rating_options: str | None = None):
        self._main_window = main_window
        self._event_handler = event_handler
        self._plot_model = None
        self._plot_widgets = {}

        main_window.resize(1500, 900)
        main_window.setMinimumSize(QtCore.QSize(1000, 600))
        self.create_main_layout(main_window, rating_options)

    def create_main_layout(self, main_window, rating_options: str | None):
        central_widget = QtWidgets.QWidget(main_window)
        central_layout = QtWidgets.QVBoxLayout(central_widget)
        central_layout.setContentsMargins(2, 2, 2, 2)
        central_layout.setSpacing(0)

        top_layout = self.create_top_layout(rating_options)
        central_layout.addLayout(top_layout)

        # add tab widget
        tabs = QtWidgets.QTabWidget()
        self.tab_widget = tabs
        self.create_plots_tab(tabs)
        self.create_info_tab(tabs)
        self.create_pulses_tab(tabs)
        tabs.currentChanged.connect(self._current_tab_changed)
        central_layout.addWidget(tabs)

        main_window.setCentralWidget(central_widget)
        self.lb_variables.setFocus()

    def create_top_layout(self, rating_options: str | None):
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addSpacing(10)
        top_layout.setSpacing(4)
        font = get_font(13)
        self.label_name = QtWidgets.QLabel()
        self.label_name.setMinimumSize(QtCore.QSize(250, 0))
        self.label_name.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.label_name.setFont(font)
        self.label_name.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        top_layout.addWidget(self.label_name, stretch=10)

        if rating_options:
            self.rating_widget = RatingWidget(
                star="star" in rating_options,
                hide="hide" in rating_options)
            self.rating_widget.rating_changed.connect(self.rating_changed)
            top_layout.addWidget(self.rating_widget)
        else:
            self.rating_widget = None

        font = get_font(10)

        self.label_uuid = QtWidgets.QLabel()
        self.label_uuid.setMinimumSize(QtCore.QSize(160, 0))
        self.label_uuid.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_uuid.setFont(font)
        top_layout.addWidget(self.label_uuid)

        self.label_datetime = QtWidgets.QLabel()
        self.label_datetime.setMinimumSize(QtCore.QSize(130, 0))
        self.label_datetime.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_datetime.setFont(font)
        top_layout.addWidget(self.label_datetime)

        self.btnPrevious = QtWidgets.QPushButton('Previous')
        self.btnPrevious.setToolTip("Load previous dataset (Ctrl+Left)")
        self.btnPrevious.setMinimumSize(QtCore.QSize(80, 0))
        # TODO cleanup interface PlotWindow vs DataViewer.
        self.btnPrevious.setVisible(self.datalist is not None)  # And get_next not abstract.
        self.btnPrevious.clicked.connect(self._get_previous)
        top_layout.addWidget(self.btnPrevious)

        self.btnNext = QtWidgets.QPushButton('Next')
        self.btnNext.setToolTip("Load next dataset (Ctrl+Right)")
        self.btnNext.setMinimumSize(QtCore.QSize(80, 0))
        self.btnNext.setVisible(self.datalist is not None)
        self.btnNext.clicked.connect(self._get_next)
        top_layout.addWidget(self.btnNext)

        self.btnLatest = QtWidgets.QPushButton('Latest')
        self.btnLatest.setMinimumSize(QtCore.QSize(80, 0))
        self.btnLatest.setVisible(self.datalist is not None and self.datalist.implements("get_latest"))
        self.btnLatest.setCheckable(True)
        self.btnLatest.setStyleSheet("QPushButton:checked { background-color: #ffc000; color: black }")
        self.btnLatest.clicked.connect(self._latest_clicked)
        top_layout.addWidget(self.btnLatest)

        self._timer_latest = QtCore.QTimer()
        self._timer_latest.timeout.connect(self._get_latest)
        self._timer_latest.setSingleShot(True)
        self._timer_latest.setInterval(100)

        self._shortcut_next = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Right"), self)
        self._shortcut_next.activated.connect(self._get_next)
        self._shortcut_previous = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Left"), self)
        self._shortcut_previous.activated.connect(self._get_previous)

        # @@@ allow change name
        return top_layout

    @qt_log_exception
    def rating_changed(self, rating: int):
        ...

    @qt_log_exception
    def _get_next(self, checked: bool = None):
        if self.datalist is not None:
            self._update_buttons()
            if not self.datalist.has_next():
                QtWidgets.QToolTip.showText(self.mapToGlobal(self.btnNext.pos() + QtCore.QPoint(0, 10)),
                                            'No more data', self.btnNext,
                                            QtCore.QRect(), 500)
            else:
                try:
                    t0 = time.perf_counter()
                    self.setCursor(QtCore.Qt.WaitCursor)
                    ds = self.datalist.get_next()
                    self.set_ds(ds)
                finally:
                    self.setCursor(QtCore.Qt.ArrowCursor)
                    t1 = time.perf_counter()
                    # print(f"Next {(t1-t0)*1000:.1f} ms")

    @qt_log_exception
    def _get_previous(self, checked: bool = None):
        if self.datalist is not None:
            self._update_buttons()
            if not self.datalist.has_previous():
                QtWidgets.QToolTip.showText(self.mapToGlobal(self.btnPrevious.pos() + QtCore.QPoint(0, 10)),
                                            'No more data', self.btnPrevious,
                                            QtCore.QRect(), 500)
            else:
                try:
                    t0 = time.perf_counter()
                    self.setCursor(QtCore.Qt.WaitCursor)
                    ds = self.datalist.get_previous()
                    self.set_ds(ds)
                finally:
                    self.setCursor(QtCore.Qt.ArrowCursor)
                    t1 = time.perf_counter()
                    # print(f"Prev {(t1-t0)*1000:.1f} ms")

    @qt_log_exception
    def _latest_clicked(self, checked: bool):
        if self.datalist is not None:
            self._update_buttons(uncheck_latest=False)

    @QtCore.pyqtSlot()
    def _get_latest(self):
        if self.btnLatest.isChecked():
            try:
                retrieve_latest = not self.datalist.is_latest()
            except StopIteration:
                retrieve_latest = False
            if retrieve_latest:
                try:
                    self.setCursor(QtCore.Qt.WaitCursor)
                    ds = self.datalist.get_latest()
                    self.set_ds(ds)
                finally:
                    self.setCursor(QtCore.Qt.ArrowCursor)
            self._timer_latest.start()

    def _update_buttons(self, uncheck_latest=True):
        if uncheck_latest:
            self.btnLatest.setChecked(False)
        if self.btnLatest.isChecked():
            self._timer_latest.start()
        else:
            self._timer_latest.stop()

    def create_plots_tab(self, tabs): # @@@ Move to separate class
        plots_widget = QtWidgets.QWidget()
        self.plots_widget = plots_widget
        # Horizontal: panel, line, grid with plots, spacer
        h_layout = QtWidgets.QHBoxLayout(plots_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(2)

        scroll_area = QtWidgets.QScrollArea()
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        # size_policy.setHeightForWidth(scroll_area.sizePolicy().hasHeightForWidth())
        scroll_area.setSizePolicy(size_policy)
        scroll_area.setMinimumWidth(380)
        scroll_area.setMaximumWidth(380)
        scroll_area.setWidgetResizable(True)
        scroll_widget = QtWidgets.QWidget()
        scroll_area.setWidget(scroll_widget)

        cpanel_layout = QtWidgets.QVBoxLayout(scroll_widget)
        cpanel_layout.setContentsMargins(2, 2, 2, 2)
        cpanel_layout.setSpacing(2)

        cb_layout = QtWidgets.QHBoxLayout()
        cb_layout.setContentsMargins(5, 2, 4, 4)
        cb_only_selected = QtWidgets.QCheckBox("Single chart (the selected)")
        cb_only_selected.toggled.connect(self._only_selected_changed)
        self.cb_only_selected = cb_only_selected
        cb_layout.addWidget(cb_only_selected)
        cpanel_layout.addLayout(cb_layout)

        lb_variables = QtWidgets.QListWidget()
        lb_variables.setMinimumSize(QtCore.QSize(300, 200))
        lb_variables.setMaximumSize(QtCore.QSize(400, 300))
        lb_variables.itemSelectionChanged.connect(self._variable_selection_changed)
        lb_variables.itemChanged.connect(self._variable_item_changed)
        self.lb_variables = lb_variables

        cpanel_layout.addWidget(lb_variables, 1)

        settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout = settings_layout
        self.current_settings_widget = None
        cpanel_layout.addLayout(settings_layout)

        cpanel_layout.addSpacerItem(
            QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.MinimumExpanding))

        h_layout.addWidget(scroll_area)

        # plots panel: Grid
        zelf = self

        class MyScrollArea(QtWidgets.QScrollArea):
            def resizeEvent(self,  event: QtGui.QResizeEvent):
                super().resizeEvent(event)
                zelf._update_grid_stretch()

        scroll_area = MyScrollArea()
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        scroll_area.setSizePolicy(size_policy)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(QtWidgets.QFrame.NoFrame)
        scroll_widget = QtWidgets.QWidget()
        scroll_area.setWidget(scroll_widget)
        self._plot_scroll_area = scroll_area

        plots_layout = QtWidgets.QGridLayout(scroll_widget)
        plots_layout.setSpacing(2)
        plots_layout.setContentsMargins(0, 0, 0, 0)
        self.plots_layout = plots_layout

        h_layout.addWidget(scroll_area, 1)

        tabs.addTab(plots_widget, "Plots")

    def _selected_row(self):
        selected = self.lb_variables.selectedIndexes()
        if len(selected) == 0:
            return None
        return selected[0].row()

    @qt_log_exception
    def _only_selected_changed(self, checked):
        selected_row = self._selected_row()
        if selected_row is None:
            return
        selected = self.lb_variables.selectedIndexes()[0].row()
        layout = self.plots_layout

        nplots = 0
        for seq_nr, widget in sorted(self._plot_widgets.items()):
            if (int(seq_nr) == selected) or not checked:
                irow, icol = divmod(nplots, N_PLOT_COLUMNS)
                layout.addWidget(widget, irow, icol)
                widget.setVisible(True)
                nplots += 1
            else:
                widget.setVisible(False)

        self._update_grid_stretch()

    @qt_log_exception
    def _variable_selection_changed(self):
        selected_row = self._selected_row()
        if selected_row is None:
            return
        selected_item = self.lb_variables.selectedItems()[0]
        hidden = selected_item.checkState() != QtCore.Qt.Checked
        self._event_handler.variable_selection_changed(selected_row, hidden)
        self._update_plot_borders()
        if self.cb_only_selected.isChecked():
            layout = self.plots_layout
            selected_row
            nplots = 0
            for seq_nr, widget in self._plot_widgets.items():
                if int(seq_nr) == selected_row:
                    irow, icol = divmod(nplots, N_PLOT_COLUMNS)
                    layout.addWidget(widget, irow, icol)
                    widget.setVisible(True)
                    nplots += 1
                else:
                    widget.setVisible(False)
            self._update_grid_stretch()

    def _update_plot_borders(self):
        # Highlight plot
        for i in range(self.lb_variables.count()):
            selected = self.lb_variables.item(i).isSelected()
            try:
                widget = self._plot_widgets[i]
            except KeyError:
                pass
            else:
                if selected:
                    widget.setStyleSheet('QFrame {border-width: 0} QFrame[frameShape="2"] {border-width: 2}')
                    widget.layout().setContentsMargins(4, 4, 6, 4)
                    self._plot_scroll_area.ensureWidgetVisible(widget)
                else:
                    widget.setStyleSheet('QFrame {border-width: 0} QFrame[frameShape="2"] {border-width: 1}')
                    widget.layout().setContentsMargins(5, 5, 7, 5)

    @qt_log_exception
    def _variable_item_changed(self, item):
        hidden = item.checkState() != QtCore.Qt.Checked
        index = self.lb_variables.indexFromItem(item).row()
        self._event_handler.variable_hidden_changed(index, hidden)
        selected_row = self._selected_row()
        if selected_row == index and self.current_settings_widget is not None:
            self.current_settings_widget.setVisible(not hidden)

    def create_info_tab(self, tabs):
        info_widget = InfoWidget()
        self.info_widget = info_widget
        tabs.addTab(info_widget, "Info")

    def create_pulses_tab(self, tabs):
        pulses_widget = PulsesWidget()
        self.pulses_widget = pulses_widget
        tabs.addTab(pulses_widget, "Pulses")

    def set_dataset_info(self, name, uuid_str: str, start_time: datetime, rating: int):
        if len(name) > 80:
            name = name[:80] + '...'
        start_time_str = f"{start_time:%H:%M:%S %Y-%m-%d}" if start_time else "--:--:-- ____-__-__"
        self.setWindowTitle(f'{name}  {start_time_str}  {uuid_str}')

        self.label_name.setText(name)
        self.label_uuid.setText(uuid_str)
        start_time_str = f"{start_time:%Y-%m-%d %H:%M:%S}" if start_time else "____-__-__ --:--:--"
        self.label_datetime.setText(f'{start_time_str}')
        if self.rating_widget:
            self.rating_widget.set_rating(rating)

    def set_details_info(self, details_list: list[tuple[str, str]]):
        self.info_widget.set_info(details_list)

    def set_snapshot(self, snapshot: None | str | dict[str, Any]):
        if isinstance(snapshot, str):
            tree_data = json.loads(snapshot)
        elif isinstance(snapshot, dict):
            tree_data = snapshot
        elif snapshot is None:
            tree_data = None
        else:
            raise Exception(f"Unknown snapshot type: {type(snapshot)}")

        self.info_widget.set_snapshot(tree_data)
        self._set_pulses(tree_data)

    def _set_pulses(self, snapshot_tree):
        pulses = None
        if snapshot_tree:
            try:
                pulses = snapshot_tree['measurement']['sequence']
                _ = pulses['pc0']
            except KeyError:
                pulses = None
        self.pulses_widget.set_pulses(pulses)
        self.tab_widget.setTabVisible(2, pulses is not None)

    @qt_log_exception
    def _current_tab_changed(self, current_index: int):
        self.pulses_widget.set_active(current_index == 2)

    def clear_variables(self):
        if self.current_settings_widget is not None:
            self.current_settings_widget.deleteLater()
            self.current_settings_widget = None
        for widget in self._plot_widgets.values():
            widget.deleteLater()
        self._plot_widgets = {}
        for i in reversed(range(self.plots_layout.count())):
            widget = self.plots_layout.itemAt(i).widget()
            widget.deleteLater()

        for i in range(self.settings_layout.count()):
            widget = self.settings_layout.itemAt(i).widget()
            widget.deleteLater()
        self.lb_variables.clear()

    def add_variable(self, name: str, hidden: bool):
        self.lb_variables.addItem(name)
        item = self.lb_variables.item(self.lb_variables.count()-1)
        if self.lb_variables.count() == 1:
            item.setSelected(True)
        item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(QtCore.Qt.Unchecked if hidden else QtCore.Qt.Checked)

    def set_no_data_message(self):
        widget = QtWidgets.QFrame(self)
        widget.setMinimumWidth(250)
        widget.setMinimumHeight(250)
        widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        widget.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        widget_layout = QtWidgets.QVBoxLayout(widget)
        widget_layout.setContentsMargins(5, 5, 7, 5)
        widget_layout.setSpacing(0)

        label_msg = QtWidgets.QLabel("No measurement data (yet)")
        label_msg.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label_msg.setFont(get_font(12))
        widget_layout.addWidget(label_msg)
        self.plots_layout.addWidget(widget, 0, 0)
        self._update_grid_stretch()

    def show_settings(self, index: int, plot_model: PlotModel, hidden: bool):
        if self.current_settings_widget is not None:
            self.current_settings_widget.deleteLater()

        settings_widget = PlotSettings(plot_model)
        self.settings_layout.addWidget(settings_widget)
        settings_widget.setVisible(not hidden)
        self.current_settings_widget = settings_widget

    def add_plot(self, title: str, seq_nr: float):
        logger.debug(f"Add {title}")
        if seq_nr in self._plot_widgets:
            raise Exception(f"Duplicate plot {seq_nr}")
        layout = self.plots_layout

        # Move plots to insert at right position
        seq_nrs = sorted(self._plot_widgets.keys())
        plot_index = len(seq_nrs)
        for i, n in reversed(list(enumerate(seq_nrs))):
            if n < seq_nr:
                break
            plot_index = i
            irow, icol = divmod(i, N_PLOT_COLUMNS)
            widget = self._plot_widgets[n]
            irow, icol = divmod(i+1, N_PLOT_COLUMNS)
            layout.addWidget(widget, irow, icol)

        widget = ClickFrame(self)
        widget.setMinimumWidth(250)
        widget.setMinimumHeight(250)
        widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        widget.setFrameStyle(QtWidgets.QFrame.Panel)
        widget.onMousePressed(partial(self._mouse_clicked, seq_nr=seq_nr))
        widget_layout = QtWidgets.QVBoxLayout(widget)
        widget_layout.setContentsMargins(5, 5, 7, 5)
        widget_layout.setSpacing(0)

        label_title = QtWidgets.QLabel(title)
        label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        label_title.setFont(get_font(10))
        widget_layout.addWidget(label_title)

        plot_layout = QtWidgets.QVBoxLayout()
        plot_layout.setSpacing(4)
        widget_layout.addLayout(plot_layout, stretch=1)

        if self.cb_only_selected.isChecked():
            selected = self.lb_variables.selectedIndexes()[0].row()
            plot_index = 0  # TODO not correct with sub-plots (cross-hair slicing)
            if int(seq_nr) != selected:
                widget.setVisible(False)
        irow, icol = divmod(plot_index, N_PLOT_COLUMNS)
        layout.addWidget(widget, irow, icol)

        self._plot_widgets[seq_nr] = widget

        self._update_grid_stretch()
        self._update_plot_borders()

        return plot_layout

    def _mouse_clicked(self, *args, seq_nr=None, **kwargs):
        self.lb_variables.item(int(seq_nr)).setSelected(True)

    def remove_plot(self, seq_nr: float):
        if seq_nr not in self._plot_widgets:
            return
        layout = self.plots_layout

        widget = self._plot_widgets[seq_nr]
        widget.deleteLater()
        del self._plot_widgets[seq_nr]

        # Move plots to fill empty spot
        seq_nrs = sorted(self._plot_widgets.keys())
        for i, n in enumerate(seq_nrs):
            if n > seq_nr:
                widget = self._plot_widgets[n]
                irow, icol = divmod(i, N_PLOT_COLUMNS)
                layout.addWidget(widget, irow, icol)

        self._update_grid_stretch()

    def _update_grid_stretch(self):
        if self.cb_only_selected.isChecked():
            selected = self.lb_variables.selectedIndexes()[0].row()
            nplots = 0
            for seq_nr, widget in self._plot_widgets.items():
                if int(seq_nr) == selected:
                    nplots += 1
        else:
            nplots = len(self._plot_widgets)

        n_rows = (nplots - 1) // N_PLOT_COLUMNS + 1
        row_height = int(self._plot_scroll_area.width() / 4 * 0.8)
        layout = self.plots_layout
        for icol in range(N_PLOT_COLUMNS):
            layout.setColumnStretch(icol, 1 if icol < nplots else 0)
        for irow in range(n_rows):
            layout.setRowMinimumHeight(irow, row_height)
            layout.setRowStretch(irow, 1)
        for irow in range(n_rows, layout.rowCount()):
            layout.setRowMinimumHeight(irow, 0)
            layout.setRowStretch(irow, 0)


def get_font(point_size):
    font = QtGui.QFont()
    font.setPointSize(point_size)
    return font


class ClickFrame(QtWidgets.QFrame):

    def onMousePressed(self, func):
        self._mousePressed = func

    def mousePressEvent(self, mouseEvent: QtGui.QMouseEvent):
        try:
            func = self._mousePressed
        except AttributeError:
            pass
        else:
            func(mouseEvent)
        super().mousePressEvent(mouseEvent)


class RatingWidget(QtWidgets.QWidget):
    rating_changed = QtCore.pyqtSignal(int)

    def __init__(self, name: str = "", star: bool = False, hide: bool = False):
        super().__init__()
        self.name = name
        self._rating = 0

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        label = QtWidgets.QLabel(name)
        layout.addWidget(label, 0)

        self._updating = False
        if star:
            cb_star = QtWidgets.QCheckBox("")
            add_icons_to_checkbox(cb_star, "Starred.png", "StarWhite.png", 24)
            cb_star.stateChanged.connect(self._star_changed)
            self.cb_star = cb_star
            layout.addWidget(cb_star, 0)
        else:
            self.cb_star = None
        if hide:
            cb_hide = QtWidgets.QCheckBox("")
            add_icons_to_checkbox(cb_hide, "Hidden.png", "HideWhite.png", 24)
            cb_hide.stateChanged.connect(self._hide_changed)
            self.cb_hide = cb_hide
            layout.addWidget(cb_hide, 0)
        else:
            self.cb_hide = None

    def set_rating(self, rating: int):
        self._updating = True
        self._rating = rating
        if self.cb_star:
            self.cb_star.setCheckState(QtCore.Qt.Checked if rating > 0 else QtCore.Qt.Unchecked)
        if self.cb_hide:
            self.cb_hide.setCheckState(QtCore.Qt.Checked if rating < 0 else QtCore.Qt.Unchecked)
        self._updating = False

    @QtCore.pyqtSlot(int)
    def _star_changed(self, state: QtCore.Qt.CheckState) -> None:
        if self._updating:
            return
        if state == QtCore.Qt.Checked:
            self._rating = +1
            if self.cb_hide:
                self.cb_hide.setCheckState(QtCore.Qt.Unchecked)
            self.rating_changed.emit(self._rating)
        elif self._rating == +1:
            self._rating = 0
            self.rating_changed.emit(self._rating)

    @QtCore.pyqtSlot(int)
    def _hide_changed(self, state: QtCore.Qt.CheckState) -> None:
        if self._updating:
            return
        if state == QtCore.Qt.Checked:
            self._rating = -1
            if self.cb_star:
                self.cb_star.setCheckState(QtCore.Qt.Unchecked)
            self.rating_changed.emit(self._rating)
        elif self._rating == -1:
            self._rating = 0
            self.rating_changed.emit(self._rating)
