from datetime import datetime, timedelta
import logging

import xarray as xr

from qt_dataviewer.abstract.dataset_description import DatasetDescription
from qt_dataviewer.abstract.dataset import Dataset
from qt_dataviewer.xarray_adapters.quantify_xarray import convert_quantify


logger = logging.getLogger(__name__)


class QuantifyDataset(Dataset):
    def __init__(self, ds_description: DatasetDescription):
        super().__init__(ds_description)
        self._snapshot = None
        self._dp = ds_description.path # This is a bit ugly.
        self.reload()

    def reload(self) -> None:
        self._file_modified_time = self._dp.get_file_mtime()
        try:
            ds = self._dp.load_ds()
            self.ds_xr = convert_quantify(ds)
        except:
            logging.error(f"Failed to load {self._dp.tuid}", exc_info=True)

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
        return self._file_modified_time != self._dp.get_file_mtime()

    @property
    def formatted_uid(self) -> str:
        return self.ds_description.uid

    @property
    def info(self) -> dict[str, str]:
        if self.ds_xr is None:
            return []
        return [
            (k, str(v))
            for k, v in self.ds_xr.attrs.items()
            ]

    @property
    def snapshot(self) -> None | str | dict[str, any]:
        if self._snapshot is None:
            try:
                self._snapshot = self._dp.load_snapshot()
            except FileNotFoundError:
                return None
            except Exception as ex:
                print(ex)
                return None
        return self._snapshot
