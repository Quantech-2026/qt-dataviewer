"""
The GUI of the core-tools and sQDL browsers (rating column, rating and keyword
filters, rating widget in the viewer, live updating) on an in-memory store,
because their real stores need a database or server.
"""
import copy
from datetime import datetime, timedelta

import pytest
from qtpy import QtCore, QtWidgets

from conftest import make_xarray_dataset
from exercise import exercise_viewer, settle
from test_browsers import double_click_row, rows, select_all_dates


CORE_TOOLS = dict(
    label_keys={"Project": "project", "Setup": "setup", "Sample": "sample", "Rating": "rating",
                "UUID": "uid", "Time": "time", "Name": "name", "Keywords": "keywords"},
    column_definitions=[("Rating", 46, "rating-star"), ("UUID", ), ("Time", ), ("Name", ), ("Keywords", )],
    filters=[("Project", "list"), ("Setup", "list"), ("Sample", "list"), ("Rating", "rating-star"),
             "Name", ("Keywords", "keywords")],
)
SQDL = dict(
    label_keys={"Rating": "rating", "UUID": "uid", "Time": "time", "Name": "name",
                "Variables": "variables_measured", "Axes": "dimensions", "Setup": "setup", "Sample": "sample"},
    column_definitions=[("Rating", 54, "rating-star-hide"), ("UUID", ), ("Time", ), ("Name", ),
                        ("Variables", ), ("Axes", )],
    filters=[("Setup", "list"), ("Sample", "list"), ("Rating", "rating-star-hide"), "Name",
             ("Variables", "list"), ("Axes", "list")],
)


def make_store(synthetic):
    from qt_dataviewer.abstract import DatasetStore, Filter
    from qt_dataviewer.dataset_files.generic_xarray import XarrayDatasetDescription

    class MemStore(DatasetStore):
        def __init__(self):
            super().__init__(is_dynamic=True)
            self.all = []
            self.filter = Filter()
            now = datetime.now()
            for i, name in enumerate(["1d", "2d", "3d", "scalar", "1d_complex", "scatter", "mixed_dims"]):
                ds = synthetic[name]
                self.all.append(XarrayDatasetDescription(
                    uid=f"{1000 + i}", name=name, collected_datetime=now - timedelta(days=i // 3, minutes=i),
                    rating=[0, 1, -1][i % 3], ds_xr=ds,
                    labels=dict(project=f"proj{i % 2}", setup="setup1", sample=f"s{i % 3}",
                                keywords=["kw" + name[:2], "all"],
                                variables_measured=", ".join(ds.data_vars), dimensions=", ".join(ds.dims))))
            self.ratings_set = []

        source_name = "memory"

        def set_filter(self, filter):
            self.filter = copy.deepcopy(filter)
            self.refresh()

        def visible(self):
            f = self.filter
            out = []
            for dd in self.all:
                if f.rating == 1 and dd.rating != 1:
                    continue
                if (f.rating or 0) == 0 and dd.rating < 0:
                    continue
                if f.name_contains and f.name_contains not in dd.name:
                    continue
                ok = True
                for key, value in (f.labels or {}).items():
                    if not value:
                        continue
                    have = dd.labels.get(key)
                    if isinstance(value, list):
                        ok &= all(v in have for v in value)
                    else:
                        ok &= have == value
                if ok:
                    out.append(dd)
            return sorted(out, key=lambda d: d.collected_datetime, reverse=True)

        def refresh(self):
            vis = self.visible()
            self._set_dates(sorted({d.collected_date for d in vis}, reverse=True))
            labels = {}
            for dd in self.all:
                for k, v in dd.labels.items():
                    if isinstance(v, str):
                        labels.setdefault(k, set()).add(v)
            self._set_labels({k: sorted(v) for k, v in labels.items()})
            self.datasets_changed.emit()

        def get_dataset_descriptions(self, date):
            return [d for d in self.visible() if d.collected_date == date]

        def get_dataset_description_for_uid(self, uid):
            return next((d for d in self.all if d.uid == uid), None)

        def get_dataset(self, dd):
            return make_xarray_dataset(dd.name, dd.ds_xr, dd.collected_datetime)

        def set_rating(self, dd, rating):
            dd.rating = rating
            self.ratings_set.append((dd.uid, rating))

        def _index(self, dd):
            vis = self.visible()
            return vis, [d.uid for d in vis].index(dd.uid)

        def get_next(self, dd):
            vis, i = self._index(dd)
            if i == 0:
                raise StopIteration()
            return vis[i - 1]

        def get_previous(self, dd):
            vis, i = self._index(dd)
            if i + 1 >= len(vis):
                raise StopIteration()
            return vis[i + 1]

        def get_latest(self):
            vis = self.visible()
            if not vis:
                raise StopIteration()
            return vis[0]

        def add(self, name):
            dd = copy.copy(self.all[0])
            dd.uid = str(2000 + len(self.all))
            dd.name = name
            dd.rating = 0
            dd.collected_datetime = datetime.now()
            self.all.append(dd)
            self.new_datasets.emit([dd])

        def close(self):
            pass

    return MemStore()


def make_browser(store, config):
    from qt_dataviewer.browser_ui.main_window import DataBrowserBase

    class MemBrowser(DataBrowserBase):
        def __init__(self):
            self.data_store = store
            super().__init__("Memory", store, "Scope", sort_by_column=1, **config)

        def get_menu_actions(self):
            return None

        def browser_started(self):
            store.refresh()

    return MemBrowser()


def choose_menu(monkeypatch, text):
    def exec_(menu, *args):
        return next((a for a in menu.actions() if a.text() == text), None)
    for name in ("exec", "exec_"):
        monkeypatch.setattr(QtWidgets.QMenu, name, exec_, raising=False)


def filter_widget(browser, name):
    return next(w for w in browser.top_bar.findChildren(QtWidgets.QWidget) if getattr(w, "name", None) == name)


@pytest.mark.parametrize("config", [CORE_TOOLS, SQDL], ids=["core-tools", "sqdl"])
def test_rating_browser(qtbot, synthetic, monkeypatch, config):
    store = make_store(synthetic)
    browser = make_browser(store, config)
    qtbot.waitExposed(browser)
    select_all_dates(qtbot, browser)
    lv = browser.dataset_list_view
    hidden = config is SQDL
    assert rows(lv) == 5  # hidden (-1) datasets are filtered by default

    # rate from the list's rating column
    tv = lv.tree_view
    for text, rating in [("Star", 1), ("Default", 0)] + ([("Hide", -1)] if hidden else []):
        choose_menu(monkeypatch, text)
        index = lv.model.index(0, 0)
        dd = lv.model.item(0, 0).data(QtCore.Qt.UserRole)
        qtbot.mouseClick(tv.viewport(), QtCore.Qt.LeftButton, pos=tv.visualRect(index).center())
        settle(qtbot)
        assert store.ratings_set[-1] == (dd.uid, rating)
        assert lv.model.item(0, 0).data(QtCore.Qt.DecorationRole) is not None
    choose_menu(monkeypatch, None)

    # rating filter
    combo = filter_widget(browser, "Rating").combo_box
    for i in range(combo.count()):
        combo.setCurrentIndex(i)
        settle(qtbot)
        select_all_dates(qtbot, browser)
    combo.setCurrentText("Default")
    settle(qtbot)

    # keyword / list filters
    if config is CORE_TOOLS:
        kw = filter_widget(browser, "Keywords").text_edit
        kw.setText("kw2d, all")
        kw.editingFinished.emit()
        settle(qtbot)
        select_all_dates(qtbot, browser)
        assert rows(lv) == 1
        kw.setText("")
        kw.editingFinished.emit()
        settle(qtbot)
    for name in ("Setup", "Sample"):
        c = filter_widget(browser, name).combo_box
        for i in range(c.count()):
            c.setCurrentIndex(i)
            settle(qtbot)
            select_all_dates(qtbot, browser)
        c.setCurrentIndex(0)
        settle(qtbot)

    # viewer with rating widget
    select_all_dates(qtbot, browser)
    double_click_row(qtbot, lv, 0)
    viewer = browser.viewers[-1]
    rw = viewer.rating_widget
    assert rw is not None
    store.ratings_set.clear()
    rw.cb_star.click()
    settle(qtbot)
    assert store.ratings_set[-1][1] == 1
    if hidden:
        rw.cb_hide.click()
        settle(qtbot)
        assert store.ratings_set[-1][1] == -1
        rw.cb_hide.click()
        settle(qtbot)
        assert store.ratings_set[-1][1] == 0
    exercise_viewer(viewer, qtbot, settings=False)
    for _ in range(8):
        viewer.btnPrevious.click()
        settle(qtbot, 30)
    for _ in range(8):
        viewer.btnNext.click()
        settle(qtbot, 30)

    # live updating: new datasets open automatically
    browser.top_bar.cb_live_plotting.click()
    settle(qtbot)
    n_viewers = len([v for v in browser.viewers if v.alive])
    store.add("brand new")
    settle(qtbot, 100)
    assert browser.viewers[-1].label_name.text() == "brand new"
    assert len([v for v in browser.viewers if v.alive]) == n_viewers + 1
    browser.top_bar.cb_live_plotting.click()
    browser.close()
