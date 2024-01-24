import json
import logging
import time
import traceback
from abc import abstractmethod
from collections.abc import Mapping, Sequence
from datetime import datetime
from functools import partial
from typing import List, Tuple, Union, Dict, Any

from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import numpy as np

from qt_dataviewer.model.plot_model import PlotModel
from qt_dataviewer.utils.qt_utils import qt_log_exception
from .plot_settings_panel import PlotSettings


logger = logging.getLogger(__name__)

# default colors cycle: see matplotlib CN colors.
color_cycle = [
    '#1f77b4',  # muted blue
    '#ff7f0e',  # safety orange
    '#2ca02c',  # cooked asparagus green
    '#d62728',  # brick red
    '#9467bd',  # muted purple
    '#8c564b',  # chestnut brown
    '#e377c2',  # raspberry yogurt pink
    '#7f7f7f',  # middle gray
    '#bcbd22',  # curry yellow-green
    '#17becf'   # blue-teal
]

color_list = [pg.mkColor(cl) for cl in color_cycle]


class EventHandler:
    @abstractmethod
    def variable_selection_changed(self, index: int, hidden: bool) -> None:
        pass

    @abstractmethod
    def variable_hidden_changed(self, index: int, hidden: bool) -> None:
        pass


N_PLOT_COLUMNS = 4

class PlotWindow:
    def setup_ui(self, main_window, event_handler: EventHandler):
        self._main_window = main_window
        self._event_handler = event_handler
        self._plot_model = None
        self._plot_widgets = {}

        main_window.resize(1500, 900)
        main_window.setMinimumSize(QtCore.QSize(1000, 600))
        self.create_main_layout(main_window)

    def create_main_layout(self, main_window):
        central_widget = QtWidgets.QWidget(main_window)
        central_layout = QtWidgets.QVBoxLayout(central_widget)
        central_layout.setContentsMargins(2, 2, 2, 2)
        central_layout.setSpacing(0)

        top_layout = self.create_top_layout()
        central_layout.addLayout(top_layout)

        # add tab widget
        tabs = QtWidgets.QTabWidget()
        self.tab_widget = tabs
        self.create_plots_tab(tabs)
        self.create_info_tab(tabs)
        self.create_pulses_tab(tabs)
        central_layout.addWidget(tabs)

        main_window.setCentralWidget(central_widget)
        self.lb_variables.setFocus()

    def create_top_layout(self):
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
        self.btnPrevious.setMinimumSize(QtCore.QSize(80, 0))
        self.btnPrevious.setVisible(self.datalist is not None) # And has_next not abstract.
        self.btnPrevious.clicked.connect(self._select_previous)
        top_layout.addWidget(self.btnPrevious)
        self.btnNext = QtWidgets.QPushButton('Next')
        self.btnNext.setMinimumSize(QtCore.QSize(80, 0))
        self.btnNext.setVisible(self.datalist is not None)
        self.btnNext.clicked.connect(self._select_next)
        top_layout.addWidget(self.btnNext)
        # @@@ hamburger
        # @@@ add star
        # @@@ allow change name
        return top_layout

    @qt_log_exception
    def _select_next(self, checked: bool):
        if self.datalist is not None:
            if not self.datalist.has_next():
                QtWidgets.QToolTip.showText(self.mapToGlobal(self.btnNext.pos() + QtCore.QPoint(0, 10)),
                                            'No more data', self.btnNext,
                                            QtCore.QRect(), 500)
            else:
                try:
                    t0 = time.perf_counter()
                    self.setCursor(QtCore.Qt.WaitCursor)
                    self.datalist.select_next()
                finally:
                    self.setCursor(QtCore.Qt.ArrowCursor)
                    t1 = time.perf_counter()
                    # print(f"Next {(t1-t0)*1000:.1f} ms")

    @qt_log_exception
    def _select_previous(self, checked: bool):
        if self.datalist is not None:
            if not self.datalist.has_previous():
                QtWidgets.QToolTip.showText(self.mapToGlobal(self.btnPrevious.pos() + QtCore.QPoint(0, 10)),
                                            'No more data', self.btnPrevious,
                                            QtCore.QRect(), 500)
            else:
                try:
                    t0 = time.perf_counter()
                    self.setCursor(QtCore.Qt.WaitCursor)
                    self.datalist.select_previous()
                finally:
                    self.setCursor(QtCore.Qt.ArrowCursor)
                    t1 = time.perf_counter()
                    # print(f"Prev {(t1-t0)*1000:.1f} ms")

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
        scroll_area.setMinimumWidth(350)
        scroll_area.setMaximumWidth(350)
        scroll_area.setWidgetResizable(True)
        scroll_widget = QtWidgets.QWidget()
        scroll_area.setWidget(scroll_widget)

        cpanel_layout = QtWidgets.QVBoxLayout(scroll_widget)
        cpanel_layout.setContentsMargins(2, 2, 2, 2)
        cpanel_layout.setSpacing(2)

        cb_layout = QtWidgets.QHBoxLayout()
        cb_layout.setContentsMargins(5, 2, 4, 4)
        cb_only_selected = QtWidgets.QCheckBox("Show 1 chart (the selected)")
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

        plots_layout = QtWidgets.QGridLayout(scroll_widget) # @@@ Create dynamic flow layout
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

        self.plots_widget.setUpdatesEnabled(False)
        for seq_nr, widget in self._plot_widgets.items():
            widget.setVisible(not checked or (int(seq_nr) == selected))

        nplots = 0
        for seq_nr, widget in sorted(self._plot_widgets.items()):
            if (int(seq_nr) == selected) or not checked:
                irow, icol = divmod(nplots, N_PLOT_COLUMNS)
                layout.addWidget(widget, irow, icol)
                nplots += 1

        self._update_grid_stretch()
        self.plots_widget.setUpdatesEnabled(True)

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
            self.plots_widget.setUpdatesEnabled(False) # @@@ decorator for nested updates
            selected_row
            nplots = 0
            for seq_nr, widget in self._plot_widgets.items():
                widget.setVisible(int(seq_nr) == selected_row)
                if int(seq_nr) == selected_row:
                    irow, icol = divmod(nplots, N_PLOT_COLUMNS)
                    layout.addWidget(widget, irow, icol)
                    nplots += 1
            self._update_grid_stretch()
            self.plots_widget.setUpdatesEnabled(True)

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
                    widget.setFrameStyle(QtWidgets.QFrame.Panel)
                    widget.setLineWidth(2)
                    widget.layout().setContentsMargins(4, 4, 6, 4)
                    self._plot_scroll_area.ensureWidgetVisible(widget)
                else:
                    widget.setFrameStyle(QtWidgets.QFrame.StyledPanel)
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
        info_widget = QtWidgets.QWidget()
        # Horizontal: panel, line, grid with plots, spacer
        h_layout = QtWidgets.QHBoxLayout(info_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(2)

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.setContentsMargins(2, 2, 2, 2)
        left_layout.setSpacing(2)

        h_layout.addLayout(left_layout)

        details_widget = QtWidgets.QFrame()
        details_widget.setMinimumWidth(350)
        details_widget.setMaximumWidth(350)
        details_widget.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        details_layout = QtWidgets.QGridLayout(details_widget)
        self.details_layout = details_layout

        left_layout.addWidget(details_widget)

        left_layout.addSpacerItem(
            QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        # TODO ?
        # compact view
        # qc circuit
        # qc settings
        # gates
        # virtual matrix
        # plot sequence
        tree = QtWidgets.QTreeWidget(self)
        tree.setMinimumSize(QtCore.QSize(340, 600))
        tree.setColumnCount(2)
        tree.setColumnWidth(0, 200)
        tree.setHeaderLabels(['Path', 'Value'])
        self.snapshot_tree = tree

        h_layout.addWidget(tree, 1)

        h_layout.addSpacerItem(
            QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        tabs.addTab(info_widget, "Info")

    def create_pulses_tab(self, tabs):
        pulses_widget = QtWidgets.QWidget()
        pulses_layout = QtWidgets.QVBoxLayout(pulses_widget)
        self.pulses_layout = pulses_layout

        tabs.addTab(pulses_widget, "Pulses")

    def set_dataset_info(self, name, uuid_str: str, start_time: datetime):
        if len(name) > 80:
            name = name[:80] + '...'
        start_time_str = f"{start_time:%H:%M:%S %Y-%m-%d}" if start_time else "--:--:-- ____-__-__"
        self.setWindowTitle(f'{name}  {start_time_str}  {uuid_str}')

        self.label_name.setText(name)
        self.label_uuid.setText(uuid_str)
        start_time_str = f"{start_time:%Y-%m-%d %H:%M:%S}" if start_time else "____-__-__ --:--:--"
        self.label_datetime.setText(f'{start_time_str}')

    def set_details_info(self, details_list: List[Tuple[str, str]]):
        for i in range(self.details_layout.count()):
            widget = self.details_layout.itemAt(i).widget()
            widget.deleteLater()
        for irow, (name, value) in enumerate(details_list):
            self.details_layout.addWidget(QtWidgets.QLabel(name), irow, 0)
            self.details_layout.addWidget(QtWidgets.QLabel(value), irow, 1)

    def set_snapshot(self, snapshot: Union[str, Dict[str, Any]]):
        if isinstance(snapshot, str):
            tree_data = json.loads(snapshot)
        else:
            tree_data = snapshot

        tree = self.snapshot_tree
        tree.clear()

        if tree_data:
            self._add_items(None, tree_data)
        tree.itemExpanded.connect(self._expand_item)
        pulses = None
        if tree_data:
            try:
                pulses = tree_data['measurement']['sequence']
                _ = pulses['pc0']
            except KeyError:
                pulses = None
        self.set_pulses(pulses)

    @qt_log_exception
    def _expand_item(self, item: QtWidgets.QTreeWidgetItem):
        data, children_expanded = item.data(0, QtCore.Qt.UserRole)
        if not children_expanded:
            for index, (key, value) in enumerate(data.items()):
                child = item.child(index)
                child.setData(0, QtCore.Qt.UserRole, (value, True))
                if key != child.text(0):
                    print('Oops', key, child.text())
                if isinstance(value, Mapping):
                    self._add_items(child, value)
            item.setData(0, QtCore.Qt.UserRole, (data, True))

    def _add_items(self, parent, settings, depth=1):
        for key, value in settings.items():
            item = QtWidgets.QTreeWidgetItem()
            item.setText(0, key)
            item.setData(0, QtCore.Qt.UserRole, (value, False))
            if parent:
                parent.addChild(item)
            else:
                self.snapshot_tree.addTopLevelItem(item)
            if value is None:
                item.setText(1, 'None')
            elif isinstance(value, Mapping):
                if depth > 0:
                    self._add_items(item, value, depth-1)
            elif not isinstance(value, str) and isinstance(value, Sequence):
                item.setData(0, QtCore.Qt.UserRole, (value, True))
                for e in value:
                    li = QtWidgets.QTreeWidgetItem()
                    li.setText(0, '-')
                    li.setText(1, str(e))
                    item.addChild(li)
            else:
                item.setText(1, str(value))
                # if hasattr(value, 'dtype') and value.dtype <= float:
                #     if value.ndim == 0:
                #         value = value.item()
                #     else:
                #         value = str(value)
                # item.setData(1, QtCore.Qt.EditRole, value)
                # flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
                # item.setFlags(flags)

    @qt_log_exception
    def set_pulses(self, pulses: Union[None, Dict[str, Any]]):
        for i in range(self.pulses_layout.count()):
            widget = self.pulses_layout.itemAt(i).widget()
            widget.deleteLater()
        # self.tab_widget.setTabEnabled(2, pulses is not None)
        self.tab_widget.setTabVisible(2, pulses is not None)
        if pulses is None:
            return
        try:
            pulse_plot = pg.PlotWidget()
            pulse_plot.addLegend()
            pulse_plot.getAxis('bottom').enableAutoSIPrefix(False)
            pc_keys = [k for k, v in pulses.items() if k.startswith('pc') and v is not None]
            gate_keys = set([key for pc in pc_keys for key in pulses[pc] if not key.startswith('_')])
            try:
                baseband_freqs = pulses['LOs']
            except KeyError:
                pass
            for (j, name) in enumerate(gate_keys):
                t0 = 0
                x_plot = list()
                y_plot = list()
                # @@@ handle acquisition channels, condition channels
                # @@@ add check boxes for channels
                for pc in pc_keys:
                    legend_name = name.replace('_baseband','').replace('_pulses','')
                    x = list()
                    y = list()
                    try:
                        end_time = pulses[pc]['_total_time']
                        while isinstance(end_time, list):
                            end_time = end_time[-1]
                    except:
                        end_time = max([x['stop'] for y in pulses[pc].values() for x in y.values()])
                    try:
                        pulses[pc][name]
                    except:
                        t0 += end_time
                        continue

                    if 'baseband' in name:
                        timepoints = set([x[key] for x in pulses[pc][name].values() for key in ['start','stop']])
                        timepoints.add(end_time)
                        for tp in sorted(timepoints):
                            point1 = 0
                            point2 = 0
                            for seg_name, seg_dict in pulses[pc][name].items():
                                if seg_dict['start'] < tp and seg_dict['stop'] > tp: # active segement
                                    point1 += tp/(seg_dict['stop'] - seg_dict['start']) * ( seg_dict['v_stop'] - seg_dict['v_start'] ) + seg_dict['v_start']
                                    point2 += tp/(seg_dict['stop'] - seg_dict['start']) * ( seg_dict['v_stop'] - seg_dict['v_start'] ) + seg_dict['v_start']
                                elif seg_dict['start'] == tp:
                                    point2 += seg_dict['v_start']
                                elif seg_dict['stop'] == tp:
                                    point1 += seg_dict['v_stop']
                            x_plot += [tp + t0, tp + t0]
                            y_plot += [point1, point2]

                    elif 'pulses' in name:
                        try:
                            baseband = baseband_freqs[name.replace('_pulses','')]
                        except:
                            logger.warning('No baseband frequency found, assuming 0')
                            baseband = 0

                        for seg_name, seg_dict in pulses[pc][name].items():
                            x_ar = np.arange(seg_dict['start'], seg_dict['stop'])
                            xx_ar = x_ar-seg_dict['start']
                            f_rl = (seg_dict['frequency'] - baseband)/1e9
                            y_ar = np.sin(2*np.pi*f_rl*xx_ar+seg_dict['start_phase'])*seg_dict['amplitude']
                            x = x + list(x_ar) + [seg_dict['stop']]
                            y = y + list(y_ar) + [0]
                            x_plot = x
                            y_plot = y
                    t0 += end_time

                pulse_plot.setLabel('left', 'Voltage', 'mV')
                pulse_plot.setLabel('bottom', 'Time', 'ns')
                pulse_plot.plot(x_plot, y_plot, pen = color_list[j%len(color_list)], name = legend_name)

            self.pulses_layout.addWidget(pulse_plot, 1)
        except Exception:
            logger.error("Couldn't plot pulses", exc_info=True)
            message = traceback.format_exc()
            error_message = QtWidgets.QLabel(message)
            error_message.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            self.pulses_layout.addWidget(error_message, 1)

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

    def show_settings(self, index: int, plot_model: PlotModel, hidden: bool):
        if self.current_settings_widget is not None:
            self.current_settings_widget.deleteLater()

        settings_widget = PlotSettings(plot_model)
        settings_widget.setVisible(not hidden)
        self.settings_layout.addWidget(settings_widget)
        self.current_settings_widget = settings_widget

    def add_plot(self, title: str, seq_nr: float):
        logger.debug(f"Add {title}")
        if seq_nr in self._plot_widgets:
            raise Exception(f"Duplicate plot {seq_nr}")
        layout = self.plots_layout
        self.plots_widget.setUpdatesEnabled(False) # @@@ decorator for nested updates

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

        widget = ClickFrame()
        widget.setMinimumWidth(250)
        widget.setMinimumHeight(250)
        widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        widget.setFrameStyle(QtWidgets.QFrame.StyledPanel)
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
            widget.setVisible(int(seq_nr) == selected)
            plot_index = 0 # @@@ not correct with sub-plots
        irow, icol = divmod(plot_index, N_PLOT_COLUMNS)
        layout.addWidget(widget, irow, icol)

        self._plot_widgets[seq_nr] = widget

        self._update_grid_stretch()
        # self._update_plot_borders()
        self.plots_widget.setUpdatesEnabled(True)

        return plot_layout

    def _mouse_clicked(self, *args, seq_nr=None, **kwargs):
        self.lb_variables.item(int(seq_nr)).setSelected(True)

    def remove_plot(self, seq_nr: float):
        if seq_nr not in self._plot_widgets:
            return
        layout = self.plots_layout
        self.plots_widget.setUpdatesEnabled(False)

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
        self.plots_widget.setUpdatesEnabled(True)

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
