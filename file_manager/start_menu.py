"""
Start Menu for Scout-Organizer.
"""
from pathlib import Path
import json
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Label, Static
from textual.containers import Container, Vertical

from .user_mode import UserModeScreen
from .ai_mode import AIModeScreen


class StartMenuScreen(Screen):
    """Main start menu — choose File Manager or AI Scout Mode."""

    CSS = """
    StartMenuScreen {
        align: center middle;
        background: $surface;
    }

    #menu-container {
        width: 80;
        height: auto;
        border: round $primary;
        padding: 2 4;
        background: $panel;
        align: center middle;
    }

    #logo {
        text-align: center;
        color: $accent;
        margin-bottom: 1;
        height: auto;
        text-style: bold;
    }

    #tagline {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }

    .menu-button {
        width: 100%;
        margin: 1 0;
        height: 3;
    }

    #recent-container {
        margin-top: 2;
        border-top: solid $secondary;
        padding-top: 1;
    }

    .section-title {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    .recent-btn {
        width: 100%;
        margin-bottom: 1;
    }
    """

    LOGO = """
[bold cyan] ███████╗ ██████╗ ██████╗ ██╗   ██╗████████╗[/bold cyan]
[bold cyan] ██╔════╝██╔════╝██╔═══██╗██║   ██║╚══██╔══╝[/bold cyan]
[bold blue] ███████╗██║     ██║   ██║██║   ██║   ██║   [/bold blue]
[bold blue] ╚════██║██║     ██║   ██║██║   ██║   ██║   [/bold blue]
[bold magenta] ███████║╚██████╗╚██████╔╝╚██████╔╝   ██║   [/bold magenta]
[bold magenta] ╚══════╝ ╚═════╝ ╚═════╝  ╚═════╝    ╚═╝   [/bold magenta]
[dim]         O R G A N I Z E R[/dim]
"""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(id="menu-container"):
            with Vertical():
                yield Static(self.LOGO, id="logo")
                yield Label(
                    "AI-assisted filesystem organizer  ·  Powered by aichat",
                    id="tagline",
                )

                yield Button(
                    "File Manager  (dual-pane)",
                    id="user_mode",
                    variant="primary",
                    classes="menu-button",
                )
                yield Button(
                    "AI Scout Mode  (NL automation)",
                    id="ai_mode",
                    variant="success",
                    classes="menu-button",
                )

                with Vertical(id="recent-container"):
                    yield Label("Recent Directories", classes="section-title")

        yield Footer()

    def on_mount(self) -> None:
        recent_container = self.query_one("#recent-container", Vertical)

        recent_file = Path.home() / ".scout" / "recent.json"
        # Also check legacy TFM path
        if not recent_file.exists():
            recent_file = Path.home() / ".tfm" / "recent.json"

        recent_dirs: list = []
        if recent_file.exists():
            try:
                with open(recent_file) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        recent_dirs = data
            except Exception:
                pass

        if not recent_dirs:
            recent_container.mount(Label("No recent history", classes="text-muted"))
        else:
            for path in recent_dirs[:5]:
                btn = Button(str(path), classes="recent-btn", variant="default")
                btn.tooltip = f"Open {path}"
                recent_container.mount(btn)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "user_mode":
            self.app.push_screen(UserModeScreen())
        elif btn_id == "ai_mode":
            self.app.push_screen(AIModeScreen())
        elif event.button.has_class("recent-btn"):
            path = Path(str(event.button.label))
            if path.exists() and path.is_dir():
                self.app.push_screen(UserModeScreen(initial_path=path))
            else:
                self.notify(f"Directory not found: {path}", severity="error")
