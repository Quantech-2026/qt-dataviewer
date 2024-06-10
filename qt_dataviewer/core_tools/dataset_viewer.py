import logging
from datetime import datetime, timedelta

import numpy as np
from core_tools.data.ds.data_set_core import data_set
from core_tools.data.ds.ds2xarray import ds2xarray
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox

from qt_dataviewer import DatasetViewer, DatasetList
from qt_dataviewer.utils.qt_utils import qt_log_exception


logger = logging.getLogger(__name__)


class CoreToolsDatasetViewer(DatasetViewer):
    coretools_upgrade_message_shown = False

    def __init__(self, ds: data_set, datalist: DatasetList = None):
        ds_fullqualname = type(ds).__module__ +'.' + type(ds).__qualname__
        if ds_fullqualname != "core_tools.data.ds.data_set_core.data_set":
            raise Exception(f"Expected coretools data_set got '{ds_fullqualname}'")

        if (datalist is not None
                and hasattr(datalist, 'select_next')
                and not hasattr(datalist, 'get_next')):
            if not CoreToolsDatasetViewer.coretools_upgrade_message_shown:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("Upgrade core-tools to v1.4.44+ to use next/previous buttons")
                msg.setWindowTitle("Core-tools upgrade")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
                CoreToolsDatasetViewer.coretools_upgrade_message_shown = True

            datalist = None

        try:
            ds_xr = ds2xarray(ds, snapshot=None)
        except TypeError:
            # older version of ds2xarray always stores snapshot in attrs as json
            ds_xr = ds2xarray(ds)
        super().__init__(ds_xr, datalist=datalist, snapshot=ds.snapshot)

        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.update_ds)
        self._timer.setSingleShot(True)
        self._timer.setInterval(500)

        self._ds = ds
        if not self.is_ds_complete(ds):
            logger.info(f"Incomplete dataset {ds.exp_uuid}")
            self._timer.start()

    def set_ds(self, ds: data_set):
        self._ds = ds
        self._timer.stop()
        try:
            ds_xr = ds2xarray(ds, snapshot=None)
        except TypeError:
            # older version of ds2xarray always stores snapshot in attrs as json
            ds_xr = ds2xarray(ds)
        self._set_ds(ds_xr, ds.snapshot)

        if not self.is_ds_complete(ds):
            logger.info(f"Incomplete dataset {ds.exp_uuid}")
            self._timer.start()

    def is_ds_complete(self, ds):
        if (not ds.completed
            and datetime.now() - ds.run_timestamp < timedelta(days=2)):
            for m_param_set in ds:
                for m_param in m_param_set:
                    param = m_param[1]
                    # check length of written data
                    written = param.written()
                    if written is not None:
                        if written < np.prod(param.shape):
                            logger.info(f"Incomplete {ds.exp_uuid} {written} <> {np.prod(param.shape)}")
                            return False
                    else:
                        # length written is unknown, check if last value is not None
                        data = param()
                        if np.isnan(data.flat[-1]):
                            logger.info(f"Incomplete {ds.exp_uuid} NaN")
                            return False
        return True

    @qt_log_exception
    def update_ds(self):
        ds = self._ds
        logger.info('Update ds')
        ds.sync()
        # Update every plot
        ds_xr = ds2xarray(ds)
        for i, var in enumerate(ds_xr.data_vars.values()):
            plotter = self._plotters[i]
            logger.info(f"Update {var.name}")
            plotter.update_data(var)

        if not self._ds.completed:
            self._timer.start()

    def closeEvent(self, event):
        """ Override of QT closeEvent. """
        self._timer.stop()
        super().closeEvent(event)
