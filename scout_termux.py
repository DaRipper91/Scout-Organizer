#!/usr/bin/env python3
"""
scout_termux.py — AI-assisted filesystem organizer for Termux.

Dependencies: aichat (installed and accessible in PATH)
"""

import os
import sys
import shutil
import json
import hashlib
import fnmatch
import threading
import datetime
import subprocess

# ── Config ────────────────────────────────────────────────────────────────────

MODELS       = ["gemini:gemini-2.5-flash", "claude:claude-3-5-sonnet-20241022"]
HISTORY_FILE = os.path.expanduser("~/scout_history.json")
PRESETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets.json")

DEFAULT_PRESETS = [
    {"name": "Java Error Logs",    "pattern": "java_error_*.hprof"},
    {"name": "Trashed Files",      "pattern": ".trashed-*"},
    {"name": "Partial Downloads",  "pattern": "*.partial"},
]

# ── ANSI helpers ──────────────────────────────────────────────────────────────

NO_COLOR = not sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return text if NO_COLOR else f"\033[{code}m{text}\033[0m"

def cyan(t):    return _c("96", t)
def green(t):   return _c("92", t)
def yellow(t):  return _c("93", t)
def red(t):     return _c("91", t)
def bold(t):    return _c("1",  t)
def dim(t):     return _c("2",  t)
def magenta(t): return _c("95", t)

def clear():
    os.system("clear")

def hr(char="─", width=48):
    print(dim(char * width))

def header(title: str):
    clear()
    hr("═")
    print(bold(cyan(f"  Scout Organizer  ·  {title}")))
    hr("═")

# ── Persistence ───────────────────────────────────────────────────────────────

def load_history() -> list:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_history(history: list) -> None:
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def load_presets() -> list:
    if os.path.exists(PRESETS_FILE):
        try:
            with open(PRESETS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    with open(PRESETS_FILE, "w") as f:
        json.dump(DEFAULT_PRESETS, f, indent=2)
    return DEFAULT_PRESETS

# ── Directory browser ─────────────────────────────────────────────────────────

def browse_directory(start: str) -> str:
    """Let the user navigate to a directory; returns the chosen path."""
    cwd = os.path.abspath(start)
    while True:
        header("Browse")
        print(bold(f"  {cwd}"))
        hr()

        try:
            entries = sorted(os.scandir(cwd), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            print(red("  Permission denied."))
            cwd = os.path.dirname(cwd)
            input(dim("  Press Enter..."))
            continue

        dirs   = [e for e in entries if e.is_dir() and not e.name.startswith(".")]
        hidden = [e for e in entries if e.is_dir() and e.name.startswith(".")]
        files  = [e for e in entries if not e.is_dir()]

        # Print dirs
        numbered = dirs[:30]  # cap for phone screen
        for i, e in enumerate(numbered, 1):
            print(f"  {yellow(str(i)):>5}  {green(e.name + '/')}")

        if not numbered:
            print(dim("  (no subdirectories)"))

        file_count = len(files)
        hidden_count = len(hidden)
        print()
        if file_count:
            print(dim(f"  {file_count} file(s) in this folder"))
        if hidden_count:
            print(dim(f"  {hidden_count} hidden dir(s) not shown"))

        hr()
        print(f"  {bold('0')}  Use {bold(cyan('this folder'))}  [{os.path.basename(cwd) or '/'}]")
        print(f"  {bold('..')} Go up")
        print(f"  {bold('p')}  Type a path manually")
        print(f"  {bold('q')}  Cancel")
        hr()
        choice = input("  > ").strip()

        if choice == "0":
            return cwd
        elif choice in ("", "..", "b"):
            parent = os.path.dirname(cwd)
            if parent != cwd:
                cwd = parent
        elif choice == "p":
            raw = input(dim("  Enter path: ")).strip()
            expanded = os.path.expanduser(raw)
            if os.path.isdir(expanded):
                cwd = os.path.abspath(expanded)
            else:
                print(red("  Not a valid directory."))
                input(dim("  Press Enter..."))
        elif choice == "q":
            return cwd  # return current, don't change
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(numbered):
                    cwd = numbered[idx].path
            except ValueError:
                pass

# ── aichat call (blocking, runs in thread) ─────────────────────────────────────

def call_aichat(prompt: str, model: str, timeout: int = 120) -> str:
    try:
        proc = subprocess.run(
            ["aichat", "-m", model, prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True
        )
        out = proc.stdout.strip()
        if out.startswith("```json"):
            out = out[7:]
        if out.startswith("```"):
            out = out[3:]
        if out.endswith("```"):
            out = out[:-3]
        return out.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"aichat error: {e.stderr or e.stdout}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("aichat request timed out")

# ── Spinner ───────────────────────────────────────────────────────────────────

def run_with_spinner(label: str, fn, *args):
    """Run fn(*args) in a thread; show a spinner; return (result, error)."""
    result = [None]
    error  = [None]
    done   = threading.Event()

    def worker():
        try:
            result[0] = fn(*args)
        except Exception as e:
            error[0] = e
        finally:
            done.set()

    threading.Thread(target=worker, daemon=True).start()

    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    i = 0
    while not done.wait(timeout=0.12):
        print(f"\r  {cyan(frames[i % len(frames)])}  {label}…", end="", flush=True)
        i += 1
    print("\r" + " " * 60 + "\r", end="")

    return result[0], error[0]

# ── Scout ─────────────────────────────────────────────────────────────────────

def action_scout(state: dict) -> None:
    target = state["cwd"]
    model  = MODELS[state["model_idx"]]
    header("Scout")
    print(f"  Folder : {cyan(target)}")
    print(f"  Model  : {yellow(model)}")
    hr()

    try:
        files = os.listdir(target)
    except Exception as e:
        print(red(f"  Cannot list directory: {e}"))
        input(dim("  Press Enter..."))
        return

    if not files:
        print(yellow("  Directory is empty."))
        input(dim("  Press Enter..."))
        return

    file_list = "\n".join(files[:150])
    prompt = (
        f"Analyze the files in the directory '{target}':\n{file_list}\n\n"
        f"Suggest a logical folder structure. "
        f'Return ONLY valid JSON in this format: {{"folder_name": ["file1", "file2"]}}. '
        f"Do not include any explanation."
    )

    raw, err = run_with_spinner("Thinking", call_aichat, prompt, model)

    if err:
        print(red(f"  aichat error: {err}"))
        input(dim("  Press Enter..."))
        return

    # Validate JSON
    try:
        plan = json.loads(raw)
        state["plan"]      = plan
        state["plan_raw"]  = raw
        state["plan_for"]  = target
    except json.JSONDecodeError:
        state["plan"]      = {}
        state["plan_raw"]  = raw
        state["plan_for"]  = target
        print(yellow("  Warning: response is not valid JSON. Stored as-is."))

    print(green("  Scout complete. Plan:"))
    hr()
    _print_plan(state["plan"] or {"(raw response)": [state["plan_raw"]]})
    hr()
    input(dim("  Press Enter to continue..."))

def _print_plan(plan: dict, max_files: int = 8) -> None:
    if not plan:
        print(dim("  (empty plan)"))
        return
    for folder, files in plan.items():
        print(f"  {bold(green(folder + '/'))}")
        shown = files[:max_files]
        for f in shown:
            print(f"      {dim('→')} {f}")
        if len(files) > max_files:
            print(dim(f"      … and {len(files) - max_files} more"))

# ── Execute ───────────────────────────────────────────────────────────────────

def action_execute(state: dict) -> None:
    header("Execute")
    if not state.get("plan"):
        print(yellow("  No plan to execute. Run Scout or Dup Scan first."))
        input(dim("  Press Enter..."))
        return

    target = state.get("plan_for", state["cwd"])
    plan   = state["plan"]

    print(f"  Folder : {cyan(target)}")
    hr()
    _print_plan(plan)
    hr()
    confirm = input(f"  {bold(red('Apply these moves?'))} [y/N] ").strip().lower()
    if confirm != "y":
        print(dim("  Cancelled."))
        input(dim("  Press Enter..."))
        return

    moves = []
    errors = []
    for folder, files in plan.items():
        dest_dir = os.path.join(target, folder)
        os.makedirs(dest_dir, exist_ok=True)
        for fname in files:
            src = os.path.join(target, fname)
            dst = os.path.join(dest_dir, os.path.basename(fname))
            if os.path.exists(src):
                try:
                    shutil.move(src, dst)
                    moves.append({"src": src, "dst": dst})
                    print(f"  {green('✓')} {fname}  →  {folder}/")
                except Exception as e:
                    errors.append(str(e))
                    print(f"  {red('✗')} {fname}: {e}")
            else:
                print(dim(f"  skip {fname} (not found)"))

    if moves:
        state["history"].append({
            "timestamp": str(datetime.datetime.now()),
            "moves": moves,
        })
        save_history(state["history"])
        state["plan"] = {}

    hr()
    print(green(f"  Done — {len(moves)} move(s).") if not errors
          else yellow(f"  Done — {len(moves)} move(s), {len(errors)} error(s)."))
    input(dim("  Press Enter..."))

# ── Undo ──────────────────────────────────────────────────────────────────────

def action_undo(state: dict) -> None:
    header("Undo")
    if not state["history"]:
        print(yellow("  No history to undo."))
        input(dim("  Press Enter..."))
        return

    last = state["history"][-1]
    moves = last.get("moves", [])
    ts    = last.get("timestamp", "?")

    print(f"  Session : {dim(ts)}")
    print(f"  Moves   : {len(moves)}")
    hr()
    for m in moves[:10]:
        print(f"  {dim('←')} {os.path.basename(m['dst'])}  ←  {os.path.basename(os.path.dirname(m['dst']))}/")
    if len(moves) > 10:
        print(dim(f"  … and {len(moves) - 10} more"))
    hr()
    confirm = input(f"  {bold(red('Reverse these moves?'))} [y/N] ").strip().lower()
    if confirm != "y":
        print(dim("  Cancelled."))
        input(dim("  Press Enter..."))
        return

    restored = 0
    for m in moves:
        if os.path.exists(m["dst"]):
            try:
                os.makedirs(os.path.dirname(m["src"]), exist_ok=True)
                shutil.move(m["dst"], m["src"])
                restored += 1
            except Exception as e:
                print(red(f"  ✗ {e}"))

    state["history"].pop()
    save_history(state["history"])
    print(green(f"  Undo complete — {restored} file(s) restored."))
    input(dim("  Press Enter..."))

# ── Duplicate scan ────────────────────────────────────────────────────────────

def _dup_scan_worker(target_path: str) -> dict:
    hashes: dict = {}
    MAX_SIZE = 500 * 1024 * 1024
    for root, _, files in os.walk(target_path):
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
    plan: dict = {}
    for paths in dupes.values():
        for dup in paths[1:]:
            rel = os.path.relpath(dup, target_path)
            plan.setdefault("_Duplicates", []).append(rel)
    return plan

def action_dup_scan(state: dict) -> None:
    target = state["cwd"]
    header("Duplicate Scan")
    print(f"  Folder : {cyan(target)}")
    print(dim("  Scanning up to 3 levels deep (MD5, skips files > 500 MB)"))
    hr()

    plan, err = run_with_spinner("Scanning", _dup_scan_worker, target)

    if err:
        print(red(f"  Scan error: {err}"))
        input(dim("  Press Enter..."))
        return

    dupes = plan.get("_Duplicates", [])
    if not dupes:
        print(green("  No duplicates found."))
        input(dim("  Press Enter..."))
        return

    print(yellow(f"  Found {len(dupes)} duplicate(s):"))
    hr()
    for f in dupes[:20]:
        print(f"  {dim('·')} {f}")
    if len(dupes) > 20:
        print(dim(f"  … and {len(dupes) - 20} more"))
    hr()
    print(dim("  Plan stored. Use Execute to move dupes to _Duplicates/"))

    state["plan"]     = plan
    state["plan_for"] = target
    input(dim("  Press Enter..."))

# ── Presets ───────────────────────────────────────────────────────────────────

def action_presets(state: dict) -> None:
    target  = state["cwd"]
    presets = state["presets"]
    header("Presets Cleanup")
    print(f"  Folder  : {cyan(target)}")
    print(f"  Presets : {len(presets)}")
    hr()
    for p in presets:
        print(f"  {yellow(p['name'])}  {dim(p['pattern'])}")
    hr()
    confirm = input(f"  {bold(red('Delete matching files?'))} [y/N] ").strip().lower()
    if confirm != "y":
        print(dim("  Cancelled."))
        input(dim("  Press Enter..."))
        return

    removed = 0
    try:
        listing = os.listdir(target)
    except Exception as e:
        print(red(f"  {e}"))
        input(dim("  Press Enter..."))
        return

    for preset in presets:
        for fname in listing:
            if fnmatch.fnmatch(fname, preset["pattern"]):
                fpath = os.path.join(target, fname)
                try:
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                    else:
                        shutil.rmtree(fpath)
                    print(f"  {green('✓')} Removed [{preset['name']}]: {fname}")
                    removed += 1
                except Exception as e:
                    print(red(f"  ✗ {fname}: {e}"))

    hr()
    print(green(f"  Done — {removed} item(s) removed."))
    input(dim("  Press Enter..."))

# ── View / edit plan ──────────────────────────────────────────────────────────

def action_view_plan(state: dict) -> None:
    header("Current Plan")
    if state.get("plan"):
        print(f"  Target: {cyan(state.get('plan_for', '?'))}")
        hr()
        _print_plan(state["plan"])
    else:
        print(dim("  No plan loaded. Run Scout or Dup Scan first."))
    hr()
    input(dim("  Press Enter..."))

# ── Main menu ─────────────────────────────────────────────────────────────────

def main():
    state = {
        "cwd":       os.path.expanduser("~"),
        "model_idx": 0,
        "plan":      {},
        "plan_raw":  "",
        "plan_for":  "",
        "history":   load_history(),
        "presets":   load_presets(),
    }

    while True:
        model   = MODELS[state["model_idx"]]
        cwd     = state["cwd"]
        plan_ok = bool(state.get("plan"))
        hist_ok = bool(state["history"])

        header("Main Menu")
        print(f"  Dir   : {cyan(cwd)}")
        print(f"  Model : {yellow(model)}  {dim('(toggle with 6)')}")
        print(f"  Plan  : {green('ready') if plan_ok else dim('none')}"
              f"   History: {green(str(len(state['history'])) + ' session(s)') if hist_ok else dim('empty')}")
        hr()
        print(f"  {bold('1')}  {bold('Browse')} / change directory")
        print(f"  {bold('2')}  {bold('Scout')}  — AI organisation plan")
        print(f"  {bold('3')}  {bold('Execute')} — apply plan"
              + (f"  {dim('(no plan)')}" if not plan_ok else ""))
        print(f"  {bold('4')}  {bold('Undo')}   — reverse last session"
              + (f"  {dim('(no history)')}" if not hist_ok else ""))
        print(f"  {bold('5')}  {bold('Dup Scan')} — find duplicate files")
        print(f"  {bold('6')}  {bold('Toggle model')}  [{yellow(model)}]")
        print(f"  {bold('7')}  {bold('Presets')} — pattern-based cleanup")
        print(f"  {bold('8')}  {bold('View plan')}")
        print(f"  {bold('q')}  Quit")
        hr()

        choice = input("  > ").strip().lower()

        if choice == "1":
            state["cwd"] = browse_directory(state["cwd"])
        elif choice == "2":
            action_scout(state)
        elif choice == "3":
            action_execute(state)
        elif choice == "4":
            action_undo(state)
        elif choice == "5":
            action_dup_scan(state)
        elif choice == "6":
            state["model_idx"] = (state["model_idx"] + 1) % len(MODELS)
        elif choice == "7":
            action_presets(state)
        elif choice == "8":
            action_view_plan(state)
        elif choice in ("q", "quit", "exit"):
            print(dim("  Bye."))
            break


if __name__ == "__main__":
    main()
