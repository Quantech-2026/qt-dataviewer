from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import date


from PyQt5.QtCore import QObject
from PyQt5.QtCore import pyqtSignal as Signal

from .types import LabelsDict
from .dataset_description import DatasetDescription
from .dataset import Dataset


@dataclass
class Filter:
    name_contains: str | None = None
    collected_since: date | None = None # ??? datetime?
    collected_until: date | None = None # ??? datetime?
    rating: int | None = None
    labels: LabelsDict | None = field(default_factory=dict)


class DatasetStore(QObject):

    datasets_changed = Signal()
    dates_changed = Signal(list) # List[date]
    new_datasets = Signal(list) # List[DatasetDescription]
    """Emitted when there is new data for one of the (cached) dates"""
    labels_changed = Signal(dict)

    def __init__(self, is_dynamic):
        super().__init__()
        self._is_dynamic = is_dynamic
        self._dates: list[date] = []
        self._labels : LabelsDict = {}

    @property
    def is_dynamic(self):
        return self._is_dynamic

    @property
    def dates(self) -> list[date]:
        return self._dates

    @property
    def labels(self) -> LabelsDict:
        return self._labels

    @abstractmethod
    def set_filter(self, filter: Filter) -> None:
        raise NotImplementedError()

    def refresh(self):
        raise NotImplementedError()

    def _set_dates(self, dates: list[date]) -> None:
        if dates != self._dates:
            self._dates = dates
            self.dates_changed.emit(dates)

    def _set_labels(self, labels: LabelsDict) -> None:
        if labels != self._labels:
            self._labels = labels
            self.labels_changed.emit(labels)

    @abstractmethod
    def get_dataset_descriptions(self, date: date) -> list[DatasetDescription]:
        raise NotImplementedError()

    @abstractmethod
    def get_dataset_description_for_uid(self, uid: str) -> DatasetDescription | None:
        raise NotImplementedError()

    @abstractmethod
    def get_dataset(self, ds_description: DatasetDescription) -> Dataset:
        # TODO exceptions for data failures: file not found, no data, corrupt,
        raise NotImplementedError()

    @abstractmethod
    def set_name(self, ds_description: DatasetDescription, name: str):
        raise NotImplementedError()

    @abstractmethod
    def set_rating(self, ds_description: DatasetDescription):
        raise NotImplementedError()

    @abstractmethod
    def get_next(self, ds_description: DatasetDescription) -> DatasetDescription:
        raise NotImplementedError()

    @abstractmethod
    def get_previous(self, ds_description: DatasetDescription) -> DatasetDescription:
        raise NotImplementedError()

    @abstractmethod
    def get_latest(self) -> DatasetDescription:
        raise NotImplementedError()

    @abstractmethod
    def close(self):
        raise NotImplementedError()

    # def get_full_description(self, dataset: DatasetDescription):
    #     pass

