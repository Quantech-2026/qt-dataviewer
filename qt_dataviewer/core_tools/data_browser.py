
from qt_dataviewer.browser_ui.main_window import DataBrowserBase

from .dataset_store import CoreToolsDatasetStore

class CoreToolsDataBrowser(DataBrowserBase):
    def __init__(self):
        self.data_store = CoreToolsDatasetStore()
        super().__init__(
            "CoreTools",
            self.data_store,
            "Database",
            label_keys={
                "Project": "project",
                "Setup": "setup",
                "Sample": "sample",
                "Starred": "rating",
                "UUID": "uid",
                "Time": "time",
                "Name": "name",
                "Keywords": "keywords",
                },
            column_definitions=[
                ("Starred",  44),
                ("UUID", 140),
                ("Time", 56),
                ("Name", ),
                ("Keywords", ),
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

    def get_menu_actions(self):
        return None

