from .base import BaseClient
from .qdl import QdlClient
from .sqdl import SqdlClient


class ClientFactory():

    @staticmethod
    def create_client(backend: str = "sqdl") -> BaseClient:
        match backend:
            case "sqdl":
                return SqdlClient()
            case "qdl":
                return QdlClient()
            case _:
                raise ValueError(f"Unfamiliar backend type: {backend}")
