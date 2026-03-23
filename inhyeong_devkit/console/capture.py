import sys
import time
import bpy

MAX_LOG_LINES = 2000


class StreamCapture:
    """Intercepts sys.stdout or sys.stderr, buffers lines,
    and forwards everything to the original stream."""

    def __init__(self, stream_name, original):
        self.stream_name = stream_name
        self.original = original
        self._buffer = ""

    def write(self, text):
        if self.original:
            self.original.write(text)

        if not text:
            return

        self._buffer += text

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            append_log(line, self.stream_name)

    def flush(self):
        if self._buffer:
            append_log(self._buffer, self.stream_name)
            self._buffer = ""
        if self.original:
            self.original.flush()

    def tell(self):
        return 0

    def read(self, size=-1):
        return ""

    def seek(self, offset, whence=0):
        pass

    def truncate(self, size=None):
        pass

    @property
    def name(self):
        return self.stream_name

    @property
    def encoding(self):
        return getattr(self.original, "encoding", "utf-8")

    def isatty(self):
        return False

    def fileno(self):
        if self.original:
            return self.original.fileno()
        raise OSError("No underlying fileno")


def append_log(text, stream_name):
    """Add a log entry. Safe to call from write(), even during shutdown."""
    try:
        wm = bpy.context.window_manager

        if not hasattr(wm, "inhyeong_console"):
            return

        prefs = wm.inhyeong_console
        entries = prefs.log_entries
        entry = entries.add()
        entry.text = text
        entry.stream = stream_name
        entry.timestamp = time.strftime("%H:%M:%S")

        while len(entries) > MAX_LOG_LINES:
            entries.remove(0)

        prefs.log_index = max(0, len(entries) - 1)
    except Exception:
        pass


_stdout_capture = None
_stderr_capture = None


def is_capturing():
    return _stdout_capture is not None


def start_capture():
    global _stdout_capture, _stderr_capture
    if _stdout_capture is not None:
        return

    _stdout_capture = StreamCapture("stdout", sys.__stdout__)
    _stderr_capture = StreamCapture("stderr", sys.__stderr__)
    sys.stdout = _stdout_capture
    sys.stderr = _stderr_capture


def stop_capture():
    global _stdout_capture, _stderr_capture
    if _stdout_capture is None:
        return

    _stdout_capture.flush()
    _stderr_capture.flush()

    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    _stdout_capture = None
    _stderr_capture = None


def visible_entries(prefs):
    """Yield entries that pass the current filter + search."""
    search = prefs.search_text.lower()
    for entry in prefs.log_entries:
        if prefs.filter_mode == "STDOUT" and entry.stream != "stdout":
            continue
        if prefs.filter_mode == "STDERR" and entry.stream != "stderr":
            continue
        if search and search not in entry.text.lower():
            continue
        yield entry
