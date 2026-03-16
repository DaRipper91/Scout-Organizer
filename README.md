# Scout Organizer

AI-assisted filesystem organizer powered by a local [Ollama](https://ollama.ai/) instance.  
Three interfaces — pick whichever fits your device.

| Interface | File | Best for |
|---|---|---|
| **Desktop TUI** | `organizer.py` | Linux desktop / laptop — full dual-pane file manager + AI mode |
| **Termux CLI** | `scout_termux.py` | Android (Termux), SSH sessions, minimal installs |

---

## What's inside

Scout-Organizer is a merger of two projects:

- **Scout-Organizer** (original) — Ollama-powered directory organisation: Scout, Execute, Undo, Dup Scan, Presets.
- **TFM (The Future Manager)** — dual-pane Commander-style file manager with async file ops, multi-selection, tabs, tags, search, themes, and NL AI automation.

The unified desktop TUI gives you both: a full file manager you can use every day, and an AI assistant that plans and executes filesystem operations in plain English.

---

## Requirements

**Both scripts require:**
- Python 3.10+
- [Ollama](https://ollama.ai/) running locally (or on your network)
- At least one model pulled (see [Models](#models) below)

**Desktop TUI** (`organizer.py`) also requires:
```sh
pip install -r requirements.txt
# textual, rich, requests, jinja2, jsonschema, PyYAML
```

**Termux CLI** (`scout_termux.py`) only requires:
```sh
pip install requests
```

---

## Ollama setup

```sh
# Install Ollama (Linux / macOS)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models
ollama pull qwen2.5-coder:1.5b   # Termux default (~1 GB)
ollama pull qwen2.5-coder:7b     # Desktop default (~5 GB)

# Start server (if not already running as a service)
ollama serve
```

Ollama must be reachable at `http://localhost:11434`, or set `OLLAMA_HOST`:

```sh
export OLLAMA_HOST=http://192.168.1.10:11434
```

---

## Desktop TUI — `organizer.py`

```sh
python organizer.py
```

### Start menu

On launch you choose:
- **File Manager** — opens the dual-pane Commander-style browser
- **AI Scout Mode** — opens the NL automation console

### File Manager mode

```
┌──────────────────────────────────────────────────────────┐
│  Tabs: [Home ×]  [Downloads ×]  …                        │
│ ┌──────────────────┬──────────────────┐                  │
│ │  Left panel      │  Right panel     │  [Preview pane]  │
│ │  ~/Downloads     │  ~/Documents     │  (toggle P)      │
│ │  file1.pdf  ✓    │  project/        │                  │
│ │  image.png  ✓    │  notes.txt       │                  │
│ │  …               │  …               │                  │
│ └──────────────────┴──────────────────┘                  │
│  2 selected (1.4 MB)          Free: 42.3 GB   Sort: Name │
└──────────────────────────────────────────────────────────┘
```

#### Key bindings — File Manager

| Key | Action |
|-----|--------|
| `Tab` | Switch active panel |
| `Space` | Toggle file selection |
| `Shift+↑/↓` | Range selection |
| `Ctrl+A` / `Ctrl+D` | Select all / deselect all |
| `c` | Copy selected to other panel |
| `m` | Move selected to other panel |
| `d` | Delete selected (soft — moved to `~/.scout/trash/`) |
| `n` | New directory |
| `r` | Rename |
| `p` | Toggle file preview pane |
| `Ctrl+T` / `Ctrl+W` | New tab / close tab |
| `Ctrl+Tab` | Next tab |
| `Ctrl+R` | Refresh |
| `Ctrl+Shift+T` | Theme switcher |
| `h` | Toggle help overlay |
| `Esc` | Back to start menu |

### AI Scout mode

Left panel: quick-action buttons  
Right panel: target directory input, natural-language command box, dry-run toggle, output log

#### Quick actions

| Button | Prefills command |
|--------|-----------------|
| Organize by Type | Sort files into extension-based subfolders |
| Organize by Date | Sort files into `YYYY/MM/` subfolders |
| Cleanup Old Files | Delete files older than 30 days |
| Find Duplicates | 3-pass SHA-256 duplicate scan |
| Batch Rename | Find-and-replace in filenames |
| Scout Plan | AI-driven folder restructure (Ollama) |

All destructive actions require confirmation. **Dry-Run mode** (on by default) simulates the plan before asking.

#### Model toggle

Click **Toggle Model** in AI mode to switch between `qwen2.5-coder:7b` and `qwen3-coder:30b`.  
Or set a default: `export SCOUT_MODEL=qwen3-coder:30b`

---

## Termux CLI — `scout_termux.py`

```sh
# Install on Termux
pkg update && pkg install python
pip install requests

# Run
python scout_termux.py
```

Set `OLLAMA_HOST` if Ollama is on a remote machine:
```sh
export OLLAMA_HOST=http://192.168.1.10:11434
```

### Menu reference

```
1  Browse     Navigate to a directory
2  Scout      Ask the AI for an organisation plan
3  Execute    Apply the current plan (moves files)
4  Undo       Reverse the last execution session
5  Dup Scan   Find duplicate files (MD5, 3 levels deep)
6  Toggle     Switch Ollama model
7  Presets    Delete files matching patterns in presets.json
8  View plan  Print the current pending plan
q  Quit
```

---

## Shared features

### Tags (desktop)

Files can be tagged via the AI mode "Suggest Tags" button, or programmatically via `TagManager`. Tags are stored in `~/.scout/tags.db` (SQLite). Use the file search to find files by tag.

### Undo / redo (desktop)

All file ops (copy / move / delete / rename / create dir) flow through `FileOperations`, which maintains an in-memory undo/redo stack. Deleted files go to `~/.scout/trash/` so they can be restored.

### Duplicate scan

- **Desktop AI mode**: 3-pass strategy — size → partial hash → full SHA-256. Recursive, unlimited depth.
- **Termux CLI**: MD5, up to 3 levels deep, files ≤ 500 MB.

### Themes (desktop)

Available: `dark` (default), `light`, `solarized`, `dracula`. Switch with `Ctrl+Shift+T` or edit `~/.scout/config.yaml`.

### Presets

Pattern-based cleanup using `fnmatch`. Edit `presets.json` in the project root:

```json
[
  {"name": "Java Error Logs",   "pattern": "java_error_*.hprof"},
  {"name": "Trashed Files",     "pattern": ".trashed-*"},
  {"name": "Partial Downloads", "pattern": "*.partial"}
]
```

### Plugins (desktop)

Drop Python files implementing `TFMPlugin` into `~/.scout/plugins/` — they are loaded automatically on startup. Hooks: `on_file_added`, `on_file_deleted`, `on_organize`, `on_search_complete`.

---

## File reference

```
Scout-Organizer/
├── organizer.py          Unified desktop TUI entry point
├── scout_termux.py       Termux / minimal CLI
├── file_manager/         Core package (TFM + Scout merged)
│   ├── app.py              ScoutApp — Textual app root
│   ├── start_menu.py       Launch screen
│   ├── user_mode.py        Dual-pane file manager screen
│   ├── ai_mode.py          AI Scout Mode screen
│   ├── ai_integration.py   OllamaClient (plan generation + execution)
│   ├── ai_utils.py         OllamaExecutor (HTTP transport)
│   ├── automation.py       FileOrganizer (organize/cleanup/dupes/rename)
│   ├── file_operations.py  Async ops + undo/redo stack
│   ├── file_panel.py       MultiSelectDirectoryTree, FilePanel
│   ├── file_preview.py     Syntax-highlighted file preview widget
│   ├── tags.py             SQLite tag manager
│   ├── search.py           Name / content / size / tag search
│   ├── config.py           YAML config + category map
│   ├── context.py          Directory stats for AI prompts
│   ├── scheduler.py        Background task scheduler
│   ├── screens.py          Modal dialogs (confirm, input, theme, help)
│   ├── ui_components.py    EnhancedStatusBar, DualFilePanes
│   ├── plugins/            Plugin base class + registry
│   ├── prompts/            Jinja2 prompt templates
│   └── themes/             TCSS theme files
├── presets.json          Pattern-based cleanup rules
└── requirements.txt      Python dependencies
```

---

## Troubleshooting

**`Connection refused` / Ollama error**  
→ Run `ollama serve`. For Termux + remote host, check `OLLAMA_HOST`.

**Model not found**  
→ `ollama pull <model-name>`

**Scout returns invalid JSON**  
→ Toggle to a different model and retry. The `qwen2.5-coder` series is most reliable for structured output.

**Soft-deleted files are gone**  
→ Check `~/.scout/trash/` — files are moved there, not hard-deleted.
