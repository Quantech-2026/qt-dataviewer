import pytest

from conftest import make_xarray_dataset, synthetic_datasets
from exercise import exercise_viewer, settle

NAMES = list(synthetic_datasets())


@pytest.mark.parametrize("name", NAMES, ids=[n[:30] for n in NAMES])
def test_viewer_synthetic(qtbot, synthetic, name):
    from qt_dataviewer import DatasetViewer

    viewer = DatasetViewer(make_xarray_dataset(name, synthetic[name]))
    exercise_viewer(viewer, qtbot)
    viewer.close()
    settle(qtbot)
    assert not viewer.alive


def test_viewer_dark_style(qtbot, synthetic):
    from qt_dataviewer import DatasetViewer
    from qt_dataviewer.utils.qt_utils import qt_set_darkstyle
    from qtpy import QtWidgets

    qt_set_darkstyle()
    try:
        viewer = DatasetViewer(make_xarray_dataset("2d", synthetic["2d"]))
        exercise_viewer(viewer, qtbot, settings=False)
        viewer.close()
    finally:
        QtWidgets.QApplication.instance().setStyleSheet("")
        import pyqtgraph as pg
        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")


def test_viewer_live_dataset(qtbot, synthetic):
    """An incomplete dataset is reloaded on a timer until it is complete."""
    import xarray as xr
    from qt_dataviewer import DatasetViewer
    from qt_dataviewer.dataset_files.generic_xarray import XarrayDataset, XarrayDatasetDescription

    full = synthetic["2d"]

    class Live(XarrayDataset):
        def __init__(self):
            self.rows = 0
            super().__init__(XarrayDatasetDescription("live", "live", __import__("datetime").datetime.now()),
                             xr.Dataset())

        @property
        def is_complete(self):
            return self.rows >= 5

        @property
        def is_modified(self):
            return True

        def reload(self):
            self.rows += 1
            part = full.isel(x=slice(0, self.rows * 8)).copy()
            self.ds_xr = part

    ds = Live()
    viewer = DatasetViewer(ds)
    qtbot.waitUntil(lambda: ds.is_complete, timeout=10000)
    settle(qtbot, 700)
    assert viewer.lb_variables.count() == 2
    viewer.close()


def test_viewer_previous_next_latest(qtbot, synthetic):
    """Datalist navigation, including Latest polling."""
    from qt_dataviewer import DatasetViewer
    from qt_dataviewer.abstract import DatasetList

    names = ["1d", "2d", "3d", "scalar", "1d_complex", "empty", "scatter"]
    items = [make_xarray_dataset(n, synthetic[n]) for n in names]

    class Items(DatasetList):
        def __init__(self):
            self.i = 0

        def has_next(self):
            return self.i + 1 < len(items)

        def get_next(self):
            self.i += 1
            return items[self.i]

        def has_previous(self):
            return self.i > 0

        def get_previous(self):
            self.i -= 1
            return items[self.i]

        def is_latest(self):
            return self.i == len(items) - 1

        def get_latest(self):
            self.i = len(items) - 1
            return items[self.i]

    datalist = Items()
    viewer = DatasetViewer(items[0], datalist=datalist)
    qtbot.waitExposed(viewer)
    for _ in range(len(items) + 1):
        viewer.btnNext.click()
        settle(qtbot, 50)
    assert datalist.i == len(items) - 1
    for _ in range(len(items) + 1):
        viewer.btnPrevious.click()
        settle(qtbot, 50)
    assert datalist.i == 0
    from qtpy import QtCore
    qtbot.keyClick(viewer, QtCore.Qt.Key_Right, QtCore.Qt.ControlModifier)
    settle(qtbot, 50)
    assert datalist.i == 1
    qtbot.keyClick(viewer, QtCore.Qt.Key_Left, QtCore.Qt.ControlModifier)
    settle(qtbot, 50)
    assert datalist.i == 0
    viewer.btnLatest.click()
    assert viewer.btnLatest.isChecked()
    qtbot.waitUntil(lambda: datalist.i == len(items) - 1, timeout=3000)
    viewer.btnPrevious.click()  # unchecks Latest
    settle(qtbot, 300)
    assert not viewer.btnLatest.isChecked()
    assert datalist.i == len(items) - 2
    viewer.close()


def test_viewer_rating_widget(qtbot, synthetic):
    from qt_dataviewer import DatasetViewer

    ratings = []
    viewer = DatasetViewer(make_xarray_dataset("1d", synthetic["1d"]),
                           rating_options="rating-star-hide")
    viewer.dataset_rating_changed.connect(lambda dd, r: ratings.append(r))
    rw = viewer.rating_widget
    rw.cb_star.click()
    rw.cb_hide.click()
    rw.cb_hide.click()
    rw.cb_star.click()
    rw.cb_star.click()
    settle(qtbot)
    assert ratings == [1, -1, 0, 1, 0]
    viewer.close()
