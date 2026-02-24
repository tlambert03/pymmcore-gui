# pymmcore-gui

A full-featured desktop GUI for [Micro-Manager](https://micro-manager.org/),
built with [pymmcore-widgets](https://pymmcore-plus.github.io/pymmcore-widgets/)
and [Qt](https://doc.qt.io/).

## Features

- Complete device control for all Micro-Manager hardware
- Multi-dimensional acquisition with real-time preview
- Customizable docking interface
- Integrated IPython console
- Cross-platform (Windows, macOS, Linux)

## Installation

```bash
pip install pymmcore-gui
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install pymmcore-gui
```

## Quick start

Launch from the command line:

```bash
mmgui
```

Or from Python:

```python
from pymmcore_gui import launch

launch()
```
