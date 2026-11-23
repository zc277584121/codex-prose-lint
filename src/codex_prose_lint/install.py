"""Merge one owned handler without changing other hooks or trust decisions."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import sys
import tempfile
import time
from pathlib import Path

from .config import config_home

STATUS = "Checking defensive prose"
DEFAULT_CONFIG = '''# Codex Prose Lint
max_candidates = 36
max_message_chars = 30000
max_clause_chars = 800
max_context_chars = 2400
mode = "annotate"
'''


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def owned(handler: dict) -> bool:
    try:
        command = shlex.split(handler.get("command", ""))
    except ValueError:
        return False
    return handler.get("statusMessage") == STATUS and "codex_prose_lint" in command and "hook" in command


def atomic_write(path: Path, value: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(value)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def update_hooks(home: Path, config_path: Path, *, remove: bool = False) -> Path:
    path = home / "hooks.json"
    original = path.read_text() if path.exists() else None
    data = json.loads(original) if original else {"hooks": {}}
    if not isinstance(data, dict) or not isinstance(data.get("hooks"), dict):
        raise ValueError("hooks.json must contain a hooks object")
    groups = data["hooks"].get("Stop", [])
    if not isinstance(groups, list):
        raise ValueError("hooks.Stop must be an array")
    kept = []
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
            raise ValueError("Each Stop group must contain a hooks array")
        handlers = [h for h in group["hooks"] if not owned(h)]
        if handlers or not group["hooks"]:
            kept.append({**group, "hooks": handlers})
    if not remove:
        # Do not resolve the Python symlink: its virtual-environment path provides the package.
        command = shlex.join([str(Path(sys.executable).absolute()), "-m", "codex_prose_lint", "hook", "--config", str(config_path.absolute())])
        kept.append({"hooks": [{"type": "command", "command": command, "timeout": 50, "statusMessage": STATUS}]})
    if kept:
        data["hooks"]["Stop"] = kept
    else:
        data["hooks"].pop("Stop", None)
    updated = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if original != updated:
        if path.exists():
            shutil.copy2(path, path.with_name(f"hooks.json.backup-{time.time_ns()}"))
        atomic_write(path, updated)
    if not remove and not config_path.exists():
        atomic_write(config_path, DEFAULT_CONFIG)
    return path


def default_config_path() -> Path:
    return config_home() / "config.toml"
