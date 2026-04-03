import sys
import bpy
from bpy.props import StringProperty, EnumProperty

ADDON_PACKAGE = __package__.rsplit(".", 1)[0]


def _get_enabled_addon_items(context):
    import os
    items = [("", "— Select Addon —", "Choose an addon to reload")]
    addons_dir = bpy.utils.user_resource("SCRIPTS", path="addons")
    for mod_name in sorted(context.preferences.addons.keys()):
        if mod_name == ADDON_PACKAGE:
            continue
        addon_path = os.path.join(addons_dir, mod_name)
        linked = os.path.islink(addon_path) or _is_junction(addon_path)
        label = f"{mod_name}  [linked]" if linked else mod_name
        items.append((mod_name, label, f"Reload {mod_name}"))
    return items


class INHYEONG_OT_reload_addon(bpy.types.Operator):
    bl_idname = "inhyeong_devkit.reload_addon"
    bl_label = "Reload Addon"
    bl_description = "Reload a single addon by module name without restarting Blender"

    module_name: StringProperty(
        name="Module",
        description="The addon module name to reload",
        default="",
    )

    module_enum: EnumProperty(
        name="Addon",
        description="Select an addon to reload",
        items=lambda self, context: _get_enabled_addon_items(context),
    )

    def execute(self, context):
        mod_name = self.module_name.strip() or self.module_enum
        if not mod_name:
            self.report({"ERROR"}, "No module name specified")
            return {"CANCELLED"}

        # Guard against reloading ourselves
        if mod_name == ADDON_PACKAGE:
            self.report({"ERROR"}, "Cannot reload DevKit itself — use Blender > System > Reload Scripts instead")
            return {"CANCELLED"}

        # Check if the addon is currently enabled
        if mod_name not in context.preferences.addons:
            self.report({"ERROR"}, f"Addon '{mod_name}' is not enabled")
            return {"CANCELLED"}

        import os
        addons_dir = bpy.utils.user_resource("SCRIPTS", path="addons")
        addon_path = os.path.join(addons_dir, mod_name)
        if os.path.exists(addon_path) and not (os.path.islink(addon_path) or _is_junction(addon_path)):
            self.report({"WARNING"},
                f"'{mod_name}' is not dev-linked — changes to external sources won't take effect. "
                f"Use Link Addon Source to set up live development."
            )

        print(f"[devkit] Reloading addon: {mod_name}")

        # Disable the addon
        try:
            bpy.ops.preferences.addon_disable(module=mod_name)
        except Exception as e:
            self.report({"WARNING"}, f"Error disabling: {e}")

        # Purge all related modules from sys.modules
        to_remove = [key for key in sys.modules if key == mod_name or key.startswith(mod_name + ".")]
        for key in sorted(to_remove, reverse=True):
            del sys.modules[key]
            print(f"[devkit]   Purged: {key}")

        # Re-enable the addon, with retry on failure
        try:
            bpy.ops.preferences.addon_enable(module=mod_name)
            print(f"[devkit] Reloaded '{mod_name}' successfully")
            self.report({"INFO"}, f"Reloaded '{mod_name}'")
        except Exception as e:
            print(f"[devkit] First enable attempt failed: {e}")
            print(f"[devkit] Retrying...")
            # Retry once — sometimes the first attempt fails due to lingering state
            try:
                bpy.ops.preferences.addon_enable(module=mod_name)
                print(f"[devkit] Reloaded '{mod_name}' on retry")
                self.report({"WARNING"}, f"Reloaded '{mod_name}' (needed retry — check for errors)")
            except Exception as e2:
                self.report({"ERROR"},
                    f"Failed to re-enable '{mod_name}'. "
                    f"Try enabling it manually in Preferences > Add-ons."
                )
                print(f"[devkit] FAILED to re-enable: {e2}")
                return {"CANCELLED"}

        return {"FINISHED"}

    def invoke(self, context, event):
        if not self.module_name:
            addon_prefs = context.preferences.addons.get(ADDON_PACKAGE)
            if addon_prefs:
                target = addon_prefs.preferences.reload_target or addon_prefs.preferences.reload_target_manual
                if target:
                    self.module_name = target
                    return self.execute(context)
            return context.window_manager.invoke_props_dialog(self, width=350)
        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "module_enum")
        layout.separator()
        layout.prop(self, "module_name", text="Or type module name")
        layout.separator()
        layout.label(text="Tip: Use Link Addon Source for live dev reload", icon="INFO")


class INHYEONG_OT_reload_scripts(bpy.types.Operator):
    bl_idname = "inhyeong_devkit.reload_scripts"
    bl_label = "Reload All Scripts"
    bl_description = "Reload all Blender scripts (equivalent to F3 > Reload Scripts)"

    def execute(self, context):
        print("[devkit] Reloading all scripts...")
        bpy.ops.script.reload()
        self.report({"INFO"}, "All scripts reloaded")
        return {"FINISHED"}


class INHYEONG_OT_link_source(bpy.types.Operator):
    bl_idname = "inhyeong_devkit.link_source"
    bl_label = "Link Addon Source"
    bl_description = "Link an addon's source directory into Blender's addons folder for live development"

    filepath: StringProperty(
        name="Source Path",
        description="Path to your addon source folder or single .py file",
        subtype="FILE_PATH",
        default="",
    )

    addon_name: StringProperty(
        name="Addon Name",
        description="Name for the addon link (used as the folder/module name in Blender's addons directory)",
        default="",
    )

    needs_confirm: bpy.props.BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"})
    existing_path: bpy.props.StringProperty(default="", options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        self.needs_confirm = False
        self.existing_path = ""
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        import os
        import platform
        import shutil

        source = os.path.normpath(bpy.path.abspath(self.filepath))
        name = self.addon_name.strip()

        is_file = os.path.isfile(source) and source.endswith(".py")

        if not source or not (os.path.isdir(source) or is_file):
            self.report({"ERROR"}, f"Source not found: {source}")
            return {"CANCELLED"}

        # Auto-detect addon name
        if not name:
            if is_file:
                name = os.path.splitext(os.path.basename(source))[0]
            else:
                name = os.path.basename(os.path.normpath(source))

        # Reject dangerous or invalid names
        if not name or name in (".", "..", "addons", "scripts"):
            self.report({"ERROR"},
                f"Could not determine a safe addon name (got '{name}'). "
                f"Please type an addon name in the 'Addon Name' field."
            )
            return {"CANCELLED"}

        # Extra safety: reject names that look like system paths
        if os.sep in name or "/" in name or "\\" in name:
            self.report({"ERROR"}, f"Addon name '{name}' contains path separators — use a simple name")
            return {"CANCELLED"}

        addons_dir = bpy.utils.user_resource("SCRIPTS", path="addons")
        if not os.path.isdir(addons_dir):
            os.makedirs(addons_dir, exist_ok=True)

        link_path = os.path.join(addons_dir, name + ".py" if is_file else name)

        # Already linked correctly — nothing to do
        if os.path.islink(link_path) or _is_junction(link_path):
            existing_target = os.path.realpath(link_path)
            if os.path.normpath(existing_target) == source:
                self.report({"INFO"}, f"Already linked: {name} → {source}")
                return {"FINISHED"}

        # If existing install found and we haven't confirmed yet, ask
        if os.path.exists(link_path) and not self.needs_confirm:
            self.needs_confirm = True
            self.existing_path = link_path
            return context.window_manager.invoke_props_dialog(
                self,
                width=450,
                title="Replace Existing Addon?",
                confirm_text="Replace",
            )

        # Confirmed or nothing to replace — proceed
        if os.path.exists(link_path):
            # Safety: never delete the addons directory itself
            addons_dir_norm = os.path.normpath(addons_dir)
            link_path_norm = os.path.normpath(link_path)
            if link_path_norm == addons_dir_norm or link_path_norm in (
                os.path.normpath(os.path.join(addons_dir, ".")),
                os.path.normpath(os.path.join(addons_dir, "..")),
            ):
                self.report({"ERROR"}, "Refusing to modify the addons directory itself — check your addon name")
                return {"CANCELLED"}

            try:
                if os.path.islink(link_path) or _is_junction(link_path):
                    if platform.system() == "Windows":
                        os.rmdir(link_path)
                    else:
                        os.unlink(link_path)
                    print(f"[devkit] Removed old link: {link_path}")
                elif os.path.isdir(link_path):
                    if os.path.normpath(link_path) == source:
                        self.report({"ERROR"}, "Link path and source are the same location")
                        return {"CANCELLED"}
                    shutil.rmtree(link_path)
                    print(f"[devkit] Removed installed copy: {link_path}")
                elif os.path.isfile(link_path):
                    os.remove(link_path)
                    print(f"[devkit] Removed installed file: {link_path}")
            except Exception as e:
                self.report({"ERROR"}, f"Failed to remove existing install: {e}")
                return {"CANCELLED"}

        # Create the link
        try:
            if platform.system() == "Windows":
                if is_file:
                    os.symlink(source, link_path)
                else:
                    import subprocess
                    result = subprocess.run(
                        ["cmd", "/c", "mklink", "/J", link_path, source],
                        capture_output=True, text=True
                    )
                    if result.returncode != 0:
                        raise OSError(result.stderr.strip())
            else:
                os.symlink(source, link_path)

            print(f"[devkit] Linked: {link_path} → {source}")
            self.report({"INFO"}, f"Linked '{name}' → {source}")

            addon_prefs = context.preferences.addons.get(ADDON_PACKAGE)
            if addon_prefs:
                addon_prefs.preferences.reload_target = name
                print(f"[devkit] Set reload target to '{name}'")

            if name not in context.preferences.addons:
                try:
                    bpy.ops.preferences.addon_enable(module=name)
                    print(f"[devkit] Auto-enabled '{name}'")
                except Exception as e:
                    self.report({"WARNING"}, f"Linked but failed to auto-enable: {e}")

        except OSError as e:
            self.report({"ERROR"}, f"Failed to create link: {e}")
            return {"CANCELLED"}

        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        if self.needs_confirm:
            layout.label(text=f"An existing install was found at:", icon="ERROR")
            layout.label(text=f"  {self.existing_path}")
            layout.label(text="It will be removed and replaced with a link to your source.")
        else:
            layout.prop(self, "addon_name")


class INHYEONG_OT_unlink_source(bpy.types.Operator):
    bl_idname = "inhyeong_devkit.unlink_source"
    bl_label = "Unlink Addon Source"
    bl_description = "Remove a dev symlink/junction from Blender's addons folder"

    target: EnumProperty(
        name="Linked Addon",
        description="Select a linked addon to unlink",
        items=lambda self, context: _get_linked_addon_items(context),
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=350)

    def execute(self, context):
        import os
        import platform

        name = self.target
        if not name:
            self.report({"ERROR"}, "No addon selected")
            return {"CANCELLED"}

        addons_dir = bpy.utils.user_resource("SCRIPTS", path="addons")
        link_path = os.path.join(addons_dir, name)

        if not (os.path.islink(link_path) or _is_junction(link_path)):
            self.report({"ERROR"}, f"'{name}' is not a symlink or junction")
            return {"CANCELLED"}

        # Disable if currently enabled
        if name in context.preferences.addons:
            try:
                bpy.ops.preferences.addon_disable(module=name)
                print(f"[devkit] Disabled '{name}'")
            except Exception as e:
                self.report({"WARNING"}, f"Error disabling: {e}")

        # Remove the link
        try:
            if platform.system() == "Windows":
                if os.path.islink(link_path):
                    os.unlink(link_path)
                else:
                    os.rmdir(link_path)
            else:
                os.unlink(link_path)
            print(f"[devkit] Unlinked: {link_path}")
            self.report({"INFO"}, f"Unlinked '{name}'")
        except Exception as e:
            self.report({"ERROR"}, f"Failed to unlink: {e}")
            return {"CANCELLED"}

        # Clear reload target if it was pointing at this addon
        addon_prefs = context.preferences.addons.get(ADDON_PACKAGE)
        if addon_prefs and addon_prefs.preferences.reload_target_manual == name:
            addon_prefs.preferences.reload_target_manual = ""

        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "target")


def _get_linked_addon_items(context):
    import os
    items = [("", "— Select Addon —", "Choose a linked addon to unlink")]
    addons_dir = bpy.utils.user_resource("SCRIPTS", path="addons")
    for entry in sorted(os.listdir(addons_dir)):
        entry_path = os.path.join(addons_dir, entry)
        if os.path.islink(entry_path) or _is_junction(entry_path):
            real_target = os.path.realpath(entry_path)
            items.append((entry, f"{entry} → {real_target}", f"Unlink {entry}"))
    return items


def _is_junction(path):
    """Check if a path is a Windows junction point."""
    import os
    import platform
    if platform.system() != "Windows":
        return False
    try:
        import ctypes
        FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        return attrs != -1 and bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
    except Exception:
        return False


classes = (
    INHYEONG_OT_reload_addon,
    INHYEONG_OT_reload_scripts,
    INHYEONG_OT_link_source,
    INHYEONG_OT_unlink_source,
)