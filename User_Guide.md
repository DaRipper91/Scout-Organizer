# Scout Organizer - User Guide

Welcome to the **Scout Organizer**, an advanced AI-assisted Terminal User Interface (TUI) application designed to help you analyze, organize, and clean up your filesystem.

## Prerequisites

Before running the application, ensure you have the following installed:
1. **Python 3.10+**
2. **Ollama**: Must be installed and running locally (`http://localhost:11434`).
3. **AI Models**: Pull the required Ollama models:
   ```bash
   ollama run qwen2.5-coder:7b
   ollama run qwen3-coder:30b
   ```

## Installation

1. Navigate to the project directory:
   ```bash
   cd ~/Projects/Scout-Organizer
   ```
2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Requires `textual>=8.0.0` and `requests>=2.32.5`)*

## Running the Application

Launch the application from your terminal:
```bash
python organizer.py
```

## UI Layout

The Scout Organizer uses a two-pane layout:
- **Left Pane (35%)**: 
  - **Directory Tree**: Browse your filesystem.
  - **File Preview**: Select a file to view its contents (up to 100 lines for text) or metadata (for binary files).
- **Right Pane (65%)**: 
  - **Status Bar**: Shows the currently selected AI model.
  - **AI Response View**: Displays the organization plan proposed by the AI.
  - **Log View**: Shows activity history, errors, and system messages.
  - **Control Buttons**: Clickable buttons matching the keyboard shortcuts.

## Features & Keyboard Shortcuts

You can interact with the app using the mouse or keyboard shortcuts:

| Key | Action | Description |
|-----|--------|-------------|
| `[↑↓]` | **Navigate** | Move up and down through the directory tree. |
| `[Enter]` | **Expand/Collapse** | Open or close the currently selected folder. |
| `S` | **Scout** | Analyzes up to 150 files in the selected folder and uses AI to suggest a logical sub-folder structure. The plan appears in the AI Response pane. |
| `E` | **Execute** | Applies the generated AI organization plan or Duplicate plan, moving files into their new folders. |
| `U` | **Undo** | Reverses the last executed batch of moves. Multiple undos are supported. |
| `D` | **Dup Scan** | Scans the selected folder (up to 3 levels deep) for identical files using MD5 hashes. Suggests a plan to move duplicates to a `_Duplicates/` folder. |
| `P` | **Presets** | Immediately deletes files in the current folder that match patterns defined in `presets.json`. *(Use with caution!)* |
| `M` | **Toggle Model** | Switches between the default `qwen2.5-coder:7b` and `qwen3-coder:30b` Ollama models. |
| `Click` | **Smart Cleanup** | Clicking the "Smart Cleanup" button purges known cache directories (`~/.cache/yay/`, `~/.gradle/caches/`, `~/.cache/pip/`). |
| `Q` | **Quit** | Exits the application. |

## Configuration (Presets)

The **Presets** feature relies on a `presets.json` file located in the project root. If it doesn't exist, it will be created automatically with default rules.

You can edit this file to add your own cleanup patterns using standard glob syntax:
```json
[
  {"name": "Java Error Logs",   "pattern": "java_error_*.hprof"},
  {"name": "Trashed Files",     "pattern": ".trashed-*"},
  {"name": "Partial Downloads", "pattern": "*.partial"}
]
```

## History & Persistence
All operations executed via the **Execute** button are tracked in `~/Projects/Scout-Organizer/history.json`. This allows the **Undo** function to reliably restore your files to their original locations, even across application restarts.
