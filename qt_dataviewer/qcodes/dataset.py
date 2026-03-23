from datetime import datetime, timedelta
from typing import Any
import logging

import xarray as xr

from .dataset_description import QCoDeSDatasetDescription
from qt_dataviewer.abstract.dataset import Dataset


logger = logging.getLogger(__name__)


class QCoDeSDataset(Dataset):
    def __init__(self, ds_description: QCoDeSDatasetDescription):
        super().__init__(ds_description)

        self._ds = ds_description.ds
        self._snapshot = None
        if self._ds.completed:
            ds_description.completed_time = datetime.fromtimestamp(self._ds.completed_timestamp_raw)
        self.reload()

    def reload(self) -> None:
        self._number_of_results = self._ds.number_of_results

        if self._number_of_results == 0:
            self.ds_xr = xr.Dataset()
        else:
            self.ds_xr = self._ds.to_xarray_dataset()

    @property
    def data(self) -> xr.Dataset:
        return self.ds_xr

    @property
    def is_complete(self) -> bool:
        ds = self._ds
        if self.ds_description.completed_time is not None:
            return True
        if ds.completed:
            self.ds_description.completed_time = datetime.fromtimestamp(ds.completed_timestamp_raw)
            return True
        if datetime.now() - datetime.fromtimestamp(ds.run_timestamp_raw) > timedelta(days=3):
            return True
        return False

    @property
    def is_modified(self) -> bool:
        return self._number_of_results != self._ds.number_of_results

    @property
    def formatted_uid(self) -> str:
        return self.ds_description.uid

    @property
    def info(self) -> list[tuple[str, str]]:
        labels = self.ds_description.labels
        start_time = self.ds_description.collected_datetime
        end_time = self.ds_description.completed_time
        duration_str = "-"
        try:
            if end_time is not None:
                duration = (end_time - start_time).total_seconds()
                if duration >= 0:
                    s = duration % 60
                    m = int(duration) // 60
                    h, m = divmod(m, 60)
                    if h > 0:
                        duration_str = f"{h}h:{m:02d}m:{int(s):02d}s"
                    elif m > 0:
                        duration_str = f"{m:2d}m:{int(s):02d}s"
                    else:
                        duration_str = f"{s:.2f}s"
        except Exception:
            logger.error("Could not get duration", exc_info=True)
            duration_str = "-"
        return [
            ("Sample", labels.get("sample")),
            ("Experiment", labels.get("experiment")),
            ("Duration", duration_str),
            ]

    @property
    def snapshot(self) -> None | str | dict[str, Any]:
        if self._snapshot is None:
            self._snapshot = self._ds.snapshot
        return self._snapshot

    def close(self):
        pass
