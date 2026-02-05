from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Self, Any

from qt_dataviewer.abstract.dataset_description import DatasetDescription


@dataclass
class BaseFile(ABC):
    name: str
    md5_sum: str
    presigned_url: str
    has_data: bool
    is_mutable: bool


@dataclass
class BaseDataset(ABC):
    name: str
    title: str
    description: str
    rating: int
    uid: str
    uuid: str
    metadata: dict[str, Any]
    date_collected: datetime

    @property
    @abstractmethod
    def files(self) -> list[BaseFile]:
        pass

    @abstractmethod
    def update_rating(self, rating: int):
        pass

    @abstractmethod
    def refresh(self) -> Self | None:
        pass


@dataclass
class DatasetDescriptionWithReference(DatasetDescription):
    # note: must all be arguments with defaults, because of how the __init__ method
    #  is composed for dataclass inheritance.
    dataset_reference: BaseDataset | None = None

    def refresh(self):
        ds = self.dataset_reference.refresh()

        # todo: do we also update all the dataclass attributes?
        # self.uid = ds.uid,
        # self.name = ds.name,
        # self.date_collected = ds.date_collected,
        # self.rating = ds.rating,
        # self.labels = ds.metadata,

        self.dataset_reference = ds


@dataclass
class BaseScope(ABC):
    name: str
    description: str

    @abstractmethod
    def retrieve_dataset_from_uid(self, ds_uid: str) -> BaseDataset:
        pass

    @abstractmethod
    def search_dates(
        self,
        dataset_name_contains: str | None = None,
        rating: int | None = None,
        data_identifiers: dict[str, str | list[str]] | None = None,
        limit: int = 1000,
    ) -> list[date]:
        pass

    @abstractmethod
    def search_datasets(
        self,
        min_id: int | None = None,
        collected_since: date | None = None,
        collected_until: date | None = None,
        dataset_name_contains: str | None = None,
        rating: int | None = None,
        data_identifiers: dict[str, str | list[str]] | None = None,
        limit: int = 1000,
    ) -> list[BaseDataset]:
        pass

    @abstractmethod
    def list_data_identifiers(self, limit: int = 1000):
        pass

    @staticmethod
    @abstractmethod
    def from_response(response: Any) -> Self:
        pass


class BaseClient(ABC):
    """
    Abstract Base Class for all (S)QDL Client related backend interactions.
    """

    @abstractmethod
    def login(self):
        pass

    @abstractmethod
    def logout(self):
        pass

    @property
    @abstractmethod
    def user_info(self) -> dict[str, str]:
        pass

    @abstractmethod
    def list_scopes(self):
        pass

    @abstractmethod
    def retrieve_scope_from_name(self, scope_name: str) -> BaseScope:
        pass
