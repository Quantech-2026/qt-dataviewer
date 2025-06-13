from datetime import datetime
import xarray as xr


def convert_quantify(ds: xr.Dataset):
    ds = _qf_to_nD(ds)
    tuid = ds.attrs["tuid"]
    try:
        start_time = datetime.strptime(tuid[:18], "%Y%m%d-%H%M%S-%f")
        ds.attrs["measurement_time"] = start_time.isoformat()
    except Exception:
        pass
    if "application" not in ds.attrs:
        ds.attrs["application"] = "Quantify"
    return ds


def _qf_to_nD(ds):
    # print(ds.attrs['name'], flush=True)
    # print(ds.attrs)
    if ds.attrs.get("2D-grid") or ds.attrs.get("grid_2d_uniformly_spaced"):
        ds = ds.set_index(dim_0=["x0", "x1"]).unstack("dim_0")
    elif ds.attrs.get("1d_2_settables_uniformly_spaced"):
        # print(ds.coords)
        # print(ds.variables)
        # Set x0 as x-axis.
        # TODO set and handle other x-axis. NOTE: It could be more than 2...
        ds = ds.swap_dims({"dim_0": "x0"})
    elif len(ds.coords) == 1:
        for i, dim in enumerate(ds.dims):
            ds = ds.swap_dims({dim: f"x{i}"})
    return ds
