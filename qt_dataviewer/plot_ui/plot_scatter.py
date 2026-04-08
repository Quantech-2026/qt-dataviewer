import logging
import pyqtgraph as pg
import numpy as np

from pyqtgraph.colormap import getFromMatplotlib
from qtpy import QtCore, QtWidgets, QtGui
from matplotlib import colormaps

from qt_dataviewer.model.plot_model import ComplexMode, get_phase
from qt_dataviewer.utils.qt_utils import qt_log_exception
from qt_dataviewer.utils.configuration import get_setting
from .plots import BasePlot
from .smart_format import SmartFormatter
from .axis_helper import AxisHelper


logger = logging.getLogger(__name__)


class PlotScatter(BasePlot):
    def create(self):
        self.plot = pg.PlotItem()
        self.plot.setDefaultPadding(0.01)

        self.scatter = pg.ScatterPlotItem()
        self._color_map = get_color_map()
        self._levels = (0.0, 0.0)
        self.cb = None

        self.plot.addItem(self.scatter)

        self.widget = pg.PlotWidget(plotItem=self.plot)
        self.layout_widget = QtWidgets.QWidget()
        self.h_layout = QtWidgets.QHBoxLayout(self.layout_widget)
        self.h_layout.addWidget(self.widget)
        self._layout.addWidget(self.layout_widget)
        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignRight)

        self._layout.addWidget(self.label)

        self._log_mode = {}

        # TODO self.proxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        try:
            self.update()
            self.plot.setAspectLocked(False)
        except Exception:
            logger.error("Failed to create plot", exc_info=True)

    def show_sidebar(self, mode):
        layout = self.plot.layout
        if mode == "std":
            if self.cb is None:
                cb = pg.ColorBarItem(colorMap=get_color_map(), interactive=False, width=12)
                cb.axis.setWidth(40)
                cb.setLevels(self._levels)
                layout.addItem(cb, 2, 5)  # insert in layout after right-hand axis
                layout.setColumnFixedWidth(4, 5)  # enforce some space to axis on the left
                self.cb = cb
        else:
            if self.cb is not None:
                layout.removeItem(self.cb)
                self.cb = None

    @qt_log_exception
    def update(self):
        plot_model = self._plot_model
        self.show_sidebar(plot_model.show_sidebar)

        data = plot_model.get_data()
        self._data = data

        x_name, y_name = plot_model.plot_axes
        x_array = data[x_name]
        y_array = data[y_name]

        x_scale = x_array.attrs.get("scale", "")
        y_scale = y_array.attrs.get("scale", "")

        if np.iscomplexobj(data):
            complex_mode = plot_model.complex_mode

            match complex_mode:
                case ComplexMode.Re:
                    z_array = data.real
                case ComplexMode.Im:
                    z_array = data.imag
                case ComplexMode.Amplitude:
                    z_array = np.abs(data)
                case ComplexMode.Phase:
                    z_array = get_phase(data)
                case _:
                    logger.error(f"Complex mode {complex_mode} not supported in scatter plot")
                    z_array = data.real
        else:
            z_array = data

        x_formatter = SmartFormatter(x_array)
        self._x_formatter = x_formatter
        self._x_array = x_array
        y_formatter = SmartFormatter(y_array)
        self._y_formatter = y_formatter
        self._y_array = y_array
        z_formatter = SmartFormatter(z_array)
        self._z_formatter = z_formatter
        self._z_array = z_array

        x_helper = AxisHelper(x_array, x_scale)
        y_helper = AxisHelper(y_array, y_scale)

        z = z_array.data
        if not np.any(np.isfinite(z)):
            logger.info("no valid data to plot")
            return

        plot = self.plot
        x_helper.set_plot_axis(plot.getAxis("bottom"))
        y_helper.set_plot_axis(plot.getAxis("left"))

        levels = np.min(z), np.max(z)
        self._levels = levels

        if self.cb is not None:
            self.cb.setLevels(levels)

        log_mode = {
            "x": x_formatter.log,
            "y": y_formatter.log,
            }
        self._log_mode = log_mode
        plot.setLogMode(**log_mode)

        # create spots

        # data without unit scaling
        x = x_helper.x
        y = y_helper.x
        # apply log (not automatically done by ScatterPlotItem)
        if x_formatter.log:
            x = np.log10(x)
        if y_formatter.log:
            y = np.log10(y)

        brushes = [
            pg.mkBrush(color=color)
            for color in self._color_map
            ]

        z_norm = z - levels[0]
        if levels[1] > levels[0]:
            z_norm *= 255.999/(levels[1] - levels[0])
        z_norm = np.floor(z_norm).astype(int)
        if z.ndim > 0:
            brush = [
                brushes[icolor]
                for icolor in z_norm
                ]
            npt = len(z_norm)
            if npt < 50:
                size = 25
            elif npt < 200:
                size = 20
            elif npt < 500:
                size = 15
            else:
                size = 12
            self.scatter.setData(x=x, y=y, brush=brush, pen="w", size=size)
        else:
            # Only 1 point. It's a strange case, but can happen.
            brush = [brushes[0]]
            size = 25

            self.scatter.setData(x=[x], y=[y], brush=brush, pen="w", size=size)

    # @qt_log_exception
    # def mouseMoved(self, evt):
    #     vb = self.plot.vb
    #     pos = evt[0]  # using signal proxy turns original arguments into a tuple
    #     if vb.sceneBoundingRect().contains(pos):
    #         mousePoint = vb.mapSceneToView(pos)
    #         x_val = mousePoint.x()
    #         y_val = mousePoint.y()
    #         if self._log_mode.get("x"):
    #             x_val = 10**x_val
    #         if self._log_mode.get("y"):
    #             y_val = 10**y_val

    #         z = self._z_formatter.without_unit_prefix(self._z_array)
    #         x = self._x_formatter.without_unit_prefix(self._x_array)
    #         y = self._y_formatter.without_unit_prefix(self._y_array)

    #         d = np.abs(x-x_val)
    #         ix = np.nanargmin(d)
    #         d = np.abs(y-y_val)
    #         iy = np.nanargmin(d)
    #         value = z[ix, iy]
    #         x_val = x[ix]
    #         y_val = y[iy]

    #         x_str = self._x_formatter.with_units(x_val, x)
    #         y_str = self._y_formatter.with_units(y_val, y)
    #         z_str = self._z_formatter.with_units(value, z)

    #         self.label.setText(f"x={x_str}, y={y_str}: {z_str}")


def get_color_map(nTicks: int | None = None):
    colormap = get_setting("plotting.colormap")
    if nTicks is None:
        return getFromMatplotlib(colormap)
    colorMap = colormaps[get_setting("plotting.colormap")]
    colorList = np.linspace(0, 1, nTicks)
    lineColors = colorMap(colorList)

    lineColors = lineColors * 255
    lineColors = lineColors.astype(int)
    return pg.ColorMap(pos=np.linspace(0.0, 1.0, nTicks), color=lineColors)
