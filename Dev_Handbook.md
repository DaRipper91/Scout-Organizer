# Scout Organizer - Developer Handbook

This document provides technical details, architecture overview, and development guidelines for the **Scout-Organizer** project.

## Architecture Overview

Scout-Organizer is a single-file Python TUI application (`organizer.py`) built using the [Textual](https://textual.textualize.io/) framework.

### Core Components
- **TUI Framework**: Textual (`textual>=8.0.0`) handles the UI rendering, reactive bindings, and async event loop.
- **LLM Integration**: Communicates synchronously (wrapped in background threads) with a local Ollama instance (`http://localhost:11434/api/generate`) using the `requests` library.
- **File Operations**: Utilizes standard Python libraries (`os`, `shutil`, `hashlib`, `fnmatch`) for filesystem traversal, checksum generation, and moving/deleting files.

## Directory Structure

```text
/home/daripper/Projects/Scout-Organizer/
├── organizer.py          # Main application code
├── requirements.txt      # Python dependencies
├── presets.json          # User-defined cleanup patterns
├── history.json          # Auto-generated execution history for Undo
├── CLAUDE.md             # High-level architecture and AI context
├── AGENT_REPORT.md       # Dev-to-dev handover notes and current status
└── reports/              # Static filesystem analysis reports
```

## Application Flow

### UI Composition
The layout is defined using Textual's `CSS` string inside the `ScoutOrganizer` class and instantiated via the `compose()` method. It utilizes standard Textual widgets: `DirectoryTree`, `TextArea`, `Log`, and `Button`.

### Asynchronous Operations
To prevent blocking the main UI thread, heavy operations are offloaded to background threads using standard `threading.Thread`:
- `_scout_worker(target_path)`: Gathers up to 150 files, constructs a prompt, and makes the HTTP request to Ollama.
- `_dup_scan_worker(target_path)`: Walks up to 3 directory levels, computes MD5 hashes (skipping files > 500MB), and builds a duplicate resolution plan.

Both workers use `self.call_from_thread()` to safely update the UI components (like the AI response `TextArea` and `Log`) once their tasks complete.

### State & Persistence
- **State**: The application tracks the current model index and loaded presets in memory.
- **Persistence**: 
  - Execution moves are appended to `self.history` and immediately flushed to `history.json` in the project root via `_save_history()`.
  - The `action_undo()` method pops the last batch of moves and uses `shutil.move` to reverse them.

## Technical Debt & Known Issues

Based on recent handover reports, the following issues are known and represent immediate opportunities for improvement:

1. **Synchronous Execution/Undo**:
   Currently, `action_execute()` and `action_undo()` run synchronously on the main UI thread. For very large move sets, this will cause the UI to freeze.
   *Proposed Fix*: Wrap file moving logic in background threads (similar to `_scout_worker`) and yield UI updates periodically.

2. **Dangerous Presets Execution**:
   Pressing `P` immediately runs `fnmatch` against the current directory and deletes matches without confirmation.
   *Proposed Fix*: Implement a preview modal or confirmation dialog showing matched files before invoking `os.remove()` / `shutil.rmtree()`.

3. **Duplicate Scan Nested Path Flattening**:
   The duplicate scanner outputs a plan grouping files under `_Duplicates`. However, `action_execute()` uses `os.path.basename(f)` for the destination. If two distinct subdirectories contain duplicate files with the same name, they will collide in the `_Duplicates` directory.
   *Proposed Fix*: Flatten the relative path into the filename (e.g., `subdir_file.jpg`), or maintain the directory structure inside the `_Duplicates/` folder.

4. **Binary File Previews**:
   Currently, the preview pane simply states `[Binary file — N bytes]`.
   *Proposed Fix*: Integrate `Pillow` to display image metadata (EXIF, resolution) or utilize the `file` magic command to give more descriptive binary information.

5. **Lack of Automated Testing**:
   There are currently no unit tests for the core logic (JSON parsing, path resolution, file handling).

## Development Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Ensure Ollama is running: `systemctl start ollama` or `ollama serve`
3. Run the app: `python organizer.py`

*Note: For debugging Textual apps, you can use the Textual console by running `textual console` in one terminal and running your app with `textual run --dev organizer.py` in another.*
