"""Where the launcher keeps its own files (XDG base directories)."""

from __future__ import annotations

import os
from pathlib import Path

PRESETS_ENV = "RPG_LAUNCHER_PRESETS"
MACHINE_ENV = "RPG_LAUNCHER_MACHINE"


def _xdg(variable: str, fallback: str) -> Path:
    value = os.environ.get(variable)
    return Path(value) if value else Path.home() / fallback


def config_home() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config")


def data_home() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share")


def state_home() -> Path:
    return _xdg("XDG_STATE_HOME", ".local/state")


def default_presets_dir() -> Path:
    return config_home() / "rpg-launcher"


def log_dir() -> Path:
    return state_home() / "rpg-launcher" / "logs"
