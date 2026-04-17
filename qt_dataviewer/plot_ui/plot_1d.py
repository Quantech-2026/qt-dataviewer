import pyqtgraph as pg
import numpy as np
import xarray as xr

from numpy.typing import NDArray
from qtpy import QtCore, QtWidgets, QtGui
from qt_dataviewer.model.plot_model import ComplexMode
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
        self.proxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

        self.curves = []
        self._legend = None
        self._complex_mode = None
        self._polar = False
        self._polar_circles = []
        self._is_nyquist = False
        self._manual_range = np.array([False, False])

        vb = self.plot.getViewBox()
        vb.sigRangeChanged.connect(self._update_range)
        vb.sigRangeChangedManually.connect(self._update_range_manually)

        self.update()

    def _update_range(self, vb: object, view_range: list[list[int]], changed: list[bool]):
        self._update_grid()
        self._manual_range &= ~np.array(changed)

    def _update_range_manually(self, changed: list[bool]):
        self._manual_range |= changed

    @qt_log_exception
    def update(self):
        plot_model = self._plot_model
        plot = self.plot

        x, y = self._get_plot_data()
        if np.iscomplexobj(y):
            complex_mode = plot_model.complex_mode
        else:
            complex_mode = None

        if complex_mode != self._complex_mode:
            plot.clearPlots()
            self.curves = []
            self._complex_mode = complex_mode

        polar = False
        lock_aspect = False
        match complex_mode:
            case ComplexMode.Re | None:
                self._plot([(x, y.real, "")])
            case ComplexMode.Im:
                self._plot([(x, y.imag, "")])
            case ComplexMode.ReIm:
                self._plot([
                    (x, y.real, ".real"),
                    (x, y.imag, ".imag"),
                    ])
            case ComplexMode.Amplitude:
                self._plot([(x, np.abs(y), "")])
            case ComplexMode.Phase:
                self._plot([(x, np.angle(y), "")])
            case ComplexMode.AmplitudePhase:
                self._plot([
                    (x, np.abs(y), ".ampl"),
                    (x, np.angle(y), ".phase"),
                    ])
            case ComplexMode.Nyquist | ComplexMode.NyquistPolar:
                self._plot([(y.real, y.imag, "")])
                lock_aspect = True
                if complex_mode == ComplexMode.NyquistPolar:
                    polar = True

        self._polar = polar
        plot.setAspectLocked(lock=lock_aspect)
        self._update_grid()

    def _update_grid(self):
        polar = self._polar
        plot = self.plot
        for circle in self._polar_circles:
            plot.removeItem(circle)
        self._polar_circles = []
        if polar:
            view_range = plot.getViewBox().viewRange()
            range_min = [None, None]
            range_max = [None, None]
            for axis in [0, 1]:
                axis_range = view_range[axis]
                if axis_range[0] < 0 < axis_range[1]:
                    range_min[axis] = 0
                else:
                    range_min[axis] = np.abs(axis_range).min()
                range_max[axis] = np.abs(axis_range).max()

            min_r = np.linalg.norm(range_min)
            max_r = np.linalg.norm(range_max)
            step = self._get_tick_step(max_r - min_r)
            min_r = step * np.floor(min_r / step)
            max_r = step * np.ceil(max_r / step)

            plot.showGrid(False, False)

            color = pg.getConfigOption("foreground")
            thick_pen = pg.mkPen(color)
            color = QtGui.QColor(thick_pen.color())  # copy to a new QColor
            color.setAlpha(128)  # adjust opacity
            thick_pen.setColor(color)
            thin_pen = QtGui.QPen(thick_pen)  # copy to a new QPen
            color = QtGui.QColor(thick_pen.color())
            color.setAlpha(64)
            thin_pen.setColor(color)

            self._polar_circles.append(plot.addLine(x=0, pen=thick_pen))
            self._polar_circles.append(plot.addLine(y=0, pen=thick_pen))
            for angle in [30, 60, 120, 150]:
                self._polar_circles.append(plot.addLine(pos=[0, 0], angle=angle, pen=thin_pen))

            for i, r in enumerate(np.arange(min_r, max_r, step/10)):
                if r == 0:
                    continue
                circle = pg.QtWidgets.QGraphicsEllipseItem(-r, -r, 2*r, 2*r)
                circle.setPen(thick_pen if i % 10 == 0 else thin_pen)
                plot.addItem(circle, ignoreBounds=True)
                self._polar_circles.append(circle)
        else:
            plot.showGrid(True, True)

    def _get_tick_step(self, max_value):
        step = max_value / 6
        exp10 = 10**np.floor(np.log10(step))
        coefficient = step/exp10
        for r in [2, 5, 10]:
            if coefficient <= r:
                return r * exp10
        return 10*exp10

    def _plot(self, plots: list[tuple[NDArray, NDArray, str]]):
        name = self._plot_model.var_name
        curves = self.curves
        plot = self.plot

        legend = getattr(plot.plotItem, "legend", None)
        if len(plots) > 1 and legend is None:
            plot.addLegend()
        elif len(plots) == 1 and legend is not None:
            plot.removeItem(legend)
            # PlotItem does not have a remove legend. This works.
            plot.plotItem.legend = None

        for i, (x, y, suffix) in enumerate(plots):
            if self.one_d_is_vertical and not self._is_nyquist:
                x, y = y, x
            if i >= len(curves):
                # create new curve
                style = graph_color[i]
                if x.ndim == 0:
                    curve_style = dict(**style, symbolPen="w", symbolSize=12)
                    curve = plot.plot([x], [y], **curve_style, name=name+suffix, connect='finite')
                else:
                    npt = len(x)
                    if self.gridded:
                        if npt > 100: # TODO configurable.
                            curve_style = {"pen": style["pen"]}
                        else:
                            curve_style = dict(**style, symbolPen="w", symbolSize=6)
                    else:
                        # Scatter plot; no lines
                        if npt < 40:
                            size = 12
                        elif npt < 100:
                            size = 10
                        else:
                            size = 8
                        curve_style = {n: style[n] for n in ["symbolBrush", "symbol"]}
                        curve_style.update({"pen": None, "symbolPen": "w", "symbolSize": size})
                    curve = plot.plot(x, y, **curve_style, name=name+suffix, connect='finite')
                curves.append(curve)
            else:
                if x.ndim == 0:
                    curves[i].setData([x], [y])
                else:
                    curves[i].setData(x, y)

    def _get_plot_data(self):
        plot_model = self._plot_model
        data = plot_model.get_data()

        x_name = self.plot_axes[0]

        x = data[x_name]
        if self.gridded and x.attrs.get('scale', '').endswith("_unsorted"):
            data = data.sortby(x.name)
            x = data[x_name]
        self._data = data
        y = data

        x_formatter = SmartFormatter(x)
        y_formatter = SmartFormatter(y)

        self._x_formatter = x_formatter
        self._y_formatter = y_formatter

        self._is_nyquist = (np.iscomplexobj(y)
                            and plot_model.complex_mode in [ComplexMode.Nyquist, ComplexMode.NyquistPolar])
        if self._is_nyquist:
            plot = self.plot
            plot.setLogMode(x=False, y=False)
            plot_axis = plot.getAxis("bottom")
            y_formatter.set_plot_axis(plot_axis)
            plot_axis = plot.getAxis("left")
            y_formatter.set_plot_axis(plot_axis)

            y_data = y_formatter.without_unit_prefix(y)
            self.x_data = y_data.real
            self.y_data = y_data.imag
            self.x_axis = None
            x_axis = None
        else:
            if self.one_d_is_vertical:
                x_pos = "left"
                y_pos = "bottom"
                y_axis = 0
            else:
                x_pos = "bottom"
                y_pos = "left"
                y_axis = 1
            y_value_range = plot_model.value_range if not self._manual_range[y_axis] else None
            x_axis, x_data = self._set_axis(x, x_formatter, x_pos)
            # TODO complex: 2nd axis phase, value ranges imag
            _, y_data = self._set_axis(y, y_formatter, y_pos, y_value_range)

            # store for mouse cursor
            self.x_data = x_data
            self.x_axis = x_axis
            self.y_data = y_data
        return x_axis, y_data

    def _set_axis(self, data: xr.DataArray, formatter: SmartFormatter, axis_name: str,
                  value_range: tuple[float, float] | None = None):
        axis = "x" if axis_name == "bottom" else "y"
        log_mode = formatter.log
        plot = self.plot
        plot.setLogMode(**{axis: log_mode})
        plot_axis = plot.getAxis(axis_name)
        formatter.set_plot_axis(plot_axis)

        plot_data = formatter.without_unit_prefix(data)

        if issubclass(data.dtype.type, str) or formatter._units == "|..>": # TODO add to smartformatter?
            formatter.set_labels(plot_axis, data.data)
            axis_values = np.arange(len(data))
        else:
            axis_values = plot_data.data

        if value_range is not None and not any(np.isnan(value_range)):
            mn = formatter.without_unit_prefix(value_range[0])
            mx = formatter.without_unit_prefix(value_range[1])
            if log_mode:
                if mx <= 0:
                    mn, mx = 0.0, 1.0
                else:
                    mx = np.log10(mx)
                    if mn <= 0:
                        # If 0 or negative, plot 6 decades
                        mn = mx - 6
                    else:
                        mn = np.log10(mn)
            if not any(np.isnan([mn, mx])):
                plot.setRange(**{axis+"Range": [mn, mx]})

        return axis_values, plot_data

    @qt_log_exception
    def mouseMoved(self, evt):
        vb = self.plot.getPlotItem().vb
        pos = evt[0]  # using signal proxy turns original arguments into a tuple
        if vb.sceneBoundingRect().contains(pos):
            mousePoint = vb.mapSceneToView(pos)
            x_val = mousePoint.x()
            y_val = mousePoint.y()

            if self.one_d_is_vertical and not self._is_nyquist:
                x_val, y_val = y_val, x_val

            if self._x_formatter.log:
                x_val = 10**x_val
            if self._y_formatter.log:
                y_val = 10**y_val

            x_data = self.x_data
            x_axis = self.x_axis
            y_data = self.y_data
            plot_model = self._plot_model
            if self.x_axis is None and plot_model.complex_mode in [ComplexMode.Nyquist, ComplexMode.NyquistPolar]:
                x_str = self._y_formatter.with_units(x_val, x_data)
                y_str = self._y_formatter.with_units(y_val, y_data)
            else:
                if y_data.ndim == 0:
                    x_val = x_data
                    y_val = y_data
                else:
                    d = np.abs(x_axis - x_val)
                    idx = np.nanargmin(d)
                    x_val = x_data[idx]
                    y_val = y_data[idx]

                x_str = self._x_formatter.with_units(x_val.item(), x_data) # x_data
                y_str = self._y_formatter.with_units(y_val.item().real, y_data.real)  # TODO Add complex formatting

                if self.one_d_is_vertical and not self._is_nyquist:
                    x_str, y_str = y_str, x_str

            self.label.setText(f"x={x_str}, y={y_str}")

        # Mouse in Nyquist?
        # print real/imag values of mouse pointer.
        # Alternative: complex: np.nanargmin(np.abs(mouse-curve)) highlight point for 0.5 s with open dot.
        # point should be close enough..  data point -> pos and compare pixels. CHECK pixels!
