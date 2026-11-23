"""Local settings with compatibility for pre-0.2 configuration files."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

# Accepted for migration only; these fields have no effect on the local pipeline.
LEGACY_FIELDS = {
    "model", "threshold", "context_mode", "batch_size", "max_annotations",
    "timeout_seconds", "budget_seconds", "include_user_prompt", "env_file",
}


def config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "codex-prose-lint"


def state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "codex-prose-lint"


@dataclass(frozen=True)
class Config:
    max_candidates: int = 36
    max_message_chars: int = 30000
    max_clause_chars: int = 800
    max_context_chars: int = 2400
    mode: str = "annotate"

    def validate(self) -> Config:
        for name, limit in (("max_candidates", 100), ("max_message_chars", 100000),
                            ("max_clause_chars", 10000), ("max_context_chars", 10000)):
            value = getattr(self, name)
            if type(value) is not int or not 0 < value <= limit:
                raise ValueError(f"{name} must be an integer in [1, {limit}]")
        if self.mode not in {"annotate", "report"}:
            raise ValueError("mode must be annotate or report")
        return self


def read_settings(path: Path) -> dict:
    return tomllib.loads(path.read_text()) if path.exists() else {}


def load_config(path: Path | None = None) -> Config:
    path = path or config_home() / "config.toml"
    data = read_settings(path)
    active = {field.name for field in fields(Config)}
    unknown = set(data) - active - LEGACY_FIELDS
    if unknown:
        raise ValueError(f"Unknown configuration fields: {', '.join(sorted(unknown))}")
    return Config(**{key: value for key, value in data.items() if key in active}).validate()
