"""Shared test helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rpg_launcher.presets import PresetStore

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "presets"

MINIMAL_GAME = """
name = "Minimal"

[invitation.shared.join]
label = "Join"
url = "https://example.org/join"
"""


class PresetCase(unittest.TestCase):
    """A test case with a throwaway presets directory."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "games").mkdir()

    def write_game(self, game_id: str, text: str) -> None:
        (self.root / "games" / f"{game_id}.toml").write_text(text, encoding="utf-8")

    def write_machine(self, machine_id: str, text: str) -> None:
        (self.root / "machines").mkdir(exist_ok=True)
        (self.root / "machines" / f"{machine_id}.toml").write_text(text, encoding="utf-8")

    @property
    def store(self) -> PresetStore:
        return PresetStore(self.root)

    def write_obs_config(self) -> Path:
        """A fake OBS settings directory: profile 'RPG', collection 'Games'."""
        config = self.root / "obs-studio"
        profile = config / "basic" / "profiles" / "RPG"
        profile.mkdir(parents=True)
        (profile / "basic.ini").write_text("[General]\nName=RPG\n", encoding="utf-8")
        scenes = config / "basic" / "scenes"
        scenes.mkdir(parents=True)
        collection = {
            "name": "Games",
            "sources": [
                {"id": "browser_source", "name": "Browser"},
                {"id": "scene", "name": "Samosbor"},
                {"id": "scene", "name": "Frostpunk"},
            ],
        }
        (scenes / "Games.json").write_text(json.dumps(collection), encoding="utf-8")
        (config / "user.ini").write_text("[Basic]\nSceneCollection=Games\n", encoding="utf-8")
        return config
