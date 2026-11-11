"""Check presets and this machine before game time, without starting anything."""

from __future__ import annotations

import shutil
import subprocess

from rpg_launcher import clipboard, components
from rpg_launcher.components.base import FAIL, OK, WARN, Finding
from rpg_launcher.machine import AppSettings, Machine
from rpg_launcher.presets import Game, PresetStore
from rpg_launcher.schema import PresetError


def _flatpak_app(command: tuple[str, ...]) -> str | None:
    if command[:2] != ("flatpak", "run"):
        return None
    return next((arg for arg in command[2:] if not arg.startswith("-")), None)


def check_app(app: AppSettings) -> str | None:
    """Return what is wrong with starting this app here, or None if it looks fine."""
    program = app.command[0]
    if shutil.which(program) is None:
        return (
            f"'{program}' was not found. Install it, or set the right command "
            f"under [apps.{app.id}] in the machine preset."
        )
    flatpak_app = _flatpak_app(app.command)
    if flatpak_app:
        try:
            installed = (
                subprocess.run(
                    ["flatpak", "info", flatpak_app],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=15,
                ).returncode
                == 0
            )
        except (OSError, subprocess.SubprocessError):
            installed = False
        if not installed:
            return f"the Flatpak app '{flatpak_app}' is not installed."
    return None


def _needed_apps(game: Game) -> list[str]:
    needed = []
    for component in components.COMPONENTS:
        if component.key in game.parts:
            needed += component.needed_apps(game.parts[component.key])
    return list(dict.fromkeys(needed))


def _check_game(game: Game, machine: Machine) -> list[Finding]:
    findings = [Finding(OK, f"{game.name}: preset is valid ({game.source})")]

    if not game.parts:
        findings.append(Finding(WARN, f"{game.name}: nothing to start or open."))

    for component in components.COMPONENTS:
        if component.key in game.parts:
            for finding in component.diagnose(game.parts[component.key], machine):
                findings.append(Finding(finding.level, f"{game.name}: {finding.text}"))

    if game.invitation.has_links:
        count = len(game.invitation.players) + len(game.invitation.shared)
        findings.append(Finding(OK, f"{game.name}: invitation has {count} player link(s)"))
    else:
        findings.append(
            Finding(
                FAIL,
                f"{game.name}: no player links. Add [invitation.shared.<id>] or "
                f"[invitation.players.<id>] with a url to {game.source}.",
            )
        )
    return findings


def diagnose(
    store: PresetStore, explicit_machine: str | None = None, game_id: str | None = None
) -> list[Finding]:
    findings = [Finding(OK, f"Presets: {store.root}")]

    try:
        machine = store.resolve_machine(explicit_machine)
    except PresetError as error:
        findings += [Finding(FAIL, problem) for problem in error.problems]
        findings.append(
            Finding(WARN, "Checking games with built-in defaults instead of a machine preset.")
        )
        machine = Machine.builtin()
    else:
        findings.append(Finding(OK, f"Machine: {machine.name} ({machine.source})"))

    game_ids = store.game_ids()
    for other_id in store.machine_ids():
        if other_id == machine.id and not machine.is_builtin:
            other = machine
        else:
            try:
                other = store.load_machine(other_id)
            except PresetError as error:
                findings += [Finding(FAIL, problem) for problem in error.problems]
                continue
        for target in other.overrides:
            if target not in game_ids:
                findings.append(
                    Finding(
                        WARN,
                        f"{other.source}: overrides.{target} matches no game "
                        f"(games: {', '.join(game_ids) or 'none'}).",
                    )
                )

    if not game_ids:
        findings.append(Finding(FAIL, f"No game presets in {store.root / 'games'}."))

    needed: dict[str, list[str]] = {}
    for current_id in [game_id] if game_id else game_ids:
        try:
            game = store.load_game(current_id, machine)
        except PresetError as error:
            findings += [Finding(FAIL, problem) for problem in error.problems]
            continue
        findings += _check_game(game, machine)
        for app_id in _needed_apps(game):
            needed.setdefault(app_id, []).append(game.name)

    for app_id, games in needed.items():
        app = machine.app(app_id)
        used_by = f"used by {', '.join(games)}"
        if not app.enabled:
            findings.append(
                Finding(WARN, f"{app_id}: disabled on this machine, will be skipped ({used_by}).")
            )
            continue
        problem = check_app(app)
        if problem:
            findings.append(Finding(FAIL, f"{app_id}: {problem} ({used_by})"))
        else:
            findings.append(Finding(OK, f"{app_id}: available as '{' '.join(app.command)}'"))

    if clipboard.find_tool():
        findings.append(Finding(OK, "Clipboard: copy tool available"))
    else:
        findings.append(
            Finding(
                WARN,
                "Clipboard: no copy tool found. Invitations can be shown but not "
                "copied. Install wl-clipboard (Wayland) or xclip (X11).",
            )
        )
    return findings
