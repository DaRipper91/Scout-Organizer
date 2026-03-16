#!/usr/bin/env python3
"""
Scout-Organizer — entry point.

Launches the unified TUI that merges:
  • Dual-pane file manager (from TFM)
  • AI Scout Mode powered by aichat (from Scout-Organizer)

Usage:
    python organizer.py

Environment:
    SCOUT_MODEL   Default model   (default: gemini:gemini-2.5-flash)
"""

from file_manager.app import ScoutApp

if __name__ == "__main__":
    ScoutApp().run()
