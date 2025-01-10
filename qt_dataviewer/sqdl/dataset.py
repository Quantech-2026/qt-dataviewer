from datetime import datetime, timedelta
import io
import time
import logging

import xarray as xr
from sqdl_client.api.v1.file import File

from qt_dataviewer.abstract.dataset_description import DatasetDescription
from qt_dataviewer.abstract.dataset import Dataset
from qt_dataviewer.xarray_adapters.coretools_xarray import get_snapshot
from qt_dataviewer.utils.qt_utils import qt_show_exception

logger = logging.getLogger(__name__)


class SqdlDataset(Dataset):
    def __init__(self,
                 ds_description: DatasetDescription,
                 s3session):
        super().__init__(ds_description)
        self.uid = int(ds_description.uid)
        self._s3session = s3session
        self._snapshot = None
        self.ds_xr = None
        self.file_md5_sum = None
        self._last_refresh = None
        self.reload()

    def reload(self) -> None:
        try:
            # (re)load files
            file = self._get_changed_file()
            if file is None:
                return
            url = file.presigned_url
            self.ds_xr = self._load_hdf5_from_url(url)
            self.is_mutable = file.is_mutable
            self.file_md5_sum = file.md5_sum
        except Exception as ex:
            qt_show_exception("Dataset load failed", ex)

    def _get_changed_file(self) -> File | None:
        if (self._last_refresh is None
            or datetime.now() - self._last_refresh > timedelta(milliseconds=100)):
            sqdl_ds = self.ds_description.sqdl_ds.refresh()
            self.ds_description.sqdl_ds = sqdl_ds
            self._last_refresh = datetime.now()
        sqdl_files = self.ds_description.sqdl_ds.files
        if not sqdl_files:
            logger.warning(f"Dataset with uid '{self.uid}' contains no files")
            return
        for file in sqdl_files:
            if file.name.endswith('.hdf5'):
                break
        else:
            logger.warning(f"HDF5 file for uid '{self.uid}' not found")
            return
        if not file.has_data:
            logger.warning(f"HDF5 file '{file.name}' for uid '{self.uid}' is not uploaded")
            return
        if file.md5_sum == self.file_md5_sum:
            logger.debug('file not changed')
            return
        return file

    def _load_hdf5_from_url(self, url):
        t0 = time.perf_counter()
        resp = self._s3session.request("GET", url)
        if resp.status_code == 200:
            length = len(resp.content)
            t1 = time.perf_counter()
            with io.BytesIO(resp.content) as fp:
                res = xr.load_dataset(fp, engine="h5netcdf")
                t2 = time.perf_counter()
            logger.debug(f'Loaded HDF5 {(t1-t0)*1000:.1f} ms {length//1024} kB. Converted in {(t2-t1)*1000:.1f} ms')
            return res
        else:
            logger.warning(f"Failed to load hdf5 (status={resp.status_code})")
            logger.info(f"{resp.content}")
            return None

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
    def formatted_uid(self) -> str:
        s = str(self.uid)
        return s[:-14] + '_' + s[-14:-9] + '_' + s[-9:]

    @property
    def snapshot(self) -> None | str | dict[str, any]:
        if self._snapshot is None and self.ds_xr is not None:
            self._snapshot = get_snapshot(self.ds_xr)
        return self._snapshot

    @property
    def info(self) -> list[tuple[str, str]]:
        # TODO @@@ Use schema
        info_keys = [
            ("Project", "project"),
            ("Setup", "setup"),
            ("Sample", "sample"),
            ]
        labels = self.ds_description.labels

        return [
            (name, labels.get(key, "-"))
            for name, key in info_keys
            ]
