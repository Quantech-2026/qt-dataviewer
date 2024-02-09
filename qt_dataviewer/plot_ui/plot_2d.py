import logging
import pyqtgraph as pg
import numpy as np

from PyQt5 import QtCore, QtWidgets
from matplotlib.pyplot import get_cmap

from qt_dataviewer.utils.qt_utils import qt_log_exception
from .plots import BasePlot
from .smart_format import SmartFormatter


logger = logging.getLogger(__name__)


class Plot2D(BasePlot):
    def create(self):
        pg.setConfigOption('background', None)
        # pg.setConfigOption('background', 'white')
        pg.setConfigOption('foreground', 'k')

        self.plot = pg.PlotItem()
        self.plot.setDefaultPadding(0.01)

        self.img = pg.ImageItem()
        # set some image data. This is required for pyqtgraph > 0.11
        self.img.setImage(np.zeros((1, 1)))

        img_view = pg.ImageView(view=self.plot, imageItem=self.img)
        self.img_view = img_view
        img_view.setColorMap(get_color_map())
        img_view.ui.roiBtn.hide()
        img_view.ui.menuBtn.hide()
        img_view.ui.histogram.autoHistogramRange()
        self._plot_mode = 'uniform'

        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignRight)

        self._layout.addWidget(self.img_view)
        self._layout.addWidget(self.label)

        self._log_mode = {}

        self.proxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.update()
        self.plot.setAspectLocked(False)

    def show_sidebar(self, show):
        if self.img_view is not None:
            histogram = self.img_view.ui.histogram
        else:
            return # TODO find out how to add histogram to PColorMesh
        if not show:
            if not histogram.isHidden():
                histogram.hide()
        else:
            if histogram.isHidden():
                histogram.show()

    @qt_log_exception
    def update(self):
        plot_model = self._plot_model
        self.show_sidebar(plot_model.show_sidebar)

        data = plot_model.get_data()
        self._data = data
        x_array = data[data.dims[0]]
        y_array = data[data.dims[1]]
        x = x_array.data
        y = y_array.data

        x_formatter = SmartFormatter(x_array.attrs)
        self._x_formatter = x_formatter
        y_formatter = SmartFormatter(y_array.attrs)
        self._y_formatter = y_formatter
        z_formatter = SmartFormatter(data.attrs)
        self._z_formatter = z_formatter

        x = x * x_formatter.scale
        y = y * y_formatter.scale
        z = data.data

        plot = self.plot
        x_formatter.set_plot_axis(plot.getAxis('bottom'))
        y_formatter.set_plot_axis(plot.getAxis('left'))

        x_args = np.argwhere(np.isfinite(x)).T[0]
        y_args = np.argwhere(np.isfinite(y)).T[0]
        if len(x_args) == 0:
            # No data yet. Nothing to update.
            return
        x_limit = [np.min(x_args), np.max(x_args)]
        y_limit = [np.min(y_args), np.max(y_args)]
        x_slice = slice(x_limit[0], x_limit[1]+1)
        y_slice = slice(y_limit[0], y_limit[1]+1)

        if x_array.attrs.get('scale') == 'irregular' or y_array.attrs.get('scale') == 'irregular':
            plot_mode = 'irregular'
        else:
            plot_mode = 'uniform'

        if plot_mode == 'uniform':
            if self._plot_mode != 'uniform':
                self.plot.removeItem(self.mesh)
                self.mesh = None
                self.img = pg.ImageItem()
                # set some image data. This is required for pyqtgraph > 0.11
                self.img.setImage(np.zeros((1, 1)))
                img_view = pg.ImageView(view=self.plot, imageItem=self.img)
                self.img_view = img_view
                img_view.setColorMap(get_color_map())
                img_view.ui.roiBtn.hide()
                img_view.ui.menuBtn.hide()
                img_view.ui.histogram.autoHistogramRange()
                self._plot_mode = 'uniform'


            log_mode = {}
            if x_array.attrs.get('scale') == 'log':
                log_mode['x'] = True
                x = np.log10(x)
            if y_array.attrs.get('scale') == 'log':
                log_mode['y'] = True
                y = np.log10(y)

            x_limit_num = (x[x_limit[0]], x[x_limit[1]])
            y_limit_num = (y[y_limit[0]], y[y_limit[1]])

            x_offset = np.min(x[x_args])
            y_offset = np.min(y[y_args])
            with np.errstate(divide='ignore'):
                x_scale = abs(x_limit_num[1] - x_limit_num[0])/(x_limit[1] - x_limit[0])
                y_scale = abs(y_limit_num[1] - y_limit_num[0])/(y_limit[1] - y_limit[0])

            if x_scale == 0 or np.isnan(x_scale):
                x_scale = 1
            else:
                x_offset -= 0.5*x_scale

            if y_scale == 0 or np.isnan(y_scale):
                y_scale = 1
            else:
                y_offset -= 0.5*y_scale

            rect = QtCore.QRectF(
                x_offset,
                y_offset,
                x_scale * len(x),
                y_scale * len(y),
            )
            plot.setLogMode(**log_mode)
            self._log_mode = log_mode

            # flip axis is postive to negative scan
            if x_limit_num[0] > x_limit_num[1]:
                z = z[::-1, :]
                x_offset -= (len(x)-x_limit[1]-1)*x_scale
            else:
                x_offset -= x_limit[0]*x_scale
            if y_limit_num[0] > y_limit_num[1]:
                z = z[:, ::-1]
                y_offset -= (len(y)-y_limit[1]-1)*y_scale
            else:
                y_offset -= y_limit[0]*y_scale

            self.plot.invertY(False)
            self.img.setRect(rect)
            self.img.setImage(z)

        # TODO Cleanup !!
        if plot_mode == 'irregular':
            if self._plot_mode != 'irregular':
                self.plot.removeItem(self.img_view)
                self.img_view = None
                self.mesh = pg.PColorMeshItem()
                self.plot.addItem(self.mesh)
                self._plot_mode = 'irregular'

            log_mode = {
                'x': x_array.attrs['log'],
                'y': y_array.attrs['log'],
                }
            plot.setLogMode(**log_mode)
            self._log_mode = log_mode

            x_valid = x[x_slice]
            if log_mode.get('x'):
                if np.any(x_valid <= 0.0):
                    logger.warning("Skipping values <= 0 on x-axis")
                    x_args = np.argwhere(np.isfinite(x) & (x > 0)).T[0]
                    if len(x_args) == 0:
                        logger.warning("No data left on x-axis")
                        return
                    x_limit = [np.min(x_args), np.max(x_args)]
                    x_slice = slice(x_limit[0], x_limit[1]+1)
                    x_valid = x[x_slice]
                x_valid = np.log10(x_valid)

            y_valid = y[y_slice]
            if log_mode.get('y'):
                if np.any(y_valid <= 0.0):
                    logger.warning("Skipping values <= 0 on y-axis")
                    y_args = np.argwhere(np.isfinite(y) & (y > 0)).T[0]
                    if len(y_args) == 0:
                        logger.warning("No data left on y-axis")
                        return
                    y_limit = [np.min(y_args), np.max(y_args)]
                    y_slice = slice(y_limit[0], y_limit[1]+1)
                    y_valid = y[y_slice]
                y_valid = np.log10(y_valid)

            x_edges = self._get_edges(x_valid)
            y_edges = self._get_edges(y_valid)

            x_grid = x_edges[:, None] * np.ones(len(y_edges))
            y_grid = y_edges * np.ones(len(x_edges))[:, None]
            z = data.data[x_slice, y_slice]
            self.mesh.setData(x_grid, y_grid, z)

            # Calculate min/max values to show data with small empty border.
            # Default behavior of pyqtgraph is to select 'notural' values on axis.
            # This behavior can result in a big white space around the data.
            x_min, x_max = self._get_axis_limits(x_edges)
            y_min, y_max = self._get_axis_limits(y_edges)

            self.plot.setLimits(xMin=x_min, xMax=x_max, yMin=y_min, yMax=y_max)
            self.plot.invertY(False)

    def _get_edges(self, x):
        nx = len(x)+1
        edges = np.zeros(nx)
        edges[1:-1] = (x[1:] + x[:-1])/2
        edges[0] = 2*x[0] - edges[1]
        edges[-1] = 2*x[-1] - edges[-2]
        return edges

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
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.plot.sceneBoundingRect().contains(pos):
            mousePoint = vb.mapSceneToView(pos)
            x_val = mousePoint.x()
            y_val = mousePoint.y()
            if self._log_mode.get('x'):
                  x_val = 10**x_val
            if self._log_mode.get('y'):
                  y_val = 10**y_val

            data = self._data
            z = data * self._z_formatter.scale
            x = data[data.dims[0]] * self._x_formatter.scale
            y = data[data.dims[1]] * self._y_formatter.scale

            # Note: numpy 1.22 has nanargmin, but we're still on python 3.7.
            # So use a[isnan(a)] = np.inf to remove nans
            d = np.abs(x.data-x_val)
            d[np.isnan(d)] = np.inf
            ix = d.argmin()
            d = np.abs(y.data-y_val)
            d[np.isnan(d)] = np.inf
            iy = d.argmin()
            value = z.data[ix, iy]
            x_val = x.data[ix]
            y_val = y.data[iy]

            x_str = self._x_formatter.with_units(x_val, x)
            y_str = self._y_formatter.with_units(y_val, y)
            z_str = self._z_formatter.with_units(value, z)

            self.label.setText(f"x={x_str}, y={y_str}: {z_str}")


def get_color_map():
    numofLines = 5
    cMapType = 'viridis'
    colorMap = get_cmap(cMapType) # get_cmap is matplotlib object

    colorList = np.linspace(0, 1, numofLines)
    lineColors = colorMap(colorList)

    lineColors = lineColors * 255
    lineColors = lineColors.astype(int)
    return pg.ColorMap(pos=np.linspace(0.0, 1.0, numofLines), color=lineColors)

