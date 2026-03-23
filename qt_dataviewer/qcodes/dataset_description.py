from dataclasses import dataclass
from datetime import datetime
from qt_dataviewer.abstract import DatasetDescription
from qcodes.dataset import DataSetProtocol


@dataclass
class QCoDeSDatasetDescription(DatasetDescription):
    ds: DataSetProtocol | None = None
    completed_time: datetime | None = None
