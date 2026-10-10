import os
import shutil
import sqlite3

import numpy as np
import pytest
from qtpy import QtCore, QtWidgets

from conftest import TEST_DATA
from exercise import exercise_viewer, settle


# ------------------------------------------------------------------ helpers

def rows(view):
    return view.model.rowCount()


def double_click_row(qtbot, list_view, row):
    tv = list_view.tree_view
    index = list_view.model.index(row, 0)
    tv.scrollTo(index)
    rect = tv.visualRect(index)
    qtbot.mouseClick(tv.viewport(), QtCore.Qt.LeftButton, pos=rect.center())
    qtbot.mouseDClick(tv.viewport(), QtCore.Qt.LeftButton, pos=rect.center())
    settle(qtbot, 30)


def right_click_row(qtbot, list_view, row):
    tv = list_view.tree_view
    rect = tv.visualRect(list_view.model.index(row, 0))
    tv.customContextMenuRequested.emit(rect.center())
    settle(qtbot)


def open_all(qtbot, browser, heavy=()):
    """Double-click every dataset in the list; returns the number opened."""
    lv = browser.dataset_list_view
    n = rows(lv)
    for row in range(n):
        last = browser.viewers[-1] if browser.viewers else None
        double_click_row(qtbot, lv, row)
        assert browser.viewers and browser.viewers[-1] is not last, f"row {row} did not open"
        viewer = browser.viewers[-1]
        name = viewer.label_name.text()
        exercise_viewer(viewer, qtbot, settings=any(h in name for h in heavy))
        viewer.close()
        settle(qtbot)
    return n


def page_through(qtbot, viewer, clicks=6):
    seen = set()
    for button in [viewer.btnNext] * clicks + [viewer.btnPrevious] * (2 * clicks) + [viewer.btnNext] * clicks:
        button.click()
        settle(qtbot, 40)
        seen.add(viewer.label_uuid.text())
    return seen


# ------------------------------------------------------------------ QCoDeS

@pytest.fixture(scope="module")
def qcodes_db(tmp_path_factory):
    import qcodes as qc
    from qcodes.dataset import Measurement, initialise_or_create_database_at, load_or_create_experiment
    from qcodes.parameters import ManualParameter, Parameter
    from qcodes.validators import Arrays, ComplexNumbers

    path = tmp_path_factory.mktemp("qcodes") / "synthetic.db"
    initialise_or_create_database_at(path)
    qc.config.core.db_location = str(path)

    x = ManualParameter("x", unit="V", label="Gate X")
    y = ManualParameter("y", unit="A", label="Bias")
    sig = ManualParameter("signal", unit="V")
    noise = ManualParameter("noise", unit="V")
    iq = ManualParameter("iq", unit="V", vals=ComplexNumbers())
    t = ManualParameter("t", unit="s", vals=Arrays(shape=(64,)))
    trace = ManualParameter("trace", unit="mV", vals=Arrays(shape=(64,)))
    label = ManualParameter("label")

    def run(exp, name, setup, body):
        meas = Measurement(exp, name=name)
        setup(meas)
        with meas.run() as saver:
            body(saver)
        return saver.dataset.run_id

    exp_a = load_or_create_experiment("exp_a", sample_name="sample1")
    exp_b = load_or_create_experiment("exp_b", sample_name="sample1")
    exp_c = load_or_create_experiment("exp_c", sample_name="sample2")

    def sweep1d(meas):
        meas.register_parameter(x)
        meas.register_parameter(sig, setpoints=(x,))
        meas.register_parameter(noise, setpoints=(x,))

    def body1d(saver):
        for v in np.linspace(-1, 1, 51):
            saver.add_result((x, v), (sig, np.sin(3 * v)), (noise, 1e-3 * np.random.randn()))

    def sweep2d(meas):
        meas.register_parameter(x)
        meas.register_parameter(y)
        meas.register_parameter(sig, setpoints=(x, y))

    def body2d(saver):
        for v in np.linspace(-1, 1, 21):
            for w in np.linspace(0, 1e-3, 17):
                saver.add_result((x, v), (y, w), (sig, np.sin(4 * v) * np.cos(3000 * w)))

    def sweep_complex(meas):
        meas.register_parameter(x)
        meas.register_parameter(iq, setpoints=(x,), paramtype="complex")

    def body_complex(saver):
        for v in np.linspace(-1, 1, 41):
            saver.add_result((x, v), (iq, np.exp(1j * 4 * v) * (1 + v)))

    def sweep_array(meas):
        meas.register_parameter(x)
        meas.register_parameter(t, paramtype="array")
        meas.register_parameter(trace, setpoints=(x, t), paramtype="array")

    def body_array(saver):
        tt = np.linspace(0, 1e-6, 64)
        for v in np.linspace(0, 1, 11):
            saver.add_result((x, v), (t, tt), (trace, np.sin(2e7 * tt + v)))

    def sweep_text(meas):
        meas.register_parameter(x)
        meas.register_parameter(label, setpoints=(x,), paramtype="text")
        meas.register_parameter(sig, setpoints=(x,))

    def body_text(saver):
        for v in np.linspace(0, 1, 5):
            saver.add_result((x, v), (label, f"pt{v:.2f}"), (sig, v))

    def sweep_empty(meas):
        meas.register_parameter(x)
        meas.register_parameter(sig, setpoints=(x,))

    ids = []
    ids.append(run(exp_a, "sweep 1d", sweep1d, body1d))
    ids.append(run(exp_a, "sweep 2d", sweep2d, body2d))
    ids.append(run(exp_b, "complex s21", sweep_complex, body_complex))
    ids.append(run(exp_b, "array traces", sweep_array, body_array))
    ids.append(run(exp_c, "text labels", sweep_text, body_text))
    ids.append(run(exp_c, "empty run", sweep_empty, lambda saver: None))
    for i in range(4):
        ids.append(run(exp_c, f"repeat {i}", sweep1d, body1d))

    # spread runs over three days
    con = sqlite3.connect(path)
    for k, run_id in enumerate(ids):
        days = 2 if k < 3 else (1 if k < 6 else 0)
        con.execute("UPDATE runs SET run_timestamp = run_timestamp - ?, "
                    "completed_timestamp = completed_timestamp - ? WHERE run_id = ?",
                    (days * 86400, days * 86400, run_id))
    con.commit()
    con.close()
    return str(path)


def qcodes_browser(db):
    from qt_dataviewer.qcodes import QCoDeSDataBrowser
    return QCoDeSDataBrowser(db)


def select_all_dates(qtbot, browser):
    browser.date_list_view.selectAll()
    settle(qtbot)


def test_qcodes_browser_open_every_run(qtbot, qcodes_db):
    browser = qcodes_browser(qcodes_db)
    qtbot.waitExposed(browser)
    assert browser.date_list_view.count() == 3
    select_all_dates(qtbot, browser)
    assert rows(browser.dataset_list_view) == 10
    open_all(qtbot, browser, heavy=("sweep 2d", "complex", "array", "text"))
    browser.close()


def test_qcodes_browser_filters(qtbot, qcodes_db):
    browser = qcodes_browser(qcodes_db)
    select_all_dates(qtbot, browser)
    lv = browser.dataset_list_view
    widgets = {w.name: w for w in browser.top_bar.findChildren(QtWidgets.QWidget) if hasattr(w, "name")}
    sample = widgets["Sample"].combo_box
    experiment = widgets["Experiment"].combo_box
    sample.setCurrentText("sample2")
    settle(qtbot)
    select_all_dates(qtbot, browser)
    assert rows(lv) == 6
    assert experiment.findText("exp_a") < 0  # experiments of sample1 are gone
    experiment.setCurrentText("exp_c")
    settle(qtbot)
    sample.setCurrentIndex(0)  # -- All --
    settle(qtbot)
    select_all_dates(qtbot, browser)
    assert rows(lv) == 6
    experiment.setCurrentIndex(0)
    settle(qtbot)
    select_all_dates(qtbot, browser)
    assert rows(lv) == 10
    name = widgets["Name"].text_edit
    name.setText("repeat")
    name.editingFinished.emit()
    settle(qtbot)
    select_all_dates(qtbot, browser)
    assert rows(lv) == 4
    name.setText("")
    name.editingFinished.emit()
    settle(qtbot)
    for key in ("Variables", "Axes"):
        combo = widgets[key].combo_box
        for i in range(combo.count()):
            combo.setCurrentIndex(i)
            settle(qtbot)
            select_all_dates(qtbot, browser)
        combo.setCurrentIndex(0)
        settle(qtbot)
    select_all_dates(qtbot, browser)
    assert rows(lv) == 10
    # sorting by every column, context menu
    for col in range(lv.model.columnCount()):
        lv.tree_view.sortByColumn(col, QtCore.Qt.AscendingOrder)
        settle(qtbot)
    right_click_row(qtbot, lv, 0)
    browser.close()


def test_qcodes_browser_navigation(qtbot, qcodes_db, traps):
    browser = qcodes_browser(qcodes_db)
    select_all_dates(qtbot, browser)
    lv = browser.dataset_list_view
    double_click_row(qtbot, lv, 0)
    viewer = browser.viewers[-1]
    seen = page_through(qtbot, viewer, clicks=12)
    assert len(seen) == 10
    viewer.btnLatest.click()
    settle(qtbot, 400)
    assert viewer.btnLatest.isChecked()
    viewer.btnLatest.click()
    settle(qtbot)
    # UID box
    guid = viewer.label_uuid.text()
    uid_edit = browser.top_bar.uid_edit
    uid_edit.setText(guid)
    qtbot.keyClick(uid_edit, QtCore.Qt.Key_Return)
    settle(qtbot)
    assert len(browser.viewers) == 2
    uid_edit.setText("no-such-guid")
    qtbot.keyClick(uid_edit, QtCore.Qt.Key_Return)
    settle(qtbot)
    traps.expected = 1  # "Dataset not found"
    assert traps[-1][1] == "Dataset 'no-such-guid' not found"
    # close all plots: button and Ctrl+K
    browser.top_bar.findChild(QtWidgets.QPushButton).click()
    settle(qtbot)
    assert browser.viewers == []
    double_click_row(qtbot, lv, 1)
    qtbot.keyClick(browser, QtCore.Qt.Key_K, QtCore.Qt.ControlModifier)
    settle(qtbot)
    # reload from the menu
    for action in browser.menuBar().actions()[0].menu().actions():
        if "Reload" in action.text():
            action.trigger()
    settle(qtbot)
    select_all_dates(qtbot, browser)
    assert rows(lv) == 10
    browser.close()


def test_qcodes_viewer_closed_with_latest_checked(qtbot, qcodes_db):
    """A viewer closed with Latest checked stops looking for the latest dataset;
    deleted (as an embedded viewer is), its timer must not fire on its widgets."""
    browser = qcodes_browser(qcodes_db)
    select_all_dates(qtbot, browser)
    double_click_row(qtbot, browser.dataset_list_view, 0)
    viewer = browser.viewers[-1]
    viewer.btnLatest.click()
    settle(qtbot, 300)
    assert viewer.btnLatest.isChecked()
    viewer.close()
    assert not viewer._timer_latest.isActive()
    browser.viewers.remove(viewer)
    viewer.deleteLater()
    settle(qtbot, 300)
    browser.close()


def test_qcodes_browser_live_run(qtbot, qcodes_db):
    """A run that starts while the browser is open shows up and plots live."""
    import qcodes as qc
    from qcodes.dataset import Measurement, load_or_create_experiment
    from qcodes.parameters import ManualParameter

    qc.config.core.db_location = qcodes_db
    browser = qcodes_browser(qcodes_db)
    browser.date_list_view.item(0).setSelected(True)  # today
    settle(qtbot)
    n0 = rows(browser.dataset_list_view)
    x = ManualParameter("x", unit="V")
    sig = ManualParameter("signal", unit="V")
    exp = load_or_create_experiment("exp_live", sample_name="sample3")
    meas = Measurement(exp, name="live sweep")
    meas.register_parameter(x)
    meas.register_parameter(sig, setpoints=(x,))
    meas.write_period = 0.05
    with meas.run() as saver:
        saver.add_result((x, 0.0), (sig, 0.0))
        saver.flush_data_to_database()
        qtbot.waitUntil(lambda: rows(browser.dataset_list_view) == n0 + 1, timeout=5000)
        double_click_row(qtbot, browser.dataset_list_view, 0)
        viewer = browser.viewers[-1]
        assert viewer.label_name.text() == "live sweep"
        for i in range(1, 30):
            saver.add_result((x, i / 30), (sig, np.sin(i / 3)))
            if i % 10 == 0:
                saver.flush_data_to_database()
                settle(qtbot, 700)
        saver.flush_data_to_database()
        qtbot.waitUntil(lambda: viewer._ds.data.sizes.get("x", 0) == 30, timeout=5000)
    settle(qtbot, 1200)

    # a new run in an experiment that already has runs
    exp_a = load_or_create_experiment("exp_a", sample_name="sample1")
    meas = Measurement(exp_a, name="late run")
    meas.register_parameter(x)
    meas.register_parameter(sig, setpoints=(x,))
    with meas.run() as saver:
        saver.add_result((x, 0.0), (sig, 1.0))
    names = lambda: [browser.dataset_list_view.model.item(r, 2).text()
                     for r in range(rows(browser.dataset_list_view))]
    qtbot.waitUntil(lambda: "late run" in names(), timeout=5000)
    assert names().count("late run") == 1 and names().count("live sweep") == 1
    browser.close()


def test_qcodes_browser_dark_and_no_db(qtbot, qcodes_db):
    from qt_dataviewer.qcodes import QCoDeSDataBrowser
    b = QCoDeSDataBrowser(None)  # asks for a database: dialog cancelled
    assert b.dataset_store.db_path is None
    b.close()
    b = QCoDeSDataBrowser(qcodes_db, gui_style="dark")
    select_all_dates(qtbot, b)
    double_click_row(qtbot, b.dataset_list_view, 0)
    exercise_viewer(b.viewers[-1], qtbot, settings=False)
    b.close()
    QtWidgets.QApplication.instance().setStyleSheet("")


# ------------------------------------------------------------------ files

def walk_tree(qtbot, browser, visit):
    tree = browser.directory_tree
    stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    while stack:
        item = stack.pop(0)
        tree.setCurrentItem(item)
        settle(qtbot)
        visit(item)
        item.setExpanded(True)
        settle(qtbot)
        stack.extend(item.child(i) for i in range(item.childCount()))


@pytest.mark.parametrize("which", ["test_data", "synthetic"])
def test_file_browser(qtbot, synthetic_dir, which):
    from qt_dataviewer.data_file_browser import DataFileBrowser

    path = TEST_DATA if which == "test_data" else str(synthetic_dir)
    browser = DataFileBrowser(path)
    qtbot.waitExposed(browser)
    opened = []

    def visit(item):
        n = open_all(qtbot, browser, heavy=("2d", "3d") if which == "synthetic" else ())
        opened.append((item.text(0), n))

    walk_tree(qtbot, browser, visit)
    assert sum(n for _, n in opened) > 10, opened
    browser.close()


def test_file_browser_navigation_and_reload(qtbot, synthetic_dir, traps):
    from qt_dataviewer.data_file_browser import DataFileBrowser

    browser = DataFileBrowser(str(synthetic_dir))
    tree = browser.directory_tree
    flat = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())
            if tree.topLevelItem(i).text(0) == "flat"][0]
    tree.setCurrentItem(flat)
    settle(qtbot)
    double_click_row(qtbot, browser.dataset_list_view, 0)
    seen = page_through(qtbot, browser.viewers[-1], clicks=20)
    assert len(seen) == rows(browser.dataset_list_view)
    # reload with a nested folder selected
    nested = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())
              if tree.topLevelItem(i).text(0) == "nested"][0]
    nested.setExpanded(True)
    settle(qtbot)
    month = nested.child(0)
    month.setExpanded(True)
    settle(qtbot)
    tree.setCurrentItem(month.child(0))
    settle(qtbot)
    n = rows(browser.dataset_list_view)
    assert n > 0
    browser.reload()
    settle(qtbot)
    assert tree.currentItem() is not None and tree.currentItem().text(0) == "day1"
    assert rows(browser.dataset_list_view) == n
    browser.close()


# ------------------------------------------------------------------ quantify

@pytest.fixture
def quantify_dir(tmp_path):
    dst = tmp_path / "quantify"
    shutil.copytree(os.path.join(TEST_DATA, "quantify"), dst)
    return dst


def test_quantify_browser(qtbot, quantify_dir):
    from qt_dataviewer.quantify import QuantifyDataBrowser

    browser = QuantifyDataBrowser(str(quantify_dir))
    qtbot.waitExposed(browser)
    select_all_dates(qtbot, browser)
    n = open_all(qtbot, browser, heavy=("2D Cosine", "Spectroscopy"))
    assert n > 20
    double_click_row(qtbot, browser.dataset_list_view, 3)
    seen = page_through(qtbot, browser.viewers[-1], clicks=8)
    assert len(seen) > 8
    widgets = [w for w in browser.top_bar.findChildren(QtWidgets.QWidget) if getattr(w, "name", None) == "Name"]
    widgets[0].text_edit.setText("Spec")
    widgets[0].text_edit.editingFinished.emit()
    settle(qtbot)
    select_all_dates(qtbot, browser)
    assert 0 < rows(browser.dataset_list_view) < n
    browser.close()


def test_quantify_browser_live(qtbot, quantify_dir):
    """Live updating: a dataset written today appears and opens automatically."""
    from datetime import datetime
    from qt_dataviewer.quantify import QuantifyDataBrowser

    browser = QuantifyDataBrowser(str(quantify_dir))
    browser.top_bar.cb_live_plotting.click()
    settle(qtbot)
    now = datetime.now()
    src = quantify_dir / "20200430" / "20200430-170837-001-315f36-Cosine test"
    day = quantify_dir / f"{now:%Y%m%d}"
    day.mkdir()
    shutil.copytree(src, day / f"{now:%Y%m%d-%H%M%S}-001-abcdef-Live cosine")
    qtbot.waitUntil(lambda: any(v.label_name.text() == "Live cosine" for v in browser.viewers), timeout=5000)
    browser.top_bar.cb_live_plotting.click()
    settle(qtbot)
    browser.close()


# ------------------------------------------------------------------ others

def test_backends_import():
    """Browsers that need a server: their GUI modules must at least import."""
    import qt_dataviewer.sqdl.data_browser  # noqa: F401
    import qt_dataviewer.cli.qt_file_browser  # noqa: F401
    import qt_dataviewer.cli.qt_qcodes_browser  # noqa: F401
    import qt_dataviewer.cli.qt_quantify_browser  # noqa: F401
