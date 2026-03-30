from qt_dataviewer.quantify.data_browser import QuantifyDataBrowser
from qt_dataviewer.utils.logger import configure_logging

configure_logging()
browser = QuantifyDataBrowser("test_data/quantify")
# browser = QuantifyDataBrowser(gui_style="dark")
