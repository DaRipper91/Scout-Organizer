import os
from pathlib import Path
from typing import Optional, Union, Generator


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    f_size: float = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if f_size < 1024.0:
            return f"{f_size:.1f} {unit}"
        f_size /= 1024.0
    return f"{f_size:.1f} PB"


def recursive_scan(directory: Union[Path, str]) -> Generator[os.DirEntry, None, None]:
    """
    Recursively scan directory using os.scandir (iterative, stack-based).
    Yields os.DirEntry objects for all entries found.
    """
    stack = [str(directory)]
    while stack:
        current_dir = stack.pop()
        try:
            with os.scandir(current_dir) as it:
                for entry in it:
                    yield entry
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
        except (PermissionError, OSError):
            pass


# Stub kept for any code that still imports this name.
# aichat availability is checked via aichatExecutor.is_available() instead.
def find_gemini_executable() -> Optional[str]:
    return None
