import xarray as xr

from PyQt5 import QtWidgets

from qt_dataviewer.model.plot_model import PlotModel
from qt_dataviewer.plot_ui.plot_0d import Plot0D
from qt_dataviewer.plot_ui.plot_1d import Plot1D
from qt_dataviewer.plot_ui.plot_2d import Plot2D
from qt_dataviewer.plot_ui.plot_multiline import PlotMultiline


class DataArrayPlotter:
    def __init__(self, data: xr.DataArray, seq_nr: float):
        self._plot = None
        self._layout = None
        self._multiline_plot = False
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
        ndim = plot_model.ndim
        plot = self._plot

        if plot is not None:
            if (plot_model.dims != self._plot.dims
                    or self._plot.one_d_is_vertical != plot_model.one_d_is_vertical
                    or (ndim == 2 and self._multiline_plot != plot_model.multiline_plot)):
                plot.remove()
                plot = None
        if plot_model.error_message:
            self._plot = None
            return
        if plot is None:
            self._multiline_plot = False
            if ndim == 0:
                plot = Plot0D(self._layout, plot_model)
            elif ndim == 1:
                plot = Plot1D(self._layout, plot_model)
            elif ndim == 2:
                if plot_model.multiline_plot:
                    self._multiline_plot = True
                    plot = PlotMultiline(self._layout, plot_model)
                else:
                    plot = Plot2D(self._layout, plot_model)
            else:
                ...
                # plot = NoData
                # plot = Plot0D
            self._plot = plot
        else:
            plot.update()

    def update_data(self, data: xr.DataArray):
        self._plot_model.update_data(data)
