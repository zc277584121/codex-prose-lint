import json
import subprocess
import sys
from dataclasses import replace

import pytest

from codex_prose_lint import __version__
from codex_prose_lint.config import Config, load_config
from codex_prose_lint.install import update_hooks


def test_install_and_uninstall_preserve_other_hooks(tmp_path):
    home = tmp_path / "codex"
    home.mkdir()
    path = home / "hooks.json"
    original = {"description": "Personal hooks", "hooks": {
        "Stop": [{"hooks": [{"type": "command", "command": "memory-stop"}]}],
        "SessionStart": [{"hooks": [{"type": "command", "command": "memory-start"}]}],
    }}
    path.write_text(json.dumps(original))
    config = tmp_path / "settings/config.toml"
    update_hooks(home, config)
    update_hooks(home, config)
    installed = json.loads(path.read_text())
    assert len(installed["hooks"]["Stop"]) == 2
    assert installed["hooks"]["Stop"][0] == original["hooks"]["Stop"][0]
    assert "async" not in installed["hooks"]["Stop"][1]["hooks"][0]
    assert "threshold" not in config.read_text()
    assert "env_file" not in config.read_text()
    update_hooks(home, config, remove=True)
    assert json.loads(path.read_text()) == original
    assert list(home.glob("hooks.json.backup-*"))


def test_broken_hook_json_is_not_overwritten(tmp_path):
    path = tmp_path / "hooks.json"
    path.write_text("broken")
    with pytest.raises(ValueError):
        update_hooks(tmp_path, tmp_path / "config.toml")
    assert path.read_text() == "broken"


@pytest.mark.parametrize("changes", [
    {"max_candidates": True}, {"max_candidates": -1}, {"max_candidates": 101},
    {"max_clause_chars": 0}, {"max_message_chars": "100"}, {"mode": "anything"},
])
def test_config_rejects_invalid_active_settings(changes):
    with pytest.raises(ValueError):
        replace(Config(), **changes).validate()


def test_old_model_settings_are_accepted_without_loading_key(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('model = "typesafe/jev-1.14"\nthreshold = 0.8\nbatch_size = 12\n'
                    'context_mode = "paragraph"\nmax_annotations = 8\ntimeout_seconds = 12\n'
                    'budget_seconds = 35\ninclude_user_prompt = true\nenv_file = "missing.env"\n'
                    'max_candidates = 20\nmode = "annotate"\n')
    assert load_config(path) == replace(Config(), max_candidates=20)


def test_unknown_setting_is_rejected(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("max_canddiates = 20\n")
    with pytest.raises(ValueError, match="Unknown configuration"):
        load_config(path)


def test_doctor_reports_runtime_version_and_registered_command(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text("threshold = 0.8\n")
    home = tmp_path / "codex"
    update_hooks(home, config)
    result = subprocess.run(
        [sys.executable, "-m", "codex_prose_lint", "doctor", "--config", str(config), "--codex-home", str(home)],
        text=True, capture_output=True, check=True,
    )
    data = json.loads(result.stdout)
    assert data["version"] == __version__
    assert data["pipeline"] == "lexical"
    assert data["external_model"] is False
    assert data["api_key_required"] is False
    assert data["ignored_legacy_settings"] == ["threshold"]
    assert len(data["registered_hook_commands"]) == 1
    assert sys.executable in data["registered_hook_commands"][0]


def test_inspect_preview_is_local_and_preserves_source(tmp_path):
    path = tmp_path / "answer.md"
    path.write_text("已经完成。不过我不会保证所有人都满意。")
    config = tmp_path / "config.toml"
    result = subprocess.run(
        [sys.executable, "-m", "codex_prose_lint", "inspect", str(path), "--markdown", "--config", str(config)],
        text=True, capture_output=True, check=True,
    )
    assert result.stdout.strip() == "已经完成。~~不过我不会保证所有人都满意~~。"
