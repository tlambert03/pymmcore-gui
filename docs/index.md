# pymmcore-gui

**pymmcore-gui** is a desktop application for controlling microscopes with the
Micro-Manager core, written entirely in Python.  It brings the rest of the
ecosystem together into one cohesive app, and aims to be a pure-Python
replacement for the Java-based Micro-Manager GUI (MMStudio).

!!! info "Name pending"

    *pymmcore-gui* is a working title.  The application is usable today, but
    expect rough edges and frequent changes.

## What's inside

| Component | Role in the GUI |
| --- | --- |
| [pymmcore-plus](../pymmcore-plus/index.md) | Device control and the acquisition engine ([`CMMCorePlus`][pymmcore_plus.CMMCorePlus], [`MDAEngine`][pymmcore_plus.mda.MDAEngine]). |
| [useq-schema](../useq-schema/index.md) | Describes the experiments you run: time-lapses, z-stacks, channels, well plates, grids, ... |
| [pymmcore-widgets](../pymmcore-widgets/widgets/index.md) | The panels: camera and stage control, property browser, acquisition setup, ... |
| [ndv](https://github.com/pyapp-kit/ndv) | Fast, lightweight n-dimensional viewer for live and acquired images. |

## Features

- Complete device control and configuration (including the Hardware
  Configuration Wizard)
- Multi-dimensional acquisitions: time, z, channels, positions, grids, well plates
- Real-time image preview and acquisition visualization (2D and 3D)
- Customizable, dockable layouts
- An integrated IPython console with access to the running core
- Double-clickable application bundles for Windows and macOS

## Next steps

- [Install pymmcore-gui](install.md), either as a Python package or a bundled app.
- [Launch and script the GUI](usage.md).
- Browse the [API reference](api/pymmcore_gui/index.md) if you want to extend it.
