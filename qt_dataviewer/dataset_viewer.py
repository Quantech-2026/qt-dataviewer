import logging
from datetime import datetime, timedelta

from qtpy import QtCore, QtWidgets

from qt_dataviewer.plot_ui.plot_window import PlotWindow, EventHandler
from qt_dataviewer.plot_ui.dataarray_plotter import DataArrayPlotter
from qt_dataviewer.utils.qt_utils import (
    qt_log_exception,
    qt_init,
    qt_create_app,
    qt_run_app,
)

from .abstract import Dataset, DatasetDescription, DatasetList


logger = logging.getLogger(__name__)

_app = None


class DatasetViewer(QtWidgets.QMainWindow, PlotWindow, EventHandler):
    dataset_rating_changed = QtCore.Signal(DatasetDescription, int)

    def __init__(self, ds: Dataset, *,
                 datalist: DatasetList | None = None,
                 rating_options: str | None = None):
        try:
            global _app
            qt_app_runing = qt_init()
            if not qt_app_runing:
                # note: store reference to avoid garbage collection.
                # reference is also used to restart browser 2nd time in Python console.
                _app = qt_create_app()

            self.datalist = datalist
            super(QtWidgets.QMainWindow, self).__init__()
            self.setup_ui(self, self, rating_options)

            self._plotters: list[DataArrayPlotter] = []
            self.alive = True

            self._timer = QtCore.QTimer()
            self._timer.timeout.connect(self._update_ds)
            self._timer.setSingleShot(True)
            self._timer.setInterval(500)

            self.set_ds(ds)

            self.show()

            if _app is not None:
                qt_run_app(_app)
        except Exception:
            logger.error('Dataset viewer', exc_info=True)
            raise

    def set_ds(self, ds: Dataset) -> None:
        if ds is not None:
            self._set_ds(ds)
        else:
            logger.error("", exc_info=True)

    @qt_log_exception
    def _set_ds(self, ds: Dataset):
        self._timer.stop()
        try:
            if ds != self._ds:
                self._ds.close()
        except AttributeError:
            pass

        self._ds = ds
        if ds is None:
            self.clear_variables()
            return

        self._set_info(ds)

        # Disabling updates speeds up plot creation and drawing
        self.setUpdatesEnabled(False)
        for plotter in self._plotters:
            plotter.set_layout(None)

        self.clear_variables()

        # Create plot model for every variable
        self._plotters = []
        ds_xr = ds.data
        if len(ds_xr.data_vars) == 0:
            self.set_no_data_message()

        for var_name, var in ds_xr.data_vars.items():
            seq_nr = len(self._plotters)
            plotter = DataArrayPlotter(var, seq_nr)
            self._plotters.append(plotter)
        for var_name, var in ds_xr.data_vars.items():
            hidden = False
            self.add_variable(var.name, hidden)
        self.setUpdatesEnabled(True)

        if not ds.is_complete:
            self._timer.start()

    def _set_info(self, ds: Dataset):

        self.set_dataset_info(
            ds.name,
            uuid_str=ds.formatted_uid,
            start_time=ds.collected_datetime,
            rating=ds.ds_description.rating,
            )
        self.set_details_info(ds.info)
        self.set_snapshot(ds.snapshot)

    @qt_log_exception
    def _update_ds(self):
        ds = self._ds
        logger.info(f"Update dataset {ds.uid}")
        if ds.is_modified:
            was_empty = len(ds.data.data_vars) == 0
            try:
                self.setCursor(QtCore.Qt.WaitCursor)
                ds.reload()
            finally:
                self.setCursor(QtCore.Qt.ArrowCursor)
            if was_empty and len(ds.data.data_vars) > 0:
                self._set_ds(ds)
                return
            ds_xr = ds.data
            # Update every plot
            for i, var in enumerate(ds_xr.data_vars.values()):
                plotter = self._plotters[i]
                logger.info(f"Update {var.name}")
                plotter.update_data(var)

        if not ds.is_complete:
            # localize both timezones
            if ds.collected_datetime.astimezone() - datetime.now().astimezone() > timedelta(seconds=20):
                # slow down updates when measurement is already running for a while.
                self._timer.setInterval(1000)
            else:
                self._timer.setInterval(500)
            self._timer.start()

    def closeEvent(self, event):
        """ Override of QT closeEvent. """
        self.alive = False
        self._timer.stop()
        self._ds.close()
        self.close_plots()

    def variable_selection_changed(self, index: int, hidden: bool):
        plotter = self._plotters[index]
        self.show_settings(index, plotter.plot_model, hidden)

    def variable_hidden_changed(self, index: int, hidden: bool):
        plotter = self._plotters[index]
        if hidden:
            plotter.set_layout(None)
            self.remove_plot(index)
        else:
            plot_layout = self.add_plot(plotter.name, index)
            plotter.set_layout(plot_layout)

    @qt_log_exception
    def rating_changed(self, rating: int):
        ds = self._ds
        if ds is None:
            return
        ds.ds_description.rating = rating
        self.dataset_rating_changed.emit(ds.ds_description, rating)
