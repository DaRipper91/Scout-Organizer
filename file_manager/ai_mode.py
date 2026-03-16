"""
AI Scout Mode Screen — NL automation powered by aichat.
"""

import asyncio
import json
import os
import subprocess
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Button, Label, Input, RichLog, Checkbox
from textual.screen import Screen
from textual.binding import Binding
from textual import work

from .ai_integration import AiChatClient
from .screens import ConfirmationScreen
from .logger import get_logger

logger = get_logger("ai_mode")

def get_aichat_models() -> List[str]:
    try:
        proc = subprocess.run(["aichat", "--list-models"], capture_output=True, text=True, check=True)
        models = [line.strip() for line in proc.stdout.strip().split("\n") if line.strip()]
        return models if models else ["gemini:gemini-2.5-flash", "claude:claude-3-5-sonnet-20241022"]
    except Exception:
        return ["gemini:gemini-2.5-flash", "claude:claude-3-5-sonnet-20241022"]


class AIModeScreen(Screen):
    """Screen for aichat-powered file automation."""

    CSS = """
    AIModeScreen {
        background: $surface;
    }

    #main-container {
        padding: 1;
        height: 100%;
    }

    #left-panel {
        width: 30%;
        height: 100%;
        border-right: solid $primary;
        padding-right: 1;
    }

    #right-panel {
        width: 70%;
        height: 100%;
        padding-left: 1;
    }

    .action-btn {
        width: 100%;
        margin-bottom: 1;
    }

    #output-log {
        height: 1fr;
        border: solid $secondary;
        margin-top: 1;
        background: $panel;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #input-container {
        height: auto;
        margin-bottom: 1;
    }

    #model-label {
        color: $text-muted;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "back_to_menu", "Back to Menu", priority=True),
        Binding("up",   "history_up",   "Previous Command"),
        Binding("down", "history_down", "Next Command"),
    ]

    MODELS = get_aichat_models()

    def __init__(self):
        super().__init__()
        self._model_idx = 0
        self.ai_client      = AiChatClient(model=self.MODELS[self._model_idx])
        self.current_dir = Path.cwd()
        self.current_plan: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = self._load_history()
        self.history_index = -1

    # ------------------------------------------------------------------
    # History persistence
    # ------------------------------------------------------------------

    def _history_path(self) -> Path:
        p = Path.home() / ".scout" / "command_history.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _load_history(self) -> List[Dict[str, Any]]:
        p = self._history_path()
        if p.exists():
            try:
                with open(p) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_history_entry(self, command: str, plan: List[Dict[str, Any]], status: str) -> None:
        entry = {"timestamp": time.time(), "command": command, "plan": plan, "status": status}
        self.history.append(entry)
        try:
            with open(self._history_path(), "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="main-container"):
            with Horizontal():
                with Vertical(id="left-panel"):
                    yield Label("Quick Actions", classes="section-title")
                    yield Button("Organize by Type",  id="btn_org_type",    classes="action-btn")
                    yield Button("Organize by Date",  id="btn_org_date",    classes="action-btn")
                    yield Button("Cleanup Old Files", id="btn_cleanup",     classes="action-btn")
                    yield Button("Find Duplicates",   id="btn_duplicates",  classes="action-btn")
                    yield Button("Batch Rename",      id="btn_rename",      classes="action-btn")
                    yield Button("Scout Plan",        id="btn_scout",       classes="action-btn", variant="primary")

                with Vertical(id="right-panel"):
                    yield Label("Target Directory:", classes="section-title")
                    yield Input(str(self.current_dir), id="target_dir_input")

                    yield Label("AI Command:", classes="section-title")
                    with Horizontal(id="input-container"):
                        yield Input(
                            placeholder="Describe what you want to do...",
                            id="command_input",
                        )
                        yield Button("Run", id="process_btn", variant="primary")

                    yield Checkbox("Dry-Run Safety Mode", id="dry_run_checkbox", value=True)

                    with Horizontal():
                        yield Button("Search History", id="history_btn",     variant="default")
                        yield Button("Suggest Tags",   id="suggest_tags_btn", variant="warning")
                        yield Button("Toggle Model",   id="toggle_model_btn", variant="default")

                    yield Label(
                        f"Model: {self.MODELS[self._model_idx]}",
                        id="model-label",
                    )

                    yield Label("Output Log:", classes="section-title")
                    yield RichLog(id="output_log", wrap=True, highlight=True, markup=True)

        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#command_input").focus()
        log = self.query_one("#output_log", RichLog)
        aichat_ok = self.ai_client.executor.is_available()
        if aichat_ok:
            log.write(f"[bold green]aichat online.[/]  Model: {self.MODELS[self._model_idx]}")
        else:
            log.write("[bold red]aichat unavailable.[/]  Please install aichat and ensure it is in PATH.")
        log.write("Select a Quick Action or type a command above.")

    # ------------------------------------------------------------------
    # Key / button handlers
    # ------------------------------------------------------------------

    def action_back_to_menu(self) -> None:
        self.app.pop_screen()

    def action_history_up(self) -> None:
        if not self.history:
            return
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            cmd = self.history[-(self.history_index + 1)]["command"]
            inp = self.query_one("#command_input", Input)
            inp.value = cmd
            inp.action_end()

    def action_history_down(self) -> None:
        if self.history_index > 0:
            self.history_index -= 1
            cmd = self.history[-(self.history_index + 1)]["command"]
            inp = self.query_one("#command_input", Input)
            inp.value = cmd
            inp.action_end()
        elif self.history_index == 0:
            self.history_index = -1
            inp = self.query_one("#command_input", Input)
            inp.value = ""
            inp.action_end()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        cmd    = self.query_one("#command_input", Input)

        quick_actions = {
            "btn_org_type":   "Organize files by type",
            "btn_org_date":   "Organize files by date",
            "btn_cleanup":    "Cleanup files older than 30 days",
            "btn_duplicates": "Find duplicate files",
            "btn_rename":     "Rename files matching 'pattern' to 'replacement'",
            "btn_scout":      "Analyze the directory and suggest a logical folder structure",
        }

        if btn_id in quick_actions:
            cmd.value = quick_actions[btn_id]
            cmd.focus()
        elif btn_id == "process_btn":
            self._process_command()
        elif btn_id == "history_btn":
            self._search_history_worker(cmd.value.strip())
        elif btn_id == "suggest_tags_btn":
            self._suggest_tags()
        elif btn_id == "toggle_model_btn":
            self._toggle_model()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "command_input":
            self._process_command()

    # ------------------------------------------------------------------
    # Model toggle
    # ------------------------------------------------------------------

    def _toggle_model(self) -> None:
        self._model_idx = (self._model_idx + 1) % len(self.MODELS)
        new_model = self.MODELS[self._model_idx]
        self.ai_client = AiChatClient(model=new_model)
        self.query_one("#model-label", Label).update(f"Model: {new_model}")
        self.query_one("#output_log", RichLog).write(f"[dim]Switched to {new_model}[/]")

    # ------------------------------------------------------------------
    # Command processing
    # ------------------------------------------------------------------

    def _process_command(self) -> None:
        cmd_input     = self.query_one("#command_input", Input)
        target_input  = self.query_one("#target_dir_input", Input)
        dry_run_chk   = self.query_one("#dry_run_checkbox", Checkbox)
        log           = self.query_one("#output_log", RichLog)

        command = cmd_input.value.strip()
        if not command:
            log.write("[bold red]Error:[/] Please enter a command.")
            return

        target_path = Path(target_input.value.strip())
        if not target_path.exists():
            log.write(f"[bold red]Error:[/] Directory not found: {target_path}")
            return

        log.write(f"\n[bold blue]Processing:[/] {command}")
        self._generate_plan_worker(command, target_path, use_dry_run=dry_run_chk.value)

    def _log_message(self, message: str) -> None:
        self.query_one("#output_log", RichLog).write(message)

    @work(thread=True)
    def _generate_plan_worker(
        self, command: str, target_path: Path, use_dry_run: bool = True
    ) -> None:
        self.app.call_from_thread(self._log_message, f"[dim]Thinking…  target: {target_path}[/]")

        try:
            plan_data = self.ai_client.generate_plan(command, target_path)

            if "fallback_text" in plan_data and not plan_data.get("plan"):
                self.app.call_from_thread(
                    self._log_message,
                    "[bold red]AI could not generate a valid plan.[/]\n"
                    f"[dim]{plan_data['fallback_text']}[/]\n"
                    "[green]Please rephrase and try again.[/]",
                )
                return

            self.current_plan = plan_data.get("plan", [])
            if not self.current_plan:
                self.app.call_from_thread(self._log_message, "[red]AI returned an empty plan.[/]")
                return

            msg = "\n[bold purple]Proposed Plan:[/bold purple]\n"
            for step in self.current_plan:
                icon = "🗑️" if step.get("is_destructive") else "📝"
                msg += f"  {step['step']}. {icon} [bold]{step['action']}[/]: {step['description']}\n"

            if use_dry_run:
                msg += "\n[bold cyan]Dry-Run Simulation:[/bold cyan]\n"
                for step in self.current_plan:
                    try:
                        res = asyncio.run(self.ai_client.execute_plan_step(step, dry_run=True))
                        color = "red" if any(w in res.lower() for w in ("delete", "remove")) else \
                                "yellow" if any(w in res.lower() for w in ("move", "rename", "organize")) else \
                                "green"
                        msg += f"  Step {step['step']}: [{color}]{res}[/{color}]\n"
                    except Exception as e:
                        msg += f"  Step {step['step']}: [red]Simulation error: {e}[/]\n"

            self.app.call_from_thread(self._log_message, msg)

            if use_dry_run:
                self.app.call_from_thread(self._request_confirmation, command)
            else:
                self._save_history_entry(command, self.current_plan, "executed")
                self._execute_plan_worker()

        except Exception as e:
            self.app.call_from_thread(self._log_message, f"[bold red]Error:[/] {e}")

    def _request_confirmation(self, command: str) -> None:
        def check_confirm(confirmed: Optional[bool]) -> None:
            if confirmed:
                self._save_history_entry(command, self.current_plan, "executed")
                self._execute_plan_worker()
            else:
                self._save_history_entry(command, self.current_plan, "cancelled")
                self._log_message("[yellow]Plan cancelled.[/]")

        self.app.push_screen(
            ConfirmationScreen(
                "Execute this plan?",
                confirm_label="Confirm & Execute",
                confirm_variant="success",
            ),
            check_confirm,
        )

    @work(thread=True)
    def _execute_plan_worker(self) -> None:
        if not self.current_plan:
            return
        self.app.call_from_thread(self._log_message, "[bold]Executing Plan…[/]")
        for step in self.current_plan:
            try:
                result = asyncio.run(self.ai_client.execute_plan_step(step, dry_run=False))
                self.app.call_from_thread(
                    self._log_message, f"[green]✔ Step {step['step']}: {result}[/]"
                )
            except Exception as e:
                self.app.call_from_thread(
                    self._log_message, f"[red]✖ Step {step['step']} failed: {e}[/]"
                )
                self.app.call_from_thread(self._log_message, "[bold red]Execution aborted.[/]")
                return
        self.app.call_from_thread(self._log_message, "[bold green]Plan completed.[/]")

    @work(thread=True)
    def _search_history_worker(self, query: str) -> None:
        self.app.call_from_thread(self._log_message, f"\n[dim]Searching history for '{query}'…[/]")
        if not self.history:
            self.app.call_from_thread(self._log_message, "[yellow]No history.[/]")
            return
        results = self.ai_client.search_history(query, self.history)
        if not results:
            self.app.call_from_thread(self._log_message, "[dim]No matches.[/]")
            return
        self.app.call_from_thread(self._log_message, "\n[bold cyan]History Matches:[/bold cyan]")
        for entry in results:
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(entry["timestamp"]))
            self.app.call_from_thread(self._log_message, f"  [{ts}] {entry['command']}")

    @work(thread=True)
    def _suggest_tags(self) -> None:
        self.app.call_from_thread(self._log_message, "\n[dim]Analysing files for tags…[/]")
        files = []
        try:
            for p in self.current_dir.iterdir():
                if p.is_file():
                    try:
                        files.append({"name": p.name, "size_human": str(p.stat().st_size)})
                    except OSError:
                        pass
        except OSError as e:
            logger.error(f"Cannot list dir: {e}")

        if not files:
            self.app.call_from_thread(self._log_message, "[red]No files found.[/]")
            return

        suggestions = self.ai_client.suggest_tags(files)
        if not suggestions or not suggestions.get("suggestions"):
            self.app.call_from_thread(self._log_message, "[yellow]No tags suggested.[/]")
            return

        msg = "\n[bold yellow]Suggested Tags:[/bold yellow]\n"
        for item in suggestions.get("suggestions", []):
            tags = ", ".join(item["tags"])
            msg += f"  [bold]{item['file']}[/]: {tags}\n"

        self.app.call_from_thread(self._log_message, msg)
