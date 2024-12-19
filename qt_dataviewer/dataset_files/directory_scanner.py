from abc import abstractmethod

class DirectoryScanner:

    @abstractmethod
    def get_subdirectories(self, path: str) -> list[str]:
        pass
