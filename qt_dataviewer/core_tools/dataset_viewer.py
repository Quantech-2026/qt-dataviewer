import logging

from core_tools.data.ds.data_set_core import data_set
from PyQt5.QtWidgets import QMessageBox

from qt_dataviewer import DatasetViewer
from qt_dataviewer.abstract import DatasetDescription, Dataset, DatasetList
from .dataset import CoreToolsDataset


logger = logging.getLogger(__name__)


class CoreToolsDatasetViewer(DatasetViewer):
    """
    Viewer taking a core-tools dataset as input.
    """

    coretools_upgrade_message_shown = False

    def __init__(self, ds: data_set, datalist: DatasetList = None):
        ds_fullqualname = type(ds).__module__ +'.' + type(ds).__qualname__
        if ds_fullqualname != "core_tools.data.ds.data_set_core.data_set":
            raise Exception(f"Expected coretools data_set got '{ds_fullqualname}'")

        if (datalist is not None
                and not hasattr(datalist, 'get_next')):
            if not CoreToolsDatasetViewer.coretools_upgrade_message_shown:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("Upgrade core-tools to v1.4.44+ to use next/previous buttons")
                msg.setWindowTitle("QT-DataViewer: Core-tools upgrade")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
                CoreToolsDatasetViewer.coretools_upgrade_message_shown = True

            datalist = None

        super().__init__(ds, datalist=datalist)

    def _to_qt_ds(self, ds: data_set) -> CoreToolsDataset:
        labels = {
            "project": ds.project,
            "setup": ds.set_up,
            "sample": ds.sample_name,
            }
        s = str(ds.exp_uuid)
        uuid_str = s[:-14] + '_' + s[-14:-9] + '_' + s[-9:]
        ds_description = DatasetDescription(
                uid=uuid_str,
                name=ds.name,
                collected_datetime=ds.run_timestamp,
                rating=ds.starred,
                labels=labels,
                )

        return CoreToolsDataset(ds_description, ds)

    def set_ds(self, ds: Dataset | data_set) -> None:
        # Hack for integration with old core-tools data browser.
        if ds is not None and not isinstance(ds, Dataset):
            ds = self._to_qt_ds(ds)
        super().set_ds(ds)
