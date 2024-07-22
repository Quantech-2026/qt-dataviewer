from qt_dataviewer.dataset_list import DatasetList
from qt_dataviewer.abstract import Dataset, DatasetDescription, DatasetStore

class BrowserDatasetList(DatasetList):
    def __init__(self, ds_store: DatasetStore, ds_description: DatasetDescription):
        self.ds_store = ds_store
        self.current_dd = ds_description

    def has_next(self) -> bool:
        try:
            self.ds_store.get_next(self.current_dd)
        except StopIteration:
            return False
        return True

    def get_next(self) -> Dataset:
        dd = self.ds_store.get_next(self.current_dd)
        self.current_dd = dd
        return self.ds_store.get_dataset(dd)

    def has_previous(self) -> bool:
        try:
            self.ds_store.get_previous(self.current_dd)
        except StopIteration:
            return False
        return True

    def get_previous(self) -> Dataset:
        dd = self.ds_store.get_previous(self.current_dd)
        self.current_dd = dd
        return self.ds_store.get_dataset(dd)

    def is_latest(self) -> bool:
        dd = self.ds_store.get_latest()
        return self.current_dd.uid == dd.uid

    def get_latest(self) -> Dataset:
        dd = self.ds_store.get_latest()
        self.current_dd = dd
        return self.ds_store.get_dataset(dd)

    # TODO
    # @abstractmethod
    # def rate_dataset(self, rate: int) -> None:
    #     ...

    # @abstractmethod
    # def rename_dataset(self, name: str) -> None:
    #     ...
