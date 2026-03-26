# VSCode workbench layout: a structural anatomy

Visual Studio Code's workbench is built on a **layered abstraction model** where every visible region—sidebars, panels, activity bars, editors—is an instance of a `Part`, and the three "container" regions (primary sidebar, bottom panel, secondary sidebar) share an identical internal architecture called `AbstractPaneCompositePart`. This design makes views fully portable: any view or view container can be dragged between all three locations. At the data layer, two static registries (`IViewContainersRegistry` and `IViewsRegistry`) declare the topology, while two runtime services (`IViewDescriptorService` and `IViewsService`) manage user customizations and runtime state. The entire spatial arrangement uses a `SerializableGrid` with sash-based resizing, where each Part declares its minimum/maximum dimensions and layout priority.

---

## Eight parts arranged in a serializable grid

The workbench defines exactly **eight top-level regions** via the `Parts` enum in `layoutService.ts`:

| Part constant | Class | Purpose |
|---|---|---|
| `TITLEBAR_PART` | `BrowserTitlebarPart` | Menu bar, command center, layout controls |
| `BANNER_PART` | `BannerPart` | Optional notification banner above title bar |
| `ACTIVITYBAR_PART` | `ActivitybarPart` | Icon strip for switching sidebar containers |
| `SIDEBAR_PART` | `SidebarPart` | Primary sidebar (Explorer, Search, SCM, etc.) |
| `EDITOR_PART` | `EditorPart` | Central editor area with its own internal grid |
| `PANEL_PART` | `PanelPart` | Bottom panel (Terminal, Problems, Output) |
| `AUXILIARYBAR_PART` | `AuxiliaryBarPart` | Secondary sidebar on the opposite side |
| `STATUSBAR_PART` | `StatusbarPart` | Bottom status indicators |

These parts are arranged spatially by the `Layout` class (which implements `IWorkbenchLayoutService`) using a **`SerializableGrid`** from `vs/base/browser/ui/grid`. Each Part implements the `ISerializableView` interface, declaring `minimumWidth`, `maximumWidth`, `minimumHeight`, `maximumHeight`, a layout `priority`, and a `snap` property. The `EditorPart` uses `LayoutPriority.High` so it absorbs most window-resize changes, while the sidebar uses `LayoutPriority.Low`. Sash-based dividers between adjacent parts enable drag-to-resize, and parts like the sidebar support **snap-to-hide** when dragged below their minimum width.

Three parts are **multi-window capable** (`EDITOR_PART`, `STATUSBAR_PART`, `TITLEBAR_PART`) and can appear in auxiliary windows. All others exist only in the main window. The panel position is configurable to `BOTTOM`, `LEFT`, `RIGHT`, or `TOP`. The sidebar can be `LEFT` or `RIGHT`, with the auxiliary bar always appearing on the opposite side.

---

## Component, Part, and Composite form the class hierarchy

The inheritance chain reveals VSCode's composable primitives clearly:

```
Disposable
  └─ Themable          (theme-aware styling via getColor/updateStyles)
       └─ Component    (adds IStorageService integration for state persistence)
            ├─ Part    (a top-level layout region; implements ISerializableView)
            │    ├─ EditorPart
            │    ├─ ActivitybarPart
            │    ├─ StatusbarPart
            │    ├─ BrowserTitlebarPart
            │    ├─ BannerPart
            │    └─ AbstractPaneCompositePart    ← the critical unifier
            │         ├─ SidebarPart
            │         ├─ PanelPart
            │         └─ AuxiliaryBarPart
            └─ Composite   (a swappable UI unit loaded inside a Part)
                 └─ PaneComposite   (wraps a ViewPaneContainer)
```

**`Part`** is the abstraction for a major layout region. It has a `createTitleArea()` and `createContentArea()` template, carries a `Parts` enum ID, and participates in the grid layout. **`Composite`** is the abstraction for a swappable piece of content that lives *inside* a Part—historically called "viewlets" in the sidebar and "panels" in the bottom panel. The key architectural insight is that **`AbstractPaneCompositePart`** unifies the sidebar, panel, and auxiliary bar into one pattern, while **`PaneComposite`** unifies what gets loaded into all three.

Each `AbstractPaneCompositePart` instance manages three structural sub-areas: a **composite bar** (the icon/tab strip for switching between view containers), a **title area** (showing the active container's name and toolbar), and a **content area** (where the active `PaneComposite` renders its `ViewPaneContainer`).

---

## ViewContainers hold Views, and both are registry-driven

The declarative data model has two core concepts:

A **ViewContainer** is a logical group of views—for example, the Explorer container holds the File Explorer view, the Outline view, and the Timeline view. Each ViewContainer has an `id`, `title`, `icon`, `order`, and a `ctorDescriptor` pointing to a `ViewPaneContainer` constructor. ViewContainers are registered into the `IViewContainersRegistry` at a specific `ViewContainerLocation`:

- **`ViewContainerLocation.Sidebar`** → Primary sidebar
- **`ViewContainerLocation.Panel`** → Bottom panel
- **`ViewContainerLocation.AuxiliaryBar`** → Secondary sidebar

A **View** (described by `IViewDescriptor`) is an individual collapsible section within a ViewContainer. Each descriptor carries an `id`, `name`, `when` clause (a `ContextKeyExpression` controlling conditional visibility), `order`, `weight`, `canToggleVisibility`, `canMoveView`, and its own `ctorDescriptor` (typically `TreeViewPane` or `WebviewViewPane`). Views are registered into a specific ViewContainer via `IViewsRegistry.registerViews()`.

At runtime, each ViewContainer is backed by a **`ViewPaneContainer`** instance that manages one or more **`ViewPane`** instances. The `ViewPaneContainer` uses a `PaneView` (a vertical or horizontal split view) to lay out its panes. When a ViewContainer has **only one view** and `mergeViewWithContainerWhenSingleView` is true (the default for extensions), the view's toolbar actions merge into the container's title bar and the redundant pane header disappears.

The **`ViewContainerModel`** (one per ViewContainer) tracks which view descriptors are *active* (their when-clause is satisfied), which are *visible* (not hidden by the user), and persists per-view state including collapsed state, order, and size.

---

## Anatomy of a ViewPane: the collapsible section

Each collapsible item inside a sidebar or panel is a **`ViewPane`**, extending the base `Pane` class from `vs/base/browser/ui/splitview/paneview.ts`. A ViewPane structurally contains these elements:

- **Header container** — the clickable bar with a `.pane-header` CSS class that doubles as a **drag handle** for moving views between containers
- **Twisties** — the expand/collapse chevron icon (`.twisties` CSS class)
- **Icon container** — an optional icon displayed in the header, used especially when views are surfaced in an activity bar
- **Title and title description** — the view label (e.g., "OUTLINE") and an optional subtitle
- **Action toolbar** — a `ToolBar` instance rendering view-specific action buttons (refresh, collapse all, new file, etc.), configured via `showActionsAlways` to appear always or only on hover
- **Menu actions** — a `ViewMenuActions` object managing context-menu-contributed actions for the header, including hide and move commands
- **Progress bar** — a thin `ProgressBar` at the top of the view body, triggered via `ProgressLocation` referencing the view's ID
- **Body container** — the main content area where tree views, webview views, or custom content renders
- **Welcome view container** — an empty-state area with links, buttons, and markdown, contributed via `contributes.viewsWelcome`
- **Focus tracking** — sets a `FocusedViewContext` context key for keybinding when-clauses

The subclass **`FilterViewPane`** adds a search/filter widget in the header, used by views like the Testing Explorer and Debug console. Pane orientation is **vertical** in sidebars and **horizontal** in the bottom panel (enabling side-by-side splitting).

---

## Activity bar icons are ViewContainers, and every area has its own composite bar

**Each Activity Bar icon represents exactly one ViewContainer.** Clicking an icon activates that ViewContainer in the primary sidebar. The built-in containers include Explorer (`workbench.view.explorer`), Search (`workbench.view.search`), Source Control (`workbench.view.scm`), Run and Debug (`workbench.view.debug`), and Extensions (`workbench.view.extensions`).

The activation flow works as follows: clicking an Activity Bar icon calls `openPaneComposite(id, ViewContainerLocation.Sidebar)` on the `SidebarPart`. This deactivates the current `PaneComposite`, instantiates (or retrieves from cache) the target `PaneComposite` via its `ctorDescriptor`, which creates a `ViewPaneContainer`. The `ViewPaneContainer` reads all registered `IViewDescriptor`s for that container from the `ViewContainerModel`, creates `ViewPane` instances for each visible view, and renders them in the split layout.

The composite bar concept is **not unique to the activity bar**. All three pane-composite areas have their own switching mechanism:

- **Primary sidebar** uses an `ActivityBarCompositeBar` (a specialized `PaneCompositeBar`), positionable as `DEFAULT` (vertical side strip), `TOP`, `BOTTOM`, or `HIDDEN`
- **Bottom panel** has a `PaneCompositeBar` rendered as horizontal tabs in the panel's title area
- **Auxiliary bar** has its own `PaneCompositeBar` for switching between its containers

The `ActivitybarPart` itself is a separate `Part` that hosts the dedicated side-strip UI when the activity bar is in its `DEFAULT` position. When set to `TOP` or `BOTTOM`, the composite bar renders inline within the `SidebarPart`'s title area instead, and the standalone `ActivitybarPart` hides.

---

## Five services and two registries govern the system

The layout model is driven by a layered API architecture separating static registration from runtime operations:

**Static registries** (accessed via `Registry.as<T>()`):

`IViewContainersRegistry` registers and retrieves ViewContainer descriptors. Its `registerViewContainer(descriptor, location, options?)` method accepts a descriptor with `id`, `title`, `icon`, `ctorDescriptor`, `order`, `hideIfEmpty`, and optional `isDefault` flag. It stores containers in a `Map<ViewContainerLocation, ViewContainer[]>`.

`IViewsRegistry` registers View descriptors into ViewContainers. Its `registerViews(views, viewContainer)` method binds view descriptors to a container, and `moveViews(views, viewContainer)` supports relocation. It fires `onViewsRegistered`, `onViewsDeregistered`, and `onDidChangeContainer` events.

**Runtime services:**

**`IViewDescriptorService`** is the central topology manager. It sits on top of both registries and tracks user customizations—moved views and relocated containers—persisted under the `views.customizations` key in profile storage. Key methods include `moveViewContainerToLocation()`, `moveViewsToContainer()`, `moveViewToLocation()`, and `getViewContainerModel()`. When a user drags a view to a new location, this service creates a **generated container** (prefixed `workbench.views.service.{location}.{uuid}`) with `hideIfEmpty: true`. It also sets context keys for each view (`{viewId}.active`, `{viewId}.visible`) and each container (`{containerId}.defaultViewContainerLocation`).

**`IViewsService`** provides the operational API for runtime view interaction. Its `openView(id, focus?)` opens and optionally focuses a specific view, `closeView(id)` hides it, `openViewContainer(id)` activates a container, and `isViewVisible(id)` queries current state. It fires `onDidChangeViewVisibility` and `onDidChangeViewContainerVisibility` events.

**`IWorkbenchLayoutService`** controls the overall Part-level layout. Key methods include `setPartHidden(hidden, part)` for toggling part visibility, `focusPart(part)` for keyboard focus, `getSideBarPosition()` / `getPanelPosition()` for querying positions, `setPanelPosition()` / `setPanelAlignment()` for reconfiguration, `resizePart(part, dw, dh)` for programmatic resizing, and `toggleZenMode()` / `toggleMaximizedPanel()` for layout modes. It fires events including `onDidChangePartVisibility`, `onDidChangePanelPosition`, `onDidChangePanelAlignment`, and `onDidChangeZenMode`.

For **extensions**, registration happens declaratively via `package.json` contribution points. The `contributes.viewsContainers` field accepts entries under `"activitybar"` (→ Sidebar), `"panel"` (→ Panel), or `"secondarySidebar"` (→ AuxiliaryBar). The `contributes.views` field maps view descriptors to container IDs. The bridge code in `viewsExtensionPoint.ts` translates these declarations into registry calls, creating `SyncDescriptor<ViewPaneContainer>` instances with `mergeViewWithContainerWhenSingleView: true`.

---

## Panels are architecturally identical to sidebars

The bottom panel is **not a special construct**—it is another `AbstractPaneCompositePart` at `ViewContainerLocation.Panel`, architecturally identical to the sidebar and auxiliary bar. `PanelPart` extends `AbstractPaneCompositePart` exactly as `SidebarPart` and `AuxiliaryBarPart` do. Its composite bar renders as horizontal tabs in the title area rather than vertical icons, but the underlying machinery is the same: it opens `PaneComposite` instances that wrap `ViewPaneContainer` instances holding `ViewPane` instances.

**ViewContainers can be moved freely between all three locations.** Dragging a panel tab to the sidebar's activity bar relocates that ViewContainer from `ViewContainerLocation.Panel` to `ViewContainerLocation.Sidebar`. The `IViewDescriptorService` persists this customization, and the `Reset View Locations` command restores defaults. Individual views can also be dragged between containers across locations—when a view is dropped into a location without a suitable container, a generated container is automatically created.

The only behavioral differences between the three locations are cosmetic: sidebar containers use **vertical** pane orientation, panel containers default to **horizontal** orientation (side-by-side), and each location has different default composite bar styling (icons vs. tabs vs. labels). The `PanelAlignment` setting (`left`, `center`, `right`, `justify`) controls how the panel spans relative to the sidebar, which has no equivalent in the sidebar model.

---

## Conclusion

VSCode's workbench layout model achieves remarkable flexibility through two design decisions. First, the **`AbstractPaneCompositePart`** abstraction makes the sidebar, panel, and auxiliary bar structurally interchangeable—they differ only in position and styling, not in capability. Second, the **registry-plus-service** layering cleanly separates static declaration (what containers and views exist) from runtime topology management (where the user has moved them) and operational state (what is currently visible and focused). The `ViewContainer → ViewPaneContainer → ViewPane` nesting provides a uniform three-level hierarchy: a switchable group of views, a layout container for those views, and the individual collapsible panes with their headers, toolbars, progress bars, and content areas. This architecture is what allows any extension-contributed view to appear in any location, be dragged to any other location, and behave identically regardless of where it lands.
