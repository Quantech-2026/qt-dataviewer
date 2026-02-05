import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Self

from .base import BaseClient, BaseScope, BaseDataset, BaseFile

import requests
from qdl_client import QDLClient as Client
from qdl_client.api import v1
from qdl_client.exceptions import InvallidHashException, MissingDataException


logger = logging.getLogger(__name__)


@dataclass
class QdlFile(BaseFile):
    ref: v1.File

    def download(self, session: requests.Session | None = None) -> bytes | None:
        try:
            file, content = self.ref._api.download(
                self.ref.uuid,
                session=session,
            )
        except (InvallidHashException, MissingDataException) as exc:
            logger.error(exc)
            return None

        return content

    @staticmethod
    def from_response(response: v1.File) -> Self:
        return QdlFile(
            name=response.name,
            md5_sum=response.md5_sum,
            presigned_url=response.presigned_url,
            has_data=response.has_data,
            is_mutable=response.is_mutable,
            ref=response
        )


@dataclass
class QdlDataset(BaseDataset):
    ref: v1.Dataset

    @property
    def files(self) -> list[QdlFile]:
        response = self.ref.files
        return [QdlFile.from_response(item) for item in response]

    def update_rating(self, rating: int):
        self.ref.update_rank(rating)

    def refresh(self) -> Self | None:
        resp = self.ref.refresh()
        if resp is not None:
            return QdlDataset.from_response(resp)

    @staticmethod
    def from_response(response: v1.Dataset) -> Self:
        logger.debug(f"QDL DATASET >>> FROM RESPONSE: {response}")
        return QdlDataset(
            name=response.name,
            title=response.name,  # todo: get title from qdl?
            description=response.name,  # todo: get description from qdl
            uid=response.uid,
            uuid=response.uuid,
            rating=response.rank,
            date_collected=response.collected_at,
            metadata=response.attributes,
            ref=response
        )


@dataclass
class QdlScope(BaseScope):
    ref: v1.Scope

    def get_max_dataset_id(self) -> int:
        response = self.ref._api.list_dataset(scope_uid=self.ref.name, limit=1)
        try:
            dataset = response.pop()
            # todo: warning - "collected at" technically doesn't say anything about
            #  when the data was uploaded, so we need a better metric (which exists
            #  on QDL, but not on the client)
            return int(dataset.collected_at.timestamp())
        except IndexError:
            return -1

    def retrieve_dataset_from_uid(self, ds_uid: str) -> QdlDataset:
        response = self.ref.retrieve_dataset(ds_uid)
        return QdlDataset.from_response(response)

    def search_dates(
        self,
        dataset_name_contains: str | None = None,
        rating: int | None = None,
        data_identifiers: dict[str, str | list[str]] | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[str]:
        # todo: update qdl-client to handle keyword arguments
        return [d.isoformat() for d in self.ref.list_dates()]

    def search_datasets(
        self,
        min_id: int | None = None,
        collected_since: date | None = None,
        collected_until: date | None = None,
        dataset_name_contains: str | None = None,
        rating: int | None = None,
        data_identifiers: dict[str, str | list[str]] | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[QdlDataset]:
        # todo: figure out how to transpose dataviever kwargs to qdl kwargs
        response = self.ref._api.list_dataset(scope_uid=self.ref.name)
        return [QdlDataset.from_response(item) for item in response]

    def list_data_identifiers(self, limit=10, offset=0) -> Any:
        logger.warning("Data identifiers not yet implemented for QDL")
        return []

    @staticmethod
    def from_response(response: v1.Scope) -> Self:
        return QdlScope(
            name=response.name,
            description=response.name,  # todo: scope description from qdl
            ref=response,
        )


class QdlClient(BaseClient):
    def __init__(self):
        self._client = Client()

    def login(self):
        self._client.login()

    def logout(self):
        self._client.logout()

    @property
    def user_info(self) -> dict[str, str]:
        info = self._client.user_info
        logger.debug(f"qdl user info: {info}")
        return {
            "name": info.name,
            "role": info.role,
            "email": info.email
        }

    def list_scopes(self) -> list[QdlScope]:
        resp = self._client.api.scope.list()
        return [QdlScope.from_response(r) for r in resp]

    def retrieve_scope_from_name(self, scope_name: str) -> QdlScope:
        resp = self._client.api.scope.retrieve(scope_name)
        return QdlScope.from_response(resp)
