#!/usr/bin/env python3
"""
Scout-Organizer — unified app entry point.
"""

from pathlib import Path
from textual.app import App
from textual.binding import Binding

from .start_menu import StartMenuScreen
from .config import ConfigManager


class ScoutApp(App):
    """Scout-Organizer: AI-assisted filesystem organizer + dual-pane file manager."""

    CSS = """
    Screen {
        background: $surface;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    TITLE = "Scout-Organizer"

    def __init__(self):
        super().__init__()
        # Use ~/.scout as config dir; fall back creates it on first run
        self.config_manager = ConfigManager(config_dir=Path.home() / ".scout")

    def on_mount(self) -> None:
        self.load_configured_theme()
        self.push_screen(StartMenuScreen())

    def load_configured_theme(self) -> None:
        theme_name = self.config_manager.get_theme()
        self.load_theme_by_name(theme_name)

    def load_theme_by_name(self, theme_name: str) -> None:
        try:
            theme_path = Path(__file__).parent / "themes" / f"{theme_name}.tcss"
            if theme_path.exists():
                with open(theme_path) as f:
                    self.stylesheet.add_source(f.read(), is_default_css=False)
                    self.refresh_css()
        except Exception as e:
            pass  # Silently fall back to Textual defaults


# Keep the old name as an alias so any leftover imports still work
FileManagerApp = ScoutApp


def main():
    ScoutApp().run()


if __name__ == "__main__":
    main()
