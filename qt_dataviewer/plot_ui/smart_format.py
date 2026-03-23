import logging
from numbers import Number

import numpy as np
import xarray as xr

from pyqtgraph.functions import siScale
from pyqtgraph.graphicsItems import AxisItem


logger = logging.getLogger(__name__)

_si_prefixes = {
    "T": 1e12,
    "G": 1e9,
    "M": 1e6,
    "k": 1e3,
    "": 1.0,
    "m": 1e-3,
    "u": 1e-6,
    "\u03BC": 1e-6,  # mu
    "n": 1e-9,
    "p": 1e-12,
    "f": 1e-15,
    }
_si_units = ["s", "Hz", "A", "V", "Ohm", "\u03A9", "H", "T"]
_auto_si_units = {
    prefix+unit: (unit, scale)
    for prefix, scale in _si_prefixes.items()
    for unit in _si_units
    }


def get_unit_and_scale(units: str) -> tuple[str, float]:
    try:
        return _auto_si_units[units]
    except KeyError:
        return units, 1.0


def format_with_units(value: float | None, units: str, precision: int):
    if value is None:
        return "None"
    if not isinstance(value, float):
        value = float(value)
    try:
        units, scale = _auto_si_units[units]
        auto_si_prefix = True
    except KeyError:
        auto_si_prefix = False
    except Exception:
        logger.info(f"Error formatting with units: '{units}', value: {value}", exc_info=True)
        auto_si_prefix = False
    if units in [None, '', '#']:
        return f"{value:#.{precision}g}"
    if auto_si_prefix:
        value *= scale
        prefixscale, prefix = siScale(value)
        value *= prefixscale
        units = prefix+units
    return f"{value:#.{precision}g} {units}"


class SmartFormatter:
    def __init__(self, da: xr.DataArray):
        attrs = da.attrs
        self._label = attrs.get('long_name', da.name)
        units = attrs.get("units", "")
        if units == "no_label":
            units = ""

        if attrs.get("scale") == "labels":
            self._prefixscale = None
            self._auto_si_prefix = False
            self._units = units
        else:
            try:
                self._units, self._prefixscale = _auto_si_units[units]
                self._auto_si_prefix = True
            except KeyError:
                self._prefixscale = 1.0
                self._auto_si_prefix = False
                self._units = units

    def _get_precision(self, data: xr.DataArray):
        if data.ndim == 0:
            return 4
        n = len(data)
        if n < 2:
            d = 4
        else:
            try:
                dmin, dmax = float(data.min()), float(data.max())
                f = (dmax - dmin) / abs(dmax + dmin) * 2
                if np.isnan(f) or f/n > 0.0001 or f == 0.0:
                    d = 4
                else:
                    d = 1-int(np.log10(f/n))
            except Exception:
                d = 4
        return d

    def without_unit_prefix(self, value: Number | str) -> Number | str:
        if self._prefixscale is None:
            # labels
            return value
        return value * self._prefixscale

    def with_units(self, value: Number | str, data: xr.DataArray): # @@@ handle complex data?
        """Return value formatted with units.

        Args:
            value: value to format in units without SI-prefix
            data: collections of values to determine range (in units without SI-prefix)
        """
        if isinstance(value, str):
            # labels
            return value

        if self._units == "|..>":
            # qubit register
            value = int(value+0.5)
            n_qubits = self._get_n_qubits(data)
            return f"|{value:0{n_qubits}b}>"

        if not isinstance(value, float):
            value = float(value)
        # Note: the data can change.
        d = self._get_precision(data)
        units = self._units
        if units in [None, '', '#']:
            return f"{value:#.{d}g}"
        if self._auto_si_prefix:
            prefixscale, prefix = siScale(value)
            value *= prefixscale
            units = prefix+units
        return f"{value:#.{d}g} {units}"

    def set_plot_axis(self, axis: AxisItem):
        if self._auto_si_prefix != axis.autoSIPrefix:
            axis.enableAutoSIPrefix(self._auto_si_prefix)
            if not self._auto_si_prefix:
                # workaround for bug in pyqtgraph
                axis.autoSIPrefixScale = 1.0
        axis.setLabel(self._label, self._units)

    def set_labels(self, axis: AxisItem, data: xr.DataArray):
        if self._units == "|..>":
            labels = self._get_qubit_labels(data)
        else:
            labels = list(data)
        ticks = [
            [(i, label) for i, label in enumerate(labels)],
            [],
            ]
        axis.setTicks(ticks)

    def _get_qubit_labels(self, data: xr.DataArray):
        n_qubits = self._get_n_qubits(data)
        labels = []
        for s in range(0, int(np.max(data)+1.5)):
            labels.append(f"{s:0{n_qubits}b}")
        return labels

    def _get_n_qubits(self, data: xr.DataArray):
        return int(np.ceil(np.log2(data.max()+1)))
