# QT-DataViewer

QT-DataViewer is a dataset browser and viewer developed by the Spin Qubit
labs of QuTech. It has a GUI to search and retrieve datasets, and process
(xarray) Datasets to display them as 1D and 2D plots.
QT-DataViewer is a dataset browser for the core-tools, sQDL database, QCoDeS, Quantify, QDL,
and directories with xarray (hdf5/netcdf) files.

QT-DataViewer can automatically update plots when datasets are updated.
Multidimensional datasets can be processed to 1D and 2D plots.
Operations like slicing, averaging, FFT and histogram can be applied on
each individual axis.

<img src="https://gitlab.tudelft.nl/qutech-qdlabs/qt-dataviewer/-/raw/main/docs/QT%20Dataset%20Browser%20(CoreTools).png" width="50%" height="50%" />
<img src="https://gitlab.tudelft.nl/qutech-qdlabs/qt-dataviewer/-/raw/main/docs/Many_variables.png" width="50%" height="50%" />
<img src="https://gitlab.tudelft.nl/qutech-qdlabs/qt-dataviewer/-/raw/main/docs/shuttling%20qubit%20with%20MW%20compensation.png" width="50%" height="50%" />
<img src="https://gitlab.tudelft.nl/qutech-qdlabs/qt-dataviewer/-/raw/main/docs/Sensor__calibration%20(multiline).png" width="50%" height="50%" />
<img src="https://gitlab.tudelft.nl/qutech-qdlabs/qt-dataviewer/-/raw/main/docs/Sensor__calibration%20(histogram).png" width="50%" height="50%" />
<img src="https://gitlab.tudelft.nl/qutech-qdlabs/qt-dataviewer/-/raw/main/docs/Scatter_plot.png" width="50%" height="50%" />
<img src="https://gitlab.tudelft.nl/qutech-qdlabs/qt-dataviewer/-/raw/main/docs/Nyquist_plot.png" width="50%" height="50%" />

[Gallery](https://gitlab.tudelft.nl/qutech-qdlabs/qt-dataviewer/-/raw/main/docs/Gallery.md)

# Data storage browser

The browser uses a backend to retrieve data from various sources.
Current implementation includes backends for:
- core-tools database.
- QCoDeS sqlite database.
- sQDL (spin qubit data lake) database.
- QDL (QuTech Data Lake) databaes.
- Quantify datasets on a file system.
- xarray datasets stored in HDF5 (h5netcdf).
- QCoDeS datasets stored as HDF5 files.

Custom backends for other data sources can easily be created. The components of the
browser GUI can be configured for the search and retrieval options of the data source.

## Command line

The data browser can be started from the command line.

```
qt-file-browser [<directory>] [--dark] [--light]
qt-qcodes-browser [<database-file>] [--dark] [--light]
qt-quantify-browser [<directory>] [--dark] [--light] [--no-scan] [--check-datasets]
qt-sqdl-browser [<scope>] [--dark] [--light]
qt-qdl-browser [<scope>] [--dark] [--light]
```

## sQDL backend

SqdlDataBrowser is a data browser with sQDL backend.
The sQDL backend requires the package `sqdl-client`.

```python
from qt_dataviewer.sqdl import SqdlDataBrowser
from qt_dataviewer.utils.logger import configure_logging

configure_logging()  # Optional start logging to ~/.qt_dataviewer
browser = SqdlDataBrowser("My-Scope")
```
GUI dark style can be activated with the optional argument `gui_style="dark"`.

## Quantify

QuantifyDataBrowser is a data browser with Quantify backend.
No additional packages are needed to browse and display the quantify datasets.

```python
from qt_dataviewer.quantify.data_browser import QuantifyDataBrowser
from qt_dataviewer.utils.logger import configure_logging

configure_logging()  # Optional start logging to ~/.qt_dataviewer
browser = QuantifyDataBrowser()
```
Start browser in specific directory and in dark mode.
```python
browser = QuantifyDataBrowser(r"test_data\quantify", gui_style="dark")
```

Notes:
- The browser scans the directory and all subdirectories for Quantify datasets.
  This scanning processes can take some time.

## QCoDeS database

```Python
from qt_dataviewer.qcodes.data_browser import QCoDeSDataBrowser
from qt_dataviewer.utils.logger import configure_logging

configure_logging()  # Optional start logging to ~/.qt_dataviewer
browser = QCoDeSDataBrowser("~/Projects/Sandbox/qccodes_trials/database/experiments_2026.db")
```

## QDL database

*Experimental*

SqdlDataBrowser can be used with QDL (QuTech Data Lake) backend.
The QDL backend requires the package `qdl-client`.

```python
from qt_dataviewer.sqdl import SqdlDataBrowser
from qt_dataviewer.utils.logger import configure_logging

configure_logging()  # Optional start logging to ~/.qt_dataviewer
browser = SqdlDataBrowser("My-Scope", backend="qdl")
```


## core-tools database

CoreToolsDataBrowser is a data browser with backend for the core-tools database.
The core-tools backend requires the package `core-tools`.

The core-tools database must be configured before the browser is started.
See core-tools documentation of the configuration.

```Python
import core_tools as ct
from qt_dataviewer.core_tools.data_browser import CoreToolsDataBrowser

# configure database
ct.configure(my_configuration_file)

browser = CoreToolsDataBrowser()
```

## File browser

DataFileBrowser is a data browser for xarray datasets stored as HDF5 (h5netcdf).
No additional packages are needed to browse and display the datasets.

The backend contains a bit of logic to recognize dataasets generated by
core-tools and Quantify. It will extract some application specific attributes like
UID and measurement time.

```Python
from qt_dataviewer.data_file_browser import DataFileBrowser
from qt_dataviewer.utils.logger import configure_logging

configure_logging()  # Optional start logging to ~/.qt_dataviewer
browser = DataFileBrowser(r"C:\measurement_data")
```
GUI dark style can be activated with the optional argument `gui_style="dark"`.

# Dataset viewer

The dataset viewer component can also be used without the provided data browsers.
It can be used to directly display (a list of) xarray dataset from code.

The xarray data has to be contained in an implementation the `Dataset` class
that gives standardizes access to xarray dataset and various properties.
It has methods to check whether the dataset has changed and reload it
from the backend.


