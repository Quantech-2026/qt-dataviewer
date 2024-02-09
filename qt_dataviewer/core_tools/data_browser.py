
from qt_dataviewer.browser_ui.main_window import DataBrowserBase

from .dataset_store import CoreToolsDatasetStore

class CoreToolsDataBrowser(DataBrowserBase):
    def __init__(self):
        self.data_store = CoreToolsDatasetStore()
        super().__init__(
            self.data_store,
            "Database",
            menu_actions=None,
            column_definitions=[
                ("Starred", "rating", 44),
                ("UUID", "uid", 140),
                ("Time", "time", 56),
                ("Name", "name"),
                ("Keywords", "Keywords"),
             ],
            sort_by_column=1,
            filters=[
                ("Project", "list"),
                ("Setup", "list"),
                ("Sample", "list"),
                # TODO rating
                # "Rating",
                "Name",
                ("Keywords", "keywords"),
                ],
            )

        self.set_data_source(self.data_store.get_source_name())

    # TODO Check for updates

