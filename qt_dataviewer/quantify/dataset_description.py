import logging
import os
from datetime import datetime

from qt_dataviewer.abstract.dataset_description import DatasetDescription


logger = logging.getLogger(__name__)


class QuantifyDatasetDescription(DatasetDescription):
    """Quantify dataset description.
    Includes path to dataset.
    """

    def __init__(self, full_name: str, path: str) -> None:
        """
        Args:
            name: full name of dataset, i.e. TUID+name
            path: path to directory containing hdf5 and snapshot files.

        Notes:
            path contains TUID and name.
        """
        if len(full_name) < 26:
            raise Exception(f"{full_name} too short for TUID")
        tuid = full_name[:26]
        timestamp = datetime.strptime(tuid[:19], "%Y%m%d-%H%M%S-%f")
        if len(full_name) < 28:
            ds_name = "-- no name --"
        else:
            ds_name = full_name[27:]

        self.path = path
        self.dataset_file_path = os.path.join(path, "dataset.hdf5")

        if not os.path.isfile(self.dataset_file_path):
            raise Exception(f"No 'dataset.hdf5' in {full_name}")

        super().__init__(
            tuid,
            ds_name,
            timestamp,
            labels=dict(application="Quantify"),
            )

