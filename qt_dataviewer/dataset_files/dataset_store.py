import logging
import os
from datetime import datetime

import xarray as xr

from qt_dataviewer.abstract import DatasetDescription, Dataset, DatasetStore
from qt_dataviewer.quantify.dataset_description import QuantifyDatasetDescription
from qt_dataviewer.quantify.dataset import QuantifyDataset
from qt_dataviewer.xarray_adapters.quantify_xarray import convert_quantify

from .qcodes_files import (
    QcodesDataset,
    QcodesDatasetDescription,
    get_qcodes_dataset_description,
    )

from .core_tools_files import (
    CoreToolsDatasetDescription,
    CoreToolsDataset,
    get_core_tools_dataset_description,
    )
from .directory_scanner import DirectoryScanner
from .generic_xarray import (
    XarrayDatasetDescription,
    XarrayDataset,
    )


logger = logging.getLogger(__name__)


class FileDataStore(DatasetStore, DirectoryScanner):

    def __init__(self, base_dir: str):
        super().__init__(False)
        self.set_base_dir(base_dir)

    @property
    def source_name(self):
        return self._base_dir

    @property
    def base_dir(self):
        return self._base_dir

    def set_base_dir(self, base_dir: str):
        self._base_dir = base_dir
        self.refresh()

    def refresh(self) -> None:
        # Create empty cache
        self._dataset_descriptions: dict[str, list[DatasetDescription]] = {}
        self._directories: dict[str, list[str]] = {}
        self.datasets_changed.emit()

    def get_subdirectories(self, path: str) -> list[str]:
        if path not in self._directories:
            self._scan_dir(path)
        return self._directories[path]

    def get_dataset_descriptions(self, path: str) -> list[DatasetDescription]:
        if path not in self._dataset_descriptions:
            self._scan_dir(path)
        return self._dataset_descriptions[path]

    def get_dataset_description_for_uid(self, uid: str) -> DatasetDescription | None:
        # scan directories...
        raise NotImplementedError()

    def get_dataset(self, dd: DatasetDescription) -> Dataset:
        if isinstance(dd, QuantifyDatasetDescription):
            return QuantifyDataset(dd)
        if isinstance(dd, CoreToolsDatasetDescription):
            return CoreToolsDataset(dd, dd.ds_xr)
        if isinstance(dd, QcodesDatasetDescription):
            return QcodesDataset(dd, dd.ds_xr)
        if isinstance(dd, XarrayDatasetDescription):
            return XarrayDataset(dd, dd.ds_xr)
        raise Exception(f"Unknown dataset description {type(dd)}")

    def set_name(self, ds_description: DatasetDescription, name: str):
        raise NotImplementedError()

    def set_rating(self, ds_description: DatasetDescription, rating: int):
        raise NotImplementedError()

    def get_next(self, ds_description: DatasetDescription) -> DatasetDescription:
        dd_list, index = self._get_dd_index(ds_description)
        if index+1 < len(dd_list):
            return dd_list[index+1]
        raise StopIteration('No more datasets') from None

    def get_previous(self, ds_description: DatasetDescription) -> DatasetDescription:
        dd_list, index = self._get_dd_index(ds_description)
        if index > 0:
            return dd_list[index-1]
        raise StopIteration('No more datasets') from None

    def get_latest(self) -> DatasetDescription:
        raise NotImplementedError()

    def close(self):
        pass

    def _scan_dir(self, path: str) -> None:
        full_path = os.path.join(self._base_dir, path)

        logging.debug(f"Scanning '{full_path}'")
        dataset_descriptions = []
        directories = []
        for entry in os.scandir(full_path):
            if entry.is_file():
                if dd := self._get_dd_from_file(entry):
                    # add dataset description
                    dataset_descriptions.append(dd)
                    continue
            elif entry.is_dir():
                if dd := self._get_dd_from_dir(entry):
                    # add dataset description
                    dataset_descriptions.append(dd)
                    continue
                directories.append(entry.name)

        self._dataset_descriptions[path] = dataset_descriptions
        self._directories[path] = directories

    def _get_dd_from_dir(self, entry: os.DirEntry) -> DatasetDescription | None:
        try:
            return QuantifyDatasetDescription(entry.name, entry.path)
        except Exception:
            pass

        try:
            # check core-tools export: UUID + hdf5
            return self._get_sqdl_upload_dataset_description(entry)
        except Exception:
            raise
            pass

        return None

    def _get_dd_from_file(self, entry: os.DirEntry) -> DatasetDescription | None:
        if entry.name.endswith(".hdf5"):
            try:
                return self._get_hdf5_dataset_description(entry)
            except Exception:
                pass

        return None

    def _get_dd_index(self, dd: DatasetDescription) -> tuple[list[DatasetDescription], int]:
        path = self._get_parent_directory(dd)
        dd_list = self._dataset_descriptions[path]
        for i, dd_entry in enumerate(dd_list):
            if dd_entry.uid == dd.uid:
                index = i
                break
        else:
            raise KeyError("Dataset description not found")
        return dd_list, index

    def _get_parent_directory(self, dd: DatasetDescription) -> str:
        if isinstance(
                dd,
                QuantifyDatasetDescription
                | CoreToolsDatasetDescription
                | XarrayDatasetDescription
                ):
            parent_dir = os.path.dirname(dd.path)
            # remove base dir
            rel_path = os.path.relpath(parent_dir, self._base_dir)
            return rel_path.replace("\\", "/")
        raise Exception(f"Unknown dataset description {type(dd)}")

    def _get_sqdl_upload_dataset_description(self, entry: os.DirEntry):
        dir_name = entry.name
        if len(dir_name) != 19:
            return None
        try:
            int(dir_name)
        except ValueError:
            return None
        hdf5_file = os.path.join(entry.path, "ds_" + dir_name + ".hdf5")
        if not os.path.isfile(hdf5_file):
            return None
        try:
            with xr.open_dataset(hdf5_file) as ds_xr:
                logging.debug(f"Found sqdl upload 'ds_{dir_name}.hdf5'")
                return get_core_tools_dataset_description(ds_xr, entry.path)
        except Exception:
            return None

    def _get_hdf5_dataset_description(self, entry: os.DirEntry):
        with xr.open_dataset(entry.path) as ds_xr:
            path = entry.path

            logging.debug(f"Found xarray '{path}'")

            try:
                dd = get_core_tools_dataset_description(ds_xr, entry.path)
                if dd is not None:
                    return dd
            except Exception:
                pass

            try:
                return get_quantify_dataset_description(ds_xr, entry.path)
            except Exception:
                pass

            try:
                return get_qcodes_dataset_description(ds_xr, entry.path)
            except Exception:
                pass

            attrs = ds_xr.attrs
            collected_datetime = None
            try:
                if "measurement_time" in attrs:
                    collected_datetime = datetime.fromisoformat(attrs["measurement_time"])
            except Exception:
                pass

            if collected_datetime is None:
                collected_datetime = datetime.fromtimestamp(os.path.getmtime(path))

            # Return generic xarray
            return XarrayDatasetDescription(
                uid=str(attrs.get("uuid", entry.name)),
                name=attrs.get("title", attrs.get("name", entry.name)),
                collected_datetime=collected_datetime,
                path=entry.path,
                ds_xr=ds_xr,
                labels=dict(application=attrs.get("application", "Generic xarray")),
                )


def get_quantify_dataset_description(ds_xr: xr.Dataset, path: str):
    attrs = ds_xr.attrs
    tuid = attrs["tuid"]
    collected_datetime = datetime.strptime(tuid[:19], "%Y%m%d-%H%M%S-%f")

    ds_xr = convert_quantify(ds_xr)
    return XarrayDatasetDescription(
        uid=tuid,
        name=attrs.get("name", tuid),
        collected_datetime=collected_datetime,
        path=path,
        ds_xr=ds_xr,
        labels=dict(application=attrs.get("application", "Quantify")),
        )
