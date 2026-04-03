bl_info = {
    "name": "Inhyeong DevKit",
    "author": "desuqcafe",
    "version": (0, 5, 0),
    "blender": (4, 0, 0),
    "location": "Window > Inhyeong DevKit",
    "description": "Developer toolkit: console capture, addon hot-reload, and more",
    "category": "Development",
}

import os
import bpy
from bpy.props import IntProperty, StringProperty, EnumProperty

# Handle reloading when Blender re-imports the package
if "console" in dir():
    import importlib
    importlib.reload(console)
    importlib.reload(console.capture)
    importlib.reload(console.data)
    importlib.reload(console.operators)
    importlib.reload(console.ui)
    importlib.reload(reload)
    importlib.reload(reload.operators)

from . import console
from . import reload


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _is_linked(addon_path):
    """Check if an addon path is a symlink or Windows junction."""
    if os.path.islink(addon_path):
        return True
    # Check for Windows junction
    try:
        import ctypes
        FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(addon_path))
        return attrs != -1 and bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
    except Exception:
        return False


def _get_addon_items(self, context):
    """Build enum items from enabled addons, excluding DevKit. Shows [linked] status."""
    items = [("", "— Select Addon —", "Choose an addon to reload")]
    package = __package__
    addons_dir = bpy.utils.user_resource("SCRIPTS", path="addons")

    for mod_name in sorted(context.preferences.addons.keys()):
        if mod_name == package:
            continue

        addon_path = os.path.join(addons_dir, mod_name)
        linked = _is_linked(addon_path)
        label = f"{mod_name}  [linked]" if linked else mod_name
        desc = f"Reload {mod_name}" + (" (dev linked)" if linked else "")
        items.append((mod_name, label, desc))

    return items


def _get_reload_target(context):
    """Get the effective reload target from preferences (dropdown or manual)."""
    addon_prefs = context.preferences.addons.get(__package__)
    if not addon_prefs:
        return ""
    prefs = addon_prefs.preferences
    return prefs.reload_target or prefs.reload_target_manual or ""


# ─────────────────────────────────────────────
# Addon Preferences
# ─────────────────────────────────────────────

class InhyeongDevKitPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    popup_width: IntProperty(
        name="Console Popup Width",
        description="Width of the console popup in pixels",
        default=650,
        min=400,
        max=1600,
        step=50,
    )

    reload_target: EnumProperty(
        name="Reload Target",
        description="Addon to reload with Ctrl+Shift+F10",
        items=_get_addon_items,
    )

    reload_target_manual: StringProperty(
        name="Or Type Module Name",
        description="Manually enter a module name if not in the dropdown",
        default="",
    )

    def draw(self, context):
        layout = self.layout

        layout.label(text="Console", icon="CONSOLE")
        layout.prop(self, "popup_width", slider=True)

        layout.separator()

        layout.label(text="Hot Reload", icon="FILE_REFRESH")
        layout.prop(self, "reload_target")
        layout.prop(self, "reload_target_manual")
        target = self.reload_target or self.reload_target_manual
        if target:
            layout.label(text=f"Ctrl+Shift+F10 will reload '{target}'", icon="INFO")
        else:
            layout.label(text="Select an addon above to enable quick reload", icon="INFO")

        layout.separator()
        layout.label(text="Dev Setup", icon="LINKED")
        layout.operator("inhyeong_devkit.link_source", icon="LINK_BLEND")
        layout.operator("inhyeong_devkit.unlink_source", icon="UNLINKED")


# ─────────────────────────────────────────────
# Window Menu
# ─────────────────────────────────────────────

class INHYEONG_MT_devkit_menu(bpy.types.Menu):
    bl_idname = "INHYEONG_MT_devkit_menu"
    bl_label = "Inhyeong DevKit"

    def draw(self, context):
        layout = self.layout
        layout.operator("inhyeong_console.open", icon="CONSOLE")
        layout.separator()

        target = _get_reload_target(context)
        if target:
            op = layout.operator(
                "inhyeong_devkit.reload_addon",
                text=f"Reload: {target}",
                icon="FILE_REFRESH",
            )
            op.module_name = target
        else:
            layout.operator("inhyeong_devkit.reload_addon", text="Reload Addon...", icon="FILE_REFRESH")

        layout.operator("inhyeong_devkit.reload_scripts", icon="FILE_REFRESH")
        layout.separator()
        layout.operator("inhyeong_devkit.link_source", text="Link Addon Source...", icon="LINKED")
        layout.operator("inhyeong_devkit.unlink_source", text="Unlink Addon Source...", icon="UNLINKED")


def _window_menu_draw(self, context):
    self.layout.separator()
    self.layout.menu("INHYEONG_MT_devkit_menu", icon="TOOL_SETTINGS")


# ─────────────────────────────────────────────
# Keymaps
# ─────────────────────────────────────────────

addon_keymaps = []


def _register_keymaps():
    wm = bpy.context.window_manager
    if wm.keyconfigs.addon is None:
        return

    km = wm.keyconfigs.addon.keymaps.new(name="Window", space_type="EMPTY")

    # Ctrl+Shift+F9 — Open console
    kmi = km.keymap_items.new("inhyeong_console.open", "F9", "PRESS", ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))

    # Ctrl+Shift+F10 — Quick reload (uses reload_target from preferences)
    kmi = km.keymap_items.new("inhyeong_devkit.reload_addon", "F10", "PRESS", ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))


def _unregister_keymaps():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


# ─────────────────────────────────────────────
# Auto-start capture
# ─────────────────────────────────────────────

@bpy.app.handlers.persistent
def _on_load_post(_dummy1=None, _dummy2=None):
    console.capture.start_capture()


# ─────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────

def register():
    # Preferences first
    bpy.utils.register_class(InhyeongDevKitPreferences)

    # Console data (PropertyGroups must be registered before anything that uses them)
    for cls in console.data.classes:
        bpy.utils.register_class(cls)

    # Console UI
    for cls in console.ui.classes:
        bpy.utils.register_class(cls)

    # Console operators
    for cls in console.operators.classes:
        bpy.utils.register_class(cls)

    # Reload operators
    for cls in reload.operators.classes:
        bpy.utils.register_class(cls)

    # WindowManager property for console state
    bpy.types.WindowManager.inhyeong_console = bpy.props.PointerProperty(
        type=console.data.ConsoleSettings
    )

    # Menu, handlers, keymaps
    bpy.utils.register_class(INHYEONG_MT_devkit_menu)
    bpy.types.TOPBAR_MT_window.append(_window_menu_draw)
    bpy.app.handlers.load_post.append(_on_load_post)
    _register_keymaps()

    # Start capturing immediately
    console.capture.start_capture()


def unregister():
    console.capture.stop_capture()
    _unregister_keymaps()

    if _on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load_post)

    bpy.types.TOPBAR_MT_window.remove(_window_menu_draw)
    bpy.utils.unregister_class(INHYEONG_MT_devkit_menu)

    del bpy.types.WindowManager.inhyeong_console

    # Unregister in reverse order
    for cls in reversed(reload.operators.classes):
        bpy.utils.unregister_class(cls)

    for cls in reversed(console.operators.classes):
        bpy.utils.unregister_class(cls)

    for cls in reversed(console.ui.classes):
        bpy.utils.unregister_class(cls)

    for cls in reversed(console.data.classes):
        bpy.utils.unregister_class(cls)

    bpy.utils.unregister_class(InhyeongDevKitPreferences)


if __name__ == "__main__":
    register()