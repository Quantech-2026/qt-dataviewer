from dataclasses import dataclass
from datetime import datetime
from typing import Any

import xarray as xr

from qt_dataviewer.abstract import DatasetDescription, Dataset
from qt_dataviewer.xarray_adapters.coretools_xarray import get_snapshot


@dataclass
class CoreToolsDatasetDescription(DatasetDescription):
    path: str | None = None
    ds_xr: xr.Dataset | None = None


class CoreToolsDataset(Dataset):
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
        s = str(self.ds_description.uid)
        return s[:-14] + '_' + s[-14:-9] + '_' + s[-9:]

    @property
    def info(self) -> list[tuple[str, str]]:
        info_keys = [
            ("Project", "project"),
            ("Setup", "setup"),
            ("Sample", "sample_name"),
            ("Application", "application"),
            ]
        attrs = self.ds_xr.attrs

        return [
            (name, attrs.get(key, "-"))
            for name, key in info_keys
            ]

    @property
    def snapshot(self) -> None | str | dict[str, Any]:
        if self._snapshot is None and self.ds_xr is not None:
            self._snapshot = get_snapshot(self.ds_xr)
        return self._snapshot

    def close(self):
        pass


def get_core_tools_dataset_description(ds_xr: xr.Dataset, path: str):
    try:
        attrs = ds_xr.attrs
        application: str | None = attrs.get("application")
        if application is not None:
            application = application.split(":", maxsplit=1)[0]
            if application != "core-tools":
                return None
        application = "core-tools"
        # core-tools datasets contain following attributes
        project = attrs["project"]
        sample_name = attrs["sample_name"]
        setup = attrs.get("setup", attrs["set_up"])
        return CoreToolsDatasetDescription(
            uid=str(attrs["uuid"]),
            name=attrs["title"],
            collected_datetime=datetime.fromisoformat(attrs["measurement_time"]),
            labels=dict(
                project=project,
                sample_name=sample_name,
                setup=setup,
                application=application,
                ),
            path=path,
            ds_xr=ds_xr)
    except KeyError:
        return None
