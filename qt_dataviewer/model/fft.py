import logging
import numpy as np
import xarray as xr
from numpy.fft import rfft, rfftfreq

from qt_dataviewer.plot_ui.smart_format import get_unit_and_scale


logger = logging.getLogger(__name__)


def apply_fft(da: xr.DataArray, dim_name: str):
    axis = da.coords[dim_name]
    if axis.attrs['scale'] != 'lin':
        logger.error(f"{dim_name} is not linear. FFT can only be applied to linear range")
    index = list(da.dims).index(dim_name)
    r = rfft(da, axis=index, norm="forward")
    # remove DC component
    r[0] = 0.0
    r = np.abs(r)
    # Compensate splitting in positive and negative frequencies.
    r[1:-1] *= 2.0

    t_data = axis.values
    freq = rfftfreq(len(t_data), np.abs(t_data[1] - t_data[0]))
    units, scale = get_unit_and_scale(axis.attrs['units'])
    if units == 's':
        new_units = 'Hz'
    else:
        new_units = f"1/({units})"
    freq /= scale

    new_axis = xr.DataArray(
        freq,
        dims=(dim_name,),
        name=dim_name,
        attrs={
            'units': new_units,
            'long_name': 'Frequency',
            'scale': 'lin',
            }
        )

    coords = []
    for name in da.dims:
        if name != dim_name:
            coords.append(da.coords[name])
        else:
            coords.append(new_axis)

    attrs = {}
    for name in ["units", "long_name"]:
        if name in da.attrs:
            attrs[name] = da.attrs[name]

    da2 = xr.DataArray(
        name=da.name,
        data=r,
        coords=coords,
        attrs=attrs,
        )
    da2 = da2.isel({dim_name: slice(1, None)})
    return da2
