"""Start a game's applications and pages, and report what happened to each.

"Started" and "opened" mean only that the command ran. Nothing here verifies
sound, screen sharing or recording; those stay manual checks.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from rpg_launcher import obs as obs_config
from rpg_launcher.presets import AppSettings, Game, Machine


class Status(Enum):
    STARTED = "started"
    OPENED = "opened"
    RUNNING = "already running"
    SKIPPED = "skipped"
    FAILED = "FAILED"
    PLANNED = "planned"

    @property
    def attempted_ok(self) -> bool:
        return self in (Status.STARTED, Status.OPENED, Status.RUNNING, Status.PLANNED)


@dataclass
class Outcome:
    label: str
    status: Status
    detail: str = ""
    attention: list[str] = field(default_factory=list)
    checks: tuple[str, ...] = ()
    command: tuple[str, ...] | None = None


@dataclass
class _Spawned:
    status: Status
    detail: str = ""
    process: subprocess.Popen | None = None


def running_process_names() -> set[str]:
    names = set()
    for comm in Path("/proc").glob("[0-9]*/comm"):
        try:
            names.add(comm.read_text().strip())
        except OSError:
            pass  # the process ended while we were looking
    return names


def _log_tail(path: Path | None, lines: int = 3) -> str:
    if path is None:
        return ""
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return ""
    tail = [line.strip() for line in text.splitlines() if line.strip()][-lines:]
    return " | ".join(tail)


class Launcher:
    def __init__(
        self,
        game: Game,
        machine: Machine,
        *,
        dry_run: bool = False,
        log_dir: Path | None = None,
        settle: float = 2.0,
        running: set[str] | None = None,
    ):
        self.game = game
        self.machine = machine
        self.dry_run = dry_run
        self.log_dir = log_dir
        self.settle = settle
        self._running = running

    def run(self) -> Iterator[Outcome]:
        """Start everything, yielding one outcome per component as it happens."""
        if self.game.obs is not None:
            yield self._obs()
        for app_id in self.game.apps:
            yield self._app(app_id)
        yield from self._pages()

    def _is_running(self, app: AppSettings) -> bool:
        if not app.process_names:
            return False
        if self._running is None:
            self._running = running_process_names()
        return any(name in self._running for name in app.process_names)

    def _disabled(self, label: str, app: AppSettings) -> Outcome:
        return Outcome(
            label,
            Status.SKIPPED,
            f"{app.id} is disabled on this machine ({self.machine.source})",
        )

    def _obs(self) -> Outcome:
        settings = self.game.obs
        app = self.machine.app("obs")
        if not settings.enabled:
            return Outcome("OBS", Status.SKIPPED, "disabled for this game")
        if not app.enabled:
            return self._disabled("OBS", app)

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

        references = obs_config.check_references(app.config_dir, settings)
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

        if self._is_running(app):
            if settings.profile or settings.collection or settings.scene or settings.record:
                attention.insert(
                    0,
                    "OBS was already running, so the launcher left it alone. Its "
                    "profile, scene collection, scene and recording state are as "
                    "you left them: set them by hand.",
                )
            return Outcome(
                "OBS", Status.RUNNING, "left untouched", attention, checks, tuple(command)
            )

        spawned = self._spawn("obs", app.id, command)
        return Outcome(
            "OBS", spawned.status, spawned.detail, attention, checks, tuple(command)
        )

    def _app(self, app_id: str) -> Outcome:
        app = self.machine.app(app_id)
        if not app.enabled:
            return self._disabled(app_id, app)
        if self._is_running(app):
            return Outcome(app_id, Status.RUNNING, "left untouched", command=app.command)
        spawned = self._spawn(app_id, app.id, list(app.command))
        return Outcome(app_id, spawned.status, spawned.detail, command=app.command)

    def _pages(self) -> Iterator[Outcome]:
        enabled = []
        for item in self.game.open:
            if item.enabled:
                enabled.append(item)
            else:
                yield Outcome(item.label, Status.SKIPPED, "disabled for this game")
        if not enabled:
            return

        app = self.machine.app("chromium")
        if not app.enabled:
            for item in enabled:
                yield self._disabled(item.label, app)
            return

        base = [
            *app.command,
            f"--user-data-dir={app.user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        tabs = [item for item in enabled if not item.window]
        windows = [[item] for item in enabled if item.window]
        groups = ([tabs] if tabs else []) + windows

        for index, group in enumerate(groups):
            command = [*base, "--new-window", *(item.url for item in group)]
            spawned = self._spawn(f"chromium-{index + 1}", app.id, command)
            if index == 0 and len(groups) > 1 and spawned.status is Status.STARTED:
                self._wait_for_browser(app.user_data_dir, spawned.process)
            status = Status.OPENED if spawned.status is Status.STARTED else spawned.status
            for position, item in enumerate(group):
                where = "own window" if item.window else "tab in the game window"
                yield Outcome(
                    item.label,
                    status,
                    spawned.detail or where,
                    checks=item.checks,
                    # One command opens the whole group; show it once.
                    command=tuple(command) if position == 0 else None,
                )

    def _spawn(self, log_name: str, app_id: str, command: list[str]) -> _Spawned:
        if self.dry_run:
            return _Spawned(Status.PLANNED)

        log_path = None
        output = subprocess.DEVNULL
        if self.log_dir is not None:
            try:
                self.log_dir.mkdir(parents=True, exist_ok=True)
                log_path = self.log_dir / f"{log_name}.log"
                output = log_path.open("wb")
            except OSError:
                log_path = None

        try:
            # A new session keeps the application alive after the launcher exits.
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except FileNotFoundError:
            return _Spawned(
                Status.FAILED,
                f"'{command[0]}' was not found on this machine. Install it, or set "
                f"the right command under [apps.{app_id}] in the machine preset.",
            )
        except OSError as error:
            return _Spawned(
                Status.FAILED, f"could not run '{command[0]}': {error.strerror}"
            )
        finally:
            if output is not subprocess.DEVNULL:
                output.close()

        try:
            code = process.wait(timeout=self.settle)
        except subprocess.TimeoutExpired:
            return _Spawned(Status.STARTED, process=process)
        if code == 0:
            return _Spawned(
                Status.STARTED,
                "the command finished right away without an error (usually an "
                "instance that was already running took over)",
            )
        detail = f"exited right away with code {code}."
        tail = _log_tail(log_path)
        if tail:
            detail += f" Last output: {tail}"
        if log_path:
            detail += f" Full log: {log_path}"
        return _Spawned(Status.FAILED, detail)

    def _wait_for_browser(
        self, user_data_dir: Path | None, process: subprocess.Popen | None
    ) -> None:
        """Wait until the new browser can accept further windows.

        Chromium creates SingletonSocket in its profile once it is able to take
        over later command lines. Asking for more windows before that risks a
        second browser fighting for the same profile.
        """
        if user_data_dir is None:
            return
        socket_path = user_data_dir / "SingletonSocket"
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if socket_path.is_symlink() or socket_path.exists():
                time.sleep(0.5)
                return
            if process is not None and process.poll() is not None:
                return
            time.sleep(0.2)


def manual_checks(game: Game, outcomes: list[Outcome]) -> list[str]:
    """Checks the GM still has to do, for the components that were attempted."""
    checks = []
    for outcome in outcomes:
        if outcome.status.attempted_ok:
            checks.extend(f"{outcome.label}: {check}" for check in outcome.checks)
    checks.extend(game.checks)
    return checks
