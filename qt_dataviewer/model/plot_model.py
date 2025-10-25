import logging
import time
from dataclasses import dataclass
from numbers import Number

import numpy as np
import xarray as xr
from .histograms import histogram
from .fft import apply_fft


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
    fft: bool = False


@dataclass
class VariableSettings:
    logarithmic: bool = False
    histogram_mode: AxisMode = None
    hist_bins: int = 20
    hist_range: tuple[float, float] | None = None
    manual_value_range: tuple[float, float] | None = None
    slice_value_range: tuple[float, float] | None = None
    show_sidebar: bool = False
    multiline_plot: bool = False

    @property
    def value_range(self) -> tuple[float, float] | None:
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
        self._axis_settings: list[AxisSettings] = []
        self._var_settings = VariableSettings()
        self._changed = False
        self._current_x = None
        self._current_y = None
        self._last_selected_data = None

        self._add_axes()

        if data.name.endswith('_fraction') or data.attrs.get('units') == '%':
            self.set_value_range((0, 1))

    def _add_axes(self):
        x_axis = None
        y_axis = None
        for i, axis_name in enumerate(self._data.dims):
            data = self._data[axis_name]
            settings = AxisSettings(data, AxisMode.Average)
            self._axis_settings.append(settings)

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
        if not issubclass(data.dtype.type, Number):
            if issubclass(data.dtype.type, str):
                return "labels"
            else:
                raise Exception(f"Unknown dtype {data.dtype} for {axis.name}")
        if axis.attrs.get('units') == "|..>":
            return "qubit-register"
        ind = np.nonzero(np.isfinite(data))[0]
        n = len(ind)
        if n < 3:
            # need at least 3 points to check for logarithmic axis
            return 'lin'
        # remove NaN
        data = data[ind]

        unsorted_postfix = ""

        deltas = data[1:] - data[:-1]
        delta_ratio = np.max(deltas)/np.min(deltas)
        if delta_ratio <= 0:
            logger.warning(f"Unsorted data on axis {axis.name} will be sorted")
            unsorted_postfix = '_unsorted'
            data = np.sort(data)
            deltas = data[1:] - data[:-1]

        is_lin = 0.999 < delta_ratio < 1.001
        if is_lin:
            return 'lin' + unsorted_postfix

        # Compare with linear fit. Max difference < mean delta.
        line = np.linspace(data[0], data[-1], len(data))
        max_dev = np.max(np.abs(line-data) / np.mean(deltas))
        if max_dev < 1.0:
            return 'lin' + unsorted_postfix

        if np.any(data <= 0.0):
            return 'irregular' + unsorted_postfix

        # Add small number to avoid 0.0 in division.
        data_finite = data + 1e-100
        ratio = data_finite[:-1] / data_finite[1:]
        # the mean ratio must differ from 1.0
        mean_ratio = np.mean(ratio)
        ratio_ratio = np.min(ratio)/np.max(ratio)
        ratio_ratio = (ratio_ratio - 1) / n + 1
        is_log = (
                0.99 < ratio_ratio < 1.01
                and (mean_ratio < 0.999 or mean_ratio > 1.001))
        if is_log:
            return 'log' + unsorted_postfix
        # TODO lin_irregular / log_irregular? => auto log
        return 'irregular' + unsorted_postfix

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
                axis_data.attrs['scale'] = self._detect_axis_scale(axis_data)
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

    @plot_changer
    def set_axis_fft(self, index, fft_on):
        old_setting = self._axis_settings[index].fft
        if old_setting != fft_on:
            self._axis_settings[index].fft = fft_on
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
    def set_value_range(self, value_range: tuple[float, float] | None):
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

    def get_data(self):
        if not self._changed and self._last_selected_data is not None:
            return self._last_selected_data
        logger.debug(f"get_data {self.var_name}")
        start = time.perf_counter()
        histogram_mode = self._var_settings.histogram_mode
        da = self._data
        dims = [settings.data.name for settings in self._axis_settings]
        for settings in reversed(self._axis_settings):
            dim_name = settings.data.name
            da[dim_name].attrs['log'] = settings.logarithmic
            if settings.mode == AxisMode.Average:
                if histogram_mode is None:
                    da = da.mean(dim_name)
                dims.remove(dim_name)
                continue

        # NOTE: attributes get lost during averaging.
        for name in ['units', 'long_name']:
            try:
                da.attrs[name] = self._data.attrs[name]
            except KeyError:
                pass

        # Note: order of Average and FFT matter, because of np.abs() of FFT.
        # First average than FFT.
        for settings in reversed(self._axis_settings):
            dim_name = settings.data.name
            if settings.fft and settings.mode in [AxisMode.XAxis, AxisMode.YAxis]:
                da = apply_fft(da, dim_name)
                da[dim_name].attrs['log'] = settings.logarithmic

        value_range = (float(da.min().real), float(da.max().real)) # TODO @@@ handle complex data properly
        if histogram_mode is not None:
            logger.debug("start histogram")
            da = histogram(da, dims + ['histogram'], 50, value_range) # TODO bins, range
            da['histogram'].attrs['log'] = False
            value_range = (float(da.min()), float(da.max()))
            logger.debug("done histogram")

        # @@@ Cache pre-slice value
        # @@@ set attrs['log'] after calc.

        has_slice = False
        for settings in self._axis_settings:
            dim_name = settings.data.name
            if settings.mode == AxisMode.Slice:
                has_slice = True
                da = da[{dim_name: settings.slice_index}].drop(dim_name)
                continue

        self._var_settings.slice_value_range = value_range if has_slice else None

        da.attrs['log'] = self._var_settings.logarithmic
        logger.debug(f"Done get_data {self.var_name}")
        dims = [da[dim].name for dim in self.dims]
        da = da.transpose(*dims)
        self._last_selected_data = da
        self._changed = False
        duration = time.perf_counter() - start
        logger.info(f"Updated {self.var_name} {duration*1000:.1f} ms")
        return da



