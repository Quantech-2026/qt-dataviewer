from typing import Optional, Tuple, List

import numpy as np
import xarray as xr

def histogram(da: xr.DataArray,
              dims: List[str],
              nbins: int,
              bin_range: Optional[Tuple[float, float]] = None) -> xr.DataArray:

    if bin_range is None:
        bin_range = (float(da.min()), float(da.max()))
    binedges  = np.linspace(bin_range[0], bin_range[1], nbins+1)
    bincenters = (binedges[1:] + binedges[:-1])/2

    # create new result array
    res = xr.Dataset()
    res.coords['histogram'] = bincenters
    res.coords['histogram'].attrs = {
            'units': da.attrs['units'],
            'long_name': da.attrs['long_name'],
            'scale': 'lin',
            }
    shape = []
    loop_dims = []
    for dim in dims:
        if dim != 'histogram':
            res.coords[dim] = da.coords[dim]
            shape.append(len(da.coords[dim]))
            loop_dims.append(dim)
    shape.append(nbins)
    data = np.zeros(tuple(shape))

    _loop(da, data, loop_dims, binedges)

    hist_name = da.name+'_hist'
    attrs = {
            'units': '',
            'long_name': 'rel. frequency',
            }
    dims = loop_dims + ['histogram']
    res[hist_name] = (dims, data)
    res[hist_name].attrs = attrs
    return res[hist_name]

def _loop(da, data, dims, binedges):
    if len(dims):
        dim = dims[0]
        for i in range(data.shape[0]):
            _loop(da[{dim:i}], data[i], dims[1:], binedges)
    else:
        data[:] = np.histogram(da.data, binedges)[0]/data.shape[0]

        # TODO: check for NaN?
        # A[~np.isnan(A)]
        # np.count_nonzero(np.isnan(data))

