import copy
import logging
import os
from collections import defaultdict
from datetime import date as dt_date, datetime

from qtpy import QtCore

from qt_dataviewer.abstract import (
    Dataset, DatasetDescription, DatasetStore, Filter, LabelsDict
    )
from qt_dataviewer.utils.qt_utils import qt_log_exception

from .dataset import QuantifyDataset
from .dataset_description import QuantifyDatasetDescription


logger = logging.getLogger(__name__)


class QuantifyDatasetStore(DatasetStore):

    def __init__(self, check_datasets: bool = False):
        super().__init__(is_dynamic=True)

        self._base_dir = None
        self._filter = Filter()
        self._ds_descriptions: dict[dt_date, list[DatasetDescription]] = {}
        self._filtered_ds_descriptions: dict[dt_date, list[DatasetDescription]] = {}
        self._all_ds_paths = set()
        self._ds_descriptions_changed = False
        self._auto_scan = False
        self._check_datasets = check_datasets
        self._update_timer = QtCore.QTimer(self)
        self._update_timer.timeout.connect(self._check_for_updates)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(300)

    def open_dir(self, path):
        self._base_dir = path
        self.refresh()
        if self._auto_scan:
            self._update_timer.start()

    @property
    def source_name(self):
        return self._base_dir

    def set_filter(self, filter: Filter):
        self._filter = copy.deepcopy(filter)
        self._apply_filter()

    def refresh(self):
        self._ds_descriptions = defaultdict(list)
        self._all_ds_paths = set()
        self._scan_dirs()
        self._apply_filter()
        self._set_labels(self._get_labels())
        self.datasets_changed.emit()

    def enable_auto_scan(self, enable: bool):
        self._auto_scan = enable
        if enable and self._base_dir:
            self._update_timer.start()
        else:
            self._update_timer.stop()

    def _check_for_updates(self):
        if not self._base_dir:
            return
        try:
            today = datetime.now().date()
            today_path = os.path.join(self._base_dir, f"{today:%Y%m%d}")
            if not os.path.exists(today_path):
                return
            self._ds_descriptions_changed = False
            self._scan_date_dir(today, today_path)
            if self._ds_descriptions_changed:
                self._ds_descriptions_changed = False
                old_list = self._filtered_ds_descriptions.get(today, []).copy()
                self._apply_filter()
                new_list = self._filtered_ds_descriptions.get(today, [])
                new_ds_descriptions = []
                for ds in new_list:
                    if ds not in old_list:
                        new_ds_descriptions.append(ds)
                if new_ds_descriptions:
                    self.new_datasets.emit(new_ds_descriptions)
        finally:
            self._update_timer.start()

    @qt_log_exception
    def _scan_dirs(self):
        if self._base_dir:
            for entry in os.scandir(self._base_dir):
                if entry.is_dir():
                    try:
                        date = datetime.strptime(entry.name, "%Y%m%d").date()
                    except ValueError:
                        continue
                    else:
                        self._scan_date_dir(date, entry.path)

    def _scan_date_dir(self, date: dt_date, path):
        for entry in os.scandir(path):
            if entry.path in self._all_ds_paths:
                continue
            if entry.is_dir():
                try:
                    ds_description = QuantifyDatasetDescription(entry.name, entry.path, self._check_datasets)
                except Exception:
                    continue
                self._ds_descriptions[date].append(ds_description)
                self._ds_descriptions_changed = True
                self._all_ds_paths.add(entry.path)
        if date in self._ds_descriptions:
            self._ds_descriptions[date].sort(key=lambda dd: dd.collected_datetime, reverse=True)

    def _apply_filter(self):
        filt = self._filter
        self._filtered_ds_descriptions = defaultdict(list)

        for ds_date, entries in self._ds_descriptions.items():
            for ds_description in entries:
                if filt.name_contains and filt.name_contains.lower() not in ds_description.name.lower():
                    continue
                # TODO apply other filters
                self._filtered_ds_descriptions[ds_date].append(ds_description)
        dates = sorted(self._filtered_ds_descriptions.keys(), reverse=True)
        self._set_dates(dates)

    def _get_labels(self) -> LabelsDict:
        # TODO @@@
        return {}

    def get_dataset_descriptions(self, date: dt_date) -> list[DatasetDescription]:
        return self._filtered_ds_descriptions.get(date, [])

    def get_dataset_description_for_uid(self, uid: str) -> DatasetDescription | None:
        tuid = uid
        if len(tuid) < 26:
            # TODO @@@ Show error in GUI
            raise Exception(f"'{tuid}' is too short for valid TUID")
        date = dt_date.strptime(tuid[:8], "%Y%m%d")
        if date not in self._ds_descriptions:
            return None
        for dsd in self._ds_descriptions[date]:
            if dsd.uid == tuid:
                return dsd
        return None

    @qt_log_exception
    def get_dataset(self, ds_description: DatasetDescription) -> Dataset:
        return QuantifyDataset(ds_description)

    # TODO
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

    def set_name(self, ds_description: DatasetDescription, name: str):
        raise NotImplementedError("Cannot change name on Quantify")

    def set_rating(self, ds_description: DatasetDescription, rating: int):
        # Cannot set rating
        raise NotImplementedError("Cannot set rating on Quantify")

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
        last_date = max(self.dates)
        dds = self.get_dataset_descriptions(last_date)
        if not len(dds):
            raise StopIteration('No datasets') from None
        last_ds_description = dds[0]
        return last_ds_description

    def _index(self, ds_description: DatasetDescription, ds_descriptions: list[DatasetDescription]):
        for i, ds in enumerate(ds_descriptions):
            if ds.uid == ds_description.uid:
                return i
        else:
            raise StopIteration('Dataset not in current selection anymore')

    def close(self):
        self._update_timer.stop()
