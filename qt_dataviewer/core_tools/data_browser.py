from qt_dataviewer.browser_ui.main_window import DataBrowserBase

from .dataset_store import CoreToolsDatasetStore


class CoreToolsDataBrowser(DataBrowserBase):
    def __init__(self, gui_style: str | None = None, *, show: bool = True):
        self.data_store = CoreToolsDatasetStore()
        super().__init__(
            "CoreTools",
            self.data_store,
            "Database",
            label_keys={
                "Project": "project",
                "Setup": "setup",
                "Sample": "sample",
                "Rating": "rating",
                "UUID": "uid",
                "Time": "time",
                "Name": "name",
                "Keywords": "keywords",
                },
            column_definitions=[
                ("Rating",  46, "rating-star"),
                ("UUID", ),
                ("Time", ),
                ("Name", ),
                ("Keywords", ),
             ],
            sort_by_column=1,
            filters=[
                ("Project", "list"),
                ("Setup", "list"),
                ("Sample", "list"),
                ("Rating", "rating-star"),
                "Name",
                ("Keywords", "keywords"),
                ],
            gui_style=gui_style,
            show=show,
            )

    def get_menu_actions(self):
        return None

    def browser_started(self):
        self.data_store.refresh()
        super().browser_started()
