import bpy
from bpy.props import (
    BoolProperty,
    IntProperty,
    EnumProperty,
    CollectionProperty,
    StringProperty,
)
from bpy.types import PropertyGroup


class ConsoleLogEntry(PropertyGroup):
    text: StringProperty(name="Text", default="")
    stream: StringProperty(name="Stream", default="stdout")
    timestamp: StringProperty(name="Timestamp", default="")
    selected: BoolProperty(name="Selected", default=False)


class ConsoleSettings(PropertyGroup):
    show_timestamps: BoolProperty(
        name="Timestamps",
        default=False,
    )
    filter_mode: EnumProperty(
        name="Filter",
        items=[
            ("ALL", "All", "Show all output"),
            ("STDOUT", "Out", "Show only standard output"),
            ("STDERR", "Err", "Show only errors"),
        ],
        default="ALL",
    )
    search_text: StringProperty(
        name="Search",
        default="",
        description="Filter log entries by text",
    )
    log_entries: CollectionProperty(type=ConsoleLogEntry)
    log_index: IntProperty(name="Log Index", default=0)


classes = (
    ConsoleLogEntry,
    ConsoleSettings,
)
