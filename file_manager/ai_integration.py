"""
AI Integration — OllamaClient replaces the original GeminiClient.
Keeps the same public interface so AIModeScreen and other callers
work without changes.
"""

import json
import platform
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from jsonschema import validate, ValidationError
from jinja2 import Environment, FileSystemLoader

from .automation import FileOrganizer
from .context import DirectoryContextBuilder
from .ai_utils import OllamaExecutor
from .tags import TagManager
from .ai_schema import PLAN_SCHEMA, TAGS_SCHEMA, SEMANTIC_SEARCH_SCHEMA

logger = logging.getLogger(__name__)


class ResponseValidator:
    """Validates AI responses against JSON schemas."""

    @staticmethod
    def _validate(response_text: str, schema: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
        try:
            clean = response_text.replace("```json", "").replace("```", "").strip()
            start = clean.find("{")
            end   = clean.rfind("}")
            if start != -1 and end != -1:
                clean = clean[start:end + 1]
            data = json.loads(clean)
            validate(instance=data, schema=schema)
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid {schema_name} format (JSON Decode Error): {e}")
        except ValidationError as e:
            raise ValueError(f"Invalid {schema_name} format (Schema Validation Error): {e}")

    @staticmethod
    def validate_plan(response_text: str) -> Dict[str, Any]:
        return ResponseValidator._validate(response_text, PLAN_SCHEMA, "plan")

    @staticmethod
    def validate_tags(response_text: str) -> Dict[str, Any]:
        return ResponseValidator._validate(response_text, TAGS_SCHEMA, "tags")

    @staticmethod
    def validate_search(response_text: str) -> Dict[str, Any]:
        return ResponseValidator._validate(response_text, SEMANTIC_SEARCH_SCHEMA, "search")


class OllamaClient:
    """
    Drop-in replacement for the original GeminiClient.
    Uses a local Ollama instance instead of the Gemini CLI.
    """

    def __init__(self, model: Optional[str] = None):
        self.organizer       = FileOrganizer()
        self.executor        = OllamaExecutor(model=model)
        self.context_builder = DirectoryContextBuilder()
        self.tag_manager     = TagManager()

        try:
            self.prompt_env = Environment(
                loader=FileSystemLoader(str(Path(__file__).parent / "prompts"))
            )
        except Exception as e:
            logger.error(f"Failed to load prompt templates: {e}")
            self.prompt_env = None

    # ------------------------------------------------------------------
    # Public interface (same as GeminiClient)
    # ------------------------------------------------------------------

    def generate_plan(self, user_command: str, current_dir: Path) -> Dict[str, Any]:
        """Generate a multi-step execution plan from a natural-language command."""
        context = self.context_builder.get_context(current_dir) if self.prompt_env else {}
        prompt  = self._build_planning_prompt(user_command, current_dir, context)

        if not self.executor.is_available():
            logger.warning("Ollama not available. Using mock response.")
            return json.loads(self._mock_response(user_command, current_dir))

        max_retries = 3
        cur_prompt  = prompt
        last_error  = ""
        last_raw    = ""

        for attempt in range(max_retries + 1):
            raw      = self.executor.execute_prompt(cur_prompt)
            last_raw = raw

            if raw.startswith("Error:"):
                return {"fallback_text": raw, "error": raw, "plan": []}

            try:
                return ResponseValidator.validate_plan(raw)
            except ValueError as e:
                last_error = str(e)
                logger.warning(f"Validation failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    cur_prompt = self._build_validation_feedback(user_command, last_error, prompt)

        return {"fallback_text": last_raw, "error": last_error, "plan": []}

    async def execute_plan_step(self, step: Dict[str, Any], dry_run: bool = True) -> str:
        """Execute a single plan step — no AI call, delegates to FileOrganizer."""
        action = step.get("action")

        def _get(key: str, default: Any = None) -> Any:
            return step.get(key, default)

        try:
            if action == "organize_by_type":
                result = await self.organizer.organize_by_type(
                    Path(_get("source")), Path(_get("target")),
                    move=_get("move", True), dry_run=dry_run,
                )
                count = sum(len(v) for v in result.values())
                return f"{'Would organize' if dry_run else 'Organized'} {count} files by type."

            elif action == "organize_by_date":
                result = await self.organizer.organize_by_date(
                    Path(_get("source")), Path(_get("target")),
                    move=_get("move", True), dry_run=dry_run,
                )
                count = sum(len(v) for v in result.values())
                return f"{'Would organize' if dry_run else 'Organized'} {count} files by date."

            elif action == "cleanup_old_files":
                is_dry  = dry_run or _get("dry_run", False)
                deleted = await self.organizer.cleanup_old_files(
                    Path(_get("directory")), _get("days", 30),
                    _get("recursive", False), is_dry,
                )
                return f"{'Would delete' if is_dry else 'Deleted'} {len(deleted)} files."

            elif action == "find_duplicates":
                dupes = await self.organizer.find_duplicates(
                    Path(_get("directory")), _get("recursive", False)
                )
                count = sum(len(v) for v in dupes.values())
                return f"Found {len(dupes)} duplicate groups ({count} files)."

            elif action == "batch_rename":
                renamed = await self.organizer.batch_rename(
                    Path(_get("directory")), _get("pattern"), _get("replacement"),
                    _get("recursive", False), dry_run=dry_run,
                )
                return f"{'Would rename' if dry_run else 'Renamed'} {len(renamed)} files."

            elif action == "add_tag":
                fp  = Path(_get("file"))
                tag = _get("tag")
                if not dry_run:
                    self.tag_manager.add_tag(fp, tag)
                return f"{'Would add' if dry_run else 'Added'} tag '{tag}' to {fp.name}."

            elif action == "remove_tag":
                fp  = Path(_get("file"))
                tag = _get("tag")
                if not dry_run:
                    self.tag_manager.remove_tag(fp, tag)
                return f"{'Would remove' if dry_run else 'Removed'} tag '{tag}' from {fp.name}."

            else:
                return f"Unknown action: {action}"

        except Exception as e:
            return f"Error: {e}"

    def suggest_tags(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ask Ollama to suggest tags for a list of file descriptors."""
        if not self.executor.is_available():
            return {
                "suggestions": [
                    {"file": f.get("name", "?"), "tags": ["auto"]}
                    for f in files[:5]
                ]
            }
        raw = self.executor.execute_prompt(self._build_tagging_prompt(files), timeout=60)
        try:
            return ResponseValidator.validate_tags(raw)
        except ValueError as e:
            logger.warning(f"Tag validation failed: {e}")
            return {}

    def search_history(self, query: str, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Keyword-based history search."""
        return [h for h in history if query.lower() in h.get("command", "").lower()]

    def process_command(self, command: str, current_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Legacy/compat wrapper."""
        if current_dir is None:
            current_dir = Path.cwd()
        try:
            plan_data = self.generate_plan(command, current_dir)
            if not plan_data.get("plan"):
                return {"action": "unknown", "description": "No plan generated."}
            return {
                "action": "plan_ready",
                "plan": plan_data["plan"],
                "description": f"Generated plan with {len(plan_data['plan'])} steps.",
            }
        except Exception as e:
            return {"action": "unknown", "description": f"Error: {e}"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_planning_prompt(
        self, user_command: str, current_dir: Path, context: Dict[str, Any]
    ) -> str:
        if self.prompt_env:
            try:
                return self.prompt_env.get_template("planning.jinja2").render(
                    current_dir=str(current_dir),
                    os_name=platform.system(),
                    directory_stats=context,
                    user_command=user_command,
                )
            except Exception as e:
                logger.warning(f"Template render failed: {e}")

        return (
            "You are Scout-Organizer, an AI file automation assistant.\n"
            f"Current directory: {current_dir}\n"
            f"User command: {user_command}\n\n"
            "Respond ONLY with a valid JSON object.\n"
            'Schema: {"plan": [{"step": 1, "action": "...", "description": "...", '
            '"is_destructive": false, "source": "...", "target": "..."}]}\n'
            "Available actions: organize_by_type, organize_by_date, "
            "cleanup_old_files, find_duplicates, batch_rename, add_tag, remove_tag.\n"
            "Do not include markdown or explanation."
        )

    def _build_validation_feedback(
        self, user_command: str, error: str, original_prompt: str
    ) -> str:
        if self.prompt_env:
            try:
                return self.prompt_env.get_template("validation.jinja2").render(
                    validation_error=error, user_command=user_command
                )
            except Exception:
                pass
        return (
            f"{original_prompt}\n\n"
            f"Your previous response failed validation: {error}. "
            "Please fix and respond with valid JSON only."
        )

    def _build_tagging_prompt(self, files: List[Dict[str, Any]]) -> str:
        if self.prompt_env:
            try:
                return self.prompt_env.get_template("tagging.jinja2").render(files=files)
            except Exception:
                pass
        file_list = "\n".join(f.get("name", "?") for f in files[:20])
        return (
            "Suggest relevant tags for these files. "
            'Return ONLY JSON: {"suggestions": [{"file": "name", "tags": ["tag1"]}]}\n\n'
            f"Files:\n{file_list}"
        )

    def _mock_response(self, command: str, current_dir: Path) -> str:
        cl = command.lower()
        if "date" in cl:
            action, desc, destructive = "organize_by_date",  "Organize files by date.", False
        elif "organize" in cl or "type" in cl:
            action, desc, destructive = "organize_by_type",  "Organize files by type.", False
        elif "clean" in cl or "old" in cl:
            action, desc, destructive = "cleanup_old_files", "Clean up old files.",     True
        elif "rename" in cl:
            action, desc, destructive = "batch_rename",      "Batch rename files.",     False
        else:
            action, desc, destructive = "find_duplicates",   "Find duplicate files.",   False

        return json.dumps({"plan": [{
            "step": 1, "action": action,
            "source": str(current_dir), "target": str(current_dir / "Organized"),
            "directory": str(current_dir), "move": True, "recursive": False,
            "days": 30, "dry_run": True,
            "description": desc, "is_destructive": destructive,
        }]}, indent=2)


# Backwards-compat alias
GeminiClient = OllamaClient
