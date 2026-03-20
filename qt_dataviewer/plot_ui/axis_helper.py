import numpy as np
import xarray as xr
from numpy.typing import NDArray
from pyqtgraph.graphicsItems import AxisItem

from .smart_format import SmartFormatter


class AxisHelper:
    def __init__(self, x_array: xr.DataArray, scale: str):
        self._x_array = x_array
        self._scale = scale

        formatter = SmartFormatter(x_array)
        self._formatter = formatter
        self.x = formatter.without_unit_prefix(x_array.data)

    def set_plot_axis(self, axis: AxisItem):
        self._formatter.set_plot_axis(axis)

        if self._scale in ["labels", "qubit-register"]:
            self._formatter.set_labels(axis, self._x_array)

    def get_axis_range(self) -> tuple[float, float, bool]:
        """
        Returns:
            min, size, flip
        """
        x = self.x
        if self._scale in ["labels", "qubit-register"]:
            return -0.5, len(x), False

        if self._scale == 'log':
            x = np.log10(x)
        ix_valid = np.nonzero(np.isfinite(x))[0]
        if len(ix_valid) == 0:
            return None, None, False
        x_valid = x[ix_valid]

        ix_min, ix_max = ix_valid[0], ix_valid[-1]
        x_first, x_last = x_valid[0], x_valid[-1]

        x_offset = np.min(x_valid)
        with np.errstate(divide='ignore', invalid='ignore'):
            x_scale = (x_last - x_first)/(ix_max - ix_min)

        if x_scale == 0 or np.isnan(x_scale):
            x_scale = 1
        else:
            x_offset -= 0.5*x_scale

        # flip axis if scan from postive to negative value
        if x_scale < 0:
            flip = True
            x_scale *= -1
            x_offset -= (len(x)-ix_max-1)*x_scale
        else:
            flip = False
            x_offset -= ix_min*x_scale

        return x_offset, x_scale*len(x), flip

    def get_edges(self, is_log: bool) -> tuple[NDArray, NDArray] | tuple[None, None]:
        x = self.x
        if is_log:
            ix_valid = np.nonzero((x > 0) & np.isfinite(x))[0]
            with np.errstate(divide='ignore', invalid='ignore'):
                x = np.log10(x)
        else:
            ix_valid = np.nonzero(np.isfinite(x))[0]
        n_valid = len(ix_valid)
        if n_valid == 0:
            return None, None
        x_slice = slice(min(ix_valid), max(ix_valid)+1)
        xv = x[x_slice]

        if n_valid == 1:
            edges = np.array([xv[0]-0.5, xv[0]+0.5])
        else:
            nx = len(xv)+1
            edges = np.zeros(nx)
            edges[1:-1] = (xv[1:] + xv[:-1])/2
            edges[0] = 1.5*xv[0] - 0.5*xv[1]
            edges[-1] = 1.5*xv[-1] - 0.5*xv[-2]

        return edges, x_slice
