import copy
import logging
from datetime import date
from packaging.version import Version

from PyQt5.QtCore import QTimer

# TODO: Add abstraction in core-tools?
from core_tools import __version__ as ct_version
from core_tools.data.SQL.connect import SQL_conn_info_local, SQL_conn_info_remote
from core_tools.data.ds.data_set import load_by_uuid
from core_tools.data.SQL.queries.dataset_gui_queries import (
    query_for_samples,
    query_for_measurement_results,
    measurement_results)

from qt_dataviewer.abstract import (
    Dataset, DatasetDescription, DatasetStore, Filter
    )
from qt_dataviewer.utils.qt_utils import qt_log_exception
from .dataset import CoreToolsDataset

logger = logging.getLogger(__name__)


class CoreToolsDatasetStore(DatasetStore):

    def __init__(self):
        super().__init__(is_dynamic=True)

        if Version(ct_version) < Version("1.4.42"):
            raise Exception("CoreTools database browser requires core-tools >= v1.4.42")

        self._filter = Filter()
        self._project: str = None
        self._setup: str = None
        self._sample: str = None
        # Cache is used for easy next/previous lookup.
        self._ds_descriptions_cache: dict[date, list[DatasetDescription]] = {}
        # max_db_id is used to detect new measurements.
        self._db_max_id: int | None = None

        # Use single shot timer and restart timer after performing queries
        # This avoids updates being triggered faster than queries can be executed.
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self.check_for_updates)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(300)

    def get_source_name(self):
        if SQL_conn_info_local.host == 'localhost':
            return 'Local'
        if SQL_conn_info_remote.host:
            return 'Remote'
        return '---'

    def set_filter(self, filter: Filter):
        # check if project, setup or sample changed.
        old_labels = self._filter.labels
        new_labels = filter.labels
        self._filter = copy.deepcopy(filter)
        for name in ["project", "setup", "sample"]:
            if old_labels.get(name) != new_labels.get(name):
                self._project = new_labels.get("project")
                self._setup = new_labels.get("setup")
                self._sample = new_labels.get("sample")
                self._fetch_labels()
                break
        _, self._db_max_id = query_for_measurement_results.detect_new_meaurements(
                self._db_max_id,
                project=self._project,
                sample=self._sample,
                set_up=self._setup,
                )
        self.refresh()

    def refresh(self):
        self._ds_descriptions_cache = {}
        self._set_dates(self._fetch_dates())
        self._set_labels(self._fetch_labels())
        self._update_timer.start()
        self.datasets_changed.emit()

    def get_dataset_descriptions(self, date: date) -> list[DatasetDescription]:
        try:
            return self._ds_descriptions_cache[date]
        except KeyError:
            ds_descriptions = self._fetch_dataset_descriptions(date)
            self._ds_descriptions_cache[date] = ds_descriptions
            return ds_descriptions

    def get_dataset_description_for_uid(self, uid: str) -> DatasetDescription | None:
        ds = load_by_uuid(int(uid))
        s = str(ds.exp_uuid)
        uuid_str = s[:-14] + '_' + s[-14:-9] + '_' + s[-9:]
        labels = {
            "project": ds.project,
            "setup": ds.set_up,
            "sample": ds.sample_name,
            "keywords": ds.keywords,
            }
        ds_description = DatasetDescription(
            uid=uuid_str,
            name=ds.exp_name,
            collected_datetime=ds.run_timestamp,
            rating=ds.starred,
            labels=labels,
            )
        # Hack to prevent duplicate loading of dataset
        ds_description.ds_ct = ds
        return ds_description

    def _fetch_labels(self):
        return {
            "project": query_for_samples.get_projects(set_up=self._setup, sample=self._sample),
            "setup": query_for_samples.get_set_ups(project=self._project, sample=self._sample),
            "sample": query_for_samples.get_samples(project=self._project, set_up=self._setup),
            }

    def _fetch_dates(self) -> list[date]:
        starred = self._filter.rating is not None and self._filter.rating > 0
        return query_for_measurement_results.get_all_dates_with_meaurements(
                project=self._project,
                sample=self._sample,
                set_up=self._setup,
                name=self._filter.name_contains,
                starred=starred,
                keywords=self._filter.labels.get("keywords"),
                )

    def _fetch_dataset_descriptions(self, date: date):
        starred = self._filter.rating is not None and self._filter.rating > 0
        results: list[measurement_results] = query_for_measurement_results.get_results_for_date(
                date=date,
                project=self._project,
                sample=self._sample,
                set_up=self._setup,
                name=self._filter.name_contains,
                starred=starred,
                keywords=self._filter.labels.get("keywords"),
                )
        ds_descriptions = self._query_measurement2ds_descr(results)
        return ds_descriptions

    @qt_log_exception
    def get_dataset(self, ds_description: DatasetDescription) -> Dataset:
        return CoreToolsDataset(ds_description)

    @qt_log_exception
    def check_for_updates(self):
        try:
            _, max_id = query_for_measurement_results.detect_new_meaurements(
                    self._db_max_id,
                    project=self._project,
                    sample=self._sample,
                    set_up=self._setup,
                    )

            if max_id is not None and self._db_max_id is not None and max_id > self._db_max_id:
                starred = self._filter.rating is not None and self._filter.rating > 0
                results: list[measurement_results] = query_for_measurement_results.get_new_results(
                    self._db_max_id,
                    project=self._project,
                    sample=self._sample,
                    set_up=self._setup,
                    name=self._filter.name_contains,
                    starred=starred,
                    keywords=self._filter.labels.get("keywords"),
                    )
                new_ds_descriptions = self._query_measurement2ds_descr(results)
                if new_ds_descriptions:
                    self._emit_updates(new_ds_descriptions)
            self._db_max_id = max_id
        finally:
            # restart timer.
            self._update_timer.start()

    @staticmethod
    def _query_measurement2ds_descr(query_results: list[measurement_results]) -> list[DatasetDescription]:
        ds_descriptions = []
        for r in query_results:
            labels = {
                "project": r.project,
                "setup": r.set_up,
                "sample": r.sample,
                "keywords": r._keywords,
                }
            s = str(r.uuid)
            uuid_str = s[:-14] + '_' + s[-14:-9] + '_' + s[-9:]

            ds = DatasetDescription(
                uid=uuid_str,
                name=r.name,
                collected_datetime=r.start_time,
                rating=r.starred,
                labels=labels,
                )
            ds_descriptions.append(ds)
        ds_descriptions.sort(key=lambda ds: ds.collected_datetime, reverse=True)
        return ds_descriptions

    def _emit_updates(self, new_ds_descriptions: list[DatasetDescription]):
        update_dates = False
        for ds in new_ds_descriptions:
            if ds.collected_date in self._ds_descriptions_cache:
                del self._ds_descriptions_cache[ds.collected_date]
            if ds.collected_date not in self._dates:
                update_dates = True
            # for label, value in ds.labels.items():
            #     try:
            #         values = self._labels[label]
            #     except KeyError:
            #         self._labels[label] = [value]
            #     else:
            #         if value not in values:
            #             self._labels[label] = sorted(values + [value])
            #     # TODO emit label change ??
            if update_dates:
                self._set_dates(self._fetch_dates())
        self.new_datasets.emit(new_ds_descriptions)

    # TODO
    def set_name(self, ds_description: DatasetDescription, name: str):
        raise NotImplementedError()

    # TODO
    def set_rating(self, ds_description: DatasetDescription):
        raise NotImplementedError()

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
        dds = self.get_dataset_descriptions(self.dates[0])
        if not dds:
            raise StopIteration('No datasets') from None
        return dds[0]

    def _index(self, ds_description: DatasetDescription, ds_descriptions: list[DatasetDescription]):
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

