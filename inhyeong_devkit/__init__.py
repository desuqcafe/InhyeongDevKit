bl_info = {
    "name": "Inhyeong DevKit",
    "author": "desuqcafe",
    "version": (0, 5, 0),
    "blender": (4, 0, 0),
    "location": "Window > Inhyeong DevKit",
    "description": "Developer toolkit: console capture, addon hot-reload, and more",
    "category": "Development",
}

import bpy
from bpy.props import IntProperty, StringProperty

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

    reload_target: StringProperty(
        name="Reload Target",
        description="Default addon module name for quick reload (Ctrl+Shift+F10)",
        default="",
    )

    def draw(self, context):
        layout = self.layout

        layout.label(text="Console", icon="CONSOLE")
        layout.prop(self, "popup_width", slider=True)

        layout.separator()

        layout.label(text="Hot Reload", icon="FILE_REFRESH")
        layout.prop(self, "reload_target")
        if self.reload_target:
            layout.label(text=f"Ctrl+Shift+F10 will reload '{self.reload_target}'", icon="INFO")
        else:
            layout.label(text="Set a module name to enable quick reload with Ctrl+Shift+F10", icon="INFO")

        layout.separator()
        layout.label(text="Dev Setup", icon="LINKED")
        layout.operator("inhyeong_devkit.link_source", icon="LINK_BLEND")


# ─────────────────────────────────────────────
# Window Menu
# ─────────────────────────────────────────────

def _window_menu_draw(self, context):
    self.layout.separator()
    self.layout.operator("inhyeong_console.open", icon="CONSOLE")

    addon_prefs = context.preferences.addons.get(__package__)
    if addon_prefs and addon_prefs.preferences.reload_target:
        op = self.layout.operator(
            "inhyeong_devkit.reload_addon",
            text=f"Reload: {addon_prefs.preferences.reload_target}",
            icon="FILE_REFRESH",
        )
        op.module_name = addon_prefs.preferences.reload_target
    else:
        self.layout.operator("inhyeong_devkit.reload_addon", text="Reload Addon...", icon="FILE_REFRESH")

    self.layout.operator("inhyeong_devkit.reload_scripts", icon="FILE_REFRESH")
    self.layout.operator("inhyeong_devkit.link_source", text="Link Addon Source...", icon="LINKED")


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
