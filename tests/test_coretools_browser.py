import core_tools as ct

from qt_dataviewer.core_tools.data_browser import CoreToolsDataBrowser

# setup logging open database
# ct.configure('./cfg/ct_config_laptop_sds.yaml')
ct.configure('./cfg/ct_config_laptop_veldhorst.yaml')

browser = CoreToolsDataBrowser()
