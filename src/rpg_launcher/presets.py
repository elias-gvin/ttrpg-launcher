"""Load game and machine presets and resolve them into one effective setup.

A game preset holds what a campaign needs. A machine preset holds how this
computer differs. The effective game is the game file with the machine's
overrides for that game merged on top, so later layers (such as per-session
values) can be added the same way.

The launcher itself reads only a game's name, reminders and invitation. Every
other part of a game file belongs to a component (see the components package).
"""

from __future__ import annotations

import difflib
import os
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rpg_launcher import components, paths
from rpg_launcher.machine import Machine, parse_machine
from rpg_launcher.schema import PresetError, Reader, merge, read_toml


@dataclass(frozen=True)
class Link:
    id: str
    label: str
    url: str


@dataclass(frozen=True)
class Player:
    id: str
    name: str
    url: str


@dataclass(frozen=True)
class Invitation:
    intro: str | None = None
    note: str | None = None
    player_link_label: str = "Join game"
    shared: tuple[Link, ...] = ()
    players: tuple[Player, ...] = ()

    @property
    def has_links(self) -> bool:
        return bool(self.shared or self.players)


@dataclass(frozen=True)
class Game:
    id: str
    name: str
    source: str
    invitation: Invitation
    checks: tuple[str, ...]
    # Settings of each component this game uses, by the component's key.
    parts: dict[str, Any] = field(default_factory=dict)


def _parse_invitation(top: Reader) -> Invitation:
    data = top.table("invitation")
    if data is None:
        return Invitation()
    reader = top.child("invitation", data)
    intro = reader.text("intro")
    note = reader.text("note")
    player_link_label = reader.text("player_link_label", default="Join game")
    shared_data = reader.tables("shared")
    players_data = reader.tables("players")
    reader.done()

    shared = []
    for link_id, link_data in shared_data.items():
        link_reader = reader.child(f"shared.{link_id}", link_data)
        shared.append(
            Link(
                id=link_id,
                label=link_reader.text("label", default=link_id),
                url=link_reader.url("url"),
            )
        )
        link_reader.done()

    players = []
    for player_id, player_data in players_data.items():
        player_reader = reader.child(f"players.{player_id}", player_data)
        players.append(
            Player(
                id=player_id,
                name=player_reader.text("name", default=player_id),
                url=player_reader.url("url"),
            )
        )
        player_reader.done()

    return Invitation(
        intro=intro,
        note=note,
        player_link_label=player_link_label,
        shared=tuple(shared),
        players=tuple(players),
    )


def parse_game(game_id: str, data: dict, source: str) -> Game:
    problems: list[str] = []
    top = Reader(data, source, "", problems)
    name = top.text("name", default=game_id)
    checks = top.texts("checks")
    invitation = _parse_invitation(top)
    parts = {}
    for component in components.COMPONENTS:
        settings = component.parse(top)
        if settings is not None:
            parts[component.key] = settings
    top.done()

    if problems:
        raise PresetError(problems)
    return Game(
        id=game_id,
        name=name,
        source=source,
        invitation=invitation,
        checks=checks,
        parts=parts,
    )


def find_presets_dir(explicit: str | None = None) -> Path:
    """--presets, then $RPG_LAUNCHER_PRESETS, then ~/.config/rpg-launcher."""
    chosen = explicit or os.environ.get(paths.PRESETS_ENV)
    root = Path(os.path.expanduser(chosen)) if chosen else paths.default_presets_dir()
    if not (root / "games").is_dir():
        raise PresetError(
            f"No game presets found: {root / 'games'} does not exist.\n"
            f"Create it (see examples/presets in the launcher repository), "
            f"pass --presets DIR, or set ${paths.PRESETS_ENV}."
        )
    return root


class PresetStore:
    """A presets directory: games/*.toml and machines/*.toml."""

    def __init__(self, root: Path):
        self.root = root

    def _ids(self, kind: str) -> list[str]:
        return sorted(path.stem for path in (self.root / kind).glob("*.toml"))

    def game_ids(self) -> list[str]:
        return self._ids("games")

    def machine_ids(self) -> list[str]:
        return self._ids("machines")

    def load_game(self, game_id: str, machine: Machine | None = None) -> Game:
        shown = f"games/{game_id}.toml"
        data = read_toml(self.root / "games" / f"{game_id}.toml", shown)
        if machine and game_id in machine.overrides:
            data = merge(data, machine.overrides[game_id])
            shown = f"{shown} with overrides from {machine.source}"
        return parse_game(game_id, data, shown)

    def find_game(self, wanted: str) -> str:
        """Resolve what the GM typed (a file name or a game name) to a game id."""
        ids = self.game_ids()
        if wanted in ids:
            return wanted
        folded = wanted.casefold()
        names = {}
        for game_id in ids:
            names[game_id.casefold()] = game_id
            try:
                names.setdefault(self.load_game(game_id).name.casefold(), game_id)
            except PresetError:
                pass
        if folded in names:
            return names[folded]
        close = difflib.get_close_matches(folded, sorted(names), n=1)
        hint = f" Did you mean '{names[close[0]]}'?" if close else ""
        available = ", ".join(ids) or "none"
        raise PresetError(
            f"No game preset called '{wanted}'.{hint} Available games: {available}."
        )

    def load_machine(self, machine_id: str) -> Machine:
        shown = f"machines/{machine_id}.toml"
        data = read_toml(self.root / "machines" / f"{machine_id}.toml", shown)
        app_options: dict[str, set[str]] = {}
        for component in components.COMPONENTS:
            for app_id, keys in component.app_options.items():
                app_options.setdefault(app_id, set()).update(keys)
        return parse_machine(machine_id, data, shown, app_options)

    def resolve_machine(
        self, explicit: str | None = None, hostname: str | None = None
    ) -> Machine:
        """--machine or $RPG_LAUNCHER_MACHINE, otherwise the hostname match."""
        ids = self.machine_ids()
        explicit = explicit or os.environ.get(paths.MACHINE_ENV)
        if explicit:
            if explicit not in ids:
                available = ", ".join(ids) or "none"
                raise PresetError(
                    f"No machine preset called '{explicit}'. "
                    f"Available machines: {available}."
                )
            return self.load_machine(explicit)
        if not ids:
            return Machine.builtin()

        hostname = hostname or socket.gethostname()
        matches, broken = [], []
        for machine_id in ids:
            try:
                machine = self.load_machine(machine_id)
            except PresetError as error:
                broken.extend(error.problems)
                continue
            if machine_id == hostname or hostname in machine.hostnames:
                matches.append(machine)
        if len(matches) == 1:
            return matches[0]
        if matches:
            names = ", ".join(machine.id for machine in matches)
            raise PresetError(
                f"Several machine presets match hostname '{hostname}': {names}. "
                f"Pass --machine <id> or fix their hostnames."
            )
        raise PresetError(
            [
                f"No machine preset matches this computer (hostname '{hostname}'). "
                f"Available machines: {', '.join(ids)}. Pass --machine <id>, or add "
                f'hostnames = ["{hostname}"] to the right file in machines/.',
                *broken,
            ]
        )
