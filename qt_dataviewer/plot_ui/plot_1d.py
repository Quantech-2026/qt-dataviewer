import pyqtgraph as pg
import numpy as np

from PyQt5 import QtCore, QtWidgets
from pyqtgraph.graphicsItems import AxisItem
from qt_dataviewer.utils.qt_utils import qt_log_exception

from .smart_format import SmartFormatter
from .plots import BasePlot

graph_color = list()
graph_color += [{"pen": (0, 114, 189), 'symbolBrush': (0, 114, 189), "symbol": 'o'}]
graph_color += [{"pen": (217, 83, 25), 'symbolBrush': (217, 83, 25), "symbol": 't'}]
graph_color += [{"pen": (250, 194, 5), 'symbolBrush': (250, 194, 5), "symbol": 't3'}]
graph_color += [{"pen": (54, 55, 55), 'symbolBrush': (55, 55, 55), "symbol": 's'}]
graph_color += [{"pen": (119, 172, 48), 'symbolBrush': (119, 172, 48), "symbol": 'd'}]
graph_color += [{"pen": (19, 234, 201), 'symbolBrush': (19, 234, 201), "symbol": 't1'}]
graph_color += [{'pen': (0, 0, 200), 'symbolBrush': (0, 0, 200), "symbol": 'x'}]
graph_color += [{"pen": (0, 128, 0), 'symbolBrush': (0, 128, 0), "symbol": 'p'}]
graph_color += [{"pen": (195, 46, 212), 'symbolBrush': (195, 46, 212), "symbol": 't2'}]
graph_color += [{"pen": (237, 177, 32), 'symbolBrush': (237, 177, 32), "symbol": 'star'}]
graph_color += [{"pen": (126, 47, 142), 'symbolBrush': (126, 47, 142), "symbol": '+'}]


class Plot1D(BasePlot):

    @qt_log_exception
    def create(self):
        self.plot = pg.PlotWidget()
        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignRight)

        self._layout.addWidget(self.plot)
        self._layout.addWidget(self.label)

        self.curves = []

        plot = self.plot
        # plot.addLegend()
        plot.showGrid(True, True)

        x_data, y_data = self._get_plot_data()
        data = self._data

        label = data.attrs['long_name']

        style = graph_color[0]
        if len(x_data) > 100:
            curve_style = {"pen": style["pen"]}
        else:
            curve_style = dict(**style, symbolPen="w", symbolSize=6)

        if y_data.dtype == complex:  # TODO @@@ Properly handle complex data.
            curve = plot.plot(x_data, y_data.real, **curve_style, name=label+".real", connect='finite')
            self.curves.append(curve)
            curve = plot.plot(x_data, y_data.imag, **curve_style, name=label+".imag", connect='finite')
            self.curves.append(curve)
        else:
            curve = plot.plot(x_data, y_data, **curve_style, name=label, connect='finite')
            self.curves.append(curve)

        self.proxy = pg.SignalProxy(plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

    def _get_plot_data(self):
        plot_model = self._plot_model
        data = plot_model.get_data()
        x = data[data.dims[0]]
        if x.attrs.get('scale', '').endswith("_unsorted"):
            data = data.sortby(x.name)
            x = data[data.dims[0]]
        self._data = data
        y = data

        if self.one_d_is_vertical:
            x, y = y, x

        x_formatter = SmartFormatter(x.attrs)
        self._x_formatter = x_formatter
        y_formatter = SmartFormatter(y.attrs)
        self._y_formatter = y_formatter

        self._update_axis(x, y)

        x_data = self._x_formatter.without_unit_prefix(x.data)
        y_data = self._y_formatter.without_unit_prefix(y.data)
        x_axis = self._fix_labels(x_data, self._x_formatter, self.plot.getAxis('bottom'))
        y_axis = self._fix_labels(y_data, self._y_formatter, self.plot.getAxis('left'))
        if self.one_d_is_vertical:
            y_data = y_axis
        else:
            x_data = x_axis

        self.x_data = x_data
        self.y_data = y_data
        return x_data, y_data

    def _update_axis(self, x, y):
        log_mode = {
            'x': x.attrs.get('log', False),
            'y': y.attrs.get('log', False)
        }
        self._log_mode = log_mode
        plot = self.plot
        x_formatter = self._x_formatter
        y_formatter = self._y_formatter

        x_formatter.set_plot_axis(plot.getAxis('bottom'))
        y_formatter.set_plot_axis(plot.getAxis('left'))
        plot.setLogMode(**log_mode)

        value_range = self._plot_model.value_range
        if value_range is not None and not np.isnan(value_range[0]):
            mn, mx = value_range
            if self.one_d_is_vertical:
                mn = x_formatter.without_unit_prefix(mn)
                mx = x_formatter.without_unit_prefix(mx)
                plot.enableAutoRange(x=False)
                if not log_mode['x']:
                    plot.setXRange(mn, mx)
                else:
                    plot.setXRange(np.log10(mn), np.log10(mx))
            else:
                mn = y_formatter.without_unit_prefix(mn)
                mx = y_formatter.without_unit_prefix(mx)
                plot.enableAutoRange(y=False)
                if not log_mode['y']:
                    plot.setYRange(mn, mx)
                else:
                    plot.setYRange(np.log10(mn), np.log10(mx))

    def _fix_labels(self, x, formatter, axis: AxisItem):
        if issubclass(x.dtype.type, str) or formatter._units == "|..>":
            formatter.set_labels(axis, x)
            return np.arange(len(x))
        else:
            return x

    @qt_log_exception
    def update(self):
        x_data, y_data = self._get_plot_data()
        self.curves[0].setData(x_data, y_data, connect='finite')

    @qt_log_exception
    def mouseMoved(self, evt):
        vb = self.plot.getPlotItem().vb
        pos = evt[0]  # using signal proxy turns original arguments into a tuple
        if vb.sceneBoundingRect().contains(pos):
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
            else:
                d = np.abs(x_data - x_val)
            idx = np.nanargmin(d)
            x_val = x_data[idx]
            y_val = y_data[idx]

            x_str = self._x_formatter.with_units(x_val, x_data)
            y_str = self._y_formatter.with_units(y_val, y_data)

            self.label.setText(f"x={x_str}, y={y_str}")
