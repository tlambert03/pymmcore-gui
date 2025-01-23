# Info for Contributors

Dependencies are managed strictly using [uv](https://docs.astral.sh/uv/), and the
`uv.lock` [lockfile](https://docs.astral.sh/uv/concepts/projects/layout/#the-lockfile)
is checked into source, to ensure a reproducible environment for all developers.
The lockfile also dictates the exact dependencies that will go into the bundled application.

To get started, make sure you have
[uv installed](https://docs.astral.sh/uv/getting-started/installation/), then run

```sh
git clone https://github.com/pymmcore-plus/pymmcore-gui.git
cd pymmcore-gui
uv sync
```

That will create a virtual environment at `.venv` in the root directory, and install
all dependencies.  You can then run tests using

```sh
uv run pytest
```

At any time, you can run `uv sync` to ensure that your current environment matches
the requirements specified in `uv.lock`. The lockfile itself shouldn't be manually
edited, but if you need to modify the *constraints* of the dependencies, you should
do so in the normal way in `pyproject.toml`, and then run `uv lock` to update the
lockfile, then commit it and open a PR.
