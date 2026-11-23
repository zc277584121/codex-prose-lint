import json
from dataclasses import replace

import pytest

from codex_prose_lint.config import Config, api_key, load_config
from codex_prose_lint.install import update_hooks, write_key_file


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
    update_hooks(home, config, remove=True)
    assert json.loads(path.read_text()) == original
    assert list(home.glob("hooks.json.backup-*"))


def test_broken_hook_json_is_not_overwritten(tmp_path):
    path = tmp_path / "hooks.json"
    path.write_text("broken")
    with pytest.raises(ValueError):
        update_hooks(tmp_path, tmp_path / "config.toml")
    assert path.read_text() == "broken"


@pytest.mark.parametrize("changes", [{"threshold": 0}, {"threshold": float("nan")},
    {"batch_size": True}, {"max_candidates": -1}, {"context_mode": "anything"},
    {"budget_seconds": 99}, {"include_user_prompt": "yes"}])
def test_config_rejects_invalid_values(changes):
    with pytest.raises(ValueError):
        replace(Config(), **changes).validate()


def test_env_file_is_read_as_data_without_shell_execution(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    env_file = tmp_path / "env"
    env_file.write_text('export OPENROUTER_API_KEY="literal-$(echo never-execute)"\n')
    assert api_key(replace(Config(), env_file=str(env_file))) == "literal-$(echo never-execute)"


def test_config_resolves_relative_env_file(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('env_file = "private.env"\n')
    assert load_config(path).env_file == str(tmp_path / "private.env")


@pytest.mark.parametrize("original", ['OTHER_KEY="keep"',
    '# Private configuration\nOPENROUTER_API_KEY="old"\nOTHER_KEY="keep"\nexport OPENROUTER_API_KEY="duplicate"\n'])
def test_saving_key_preserves_other_env_entries(tmp_path, monkeypatch, original):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    path = tmp_path / "env"
    path.write_text(original)
    write_key_file(path, "new-test-key")
    assert 'OTHER_KEY="keep"' in path.read_text()
    assert path.read_text().count("OPENROUTER_API_KEY=") == 1
    assert api_key(replace(Config(), env_file=str(path))) == "new-test-key"
    assert path.stat().st_mode & 0o777 == 0o600
