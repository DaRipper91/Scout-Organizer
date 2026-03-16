"""
AiChatExecutor — replaces the old OllamaExecutor.
Calls the local aichat CLI instead of HTTP requests.
"""

import os
import subprocess
from typing import Optional, Tuple

DEFAULT_MODEL = os.environ.get("SCOUT_MODEL", "gemini:gemini-2.5-flash")

class AiChatExecutor:
    """Calls a local aichat instance to execute prompts."""

    def __init__(self, model: Optional[str] = None):
        self.model = model or DEFAULT_MODEL

    def is_available(self) -> bool:
        """Return True if the aichat CLI is reachable."""
        try:
            r = subprocess.run(["aichat", "--version"], capture_output=True, timeout=3)
            return r.returncode == 0
        except Exception:
            return False

    def execute_prompt(self, prompt: str, timeout: int = 90) -> str:
        """Send a prompt to aichat and return the response text."""
        try:
            proc = subprocess.run(
                ["aichat", "-m", self.model, prompt],
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
            return f"Error: aichat failed: {e.stderr or e.stdout}"
        except subprocess.TimeoutExpired:
            return "Error: aichat request timed out."
        except Exception as e:
            return f"Error: {e}"

    def generate_automation_command(self, user_request: str) -> Tuple[Optional[str], str]:
        """
        Translate a natural language request into a scout action hint.
        Returns (None, user_request) so AIModeScreen falls through to the
        full NL→plan flow in ai_integration.py.
        """
        return None, user_request

# Backwards-compat aliases
AIExecutor = AiChatExecutor
OllamaExecutor = AiChatExecutor
