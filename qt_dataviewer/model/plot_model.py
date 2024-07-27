import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import xarray as xr

from .histograms import histogram


logger = logging.getLogger(__name__)


class AxisMode:
    XAxis = 0
    YAxis = 1
    Average = 2
    Slice = 3


@dataclass
class AxisSettings:
    data: xr.DataArray
    mode: AxisMode
    logarithmic: bool = False
    slice_index: int = 0


@dataclass
class VariableSettings:
    logarithmic: bool = False
    histogram_mode: AxisMode = None
    hist_bins: int = 20
    hist_range: Optional[Tuple[float, float]] = None
    manual_value_range: Optional[Tuple[float, float]] = None
    slice_value_range: Optional[Tuple[float, float]] = None
    show_sidebar: bool = False
    multiline_plot: bool = False

    @property
    def value_range(self) -> Optional[Tuple[float, float]]:
        if self.manual_value_range is not None:
            return self.manual_value_range
        return self.slice_value_range


def plot_changer(func):
    def _wrapped(self, *args, **kwargs):
        try:
            self._nested_ += 1
        except AttributeError:
            self._nested_ = 1
        try:
            return func(self, *args, **kwargs)
        finally:
            self._nested_ -= 1
            if self._nested_ == 0:
                self.update()
    return _wrapped


class PlotModel:
    def __init__(self, data: xr.DataArray, seq_nr: float):
        self._data = data
        self._seq_nr = seq_nr
        self._plotter = None
        self._axis_settings: List[AxisSettings] = []
        self._var_settings = VariableSettings()
        self._changed = False
        self._current_x = None
        self._current_y = None
        self._last_selected_data = None

        self._add_axes()

        if data.name.endswith('_fraction') or data.attrs['units'] == '%':
            self.set_value_range((0, 1))

    def _add_axes(self):
        x_axis = None
        y_axis = None
        # total_axis = len(self._data.coords)
        for i, (axis_name, data) in enumerate(self._data.coords.items()):
            settings = AxisSettings(data, AxisMode.Average)
            self._axis_settings.append(settings)

            # if total_axis > 1 and axis_name == 'repetition':
            #     self.set_axis_mode(i, AxisMode.Average)
            #     continue
            if x_axis is None and len(data) > 1:
                self.set_axis_mode(i, AxisMode.XAxis)
                x_axis = i
            elif y_axis is None and len(data) > 1:
                self.set_axis_mode(x_axis, AxisMode.YAxis)
                y_axis = x_axis
                self.set_axis_mode(i, AxisMode.XAxis)
                x_axis = i
            data.attrs['scale'] = self._detect_axis_scale(data)

    def _detect_axis_scale(self, axis):
        data = axis.data
        ind = np.argwhere(np.isfinite(data)).T[0]
        n = len(ind)
        if n < 3:
            # need at least 3 points to check for logarithmic axis
            return 'lin'
        # remove NaN
        data = data[ind]

        deltas = data[1:] - data[:-1]
        delta_ratio = np.min(deltas)/np.max(deltas)
        delta_ratio = (delta_ratio - 1) / n + 1
        is_lin = 0.999 < delta_ratio < 1.001
        if is_lin:
            return 'lin'

        if delta_ratio <= 0:
            logger.error(f"Unsorted data on axis {axis.name}")
            # TODO unsorted, lin/log, regular/irregular
            return 'unsorted'

        data_finite = data + 1e-100
        ratio = data_finite[:-1] / data_finite[1:]
        mean_ratio = np.mean(ratio)
        ratio_ratio = np.min(ratio)/np.max(ratio)
        ratio_ratio = (ratio_ratio - 1) / n + 1
        is_log = (
                0.999 < ratio_ratio < 1.001
                and (mean_ratio < 0.99 or mean_ratio > 1.01))
        if is_log:
            return 'log'
        # TODO lin_irregular / log_irregular? => auto log
        return 'irregular'

    @plot_changer
    def update_data(self, data: xr.DataArray):
        try:
            if data.name != self._data.name:
                raise Exception(f"OOPS!! name of array doesn't match {data.name} <> {self._data.name}")

            old_labels = [settings.data.attrs.get('long_name', settings.data.name) for settings in self._axis_settings]
            new_labels = [data[dim].attrs.get('long_name', data[dim].name) for dim in data.dims]
            if old_labels != new_labels:
                logger.error(f"Labels differ {new_labels} <> {old_labels} {data.dims} {self._data.dims}")

            self._data = data
            for i, dim in enumerate(data.dims):
                axis_data = data[dim]
                settings = self._axis_settings[i]
                # labels must be equal. The name can change due to xarray conversion.
                new_axis_label = axis_data.attrs.get('long_name', axis_data.name)
                old_axis_label = settings.data.attrs.get('long_name', settings.data.name)
                if new_axis_label != old_axis_label:
                    raise Exception(f"OOPS!! name of coordinate {i} doesn't match "
                                    f"{new_axis_label} <> {old_axis_label}")
                settings.data = axis_data
            self._changed = True
        except Exception:
            logger.error('update failed', exc_info=True)

    @property
    def seq_nr(self):
        return self._seq_nr

    @property
    def var_name(self):
        return self._data.name

    def set_plotter(self, plotter):
        self._plotter = plotter
        self.update()

    @property
    def n_axis(self):
        return len(self._axis_settings)

    @property
    def ndim(self):
        ndim = 0
        if self._current_x is not None:
            ndim += 1
        if self._current_y is not None:
            ndim += 1
        return ndim

    @property
    def dims(self):
        dims = []
        if self._current_x is not None:
            x = self._current_x
            if isinstance(x, int):
                x = self._axis_settings[x].data.name
            dims.append(x)
        if self._current_y is not None:
            y = self._current_y
            if isinstance(y, int):
                y = self._axis_settings[y].data.name
            dims.append(y)
        return dims

    @property
    def one_d_is_vertical(self):
        return self._current_x is None and self._current_y is not None

    def get_axis_settings(self, index) -> AxisSettings:
        return self._axis_settings[index]

    @plot_changer
    def set_axis_mode(self, index, mode: AxisMode):
        if index == 'histogram':
            old_mode = self._var_settings.histogram_mode
        else:
            old_mode = self._axis_settings[index].mode
        if old_mode != mode:
            if self._current_x == index:
                self._current_x = None
            if self._current_y == index:
                self._current_y = None
            if mode == AxisMode.XAxis:
                if self._current_x is not None:
                    if old_mode == AxisMode.YAxis:
                        self.set_axis_mode(self._current_x, AxisMode.YAxis)
                    else:
                        self.set_axis_mode(self._current_x, AxisMode.Average)
                self._current_x = index
            if mode == AxisMode.YAxis:
                if self._current_y is not None:
                    if old_mode == AxisMode.XAxis:
                        self.set_axis_mode(self._current_y, AxisMode.XAxis)
                    else:
                        self.set_axis_mode(self._current_y, AxisMode.Average)
                self._current_y = index
            if index == 'histogram':
                self._var_settings.histogram_mode = mode if mode in [AxisMode.XAxis, AxisMode.YAxis] else None
            else:
                self._axis_settings[index].mode = mode
            self._changed = True

    @plot_changer
    def set_axis_log(self, index, logarithmic):
        old_setting = self._axis_settings[index].logarithmic
        if old_setting != logarithmic:
            self._axis_settings[index].logarithmic = logarithmic
            self._changed = True

    @plot_changer
    def set_axis_slice(self, index, slice_index):
        old_index = self._axis_settings[index].slice_index
        if old_index != slice_index:
            self._axis_settings[index].slice_index = slice_index
            self._changed = True

    @property
    def histogram_mode(self):
        return self._var_settings.histogram_mode

    @plot_changer
    def set_logarithmic(self, logarithmic):
        if self._var_settings.logarithmic != logarithmic:
            self._var_settings.logarithmic = logarithmic
            self._changed = True

    @property
    def logarithmic(self):
        return self._var_settings.logarithmic

    @plot_changer
    def set_multiline_plot(self, multiline_plot):
        if self._var_settings.multiline_plot != multiline_plot:
            self._var_settings.multiline_plot = multiline_plot
            self._changed = True

    @property
    def multiline_plot(self):
        return self._var_settings.multiline_plot

    @plot_changer
    def set_value_range(self, value_range: Optional[Tuple[float, float]]):
        if self._var_settings.manual_value_range != value_range:
            if value_range is not None and not isinstance(value_range, tuple):
                raise ValueError(f"Invalid range {value_range}. Expected None or tuple")
            self._var_settings.manual_value_range = value_range
            self._changed = True

    @property
    def value_range(self):
        return self._var_settings.value_range

    @plot_changer
    def set_show_sidebar(self, show):
        if self._var_settings.show_sidebar != show:
            self._var_settings.show_sidebar = show
            self._changed = True

    @property
    def show_sidebar(self):
        return self._var_settings.show_sidebar

    def update(self):
        if self._changed and self._plotter:
            self._plotter.update()
            # self._changed = False

    def get_data(self):
        if not self._changed and self._last_selected_data is not None:
            return self._last_selected_data
        logger.debug(f"get_data {self.var_name}")
        start = time.perf_counter()
        histogram_mode = self._var_settings.histogram_mode
        da = self._data
        dims = [settings.data.name for settings in self._axis_settings]
        if histogram_mode is None:
            for settings in reversed(self._axis_settings):
                if settings.mode == AxisMode.Average:
                    dim_name = settings.data.name
                    da = da.mean(dim_name)
                    dims.remove(dim_name)

        value_range = (float(da.min()), float(da.max()))
        # if histogram_mode is not None:
        #     da = histogram(da, dims, 40, value_range) # TODO bins, range
        #     da['histogram'].attrs['log'] = False
        #     value_range = (float(da.min()), float(da.max()))

        has_slice = False
        for settings in self._axis_settings:
            dim_name = settings.data.name
            if dim_name in da.coords:
                da[dim_name].attrs['log'] = settings.logarithmic
            if settings.mode == AxisMode.Slice:
                has_slice = True
                da = da[{dim_name:settings.slice_index}].drop(dim_name)

        self._var_settings.slice_value_range = value_range if has_slice and histogram_mode is None else None

        if histogram_mode is not None:
            da = histogram(da, self.dims, 50, value_range) # TODO bins, range
            da['histogram'].attrs['log'] = False
            # TODO: set slice_value_range
            # if has_slice:
            #     self._var_settings.slice_value_range = value_range
        else:
            for name in ['units', 'long_name']:
                da.attrs[name] = self._data.attrs[name]

        da.attrs['log'] = self._var_settings.logarithmic
        logger.debug(f"Done get_data {self.var_name}")
        dims = [da[coord].dims[0] for coord in self.dims]
        da = da.transpose(*dims)
        self._last_selected_data = da
        self._changed = False
        duration = time.perf_counter() - start
        logger.info(f"Updated {self.var_name} {duration*1000:.1f} ms")
        return da
