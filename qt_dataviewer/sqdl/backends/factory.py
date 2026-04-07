from .base import BaseClient
from .qdl import QdlClient
from .sqdl import SqdlClient


class ClientFactory():

    @staticmethod
    def create_client(backend_type: str | None = None) -> BaseClient:
        if backend_type is None:
            backend_type = "sqdl"

        match backend_type:
            case "sqdl":
                return SqdlClient()
            case "qdl":
                return QdlClient()
            case _:
                raise ValueError(f"Unfamiliar backend type: {backend_type}")
