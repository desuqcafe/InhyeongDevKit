import sys
import bpy
from .capture import is_capturing, start_capture, stop_capture, visible_entries

ADDON_PACKAGE = __package__.rsplit(".", 1)[0]


class INHYEONG_OT_clear(bpy.types.Operator):
    bl_idname = "inhyeong_console.clear"
    bl_label = "Clear"
    bl_description = "Clear all log entries"

    def execute(self, context):
        prefs = context.window_manager.inhyeong_console
        prefs.log_entries.clear()
        prefs.log_index = 0
        return {"FINISHED"}


class INHYEONG_OT_toggle_capture(bpy.types.Operator):
    bl_idname = "inhyeong_console.toggle_capture"
    bl_label = "Toggle Capture"
    bl_description = "Pause or resume capturing output"

    def execute(self, context):
        if is_capturing():
            stop_capture()
        else:
            start_capture()
        return {"FINISHED"}


class INHYEONG_OT_copy_all(bpy.types.Operator):
    bl_idname = "inhyeong_console.copy_all"
    bl_label = "Copy All"
    bl_description = "Copy all visible log entries to clipboard"

    def execute(self, context):
        prefs = context.window_manager.inhyeong_console
        lines = [e.text for e in visible_entries(prefs)]
        bpy.context.window_manager.clipboard = "\n".join(lines)
        self.report({"INFO"}, f"Copied {len(lines)} entries")
        return {"FINISHED"}


class INHYEONG_OT_copy_selected(bpy.types.Operator):
    bl_idname = "inhyeong_console.copy_selected"
    bl_label = "Copy Selected"
    bl_description = "Copy checked log entries to clipboard"

    @classmethod
    def poll(cls, context):
        prefs = context.window_manager.inhyeong_console
        return any(e.selected for e in prefs.log_entries)

    def execute(self, context):
        prefs = context.window_manager.inhyeong_console
        lines = [e.text for e in prefs.log_entries if e.selected]
        bpy.context.window_manager.clipboard = "\n".join(lines)
        self.report({"INFO"}, f"Copied {len(lines)} entries")
        return {"FINISHED"}


class INHYEONG_OT_select_all(bpy.types.Operator):
    bl_idname = "inhyeong_console.select_all"
    bl_label = "Select All"
    bl_description = "Check all visible entries"

    def execute(self, context):
        prefs = context.window_manager.inhyeong_console
        for entry in visible_entries(prefs):
            entry.selected = True
        return {"FINISHED"}


class INHYEONG_OT_select_none(bpy.types.Operator):
    bl_idname = "inhyeong_console.select_none"
    bl_label = "Select None"
    bl_description = "Uncheck all entries"

    def execute(self, context):
        prefs = context.window_manager.inhyeong_console
        for entry in prefs.log_entries:
            entry.selected = False
        return {"FINISHED"}


class INHYEONG_OT_test_print(bpy.types.Operator):
    bl_idname = "inhyeong_console.test_print"
    bl_label = "Run Diagnostics"
    bl_description = "Test what gets captured and what doesn't"

    def execute(self, context):
        import logging
        import warnings
        import traceback

        print("[test] stdout print()")
        print(f"[test] Blender {bpy.app.version_string}")
        sys.stdout.write("[test] sys.stdout.write()\n")

        print("[test] stderr:", file=sys.stderr)
        sys.stderr.write("[test] sys.stderr.write()\n")

        warnings.warn("[test] warnings.warn()")

        logger = logging.getLogger("inhyeong_console_test")
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            logger.addHandler(handler)
        logger.warning("[test] logging.warning()")
        logger.error("[test] logging.error()")

        try:
            _ = 1 / 0
        except ZeroDivisionError:
            traceback.print_exc()

        self.report({"WARNING"}, "[test] self.report() — info bar only, not captured")
        print("[test] Done!")
        return {"FINISHED"}


class INHYEONG_OT_close_popup(bpy.types.Operator):
    bl_idname = "inhyeong_console.close_popup"
    bl_label = "Close"
    bl_description = "Close the console popup"

    def execute(self, context):
        return {"FINISHED"}


class INHYEONG_OT_open_console(bpy.types.Operator):
    bl_idname = "inhyeong_console.open"
    bl_label = "Inhyeong Console"
    bl_description = "Open the Inhyeong Console"
    bl_options = {"REGISTER"}

    def invoke(self, context, event):
        addon_prefs = context.preferences.addons[ADDON_PACKAGE].preferences
        return context.window_manager.invoke_props_dialog(
            self,
            width=addon_prefs.popup_width,
            title="Inhyeong Console",
            confirm_text="",
        )

    def execute(self, context):
        return {"FINISHED"}

    def check(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        prefs = context.window_manager.inhyeong_console

        # Top toolbar
        row = layout.row(align=True)

        if is_capturing():
            row.operator("inhyeong_console.toggle_capture", text="", icon="PAUSE", depress=True)
        else:
            row.operator("inhyeong_console.toggle_capture", text="", icon="PLAY")

        row.separator()
        row.prop(prefs, "filter_mode", expand=True)
        row.separator()
        row.prop(prefs, "show_timestamps", text="", icon="TIME")
        row.separator()
        row.operator("inhyeong_console.copy_selected", text="", icon="DOCUMENTS")
        row.operator("inhyeong_console.copy_all", text="", icon="COPYDOWN")
        row.separator()
        row.operator("inhyeong_console.select_all", text="", icon="CHECKBOX_HLT")
        row.operator("inhyeong_console.select_none", text="", icon="CHECKBOX_DEHLT")
        row.separator()
        row.operator("inhyeong_console.clear", text="", icon="TRASH")

        # Search
        row = layout.row(align=True)
        row.prop(prefs, "search_text", text="", icon="VIEWZOOM")

        # Log list
        col = layout.column()
        col.template_list(
            "INHYEONG_UL_log_entries",
            "inhyeong_popup_log",
            prefs,
            "log_entries",
            prefs,
            "log_index",
            rows=25,
        )

        # Status bar
        total = len(prefs.log_entries)
        selected = sum(1 for e in prefs.log_entries if e.selected)
        err_count = sum(1 for e in prefs.log_entries if e.stream == "stderr")

        parts = [f"{total} lines"]
        if err_count:
            parts.append(f"{err_count} errors")
        if selected:
            parts.append(f"{selected} selected")

        row = layout.row()
        row.scale_y = 0.5
        row.label(text="  ·  ".join(parts))

        # Single Close button — fallback for older Blender without template_popup_confirm
        if hasattr(layout, "template_popup_confirm"):
            layout.template_popup_confirm("inhyeong_console.close_popup", text="Close", cancel_text="")
        else:
            layout.operator("inhyeong_console.close_popup", text="Close")


classes = (
    INHYEONG_OT_clear,
    INHYEONG_OT_toggle_capture,
    INHYEONG_OT_copy_all,
    INHYEONG_OT_copy_selected,
    INHYEONG_OT_select_all,
    INHYEONG_OT_select_none,
    INHYEONG_OT_test_print,
    INHYEONG_OT_close_popup,
    INHYEONG_OT_open_console,
)
