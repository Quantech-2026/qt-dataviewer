"""Drive every control of a DatasetViewer the way a user would."""
import pyqtgraph as pg
from qtpy import QtCore, QtWidgets


def settle(qtbot, ms=20):
    qtbot.wait(ms)


def hover_plots(viewer, qtbot):
    """Move the mouse over every plot (crosshair / value label)."""
    for gv in viewer.findChildren(pg.GraphicsView):
        if not gv.isVisible():
            continue
        scene = gv.scene()
        r = gv.rect()
        for fx, fy in ((0.5, 0.5), (0.25, 0.75), (0.9, 0.1)):
            pt = gv.mapToScene(QtCore.QPoint(int(r.width() * fx), int(r.height() * fy)))
            scene.sigMouseMoved.emit(pt)
            settle(qtbot, 20)


def exercise_settings(viewer, qtbot):
    s = viewer.current_settings_widget
    if s is None or not hasattr(s, "_cb_multiline"):
        return  # panel shows the plot model's error message only
    # every axis mode, slice sliders and their loop button
    for key, group in list(s._rb_groups.items()):
        for button in list(group.buttons()):
            if s is not viewer.current_settings_widget:
                return
            if not button.isEnabled():
                continue
            button.click()
            settle(qtbot)
            hover_plots(viewer, qtbot)
            slider = s._sliders.get(key)
            if slider is not None and slider._enabled:
                q = slider.qslider
                q.setValue(q.maximum())
                settle(qtbot)
                q.setValue(q.maximum() // 2)
                settle(qtbot)
                slider.loop_btn.click()
                qtbot.wait(250)
                slider.loop_btn.click()
                settle(qtbot)
    # histogram off again (both buttons unchecked)
    hist = s._rb_groups.get("histogram")
    if hist is not None:
        for b in hist.buttons():
            if b.isChecked():
                b.click()
                settle(qtbot)
    for cbs in (s._cb_log, s._cb_fft):
        for cb in list(cbs.values()):
            if cb.isEnabled():
                cb.click()
                settle(qtbot)
                hover_plots(viewer, qtbot)
                cb.click()
                settle(qtbot)
    for cb in (s._cb_multiline, s._cb_measured_log):
        for _ in range(2):
            if cb.isEnabled():
                cb.click()
                settle(qtbot)
                hover_plots(viewer, qtbot)
    if getattr(s, "_complex_mode_cbx", None) is not None:
        cbx = s._complex_mode_cbx
        for i in range(cbx.count()):
            cbx.setCurrentIndex(i)
            settle(qtbot)
            hover_plots(viewer, qtbot)
    for b in s._rb_sidebar.buttons():
        if b.isEnabled():
            b.click()
            settle(qtbot)
            hover_plots(viewer, qtbot)
    for b in s._rb_sidebar.buttons():
        if b.isEnabled() and b.text() == "off":
            b.click()
            settle(qtbot)


def exercise_viewer(viewer, qtbot, settings=True):
    qtbot.waitExposed(viewer)
    lb = viewer.lb_variables
    hover_plots(viewer, qtbot)
    for row in range(lb.count()):
        lb.setCurrentRow(row)
        settle(qtbot)
        if settings:
            exercise_settings(viewer, qtbot)
    # click on each plot frame: selects its variable
    for seq_nr, frame in list(viewer._plot_widgets.items()):
        qtbot.mouseClick(frame, QtCore.Qt.LeftButton, pos=QtCore.QPoint(3, 3))
        settle(qtbot)
    # hide and show every variable
    for row in range(lb.count()):
        lb.item(row).setCheckState(QtCore.Qt.Unchecked)
        settle(qtbot)
    for row in range(lb.count()):
        lb.item(row).setCheckState(QtCore.Qt.Checked)
        settle(qtbot)
    # single chart
    if lb.count():
        viewer.cb_only_selected.click()
        settle(qtbot)
        for row in range(lb.count()):
            lb.setCurrentRow(row)
            settle(qtbot)
        lb.item(lb.count() - 1).setCheckState(QtCore.Qt.Unchecked)
        settle(qtbot)
        lb.item(lb.count() - 1).setCheckState(QtCore.Qt.Checked)
        settle(qtbot)
        viewer.cb_only_selected.click()
        settle(qtbot)
    # tabs: info (snapshot tree), pulses
    tabs = viewer.tab_widget
    for i in range(tabs.count()):
        if tabs.isTabVisible(i):
            tabs.setCurrentIndex(i)
            settle(qtbot, 50)
    expand_snapshot(viewer, qtbot)
    info = viewer.info_widget
    info.cb_condensed_snapshot.click()
    settle(qtbot)
    expand_snapshot(viewer, qtbot)
    info.cb_condensed_snapshot.click()
    settle(qtbot)
    if viewer.pulses_widget.pulses is not None:
        tabs.setCurrentIndex(2)
        settle(qtbot, 50)
        hover_plots(viewer, qtbot)
    tabs.setCurrentIndex(0)
    settle(qtbot)
    # resize: grid stretch recalculation
    viewer.resize(1200, 700)
    settle(qtbot)
    viewer.resize(1600, 1000)
    settle(qtbot)


def expand_snapshot(viewer, qtbot, max_items=300):
    tree = viewer.info_widget.snapshot_tree
    stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    n = 0
    while stack and n < max_items:
        item = stack.pop()
        if item.childCount() == 0:
            continue  # leaves have no expand indicator
        item.setExpanded(True)
        n += 1
        stack.extend(item.child(i) for i in range(item.childCount()))
    settle(qtbot)
