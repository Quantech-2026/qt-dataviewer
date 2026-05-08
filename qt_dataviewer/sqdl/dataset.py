from datetime import datetime, timedelta
import io
import time
import logging

import xarray as xr

from .backends.base import DatasetDescriptionWithReference, BaseFile

from qt_dataviewer.abstract.dataset import Dataset
from qt_dataviewer.xarray_adapters.coretools_xarray import get_snapshot
from qt_dataviewer.utils.qt_utils import qt_show_exception
from requests import Session
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)


class SqdlDataset(Dataset):
    def __init__(
            self,
            ds_description: DatasetDescriptionWithReference,
            s3session: Session,
    ):
        super().__init__(ds_description)
        self._s3session = s3session
        self._snapshot = None
        self.ds_xr = None
        self.file_md5_sum = None
        self._last_refresh = None
        self._load_error_msg = None
        self.reload()

    def reload(self) -> None:
        try:
            # (re)load files
            file = self._get_changed_file()
            if file is None:
                return
            self.ds_xr = self._load_hdf5_from_url(file)
            self.is_mutable = file.is_mutable
            self.file_md5_sum = file.md5_sum
        except Exception as ex:
            qt_show_exception("Dataset load failed", ex)

    def _get_changed_file(self) -> BaseFile | None:
        if (
            self._last_refresh is None
            or datetime.now() - self._last_refresh > timedelta(milliseconds=100)
        ):
            self.ds_description.refresh()
            self._last_refresh = datetime.now()

        sqdl_files = self.ds_description.files
        if not sqdl_files:
            logger.warning(f"Dataset with uid '{self.uid}' contains no files")
            return

        for file in sqdl_files:
            if file.name.endswith('.hdf5'):
                break
        else:
            self._load_error_msg = "No HDF5 file found"
            logger.warning(f"HDF5 file for uid '{self.uid}' not found")
            logger.info(f"Dataset contains files: {[file.name for file in sqdl_files]}")
            return

        if not file.has_data:
            logger.warning(
                f"HDF5 file '{file.name}' for uid '{self.uid}' is not uploaded"
            )
            return

        if file.md5_sum == self.file_md5_sum:
            logger.debug('file not changed')
            return

        return file

    def _load_hdf5_from_url(self, file) -> xr.Dataset | None:
        t0 = time.perf_counter()
        self._load_error = None
        try:
            content = file.download(self._s3session)
        except HTTPError as exc:
            logger.warning(
                f"Failed to load hdf5 (status={exc.response.status_code})"
            )
            self._load_error_msg = f"Failed to load ({exc.response.status_code})"
            logger.info(f"{exc.response.content}")
            return None

        if content is None:
            self._load_error_msg = "Empty file"
            return None

        length = len(content)

        t1 = time.perf_counter()
        with io.BytesIO(content) as fp:
            res = xr.load_dataset(fp, engine="h5netcdf")
            t2 = time.perf_counter()

        logger.debug(
            f"Loaded HDF5 {(t1-t0)*1000:.1f} ms {length//1024} kB."
            f" Converted in {(t2-t1)*1000:.1f} ms"
        )
        return res

    @property
    def data(self) -> xr.Dataset:
        if self.ds_xr is None:
            return xr.Dataset()
        return self.ds_xr

    @property
    def is_complete(self) -> bool:
        if self.ds_xr is None:
            return False
        return not self.is_mutable

    @property
    def is_modified(self) -> bool:
        return self._get_changed_file() is not None

    @property
    def formatted_uid(self) -> str: # TODO: get application from sqdl dataset description?
        if self.ds_xr is not None and self.ds_xr.attrs.get("application", "").startswith("core-tools:"):
            s = str(int(self.uid))
            return s[:-14] + '_' + s[-14:-9] + '_' + s[-9:]
        else:
            return self.uid

    @property
    def snapshot(self) -> None | str | dict[str, any]:
        if self._snapshot is None and self.ds_xr is not None:
            self._snapshot = get_snapshot(self.ds_xr)
        return self._snapshot

    @property
    def info(self) -> list[tuple[str, str]]:
        if self.ds_xr is None:
            return [("No data", self._load_error_msg)]

        # TODO @@@ Use schema
        info_keys = [
            ("Project", "project"),
            ("Setup", "setup"),
            ("Sample", "sample"),
            ]
        labels = self.ds_description.labels

        start_time = self.ds_xr.attrs.get("measurement_time")
        end_time = self.ds_xr.attrs.get("completed_time")
        duration_str = "-"
        try:
            if end_time is not None and start_time is not None:
                end_time = datetime.fromisoformat(end_time)
                start_time = datetime.fromisoformat(start_time)
                duration = (end_time - start_time).total_seconds()
                if duration >= 0:
                    s = duration % 60
                    m = int(duration) // 60
                    h, m = divmod(m, 60)
                    if h > 0:
                        duration_str = f"{h}h:{m:02d}m:{int(s):02d}s"
                    elif m > 0:
                        duration_str = f"{m:2d}m:{int(s):02d}s"
                    else:
                        duration_str = f"{s:.2f}s"
        except Exception:
            logger.error("Could not get duration", exc_info=True)
            duration_str = "-"

        info = [
            (name, labels.get(key, "-"))
            for name, key in info_keys
            ]
        info.append(
            ("Duration", duration_str)
            )
        return info
