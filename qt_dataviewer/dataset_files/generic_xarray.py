from dataclasses import dataclass

import xarray as xr

from qt_dataviewer.abstract import DatasetDescription, Dataset
from qt_dataviewer.xarray_adapters.coretools_xarray import get_snapshot


@dataclass
class XarrayDatasetDescription(DatasetDescription):
    path: str | None = None
    ds_xr: xr.Dataset | None = None


class XarrayDataset(Dataset):
    def __init__(self, ds_description: DatasetDescription,
                 ds_xr: xr.Dataset):
        super().__init__(ds_description)
        self.ds_xr = ds_xr
        self._snapshot = None

    @property
    def data(self) -> xr.Dataset:
        return self.ds_xr

    @property
    def is_complete(self) -> bool:
        return True

    @property
    def is_modified(self) -> bool:
        return False

    def reload(self) -> None:
        pass

    @property
    def formatted_uid(self) -> str:
        return str(self.ds_description.uid)

    @property
    def info(self) -> list[tuple[str, str]]:
        return [
            (key, str(value))
            for key, value in self.ds_xr.attrs.items()
            ]

    @property
    def snapshot(self) -> None | str | dict[str, any]:
        if self._snapshot is None and self.ds_xr is not None:
            self._snapshot = get_snapshot(self.ds_xr)
        return self._snapshot

    def close(self):
        pass

