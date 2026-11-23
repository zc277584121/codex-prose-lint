"""Command-line interface; the hook subcommand always emits valid protocol JSON."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from .config import api_key, config_home, load_config, state_home
from .hook import process, write_event
from .install import codex_home, default_config_path, update_hooks, write_key_file
from .judge import PROMPT_HASH, judge
from .scan import annotate, scan


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Flag defensive prose in the last assistant message.")
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("hook", "doctor", "inspect", "install", "uninstall", "configure-key"):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path, default=default_config_path())
        if name in {"install", "uninstall", "doctor"}:
            command.add_argument("--codex-home", type=Path, default=codex_home())
        if name == "inspect":
            command.add_argument("file", type=Path)
            command.add_argument("--question", default="")
            command.add_argument("--live", action="store_true", help="Call OpenRouter; incurs API usage.")
            command.add_argument("--markdown", action="store_true", help="Print an annotated preview with --live.")
        if name == "configure-key":
            command.add_argument("--from-env", action="store_true", help="Save OPENROUTER_API_KEY from this shell.")
    return root


def main() -> None:
    args = parser().parse_args()
    if args.command == "hook":
        output = {}
        try:
            raw = sys.stdin.read(256_001)
            if len(raw) > 256_000:
                raise ValueError("Hook payload is too large")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("Hook payload must be an object")
            output = process(payload, load_config(args.config))
        except Exception as exc:
            # Exception classes are enough for logs; arbitrary network bodies may contain sensitive data.
            print(f"codex-prose-lint: allowed original answer after {type(exc).__name__}", file=sys.stderr)
            write_event(state_home(), {"status": "error", "error_type": type(exc).__name__})
        print(json.dumps(output, ensure_ascii=False))
        return
    try:
        run_command(args)
    except Exception as exc:
        print(f"codex-prose-lint: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


def run_command(args: argparse.Namespace) -> None:
    if args.command in {"install", "uninstall"}:
        path = update_hooks(args.codex_home, args.config, remove=args.command == "uninstall")
        print(f"Updated {path}")
        if args.command == "install":
            print(f"Settings: {args.config}")
            print("Review and trust the new Stop hook in Codex App's Hooks settings before using it.")
            print("Run codex-prose-lint doctor to check the credential.")
        return
    if args.command == "configure-key":
        value = os.environ.get("OPENROUTER_API_KEY", "") if args.from_env else getpass.getpass("OpenRouter API key: ")
        value = value.strip()
        if not value or any(char in value for char in "\r\n\"'"):
            raise ValueError("A non-empty, single-line OpenRouter key is required")
        config = load_config(args.config)
        path = Path(config.env_file) if config.env_file else config_home() / "env"
        write_key_file(path, value)
        print(f"Saved credential to {path} with permissions 0600")
        return
    config = load_config(args.config)
    if args.command == "doctor":
        try:
            api_key(config)
            credential = "available"
        except ValueError:
            credential = "missing"
        print(json.dumps({"config": str(args.config), "model": config.model, "threshold": config.threshold,
                          "context_mode": config.context_mode, "credential": credential,
                          "hooks_file": str(args.codex_home / "hooks.json"), "prompt_hash": PROMPT_HASH,
                          "note": "Hook trust is reviewed in Codex App; this command does not grant trust."}, indent=2))
        return
    message = args.file.read_text()
    candidates = scan(message, context_limit=config.max_context_chars)
    output = {"candidates": [item.to_dict() for item in candidates]}
    if args.live:
        result = judge(candidates[:config.max_candidates], args.question, config, api_key(config))
        output["judgment"] = asdict(result)
        selected = [item for item in candidates if result.scores.get(item.id, 0) >= config.threshold]
        if args.markdown:
            print(annotate(message, selected))
            return
    elif args.markdown:
        raise ValueError("--markdown requires --live")
    print(json.dumps(output, ensure_ascii=False, indent=2))
