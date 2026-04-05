import xarray as xr

from qtpy import QtWidgets

from qt_dataviewer.model.plot_model import PlotModel
from .plots import BasePlot
from .plot_0d import Plot0D
from .plot_1d import Plot1D
from .plot_2d import Plot2D
from .plot_multiline import PlotMultiline
from .plot_scatter import PlotScatter


class DataArrayPlotter:
    def __init__(self, data: xr.DataArray, seq_nr: float):
        self._plot: BasePlot | None = None
        self._layout = None
        self.name = data.attrs.get("long_name", data.name)
        if self.name is None:
            self.name = "<no name>"
        if "long_name" not in data.attrs:
            data.attrs["long_name"] = "<no name>"
        plot_model = PlotModel(data, seq_nr)
        self._plot_model = plot_model
        plot_model.set_plotter(self)

    @property
    def plot_model(self):
        return self._plot_model

    def set_layout(self, layout: QtWidgets.QVBoxLayout):
        self._layout = layout
        if layout is None and self._plot is not None:
            self._plot.remove()
            self._plot = None
        self.update()

    def update(self):
        if self._layout is None:
            return
        plot_model = self._plot_model
        plot_axes = plot_model.plot_axes
        ndim = len(plot_axes)
        gridded = plot_model.gridded
        plot = self._plot

        if plot is not None:
            if (plot.plot_axes != plot_axes
                    or plot.gridded != gridded
                    or (ndim == 1 and plot.one_d_is_vertical != plot_model.one_d_is_vertical)
                    or (ndim == 2 and plot.multiline_plot != plot_model.multiline_plot)):
                plot.remove()
                plot = None
        if plot_model.error_message:
            self._plot = None
            return
        if plot is None:
            self._plot = self._create_plot()
        else:
            plot.update()

    def update_data(self, data: xr.DataArray):
        self._plot_model.update_data(data)

    def _create_plot(self):
        plot_model = self._plot_model
        plot_axes = plot_model.plot_axes
        ndim = len(plot_axes)
        gridded = plot_model.gridded

        if ndim == 0:
            return Plot0D(self._layout, plot_model)
        if ndim == 1:
            return Plot1D(self._layout, plot_model)
        if ndim == 2:
            if gridded:
                if plot_model.multiline_plot:
                    return PlotMultiline(self._layout, plot_model)
                else:
                    return Plot2D(self._layout, plot_model)
            else:
                return PlotScatter(self._layout, plot_model)
            return None
