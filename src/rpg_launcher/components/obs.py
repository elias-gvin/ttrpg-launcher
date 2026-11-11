"""OBS Studio: the [obs] table in a game preset.

A game refers to an OBS profile, scene collection and scene by the names OBS
shows, and OBS is started with its own options for them. The launcher reads
OBS's settings files to check that those names exist; it never writes to them.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from rpg_launcher import paths
from rpg_launcher.components.base import (
    FAIL,
    OK,
    WARN,
    Component,
    Finding,
    LaunchContext,
    Outcome,
    Status,
)
from rpg_launcher.machine import Machine
from rpg_launcher.schema import Reader

# ".obs-wrapped" is the process name of the nixpkgs build.
PROCESS_NAMES = ("obs", ".obs-wrapped")


@dataclass(frozen=True)
class ObsSettings:
    enabled: bool
    profile: str | None
    collection: str | None
    scene: str | None
    record: bool
    checks: tuple[str, ...]


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


def check_references(config_dir: Path, obs: ObsSettings) -> ObsCheck:
    """Check that the profile, scene collection and scene named in a preset exist."""
    check = ObsCheck()
    if not (obs.profile or obs.collection or obs.scene):
        return check
    if not config_dir.is_dir():
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


def _config_dir(machine: Machine) -> Path:
    return machine.app("obs").path("config_dir", paths.config_home() / "obs-studio")


class Obs(Component):
    key = "obs"
    app_options = {"obs": ("config_dir",)}

    def parse(self, top: Reader) -> ObsSettings | None:
        data = top.table("obs")
        if data is None:
            return None
        reader = top.child("obs", data)
        settings = ObsSettings(
            enabled=reader.flag("enabled", True),
            profile=reader.text("profile"),
            collection=reader.text("collection"),
            scene=reader.text("scene"),
            record=reader.flag("record", False),
            checks=reader.texts("checks"),
        )
        reader.done()
        return settings

    def start(self, settings: ObsSettings, context: LaunchContext) -> Iterator[Outcome]:
        app = context.machine.app("obs")
        if not settings.enabled:
            yield Outcome("OBS", Status.SKIPPED, "disabled for this game")
            return
        if not app.enabled:
            yield context.disabled("OBS", app)
            return

        command = list(app.command)
        for option, value in (
            ("--profile", settings.profile),
            ("--collection", settings.collection),
            ("--scene", settings.scene),
        ):
            if value:
                command += [option, value]
        if settings.record:
            command.append("--startrecording")

        references = check_references(_config_dir(context.machine), settings)
        attention = references.problems + references.unverified
        if settings.record:
            recording = (
                "Recording was requested at startup: confirm in OBS that it is "
                "actually recording."
            )
        else:
            recording = (
                "Recording is not started by the launcher: start it in OBS when "
                "you are ready."
            )
        checks = (*settings.checks, recording)

        if context.is_running(app, PROCESS_NAMES):
            if settings.profile or settings.collection or settings.scene or settings.record:
                attention.insert(
                    0,
                    "OBS was already running, so the launcher left it alone. Its "
                    "profile, scene collection, scene and recording state are as "
                    "you left them: set them by hand.",
                )
            yield Outcome(
                "OBS", Status.RUNNING, "left untouched", attention, checks, tuple(command)
            )
            return

        spawned = context.spawn("obs", app, command)
        yield Outcome("OBS", spawned.status, spawned.detail, attention, checks, tuple(command))

    def needed_apps(self, settings: ObsSettings) -> list[str]:
        return ["obs"] if settings.enabled else []

    def diagnose(self, settings: ObsSettings, machine: Machine) -> list[Finding]:
        if not (settings.enabled and machine.app("obs").enabled):
            return []
        check = check_references(_config_dir(machine), settings)
        findings = [Finding(FAIL, text) for text in check.problems]
        findings += [Finding(WARN, text) for text in check.unverified]
        named = settings.profile or settings.collection or settings.scene
        if named and not findings:
            findings.append(Finding(OK, "the OBS names in the preset exist in OBS"))
        return findings
