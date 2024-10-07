import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import xarray as xr

from qt_dataviewer.abstract.dataset_description import DatasetDescription


logger = logging.getLogger(__name__)


class DatasetPath:
    """Path to quantify dataset with TUID and name.
    """

    def __init__(self, full_name: str, path: str) -> None:
        """
        Args:
            name: full name of dataset, i.e. TUID+name
            path: path to directory containing hdf5 and snapshot files.

        Notes:
            path contains TUID and name.
        """
        self._path = Path(path)
        if len(full_name) < 26:
            raise Exception(f"{full_name} too short for TUID")
        self._tuid = full_name[:26]
        self._timestamp = datetime.strptime(self._tuid[:19], "%Y%m%d-%H%M%S-%f")
        if len(full_name) < 28:
            self._ds_name = "-- no name --"
        else:
            self._ds_name = full_name[27:]

        self._dataset_file_path = self._path / "dataset.hdf5"
        if not self._dataset_file_path.is_file():
            raise Exception(f"No dataset.hdf5 in {full_name}")
        self._ds_description = self._get_ds_description()

    def __str__(self) -> str:
        """Returns full path.
        """
        return self._path

    @property
    def dataset_description(self) -> DatasetDescription:
        return self._ds_description

    @property
    def timestamp(self) -> datetime:
        """Returns the timestamp of dataset creation
        """
        return self._timestamp

    @property
    def name(self) -> str:
        """Returns dataset name
        """
        return self._ds_name

    @property
    def tuid(self) -> str:
        """Returns the tuid string
        """
        return self._tuid

    def _get_ds_description(self):
        dd = DatasetDescription(
            self.tuid,
            self.name,
            self.timestamp,
            )

        # For the sake of performance we do not yet load the variables and coordinates
        # try:
        #     # @@@ add caching !!
        #     ds = self.load_ds()

        #     dd.variables = [
        #         ArrayDescription(name, var.shape)
        #         for name, var in ds.data_vars.items()
        #         ]
        #     dd.coordinates = [
        #         ArrayDescription(name, var.shape)
        #         for name, var in ds.coords.items()
        #         ]
        # except:
        #     # TODO load attributes later.
        #     pass

        dd.path = self # FIXME: this is a bit dirty

        # TODO: retrieve other labels?
        return dd

    def get_file_mtime(self):
        return datetime.fromtimestamp(os.path.getmtime(self._dataset_file_path))

    def load_ds(self) -> xr.Dataset:
        now = datetime.now()
        active = now - self.get_file_mtime() < timedelta(minutes=1)

        file_path = self._dataset_file_path
        if active:
            # assume we have write permission!
            tmp_file = str(file_path)[:-5]+".qt_tmp.hdf5"
            shutil.copy(file_path, tmp_file)
            dsx = xr.load_dataset(tmp_file)
            os.remove(tmp_file)
            return dsx
        else:
            return xr.load_dataset(file_path)

    def load_snapshot(self) -> dict[str, any]:
        with open(self._path / "snapshot.json") as fp:
            return json.load(fp)
