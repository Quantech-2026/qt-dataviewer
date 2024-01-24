import pyqtgraph as pg
import numpy as np

from PyQt5 import QtCore, QtWidgets
from qt_dataviewer.utils.qt_utils import qt_log_exception

from .smart_format import SmartFormatter
from .plots import BasePlot


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


class PlotMultiline(BasePlot):
    def create(self):
        plot_model = self._plot_model
        data = plot_model.get_data()
        self._data = data

        pg.setConfigOption('background', None)
        # pg.setConfigOption('background', 'white')
        pg.setConfigOption('foreground', 'k')

        self.plot = pg.PlotWidget()
        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignRight)

        self._layout.addWidget(self.plot)
        self._layout.addWidget(self.label)

        self.curves = {}

        plot = self.plot
        # plot.addLegend()
        plot.showGrid(True, True)

        self.update()
        # self.proxy = pg.SignalProxy(plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

    def _update_axis(self, x, y):
        log_mode = {'x': x.attrs['log'], 'y': y.attrs['log']}
        self._log_mode = log_mode
        x_formatter = self._x1_formatter
        y_formatter = self._y_formatter

        plot = self.plot
        plot.getAxis('bottom').enableAutoSIPrefix(x_formatter.auto_si_prefix)
        plot.getAxis('left').enableAutoSIPrefix(y_formatter.auto_si_prefix)
        plot.setLabel('bottom', x.attrs['long_name'], units=x_formatter.units)
        plot.setLabel('left', y.attrs['long_name'], units=y_formatter.units)
        plot.setLogMode(**log_mode)

        value_range = self._plot_model.value_range
        if value_range is not None:
            mn, mx = value_range
            mn *= y_formatter.scale
            mx *= y_formatter.scale
            plot.enableAutoRange(y=False)
            if not log_mode['y']:
                plot.setYRange(mn, mx)
            else:
                plot.setYRange(np.log10(mn), np.log10(mx))

    @qt_log_exception
    def update(self):
        plot = self.plot
        plot_model = self._plot_model
        data = plot_model.get_data()
        self._data = data

        data = plot_model.get_data()
        self._data = data
        x0 = data[data.dims[0]]
        x1 = data[data.dims[1]]
        y = data

        x0_formatter = SmartFormatter(x0.attrs['units'])
        self._x0_formatter = x0_formatter
        x1_formatter = SmartFormatter(x1.attrs['units'])
        self._x1_formatter = x1_formatter
        y_formatter = SmartFormatter(y.attrs['units'])
        self._y_formatter = y_formatter
        self._update_axis(x1, y)
        x0_data = self._x0_formatter.scale * x0.data
        x1_data = self._x1_formatter.scale * x1.data
        y_data = self._y_formatter.scale * y.data
        self.x0_data = x0_data
        self.x1_data = x1_data
        self.y_data = y_data

        for i, v1 in enumerate(x1_data):
            if np.isnan(v1):
                continue
            label = x1_formatter.with_units(v1, x1_data)
            if i not in self.curves:
                curve = plot.plot(x0_data, y_data[:,i], pen=dict(color=color_cycle[i % 10], width=2),
                                  name=label, connect='finite')
                self.curves[i] = curve
            else:
                self.curves[i].setData(x0_data, y_data[:,i], connect='finite')


    @qt_log_exception
    def mouseMoved(self, evt):
        vb = self.plot.getPlotItem().vb
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.plot.sceneBoundingRect().contains(pos):
            mousePoint = vb.mapSceneToView(pos)
            x_val = mousePoint.x()
            y_val = mousePoint.y()
            if self._log_mode['x']:
                 x_val = 10**x_val
            if self._log_mode['y']:
                 y_val = 10**y_val

            x_data = self.x_data
            y_data = self.y_data
            if self.one_d_is_vertical:
                d = np.abs(y_data - y_val)
                d[np.isnan(d)] = np.inf
                iy = d.argmin()
                x_val = x_data[iy]
                y_val = y_data[iy]
            else:
                d = np.abs(x_data - x_val)
                d[np.isnan(d)] = np.inf
                ix = d.argmin()
                x_val = x_data[ix]
                y_val = y_data[ix]

            x_str = self._x_formatter.with_units(x_val, x_data)
            y_str = self._y_formatter.with_units(y_val, y_data)

            self.label.setText(f"x={x_str}, y={y_str}")
