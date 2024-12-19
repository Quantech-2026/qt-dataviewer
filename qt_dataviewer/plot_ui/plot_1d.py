import pyqtgraph as pg
import numpy as np

from PyQt5 import QtCore, QtWidgets
from qt_dataviewer.utils.qt_utils import qt_log_exception

from .smart_format import SmartFormatter
from .plots import BasePlot


graph_color = list()
graph_color += [{"pen":(0,114,189), 'symbolBrush':(0,114,189), 'symbolPen':'w', "symbol":'o', "symbolSize":7}]
graph_color += [{"pen":(217,83,25), 'symbolBrush':(217,83,25), 'symbolPen':'w', "symbol":'t', "symbolSize":7}]
graph_color += [{"pen":(250,194,5), 'symbolBrush':(250,194,5), 'symbolPen':'w', "symbol":'t3', "symbolSize":7}]
graph_color += [{"pen":(54,55,55), 'symbolBrush':(55,55,55), 'symbolPen':'w', "symbol":'s', "symbolSize":7}]
graph_color += [{"pen":(119,172,48), 'symbolBrush':(119,172,48), 'symbolPen':'w', "symbol":'d', "symbolSize":7}]
graph_color += [{"pen":(19,234,201), 'symbolBrush':(19,234,201), 'symbolPen':'w', "symbol":'t1', "symbolSize":7}]
graph_color += [{'pen':(0,0,200), 'symbolBrush':(0,0,200), 'symbolPen':'w', "symbol":'x', "symbolSize":7}]
graph_color += [{"pen":(0,128,0), 'symbolBrush':(0,128,0), 'symbolPen':'w', "symbol":'p', "symbolSize":7}]
graph_color += [{"pen":(195,46,212), 'symbolBrush':(195,46,212), 'symbolPen':'w', "symbol":'t2', "symbolSize":7}]
graph_color += [{"pen":(237,177,32), 'symbolBrush':(237,177,32), 'symbolPen':'w', "symbol":'star', "symbolSize":7}]
graph_color += [{"pen":(126,47,142), 'symbolBrush':(126,47,142), 'symbolPen':'w', "symbol":'+', "symbolSize":7}]


class Plot1D(BasePlot):

    @qt_log_exception
    def create(self):
        plot_model = self._plot_model
        data = plot_model.get_data()
        self._data = data

        self.plot = pg.PlotWidget()
        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignRight)

        self._layout.addWidget(self.plot)
        self._layout.addWidget(self.label)

        self.curves = []

        plot = self.plot
        # plot.setBackground('white')
        # plot.addLegend()
        plot.showGrid(True, True)

        # TODO: @@@ cleanup. Merge with update()
        label = data.attrs['long_name']
        x = data[data.dims[0]]
        if x.attrs.get('scale', '').endswith("_unsorted"):
            data = data.sortby(x.name)
            x = data[data.dims[0]]
        y = data

        if self.one_d_is_vertical:
            x, y = y, x

        self._update_axis(x, y)
        x_data = self._x_formatter.scale * x.data
        y_data = self._y_formatter.scale * y.data
        self.x_data = x_data
        self.y_data = y_data
        curve_style = graph_color[0]
        if len(x_data) > 100:
            curve_style = {"pen": curve_style["pen"]}

#        if not np.any(np.isfinite(y_data)):
#            print("Oops", label)

        curve = plot.plot(x_data, y_data, **curve_style, name=label, connect='finite')
        self.curves.append(curve)

        self.proxy = pg.SignalProxy(plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

    def _update_axis(self, x, y):
        log_mode = {
            'x': x.attrs.get('log', False),
            'y': y.attrs.get('log', False)
            }
        self._log_mode = log_mode
        x_formatter = SmartFormatter(x.attrs)
        self._x_formatter = x_formatter
        y_formatter = SmartFormatter(y.attrs)
        self._y_formatter = y_formatter

        plot = self.plot
        x_formatter.set_plot_axis(plot.getAxis('bottom'))
        y_formatter.set_plot_axis(plot.getAxis('left'))
        plot.setLogMode(**log_mode)

        value_range = self._plot_model.value_range
        if value_range is not None and not np.isnan(value_range[0]):
            mn, mx = value_range
            if self.one_d_is_vertical:
                mn *= x_formatter.scale
                mx *= x_formatter.scale
                plot.enableAutoRange(x=False)
                if not log_mode['x']:
                    plot.setXRange(mn, mx)
                else:
                    plot.setXRange(np.log10(mn), np.log10(mx))
            else:
                mn *= y_formatter.scale
                mx *= y_formatter.scale
                plot.enableAutoRange(y=False)
                if not log_mode['y']:
                    plot.setYRange(mn, mx)
                else:
                    plot.setYRange(np.log10(mn), np.log10(mx))

    @qt_log_exception
    def update(self):
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
        self._update_axis(x, y)

        x_data = self._x_formatter.scale * x.data
        y_data = self._y_formatter.scale * y.data
        self.x_data = x_data
        self.y_data = y_data
        self.curves[0].setData(x_data, y_data, connect='finite')

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
                d[np.isnan(d)] = np.inf # @@@
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
