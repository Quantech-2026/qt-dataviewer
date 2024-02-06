# Changelog
All notable changes to QT-DataViewer will be documented in this file.

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
