# Inhyeong DevKit

A Blender developer toolkit that bundles essential dev tools into one addon.

## Features

### Console

Replaces Blender's clunky system console with an in-app popup.

- **Auto-capture on startup** — intercepts `stdout`/`stderr` the moment the addon is enabled
- **Popup console** — open from **Window → Inhyeong Console** or **Ctrl+Shift+F9**
- **Stream filtering** — toggle between All / stdout / stderr output
- **Text search** — filter log entries in real-time
- **Per-line selection** — checkbox on each entry, copy selected lines
- **Select All / Select None** — bulk selection for visible (filtered) entries
- **Timestamps** — optional per-line timestamps (off by default)
- **Configurable width** — set popup width in addon preferences

#### What Gets Captured

| Source | Captured? |
|--------|-----------|
| `print()` from any script/addon/operator | ✅ |
| `sys.stdout.write()` / `sys.stderr.write()` | ✅ |
| `warnings.warn()` | ✅ |
| Python `logging` module | ✅ |
| `traceback.print_exc()` | ✅ |
| `self.report()` (operator reports) | ❌ Goes to Blender info bar |
| C-engine messages (GPU, depsgraph, memory) | ❌ OS-level file descriptors |
| Pre-startup messages | ❌ Addon not loaded yet |

### Hot Reload

Reload addons without restarting Blender or manually uninstalling/reinstalling.

- **Link Addon Source** — one-click setup that links your dev folder into Blender's addons directory (uses junctions on Windows, no admin needed)
- **Quick reload** — set a target addon in preferences, then hit **Ctrl+Shift+F10** to reload it instantly
- **Single addon reload** — disable → purge all submodules from `sys.modules` → re-enable, in one operation
- **Reload All Scripts** — convenience wrapper for `bpy.ops.script.reload()`
- **Window menu access** — all reload actions available from Window menu

#### Dev Setup

1. Install Inhyeong DevKit normally (zip install)
2. Go to **Window → Link Addon Source...** or find it in addon preferences under "Dev Setup"
3. Browse to your addon's source folder (the one containing `__init__.py`)
4. The operator removes the installed copy and creates a link to your source — your edits are now live
5. The reload target is auto-set. Hit **Ctrl+Shift+F10** after saving code changes to reload.

On Windows this uses directory junctions which don't require admin privileges or Developer Mode. On Mac/Linux it uses standard symlinks.

<details>
<summary>Manual symlink setup (alternative)</summary>

**Windows (run PowerShell as admin):**
```powershell
mklink /d "C:\Users\YOU\AppData\Roaming\Blender Foundation\Blender\5.0\scripts\addons\your_addon" "C:\path\to\your\addon\source"
```

**Mac / Linux:**
```bash
ln -s /path/to/your/addon/source ~/.config/blender/5.0/scripts/addons/your_addon
```

Then set the addon's module name as the "Reload Target" in DevKit preferences.
</details>

## Installation

1. Download `inhyeong_devkit.zip` from [Releases](https://github.com/desuqcafe/InhyeongDevKit/releases) or zip the `inhyeong_devkit` folder yourself
2. In Blender: **Edit → Preferences → Add-ons → Install from Disk**
3. Select the zip file and enable the addon

The console starts capturing immediately — no manual setup needed.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+F9 | Open Inhyeong Console |
| Ctrl+Shift+F10 | Quick reload target addon |

## Configuration

In **Edit → Preferences → Add-ons → Inhyeong DevKit**:

- **Console Popup Width** — adjust the console popup width (400–1600px)
- **Reload Target** — the addon module name to reload with Ctrl+Shift+F10
- **Link Addon Source** — set up a dev link to your addon source folder

## Known Quirks

These are Blender UI framework limitations, not bugs:

- **Clicking outside the popup closes it.** Logs are preserved — just reopen with Ctrl+Shift+F9.
- **The popup width is not resizable by dragging.** Set your preferred width in addon preferences instead. Height can be stretched.
- **No native Ctrl+C in the log list.** Use the per-line checkboxes + Copy Selected as a workaround.
- **C-level engine messages are not captured.** GPU driver warnings, depsgraph debug, and memory stats bypass Python. For those you still need the system console or a terminal.
- **Hot reload may not work perfectly with all addons.** Addons that store state in global variables or register callbacks in unusual ways may need a full Blender restart.

## Project Structure

```
inhyeong_devkit/
├── __init__.py              Main entry point, preferences, registration
├── console/
│   ├── __init__.py
│   ├── capture.py           StreamCapture, stdout/stderr interception
│   ├── data.py              PropertyGroups (log entries, settings)
│   ├── operators.py         Console popup, copy, filter, diagnostics
│   └── ui.py                UIList for log display
└── reload/
    ├── __init__.py
    └── operators.py          Addon reload, script reload
```

## Requirements

- Blender 4.0+

## License

MIT License — see [LICENSE](LICENSE) for details.