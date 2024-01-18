import logging
from datetime import datetime
from typing import List, Dict, Any, Union

import xarray as xr
from PyQt5 import QtCore, QtWidgets

from qt_dataviewer.plot_ui.plot_window import PlotWindow, EventHandler
from qt_dataviewer.utils.qt_utils import qt_log_exception
from .dataarray_plotter import DataArrayPlotter
from .dataset_list import DatasetList


logger = logging.getLogger(__name__)


class DatasetViewer(QtWidgets.QMainWindow, PlotWindow, EventHandler):
    def __init__(self, ds: xr.Dataset, *,
                 snapshot: Union[None, str, Dict[str, Any]] = None,
                 datalist: DatasetList = None):
        try:
            self.app = QtCore.QCoreApplication.instance()
            self.instance_ready = True
            if self.app is None:
                self.instance_ready = False
                self.app = QtWidgets.QApplication([])

            self.datalist = datalist
            super(QtWidgets.QMainWindow, self).__init__()
            self.setup_ui(self, self)

            self._plotters: List[DataArrayPlotter] = []
            self.alive = True

            self._set_ds(ds, snapshot)

            self.show()

            if self.instance_ready == False:
                self.app.exec()
        except Exception:
            logger.error('Dataset viewer', exc_info=True)
            raise

    def set_ds(self, ds: xr.Dataset, snapshot: Union[None, str, Dict[str, Any]] = None) -> None:
        self._set_ds(ds, snapshot)

    @qt_log_exception
    def _set_ds(self, ds: xr.Dataset, snapshot: Union[None, str, Dict[str, Any]] = None):
        if ds is None:
            self.clear_variables()
            return

        if not isinstance(ds, xr.Dataset):
            raise Exception(f"Unknown dataset class: {type(ds)}")

        if 'tuid' in ds.attrs:
            # Quantify
            ds = self._qf_to_nD(ds) # @@@ Move to quantify dataviwer

        self._set_info(ds, snapshot)

        for plotter in self._plotters:
            plotter.set_layout(None)

        self.clear_variables()

        # Create plot model for every variable
        self._plotters = []
        for var_name, var in ds.data_vars.items():
            seq_nr = len(self._plotters)
            plotter = DataArrayPlotter(var, seq_nr)
            self._plotters.append(plotter)
        self.setUpdatesEnabled(False)
        for var_name, var in ds.data_vars.items():
            hidden = False
            self.add_variable(var.name, hidden)
        self.setUpdatesEnabled(True)

    def _set_info(self, ds: xr.Dataset, snapshot: Union[None, str, Dict[str, Any]] = None):
        if 'uuid' in ds.attrs:
            # core-tools:
            s = str(ds.attrs['uuid'])
            uuid_str = s[:-14] + '_' + s[-14:-9] + '_' + s[-9:]
            self.set_dataset_info(
                ds.attrs['title'],
                uuid_str=uuid_str,
                start_time=datetime.fromisoformat(ds.attrs['measurement_time'])
                )
            self.set_details_info(
                [(name, ds.attrs[name])
                 for name in ['project', 'set_up', 'sample_name']]
                )
            self.set_snapshot(ds.attrs['snapshot'] if not snapshot else snapshot)
        elif 'tuid' in ds.attrs:
            # Quantify
            self.set_dataset_info(
                ds.attrs.get('name', '<no-name>'),
                uuid_str=ds.attrs['tuid'],
                start_time=None
                )
            self.set_snapshot(snapshot)
        else:
            logger.warning(f"Unknown xarray format. Attrs:{[name for name in ds.attrs]}")

    def _qf_to_nD(self, ds):
        # print(ds.attrs['name'], flush=True)
        # print(ds.attrs.keys())
        if ds.attrs.get('2D-grid'):
            ds = ds.set_index(dim_0=['x0','x1']).unstack('dim_0')
        elif len(ds.coords) == 1:
            for i, dim in enumerate(ds.dims):
                ds = ds.swap_dims({dim:f"x{i}"})
        return ds

    def closeEvent(self, event):
        """ Override of QT closeEvent. """
        self.alive = False

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

