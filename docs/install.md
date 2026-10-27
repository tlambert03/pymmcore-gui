# Installing pymmcore-gui

There are two ways to get pymmcore-gui: as a Python package, or as a bundled,
double-clickable application.

=== "Python package"

    You'll need Python 3.11 or newer, and `git` (pip uses it to fetch the code).

    ```sh
    # install the latest version from GitHub
    pip install git+https://github.com/pymmcore-plus/pymmcore-gui

    # install Micro-Manager device adapters
    mmcore install

    # run the app (with the demo devices)
    mmgui run --demo-config
    ```

    Or run it without installing anything permanently, using
    [uv](https://docs.astral.sh/uv/):

    ```sh
    uvx --from git+https://github.com/pymmcore-plus/pymmcore-gui mmgui
    ```

    pymmcore-gui isn't released on PyPI yet.  (There *is* a `pymmcore-gui` package
    there, but it's an outdated pre-release, so please install from GitHub.)

    pymmcore-gui requires a specific version of PyQt6, so install it in its own
    environment rather than next to another Qt application (or a PySide6 project).

    !!! tip

        The GitHub version may change at any time, so pin a specific commit if
        you add it to your own dependencies:
        `pymmcore-gui @ git+https://github.com/pymmcore-plus/pymmcore-gui@<commit>`

=== "Bundled application"

    Pre-built bundles include the Python runtime and all dependencies.  Download
    and extract the archive, then run the application.

    | Platform | Latest nightly build |
    | :--: | :--- |
    | Windows | [pymmgui-Windows.zip][win-zip] |
    | macOS | [pymmgui-macOS.zip][mac-zip] |

    [win-zip]: https://nightly.link/pymmcore-plus/pymmcore-gui/workflows/bundle/main/pymmgui-Windows.zip
    [mac-zip]: https://nightly.link/pymmcore-plus/pymmcore-gui/workflows/bundle/main/pymmgui-macOS.zip

    !!! warning "Unsigned app"

        Until the bundles are signed, your OS will warn you about running an app
        from an unidentified developer; you will need to accept that warning.

## Micro-Manager device adapters

Neither option includes the Micro-Manager device adapters (the drivers for your
hardware).  Install them in one of these ways:

- Use the **Devices > Install Devices...** menu in the GUI.
- Run `mmcore install` (or `uvx --from "pymmcore-plus[cli]" mmcore install`).
- Install a [Micro-Manager nightly build](https://micro-manager.org/Micro-Manager_Nightly_Builds).

See [Installing Micro-Manager device adapters](../pymmcore-plus/install.md#installing-micro-manager-device-adapters)
for details.

!!! note "License"

    The bundled application includes PyQt6 (GPL-3.0), so the bundle is
    distributed as a combined work under the GPL-3.0.  pymmcore-gui itself is
    BSD-3-Clause.
