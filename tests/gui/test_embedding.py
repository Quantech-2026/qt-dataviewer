"""
Embedding browser and viewers in another window: show=False and
DataBrowserBase.create_viewer().
"""
import os
import subprocess
import sys
import textwrap

from qtpy import QtWidgets

from conftest import make_xarray_dataset
from exercise import settle
from test_browsers import double_click_row, qcodes_db, select_all_dates  # noqa: F401 (fixture)


def test_viewer_shows_itself_by_default(qtbot, synthetic):
    from qt_dataviewer import DatasetViewer

    viewer = DatasetViewer(make_xarray_dataset("1d", synthetic["1d"]))
    assert viewer.isVisible() and viewer.isWindow()
    viewer.close()


def test_viewer_in_a_tab(qtbot, synthetic):
    from qt_dataviewer import DatasetViewer

    viewer = DatasetViewer(make_xarray_dataset("1d", synthetic["1d"]), show=False)
    assert not viewer.isVisible()
    tabs = QtWidgets.QTabWidget()
    qtbot.addWidget(tabs)
    tabs.addTab(viewer, "1d")
    tabs.show()
    qtbot.waitExposed(tabs)
    assert viewer.isVisible() and not viewer.isWindow()
    viewer.close()
    settle(qtbot)
    assert not viewer.alive


def test_qcodes_browser_in_a_tab(qtbot, qcodes_db):
    """The browser and the viewers it opens (double-click, open_uid) all in one tab widget."""
    from qcodes.dataset import load_by_id
    from qt_dataviewer import DatasetViewer
    from qt_dataviewer.qcodes import QCoDeSDataBrowser

    tabs = QtWidgets.QTabWidget()
    qtbot.addWidget(tabs)

    class Browser(QCoDeSDataBrowser):
        def create_viewer(self, ds, datalist):
            viewer = DatasetViewer(ds, datalist=datalist, rating_options=self.rating_options,
                                   show=False)
            assert not viewer.isVisible()
            tabs.addTab(viewer, ds.name)
            return viewer

    browser = Browser(qcodes_db, show=False)
    assert not browser.isVisible()
    tabs.addTab(browser, "browser")
    tabs.show()
    qtbot.waitExposed(tabs)
    assert browser.isVisible() and not browser.isWindow()

    select_all_dates(qtbot, browser)
    double_click_row(qtbot, browser.dataset_list_view, 0)
    browser.open_uid(load_by_id(2).guid)
    settle(qtbot)
    viewers = list(browser.viewers)
    assert len(viewers) == 2 and tabs.count() == 3
    assert all(tabs.indexOf(v) > 0 and not v.isWindow() for v in viewers)
    assert viewers[1].label_name.text() == "sweep 2d"

    viewers[1].btnPrevious.click()  # paging stays in the tab
    settle(qtbot, 40)
    assert tabs.indexOf(viewers[1]) > 0 and not viewers[1].isWindow()

    browser.close()  # closes its viewers and the store
    settle(qtbot)
    assert not any(v.alive for v in viewers)


def test_show_false_without_qt_application_returns():
    """Without a running QApplication the constructors run the Qt event loop themselves,
    unless show=False: then they return, and the caller runs the application."""
    script = textwrap.dedent("""
        import xarray as xr
        from qtpy import QtWidgets
        from qt_dataviewer import DatasetViewer
        from qt_dataviewer.dataset_files.generic_xarray import XarrayDataset, XarrayDatasetDescription
        from datetime import datetime

        assert QtWidgets.QApplication.instance() is None
        ds_xr = xr.Dataset({"v": ("x", [1.0, 2.0])}, coords={"x": [0.0, 1.0]})
        dd = XarrayDatasetDescription(uid="u", name="n", collected_datetime=datetime.now(), ds_xr=ds_xr)
        viewer = DatasetViewer(XarrayDataset(dd, ds_xr), show=False)
        assert not viewer.isVisible()
        print("returned")
        """)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                            timeout=120, env=env)
    assert result.returncode == 0, result.stderr
    assert "returned" in result.stdout
