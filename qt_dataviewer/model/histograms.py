import numpy as np
import xarray as xr


def histogram(da: xr.DataArray,
              dims: list[str],
              nbins: int,
              bin_range: tuple[float, float] | None = None) -> xr.DataArray:

    if bin_range is None:
        mn = float(da.min())
        mx = float(da.max())
    else:
        mn, mx = bin_range
    if not (np.isfinite(mn) and np.isfinite(mx)):
        # no data (yet)
        mn, mx = 0.0, 0.0
    if mx == mn:
        # all values are equal
        half_width = abs(mn) * 0.1 if mn != 0 else 0.5
        mn, mx = mn - half_width, mx + half_width
    step = (mx-mn)/nbins
    bin_range = (mn-step/2, mx+step/2)
    binedges = np.linspace(bin_range[0], bin_range[1], nbins+1)
    bincenters = (binedges[1:] + binedges[:-1])/2

    if dims[-1] != 'histogram':
        raise Exception(f"Oops! Unexpected dims: {dims}")

    # create new result array
    res = xr.Dataset()
    res.coords['histogram'] = bincenters
    res.coords['histogram'].attrs = {
            'units': da.attrs.get('units'),
            'long_name': da.attrs.get('long_name'),
            'scale': 'lin',
            }

    agg_dims = list(da.dims)
    total_points = np.prod(da.shape)
    shape = []
    loop_dims = []
    for dim in dims:
        if dim != 'histogram':
            res.coords[dim] = da.coords[dim]
            shape.append(len(da.coords[dim]))
            loop_dims.append(dim)
            agg_dims.remove(dim)
    points_histogram = total_points / np.prod(shape)

    res_dims = loop_dims + ['histogram']
    if res_dims != dims:
        raise Exception(f"Oops: {res_dims} <> dims")

    if not loop_dims:
        # np.histogram is fastest
        data = np.histogram(da.values, binedges)[0]/points_histogram
    else:
        # calculating histogram with basic np functions is faster than looping over np.histogram
        da = da.transpose(*loop_dims, *agg_dims)
        res_dims = ['histogram'] + loop_dims
        shape = [nbins]+shape
        data = np.zeros(tuple(shape))
        d = (da.values - bin_range[0]) * (nbins / (bin_range[1]-bin_range[0]))
        d = np.floor(d)
        d = d.reshape(tuple(shape[1:]+[-1]))
        for i in range(nbins):
            data[i] = np.sum(d == i, axis=-1)
        data /= points_histogram

    hist_name = da.name+'_hist'
    attrs = {
            'units': '',
            'long_name': 'rel. frequency',
            }
    res[hist_name] = (res_dims, data)
    res[hist_name].attrs = attrs

    return res[hist_name]
