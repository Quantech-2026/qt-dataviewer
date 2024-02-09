from abc import abstractmethod
from typing import Any

class DatasetList:
    """
    All methods are optional.
    DataViewer checks whether a method is implemented before a button is enabled or made visible.
    """
    @abstractmethod
    def has_next(self) -> bool:
        ...

    @abstractmethod
    def get_next(self) -> Any:
        ...

    @abstractmethod
    def has_previous(self) -> bool:
        ...

    @abstractmethod
    def get_previous(self) -> Any:
        ...

    @abstractmethod
    def rate_current_dataset(self, rate: int) -> None:
        ...

    @abstractmethod
    def rename_current_dataset(self, name: str) -> None:
        ...

    def implements(self, method_name: str) -> bool:
        method = getattr(self, method_name, None)
        if method is None:
            return False
        # Abstract methods have the attribute __isabstractmethod__
        return getattr(method, "__isabstractmethod__", False)
