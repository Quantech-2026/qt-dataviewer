from datetime import datetime, timedelta
import logging

import numpy as np
import xarray as xr
from core_tools.data.ds.data_set import load_by_uuid
from core_tools.data.ds.data_set_core import data_set
from core_tools.data.ds.ds2xarray import ds2xarray

from qt_dataviewer.abstract.dataset_description import DatasetDescription
from qt_dataviewer.abstract.dataset import Dataset


logger = logging.getLogger(__name__)


class CoreToolsDataset(Dataset):
    def __init__(self,
                 ds_description: DatasetDescription,
                 ds_ct: data_set | None = None):
        """
        Note: ds_ct is passed as optimization to avoid duplicate loading.
        """
        super().__init__(ds_description)
        self.uuid = int(ds_description.uid)
        self._last_sync = None
        self._ct_total_written = 0
        if ds_ct is None:
            ds_ct = getattr(ds_description, 'ds_ct', None)
        if ds_ct is None:
            ds_ct = load_by_uuid(self.uuid)
        self.ds_ct = ds_ct
        if len(ds_ct) == 0:
            self.ds_xr = xr.Dataset()
        else:
            self.ds_xr = ds2xarray(self.ds_ct, snapshot=None)

    def reload(self) -> None:
        self._sync_data()
        if len(self.ds_ct) == 0:
            self.ds_xr = xr.Dataset()
        else:
            self._ct_total_written = self._get_total_written()
            self.ds_xr = ds2xarray(self.ds_ct, snapshot=None)

    @property
    def data(self) -> xr.Dataset:
        return self.ds_xr

    @property
    def is_complete(self) -> bool:
        ds = self.ds_ct
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
                            logger.info(f"Incomplete {ds.exp_uuid} (NaN at end)")
                            return False
        return True

    @property
    def is_modified(self) -> bool:
        self.ds_ct.sync()
        return self._ct_total_written != self._get_total_written()

    def _sync_data(self) -> None:
        if (self._last_sync is None
            or datetime.now() - self._last_sync > timedelta(milliseconds=100)):
            self.ds_ct.sync()
            self._last_sync = datetime.now()

    def _get_total_written(self) -> int:
        total = 0
        ds = self.ds_ct
        self._sync_data()
        for m_param_set in ds:
            for m_param in m_param_set:
                param = m_param[1]
                written = param.written()
                if written is not None:
                    total +=  written
        return total

    @property
    def formatted_uid(self) -> str:
        return self.ds_description.uid
        # s = str(self.uuid)
        # return s[:-14] + '_' + s[-14:-9] + '_' + s[-9:]

    @property
    def info(self) -> dict[str, str]:
        labels = self.ds_description.labels
        return [
            ("Project", labels.get("project")),
            ("Setup", labels.get("setup")),
            ("Sample", labels.get("sample")),
            ]

    @property
    def snapshot(self) -> None | str | dict[str, any]:
        return self.ds_ct.snapshot

    def close(self):
        self.ds_ct.close()
