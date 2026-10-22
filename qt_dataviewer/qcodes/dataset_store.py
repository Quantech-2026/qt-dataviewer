import copy
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime

from qtpy.QtCore import QTimer
from qcodes.dataset import (
    connect,
    experiments,
    load_by_counter,
    load_experiment,
)
from qcodes.dataset.experiment_container import Experiment

from qt_dataviewer.abstract import (
    Dataset, DatasetDescription, DatasetStore, Filter
    )
from qt_dataviewer.utils.qt_utils import qt_log_exception
from .dataset import QCoDeSDataset
from .dataset_description import QCoDeSDatasetDescription

logger = logging.getLogger(__name__)


class QCoDeSDatasetStore(DatasetStore):

    def __init__(self, db_path: str): # @@@ str | Path | PathLike
        super().__init__(is_dynamic=False)

        self._db_path = db_path
        self._db_conn = None
        self._db_conn_path: str = None
        self._filter = Filter()
        self._sample: str = None
        self._experiment: str = None

        # experiments and ds descriptions from current database.
        self._experiments: list[ExperimentInMem] = []
        # Filtered is used for easy next/previous lookup.
        self._filtered_ds_descriptions: dict[date, list[DatasetDescription]] = defaultdict(list)

        # Use single shot timer and restart timer after performing queries
        # This avoids updates being triggered faster than queries can be executed.
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self.check_for_updates)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(300)

    @property
    def source_name(self):
        if self._db_path is None:
            return '---'
        else:
            return self._db_path

    @property
    def db_path(self):
        return self._db_path

    @db_path.setter
    def db_path(self, db_path):
        self._db_path = db_path

    def set_filter(self, filter: Filter):
        new_labels = filter.labels
        self._filter = copy.deepcopy(filter)
        self._sample = new_labels.get("sample")
        self._experiment = new_labels.get("experiment")
        self._apply_filter()

    def refresh(self):
        if self._db_path is None:
            return

        # @@@ try/except
        db_path = os.path.expanduser(self._db_path)

        # @@@ Open database. Print exception.
        # The datasets in open viewers use the connection: closed only for another database.
        if self._db_conn is not None and db_path != self._db_conn_path:
            self._db_conn.close()
            self._db_conn = None

        # @@@ clear dates, labels, ...
        self._experiments = []

        if self._db_conn is None:
            self._db_conn = connect(db_path, version=5, read_only=True)
            self._db_conn_path = db_path

        for experiment in experiments(self._db_conn):
            exp_id = experiment.exp_id
            exp = ExperimentInMem(
                experiment,
                exp_id,
                experiment.name,
                experiment.sample_name,
                experiment.last_counter,
                )
            self._experiments.append(exp)

            for ds in experiment.data_sets():
                if not ds.started:
                    # no start time yet: check_for_updates lists it once started
                    exp.unstarted.append(ds.counter)
                    continue
                dd = self._get_ds_description(ds, exp)
                exp.ds_descriptions.append(dd)
        self._apply_filter()
        self._update_timer.start()

    def _get_ds_description(self, ds, exp):
        vars = [par.name for par in ds.dependent_parameters]
        axes = set(ds.paramspecs.keys())
        axes -= set(vars)
        return QCoDeSDatasetDescription(
            uid=ds.guid,
            name=ds.name,
            collected_datetime=datetime.fromtimestamp(ds.run_timestamp_raw),
            labels=dict(
                experiment=exp.name,
                sample=exp.sample_name,
                vars=", ".join(sorted(vars)),
                axes=", ".join(sorted(axes)),
                ),
            ds=ds,
            )

    def _apply_filter(self):
        # Clear previous filtered results to avoid stale/duplicate entries
        self._filtered_ds_descriptions = defaultdict(list)

        # include all sample names
        sample_names: set[str] = set()
        # include only experiements with selected sample name
        experiment_names: set[str] = set()
        # include only date, vars, axes that match sample name and experiment name
        vars: set[str] = set()
        axes: set[str] = set()
        # include only dates that match full filter
        dates: set[date] = set()

        for exp in self._experiments:
            sample_names.add(exp.sample_name)
            if self._sample is not None and exp.sample_name != self._sample:
                continue
            experiment_names.add(exp.name)
            if self._experiment is not None and exp.name != self._experiment:
                continue
            for ds_descr in exp.ds_descriptions:
                vars.add(ds_descr.labels["vars"])
                axes.add(ds_descr.labels["axes"])

                filter_vars = self._filter.labels.get("vars")
                filter_axes = self._filter.labels.get("axes")
                if filter_vars and ds_descr.labels["vars"] != filter_vars:
                    continue
                if filter_axes and ds_descr.labels["axes"] != filter_axes:
                    continue
                if self._filter.name_contains and self._filter.name_contains not in ds_descr.name:
                    continue
                _date = ds_descr.collected_date
                self._filtered_ds_descriptions[_date].append(ds_descr)
                dates.add(_date)
        for _date, dds in self._filtered_ds_descriptions.items():
            self._filtered_ds_descriptions[_date] = sorted(dds, key=lambda d: d.collected_datetime, reverse=True)
        self._set_dates(sorted(dates, reverse=True))
        labels = {
            "sample": sorted(sample_names),
            "experiment": sorted(experiment_names),
            "vars": sorted(vars),
            "axes": sorted(axes),
            }
        self._set_labels(labels)
        self.datasets_changed.emit()

    def get_dataset_descriptions(self, date: date) -> list[DatasetDescription]:
        return self._filtered_ds_descriptions.get(date, [])

    def get_dataset_description_for_uid(self, uid: str) -> DatasetDescription | None:
        # linear search should be fast enough
        for exp in self._experiments:
            for ds_descr in exp.ds_descriptions:
                if ds_descr.uid == uid:
                    return ds_descr
        return None

    @qt_log_exception
    def get_dataset(self, ds_description: QCoDeSDatasetDescription) -> Dataset:
        # @@@ TODO: LRU cache
        return QCoDeSDataset(ds_description)

    @qt_log_exception
    def check_for_updates(self):
        new_ds_descriptions = []

        # Use public API to detect new experiments
        loaded_exp_ids = {exp.exp_id for exp in self._experiments}
        for experiment in experiments(self._db_conn):
            if experiment.exp_id not in loaded_exp_ids:
                exp = ExperimentInMem(
                    experiment,
                    experiment.exp_id,
                    experiment.name,
                    experiment.sample_name,
                    0,
                    )
                self._experiments.append(exp)

        for exp in self._experiments:
            current_counter = exp.experiment.last_counter
            # the runs not started at the last check, then the new ones
            counters = exp.unstarted + list(range(exp.last_counter + 1, current_counter + 1))
            exp.unstarted = []
            for counter in counters:
                ds = load_by_counter(counter, exp.exp_id, self._db_conn)
                if not ds.started:
                    # created, but without start time and parameters yet
                    exp.unstarted.append(counter)
                    continue
                dd = self._get_ds_description(ds, exp)
                exp.ds_descriptions.append(dd)
                new_ds_descriptions.append(dd)
            exp.last_counter = current_counter

        if new_ds_descriptions:
            self._emit_updates(new_ds_descriptions)

        self._update_timer.start()

    def _emit_updates(self, new_ds_descriptions: list[DatasetDescription]):
        update_dates = False
        dates = self._dates.copy()
        filtered_new_ds_descr = []
        for ds_descr in new_ds_descriptions:

            filter_vars = self._filter.labels.get("vars")
            filter_axes = self._filter.labels.get("axes")
            if filter_vars and ds_descr.labels["vars"] != filter_vars:
                continue
            if filter_axes and ds_descr.labels["axes"] != filter_axes:
                continue
            if self._filter.name_contains and self._filter.name_contains not in ds_descr.name:
                continue
            _date = ds_descr.collected_date
            self._filtered_ds_descriptions[_date].append(ds_descr)
            self._filtered_ds_descriptions[_date] = sorted(self._filtered_ds_descriptions[_date],
                                                           key=lambda d: d.collected_datetime,
                                                           reverse=True)
            filtered_new_ds_descr.append(ds_descr)
            if _date not in dates:
                dates.append(_date)
                update_dates = True
        if update_dates:
            self._set_dates(sorted(dates, reverse=True))

        if filtered_new_ds_descr:
            self.new_datasets.emit(filtered_new_ds_descr)

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


@dataclass
class ExperimentInMem:
    experiment: Experiment
    exp_id: int
    name: str
    sample_name: str
    last_counter: int
    ds_descriptions: list[QCoDeSDatasetDescription] = field(default_factory=list)
    # counters of the runs created but not started yet
    unstarted: list[int] = field(default_factory=list)
