from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Union
from collections.abc import Iterable

import xarray as xr

from PyQt5.QtCore import QObject
from PyQt5.QtCore import pyqtSignal as Signal

from .types import LabelsDict
from .dataset_description import DatasetDescription


@dataclass
class Filter:
    name_contains: Optional[str] = None
    collected_since: Optional[date] = None # ??? datetime?
    collected_until: Optional[date] = None # ???
    rating: Optional[int] = None
    labels: Optional[LabelsDict] = field(default_factory=dict)


class DatasetStore(QObject):

    dates_changed = Signal(list) # List[date]
    new_datasets = Signal(list) # List[DatasetDescription]
    """Emitted when there is new data for one of the (cached) dates"""

    def __init__(self, is_dynamic):
        super().__init__()
        self._is_dynamic = is_dynamic
        self._dates: List[date] = []

    @property
    def is_dynamic(self):
        return self._is_dynamic

    @property
    def dates(self) -> List[date]:
        return self._dates

    @abstractmethod
    def get_labels(self) -> LabelsDict:
        return {}

    @abstractmethod
    def set_filter(self, filter: Filter) -> None:
        raise NotImplementedError()

    @abstractmethod
    def refresh(self):
        raise NotImplementedError()

    def _set_dates(self, dates: List[date]):
        if dates != self._dates:
            self._dates = dates
            self.dates_changed.emit(dates)

    @abstractmethod
    def get_dataset_descriptions(self, date: date) -> List[DatasetDescription]:
        raise NotImplementedError()

    @abstractmethod
    def get_dataset(self, ds_description: DatasetDescription) -> xr.Dataset:
        # TODO exceptions for data failures: file not found, no data, corrupt,
        raise NotImplementedError()

    @abstractmethod
    def set_name(self, ds_description: DatasetDescription, name: str): # TODO UID or ds_descr
        raise NotImplementedError()

    @abstractmethod
    def set_rating(self, ds_description: DatasetDescription):
        raise NotImplementedError()

    @abstractmethod
    def get_next(self, ds_description: DatasetDescription) -> DatasetDescription:
        pass

    @abstractmethod
    def get_previous(self, ds_description: DatasetDescription) -> DatasetDescription:
        pass

    # def get_full_description(self, dataset: DatasetDescription):
    #     pass

