import os
import copy
import logging
import time
from collections import defaultdict
from datetime import date, timedelta

import requests
from qtpy.QtCore import QTimer

from qt_dataviewer.abstract import (
    Dataset, DatasetDescription, DatasetStore, Filter
)
from qt_dataviewer.utils.qt_utils import (
    qt_log_exception, qt_show_exception, qt_show_error
)
from .dataset import SqdlDataset
from .backends.base import DatasetDescriptionWithReference
from .backends.factory import ClientFactory
from .backends.exceptions import DatasetNotFoundException


logger = logging.getLogger(__name__)


class SqdlDatasetStore(DatasetStore):

    def __init__(self, ):
        super().__init__(is_dynamic=True)
        logger.debug("Starting SQDL DatasetStore")
        self.scope_name = None
        self.scope = None
        self._init_scope()

        backend_type = os.environ.get("QDL_TEST", "sqdl")  # note: testing solution
        self._client = ClientFactory.create_client(backend_type)
        self._client.login()

        try:
            info = self._client.user_info
            logger.debug(f"user info: {info}")
            self.user_name = info.get("name")  # todo: verify that qdl shares key
        except Exception as exc:
            self.user_name = None
            logger.error(exc)
        self.s3_session = requests.Session()

        # Use single shot timer and restart timer after performing queries
        # This avoids updates being triggered faster than queries can be executed.
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._check_for_updates)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(300)

    def logout(self):
        # This will automatically trigger a new login
        self._client.logout()

    def set_scope(self, scope_name):
        self.scope_name = scope_name
        if scope_name:
            try:
                self.scope = self._client.retrieve_scope_from_name(scope_name)
            except Exception as ex:
                qt_show_exception(
                    "Failure retrieving scope",
                    ex,
                    extra_line=f"Are you authorized for scope '{scope_name}'?"
                )
                self.scope = None
                self.scope_name = None
        else:
            self.scope = None
        self._init_scope()
        if self.scope is None:
            self._update_timer.stop()
        else:
            self._update_timer.start()
        self.refresh()

    def get_scopes(self):
        try:
            sqdl_scopes = self._client.list_scopes()
            if not sqdl_scopes:
                qt_show_error(
                    "No scopes found",
                    "No scopes found. Ask administrator to assign scopes."
                )
        except Exception as ex:
            qt_show_exception("Failure retrieving scopes", ex)
            return []
        return sorted(scope.name for scope in sqdl_scopes)  # todo-marker

    def _init_scope(self):
        self._filter = Filter()
        # Cache is used for easy next/previous lookup.
        self._ds_descriptions_cache: dict[date, list[DatasetDescription]] = {}
        # max_dataset_id is used to detect new measurements.
        self._max_dataset_id: int = -1

    @property
    def source_name(self):
        return self.scope_name or "<select scope>"

    def set_filter(self, filter: Filter):
        if self.scope is None:
            return
        self._filter = copy.deepcopy(filter)
        self.refresh()

    def refresh(self):
        if self.scope is None:
            return
        logger.debug("Refresh")
        try:
            self._max_dataset_id = self.scope.get_max_dataset_id()
            self._ds_descriptions_cache = {}
            self._set_dates(self._fetch_dates())
            self._set_labels(self._fetch_labels())
            self.datasets_changed.emit()
        except Exception as ex:
            qt_show_exception("Failure loading datasets", ex)

    def get_dataset_descriptions(self, date: date) -> list[DatasetDescription]:
        try:
            return self._ds_descriptions_cache[date]
        except KeyError:
            try:
                ds_descriptions = self._fetch_dataset_descriptions(date)
            except Exception as ex:
                qt_show_exception("Failure loading datasets", ex)
                return []

            self._ds_descriptions_cache[date] = ds_descriptions
            return ds_descriptions

    @qt_log_exception
    def get_dataset_description_for_uid(self, uid: str) -> DatasetDescription | None:
        try:
            # try to remove "_" from input
            logger.debug(f"examples - stripping underscope from: '{uid}'")
            # why not s.replace("_", "")?
            uid_value = int(uid)
            uid = str(uid_value)
        except Exception:
            pass
        try:

            ds = self.scope.retrieve_dataset_from_uid(uid)
        except DatasetNotFoundException:
            return None
        except Exception as ex:
            # TODO @@@ Consistent exception handling: Now gives 2 message boxes: HTTP Error and Dataset not found
            qt_show_exception("Failure loading dataset", ex)
            return None

        ds_description = DatasetDescriptionWithReference(
            ds.uid,
            ds.name,
            ds.date_collected,
            rating=ds.rating,
            labels=ds.metadata,
            dataset_reference=ds
        )

        return ds_description

    def _fetch_labels(self):
        if self.scope is None:
            return {}
        data_identifiers = self.scope.list_data_identifiers(limit=1000)

        di_dict = defaultdict(list)
        for di in data_identifiers:
            di_dict[di.key].append(di.value)

        return di_dict.copy()

    def _fetch_dates(self) -> list[date]:
        if self.scope is None:
            return []

        t0 = time.perf_counter()
        data_identifiers = {}
        for name in self._labels:
            value = self._filter.labels.get(name)
            if value is not None:
                data_identifiers[name] = value

        filter_rating = self._filter.rating
        if filter_rating is None:
            filter_rating = 0

        dates = [
            date.fromisoformat(d)
            for d
            in self.scope.search_dates(
                dataset_name_contains=self._filter.name_contains,
                rating=filter_rating,
                data_identifiers=data_identifiers,
                limit=1000,
            )
        ]
        t1 = time.perf_counter()
        logger.debug(f"Fetch dates in {(t1-t0):.3f} s")
        return dates

    def _fetch_dataset_descriptions(self, date: date):
        if self.scope is None:
            return []

        data_identifiers = {}
        for name in self._labels:
            value = self._filter.labels.get(name)
            if value is not None:
                data_identifiers[name] = value

        ds_descriptions = []
        t0 = time.perf_counter()
        filter_rating = self._filter.rating
        if filter_rating is None:
            filter_rating = 0
        datasets = self.scope.search_datasets(
            collected_since=date.isoformat(),
            collected_until=(date+timedelta(1)).isoformat(),
            dataset_name_contains=self._filter.name_contains,
            rating=filter_rating,
            data_identifiers=data_identifiers,
            limit=1000,
        )
        for ds in datasets:
            ds_description = DatasetDescriptionWithReference(
                ds.uid,
                ds.name,
                ds.date_collected,
                rating=ds.rating,
                labels=ds.metadata,
                dataset_reference=ds
            )
            ds_descriptions.append(ds_description)
        t1 = time.perf_counter()
        logger.debug(f"Fetched {len(ds_descriptions)} in {(t1-t0):.3f} s")
        ds_descriptions.sort(key=lambda ds: ds.collected_datetime, reverse=True)
        return ds_descriptions

    @qt_log_exception
    def get_dataset(self, ds_description: DatasetDescription) -> Dataset:
        # todo: figure out better name for duplicates
        return SqdlDataset(ds_description, self.s3_session)

    @qt_log_exception
    def _check_for_updates(self):
        if self.scope is None:
            return
        try:
            t0 = time.perf_counter()
            max_dataset_id = self.scope.get_max_dataset_id()
            if max_dataset_id > self._max_dataset_id:
                t1 = time.perf_counter()
                data_identifiers = {}
                for name in self._labels:
                    value = self._filter.labels.get(name)
                    if value is not None:
                        data_identifiers[name] = value

                if self.dates:
                    last_date = max(self.dates)
                    current_ds_uids = [
                        dsd.uid
                        for dsd
                        in self.get_dataset_descriptions(last_date)
                    ]
                else:
                    last_date = date(2020, 1, 1)
                    current_ds_uids = []

                filter_rating = self._filter.rating
                if filter_rating is None:
                    filter_rating = 0

                new_datasets = list(self.scope.search_datasets(
                    dataset_name_contains=self._filter.name_contains,
                    rating=filter_rating,
                    min_id=self._max_dataset_id,
                    data_identifiers=data_identifiers,
                    limit=1000,
                ))

                t2 = time.perf_counter()
                new_ds_descriptions = []
                for ds in new_datasets:
                    if ds.uid in current_ds_uids:
                        continue

                    ds_description = DatasetDescriptionWithReference(
                        ds.uid,
                        ds.name,
                        ds.date_collected,
                        rating=ds.rating,
                        labels=ds.metadata,
                        dataset_reference=ds,
                    )

                    logger.debug(f"New ds {ds_description.uid} {ds.date_collected}")
                    new_ds_descriptions.append(ds_description)

                t3 = time.perf_counter()
                logger.debug(
                    f"Update {len(new_datasets)} {len(new_ds_descriptions)} in "
                    f"{(t1-t0):.3f} s, {(t2-t1):.3f} s, {(t3-t2):.3f} s"
                )

                new_ds_descriptions = new_ds_descriptions.copy()
                if new_ds_descriptions:
                    self._emit_updates(new_ds_descriptions)

            self._max_dataset_id = max_dataset_id
        except Exception as ex:
            # @@@ TODO: distinguish requests.exceptions.Timeout (warning+message), ConnectionError (warning+message), RequestException(error)
            qt_show_exception("Auto update failed", ex)

        # restart timer.
        self._update_timer.start()

    def _emit_updates(self, new_ds_descriptions: list[DatasetDescription]):
        update_dates = False
        for ds in new_ds_descriptions:
            if ds.collected_date in self._ds_descriptions_cache:
                del self._ds_descriptions_cache[ds.collected_date]

            if ds.collected_date not in self._dates:
                update_dates = True

            # # TODO only if in schema..
            # for label, new_values in ds.labels.items():
            #     try:
            #         old_values = self._labels[label]
            #         print(old_values, new_values)
            #     except KeyError:
            #         self._labels[label] = new_values
            #     else:
            #         values = old_values.copy()
            #         for value in new_values:
            #             if value not in values:
            #                 values.append(value)
            #         self._labels[label] = sorted(values)
            #     # TODO emit label change ??

        if update_dates:
            self._set_dates(self._fetch_dates())
        self.new_datasets.emit(new_ds_descriptions)

# TODO
    def set_name(self, ds_description: DatasetDescription, name: str):
        raise NotImplementedError()

    @qt_log_exception
    def set_rating(self, ds_description: DatasetDescription, rating: int):
        sqdl_ds = ds_description.sqdl_ds
        if rating != sqdl_ds.rating:
            sqdl_ds.update_rating(rating)

# TODO @@@ @Exception
    def get_next(self, ds_description: DatasetDescription) -> DatasetDescription:
        date = ds_description.collected_date
        dds = self.get_dataset_descriptions(date)
        i = self._index(ds_description, dds)

        # list is sorted on date DESCENDING
        if i > 0:
            return dds[i-1]
        else:
            index = self._dates.index(date)
            if index > 0:
                dds = self.get_dataset_descriptions(self._dates[index-1])
                return dds[-1]
            else:
                raise StopIteration('No more datasets') from None

# TODO @@@ @Exception
    def get_previous(self, ds_description: DatasetDescription) -> DatasetDescription:
        date = ds_description.collected_date
        dds = self.get_dataset_descriptions(date)
        i = self._index(ds_description, dds)

        # list is sorted on date DESCENDING
        if i < len(dds) - 1:
            return dds[i+1]
        else:
            index = self._dates.index(date)
            if index < len(self._dates) - 1:
                dds = self.get_dataset_descriptions(self._dates[index+1])
                return dds[0]
            else:
                raise StopIteration('No more datasets') from None

    def get_latest(self) -> DatasetDescription:
        if not self.dates:
            raise StopIteration('No datasets') from None
        last_date = max(self.dates)
        dds = self.get_dataset_descriptions(last_date)
        if not len(dds):
            raise StopIteration('No datasets') from None
        last_ds_description = dds[0]
        return last_ds_description

    def _index(
            self,
            ds_description: DatasetDescription,
            ds_descriptions: list[DatasetDescription]
    ):
        for i, ds in enumerate(ds_descriptions):
            if ds.uid == ds_description.uid:
                return i
        else:
            raise StopIteration('Dataset not in current selection anymore')

    def close(self):
        self._update_timer.stop()

    # add caching of files? Only if completed.
    # .qt_viewer/cache/cache.db; files
    # uuid, last_accessed, size, write_cursors:dict[id,cursor]
