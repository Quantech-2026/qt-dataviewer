import logging
import pyqtgraph as pg
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
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

        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignRight)

        self._layout.addWidget(self.img_view)
        self._layout.addWidget(self.label)

        self.proxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.update()
        self.plot.setAspectLocked(False)

    def show_sidebar(self, show):
        histogram = self.img_view.ui.histogram
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

        x_formatter = SmartFormatter(x_array.attrs['units'])
        self._x_formatter = x_formatter
        y_formatter = SmartFormatter(y_array.attrs['units'])
        self._y_formatter = y_formatter
        z_formatter = SmartFormatter(data.attrs['units'])
        self._z_formatter = z_formatter

        x = x * x_formatter.scale
        y = y * y_formatter.scale
        log_mode = {}
        if self.detect_log_mode(x):
            log_mode['x'] = True
            x = np.log10(x)
        if self.detect_log_mode(y):
            log_mode['y'] = True
            y = np.log10(y)

        plot = self.plot
        plot.getAxis('bottom').enableAutoSIPrefix(x_formatter.auto_si_prefix)
        plot.getAxis('left').enableAutoSIPrefix(y_formatter.auto_si_prefix)
        plot.setLabel('bottom', x_array.attrs['long_name'], units=x_formatter.units)
        plot.setLabel('left', y_array.attrs['long_name'], units=y_formatter.units)
        plot.setLogMode(**log_mode)

        x_args = np.argwhere(np.isfinite(x)).T[0]
        if len(x_args) == 0:
            # No data yet. Nothing to update.
            return
        x_limit = [np.min(x_args), np.max(x_args)]
        x_limit_num = (x[x_limit[0]], x[x_limit[1]])
        y_args = np.argwhere(np.isfinite(y)).T[0]
        y_limit = [np.min(y_args), np.max(y_args)]
        y_limit_num = (y[y_limit[0]], y[y_limit[1]])

        data_cp = np.full(data.shape, np.nan)
        x_slice = slice(x_limit[0], x_limit[1]+1)
        y_slice = slice(y_limit[0], y_limit[1]+1)
        data_cp[x_slice, y_slice] = data.data[x_slice, y_slice]
        data = data_cp

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

        # flip axis is postive to negative scan
        if x_limit_num[0] > x_limit_num[1]:
            data = data[::-1, :]
            x_offset -= (len(x)-x_limit[1]-1)*x_scale
        else:
            x_offset -= x_limit[0]*x_scale
        if y_limit_num[0] > y_limit_num[1]:
            data = data[:, ::-1]
            y_offset -= (len(y)-y_limit[1]-1)*y_scale
        else:
            y_offset -= y_limit[0]*y_scale

        self.plot.invertY(False)
        self.img.setImage(data)

        tr = QtGui.QTransform()
        tr.translate(x_offset, y_offset)
        tr.scale(x_scale, y_scale)
        self.img.setTransform(tr)

    def detect_log_mode(self, data):
        ind = np.argwhere(np.isfinite(data)).T[0]
        if len(ind) < 3:
            # need at least 3 points to check for logarithmic axis
            return False
        data_finite = data[ind] + 1e-100
        ratio = data_finite[:-1] / data_finite[1:]
        mean_ratio = np.mean(ratio)
        is_log = (
                0.99999 < np.min(ratio)/np.max(ratio) < 1.00001
                and (mean_ratio < 0.99 or mean_ratio > 1.01))
        if is_log:
            logger.info(f'LOG {self.data.name}')
        return is_log

    @qt_log_exception
    def mouseMoved(self, evt):
        vb = self.plot.vb
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.plot.sceneBoundingRect().contains(pos):
            mousePoint = vb.mapSceneToView(pos)
            x_val = mousePoint.x()
            # if self.logmode['x'] == True: # @@@
            #     x_val = 10**x_val
            y_val = mousePoint.y()
            # if self.logmode['y'] == True:
            #     y_val = 10**y_val

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

