"""PoC: QtAds-based workbench with 4 fixed regions (left/center/bottom/right).

Run standalone:  python -m pymmcore_gui._layout._ads_workbench_poc
"""

from __future__ import annotations

from weakref import WeakKeyDictionary

from superqt import QIconifyIcon

from pymmcore_gui._qt.QtAds import (
    CDockAreaWidget,
    CDockManager,
    CDockWidget,
    DockWidgetArea,
)
from pymmcore_gui._qt.QtCore import QEvent, QObject, Qt, QTimer, Signal
from pymmcore_gui._qt.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ._enums import PanelAlignment

_PERIPHERALS = ("left", "bottom", "right")
_DEFAULT_SIDEBAR_WIDTH = 250
_DEFAULT_PANEL_HEIGHT = 200
_MIN_SIDEBAR_WIDTH = 170
_MIN_PANEL_HEIGHT = 80

# Icon pairs: (on_icon_key, off_icon_key)
_TOGGLE_ICONS = {
    "left": ("codicon:layout-sidebar-left", "codicon:layout-sidebar-left-off"),
    "bottom": ("codicon:layout-panel", "codicon:layout-panel-off"),
    "right": (
        "codicon:layout-sidebar-right",
        "codicon:layout-sidebar-right-off",
    ),
}
_ALIGN_ICONS = {
    PanelAlignment.LEFT: "codicon:layout-panel-left",
    PanelAlignment.CENTER: "codicon:layout-panel-center",
    PanelAlignment.RIGHT: "codicon:layout-panel-right",
    PanelAlignment.JUSTIFY: "codicon:layout-panel-justify",
}
_ALIGN_CYCLE = [
    PanelAlignment.LEFT,
    PanelAlignment.CENTER,
    PanelAlignment.RIGHT,
    PanelAlignment.JUSTIFY,
]

DWA = DockWidgetArea

# Area values from the DockWidgetArea enum used in QLabel properties
_CENTER_AREA_VALUE = 16  # CenterDockWidgetArea
_NSEW_AREA_VALUES = {1, 2, 4, 8}  # Left, Right, Top, Bottom


class _ReshowFilter(QObject):
    """Re-show a widget immediately when it gets hidden."""

    _active = False

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Hide and not self._active:
            self._active = True
            obj.setVisible(True)  # type: ignore[arg-type]
            self._active = False
        return False


def _suppress_overlay_indicators(app: QApplication) -> None:
    """Suppress NSEW indicators on all overlay cross widgets.

    NSEW labels get ``setFixedSize(0, 0)``; Center labels get a
    ``_ReshowFilter`` so they can never be hidden.
    """
    reshow = _ReshowFilter(app)  # prevent GC

    for w in app.topLevelWidgets():
        for label in w.findChildren(QLabel, "DockWidgetAreaLabel"):
            area_val = label.property("dockWidgetArea")
            if area_val in _NSEW_AREA_VALUES:
                label.setFixedSize(0, 0)
            elif area_val == _CENTER_AREA_VALUE:
                label.installEventFilter(reshow)


class AdsWorkbench(QWidget):
    """QtAds-based workbench with left/center/bottom/right regions."""

    visibilityChanged = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._panel_alignment = PanelAlignment.CENTER
        self._rebuilding = False

        self._areas: dict[str, CDockAreaWidget] = {}
        self._toggle_buttons: dict[str, QToolButton] = {}
        self._user_widgets: list[CDockWidget] = []
        self._widget_region: WeakKeyDictionary[CDockWidget, str] = WeakKeyDictionary()
        # Saved pixel sizes: left/right store width, bottom stores height
        self._saved_sizes: dict[str, int] = {
            "left": _DEFAULT_SIDEBAR_WIDTH,
            "right": _DEFAULT_SIDEBAR_WIDTH,
            "bottom": _DEFAULT_PANEL_HEIGHT,
        }
        self._collapsed: dict[str, bool] = dict.fromkeys(_PERIPHERALS, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._dock_manager = CDockManager(self)
        self._dock_manager.setStyleSheet("")
        layout.addWidget(self._dock_manager, 1)

        # Hidden anchors: keep each region alive even when all user
        # widgets are dragged away.  NoTab makes them invisible.
        self._anchors: dict[str, CDockWidget] = {}
        for key in ("center", *_PERIPHERALS):
            dw = CDockWidget(f"_anchor_{key}", self)
            dw.setWidget(QWidget())
            for feat in (
                CDockWidget.DockWidgetFeature.NoTab,
                CDockWidget.DockWidgetFeature.DockWidgetFloatable,
                CDockWidget.DockWidgetFeature.DockWidgetMovable,
                CDockWidget.DockWidgetFeature.DockWidgetClosable,
                CDockWidget.DockWidgetFeature.DockWidgetPinnable,
            ):
                dw.setFeature(feat, feat == CDockWidget.DockWidgetFeature.NoTab)
            self._anchors[key] = dw

        self._areas["center"] = self._dock_manager.setCentralWidget(
            self._anchors["center"]
        )

        # Post-drop validation
        self._dock_manager.dockAreaCreated.connect(self._on_area_created)
        self._dock_manager.floatingWidgetCreated.connect(self._on_floating_created)

        toggle_bar = self._create_toggle_bar()
        layout.addWidget(toggle_bar)

    # ------------------------------------------------------------------
    #  Layout building
    # ------------------------------------------------------------------

    def _build_regions(self, alignment: PanelAlignment) -> None:
        """(Re)build the peripheral splitter tree for *alignment*.

        Takes the current ``_user_widgets`` list, groups them by their
        tracked region, and adds them in the order that produces the
        desired splitter nesting.  The *first* widget in each region
        creates the CDockAreaWidget; subsequent ones are tabbed in.
        """
        self._rebuilding = True
        self.setUpdatesEnabled(False)
        try:
            # 0. Save current sizes before tearing down
            self._save_sizes()

            # 1. Snapshot current region assignments
            for dw in self._user_widgets:
                area = dw.dockAreaWidget()
                region = self._region_for_area(area) if area else None
                if region and region in _PERIPHERALS:
                    self._widget_region[dw] = region

            # 2. Group widgets by region
            groups: dict[str, list[CDockWidget]] = {k: [] for k in _PERIPHERALS}
            for dw in self._user_widgets:
                groups[self._widget_region.get(dw, "left")].append(dw)

            # 3. Remove all peripheral widgets (user + anchors)
            for key in _PERIPHERALS:
                area = self._areas.get(key)
                if area is None:
                    continue
                try:
                    dws = list(area.dockWidgets())
                except RuntimeError:
                    continue  # C++ object already deleted
                for dw in dws:
                    self._dock_manager.removeDockWidget(dw)
            # Also remove anchors that may not be in an area anymore
            for key in _PERIPHERALS:
                anchor = self._anchors[key]
                try:
                    if anchor.dockAreaWidget() is not None:
                        self._dock_manager.removeDockWidget(anchor)
                except RuntimeError:
                    pass

            # 4. Clear stale area refs
            for key in _PERIPHERALS:
                self._areas.pop(key, None)

            # 5. Add first widget of each region in alignment order,
            #    then tab the rest
            self._add_in_order(alignment, groups)

            # 6. Apply restrictions
            self._apply_area_restrictions()

            # 7. Restore saved sizes
            self._restore_sizes()

            # 8. Make peripheral areas collapsible and monitor splitters
            self._wire_splitters()

            # 9. Patch tabs menus to exclude anchor entries
            self._patch_tabs_menus()
        finally:
            self._rebuilding = False
            self.setUpdatesEnabled(True)

    def _add_in_order(
        self,
        alignment: PanelAlignment,
        groups: dict[str, list[CDockWidget]],
    ) -> None:
        """Add the first widget per region in the right order for *alignment*.

        The order of ``addDockWidget`` calls controls the internal splitter
        tree that QtAds builds.
        """
        center_area = self._areas["center"]

        # Define the add-sequence for each alignment.
        # Each entry is (region_key, DockWidgetArea, target_area_or_None).
        # target_area_or_None=center_area means "add relative to central area"
        # (produces a nested V-splitter around central for CENTER alignment).
        if alignment == PanelAlignment.CENTER:
            seq = [
                ("left", DWA.LeftDockWidgetArea, None),
                ("bottom", DWA.BottomDockWidgetArea, center_area),
                ("right", DWA.RightDockWidgetArea, None),
            ]
        elif alignment == PanelAlignment.JUSTIFY:
            seq = [
                ("left", DWA.LeftDockWidgetArea, None),
                ("right", DWA.RightDockWidgetArea, None),
                ("bottom", DWA.BottomDockWidgetArea, None),
            ]
        elif alignment == PanelAlignment.LEFT:
            seq = [
                ("left", DWA.LeftDockWidgetArea, None),
                ("bottom", DWA.BottomDockWidgetArea, None),
                ("right", DWA.RightDockWidgetArea, None),
            ]
        else:  # RIGHT
            seq = [
                ("right", DWA.RightDockWidgetArea, None),
                ("bottom", DWA.BottomDockWidgetArea, None),
                ("left", DWA.LeftDockWidgetArea, None),
            ]

        for key, dock_area, target in seq:
            # Anchor always goes first — it creates/defines the area
            anchor = self._anchors[key]
            self._areas[key] = self._dock_manager.addDockWidget(
                dock_area, anchor, target
            )
            # User widgets tab into the anchor's area
            for dw in groups.get(key, []):
                self._dock_manager.addDockWidgetTabToArea(dw, self._areas[key])

    def _apply_area_restrictions(self) -> None:
        """Restrict drops to tab-only within peripheral areas."""
        for key in _PERIPHERALS:
            area = self._areas.get(key)
            if area is not None:
                area.setAllowedAreas(DWA.CenterDockWidgetArea)
        self._areas["center"].setAllowedAreas(DWA.NoDockWidgetArea)

        # Suppress NSEW overlay indicators (only needed once)
        if not hasattr(self, "_overlays_suppressed") and (
            overlay := self._dock_manager.containerOverlay()
        ):
            overlay.showOverlay(self._dock_manager)
            overlay.hideOverlay()
            if app := QApplication.instance():
                app.processEvents()
                _suppress_overlay_indicators(app)
            self._overlays_suppressed = True

    # ------------------------------------------------------------------
    #  Size persistence
    # ------------------------------------------------------------------

    def _save_sizes(self) -> None:
        """Save current pixel sizes of peripheral regions."""
        for key in _PERIPHERALS:
            area = self._areas.get(key)
            if area is None:
                continue
            try:
                if not area.isVisible():
                    continue
                sz = area.width() if key in ("left", "right") else area.height()
                if sz > 0:
                    self._saved_sizes[key] = sz
            except RuntimeError:
                pass

    def _restore_sizes(self) -> None:
        """Restore saved pixel sizes after layout rebuild.

        For left/right: set width in the parent (horizontal) splitter.
        For bottom: set height in the parent (vertical) splitter.
        The "donor" that absorbs the size change is always the largest
        sibling — typically the central editor area.
        """
        for key in _PERIPHERALS:
            area = self._areas.get(key)
            target_px = self._saved_sizes.get(key, 0)
            if area is None or target_px <= 0:
                continue
            try:
                splitter = area.parentSplitter()
                if splitter is None:
                    continue
                idx = splitter.indexOf(area)
                if idx < 0:
                    continue
                sizes = list(splitter.sizes())
                if not sizes or idx >= len(sizes):
                    continue

                old = sizes[idx]
                delta = target_px - old
                if delta == 0:
                    continue

                # Take/give space from the largest sibling
                others = [(i, sizes[i]) for i in range(len(sizes)) if i != idx]
                if not others:
                    continue
                donor_idx = max(others, key=lambda x: x[1])[0]
                sizes[idx] = target_px
                sizes[donor_idx] = max(1, sizes[donor_idx] - delta)
                splitter.setSizes(sizes)
            except RuntimeError:
                pass

    # ------------------------------------------------------------------
    #  Splitter-drag collapse
    # ------------------------------------------------------------------

    def _wire_splitters(self) -> None:
        """Set minimum sizes and connect splitterMoved on parent splitters.

        QSplitter natively snaps a collapsible widget to zero when dragged
        below about half its minimum size.  We just set the minimum to
        ``_MIN_REGION_SIZE`` and ``setCollapsible(True)`` — then monitor
        ``splitterMoved`` to track collapsed state.
        """
        seen: set[int] = set()
        for key in _PERIPHERALS:
            area = self._areas.get(key)
            if area is None:
                continue
            if key in ("left", "right"):
                area.setMinimumWidth(_MIN_SIDEBAR_WIDTH)
                area.setMinimumHeight(0)
            else:
                area.setMinimumHeight(_MIN_PANEL_HEIGHT)
                area.setMinimumWidth(0)
            try:
                splitter = area.parentSplitter()
            except RuntimeError:
                continue
            if splitter is None:
                continue
            idx = splitter.indexOf(area)
            if idx >= 0:
                splitter.setCollapsible(idx, True)
            sid = id(splitter)
            if sid not in seen:
                seen.add(sid)
                splitter.splitterMoved.connect(self._on_splitter_moved)

    def _patch_tabs_menus(self) -> None:
        """Remove anchor entries from each dock area's tabs dropdown menu.

        QtAds's ``onTabsMenuAboutToShow`` rebuilds the menu from the tab
        bar, including NoTab anchors (they're "open" even if invisible).
        We connect a second handler that runs *after* the QtAds handler
        (same signal, later connection order) and strips anchor actions.
        """
        anchor_titles = {dw.windowTitle() for dw in self._anchors.values()}
        for key in _PERIPHERALS:
            area = self._areas.get(key)
            if area is None:
                continue
            try:
                tb = area.titleBar()
                if tb is None:
                    continue
                menu_btn = tb.findChild(QToolButton, "tabsMenuButton")
                if menu_btn is None:
                    continue
                menu = menu_btn.menu()
                if menu is None:
                    continue
            except RuntimeError:
                continue
            # Connect AFTER QtAds's own aboutToShow handler
            menu.aboutToShow.connect(
                lambda m=menu, names=anchor_titles: self._strip_anchor_actions(m, names)
            )

    @staticmethod
    def _strip_anchor_actions(menu: QWidget, anchor_titles: set[str]) -> None:
        for action in menu.actions():  # type: ignore[union-attr]
            if action.text() in anchor_titles:
                menu.removeAction(action)  # type: ignore[union-attr]

    def _on_splitter_moved(self) -> None:
        """Track collapsed state from native QSplitter snap-to-collapse."""
        if self._rebuilding:
            return
        for key in _PERIPHERALS:
            area = self._areas.get(key)
            if area is None:
                continue
            try:
                splitter = area.parentSplitter()
                if splitter is None:
                    continue
                idx = splitter.indexOf(area)
                if idx < 0:
                    continue
                sz = splitter.sizes()[idx]
            except (RuntimeError, IndexError):
                continue

            was_collapsed = self._collapsed.get(key, False)
            is_collapsed = sz == 0

            if is_collapsed != was_collapsed:
                self._collapsed[key] = is_collapsed
            min_sz = (
                _MIN_SIDEBAR_WIDTH if key in ("left", "right") else _MIN_PANEL_HEIGHT
            )
            if not is_collapsed and sz >= min_sz:
                self._saved_sizes[key] = sz
        self._sync_button_states()

    def _region_for_area(self, area: CDockAreaWidget | None) -> str | None:
        for key, a in self._areas.items():
            try:
                if a is area:
                    return key
            except RuntimeError:
                continue  # C++ object deleted
        return None

    # ------------------------------------------------------------------
    #  Post-drop validation
    # ------------------------------------------------------------------

    def _on_area_created(self, area: object) -> None:
        if self._rebuilding:
            return
        QTimer.singleShot(0, self._validate_layout)

    def _on_floating_created(self, floating: object) -> None:
        if self._rebuilding:
            return
        QTimer.singleShot(0, self._validate_layout)

    def _validate_layout(self) -> None:
        """Move rogue widgets home; update tracking for valid tab-drops."""
        valid = set(self._areas.values())
        for dw in self._user_widgets:
            area = dw.dockAreaWidget()
            if area is not None and area in valid:
                region = self._region_for_area(area)
                if region and region in _PERIPHERALS:
                    self._widget_region[dw] = region
            else:
                target_key = self._widget_region.get(dw, "left")
                target_area = self._areas.get(target_key)
                if target_area is not None:
                    self._dock_manager.addDockWidgetTabToArea(dw, target_area)
        self._sync_button_states()

    # ------------------------------------------------------------------
    #  Panel alignment
    # ------------------------------------------------------------------

    @property
    def panelAlignment(self) -> PanelAlignment:
        return self._panel_alignment

    def setPanelAlignment(self, alignment: PanelAlignment) -> None:
        if alignment == self._panel_alignment:
            return
        self._panel_alignment = alignment
        self._build_regions(alignment)
        if hasattr(self, "_align_button"):
            self._align_button.setIcon(QIconifyIcon(_ALIGN_ICONS[alignment]))
            self._align_button.setToolTip(
                f"Panel Alignment: {alignment.value.capitalize()}"
            )

    def cyclePanelAlignment(self) -> None:
        cur = self._panel_alignment
        idx = _ALIGN_CYCLE.index(cur) if cur in _ALIGN_CYCLE else -1
        self.setPanelAlignment(_ALIGN_CYCLE[(idx + 1) % len(_ALIGN_CYCLE)])

    # ------------------------------------------------------------------
    #  Toggle buttons
    # ------------------------------------------------------------------

    def _create_toggle_bar(self) -> QWidget:
        bar = QWidget()
        outer = QHBoxLayout(bar)
        outer.setContentsMargins(4, 2, 4, 2)
        outer.setSpacing(0)
        outer.addStretch()

        # All buttons together in one group on the right
        group = QHBoxLayout()
        group.setSpacing(0)

        self._align_button = QToolButton()
        self._align_button.setIcon(QIconifyIcon(_ALIGN_ICONS[self._panel_alignment]))
        self._align_button.setToolTip(
            f"Panel Alignment: {self._panel_alignment.value.capitalize()}"
        )
        self._align_button.setAutoRaise(True)
        self._align_button.clicked.connect(self.cyclePanelAlignment)
        group.addWidget(self._align_button)

        for key in _PERIPHERALS:
            on_key, off_key = _TOGGLE_ICONS[key]
            btn = QToolButton()
            btn.setIcon(QIconifyIcon(on_key))
            btn.setAutoRaise(True)
            btn.setToolTip(f"Toggle {key.capitalize()}")
            btn.setProperty("iconOn", on_key)
            btn.setProperty("iconOff", off_key)
            btn.clicked.connect(lambda _, k=key: self._on_toggle_clicked(k))
            self._toggle_buttons[key] = btn
            group.addWidget(btn)

        outer.addLayout(group)
        return bar

    def _on_toggle_clicked(self, region: str) -> None:
        """Toggle a region between collapsed and restored."""
        show = self._collapsed.get(region, False)  # if collapsed, show it
        self._collapsed[region] = not show

        area = self._areas.get(region)
        if area is None:
            return

        if show:
            # Restore: show all widgets and set splitter to saved size
            try:
                for dw in area.dockWidgets():
                    dw.toggleView(True)
            except RuntimeError:
                return
            self._restore_region_size(region)
        else:
            # Collapse: snap splitter to 0
            try:
                splitter = area.parentSplitter()
                if splitter is not None:
                    idx = splitter.indexOf(area)
                    if idx >= 0:
                        sizes = list(splitter.sizes())
                        others = [(i, sizes[i]) for i in range(len(sizes)) if i != idx]
                        if others:
                            donor = max(others, key=lambda x: x[1])[0]
                            sizes[donor] += sizes[idx]
                        sizes[idx] = 0
                        splitter.setSizes(sizes)
            except RuntimeError:
                pass
        self._sync_button_states()

    def _restore_region_size(self, key: str) -> None:
        """Set a region's splitter size back to its saved value."""
        area = self._areas.get(key)
        min_sz = _MIN_SIDEBAR_WIDTH if key in ("left", "right") else _MIN_PANEL_HEIGHT
        target = max(self._saved_sizes.get(key, min_sz), min_sz)
        if area is None:
            return
        try:
            splitter = area.parentSplitter()
            if splitter is None:
                return
            idx = splitter.indexOf(area)
            if idx < 0:
                return
            sizes = list(splitter.sizes())
            others = [(i, sizes[i]) for i in range(len(sizes)) if i != idx]
            if not others:
                return
            donor = max(others, key=lambda x: x[1])[0]
            sizes[idx] = target
            sizes[donor] = max(1, sizes[donor] - target)
            splitter.setSizes(sizes)
        except RuntimeError:
            pass

    def _sync_button_states(self) -> None:
        if self._rebuilding:
            return
        for key in _PERIPHERALS:
            btn = self._toggle_buttons.get(key)
            if btn is None:
                continue
            visible = not self._collapsed.get(key, False)
            icon_key = btn.property("iconOn" if visible else "iconOff")
            if icon_key:
                btn.setIcon(QIconifyIcon(icon_key))
        self.visibilityChanged.emit()

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def addDockWidget(
        self,
        title: str,
        widget: QWidget,
        region: str = "left",
    ) -> CDockWidget:
        """Add *widget* as a new tab in *region* ('left', 'bottom', 'right')."""
        if region not in _PERIPHERALS:
            raise ValueError(f"region must be one of {_PERIPHERALS}, got {region!r}")

        dw = CDockWidget(title, self)
        dw.setWidget(widget)
        dw.setFeature(CDockWidget.DockWidgetFeature.DockWidgetFloatable, False)
        dw.setFeature(CDockWidget.DockWidgetFeature.DockWidgetClosable, False)
        dw.setFeature(CDockWidget.DockWidgetFeature.DockWidgetPinnable, False)
        dw.viewToggled.connect(lambda _: self._sync_button_states())

        self._user_widgets.append(dw)
        self._widget_region[dw] = region

        area = self._areas.get(region)
        if area is not None:
            self._dock_manager.addDockWidgetTabToArea(dw, area)

        return dw

    def buildInitialLayout(self) -> None:
        """Build the splitter tree after all initial widgets have been added."""
        self._build_regions(self._panel_alignment)


# ======================================================================
#  Standalone runner
# ======================================================================


def _add_test_widgets(wb: AdsWorkbench) -> None:
    tests = [
        ("Explorer", "#2d4a2d", "left"),
        ("Search", "#4a2d2d", "left"),
        ("Terminal", "#2d2d4a", "bottom"),
        ("Problems", "#4a4a2d", "bottom"),
        ("Outline", "#2d4a4a", "right"),
        ("Debug", "#4a2d4a", "right"),
    ]
    for title, color, region in tests:
        label = QLabel(f"  {title} content  ")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"background: {color}; color: #ccc; padding: 20px; font-size: 14px;"
        )
        label.setMinimumSize(100, 60)
        wb.addDockWidget(title, label, region)


if __name__ == "__main__":
    import sys

    from pymmcore_gui._ads_style import (
        AdsAwareQlementineStyle,
        apply_dark_theme,
    )

    app = QApplication(sys.argv)

    style = AdsAwareQlementineStyle()
    apply_dark_theme(style)
    app.setStyle(style)

    CDockManager.setConfigFlag(CDockManager.eConfigFlag.OpaqueSplitterResize, True)
    CDockManager.setConfigFlag(CDockManager.eConfigFlag.DockAreaHasCloseButton, False)
    CDockManager.setConfigFlag(CDockManager.eConfigFlag.DockAreaHasUndockButton, False)
    CDockManager.setConfigFlag(CDockManager.eConfigFlag.AlwaysShowTabs, True)
    CDockManager.setConfigFlag(CDockManager.eConfigFlag.FocusHighlighting, True)

    w = AdsWorkbench()
    w.setWindowTitle("QtAds Workbench PoC")
    w.resize(1200, 800)

    _add_test_widgets(w)
    w.buildInitialLayout()

    w.show()
    sys.exit(app.exec())
