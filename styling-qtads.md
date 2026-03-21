# Styling qtads with Qlementine Design System

## QtAds Dock Area Title Bar and Tabs Widget Structure

Based on my thorough analysis of the QtAds source code, here's the exact widget structure:

CDockAreaTitleBar (/Users/talley/dev/self/PyQt6Ads/Qt-Advanced-Docking-System/src/DockAreaTitleBar.h and .cpp)

Type: QFrame subclass
Object Name: "dockAreaTitleBar"
Layout: QBoxLayout (LeftToRight), margins 0, spacing 0
Size Policy: Preferred width, Fixed height

Child Widgets (in layout order):

1. CDockAreaTabBar - The scrollable tab container (created by createTabBar())

  - Object name: (none explicitly set)
  - Size policy: Maximum width, Preferred height
  - Added only if not in TabsAtBottom mode

1. CElidingLabel - Auto-hide title label

  - Object name: "autoHideTitleLabel"
  - Only visible in auto-hide areas or when TabsAtBottom is true
  - Created by createAutoHideTitleLabel()

1. CSpacerWidget - Spacer for drag handling

  - No explicit object name
  - Expands to fill available space

1. CTitleBarButton (TabsMenuButton)

  - Object name: "tabsMenuButton"
  - Type: QToolButton subclass
  - Icon: List/tabs menu icon (16px)
  - PopupMode: InstantPopup
  - Auto-raise: true

1. CTitleBarButton (UndockButton)

  - Object name: "detachGroupButton"
  - Icon: Detach/undock icon (16px)
  - Auto-raise: true

1. CTitleBarButton (AutoHideButton)

  - Object name: "dockAreaAutoHideButton"
  - Checkable: Depends on AutoHideButtonCheckable config
  - Auto-raise: true

1. CTitleBarButton (MinimizeButton)

  - Object name: "dockAreaMinimizeButton"
  - Initially hidden
  - Only visible in auto-hide mode

1. CTitleBarButton (CloseButton)

  - Object name: "dockAreaCloseButton"
  - Icon size: 16x16
  - Auto-raise: true

CTitleBarButton Definition

CTitleBarButton is defined as:
using tTitleBarButton = QToolButton;  // Line 48, DockAreaTitleBar.h

class CTitleBarButton : public tTitleBarButton  // A QToolButton subclass

Features:

- Respects CDockManager::DockAreaHas_xxx_Button config flags
- Respects CDockManager::DockAreaHideDisabledButtons - hides when disabled if configured
- Responds to EnabledChanged events for visibility updates
- Has internal ShowInTitleBar and HideWhenDisabled flags

CDockAreaTabBar (/Users/talley/dev/self/PyQt6Ads/Qt-Advanced-Docking-System/src/DockAreaTabBar.h and .cpp)

Type: QScrollArea subclass
Object Name: (none explicitly set in code)
Layout: Internal QWidget (TabsContainerWidget) with QBoxLayout
Frame Style: NoFrame
Scroll Bars: Both always off
Size Policy: Preferred width, Preferred height

Internal Structure:
CDockAreaTabBar (QScrollArea)
  └─ TabsContainerWidget (QWidget)
      └─ TabsLayout (QBoxLayout LeftToRight)
          ├─ CDockWidgetTab[0]
          ├─ CDockWidgetTab[1]
          ├─ ...
          └─ Stretch item (count() - 1)

Track Current Tab: Uses CurrentIndex field in private data (int, default -1)

Key Methods:

- setCurrentIndex(int) - Sets and updates active tab
- currentIndex() - Returns current active tab index
- currentTab() - Returns actual CDockWidgetTab pointer for current index

CDockWidgetTab (/Users/talley/dev/self/PyQt6Ads/Qt-Advanced-Docking-System/src/DockWidgetTab.h and .cpp)

Type: QFrame subclass
Object Name: (none set in code)
Layout: QBoxLayout (LeftToRight)
Mouse Propagation: Disabled (Qt::WA_NoMousePropagation)
Focus Policy: NoFocus
Layout Margins: Left margin varies with font height (Spacing = fm.height() / 4), Top/Bottom 0, Right 0
Layout Spacing: 0

Child Widgets (in createLayout order):

1. CElidingLabel - Tab title text

  - Object name: "dockWidgetTabLabel"
  - Property: Text of the dock widget's windowTitle()
  - Alignment: Center
  - Elide mode: Configurable (default: ElideRight unless DisableTabTextEliding)
  - Optional: Can be hidden if ShowTabTextOnlyForActiveTab and tab has icon

1. QLabel - Icon label (OPTIONAL)

  - Created dynamically when icon is set via setIcon()
  - Object name: (none explicitly set)
  - Size policy: Fixed width, Preferred height
  - Alignment: VCenter
  - Only present if icon is set

1. QAbstractButton - Close button (QPushButton or QToolButton)

  - Object name: "tabCloseButton"
  - Type: Depends on CDockManager::TabCloseButtonIsToolButton config
  - Icon: Close button icon (16px)
  - Size policy: Fixed, Fixed
  - Focus policy: NoFocus
  - Visibility: Depends on:
    - DockWidget::DockWidgetClosable feature
    - CDockManager::ActiveTabHasCloseButton (if active tab)
    - CDockManager::AllTabsHaveCloseButton (always shown if true)

Active/Inactive State:

- isActiveTab() / setActiveTab(bool) property
- Updates visual style via stylesheet (activeTab="true" / "false")
- Q_PROPERTY with activeTabChanged() signal
- Controls close button visibility

CSS Stylesheet Rules (/Users/talley/dev/self/PyQt6Ads/Qt-Advanced-Docking-System/src/stylesheets/default.css)

CDockAreaTitleBar buttons (CTitleBarButton):

```css
ads--CTitleBarButton {
    padding: 0px 0px;
}

# tabsMenuButton::menu-indicator { image: none; }

# tabsMenuButton { qproperty-icon: url(...); qproperty-iconSize: 16px; }

# dockAreaCloseButton { qproperty-icon: url(...); qproperty-iconSize: 16px; }

# detachGroupButton { qproperty-icon: url(...); qproperty-iconSize: 16px; }

# dockAreaAutoHideButton { qproperty-icon: url(...); qproperty-iconSize: 16px; }

# dockAreaMinimizeButton { qproperty-icon: url(...); qproperty-iconSize: 16px; }

CDockWidgetTab:
ads--CDockWidgetTab {
    background: palette(window);
    border-color: palette(light);
    border-style: solid;
    border-width: 0 1px 0 0;  /*Right border only*/
    padding: 0 0px;
}

ads--CDockWidgetTab[activeTab="true"] {
    background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:0.5,
        stop:0 palette(window), stop:1 palette(light));
}

ads--CDockWidgetTab QLabel { color: palette(dark); }
ads--CDockWidgetTab[activeTab="true"] QLabel { color: palette(foreground); }
```

Tab Close Button:

```css
# tabCloseButton {

    margin-top: 2px;
    background: none;
    border: none;
    padding: 0px -2px;
    qproperty-icon: url(...);
    qproperty-iconSize: 16px;
}

# tabCloseButton:hover {

    border: 1px solid rgba(0, 0, 0, 32);
    background: rgba(0, 0, 0, 16);
}

# tabCloseButton:pressed { background: rgba(0, 0, 0, 32); }
```

Auto-hide title label:

```css
# autoHideTitleLabel {

    padding-left: 4px;
    color: palette(foreground);
}
```

This is the complete, accurate widget structure and styling from the QtAds source. All object names, CSS selectors,
and layout arrangements come directly from the source code files.

--------------------------------------

## Qlementine Design System Summary

Based on my exploration of the PyQlementine source code, here's a comprehensive breakdown of Qlementine's design
system for tabs, buttons, and related UI elements:

1. TAB STYLING (QTabBar/QTabWidget)

File: /Users/talley/dev/self/PyQlementine/qlementine/lib/src/style/QlementineStyle.cpp

Tab Control Elements:

- CE_TabBarTab - Main tab drawing (handles layout, padding, shape, and label)
- CE_TabBarTabShape - Tab background/border rendering
- CE_TabBarTabLabel - Tab text and icon rendering

Tab Colors (from tabBackgroundColor() at line 5623):

- Selected tab (normal): backgroundColorMain2 (#f3f3f3 in light theme)
- Selected tab (hovered): backgroundColorMain2 (#f3f3f3)
- Selected tab (pressed): backgroundColorMain2 (#f3f3f3)
- Inactive tab (normal): backgroundColorMainTransparent (transparent)
- Inactive tab (hovered): neutralColor (#d1d1d1 in light theme)
- Inactive tab (pressed): backgroundColorMain2 (#f3f3f3)

Tab Text/Foreground Colors (from tabForegroundColor() at line 5643):

- Uses buttonForegroundColor(mouse, ColorRole::Secondary) which adapts based on mouse state

Tab Border Radius and Padding:

- Border radius: theme.borderRadius = 6.0 (defined at line 158 of Theme.hpp)
- For selected tabs: Full rounded corners RadiusesF(radius, radius, radius, radius) (line 1267)
- For inactive tabs: Top-only rounded corners RadiusesF(radius, radius, 0., 0.) (line 1267)
- Extra padding: tabExtraPadding() (line 200) - adds spacing/2 on top, and spacing on left/right for first/last/moved tabs
- Spacing from theme: theme.spacing = 8 pixels

Tab Close Button Colors (from tabCloseButtonBackgroundColor() at line 5655):

- Selected tab, hovered: neutralColor (#d1d1d1)
- Selected tab, pressed: neutralColorPressed (#d5d5d5)
- Selected tab, normal: neutralColorTransparent (transparent)
- Inactive tab, hovered: semiTransparentColor2 (semi-transparent black, ~19% opacity)
- Inactive tab, pressed: semiTransparentColor4 (semi-transparent black, ~40% opacity)
- Inactive tab, normal: semiTransparentColorTransparent (fully transparent)

Tab Bar Height:

- Line 465: controlHeightLarge + spacing = 28 + 8 = 36 pixels
- controlHeightLarge = 28 (from Theme.hpp line 163)

--------------------------------------

1. COLOR PALETTE / THEME SYSTEM

File: /Users/talley/dev/self/PyQlementine/qlementine/lib/include/oclero/qlementine/style/Theme.hpp

Key Color Categories:

Background Colors:

- backgroundColorMain1: #ffffff (white, primary surface)
- backgroundColorMain2: #f3f3f3 (light gray, secondary surface)
- backgroundColorMain3: #e3e3e3 (medium gray)
- backgroundColorMain4: #dfdfdf (darker gray)
- backgroundColorTabBar: #dfdfdf
- backgroundColorMainTransparent: Transparent variant

Neutral Colors (for inactive/disabled states):

- neutralColor: #d1d1d1 (default)
- neutralColorHovered: #d3d3d3
- neutralColorPressed: #d5d5d5
- neutralColorDisabled: #eeeeee

Primary Colors (blue, ~#1890ff):

- Base: #1890ff
- Hovered: #2c9dff
- Pressed: #40a9ff
- Disabled: #d1e9ff
- Foreground: #ffffff (white text on blue)

Secondary Colors (dark, ~#404040):

- Base: #404040
- Hovered: #333333
- Pressed: #262626
- Disabled: #d4d4d4
- Foreground: #ffffff (white text)

Status Colors:

- Success: #2bb5a0 (teal)
- Info: #1ba8d5 (cyan)
- Warning: #fbc064 (gold)
- Error: #e96b72 (red)
- Each with hovered, pressed, disabled variants and white foreground

Border Colors:

- Default: #d3d3d3
- Hovered: #b3b3b3
- Pressed: #a3a3a3
- Disabled: #e9e9e9

Shadow/Semi-transparent Colors:

- shadowColor1: 20% black opacity
- shadowColor2: 40% black opacity (used for tab shadows)
- shadowColor3: 60% black opacity
- semiTransparentColor2: ~19% black opacity
- semiTransparentColor4: ~40% black opacity

--------------------------------------

1. BUTTON STYLING (QToolButton with/without menu)

File: /Users/talley/dev/self/PyQlementine/qlementine/lib/src/style/QlementineStyle.cpp, lines 2929-3050

Tool Button Drawing (CC_ToolButton):

Button Parts:

- Main button background and foreground
- Menu button (optional, separate) with separator line
- Menu arrow indicator

Button Colors (from toolButtonBackgroundColor()):

- Depends on mouse state (Normal, Hovered, Pressed) and color role (Primary, Secondary)
- Uses animations: _impl->animations.animateBackgroundColor2(w, bgColor,_impl->theme.animationDuration)

Menu Arrow Styling (lines 3031-3041):

- Arrow size: _impl->theme.iconSize = 16x16
- Arrow is drawn as a path (getMenuIndicatorPath())
- Arrow color: toolButtonForegroundColor(menuButtonMouse, role) with animation
- Arrow pen width: iconPenWidth = 1.01 (line 79)
- Cap style: Round

Menu Button Separator Line (lines 3018-3029):

- Line width: _impl->theme.borderWidth = 1
- Line color: toolButtonSeparatorColor(mouse, role)
- Vertical line between button and menu parts

Tab Bar Scroll Button Special Case (lines 2962-2989):

- Special styling for left/right arrow buttons in QTabBar
- Button size: controlHeightMedium x controlHeightMedium = 24x24
- Background color: tabBarBackgroundColor(tabBarState)
- If not documentMode (first/last tab):
  - Applies rounded corners on one side
  - bgRadius: borderRadius *1.5 = 6* 1.5 = 9.0
  - Left button: RadiusesF(0., bgRadius, 0., 0.) (top-right only)
  - Right button: RadiusesF(bgRadius, 0., 0., 0.) (top-left only)
- Icons: SP_ArrowLeft and SP_ArrowRight at iconSize

Tool Button Background (Primitive Element PE_PanelButtonTool, lines 515-545):

- Border radius: borderRadius = 6.0 for normal tool buttons
- Menu bar extension buttons: menuBarItemBorderRadius = 2.0
- Tab bar scroll buttons: Fully rounded with radius = rect.height() (circle)
- Background fills using drawRoundedRect()

--------------------------------------

1. CLOSE BUTTONS & SMALL ICON BUTTONS

Close Button Styling:

- Uses tabCloseButtonBackgroundColor() and tabCloseButtonForegroundColor()
- For selected tabs:
  - Hovered: neutralColor (#d1d1d1) background
  - Pressed: neutralColorPressed (#d5d5d5) background
  - Normal: Transparent background
- For inactive tabs: Semi-transparent backgrounds (2, 4 with opacity)

Generic Icon Button Styling:

- Controlled by PE_PanelButtonTool primitive
- Border radius: borderRadius = 6.0
- Icon size: iconSize = 16x16 (default)
- Alternative sizes available:
  - iconSizeMedium: 24x24
  - iconSizeLarge: 24x24
  - iconSizeExtraSmall: 12x12

--------------------------------------

1. SPACING, PADDING, AND BORDER-RADIUS VALUES

From Theme.hpp (lines 158-189):

┌─────────────────────────┬───────┬───────────────────────────────────────────────────────────────┐
│        Property         │ Value │                             Usage                             │
├─────────────────────────┼───────┼───────────────────────────────────────────────────────────────┤
│ borderRadius            │ 6.0   │ Standard rounded corners for buttons, tabs, inputs            │
├─────────────────────────┼───────┼───────────────────────────────────────────────────────────────┤
│ checkBoxBorderRadius    │ 4.0   │ Checkbox/radio button corners                                 │
├─────────────────────────┼───────┼───────────────────────────────────────────────────────────────┤
│ menuItemBorderRadius    │ 4.0   │ Menu item corners                                             │
├─────────────────────────┼───────┼───────────────────────────────────────────────────────────────┤
│ menuBarItemBorderRadius │ 2.0   │ Menu bar item corners                                         │
├─────────────────────────┼───────┼───────────────────────────────────────────────────────────────┤
│ borderWidth             │ 1     │ Standard border thickness                                     │
├─────────────────────────┼───────┼───────────────────────────────────────────────────────────────┤
│ focusBorderWidth        │ 2     │ Focus ring thickness                                          │
├─────────────────────────┼───────┼───────────────────────────────────────────────────────────────┤
│ controlHeightLarge      │ 28    │ Standard button/input height, tab bar height                  │
├─────────────────────────┼───────┼───────────────────────────────────────────────────────────────┤
│ controlHeightMedium     │ 24    │ Medium buttons, tab scroll buttons                            │
├─────────────────────────┼───────┼───────────────────────────────────────────────────────────────┤
│ controlHeightSmall      │ 16    │ Small buttons                                                 │
├─────────────────────────┼───────┼───────────────────────────────────────────────────────────────┤
│ spacing                 │ 8     │ Default spacing between elements, horizontal/vertical padding │
├─────────────────────────┼───────┼───────────────────────────────────────────────────────────────┤
│ tabBarPaddingTop        │ 4     │ Top padding of tab bar                                        │
├─────────────────────────┼───────┼───────────────────────────────────────────────────────────────┤
│ scrollBarThicknessFull  │ 12    │ Full scrollbar width                                          │
├─────────────────────────┼───────┼───────────────────────────────────────────────────────────────┤
│ scrollBarThicknessSmall │ 6     │ Small scrollbar width                                         │
└─────────────────────────┴───────┴───────────────────────────────────────────────────────────────┘

Tab-Specific Spacing:

- Top extra padding on first/last tabs: spacing/2 = 4 pixels
- Left/right extra padding on first/last/moved tabs: spacing = 8 pixels
- Tab bar height: controlHeightLarge + spacing = 36 pixels
- Button spacing inside tab bar: controlHeightMedium *2 + spacing* 3 for scroll buttons = 242 + 83 = 72 pixels

Tab Bar Scroll Buttons Layout (line 2978-2982):

- Button size: 24x24
- Horizontal offset from edge: spacing / 2 = 4 pixels
- Vertical centering within tab bar

--------------------------------------

1. BADGE/PILL STYLING

File: /Users/talley/dev/self/PyQlementine/qlementine/lib/include/oclero/qlementine/utils/BadgeUtils.hpp

Badge Types:

- StatusBadge::Success, Info, Warning, Error

Badge Sizes (from getStatusBadgeSizes()):

- Small: 16x16 container, 10x10 icon
- Medium: 24x24 container, 16x16 icon

Badge Colors:
Maps status badge type to background + foreground colors:

- Success: statusColorSuccess + statusColorForeground (teal with white)
- Info: statusColorInfo + statusColorForeground (cyan with white)
- Warning: statusColorWarning + statusColorForeground (gold with white)
- Error: statusColorError + statusColorForeground (red with white)

Badge Icons:

- Small badges: Circular outline with checkmark/info/warning/error icon
- Medium badges: Similar but larger
- Line thickness: lineThickness parameter (typically ~1.01)

--------------------------------------

1. KEY FILES FOR REFERENCE

1. Main Style Implementation:

  - /Users/talley/dev/self/PyQlementine/qlementine/lib/src/style/QlementineStyle.cpp
  - /Users/talley/dev/self/PyQlementine/qlementine/lib/include/oclero/qlementine/style/QlementineStyle.hpp

1. Theme Definition:

  - /Users/talley/dev/self/PyQlementine/qlementine/lib/include/oclero/qlementine/style/Theme.hpp
  - /Users/talley/dev/self/PyQlementine/qlementine/lib/src/style/Theme.cpp

1. Theme Data (Light):

  - /Users/talley/dev/self/PyQlementine/qlementine/showcase/resources/themes/light.json

1. Primitive Drawing Utilities:

  - /Users/talley/dev/self/PyQlementine/qlementine/lib/include/oclero/qlementine/utils/PrimitiveUtils.hpp
  - /Users/talley/dev/self/PyQlementine/qlementine/lib/src/utils/PrimitiveUtils.cpp

1. Badge Utilities:

  - /Users/talley/dev/self/PyQlementine/qlementine/lib/include/oclero/qlementine/utils/BadgeUtils.hpp
  - /Users/talley/dev/self/PyQlementine/qlementine/lib/src/utils/BadgeUtils.cpp

--------------------------------------

### Key Insights for Tab Menu Button Design

For your tab menu button in pymmcore-gui, Qlementine's design suggests:

1. Button Size: 24x24 (controlHeightMedium) with 6px border-radius
2. Dropdown Arrow: 16x16 icon with subtle separating line before it
3. Spacing: 8px padding/spacing between button parts, 4px margins
4. Colors:

  - Inactive tab context: Use semiTransparentColor2 (~19% black opacity) when hovered
  - Selected tab context: Use neutralColor (#d1d1d1) when hovered

1. Rounded Corners: Full 6px radius for standalone buttons; contextual radius (e.g., 9px on specific corners) when in
tab bar
2. Shadows: Optional subtle shadow using shadowColor2 (40% black opacity)
