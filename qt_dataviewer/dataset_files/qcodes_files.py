import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import xarray as xr

from qt_dataviewer.abstract import DatasetDescription, Dataset


@dataclass
class QcodesDatasetDescription(DatasetDescription):
    path: str | None = None
    ds_xr: xr.Dataset | None = None


class QcodesDataset(Dataset):
    def __init__(self, ds_description: DatasetDescription,
                 ds_xr: xr.Dataset):
        super().__init__(ds_description)
        self.ds_xr = ds_xr
        self._snapshot = None

    @property
    def data(self) -> xr.Dataset:
        return self.ds_xr

    @property
    def is_complete(self) -> bool:
        return True

    @property
    def is_modified(self) -> bool:
        return False

    def reload(self) -> None:
        pass

    @property
    def formatted_uid(self) -> str:
        return self.ds_description.uid

    @property
    def info(self) -> list[tuple[str, str]]:
        info_keys = [
            ("Experiment name", "exp_name"),
            ("Dataset name", "ds_name"),
            ("Sample", "sample_name"),
            ("Started", "run_timestamp"),
            ("Completed", "completed_timestamp"),
            ("Run ID", "run_id"),
            ("Capured run ID", "captured_run_id"),
            ("File name", "filename"),
            ("Application", "application"),
            ]
        attrs = self.ds_xr.attrs

        return [
            (name, attrs.get(key, "-"))
            for name, key in info_keys
            ]

    @property
    def snapshot(self) -> None | str | dict[str, Any]:
        if 'snapshot' in self.ds_xr.attrs:
            return self.ds_xr.attrs['snapshot']
        return None

    def close(self):
        pass


def get_qcodes_dataset_description(ds_xr: xr.Dataset, path: str):
    try:
        attrs = ds_xr.attrs
        # QCoDeS datasets contain following attributes
        guid = attrs["guid"]
        sample_name = attrs["sample_name"]
        name = attrs["exp_name"] + "/" + attrs["ds_name"]
        try:
            run_description = json.loads(attrs["run_description"])
            version = run_description["version"]
        except Exception:
            return None

        dd = QcodesDatasetDescription(
            uid=guid,
            name=name,
            collected_datetime=datetime.fromisoformat(attrs["run_timestamp"]),
            labels=dict(
                sample_name=sample_name,
                application="QCoDeS",
                ),
            path=path,
            ds_xr=ds_xr)
        if "application" not in attrs:
            attrs["application"] = f"QCoDeS:v{version}"
        attrs["filename"] = os.path.basename(path)
        return dd
    except KeyError:
        return None
