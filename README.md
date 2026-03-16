# Scout Organizer

AI-assisted filesystem organizer powered by a local [Ollama](https://ollama.ai/) instance.
Two interfaces, one brain — pick whichever fits your device.

| Interface | File | Best for |
|---|---|---|
| **Desktop TUI** | `organizer.py` | Linux desktop / laptop |
| **Termux CLI** | `scout_termux.py` | Android (Termux), SSH sessions, minimal installs |

---

## How it works

1. Point Scout at a directory.
2. It sends the file list to a local Ollama model.
3. The model returns a JSON reorganisation plan — `{"FolderName": ["file1", "file2"]}`.
4. Review the plan, then Execute to move the files.
5. Undo reverses the last batch if you change your mind.

No files are modified until you explicitly confirm. Every execution is logged to a history file so undo always works.

---

## Requirements

**Both scripts require:**
- Python 3.10+
- [Ollama](https://ollama.ai/) running locally (or on your network)
- At least one Ollama model pulled (see [Models](#models) below)

**Desktop TUI** (`organizer.py`) also requires:
```sh
pip install textual>=8.0.0 requests
# or
pip install -r requirements.txt
```

**Termux CLI** (`scout_termux.py`) only requires:
```sh
pip install requests
```

---

## Ollama setup

Install Ollama and pull a model before running either script.

```sh
# Install (Linux / macOS)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the default models
ollama pull qwen2.5-coder:1.5b   # Termux default (fast, ~1 GB)
ollama pull qwen2.5-coder:7b     # Desktop default (~5 GB)

# Start the server (if not already running as a service)
ollama serve
```

Ollama must be reachable at `http://localhost:11434` — or set `OLLAMA_HOST` (see below).

---

## Desktop TUI — `organizer.py`

### Run

```sh
python organizer.py
```

### Layout

```
┌─────────────────┬──────────────────────────────────────┐
│  Directory tree │  Status bar (active model)            │
│  (top 60 %)     │  AI response / plan (JSON)            │
│─────────────────│  Action log                           │
│  File preview   │  [Scout] [Execute] [Undo]             │
│  (bottom 40 %)  │  [Dup Scan] [Presets] [Model]         │
└─────────────────┴──────────────────────────────────────┘
```

### Key bindings

| Key | Action |
|-----|--------|
| `S` | **Scout** — ask the AI for an organisation plan for the selected folder |
| `E` | **Execute** — apply the plan (moves files into subfolders) |
| `U` | **Undo** — reverse the last execution batch |
| `D` | **Dup Scan** — MD5-checksum scan for duplicate files (up to 3 levels deep) |
| `P` | **Presets** — delete files matching patterns in `presets.json` |
| `M` | **Toggle model** — switch between `qwen2.5-coder:7b` and `qwen3-coder:30b` |
| `H` / `?` | Show help modal |
| `Q` | Quit |
| `↑↓` | Navigate the directory tree |
| `Enter` | Expand / collapse a folder |

### Models (desktop)

| Model | Size | Notes |
|-------|------|-------|
| `qwen2.5-coder:7b` | ~5 GB | Default — good balance of speed and quality |
| `qwen3-coder:30b` | ~19 GB | Slower; better reasoning on large/complex directories |

Toggle with `M` at any time. The active model is shown in the status bar.

---

## Termux CLI — `scout_termux.py`

Designed for phone-sized screens and thumb-typing. No Textual, no curses — just ANSI colour and numbered menus.

### Install on Termux

```sh
pkg update && pkg install python
pip install requests
```

### Run

```sh
python scout_termux.py
```

### Remote Ollama

If Ollama is running on a PC on the same network (common when using Termux on Android):

```sh
export OLLAMA_HOST=http://192.168.1.10:11434
python scout_termux.py
```

You can put the export in `~/.bashrc` or `~/.zshrc` so you don't have to set it every time.

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

### Directory browser

Inside **Browse**, enter:

| Input | Action |
|-------|--------|
| A number | Enter that subdirectory |
| `0` | Use the current directory |
| `..` or `b` | Go up one level |
| `p` | Type an absolute or `~`-relative path |
| `q` | Cancel (keep current directory) |

### Models (Termux)

| Model | Size | Notes |
|-------|------|-------|
| `qwen2.5-coder:1.5b` | ~1 GB | Default — fast, works on most phones |
| `qwen2.5-coder:7b` | ~5 GB | Better plans; needs a powerful device or remote Ollama |

Toggle with option **6** in the main menu.

---

## Shared features

### Execute

Parses the AI's JSON plan and calls `shutil.move()` for each file. Destination subfolders are created automatically. Only files that actually exist in the target directory are moved — everything else is silently skipped.

Every execution is appended to the history file before any files are moved.

### Undo

Reverses the most recent execution batch by moving each file back to its original path. You are shown the session details and asked to confirm before anything changes.

History is stored in:
- Desktop: `~/Projects/Scout-Organizer/history.json`
- Termux: `~/scout_history.json`

### Duplicate scan

Walks the selected directory up to **3 levels deep**, MD5-checksums every file under 500 MB, and groups identical files. The first occurrence of each group is kept in place; all others become candidates for the `_Duplicates/` subfolder. Review the plan, then Execute to move them.

### Presets

Pattern-based cleanup using Python's `fnmatch`. Edit `presets.json` in the project root to add your own rules:

```json
[
  {"name": "Java Error Logs",   "pattern": "java_error_*.hprof"},
  {"name": "Trashed Files",     "pattern": ".trashed-*"},
  {"name": "Partial Downloads", "pattern": "*.partial"}
]
```

Each matched file or directory in the **currently selected folder** (not recursive) is permanently deleted. A confirmation prompt is shown before anything is removed.

---

## File reference

```
Scout-Organizer/
├── organizer.py        Desktop Textual TUI
├── scout_termux.py     Termux / minimal CLI
├── presets.json        Cleanup patterns (auto-created on first run)
├── requirements.txt    Python dependencies for the desktop version
└── reports/            Static filesystem snapshots (reference only)
```

---

## Troubleshooting

**`Connection refused` / Ollama error**
- Make sure `ollama serve` is running.
- If using Termux with a remote host, double-check `OLLAMA_HOST` is set correctly and the port is reachable (`curl $OLLAMA_HOST`).

**Model not found**
- Run `ollama pull <model-name>` for whichever model is selected.

**Scout returns invalid JSON**
- The model occasionally wraps its answer in markdown fences or adds prose. Try toggling to a different model or re-running Scout.

**Textual version crashes on startup** (`unexpected keyword argument 'class_'`)
- Make sure `textual>=8.0.0` is installed: `pip install -U textual`.
