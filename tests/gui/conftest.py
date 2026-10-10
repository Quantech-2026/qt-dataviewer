"""
GUI tests: drive the viewer and the browsers like a user, with any qtpy
binding (QT_API).

Run from the repository root, e.g.:

    QT_API=pyside6 QT_QPA_PLATFORM=offscreen pytest tests/gui

Needs pytest, pytest-qt, qcodes, scipy (NetCDF3 files in test_data) and
requests (sqdl import).

Every test fails on
- an exception in a Qt slot or virtual method (pytest-qt),
- an ERROR log record (qt_log_exception logs before re-raising, and many
  places only log),
- a message box (recorded instead of blocking).
Context menus return "no action" instead of blocking.
"""
import json
import logging
import os
from datetime import datetime, timedelta

import numpy as np
import pytest
import xarray as xr

TEST_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_data")


def pytest_report_header(config):
    import qtpy
    return f"qtpy binding: {qtpy.API_NAME} {qtpy.QT_VERSION}"


def _by_design(record):
    """Unplottable data types: the plot model logs and shows them as 'Error: ...'."""
    if record.getMessage() == "Exception creating plot model" and record.exc_info:
        text = str(record.exc_info[1])
        return text.startswith(("Unknown dtype", "Cannot plot data of type"))
    return False


@pytest.fixture(autouse=True)
def traps(monkeypatch, caplog):
    from qtpy import QtWidgets

    class Boxes(list):
        expected = 0

    boxes = Boxes()

    def box_exec(self, *args):
        boxes.append((self.windowTitle(), self.text()))
        return 0

    for name in ("exec", "exec_"):
        monkeypatch.setattr(QtWidgets.QMessageBox, name, box_exec, raising=False)
        monkeypatch.setattr(QtWidgets.QMenu, name, lambda self, *a: None, raising=False)
    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: ("", "")))
    monkeypatch.setattr(QtWidgets.QFileDialog, "getExistingDirectory",
                        staticmethod(lambda *a, **k: ""))
    caplog.set_level(logging.WARNING)
    yield boxes
    records = caplog.get_records("setup") + caplog.get_records("call") + caplog.get_records("teardown")
    errors = [r for r in records if r.levelno >= logging.ERROR and not _by_design(r)]
    assert len(boxes) == boxes.expected, f"message boxes: {boxes}"
    assert not errors, "\n\n".join(
        f"{r.name}: {r.getMessage()}\n{caplog.handler.format(r) if r.exc_info else ''}"
        for r in errors)


@pytest.fixture(autouse=True)
def close_windows(qapp):
    yield
    from qtpy import QtWidgets
    for w in QtWidgets.QApplication.topLevelWidgets():
        if w.isVisible():
            w.close()
    for _ in range(3):
        qapp.processEvents()


# ---------------------------------------------------------------- synthetic data

def _snapshot(pulses=False):
    snap = {
        "station": {
            "instruments": {
                "dac": {"parameters": {f"ch{i}": {"value": 0.1 * i, "unit": "V"} for i in range(4)},
                        "functions": {}, "submodules": {}, "__class__": "Dac"},
                "lockin": {"parameters": {"freq": {"value": 1e3, "unit": "Hz"},
                                          "list_param": {"value": [1, 2, 3]},
                                          "none_param": {"value": None}}},
            },
        },
    }
    if pulses:
        snap["measurement"] = {"sequence": {
            "pc0": {
                "_total_time": 1000.0,
                "P1_baseband": {
                    "p0": {"start": 0.0, "stop": 400.0, "v_start": 10.0, "v_stop": 10.0},
                    "p1": {"start": 400.0, "stop": 800.0, "v_start": -5.0, "v_stop": 5.0},
                },
                "P2_baseband": {
                    "p0": {"start": 100.0, "stop": 900.0, "v_start": 3.0, "v_stop": 3.0},
                },
                "P1_pulses": {
                    "p0": {"start": 450.0, "stop": 550.0, "amplitude": 2.0,
                           "frequency": 2.0e7, "start_phase": 0.0},
                },
                "q1_pulses": {
                    "p0": {"start": 200.0, "stop": 300.0, "amplitude": 50.0,
                           "frequency": 1.0e8, "start_phase": 0.0, "AM_envelope": "flattop",
                           "PM_envelope": None},
                },
            },
            "pc1": {
                "_total_time": 500.0,
                "P1_baseband": {
                    "p0": {"start": 0.0, "stop": 500.0, "v_start": 2.0, "v_stop": 2.0},
                },
            },
            "LOs": {"q1": 5.0e9},
        }}
    return json.dumps(snap)


def synthetic_datasets():
    """name -> xr.Dataset, covering the shapes and dtypes the plot model handles."""
    rng = np.random.default_rng(1)
    x = xr.DataArray(np.linspace(-1, 1, 41), dims="x", attrs={"units": "V", "long_name": "Gate X"})
    y = xr.DataArray(np.linspace(0, 2e-3, 31), dims="y", attrs={"units": "A", "long_name": "Bias"})
    z = xr.DataArray(np.arange(5) * 1.0e9, dims="z", attrs={"units": "Hz"})
    f = xr.DataArray(np.logspace(3, 9, 50), dims="f", attrs={"units": "Hz"})
    t = xr.DataArray(np.linspace(0, 1e-6, 128), dims="t", attrs={"units": "s"})
    X, Y = np.meshgrid(x, y, indexing="ij")
    ds = {}

    ds["scalar"] = xr.Dataset(
        {"v": ((), 1.234, {"units": "V"}), "count": ((), 7)},
    )
    ds["1d"] = xr.Dataset(
        {"signal": ("x", np.sin(3 * x.values), {"units": "V", "long_name": "Signal"}),
         "noise": ("x", rng.normal(size=41) * 1e-6, {"units": "A"})},
        coords={"x": x})
    ds["1d_nan_partial"] = xr.Dataset(
        {"signal": ("x", np.where(np.arange(41) < 20, np.cos(x.values), np.nan), {"units": "V"})},
        coords={"x": x})
    ds["1d_all_nan"] = xr.Dataset(
        {"signal": ("x", np.full(41, np.nan), {"units": "V"})},
        coords={"x": x})
    ds["1d_log_axis"] = xr.Dataset(
        {"response": ("f", 1 / (1 + (f.values / 1e6) ** 2), {"units": "V"})},
        coords={"f": f})
    ds["1d_time_fft"] = xr.Dataset(
        {"trace": ("t", np.sin(2 * np.pi * 20e6 * t.values) + 0.1 * rng.normal(size=128), {"units": "mV"})},
        coords={"t": t})
    ds["1d_no_coords"] = xr.Dataset(
        {"raw": ("n", rng.normal(size=100))})
    ds["1d_int"] = xr.Dataset(
        {"counts": ("x", rng.integers(0, 100, 41))},
        coords={"x": x})
    ds["1d_bool"] = xr.Dataset(
        {"flag": ("x", rng.integers(0, 2, 41).astype(bool))},
        coords={"x": x})
    ds["1d_complex"] = xr.Dataset(
        {"s21": ("f", np.exp(1j * f.values / 1e8) / (1 + 1j * f.values / 1e6), {"units": "V"})},
        coords={"f": f})
    ds["2d"] = xr.Dataset(
        {"current": (("x", "y"), np.sin(4 * X) * np.cos(2000 * Y), {"units": "A"}),
         "phase": (("x", "y"), np.arctan2(X, Y + 1e-4), {"units": "rad"})},
        coords={"x": x, "y": y})
    ds["2d_complex"] = xr.Dataset(
        {"iq": (("x", "y"), np.exp(1j * 5 * X) * (1 + Y * 100), {"units": "V"})},
        coords={"x": x, "y": y})
    ds["2d_nan_partial"] = xr.Dataset(
        {"current": (("x", "y"), np.where(X < 0.2, np.sin(4 * X) + Y, np.nan), {"units": "A"})},
        coords={"x": x, "y": y})
    ds["2d_single_row"] = xr.Dataset(
        {"current": (("x", "y"), np.ones((1, 31)), {"units": "A"})},
        coords={"x": x[:1], "y": y})
    ds["2d_nonuniform"] = xr.Dataset(
        {"g": (("x", "f"), np.outer(np.cos(x.values), np.log10(f.values)))},
        coords={"x": x, "f": f})
    ds["3d"] = xr.Dataset(
        {"cube": (("z", "x", "y"), rng.normal(size=(5, 41, 31)), {"units": "V"}),
         "line": ("z", np.arange(5.0), {"units": "V"})},
        coords={"z": z, "x": x, "y": y})
    ds["4d"] = xr.Dataset(
        {"hyper": (("z", "x", "y", "n"), rng.normal(size=(5, 41, 31, 3)))},
        coords={"z": z, "x": x, "y": y})
    # coordinates that are not dimensions: scatter / non-gridded data
    n = 200
    ds["scatter"] = xr.Dataset(
        {"value": ("i", rng.normal(size=n), {"units": "V"})},
        coords={"px": ("i", rng.uniform(-1, 1, n), {"units": "V"}),
                "py": ("i", rng.uniform(0, 5, n), {"units": "mV"})})
    ds["2d_coord_on_grid"] = xr.Dataset(
        {"current": (("x", "y"), np.sin(4 * X) + Y)},
        coords={"x": x, "y": y, "x_alt": ("x", x.values * 2, {"units": "V"}),
                "xy": (("x", "y"), X + Y)})
    ds["multi_var_many"] = xr.Dataset(
        {f"var{i}": ("x", np.sin(x.values * i), {"units": "V"}) for i in range(9)},
        coords={"x": x})
    ds["mixed_dims"] = xr.Dataset(
        {"a": ("x", np.cos(x.values)), "b": (("x", "y"), X * Y), "c": ((), 3.0),
         "d": ("t", np.sin(t.values * 1e7))},
        coords={"x": x, "y": y, "t": t})
    ds["empty"] = xr.Dataset()
    ds["long_name_" + "x" * 120] = xr.Dataset({"v": ("x", x.values)}, coords={"x": x})
    ds["negative_for_log"] = xr.Dataset(
        {"v": ("x", x.values, {"units": "V"})}, coords={"x": x})
    ds["constant"] = xr.Dataset(
        {"v": ("x", np.zeros(41)), "m": (("x", "y"), np.zeros((41, 31)))},
        coords={"x": x, "y": y})
    ds["single_point"] = xr.Dataset(
        {"v": ("x", [1.0])}, coords={"x": [0.5]})
    ds["datetime_axis"] = xr.Dataset(
        {"temp": ("time", 20 + rng.normal(size=24))},
        coords={"time": [datetime(2026, 1, 1) + timedelta(hours=h) for h in range(24)]})
    ds["reversed_axis"] = xr.Dataset(
        {"v": (("x", "y"), X + Y)},
        coords={"x": x.values[::-1], "y": y})
    for name, d in ds.items():
        d.attrs.update(title=name, uuid=f"syn-{name[:20]}",
                       snapshot=_snapshot(pulses=name in ("2d", "1d")))
    return ds


def make_xarray_dataset(name, ds_xr, when=None):
    from qt_dataviewer.dataset_files.generic_xarray import XarrayDataset, XarrayDatasetDescription
    dd = XarrayDatasetDescription(uid=ds_xr.attrs.get("uuid", name), name=name,
                                  collected_datetime=when or datetime(2026, 10, 1, 12, 0),
                                  ds_xr=ds_xr)
    return XarrayDataset(dd, ds_xr)


@pytest.fixture(scope="session")
def synthetic():
    return synthetic_datasets()


@pytest.fixture(scope="session")
def synthetic_dir(tmp_path_factory, synthetic):
    """The synthetic datasets as netCDF files: a flat folder and nested folders."""
    root = tmp_path_factory.mktemp("files")
    flat = root / "flat"
    nested = root / "nested" / "2026-10" / "day1"
    flat.mkdir()
    nested.mkdir(parents=True)
    for i, (name, d) in enumerate(synthetic.items()):
        if name == "datetime_axis" or name.startswith("long_name"):
            continue
        target = flat if i % 2 else nested
        d2 = d.copy()
        for v in list(d2.data_vars):
            if np.iscomplexobj(d2[v]):
                d2[v].encoding = {}
        d2.to_netcdf(target / f"{name}.nc", engine="h5netcdf", invalid_netcdf=True)
    return root
