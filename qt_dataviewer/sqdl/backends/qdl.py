import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Self

from .base import BaseClient, BaseScope, BaseDataset, BaseFile
from .exceptions import DatasetNotFoundException

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
        resp = self.ref._api.retrieve(self.uuid)
        if resp is not None:
            return QdlDataset.from_response(resp)

    @staticmethod
    def from_response(response: v1.Dataset) -> Self:
        return QdlDataset(
            name=response.name,
            title=response.name,
            description=response.description,
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
        # in-progress: feature request with SDST for a cleaner /latest endpoint
        response = self.ref.list_datasets(limit=1)
        try:
            dataset = response.pop()
            return int(dataset.created_at.timestamp())
        except IndexError:
            return -1

    def retrieve_dataset_from_uid(self, ds_uid: str) -> QdlDataset:
        try:
            response = self.ref.retrieve_dataset(ds_uid)
        except v1.exceptions.NotFoundException as exc:
            raise DatasetNotFoundException(
                f"Dataset not found in scope: ds={ds_uid}, scope={self.name}",
                request=None,
                response=exc,
            ) from exc
        return QdlDataset.from_response(response)

    def search_dates(
        self,
        dataset_name_contains: str | None = None,
        rating: int | None = None,
        data_identifiers: dict[str, str | list[str]] | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[str]:

        kwargs = {}
        if dataset_name_contains:
            kwargs.update({"name": dataset_name_contains})

        if rating:
            kwargs.update({"rank": rating})

        if data_identifiers:
            kwargs.update(data_identifiers)

        dates = self.ref.list_dates(**kwargs)
        return [d.isoformat() for d in dates]

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

        kwargs = {
            "limit": limit,
            "offset": offset,
        }

        if min_id:
            collected_last = datetime.fromtimestamp(min_id)

            if collected_since and collected_since < collected_last:
                collected_since = collected_last

        if collected_since:
            kwargs.update({"since": collected_since})

        if collected_until:
            kwargs.update({"until": collected_until})

        if dataset_name_contains:
            kwargs.update({"name": dataset_name_contains})

        if rating:
            kwargs.update({"rank": rating})

        if data_identifiers:
            kwargs.update(data_identifiers)

        logger.info(f"Searching for datasets: filters={kwargs}")
        response = self.ref._api.list_datasets(
            scope_uid=self.ref.name,
            **kwargs,
        )
        return [QdlDataset.from_response(item) for item in response]

    def list_data_identifiers(self, limit=10, offset=0) -> dict[str, list[str]]:
        attributes = self.ref.list_attributes(
            limit=limit,
            offset=offset
        )
        return attributes

    @staticmethod
    def from_response(response: v1.Scope) -> Self:
        return QdlScope(
            name=response.name,
            description=response.description,
            ref=response,
        )


class QdlClient(BaseClient):
    def __init__(self):
        self._client = Client()

    def login(self):
        self._client.login()

    def logout(self):
        self._client.logout()

    def close(self):
        """
        Properly terminate the async runtime used by the QDL Backend library.
        """
        self._client.close()

    @property
    def user_info(self) -> dict[str, str]:
        info = self._client.user_info
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
