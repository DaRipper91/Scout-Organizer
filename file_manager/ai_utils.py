"""
OllamaExecutor — replaces the old Gemini CLI AIExecutor.
Calls the local Ollama HTTP API instead of shelling out to gemini.
"""

import os
import requests
from typing import Optional, Tuple

OLLAMA_HOST   = os.environ.get("OLLAMA_HOST", "http://100.115.141.124:11434")
OLLAMA_URL    = f"{OLLAMA_HOST}/api/generate"
DEFAULT_MODEL = os.environ.get("SCOUT_MODEL", "qwen2.5-coder:7b")


class OllamaExecutor:
    """Calls a local Ollama instance to execute prompts."""

    def __init__(self, model: Optional[str] = None):
        self.model = model or DEFAULT_MODEL

    def is_available(self) -> bool:
        """Return True if the Ollama server is reachable."""
        try:
            r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def execute_prompt(self, prompt: str, timeout: int = 90) -> str:
        """Send a prompt to Ollama and return the response text."""
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={
                    "model":  self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except requests.exceptions.ConnectionError:
            return "Error: Cannot connect to Ollama. Is it running?"
        except requests.exceptions.Timeout:
            return "Error: Ollama request timed out."
        except Exception as e:
            return f"Error: {e}"

    def generate_automation_command(self, user_request: str) -> Tuple[Optional[str], str]:
        """
        Translate a natural language request into a scout action hint.
        Returns (None, user_request) so AIModeScreen falls through to the
        full NL→plan flow in ai_integration.py.
        """
        return None, user_request


# Backwards-compat alias so any code that still imports AIExecutor still works.
AIExecutor = OllamaExecutor
