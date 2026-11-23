"""Command-line interface for the local scanner and Stop hook."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .config import LEGACY_FIELDS, load_config, read_settings, state_home
from .hook import PROMPT_HASH, process, select_candidates, write_event
from .install import codex_home, default_config_path, owned, update_hooks
from .scan import annotate


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Review lexical candidates in the last assistant message.")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("hook", "doctor", "inspect", "install", "uninstall"):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path, default=default_config_path())
        if name in {"install", "uninstall", "doctor"}:
            command.add_argument("--codex-home", type=Path, default=codex_home())
        if name == "inspect":
            command.add_argument("file", type=Path)
            command.add_argument("--markdown", action="store_true", help="Preview every lexical candidate with strikethrough, before contextual review.")
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
            print("Run codex-prose-lint doctor to inspect the installed version and hook command.")
        return
    config = load_config(args.config)
    if args.command == "doctor":
        hooks_path = args.codex_home / "hooks.json"
        data = json.loads(hooks_path.read_text()) if hooks_path.exists() else {}
        commands = [handler["command"] for group in data.get("hooks", {}).get("Stop", [])
                    for handler in group.get("hooks", []) if owned(handler)]
        print(json.dumps({
            "version": __version__, "pipeline": "lexical",
            "external_model": False, "api_key_required": False,
            "python_executable": sys.executable, "module_path": str(Path(__file__).resolve()),
            "config": str(args.config), "settings": asdict(config),
            "ignored_legacy_settings": sorted(set(read_settings(args.config)) & LEGACY_FIELDS),
            "hooks_file": str(hooks_path), "registered_hook_commands": commands,
            "prompt_hash": PROMPT_HASH,
        }, indent=2))
        return
    message = args.file.read_text()
    if len(message) > config.max_message_chars:
        raise ValueError("Message exceeds max_message_chars")
    candidates, omitted = select_candidates(message, config)
    if args.markdown:
        print(annotate(message, candidates))
    else:
        print(json.dumps({"version": __version__, "pipeline": "lexical",
                          "candidates": [item.to_dict() for item in candidates],
                          "omitted_candidates": omitted}, ensure_ascii=False, indent=2))
