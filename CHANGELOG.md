# Changelog
All notable changes to QT-DataViewer will be documented in this file.

## \[0.5.5] - 2026-05-08

- Improved QCoDeS dataset viewer.

## \[0.5.4] - 2026-04-17

- Fixed some exceptions using QDL.
- Fixed bug in FFT plot (bug in 0.5.0 - 0.5.3)
- Show error message in dataset info when loading from QDL/sQDL fails.

## \[0.5.3] - 2026-04-16

- Fixed handling of UID for QDL.

## \[0.5.2] - 2026-04-15

- Fixed FFT

## \[0.5.1\] - 2026-04-15

- Updated project dependencies.
- Fixed 2D sidebar histogram for irregular mesh.
- Fixed import of logging handler.

## \[0.5.0] - 2026-04-13

- Added Command line interface: qt-file-browser, qt-sqdl-browser, qt-qcodes-browser, qt-quantify-browser.
- Added scatter plots.
- Added plotting of 0D (scalar) value.
- Added plotting of complex values data.
- Added backend for QDL database.
- Added backend for QCoDeS sqlite database.
- Added display of time at mouse cursor to pulse plot.
- Added configuration in "~/.qt-dataviewer/config.yaml"
- Added settings: plotting.colormap, plotting.2D-colorbar.
- Added configurable logging. Default to ~/.qt-dataviewer/logs
- Replaced pyqt5 by qtpy.
- Fixed plotting qubit register values.
- Speed up of scanning of directories with Quantify data directories.

## \[0.4.19] - 2025-11-10

- Fixed plotting of MW pulses of sequence with multiple segments.
- Fixed 2Dplot of irregular data (broken in previous release)

## \[0.4.17] - 2025-10-29

- Plot labels and qubit-registers on axis.
- Copy with correct background color.
- Added Duration to info panel.

## \[0.4.15] - 2025-10-08

- Fixed negative frequency when scanning high to low.
- Improved lin/log determination for slightly irregular linear steps.
- Fixed axis of 2D plot of incomplete scan when scanning high to low.
- Fixed parsing of hdf5 files in FileBrowser.

## \[0.4.13] - 2025-08-08

- Fix missing icons

## \[0.4.11] - 2025-08-07

- Improved performance when drawing many 2D plots in one window.

## \[0.4.9] - 2025-07-21

- Improved plotting of pulses containing sine waves, e.g. conveyor shuttling.

## \[0.4.7] - 2025-07-18

- Fixed use time zone in time comparison.

## \[0.4.5] - 2025-07-11

- Added basic support for QCoDeS datasets exported as xarray hdf5 file.
- Improved live updates of long running measurements
- Automatic log-scale with very small steps, e.g. np.geomspace(1, 10, 2001)
- Handle Quantify "1d_2_settables_uniformly_spaced": True

## \[0.4.3] - 2025-05-22

- Ignore strange parameter units during smart formatting.

## \[0.4.2] - 2025-01-10

- Fixed loading of quantify files; explicitly use engine="h5netcdf".
- Improved condensed snapshot view. (Now also works with Quantify.)

## \[0.4.1] - 2024-12-20

- Removed unintended print messages.

## \[0.4.0] - 2024-12-20

- Added file browser for exported core-tools data.
- Made parsing of xarray attributes more robust
- Removed spaces surrounding entered uid / uuid

## \[0.3.12] - 2024-10-21

- Support dark style. (requires installation of qdarkstyle)

## \[0.3.11] - 2024-10-07

- Improved scanning of Quantify directory.

## \[0.3.10] - 2024-09-25

- Format values in snapshot in 6 digits.
- Fixed startup problem due to icons and images.

## \[0.3.9] - 2024-09-12

- Added filtering on starred (core-tools) and rating (sQDL)
- Fixed bug when creating QuantifyDataBrowser without specifying path.

## \[0.3.8] - 2024-09-06

- Fixed open TUID on QuantifyDataBrowser.
- Fix CoreToolsDataBrowser (broken in previous release).

## \[0.3.7] - 2024-09-06

- Added QuantifyDataBrowser.
- Added logout to SqdlDataBrowser.
- Do not show units "no_label".
- Improved histogram speed.

## \[0.3.6] - 2024-08-21

- Fixed missing Qt5 event loop start.
- Fixed auto formatting of units without SI prefix.
- Fixed missing h5netcdf dependency.
- Improved error messages.

## \[0.3.5] - 2024-08-19

- Fixed duplicate entries in snapshot presentation

## \[0.3.4] - 2024-08-12

- Added shortcuts Ctrl-Left and Ctrl-Right for browsing through datasets
- Show busy cursor when reloading changed dataset
- Only reload data and redraw plots when data has changed

## \[0.3.3] - 2024-08-07

- Fixed FFT log frequency axis

## \[0.3.2] - 2024-07-31

- Sort sQDL scopes
- Fixed sorting of datasets with unsorted axes in 1D and 2D plots.
- Fixed duplicate drawing of new figure.
- Fixed 2D plots with irregular spaced axis.
- Show focus on slider with dotted outline.

NOTE: uses patched version of pyqtgraph: 0.13.7.1 !!

## \[0.3.1] - 2024-07-29

- Added FFT
- Added auto-sorting of unsorted axis
- Added live data updates to sQDL data plotting
- Only use axis of dataset for x or y if it has > 1 value.
- Fixed pulse plotting for MW pulses and sine.

## \[0.3.0] - 2024-07-22

- Changed DatasetList to get a cleaner interface.
- Added QT-Dataset Browser for core-tools and sQDL.
- Added sQDL and core-tools backends.

## \[0.2.7] - 2024-02-06

- Remove values <= 0 when plotting on logarithmic scale.

## \[0.2.6] - 2024-02-06

- Fix formatting in case the value is a DataArray element (old version of xarray)

## \[0.2.5] - 2024-02-05

- Fixed bug in 2D when dataset was opened before any data was written to it.

## \[0.2.4] - 2024-02-02

- Fixed pulse plotting: faster and also conditional segments
- Added 2D plotting of non-uniform 2D grid.
- Fixed auto SI-prefix with not scaling units like '#' and 'a.u.'

## \[0.2.3] - 2024-02-01

- Postpone plotting of pulses till tab is selected (performance improvement)
- Fixed flashing window

## \[0.2.2] - 2024-01-31

- Fixed bug in 2D plotting with logarithmic axis
- Fixed plotting of MW pulses

## \[0.2.1] - 2024-01-29

- Added condensed snapshot view

## \[0.2.0] - 2024-01-29

- Added snapshot tree
- Added pulse plotting
- Added multiline plots
- Do not show data point markers when > 100 points

## \[0.1.2] - 2024-01-18

- Disabled snapshot tree for performance reasons

## \[0.1.1] - 2024-01-18

- Removed opengl imports

## \[0.1.0] - 2024-01-18

- First release
