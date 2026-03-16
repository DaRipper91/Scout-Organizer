# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Scout-Organizer** is a Python TUI (terminal UI) application for AI-assisted filesystem organization. It uses [Textual](https://textual.textualize.io/) for the interface and calls a local [Ollama](https://ollama.ai/) instance to analyze directory contents and suggest folder reorganization plans.

## Commands

```sh
# Run the app
python organizer.py

# Install dependencies (no pyproject.toml yet — install manually)
pip install textual requests
```

## Customising cleanup presets

Edit `presets.json` in the project root. Each entry is `{"name": "...", "pattern": "glob_pattern"}`.
The `P` key / Presets button runs `fnmatch` against every filename in the currently selected directory.

## Architecture

Single-file app: `organizer.py`

**Layout (two-pane TUI):**
- Left pane (`#left_pane`, 35%): `DirectoryTree` (top 60%) + file preview `TextArea` (bottom 40%)
- Right pane (`#controls`, 65%): status bar, AI response `TextArea`, action `Log`, and three button rows

**Key flow:**
1. User navigates to a folder in the tree and presses `S` (Scout)
2. `_scout_worker()` runs in a background thread — lists files (up to 150), calls Ollama, returns JSON `{"folder_name": ["file1", ...]}`. UI stays responsive while "Thinking..."
3. AI response appears in the right-side `TextArea`
4. User presses `E` (Execute) to parse the JSON and call `shutil.move()` for each file
5. Each execution session is appended to `history.json` for undo support
6. `U` (Undo) pops the last session from history and reverses the moves
7. `D` (Dup Scan) runs `_dup_scan_worker()` — MD5-checksums all files up to 3 levels deep, populates the `TextArea` with a `{"_Duplicates": [...]}` plan; Execute then moves dupes to a `_Duplicates/` subfolder
8. `P` (Presets) runs `fnmatch` patterns from `presets.json` against the current directory and deletes matches

**Ollama integration:**
- Endpoint: `http://localhost:11434/api/generate` (must be running locally)
- Models toggled with `M`: `qwen2.5-coder:7b` (default) and `qwen3-coder:30b`
- Requests use `stream: False` and `format: "json"` to get structured output

**Persistence:**
- Move history is saved to `~/Projects/Scout-Organizer/history.json`

## Key Bindings

| Key | Action |
|-----|--------|
| `S` | Scout — async AI query for organization plan of selected folder |
| `E` | Execute — apply the AI's plan (moves files) |
| `U` | Undo — reverse last execution batch |
| `D` | Dup Scan — async MD5 duplicate scan (up to 3 levels deep) |
| `P` | Presets — pattern-based cleanup via `presets.json` |
| `M` | Toggle Ollama model (7b ↔ 30b) |
| `H` / `?` | Show help modal |
| `Q` | Quit |

## Supporting Files

The `reports/` directory contains static filesystem analysis documents (pre/post cleanup snapshots, package list). The two `full_filesystem_list_*.txt` files are ~99 MB each — use targeted `grep` rather than reading them fully.
