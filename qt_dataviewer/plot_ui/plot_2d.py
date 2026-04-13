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


class Plot2D(BasePlot):
    def create(self):
        self.plot = pg.PlotItem()
        self.plot.setDefaultPadding(0.01)

        self.img = pg.ImageItem()
        # set some image data. This is required for pyqtgraph > 0.11
        self.img.setImage(np.zeros((1, 1)))
        self.img.setColorMap(get_color_map())

        self.mesh = None
        self.hist = None
        self.cb = None
        self.plot.addItem(self.img)
        self.widget = pg.PlotWidget(plotItem=self.plot)
        self.layout_widget = QtWidgets.QWidget()
        self.h_layout = QtWidgets.QHBoxLayout(self.layout_widget)
        self.h_layout.addWidget(self.widget)
        self._layout.addWidget(self.layout_widget)

        self._plot_mode = "uniform"
        self._log_mode = {}

        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignRight)

        self._layout.addWidget(self.label)

        self.proxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        try:
            self.update()
            self.plot.setAspectLocked(False)
        except Exception:
            logger.error("Failed to create plot", exc_info=True)

    def show_sidebar(self, mode):
        if mode == "std":
            if self.cb is None:
                cb = pg.ColorBarItem(colorMap=get_color_map(), interactive=False, width=12)
                cb.axis.setWidth(40)
                cb.setImageItem(self.img or self.mesh, insert_in=self.plot)
                self.cb = cb
        else:
            if self.cb is not None:
                self.plot.layout.removeItem(self.cb)
                self.cb = None

        if mode == "histogram":
            if self.hist is None:
                hist = pg.HistogramLUTWidget()
                hist.setMinimumWidth(76)
                hist.vb.setMinimumWidth(24)
                hist.gradient.setColorMap(get_color_map())  # nTicks=5))
                hist.gradient.showTicks(False)
                hist.setImageItem(self.img or self.mesh)
                self.h_layout.addWidget(hist)
                self.hist = hist
        else:
            if self.hist is not None:
                hist = self.hist
                # disconnect and delete
                if self.img:
                    self.img.sigImageChanged.disconnect(hist.imageChanged)
                self.h_layout.removeWidget(hist)
                self.hist.deleteLater()
                self.hist = None

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
        if x_scale.endswith("_unsorted"):
            x_scale = x_scale[:-9]
            data = data.sortby(x_array.name)
            x_array = data[data.dims[0]]
        if y_scale.endswith("_unsorted"):
            y_scale = y_scale[:-9]
            data = data.sortby(y_array.name)
            y_array = data[data.dims[1]]

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
                    logger.error(f"Complex mode {complex_mode} not supported in 2D")
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

        if x_scale == "irregular" or y_scale == "irregular":
            plot_mode = "irregular"
        else:
            plot_mode = "uniform"

        if plot_mode == "uniform":
            if self._plot_mode != "uniform":
                self.plot.removeItem(self.mesh)
                self.mesh = None
                self.img = pg.ImageItem()
                # set some image data. This is required for pyqtgraph > 0.11
                self.img.setImage(np.zeros((1, 1)))
                self.plot.addItem(self.img)
                if self.hist is not None:
                    self.hist.setImageItem(self.img)
                elif self.cb is not None:
                    self.cb.setImageItem(self.img)
                else:
                    self.img.setColorMap(get_color_map())
                self._plot_mode = "uniform"

            x_offset, x_width, x_flip = x_helper.get_axis_range()
            y_offset, y_height, y_flip = y_helper.get_axis_range()

            if x_offset is None or y_offset is None:
                logger.warning("No valid values on axis")
                return

            if x_flip:
                z = z[::-1, :]
            if y_flip:
                z = z[:, ::-1]

            rect = QtCore.QRectF(
                x_offset,
                y_offset,
                x_width,
                y_height,
            )
            # log mode determined by axis data
            log_mode = {
                "x": x_scale == "log",
                "y": y_scale == "log",
                }
            self._log_mode = log_mode
            plot.setLogMode(**log_mode)

            self.img.setImage(z)
            self.img.setRect(rect)
            if self.cb:
                self.cb.setLevels(self.img.getLevels())
            dx = x_width / len(x_array)
            dy = y_height / len(y_array)
            self.plot.setLimits(xMin=x_offset-dx, xMax=x_offset+x_width+dx,
                                yMin=y_offset-dy, yMax=y_offset+y_height+dy)

        # TODO Cleanup !!
        if plot_mode == "irregular":
            if self._plot_mode != "irregular":
                self.plot.removeItem(self.img)
                self.img = None
                self.mesh = MyPColorMesh()
                if self.hist is not None:
                    self.hist.setImageItem(self.mesh)
                elif self.cb is not None:
                    self.cb.setImageItem(self.img)
                else:
                    self.mesh.setColorMap(get_color_map())
                self.plot.addItem(self.mesh)
                self._plot_mode = "irregular"

            # log mode determined by plot settings
            log_mode = {
                "x": x_formatter.log,
                "y": y_formatter.log,
                }
            self._log_mode = log_mode
            plot.setLogMode(**log_mode)

            x_edges, x_slice = x_helper.get_edges(log_mode.get("x"))
            y_edges, y_slice = y_helper.get_edges(log_mode.get("y"))

            if x_slice is None or y_slice is None:
                logger.warning("No valid values on axis")
                return

            x_grid = x_edges[:, None] * np.ones(len(y_edges))
            y_grid = y_edges * np.ones(len(x_edges))[:, None]

            z = z_array.data[x_slice, y_slice]
            # determine z-levels.
            if np.any(np.isfinite(z)):
                levels = (np.nanmin(z), np.nanmax(z))
                self.mesh.setLevels(levels, update=False)
                if self.cb:
                    self.cb.setLevels(levels)

            self.mesh.setData(x_grid, y_grid, z, autoLevels=False)
            if self.hist:
                self.hist.imageChanged()

            # Calculate min/max values to show data with small empty border.
            # Default behavior of pyqtgraph is to select "notural" values on axis.
            # This behavior can result in a big white space around the data.
            x_min, x_max = self._get_axis_limits(x_edges)
            y_min, y_max = self._get_axis_limits(y_edges)

            self.plot.setLimits(xMin=x_min, xMax=x_max, yMin=y_min, yMax=y_max)

    def _get_axis_limits(self, values):
        x_min = min(values)
        x_max = max(values)
        delta = (x_max - x_min) * 0.02
        x_min -= delta
        x_max += delta
        return x_min, x_max

    @qt_log_exception
    def mouseMoved(self, evt):
        vb = self.plot.vb
        pos = evt[0]  # using signal proxy turns original arguments into a tuple
        if vb.sceneBoundingRect().contains(pos):
            mousePoint = vb.mapSceneToView(pos)
            x_val = mousePoint.x()
            y_val = mousePoint.y()
            if self._log_mode.get("x"):
                x_val = 10**x_val
            if self._log_mode.get("y"):
                y_val = 10**y_val

            z = self._z_formatter.without_unit_prefix(self._z_array)
            x = self._x_formatter.without_unit_prefix(self._x_array)
            y = self._y_formatter.without_unit_prefix(self._y_array)

            d = np.abs(x-x_val)
            ix = np.nanargmin(d)
            d = np.abs(y-y_val)
            iy = np.nanargmin(d)
            value = z[ix, iy]
            x_val = x[ix]
            y_val = y[iy]

            x_str = self._x_formatter.with_units(x_val, x)
            y_str = self._y_formatter.with_units(y_val, y)
            z_str = self._z_formatter.with_units(value, z)

            self.label.setText(f"x={x_str}, y={y_str}: {z_str}")


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


class MyPColorMesh(pg.PColorMeshItem):
    """
    Makes PColorMeshItem compatible with ImageItem for the
    interaction with the histogram lut.

    The code is a bit hacky, but works for now.
    """

    def setLookupTable(self, lut, update=True):
        if not isinstance(lut, list):
            _lut = lut(n=256)
            # print(_lut)
            lut = [
                QtGui.QColor.fromRgb(rgb[0], rgb[1], rgb[2]) for rgb in _lut
                ]
        super().setLookupTable(lut)

    def getHistogram(self):
        data = self.z
        mn = np.nanmin(data)
        mx = np.nanmax(data)

        if mn is None or mx is None:
            # the data are all-nan
            return None, None
        if mx == mn:
            # degenerate image, arange will fail
            mx += 1
        bins = np.linspace(mn, mx, 500)

        data = data[np.isfinite(data)]
        hist = np.histogram(data, bins=bins)
        return hist[1][:-1], hist[0]
