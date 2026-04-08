from __future__ import annotations
import logging
import re
import time
from dataclasses import dataclass, field
from enum import StrEnum, IntEnum
from numbers import Number

import numpy as np
import xarray as xr
from .histograms import histogram
from .fft import apply_fft


logger = logging.getLogger(__name__)


"""
Notes on plotting.

Selected data can be gridded, i.e. all plot axis are dimensions of the data
and all dimensions are plotted.

All other selected data is non-gridded: data contains dimension that is not on axis.
"""


class AxisMode:
    XAxis = 0
    YAxis = 1
    Average = 2
    Slice = 3
    All = 4


class ComplexMode(StrEnum):
    """
    FFT:
        FFT gives complex data, but we only return amplitude!
        Complex input for FFT does not make sense.
        Re, Im, or amplitude input, amplitude output.
        Re+Im input?
        => Info line on settings panel !! Plotting FFT of real component / amplitude.
    Histogram:
        Re, Im or amplitude output.

    Model.is_complex
    Model.complex_mode
    """
    Re = "Re"
    Im = "Im"
    ReIm = "Re+Im"
    Nyquist = "Nyquist"
    NyquistPolar = "Nyquist (polar)"
    Amplitude = "Amplitude"
    Phase = "Phase"
    AmplitudePhase = "Amplitude+Phase"

    @staticmethod
    def modes_2D():
        return [ComplexMode.Re, ComplexMode.Im, ComplexMode.Amplitude, ComplexMode.Phase]

    def to_2D_mode(self):
        if self in [ComplexMode.ReIm, ComplexMode.Nyquist, ComplexMode.NyquistPolar]:
            return ComplexMode.Re
        if self == ComplexMode.AmplitudePhase:
            return ComplexMode.Amplitude
        return self


class AxisType(IntEnum):
    Dim = 1
    Coord = 2
    DimCoord = 3

    @property
    def is_dim(self):
        return (self & 1) != 0

    @property
    def is_coord(self):
        return (self & 2) != 0


@dataclass
class AxisSettings:
    name: str
    data: xr.DataArray = field(repr=False)
    axis_type: AxisType
    mode: AxisMode = AxisMode.All
    logarithmic: bool = False
    slice_index: int = 0
    fft: bool = False

    @property
    def dims(self):
        return self.data.dims

    def update_dim_size(self, size: int):
        self.data = self._get_dim_data(self.name, size)

    @staticmethod
    def _get_dim_data(name, size):
        return xr.DataArray(
            name=name,
            data=np.arange(size, dtype=int),
            dims=(name,),
            )

    @staticmethod
    def from_coords(coords: xr.DataArray) -> AxisSettings:
        if (coords.name, ) == coords.dims:
            axis_type = AxisType.DimCoord
            mode = AxisMode.Average
        else:
            axis_type = AxisType.Coord
            mode = AxisMode.All
        return AxisSettings(coords.name, coords, axis_type, mode)

    @staticmethod
    def from_dim(name: str, size: int) -> AxisSettings:
        data = AxisSettings._get_dim_data(name, size)
        ax = AxisSettings(name, data, AxisType.Dim, AxisMode.All)
        return ax


@dataclass
class VariableSettings:
    logarithmic: bool = False
    histogram_mode: AxisMode = None
    hist_bins: int = 20
    hist_range: tuple[float, float] | None = None
    manual_value_range: tuple[float, float] | None = None
    slice_value_range: tuple[float, float] | None = None
    slice_imag_range: tuple[float, float] | None = None
    slice_ampl_range: tuple[float, float] | None = None
    show_sidebar: str = "off"
    multiline_plot: bool = False
    complex_mode: ComplexMode = ComplexMode.Re

    @property
    def value_range(self) -> tuple[float, float] | None:
        if self.manual_value_range is not None:
            return self.manual_value_range
        return self.slice_value_range

    @property
    def imag_range(self) -> tuple[float, float] | None:
        if self.manual_value_range is not None:
            return self.manual_value_range
        return self.slice_imag_value_range

    @property
    def amplitude_range(self) -> tuple[float, float] | None:
        if self.manual_value_range is not None:
            return self.manual_value_range
        return self.slice_ampl_value_range


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
        self._current_x = None
        self._current_y = None
        self._data_changed = True
        self._plot_changed = False
        self._slice_changed = False
        self._last_selected_data = None
        self._pre_slice_data = None
        self._info_message = None

        self._iscomplex = np.iscomplexobj(data)

        try:
            self._add_axes()

            if data.name.endswith('_fraction') or data.attrs.get('units') == '%':
                self.set_value_range((0, 1))
        except Exception as ex:
            logger.error("Exception creating plot model", exc_info=True)
            self._error_message = str(ex)
            # remove axes
            self._axis_settings: list[AxisSettings] = []
        else:
            self._error_message = None

    def _add_axes(self):
        x_axis = None
        y_axis = None
        data = self._data

        for axis_name in data.coords:
            coords = data[axis_name]
            if coords.dtype == object:
                # skip multi-index
                continue

            settings = AxisSettings.from_coords(coords)
            self._axis_settings.append(settings)
            coords.attrs['scale'] = self._detect_axis_scale(coords)
            if "log" in coords.attrs['scale']:
                settings.logarithmic = True

            idx = len(self._axis_settings) - 1
            if x_axis is None and len(coords) > 1:
                self.set_axis_mode(idx, AxisMode.XAxis)
                x_axis = idx
            elif y_axis is None and len(coords) > 1:
                self.set_axis_mode(x_axis, AxisMode.YAxis)
                y_axis = x_axis
                self.set_axis_mode(idx, AxisMode.XAxis)
                x_axis = idx

        for i, axis_name in enumerate(data.dims):
            if axis_name in data.coords and data[axis_name].dtype != object:
                continue
            settings = AxisSettings.from_dim(axis_name, data.shape[i])
            self._axis_settings.append(settings)

    def _detect_axis_scale(self, coords):
        data = coords.data
        if not issubclass(data.dtype.type, Number):
            if issubclass(data.dtype.type, str):
                return "labels"
            else:
                raise Exception(f"Unknown dtype {coords.dtype} for {coords.name}")
        if coords.attrs.get('units') == "|..>":
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
            logger.info(f"Unsorted data on axis {coords.name} will be sorted")
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
            var_name = self.var_name
            if data.name != self._data.name:
                msg = f"Update failure. Array name changed from {self._data.name} to {data.name}"
                self._error_message = msg
                raise Exception(msg)

            if self._data.dims != data.dims:
                msg = f"Dimensions of {var_name} changed from {self._data.dims} to {data.dims}"
                if not equivalent_names(self._data.dims, data.dims):
                    raise Exception(msg)
                else:
                    logger.info(msg)

            old_coords = [name for name in self._data.coords]
            new_coords = [name for name in data.coords]
            if new_coords != old_coords:
                msg = f"Coordinates of {var_name} changed from {old_coords} to {new_coords}"
                if not equivalent_names(self._data.dims, data.dims):
                    raise Exception(msg)
                else:
                    logger.info(msg)

            for i, axis_name in enumerate(data.coords):
                coords = data[axis_name]
                settings = self._axis_settings[i]
                old_coords = self._data[settings.name]
                # labels must be equal. The name can change due to xarray conversion.
                new_axis_label = coords.attrs.get('long_name', coords.name)
                old_axis_label = old_coords.attrs.get('long_name', settings.name)
                if new_axis_label != old_axis_label:
                    raise Exception(f"Coordinate of {var_name} changed from {old_axis_label} to {new_axis_label}")
                coords.attrs['scale'] = self._detect_axis_scale(coords)
                # update name, in case up equivalent names.
                settings.name = axis_name

            for settings in self._axis_settings:
                if settings.axis_type is AxisType.Dim:
                    dim_idx = self._data.dims.index(settings.name)
                    # Also update name. Could have changed. See equivalent_names.
                    settings.name = data.dims[dim_idx]
                    settings.update_dim_size(data.shape[dim_idx])

            self._data = data
            self._iscomplex = np.iscomplexobj(data)

            self._data_changed = True
        except Exception as ex:
            msg = "Update failed"
            if ex.args:
                msg += " " + str(ex.args[0])
            self._error_message = msg
            logger.error(msg, exc_info=True)

    @property
    def error_message(self) -> str | None:
        return self._error_message

    @property
    def info_message(self) -> str | None:
        return self._info_message

    @property
    def seq_nr(self) -> int:
        return self._seq_nr

    @property
    def var_name(self) -> str:
        return self._data.name

    @property
    def title(self) -> str:
        return self._data.attrs.get("long_name", self._data.name)

    @property
    def iscomplex(self) -> bool:
        return self._iscomplex

    def set_plotter(self, plotter):
        self._plotter = plotter
        self.update()

    @property
    def n_axis(self) -> int:
        return len(self._axis_settings)

    @property
    def ndim(self) -> int:
        ndim = 0
        if self._current_x is not None:
            ndim += 1
        if self._current_y is not None:
            ndim += 1
        return ndim

    @property
    def plot_axes(self) -> list[str]:
        axes = []
        if self._current_x is not None:
            x = self._current_x
            if isinstance(x, int):
                x = self._axis_settings[x].name
            axes.append(x)
        if self._current_y is not None:
            y = self._current_y
            if isinstance(y, int):
                y = self._axis_settings[y].name
            axes.append(y)
        return axes

    @property
    def gridded(self) -> bool:
        for setting in self._axis_settings:
            if setting.axis_type.is_dim:
                if setting.mode == AxisMode.All and not self.histogram_mode:
                    return False
            else:
                if setting.mode in [AxisMode.XAxis, AxisMode.YAxis]:
                    return False
        return True

    @property
    def one_d_is_vertical(self):
        return self._current_x is None and self._current_y is not None

    def get_axis_settings(self, index) -> AxisSettings:
        return self._axis_settings[index]

    @plot_changer
    def set_axis_mode(self, index: int | str, mode: AxisMode):
        axis_settings = self._axis_settings

        if index == "histogram":
            old_mode = self._var_settings.histogram_mode
        else:
            old_mode = axis_settings[index].mode
        if old_mode == mode:
            return

        if self._current_x == index:
            self._current_x = None
        if self._current_y == index:
            self._current_y = None

        # swap x-y
        if mode == AxisMode.XAxis and old_mode == AxisMode.YAxis:
            self._update_axis_settings(self._current_x, old_mode)
            self._update_axis_settings(index, mode)
            return
        if mode == AxisMode.YAxis and old_mode == AxisMode.XAxis:
            self._update_axis_settings(self._current_y, old_mode)
            self._update_axis_settings(index, mode)
            return

        # clear histogram
        if mode == self._var_settings.histogram_mode:
            self._update_axis_settings(index, mode)
            self._update_axis_settings("histogram", None)
            return

        # change setting of old x/y axis
        old_axis = None
        if mode == AxisMode.XAxis:
            old_axis = self._current_x
        elif mode == AxisMode.YAxis:
            old_axis = self._current_y

        if old_axis is not None:
            # Note: new mode for old axis may be overriden below (see below)
            if axis_settings[old_axis].axis_type == AxisType.DimCoord:
                new_mode = AxisMode.Average
            else:
                new_mode = AxisMode.All
            self._update_axis_settings(old_axis, new_mode)

        if index != "histogram":
            if axis_settings[index].axis_type.is_dim and mode in [AxisMode.Average]:
                dim_name = axis_settings[index].name
                # Set to All. Just to be save.
                for idx, settings in enumerate(self._axis_settings):
                    if settings.axis_type == AxisType.Coord:
                        if dim_name in self._data[settings.name].dims:
                            self._update_axis_settings(idx, AxisMode.All)

            if axis_settings[index].axis_type == AxisType.Coord and mode in [AxisMode.XAxis, AxisMode.YAxis]:
                # Set all it's dims to All
                # TODO: this does not yet properly cover cases with multiple dims.
                dims = self._data[axis_settings[index].name].dims
                for idx, settings in enumerate(self._axis_settings):
                    if settings.name in dims:
                        self._update_axis_settings(idx, AxisMode.All)

        self._update_axis_settings(index, mode)

    def _update_axis_settings(self, index, mode):
        if index is None:
            return
        if index == "histogram":
            self._var_settings.histogram_mode = mode if mode in [AxisMode.XAxis, AxisMode.YAxis] else None
        else:
            self._axis_settings[index].mode = mode
        if mode == AxisMode.XAxis:
            self._current_x = index
        elif self._current_x == index:
            self._current_x = None
        if mode == AxisMode.YAxis:
            self._current_y = index
        elif self._current_y == index:
            self._current_y = None
        self._data_changed = True

    @property
    def changed(self):
        return self._data_changed or self._plot_changed or self._slice_changed

    @plot_changer
    def set_axis_log(self, index, logarithmic):
        old_setting = self._axis_settings[index].logarithmic
        if old_setting != logarithmic:
            settings = self._axis_settings[index]
            settings.logarithmic = logarithmic
            self._plot_changed = True

            if self._last_selected_data is not None and settings.name in self._last_selected_data.coords:
                self._last_selected_data[settings.name].attrs['log'] = settings.logarithmic

    @plot_changer
    def set_axis_slice(self, index, slice_index):
        old_index = self._axis_settings[index].slice_index
        if old_index != slice_index:
            self._axis_settings[index].slice_index = slice_index
            self._slice_changed = True

    @plot_changer
    def set_axis_fft(self, index, fft_on):
        old_setting = self._axis_settings[index].fft
        if old_setting != fft_on:
            self._axis_settings[index].fft = fft_on
            self._data_changed = True

    @property
    def histogram_mode(self):
        return self._var_settings.histogram_mode

    @plot_changer
    def set_complex_mode(self, mode: ComplexMode):
        if self._var_settings.complex_mode != mode:
            self._var_settings.complex_mode = mode
            self._data_changed = True  # TODO only if FFT or histogram

    @property
    def complex_mode(self):
        return self._var_settings.complex_mode

    @plot_changer
    def set_logarithmic(self, logarithmic):
        if self._var_settings.logarithmic != logarithmic:
            self._var_settings.logarithmic = logarithmic
            self._plot_changed = True
            if self._last_selected_data is not None:
                self._last_selected_data.attrs['log'] = logarithmic

    @property
    def logarithmic(self):
        return self._var_settings.logarithmic

    @plot_changer
    def set_multiline_plot(self, multiline_plot):
        if self._var_settings.multiline_plot != multiline_plot:
            self._var_settings.multiline_plot = multiline_plot
            self._plot_changed = True

    @property
    def multiline_plot(self):
        return self._var_settings.multiline_plot

    @plot_changer
    def set_value_range(self, value_range: tuple[float, float] | None):
        if self._var_settings.manual_value_range != value_range:
            if value_range is not None and not isinstance(value_range, tuple):
                raise ValueError(f"Invalid range {value_range}. Expected None or tuple")
            self._var_settings.manual_value_range = value_range
            self._plot_changed = True

    @property
    def value_range(self):
        return self._var_settings.value_range

    @plot_changer
    def set_show_sidebar(self, state):
        if self._var_settings.show_sidebar != state:
            self._var_settings.show_sidebar = state
            self._plot_changed = True

    @property
    def show_sidebar(self):
        return self._var_settings.show_sidebar

    def update(self):
        if self.changed and self._plotter: # TODO plotting changed, data changed, slice changed.
            self._plot_changed = False
            # plotter calls get_data().
            self._plotter.update()

    def get_data(self):
        if not self._data_changed and not self._slice_changed:
            return self._last_selected_data

        logger.debug(f"get_data {self.var_name}")
        start = time.perf_counter()
        var_settings = self._var_settings

        if self._data_changed:
            self._info_message = None

            histogram_mode = var_settings.histogram_mode
            da = self._data

            dims = list(da.dims)
            for settings in reversed(self._axis_settings):
                if settings.mode == AxisMode.Average:
                    if not settings.axis_type.is_dim:
                        raise Exception(f"Cannot average {settings}")
                    dim_name = settings.name
                    if histogram_mode is None:
                        da = da.mean(dim_name)
                    dims.remove(dim_name)
                if settings.mode == AxisMode.All and settings.axis_type.is_dim:
                    dims.remove(settings.name)

            # Copy attributes. They get lost during averaging.
            for name in ['units', 'long_name']:
                try:
                    da.attrs[name] = self._data.attrs[name]
                except KeyError:
                    pass

            # Note: order of Average and FFT matter, because of np.abs() of FFT.
            # FFT after averaging
            for settings in reversed(self._axis_settings):
                if settings.fft and settings.mode in [AxisMode.XAxis, AxisMode.YAxis]:
                    if settings.axis_type != AxisType.DimCoord:
                        raise Exception(f"Cannot apply FFT on {settings}")
                    if np.iscomplexobj(da):
                        da = self._select_complex_component(da, "FFT")
                    dim_name = settings.name
                    da = apply_fft(da, dim_name)
                    da[settings.name].attrs['log'] = settings.logarithmic

            self._value_range = (float(da.min().real), float(da.max().real))
            if np.iscomplexobj(da):
                imag = da.imag
                amplitude = np.abs(da)
                self._imag_range = (float(imag.min()), float(imag.max()))
                self._ampl_range = (float(amplitude.min()), float(amplitude.max()))

            if histogram_mode is not None:
                logger.debug("start histogram")
                if np.iscomplexobj(da):
                    da = self._select_complex_component(da, "histogram")
                da = histogram(da, dims + ['histogram'], 50, self._value_range)  # TODO bins, range
                da['histogram'].attrs['log'] = False
                self._value_range = (float(da.min()), float(da.max()))
                logger.debug("done histogram")

            self._pre_slice_data = da
        else:
            da = self._pre_slice_data

        has_slice = False
        for settings in self._axis_settings:
            if settings.mode == AxisMode.Slice:
                if not settings.axis_type.is_dim:
                    raise Exception("Cannot slice {settings}")
                has_slice = True
                dim_name = settings.name
                da = da[{dim_name: settings.slice_index}]
                if settings.axis_type == AxisType.DimCoord:
                    da = da.drop(dim_name)

        var_settings.slice_value_range = self._value_range if has_slice else None
        if np.iscomplexobj(da):
            var_settings.slice_imag_range = self._imag_range if has_slice else None
            var_settings.slice_ampl_range = self._ampl_range if has_slice else None

        for settings in self._axis_settings:
            if settings.name in da.coords:
                da[settings.name].attrs['log'] = settings.logarithmic
        da.attrs['log'] = var_settings.logarithmic

        plot_axes = self.plot_axes
        if self.gridded:
            # all axes are dims!
            dims = [da[dim].name for dim in plot_axes]
            da = da.transpose(*dims)
        else:
            # set simple coordinates for remaining dims.
            for dim in da.dims:
                if dim not in da.coords and dim in plot_axes:
                    da[dim] = settings.data
            # not gridded: flatten all.
            da = da.stack({"_": [...]}, create_index=False)

        self._last_selected_data = da
        self._slice_changed = False
        self._data_changed = False
        duration = time.perf_counter() - start
        logger.info(f"Updated {self.var_name} {duration*1000:.1f} ms")
        return da

    def _select_complex_component(self, da: xr.DataArray, transformation: str) -> xr.DataArray:
        mode = self._var_settings.complex_mode
        if mode in [ComplexMode.ReIm, ComplexMode.Nyquist, ComplexMode.NyquistPolar]:
            self._info_message = f"Only real component used for {transformation}"
            return da.real
        if mode == ComplexMode.AmplitudePhase:
            self._info_message = f"Only amplitude used for {transformation}"
            return np.abs(da)
        if mode == ComplexMode.Re:
            return da.real
        if mode == ComplexMode.Im:
            return da.imag
        if mode == ComplexMode.Amplitude:
            return np.abs(da)
        if mode == ComplexMode.Phase:
            return get_phase(da)


def get_phase(da: xr.DataArray) -> xr.DataArray:
    # np.angle does not return an xarray DataArray
    da2 = xr.DataArray(
        data=np.angle(da),
        coords=da.coords,
        attrs=da.attrs.copy(),
        )
    da2.attrs["units"] = "rad"
    return da2


def equivalent_names(names1: list[str], names2: list[str]):
    """
    Names are equivalent if the are equal up to an optional extension, where
    the extension is "-{number}".

    Note: This might be specific for core-tools (exported) data.
    """
    pattern = re.compile(r"(.*?)(-\d)?")
    for name1, name2 in zip(names1, names2):
        if name1 == name2:
            continue

        m1 = pattern.fullmatch(name1)
        m2 = pattern.fullmatch(name2)
        if m1.group(1) != m2.group(1):
            return False

    return True
