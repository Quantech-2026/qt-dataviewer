import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import Any

import xarray as xr

from qt_dataviewer.abstract.dataset import Dataset
from qt_dataviewer.xarray_adapters.quantify_xarray import convert_quantify
from .dataset_description import QuantifyDatasetDescription

logger = logging.getLogger(__name__)


class QuantifyDataset(Dataset):
    def __init__(self, ds_description: QuantifyDatasetDescription):
        super().__init__(ds_description)
        self._snapshot = None
        self.reload()

    def reload(self) -> None:
        self._file_modified_time = self._get_file_mtime()
        try:
            ds = self._load_ds()
            self.ds_xr = convert_quantify(ds)
        except Exception:
            logging.error(f"Failed to load {self.ds_description.uid}", exc_info=True)

    @property
    def data(self) -> xr.Dataset:
        if self.ds_xr is None:
            return xr.Dataset()
        return self.ds_xr

    @property
    def is_complete(self) -> bool:
        # TODO How can we know data is complete?
        # Assume it does not change anymore if not changed in last 10 minutes
        now = datetime.now()
        return now - self._file_modified_time > timedelta(minutes=10)

    @property
    def is_modified(self) -> bool:
        return self._file_modified_time != self._get_file_mtime()

    @property
    def formatted_uid(self) -> str:
        return self.ds_description.uid

    @property
    def info(self) -> list[tuple[str, str]]:
        if self.ds_xr is None:
            return []
        return [
            (k, str(v))
            for k, v in self.ds_xr.attrs.items()
            ]

    @property
    def snapshot(self) -> None | str | dict[str, Any]:
        if self._snapshot is None:
            try:
                self._snapshot = self._load_snapshot()
            except FileNotFoundError:
                return None
            except Exception as ex:
                print(ex)
                return None
        return self._snapshot

    def _get_file_mtime(self):
        file_path = self.ds_description.dataset_file_path
        return datetime.fromtimestamp(os.path.getmtime(file_path))

    def _load_ds(self) -> xr.Dataset:
        now = datetime.now()
        active = now - self._get_file_mtime() < timedelta(minutes=1)

        file_path = self.ds_description.dataset_file_path
        if active:
            # assume we have write permission!
            tmp_file = str(file_path)[:-5]+".qt_tmp.hdf5"
            shutil.copy(file_path, tmp_file)
            dsx = xr.load_dataset(tmp_file, engine="h5netcdf")
            os.remove(tmp_file)
            return dsx
        else:
            return xr.load_dataset(file_path, engine="h5netcdf")

    def _load_snapshot(self) -> dict[str, Any]:
        with open(os.path.join(self.ds_description.path, "snapshot.json")) as fp:
            return json.load(fp)
