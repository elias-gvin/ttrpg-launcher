"""Plain applications: `apps = ["discord"]` in a game preset.

An application is started by its id unless the machine preset gives another
command under [apps.<id>].
"""

from __future__ import annotations

from collections.abc import Iterator

from rpg_launcher.components.base import Component, LaunchContext, Outcome, Status
from rpg_launcher.schema import Reader


class Apps(Component):
    key = "apps"

    def parse(self, top: Reader) -> tuple[str, ...] | None:
        return top.texts("apps") or None

    def start(self, settings: tuple[str, ...], context: LaunchContext) -> Iterator[Outcome]:
        for app_id in settings:
            app = context.machine.app(app_id)
            if not app.enabled:
                yield context.disabled(app_id, app)
            elif context.is_running(app):
                yield Outcome(app_id, Status.RUNNING, "left untouched", command=app.command)
            else:
                spawned = context.spawn(app_id, app, list(app.command))
                yield Outcome(app_id, spawned.status, spawned.detail, command=app.command)

    def needed_apps(self, settings: tuple[str, ...]) -> list[str]:
        return list(settings)
