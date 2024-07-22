from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, Union

import xarray as xr

from .dataset_description import DatasetDescription


class Dataset:
    def __init__(self, ds_description: DatasetDescription):
        self.ds_description = ds_description

    @property
    @abstractmethod
    def data(self) -> xr.Dataset:
        raise NotImplementedError()

    @property
    @abstractmethod
    def is_complete(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def reload(self) -> None:
        raise NotImplementedError()

    @property
    def collected_datetime(self) -> datetime:
        return self.ds_description.collected_datetime

    @property
    def name(self) -> str:
        return self.ds_description.name

    @property
    @abstractmethod
    def formatted_uid(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def info(self) -> Dict[str, str]:
        raise NotImplementedError()

    @property
    @abstractmethod
    def snapshot(self) -> Union[None, str, Dict[str, Any]]:
        raise NotImplementedError()

    def close(self):
        pass

    # @@@ Add views / charts / plots / figures
