from .base import BaseClient

from qdl_client import QDLClient as Client


class QDLClient(BaseClient):
    def __init__(self):
        self.client = Client()

    def login(self):
        self.client.login()

    def logout(self):
        self.client.logout()
