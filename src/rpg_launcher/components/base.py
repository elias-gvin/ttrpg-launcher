"""What every component shares.

A component is one kind of thing a game can start: OBS, plain applications,
browser pages. Each lives in its own module in this package, subclasses
Component, and is listed in COMPONENTS in __init__.py. Nothing else in the
launcher needs to know it exists.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from rpg_launcher.machine import AppSettings, Machine
from rpg_launcher.schema import Reader


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
    """What happened to one thing the GM asked for."""

    label: str
    status: Status
    detail: str = ""
    attention: list[str] = field(default_factory=list)  # needs the GM's eye now
    checks: tuple[str, ...] = ()  # manual checks, listed if this was attempted
    command: tuple[str, ...] | None = None  # shown in a dry run


@dataclass
class Spawned:
    status: Status
    detail: str = ""
    process: subprocess.Popen | None = None


OK, WARN, FAIL = "ok", "warn", "fail"


@dataclass
class Finding:
    """One line of `doctor` output."""

    level: str
    text: str


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


class LaunchContext:
    """What a component gets to work with while starting things."""

    def __init__(
        self,
        machine: Machine,
        *,
        dry_run: bool = False,
        log_dir: Path | None = None,
        settle: float = 2.0,
        running: set[str] | None = None,
    ):
        self.machine = machine
        self.dry_run = dry_run
        self.log_dir = log_dir
        self.settle = settle
        self._running = running

    def is_running(self, app: AppSettings, usual_names: Iterable[str] = ()) -> bool:
        """Whether the application already runs, judged by its process names."""
        names = app.process_names or tuple(usual_names)
        if not names:
            return False
        if self._running is None:
            self._running = running_process_names()
        return any(name in self._running for name in names)

    def disabled(self, label: str, app: AppSettings) -> Outcome:
        return Outcome(
            label,
            Status.SKIPPED,
            f"{app.id} is disabled on this machine ({self.machine.source})",
        )

    def spawn(self, log_name: str, app: AppSettings, command: list[str]) -> Spawned:
        """Start a command and report whether it stayed up.

        In a dry run nothing is started and the status is PLANNED.
        """
        if self.dry_run:
            return Spawned(Status.PLANNED)

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
            return Spawned(
                Status.FAILED,
                f"'{command[0]}' was not found on this machine. Install it, or set "
                f"the right command under [apps.{app.id}] in the machine preset.",
            )
        except OSError as error:
            return Spawned(Status.FAILED, f"could not run '{command[0]}': {error.strerror}")
        finally:
            if output is not subprocess.DEVNULL:
                output.close()

        try:
            code = process.wait(timeout=self.settle)
        except subprocess.TimeoutExpired:
            return Spawned(Status.STARTED, process=process)
        if code == 0:
            return Spawned(
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
        return Spawned(Status.FAILED, detail)


class Component:
    """One kind of thing a game can start.

    `key` is the top-level key in a game preset that this component owns.
    Whatever parse() returns is kept as the game's settings for this component
    and handed back to the other methods.
    """

    key: str

    # Extra keys this component understands under [apps.<id>] in a machine
    # preset, by application id. Read them with AppSettings.options or .path().
    app_options: dict[str, tuple[str, ...]] = {}

    def parse(self, top: Reader) -> Any | None:
        """Read this component's part of a game preset.

        `top` reads the top level of the game file. Return the settings, or
        None when the game does not use this component.
        """
        raise NotImplementedError

    def start(self, settings: Any, context: LaunchContext) -> Iterator[Outcome]:
        """Start what the game asks for, yielding an outcome for each thing.

        Start processes through context.spawn(): it handles dry runs, logs and
        failures. Anything else with side effects must check context.dry_run.
        """
        raise NotImplementedError

    def needed_apps(self, settings: Any) -> list[str]:
        """Ids of the applications this needs, for `doctor` to look for."""
        return []

    def diagnose(self, settings: Any, machine: Machine) -> list[Finding]:
        """Checks for `doctor` that need no running application."""
        return []
