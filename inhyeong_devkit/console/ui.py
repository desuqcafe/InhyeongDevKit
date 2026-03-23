import bpy


class INHYEONG_UL_log_entries(bpy.types.UIList):
    bl_idname = "INHYEONG_UL_log_entries"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        prefs = context.window_manager.inhyeong_console

        row = layout.row(align=True)
        row.scale_y = 0.7

        row.prop(item, "selected", text="")

        if prefs.show_timestamps:
            sub = row.row(align=True)
            sub.scale_x = 0.5
            sub.label(text=item.timestamp)

        if item.stream == "stderr":
            row.alert = True
            sub = row.row(align=True)
            sub.scale_x = 0.22
            sub.label(text="ERR")

        row.label(text=item.text)

    def filter_items(self, context, data, propname):
        prefs = context.window_manager.inhyeong_console
        entries = getattr(data, propname)
        flt_flags = [self.bitflag_filter_item] * len(entries)
        flt_neworder = list(range(len(entries)))

        search = prefs.search_text.lower()

        for i, entry in enumerate(entries):
            if prefs.filter_mode == "STDOUT" and entry.stream != "stdout":
                flt_flags[i] = 0
            elif prefs.filter_mode == "STDERR" and entry.stream != "stderr":
                flt_flags[i] = 0

            if search and search not in entry.text.lower():
                flt_flags[i] = 0

        return flt_flags, flt_neworder


classes = (
    INHYEONG_UL_log_entries,
)
