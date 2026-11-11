"""Load game and machine presets and resolve them into one effective setup.

A game preset holds what a campaign needs. A machine preset holds how this
computer differs. The effective game is the game file with the machine's
overrides for that game merged on top, so later layers (such as per-session
values) can be added the same way.

URLs are kept exactly as written: the launcher never parses or rewrites them.
"""

from __future__ import annotations

import difflib
import os
import socket
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from rpg_launcher import paths


class PresetError(Exception):
    """One or more problems in the preset files that the GM can fix."""

    def __init__(self, problems: list[str] | str):
        self.problems = [problems] if isinstance(problems, str) else list(problems)
        super().__init__("\n".join(self.problems))


@dataclass(frozen=True)
class OpenItem:
    """A page the GM's browser opens. Never part of the player invitation."""

    id: str
    label: str
    url: str
    window: bool
    enabled: bool
    checks: tuple[str, ...]


@dataclass(frozen=True)
class ObsSettings:
    enabled: bool
    profile: str | None
    collection: str | None
    scene: str | None
    record: bool
    checks: tuple[str, ...]


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
    apps: tuple[str, ...]
    obs: ObsSettings | None
    open: tuple[OpenItem, ...]
    invitation: Invitation
    checks: tuple[str, ...]


@dataclass(frozen=True)
class AppSettings:
    """How one application is started on a machine."""

    id: str
    command: tuple[str, ...]
    enabled: bool = True
    process_names: tuple[str, ...] = ()
    config_dir: Path | None = None
    user_data_dir: Path | None = None


@dataclass(frozen=True)
class Machine:
    id: str
    name: str
    source: str
    hostnames: tuple[str, ...] = ()
    apps: dict[str, AppSettings] = field(default_factory=dict)
    overrides: dict[str, dict] = field(default_factory=dict)
    is_builtin: bool = False

    def app(self, app_id: str) -> AppSettings:
        return self.apps.get(app_id) or _app_from(app_id, {})

    @staticmethod
    def builtin() -> Machine:
        return Machine(
            id="default",
            name="built-in defaults (no machine file)",
            source="(built-in)",
            is_builtin=True,
        )


def _default_app(app_id: str) -> dict:
    defaults: dict = {"command": [app_id], "enabled": True, "process_names": []}
    if app_id == "obs":
        # ".obs-wrapped" is the process name of the nixpkgs build.
        defaults["process_names"] = ["obs", ".obs-wrapped"]
        defaults["config_dir"] = str(paths.config_home() / "obs-studio")
    if app_id == "chromium":
        defaults["user_data_dir"] = str(
            paths.data_home() / "rpg-launcher" / "chromium-profile"
        )
    return defaults


def _app_from(app_id: str, configured: dict) -> AppSettings:
    merged = _default_app(app_id) | configured

    def as_path(key: str) -> Path | None:
        value = merged.get(key)
        return Path(os.path.expanduser(value)) if value else None

    return AppSettings(
        id=app_id,
        command=tuple(merged["command"]),
        enabled=merged["enabled"],
        process_names=tuple(merged["process_names"]),
        config_dir=as_path("config_dir"),
        user_data_dir=as_path("user_data_dir"),
    )


_MISSING = object()


class _Reader:
    """Reads one TOML table, recording wrong types and unknown keys."""

    def __init__(self, data: dict, source: str, path: str, problems: list[str]):
        self.data = data
        self.source = source
        self.path = path
        self.problems = problems
        self.known: set[str] = set()

    def _where(self, key: str | None = None) -> str:
        parts = [part for part in (self.path, key) if part]
        return f"{self.source}: {'.'.join(parts)}" if parts else self.source

    def _take(self, key: str, required: bool = False):
        self.known.add(key)
        if key not in self.data:
            if required:
                self.problems.append(f"{self._where()}: '{key}' is required")
            return _MISSING
        return self.data[key]

    def _bad(self, key: str, expected: str) -> None:
        self.problems.append(f"{self._where(key)}: must be {expected}")

    def text(self, key: str, default: str | None = None, required: bool = False):
        value = self._take(key, required)
        if value is _MISSING:
            return default
        if not isinstance(value, str) or not value.strip():
            self._bad(key, "non-empty text")
            return default
        return value

    def url(self, key: str) -> str:
        value = self.text(key, default="", required=True)
        if value and (value.startswith("-") or any(c.isspace() for c in value)):
            self._bad(key, "a URL without spaces")
        return value

    def flag(self, key: str, default: bool) -> bool:
        value = self._take(key)
        if value is _MISSING:
            return default
        if not isinstance(value, bool):
            self._bad(key, "true or false")
            return default
        return value

    def texts(self, key: str) -> tuple[str, ...]:
        value = self._take(key)
        if value is _MISSING:
            return ()
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            self._bad(key, 'a list of texts, like ["one", "two"]')
            return ()
        return tuple(value)

    def table(self, key: str) -> dict | None:
        value = self._take(key)
        if value is _MISSING:
            return None
        if not isinstance(value, dict):
            self._bad(key, f"a table, written as [{'.'.join(filter(None, (self.path, key)))}]")
            return None
        return value

    def tables(self, key: str) -> dict[str, dict]:
        """A table of named tables, such as [open.music] and [open.board]."""
        value = self.table(key)
        if value is None:
            return {}
        result = {}
        for name, entry in value.items():
            if isinstance(entry, dict):
                result[name] = entry
            else:
                where = ".".join(filter(None, (self.path, key)))
                self.problems.append(
                    f"{self.source}: {where}.{name}: must be a table, "
                    f"written as [{where}.<id>] with keys below it"
                )
        return result

    def child(self, key: str, data: dict) -> _Reader:
        path = ".".join(filter(None, (self.path, key)))
        return _Reader(data, self.source, path, self.problems)

    def done(self) -> None:
        for key in self.data:
            if key in self.known:
                continue
            close = difflib.get_close_matches(key, sorted(self.known), n=1)
            hint = f" (did you mean '{close[0]}'?)" if close else ""
            self.problems.append(f"{self._where(key)}: unknown key{hint}")


def _parse_game(game_id: str, data: dict, source: str) -> Game:
    problems: list[str] = []
    top = _Reader(data, source, "", problems)
    name = top.text("name", default=game_id)
    apps = top.texts("apps")
    checks = top.texts("checks")
    obs_data = top.table("obs")
    open_data = top.tables("open")
    invitation_data = top.table("invitation")
    top.done()

    obs = None
    if obs_data is not None:
        reader = top.child("obs", obs_data)
        obs = ObsSettings(
            enabled=reader.flag("enabled", True),
            profile=reader.text("profile"),
            collection=reader.text("collection"),
            scene=reader.text("scene"),
            record=reader.flag("record", False),
            checks=reader.texts("checks"),
        )
        reader.done()

    open_items = []
    for item_id, item_data in open_data.items():
        reader = top.child(f"open.{item_id}", item_data)
        open_items.append(
            OpenItem(
                id=item_id,
                label=reader.text("label", default=item_id),
                url=reader.url("url"),
                window=reader.flag("window", False),
                enabled=reader.flag("enabled", True),
                checks=reader.texts("checks"),
            )
        )
        reader.done()

    invitation = Invitation()
    if invitation_data is not None:
        reader = top.child("invitation", invitation_data)
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

        invitation = Invitation(
            intro=intro,
            note=note,
            player_link_label=player_link_label,
            shared=tuple(shared),
            players=tuple(players),
        )

    if problems:
        raise PresetError(problems)
    return Game(
        id=game_id,
        name=name,
        source=source,
        apps=apps,
        obs=obs,
        open=tuple(open_items),
        invitation=invitation,
        checks=checks,
    )


def _parse_machine(machine_id: str, data: dict, source: str) -> Machine:
    problems: list[str] = []
    top = _Reader(data, source, "", problems)
    name = top.text("name", default=machine_id)
    hostnames = top.texts("hostnames")
    apps_data = top.tables("apps")
    overrides = top.tables("overrides")
    top.done()

    apps = {}
    for app_id, app_data in apps_data.items():
        reader = top.child(f"apps.{app_id}", app_data)
        command = reader.texts("command")
        enabled = reader.flag("enabled", True)
        process_names = reader.texts("process_names")
        directories = {
            key: reader.text(key) for key in ("config_dir", "user_data_dir")
        }
        reader.done()

        # Only what the file sets replaces the built-in defaults for this app.
        configured: dict = {k: v for k, v in directories.items() if v}
        if command:
            configured["command"] = list(command)
        elif app_data.get("command") == []:
            problems.append(f"{source}: apps.{app_id}.command: must not be empty")
        if "enabled" in app_data:
            configured["enabled"] = enabled
        if "process_names" in app_data:
            configured["process_names"] = list(process_names)
        apps[app_id] = _app_from(app_id, configured)

    if problems:
        raise PresetError(problems)
    return Machine(
        id=machine_id,
        name=name,
        source=source,
        hostnames=hostnames,
        apps=apps,
        overrides=overrides,
    )


def _merge(base: dict, override: dict) -> dict:
    """Layer `override` on `base`: tables merge, every other value replaces."""
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _read_toml(path: Path, shown: str) -> dict:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError:
        raise PresetError(f"{shown}: file not found") from None
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise PresetError(f"{shown}: not valid TOML: {error}") from None
    except OSError as error:
        raise PresetError(f"{shown}: cannot be read: {error.strerror}") from None


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
        data = _read_toml(self.root / "games" / f"{game_id}.toml", shown)
        if machine and game_id in machine.overrides:
            data = _merge(data, machine.overrides[game_id])
            shown = f"{shown} with overrides from {machine.source}"
        return _parse_game(game_id, data, shown)

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
        data = _read_toml(self.root / "machines" / f"{machine_id}.toml", shown)
        return _parse_machine(machine_id, data, shown)

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
