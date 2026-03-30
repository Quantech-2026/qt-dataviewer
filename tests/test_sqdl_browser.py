from qt_dataviewer.utils.logger import configure_logging
from qt_dataviewer.sqdl import SqdlDataBrowser


configure_logging()

browser = SqdlDataBrowser(
    # gui_style="dark",
    )

