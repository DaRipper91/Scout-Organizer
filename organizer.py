#!/usr/bin/env python3
"""
Scout-Organizer — entry point.

Launches the unified TUI that merges:
  • Dual-pane file manager (from TFM)
  • AI Scout Mode powered by Ollama (from Scout-Organizer)

Usage:
    python organizer.py

Environment:
    OLLAMA_HOST   Ollama base URL (default: http://localhost:11434)
    SCOUT_MODEL   Default model   (default: qwen2.5-coder:7b)
"""

from file_manager.app import ScoutApp

if __name__ == "__main__":
    ScoutApp().run()
