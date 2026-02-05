import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Self

from .base import BaseClient, BaseScope, BaseDataset, BaseFile
from .exceptions import DatasetNotFoundException

import requests
from sqdl_client.client import QDLClient as Client
from sqdl_client.api import v1
from sqdl_client.exceptions import ObjectNotFoundException


logger = logging.getLogger(__name__)


@dataclass
class SqdlFile(BaseFile):

    def download(self, session: requests.Session | None = None) -> bytes | None:
        if session is not None:
            response = session.get(url=self.presigned_url)
        else:
            response = requests.get(url=self.presigned_url)

        response.raise_for_status()
        return response.content

    @staticmethod
    def from_response(response: v1.file.File) -> Self:
        return SqdlFile(
            name=response.name,
            md5_sum=response.md5_sum,
            presigned_url=response.presigned_url,
            has_data=response.has_data,
            is_mutable=response.is_mutable
        )


@dataclass
class SqdlDataset(BaseDataset):
    ref: v1.dataset.Dataset

    @property
    def files(self) -> list[SqdlFile]:
        response = self.ref.files
        return [SqdlFile.from_response(item) for item in response]

    def update_rating(self, rating: int):
        self.ref.update_rating(rating)

    def refresh(self) -> Self | None:
        resp = self.ref.refresh()
        if resp is not None:
            return SqdlDataset.from_response(resp)

    @staticmethod
    def from_response(response: v1.dataset.Dataset) -> Self:
        return SqdlDataset(
            name=response.name,
            title=response.title,
            description=response.description,
            uid=response.uid,
            uuid=response.uuid,
            rating=response.rating,
            date_collected=response.date_collected,
            metadata=response.metadata,
            ref=response
        )


@dataclass
class SqdlScope(BaseScope):
    ref: v1.scope.Scope

    def get_max_dataset_id(self) -> int:
        return self.ref.get_max_dataset_id()

    def retrieve_dataset_from_uid(self, ds_uid: str) -> SqdlDataset:
        try:
            resp = self.ref.retrieve_dataset_from_uid(ds_uid)
        except ObjectNotFoundException as exc:
            raise DatasetNotFoundException(
                f"Dataset not found in scope: ds={ds_uid}, scope={self.name}",
                request=exc.request,
                response=exc.response,
            ) from exc

        return SqdlDataset.from_response(resp)

    def search_dates(
        self,
        dataset_name_contains: str | None = None,
        rating: int | None = None,
        data_identifiers: dict[str, str | list[str]] | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[str]:
        return self.ref.search_dates(
            dataset_name_contains=dataset_name_contains,
            rating=rating,
            data_identifiers=data_identifiers,
            limit=limit,
            offset=offset,
        )

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
    ) -> list[SqdlDataset]:
        """

        """
        response = self.ref.search_datasets(
            min_id=min_id,
            collected_since=collected_since,
            collected_until=collected_until,
            dataset_name_contains=dataset_name_contains,
            rating=rating,
            data_identifiers=data_identifiers,
            limit=limit,
            offset=offset,
        )
        return [SqdlDataset.from_response(item) for item in response]

    def list_data_identifiers(self, limit=10, offset=0) -> Any:
        # returns non-descript "PaginatedResponse"
        identifiers = self.ref.list_data_identifiers(limit=limit, offset=offset)
        logger.debug(f"Received data identifiers from SQDL backend: {identifiers}")
        return identifiers

    @staticmethod
    def from_response(response: v1.scope.Scope) -> Self:
        return SqdlScope(
            name=response.name,
            description=response.description,
            ref=response,
        )


class SqdlClient(BaseClient):
    def __init__(self):
        self._client = Client()

    def login(self):
        self._client.login()

    def logout(self):
        self._client.logout()

    @property
    def user_info(self) -> dict[str, str]:
        return self._client.user_info

    def list_scopes(self) -> list[SqdlScope]:
        resp = self._client.api.scope.list()
        return [SqdlScope.from_response(r) for r in resp]

    def retrieve_scope_from_name(self, scope_name: str) -> SqdlScope:
        resp = self._client.api.scope.retrieve_from_name(scope_name)
        return SqdlScope.from_response(resp)
