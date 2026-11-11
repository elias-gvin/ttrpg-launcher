"""Read-only checks against OBS Studio's own configuration files.

The launcher refers to OBS profiles, scene collections and scenes by the names
OBS shows. It never writes to these files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from rpg_launcher.presets import ObsSettings


@dataclass
class ObsCheck:
    problems: list[str] = field(default_factory=list)  # a referenced name is missing
    unverified: list[str] = field(default_factory=list)  # could not be checked


def _ini_value(path: Path, section: str, key: str) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return None
    current = None
    for line in lines:
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
        elif current == section and line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    return None


def profile_names(config_dir: Path) -> list[str]:
    names = []
    for ini in sorted((config_dir / "basic" / "profiles").glob("*/basic.ini")):
        names.append(_ini_value(ini, "General", "Name") or ini.parent.name)
    return names


def _load_collection(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def collections(config_dir: Path) -> dict[str, dict]:
    """Scene collections by the name OBS shows."""
    found = {}
    for path in sorted((config_dir / "basic" / "scenes").glob("*.json")):
        data = _load_collection(path)
        if data is not None:
            found[data.get("name") or path.stem] = data
    return found


def current_collection(config_dir: Path) -> str | None:
    # OBS 31+ keeps this in user.ini; older versions in global.ini.
    for file_name in ("user.ini", "global.ini"):
        name = _ini_value(config_dir / file_name, "Basic", "SceneCollection")
        if name:
            return name
    return None


def scene_names(collection: dict) -> list[str]:
    return [
        source.get("name", "")
        for source in collection.get("sources", [])
        if isinstance(source, dict) and source.get("id") == "scene"
    ]


def _listed(names: list[str]) -> str:
    return ", ".join(f"'{name}'" for name in names) or "none"


def check_references(config_dir: Path | None, obs: ObsSettings) -> ObsCheck:
    """Check that the profile, scene collection and scene named in a preset exist."""
    check = ObsCheck()
    if not (obs.profile or obs.collection or obs.scene):
        return check
    if config_dir is None or not config_dir.is_dir():
        check.unverified.append(
            f"OBS settings were not found at {config_dir}, so the profile, scene "
            f"collection and scene names could not be checked. If OBS keeps its "
            f"settings elsewhere on this machine, set config_dir under [apps.obs] "
            f"in the machine preset."
        )
        return check

    if obs.profile:
        profiles = profile_names(config_dir)
        if obs.profile not in profiles:
            check.problems.append(
                f"OBS has no profile called '{obs.profile}'. "
                f"Profiles on this machine: {_listed(profiles)}."
            )

    known = collections(config_dir)
    collection_name = obs.collection
    if obs.collection and obs.collection not in known:
        check.problems.append(
            f"OBS has no scene collection called '{obs.collection}'. "
            f"Scene collections on this machine: {_listed(sorted(known))}."
        )
        return check

    if obs.scene:
        collection_name = collection_name or current_collection(config_dir)
        if collection_name not in known:
            check.unverified.append(
                f"Could not tell which OBS scene collection is active, so the "
                f"scene '{obs.scene}' was not checked. Name the collection in the "
                f"preset to have it checked."
            )
            return check
        scenes = scene_names(known[collection_name])
        if obs.scene not in scenes:
            check.problems.append(
                f"OBS scene collection '{collection_name}' has no scene called "
                f"'{obs.scene}'. Scenes in it: {_listed(scenes)}."
            )
    return check
