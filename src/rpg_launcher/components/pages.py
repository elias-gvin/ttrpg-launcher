"""Browser pages for the GM: the [open.<id>] tables in a game preset.

Pages open in a Chromium profile of their own, apart from everyday browsing.
URLs are passed on exactly as written.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from rpg_launcher import paths
from rpg_launcher.components.base import (
    FAIL,
    Component,
    Finding,
    LaunchContext,
    Outcome,
    Status,
)
from rpg_launcher.machine import Machine
from rpg_launcher.schema import Reader


@dataclass(frozen=True)
class Page:
    id: str
    label: str
    url: str
    window: bool
    enabled: bool
    checks: tuple[str, ...]


def _wait_for_browser(profile: Path, process: subprocess.Popen | None) -> None:
    """Wait until the new browser can accept further windows.

    Chromium creates SingletonSocket in its profile once it is able to take
    over later command lines. Asking for more windows before that risks a
    second browser fighting for the same profile.
    """
    socket_path = profile / "SingletonSocket"
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if socket_path.is_symlink() or socket_path.exists():
            time.sleep(0.5)
            return
        if process is not None and process.poll() is not None:
            return
        time.sleep(0.2)


class Pages(Component):
    key = "open"
    app_options = {"chromium": ("user_data_dir",)}

    def parse(self, top: Reader) -> tuple[Page, ...] | None:
        pages = []
        for page_id, data in top.tables("open").items():
            reader = top.child(f"open.{page_id}", data)
            pages.append(
                Page(
                    id=page_id,
                    label=reader.text("label", default=page_id),
                    url=reader.url("url"),
                    window=reader.flag("window", False),
                    enabled=reader.flag("enabled", True),
                    checks=reader.texts("checks"),
                )
            )
            reader.done()
        return tuple(pages) or None

    def start(self, settings: tuple[Page, ...], context: LaunchContext) -> Iterator[Outcome]:
        enabled = []
        for page in settings:
            if page.enabled:
                enabled.append(page)
            else:
                yield Outcome(page.label, Status.SKIPPED, "disabled for this game")
        if not enabled:
            return

        app = context.machine.app("chromium")
        if not app.enabled:
            for page in enabled:
                yield context.disabled(page.label, app)
            return

        profile = app.path(
            "user_data_dir", paths.data_home() / "rpg-launcher" / "chromium-profile"
        )
        base = [
            *app.command,
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        tabs = [page for page in enabled if not page.window]
        windows = [[page] for page in enabled if page.window]
        groups = ([tabs] if tabs else []) + windows

        for index, group in enumerate(groups):
            command = [*base, "--new-window", *(page.url for page in group)]
            spawned = context.spawn(f"chromium-{index + 1}", app, command)
            if index == 0 and len(groups) > 1 and spawned.status is Status.STARTED:
                _wait_for_browser(profile, spawned.process)
            status = Status.OPENED if spawned.status is Status.STARTED else spawned.status
            for position, page in enumerate(group):
                where = "own window" if page.window else "tab in the game window"
                yield Outcome(
                    page.label,
                    status,
                    spawned.detail or where,
                    checks=page.checks,
                    # One command opens the whole group; show it once.
                    command=tuple(command) if position == 0 else None,
                )

    def needed_apps(self, settings: tuple[Page, ...]) -> list[str]:
        return ["chromium"] if any(page.enabled for page in settings) else []

    def diagnose(self, settings: tuple[Page, ...], machine: Machine) -> list[Finding]:
        findings = []
        for page in settings:
            if page.enabled and page.url.startswith("file://"):
                path = Path(unquote(page.url.removeprefix("file://")))
                if not path.exists():
                    findings.append(Finding(FAIL, f"{page.label}: {path} does not exist."))
        return findings
