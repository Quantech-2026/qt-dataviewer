from abc import abstractmethod

class DatasetList:
    """
    All methods are optional.
    DataViewer checks whether a method is implemented before a button is enabled or made visible.

    """
    @abstractmethod
    def has_next(self):
        ...

    @abstractmethod
    def select_next(self):
        ...

    @abstractmethod
    def has_previous(self):
        ...

    @abstractmethod
    def select_previous(self):
        ...

    @abstractmethod
    def rate_current(self, rate: int):
        ...

    @abstractmethod
    def rename_current(self, name: str):
        ...

    def implements(self, method_name: str) -> bool:
        method = getattr(self, method_name, None)
        if method is None:
            return False
        # Abstract methods have the attribute __isabstractmethod__
        return getattr(method, "__isabstractmethod__", False)
