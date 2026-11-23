"""Small, explicit configuration and credential loading."""

from __future__ import annotations

import math
import os
import shlex
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path


def config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "codex-prose-lint"


def state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "codex-prose-lint"


@dataclass(frozen=True)
class Config:
    model: str = "typesafe/jev-1.14"
    threshold: float = 0.8
    context_mode: str = "paragraph"
    batch_size: int = 12
    max_candidates: int = 36
    max_annotations: int = 8
    max_message_chars: int = 30000
    max_context_chars: int = 2400
    timeout_seconds: float = 12.0
    budget_seconds: float = 35.0
    include_user_prompt: bool = True
    mode: str = "annotate"
    env_file: str = ""

    def validate(self) -> Config:
        for name in ("threshold", "timeout_seconds", "budget_seconds"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if not 0 < self.threshold <= 1:
            raise ValueError("threshold must be in (0, 1]")
        if not 0 < self.timeout_seconds <= self.budget_seconds <= 45:
            raise ValueError("timeouts must satisfy 0 < timeout_seconds <= budget_seconds <= 45")
        for name, limit in (("batch_size", 36), ("max_candidates", 100), ("max_annotations", 30),
                            ("max_message_chars", 100000), ("max_context_chars", 10000)):
            value = getattr(self, name)
            if type(value) is not int or not 0 < value <= limit:
                raise ValueError(f"{name} must be an integer in [1, {limit}]")
        if self.context_mode not in {"clause", "sentence", "paragraph"}:
            raise ValueError("context_mode must be clause, sentence, or paragraph")
        if self.mode not in {"annotate", "report"}:
            raise ValueError("mode must be annotate or report")
        if not isinstance(self.model, str) or not self.model:
            raise ValueError("model must be a non-empty string")
        if type(self.include_user_prompt) is not bool or not isinstance(self.env_file, str):
            raise ValueError("invalid include_user_prompt or env_file")
        return self


def load_config(path: Path | None = None) -> Config:
    path = path or config_home() / "config.toml"
    data = tomllib.loads(path.read_text()) if path.exists() else {}
    unknown = set(data) - {field.name for field in fields(Config)}
    if unknown:
        raise ValueError(f"Unknown configuration fields: {', '.join(sorted(unknown))}")
    if data.get("env_file"):
        value = Path(data["env_file"]).expanduser()
        data["env_file"] = str(value if value.is_absolute() else path.parent / value)
    else:
        data["env_file"] = str(path.parent / "env")
    return Config(**data).validate()


def api_key(config: Config) -> str:
    value = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if value:
        return value
    path = Path(config.env_file).expanduser() if config.env_file else config_home() / "env"
    if path.is_file():
        for line in path.read_text().splitlines():
            line = line.strip().removeprefix("export ").strip()
            name, separator, raw = line.partition("=")
            if separator and name.strip() == "OPENROUTER_API_KEY":
                tokens = shlex.split(raw, comments=True)
                if len(tokens) == 1 and tokens[0]:
                    return tokens[0]
    raise ValueError("OPENROUTER_API_KEY is missing; run doctor or configure a private env file")
