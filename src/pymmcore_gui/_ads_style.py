"""QtAds-aware proxy style for use with QlementineStyle (or any custom QStyle).

QtAds uses a global stylesheet that conflicts with custom QStyle implementations
by creating a QStyleSheetStyle proxy on all descendant widgets. This module provides
a QProxyStyle that renders QtAds dock tabs and title bars through the QStyle system,
using QlementineStyle's actual theme tokens for full theme awareness.

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
from pymmcore_gui._qt.QtGui import QColor, QIcon, QPainter, QPainterPath, QPalette, QPen
from pymmcore_gui._qt.QtWidgets import (
    QProxyStyle,
    QStyle,
    QStyleOption,
    QStyleOptionToolButton,
    QWidget,
)

_ADS_ICON_MAP = {
    "tabsMenuButton": ":/ads/images/tabs-menu-button.svg",
    "tabCloseButton": ":/ads/images/close-button.svg",
    "detachGroupButton": ":/ads/images/detach-button.svg",
    "dockAreaCloseButton": ":/ads/images/close-button.svg",
    "dockAreaAutoHideButton": ":/ads/images/vs-pin-button.svg",
}

_ADS_BUTTONS = set(_ADS_ICON_MAP)


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

    def drawControl(self, element, option, painter, widget=None):
        if widget is not None:
            if element == QStyle.ControlElement.CE_ShapedFrame:
                active = widget.property("activeTab")
                if active is not None:
                    self._draw_dock_tab(option, painter, widget, bool(active))
                    return
                if widget.objectName() == "dockAreaTitleBar":
                    self._draw_title_bar(option, painter, widget)
                    return

            # Flat close button: suppress bevel background
            if (
                element == QStyle.ControlElement.CE_PushButtonBevel
                and widget.objectName() in _ADS_BUTTONS
            ):
                self._draw_ads_button_bg(option, painter)
                return

        super().drawControl(element, option, painter, widget)

    def drawPrimitive(self, element, option, painter, widget=None):
        if (
            element == QStyle.PrimitiveElement.PE_PanelButtonTool
            and widget is not None
            and widget.objectName() in _ADS_BUTTONS
        ):
            self._draw_ads_button_bg(option, painter)
            return
        super().drawPrimitive(element, option, painter, widget)

    def drawComplexControl(self, control, option, painter, widget=None):
        if (
            control == QStyle.ComplexControl.CC_ToolButton
            and widget is not None
            and widget.objectName() == "tabsMenuButton"
            and isinstance(option, QStyleOptionToolButton)
        ):
            option.features &= ~QStyleOptionToolButton.ToolButtonFeature.HasMenu
        super().drawComplexControl(control, option, painter, widget)

    def polish(self, obj):
        # Call base style first, then apply our overrides
        result = super().polish(obj)
        if isinstance(obj, QWidget):
            name = obj.objectName()
            if name in _ADS_ICON_MAP:
                icon = QIcon(_ADS_ICON_MAP[name])
                if not icon.isNull() and hasattr(obj, "setIcon"):
                    obj.setIcon(icon)
            if name in _ADS_BUTTONS and hasattr(obj, "setFlat"):
                obj.setFlat(True)
            # Set title bar bg color on intermediate widgets so auto-fill
            # paints the correct color instead of palette(Window)
            qlm = self._qlementine()
            if qlm is not None:
                tb_bg = qlm.tabBarBackgroundColor(MouseState.Normal)
            else:
                tb_bg = obj.palette().color(
                    QPalette.ColorRole.Dark
                )
            if obj.property("activeTab") is not None:
                self._set_widget_bg(obj, tb_bg)
            if name == "tabsContainerWidget":
                self._set_widget_bg(obj, tb_bg)
            if name == "dockAreaTitleBar":
                from pymmcore_gui._qt.QtWidgets import QScrollArea

                for child in obj.findChildren(QScrollArea):
                    self._set_widget_bg(child, tb_bg)
                    self._set_widget_bg(child.viewport(), tb_bg)
        return result

    @staticmethod
    def _set_widget_bg(widget: QWidget, color: QColor) -> None:
        pal = widget.palette()
        pal.setColor(QPalette.ColorRole.Window, color)
        widget.setPalette(pal)
        widget.setAutoFillBackground(True)

    # ---- Private drawing helpers ----

    def _draw_dock_tab(self, option, painter, widget, is_active):
        rect = QRectF(option.rect)
        qlm = self._qlementine()
        mouse = _mouse_state(option)
        sel = SelectionState.Selected if is_active else SelectionState.NotSelected
        radius = 6.0

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        if qlm is not None:
            bg = qlm.tabBackgroundColor(mouse, sel)
        else:
            palette = widget.palette()
            bg = palette.color(
                QPalette.ColorRole.Window
                if is_active
                else QPalette.ColorRole.Dark
            )

        if is_active:
            # Rounded top corners, open bottom — connects to content
            path = QPainterPath()
            path.moveTo(rect.left(), rect.bottom() + 1)
            path.lineTo(rect.left(), rect.top() + radius)
            path.quadTo(
                rect.left(), rect.top(), rect.left() + radius, rect.top()
            )
            path.lineTo(rect.right() - radius, rect.top())
            path.quadTo(
                rect.right(), rect.top(), rect.right(), rect.top() + radius
            )
            path.lineTo(rect.right(), rect.bottom() + 1)
            path.closeSubpath()
            painter.fillPath(path, bg)
        elif bg.alpha() > 0:
            # Inactive with visible bg (hovered state)
            painter.setBrush(bg)
            painter.drawRoundedRect(rect, radius, radius)

        painter.restore()

        # Update label text colors
        self._update_tab_label_color(widget, is_active, mouse)

    def _update_tab_label_color(self, tab_widget, is_active, mouse):
        qlm = self._qlementine()
        sel = SelectionState.Selected if is_active else SelectionState.NotSelected
        if qlm is not None:
            target = qlm.tabForegroundColor(mouse, sel)
        else:
            palette = tab_widget.palette()
            role = (
                QPalette.ColorRole.WindowText
                if is_active
                else QPalette.ColorRole.PlaceholderText
            )
            target = palette.color(role)

        for child in tab_widget.children():
            if (
                isinstance(child, QWidget)
                and child.objectName() == "dockWidgetTabLabel"
            ):
                current = child.palette().color(QPalette.ColorRole.WindowText)
                if current != target:
                    pal = child.palette()
                    pal.setColor(QPalette.ColorRole.WindowText, target)
                    child.setPalette(pal)

    def _draw_title_bar(self, option, painter, widget):
        rect = option.rect
        qlm = self._qlementine()

        painter.save()

        if qlm is not None:
            bg = qlm.tabBarBackgroundColor(MouseState.Normal)
            shadow = qlm.tabBarBottomShadowColor()
        else:
            palette = widget.palette()
            bg = palette.color(QPalette.ColorRole.Dark)
            shadow = palette.color(QPalette.ColorRole.Mid)

        painter.fillRect(rect, bg)

        # Bottom separator
        painter.setPen(QPen(shadow, 1))
        painter.drawLine(
            rect.left(), rect.bottom(), rect.right(), rect.bottom()
        )

        painter.restore()

    def _draw_ads_button_bg(self, option: QStyleOption, painter: QPainter):
        state = option.state
        if state & QStyle.StateFlag.State_Sunken:
            alpha = 0.12
        elif state & QStyle.StateFlag.State_MouseOver:
            alpha = 0.07
        else:
            return

        text_color = option.palette.color(QPalette.ColorRole.WindowText)
        color = QColor(text_color)
        color.setAlphaF(alpha)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(QRectF(option.rect), 4, 4)
        painter.restore()
