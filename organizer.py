import os
import shutil
import json
import hashlib
import fnmatch
import requests
import datetime
from textual.app import App, ComposeResult
import threading
from textual.widgets import Header, Footer, DirectoryTree, Button, Log, TextArea, Label, Static
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELS = ["qwen2.5-coder:7b", "qwen3-coder:30b"]
HISTORY_FILE = os.path.expanduser("~/Projects/Scout-Organizer/history.json")
PRESETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets.json")

DEFAULT_PRESETS = [
    {"name": "Java Error Logs", "pattern": "java_error_*.hprof"},
    {"name": "Trashed Files",   "pattern": ".trashed-*"},
    {"name": "Partial Downloads", "pattern": "*.partial"},
]


def load_presets() -> list:
    if os.path.exists(PRESETS_FILE):
        try:
            with open(PRESETS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    # Write defaults on first run
    with open(PRESETS_FILE, "w") as f:
        json.dump(DEFAULT_PRESETS, f, indent=2)
    return DEFAULT_PRESETS



class ScoutOrganizer(App):
    """An Advanced AI-assisted Filesystem Manager."""

    CSS = """
    Screen { layout: horizontal; }
    #left_pane { width: 35%; }
    #browser { height: 60%; border: solid green; }
    #preview { height: 40%; border: solid cyan; padding: 1; }
    #controls { width: 65%; border: solid blue; }
    #status_bar { height: 3; background: $accent; color: white; padding: 1; }
    #ai_response { height: 38%; border: solid yellow; padding: 1; }
    #log_view { height: 28%; border: solid red; }
    .btn-row { height: 6; layout: horizontal; }
    Button { width: 1fr; margin: 1; }
    #help_bar { height: 5; background: $boost; padding: 1 2; color: $text-muted; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "scout", "AI Scout"),
        Binding("e", "execute", "Execute"),
        Binding("u", "undo", "Undo Last"),
        Binding("d", "scan_duplicates", "Dup Scan"),
        Binding("p", "run_presets", "Presets"),
        Binding("m", "toggle_model", "Switch Model"),
    ]

    def __init__(self):
        super().__init__()
        self.current_model_idx = 0
        self.history = self._load_history()
        self.presets = load_presets()

    def _load_history(self) -> list:
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_history(self) -> None:
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.history, f, indent=2)

    def _current_dir(self) -> str:
        tree = self.query_one(DirectoryTree)
        path = str(tree.cursor_node.data.path) if tree.cursor_node else os.path.expanduser("~")
        return path if os.path.isdir(path) else os.path.dirname(path)

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="left_pane"):
            yield DirectoryTree(os.path.expanduser("~"), id="browser")
            yield TextArea("Select a file to preview.", id="preview", read_only=True)
        with Vertical(id="controls"):
            yield Label(f"Model: {MODELS[self.current_model_idx]}", id="status_bar")
            yield TextArea(id="ai_response", read_only=True)
            yield Log(id="log_view")
            with Horizontal(classes="btn-row"):
                yield Button("Scout (S)", id="btn_scout", variant="primary")
                yield Button("Execute (E)", id="btn_execute", variant="success")
                yield Button("Undo (U)", id="btn_undo", variant="warning")
            with Horizontal(classes="btn-row"):
                yield Button("Dup Scan (D)", id="btn_dupes", variant="error")
                yield Button("Presets (P)", id="btn_presets")
                yield Button("Smart Cleanup", id="btn_clean", variant="error")
                yield Button("Model (M)", id="btn_model")
            yield Static(
                " [S] Scout  [E] Execute  [U] Undo  [D] Dup Scan  [P] Presets  [M] Model  [Q] Quit\n"
                " [↑↓] Navigate tree  [Enter] Expand/collapse folder  [Click] Preview file",
                id="help_bar",
            )
        yield Footer()

    # ── File preview ──────────────────────────────────────────────────────────

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        path = str(event.path)
        try:
            stat = os.stat(path)
            size = stat.st_size
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            try:
                with open(path, "r", errors="replace") as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= 100:
                            lines.append("... (truncated)")
                            break
                        lines.append(line.rstrip())
                content = "\n".join(lines)
            except Exception:
                content = f"[Binary file — {size:,} bytes]"
            header = f"── {os.path.basename(path)}  ({size:,} bytes, {mtime}) ──\n\n"
            self.query_one("#preview").text = header + content
        except Exception as e:
            self.query_one("#preview").text = f"Preview error: {e}"

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_toggle_model(self) -> None:
        self.current_model_idx = (self.current_model_idx + 1) % len(MODELS)
        self.query_one("#status_bar").update(f"Model: {MODELS[self.current_model_idx]}")
        self.query_one(Log).write(f"Switched to {MODELS[self.current_model_idx]}")

    # ── Async Scout ───────────────────────────────────────────────────────────

    def action_scout(self) -> None:
        target = self._current_dir()
        self.query_one(Log).write(f"Scouting {target}...")
        self.query_one("#ai_response").text = "Thinking..."
        threading.Thread(target=self._scout_worker, args=(target,), daemon=True).start()

    def _scout_worker(self, target_path: str) -> None:
        files = os.listdir(target_path)
        file_list_str = "\n".join(files[:150])
        prompt = (
            f"Analyze files in '{target_path}':\n{file_list_str}\n"
            f'Suggest a logical folder structure. Return ONLY JSON: {{"folder_name": ["file1", "file2"]}}.'
        )
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": MODELS[self.current_model_idx],
                "prompt": prompt, "stream": False, "format": "json",
            }, timeout=60)
            result = resp.json().get("response", "{}")
            self.call_from_thread(self._set_ai_response, result, "Scout complete.")
        except Exception as e:
            self.call_from_thread(self.query_one(Log).write, f"Ollama Error: {e}")
            self.call_from_thread(self._set_ai_response, "{}", None)

    def _set_ai_response(self, text: str, log_msg: str | None) -> None:
        self.query_one("#ai_response").text = text
        if log_msg:
            self.query_one(Log).write(log_msg)

    # ── Execute / Undo ────────────────────────────────────────────────────────

    def action_execute(self) -> None:
        plan_text = self.query_one("#ai_response").text
        try:
            plan = json.loads(plan_text)
            target_path = self._current_dir()
            moves = []
            for folder, files in plan.items():
                dest_dir = os.path.join(target_path, folder)
                os.makedirs(dest_dir, exist_ok=True)
                for f in files:
                    src = os.path.join(target_path, f)
                    dst = os.path.join(dest_dir, os.path.basename(f))
                    if os.path.exists(src):
                        shutil.move(src, dst)
                        moves.append({"src": src, "dst": dst})
            self.history.append({"timestamp": str(datetime.datetime.now()), "moves": moves})
            self._save_history()
            self.query_one(Log).write(f"Executed {len(moves)} moves. Undo available.")
            self.query_one(DirectoryTree).reload()
        except Exception as e:
            self.query_one(Log).write(f"Execution Error: {e}")

    def action_undo(self) -> None:
        if not self.history:
            self.query_one(Log).write("No history to undo.")
            return
        last_session = self.history.pop()
        for m in last_session["moves"]:
            if os.path.exists(m["dst"]):
                shutil.move(m["dst"], m["src"])
        self._save_history()
        self.query_one(Log).write("Undo complete.")
        self.query_one(DirectoryTree).reload()

    # ── Async Duplicate Scan ──────────────────────────────────────────────────

    def action_scan_duplicates(self) -> None:
        target = self._current_dir()
        self.query_one(Log).write(f"Scanning duplicates in {target}...")
        self.query_one("#ai_response").text = "Scanning..."
        threading.Thread(target=self._dup_scan_worker, args=(target,), daemon=True).start()

    def _dup_scan_worker(self, target_path: str) -> None:
        hashes: dict = {}
        MAX_SIZE = 500 * 1024 * 1024  # skip files > 500 MB
        try:
            for root, _, files in os.walk(target_path):
                # Limit to 3 levels deep
                if os.path.relpath(root, target_path).count(os.sep) >= 3:
                    continue
                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        if os.path.getsize(fpath) > MAX_SIZE:
                            continue
                        h = hashlib.md5()
                        with open(fpath, "rb") as f:
                            for chunk in iter(lambda: f.read(65536), b""):
                                h.update(chunk)
                        hashes.setdefault(h.hexdigest(), []).append(fpath)
                    except (OSError, PermissionError):
                        continue

            dupes = {k: v for k, v in hashes.items() if len(v) > 1}
            if not dupes:
                self.call_from_thread(self._set_ai_response, "{}", "No duplicates found.")
                return

            # Keep first occurrence; move the rest to _Duplicates/
            plan: dict = {}
            for paths in dupes.values():
                for dup in paths[1:]:
                    rel = os.path.relpath(dup, target_path)
                    plan.setdefault("_Duplicates", []).append(rel)

            total = len(plan.get("_Duplicates", []))
            self.call_from_thread(
                self._set_ai_response,
                json.dumps(plan, indent=2),
                f"Found {total} duplicate(s). Review above, then Execute to move to _Duplicates/.",
            )
        except Exception as e:
            self.call_from_thread(self.query_one(Log).write, f"Scan Error: {e}")
            self.call_from_thread(self._set_ai_response, "{}", None)

    # ── Presets Cleanup ───────────────────────────────────────────────────────

    def action_run_presets(self) -> None:
        target = self._current_dir()
        log = self.query_one(Log)
        removed = 0
        for preset in self.presets:
            name = preset.get("name", preset["pattern"])
            for fname in os.listdir(target):
                if fnmatch.fnmatch(fname, preset["pattern"]):
                    fpath = os.path.join(target, fname)
                    try:
                        os.remove(fpath) if os.path.isfile(fpath) else shutil.rmtree(fpath)
                        log.write(f"Removed [{name}]: {fname}")
                        removed += 1
                    except Exception as e:
                        log.write(f"Error removing {fname}: {e}")
        log.write(f"Presets cleanup done — {removed} item(s) removed.")
        if removed:
            self.query_one(DirectoryTree).reload()

    # ── Smart Cleanup (cache purge) ───────────────────────────────────────────

    def run_smart_cleanup(self) -> None:
        targets = [
            ("Yay Cache",    os.path.expanduser("~/.cache/yay/")),
            ("Gradle Cache", os.path.expanduser("~/.gradle/caches/")),
            ("Pip Cache",    os.path.expanduser("~/.cache/pip/")),
        ]
        for name, path in targets:
            if os.path.exists(path):
                shutil.rmtree(path)
                os.makedirs(path)
                self.query_one(Log).write(f"Purged {name}")
        self.query_one(Log).write("Smart Cleanup Finished.")

    # ── Button dispatch ───────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        actions = {
            "btn_scout":   self.action_scout,
            "btn_execute": self.action_execute,
            "btn_undo":    self.action_undo,
            "btn_dupes":   self.action_scan_duplicates,
            "btn_presets": self.action_run_presets,
            "btn_clean":   self.run_smart_cleanup,
            "btn_model":   self.action_toggle_model,
        }
        action = actions.get(event.button.id)
        if action:
            action()


if __name__ == "__main__":
    ScoutOrganizer().run()
