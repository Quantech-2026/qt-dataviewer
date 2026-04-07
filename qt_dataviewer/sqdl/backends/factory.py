from .base import BaseClient


class ClientFactory():

    @staticmethod
    def create_client(backend_type: str | None = None) -> BaseClient:
        if backend_type is None:
            backend_type = "sqdl"

        match backend_type:
            case "sqdl":
                from .sqdl import SqdlClient
                return SqdlClient()
            case "qdl":
                from .qdl import QdlClient
                return QdlClient()
            case _:
                raise ValueError(f"Unfamiliar backend type: {backend_type}")
