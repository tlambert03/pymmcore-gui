"""QtAds-aware proxy style for use with QlementineStyle.

QtAds applies a global stylesheet to CDockManager, which creates a QStyleSheetStyle
proxy that intercepts painting for all descendant widgets — breaking custom QStyle
implementations like QlementineStyle. This module provides a QProxyStyle that renders
QtAds dock tabs and title bars through the QStyle system, using QlementineStyle's
theme tokens for full theme awareness.

Usage::

    style = AdsAwareStyle(QlementineStyle())
    app.setStyle(style)
    dock_manager.setStyleSheet("")  # remove QtAds default CSS
"""

from __future__ import annotations

from pymmcore_gui._qt.Qlementine import (
    MouseState,
    QlementineStyle,
    SelectionState,
)
from pymmcore_gui._qt.QtCore import QRectF, Qt
from pymmcore_gui._qt.QtGui import QColor, QPalette, QPen
from pymmcore_gui._qt.QtWidgets import (
    QProxyStyle,
    QStyle,
    QStyleOption,
    QStyleOptionToolButton,
    QWidget,
)

# Icon keys for QtAds buttons, resolved via pyconify at runtime.
_ADS_ICON_MAP = {
    "tabCloseButton": "codicon:close",
    "tabsMenuButton": "codicon:chevron-down",
    "detachGroupButton": "codicon:link-external",
    "dockAreaCloseButton": "codicon:close",
    "dockAreaAutoHideButton": "codicon:pinned",
}

_svg_cache: dict[str, bytes] = {}


def _ads_icon_svg(name: str) -> bytes:
    """Get cached SVG bytes for an ads button icon."""
    if name not in _svg_cache:
        import pyconify

        _svg_cache[name] = pyconify.svg(_ADS_ICON_MAP[name])
    return _svg_cache[name]


def _mouse_state(option: QStyleOption) -> MouseState:
    """Map QStyle state flags to Qlementine MouseState."""
    state = option.state
    if not (state & QStyle.StateFlag.State_Enabled):
        return MouseState.Disabled
    if state & QStyle.StateFlag.State_Sunken:
        return MouseState.Pressed
    if state & QStyle.StateFlag.State_MouseOver:
        return MouseState.Hovered
    return MouseState.Normal


class AdsAwareStyle(QProxyStyle):
    """Proxy style adding QtAds dock widget awareness to QlementineStyle."""

    def _qlementine(self) -> QlementineStyle | None:
        style = self.baseStyle()
        return style if isinstance(style, QlementineStyle) else None

    # ---- Drawing overrides ----

    def drawControl(self, element, option, painter, widget=None):
        if element == QStyle.ControlElement.CE_ShapedFrame and widget:
            active = widget.property("activeTab")
            if active is not None:
                self._draw_dock_tab(option, painter, widget, bool(active))
                return
            if widget.objectName() == "dockAreaTitleBar":
                self._draw_title_bar(option, painter, widget)
                return
        super().drawControl(element, option, painter, widget)

    def drawComplexControl(self, control, option, painter, widget=None):
        # Suppress the double-chevron menu indicator on the tabs menu
        if (
            control == QStyle.ComplexControl.CC_ToolButton
            and widget is not None
            and widget.objectName() == "tabsMenuButton"
            and isinstance(option, QStyleOptionToolButton)
        ):
            option.features &= ~QStyleOptionToolButton.ToolButtonFeature.HasMenu
        super().drawComplexControl(control, option, painter, widget)

    # ---- Widget polishing ----

    def polish(self, obj):
        result = super().polish(obj)
        if not isinstance(obj, QWidget):
            return result

        name = obj.objectName()

        # Set themed icons on QtAds buttons.
        # Qlementine re-colorizes at paint time when AutoIconColor is
        # enabled (set on the style or per-widget by the caller).
        if name in _ADS_ICON_MAP and hasattr(obj, "setIcon"):
            qlm = self._qlementine()
            if qlm is not None:
                obj.setIcon(qlm.makeThemedIconFromData(_ads_icon_svg(name)))

        # Flat close buttons so Qlementine skips the button bevel
        if name == "tabCloseButton" and hasattr(obj, "setFlat"):
            obj.setFlat(True)

        # Set title bar background on intermediate widgets that would
        # otherwise auto-fill with palette(Window), covering the
        # darker title bar painted by _draw_title_bar.
        if obj.property("activeTab") is not None or name == "tabsContainerWidget":
            self._set_widget_bg(obj, self._title_bar_bg(obj))
        elif name == "dockAreaTitleBar":
            tb_bg = self._title_bar_bg(obj)
            from pymmcore_gui._qt.QtWidgets import QScrollArea

            for child in obj.findChildren(QScrollArea):
                self._set_widget_bg(child, tb_bg)
                self._set_widget_bg(child.viewport(), tb_bg)

        return result

    # ---- Private helpers ----

    def _title_bar_bg(self, widget: QWidget) -> QColor:
        qlm = self._qlementine()
        if qlm is not None:
            return qlm.tabBarBackgroundColor(MouseState.Normal)
        return widget.palette().color(QPalette.ColorRole.Dark)

    @staticmethod
    def _set_widget_bg(widget: QWidget, color: QColor) -> None:
        pal = widget.palette()
        pal.setColor(QPalette.ColorRole.Window, color)
        widget.setPalette(pal)
        widget.setAutoFillBackground(True)

    def _draw_dock_tab(self, option, painter, widget, is_active):
        qlm = self._qlementine()
        mouse = _mouse_state(option)
        sel = SelectionState.Selected if is_active else SelectionState.NotSelected

        if qlm is not None:
            bg = qlm.tabBackgroundColor(mouse, sel)
        else:
            palette = widget.palette()
            bg = palette.color(
                QPalette.ColorRole.Window if is_active else QPalette.ColorRole.Dark
            )

        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        if is_active:
            painter.fillRect(option.rect, bg)
        else:
            if bg.alpha() > 0:
                painter.setBrush(bg)
                painter.drawRoundedRect(QRectF(option.rect), 6.0, 6.0)
            # Separator between inactive tabs
            sep = QColor(widget.palette().color(QPalette.ColorRole.WindowText))
            sep.setAlphaF(0.2)
            painter.setPen(QPen(sep, 1))
            x = int(option.rect.right())
            painter.drawLine(
                x,
                option.rect.top() + 5,
                x,
                option.rect.bottom() - 5,
            )

        painter.restore()
        self._update_tab_label_color(widget, mouse, sel)

    def _update_tab_label_color(self, tab, mouse, sel):
        qlm = self._qlementine()
        if qlm is not None:
            target = qlm.tabForegroundColor(mouse, sel)
        else:
            palette = tab.palette()
            role = (
                QPalette.ColorRole.WindowText
                if sel == SelectionState.Selected
                else QPalette.ColorRole.PlaceholderText
            )
            target = palette.color(role)

        for child in tab.children():
            if (
                isinstance(child, QWidget)
                and child.objectName() == "dockWidgetTabLabel"
                and child.palette().color(QPalette.ColorRole.WindowText) != target
            ):
                pal = child.palette()
                pal.setColor(QPalette.ColorRole.WindowText, target)
                child.setPalette(pal)

    def _draw_title_bar(self, option, painter, widget):
        qlm = self._qlementine()
        if qlm is not None:
            bg = qlm.tabBarBackgroundColor(MouseState.Normal)
            shadow = qlm.tabBarBottomShadowColor()
        else:
            palette = widget.palette()
            bg = palette.color(QPalette.ColorRole.Dark)
            shadow = palette.color(QPalette.ColorRole.Mid)

        painter.save()
        painter.fillRect(option.rect, bg)
        painter.setPen(QPen(shadow, 1))
        painter.drawLine(
            option.rect.left(),
            option.rect.bottom(),
            option.rect.right(),
            option.rect.bottom(),
        )
        painter.restore()
