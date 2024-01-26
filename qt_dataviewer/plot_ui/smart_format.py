import numpy as np
import xarray as xr

from pyqtgraph.functions import siScale

_si_prefixes = {
    "T": 1e12,
    "G": 1e9,
    "M": 1e6,
    "k": 1e3,
    "" : 1,
    "m": 1e-3,
    "u": 1e-6,
    "\u03BC": 1e-6,  # mu
    "n": 1e-9,
    "p": 1e-12,
    "f": 1e-15,
    }
_si_units = ["s", "Hz", "A", "V", "Ohm", "\u03A9", "H", "T"]
_auto_si_units = {
    prefix+unit: scale
    for prefix, scale in _si_prefixes.items()
    for unit in _si_units
    }


class SmartFormatter:
    def __init__(self, units):
        try:
            self.scale = _auto_si_units[units]
            self.auto_si_prefix = True
            if self.scale != 1.0:
                self.units = units[1:]
            else:
                self.units = units
        except KeyError:
            self.scale = 1.0
            self.auto_si_prefix = False
            self.units = units

    def get_precision(self, data: xr.DataArray):
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

    def with_units(self, value: float, data: xr.DataArray):
        # Note: the data can change.
        d = self.get_precision(data)
        units = self.units
        if units in [None, '', '#']:
            return f"{value:#.{d}g}"
        if self.auto_si_prefix:
            prefixscale, prefix = siScale(value)
            value = value * prefixscale
            units = prefix+units
        return f"{value:#.{d}g} {units}"

