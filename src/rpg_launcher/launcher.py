"""Start what a game asks for, and report what happened to each part.

"Started" and "opened" mean only that the command ran. Nothing here verifies
sound, screen sharing or recording; those stay manual checks.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from rpg_launcher import components
from rpg_launcher.components.base import LaunchContext, Outcome
from rpg_launcher.machine import Machine
from rpg_launcher.presets import Game


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
        self.context = LaunchContext(
            machine, dry_run=dry_run, log_dir=log_dir, settle=settle, running=running
        )

    def run(self) -> Iterator[Outcome]:
        """Go through the components this game uses, yielding outcomes as they happen."""
        for component in components.COMPONENTS:
            settings = self.game.parts.get(component.key)
            if settings is not None:
                yield from component.start(settings, self.context)


def manual_checks(game: Game, outcomes: list[Outcome]) -> list[str]:
    """Checks the GM still has to do, for the components that were attempted."""
    checks = []
    for outcome in outcomes:
        if outcome.status.attempted_ok:
            checks.extend(f"{outcome.label}: {check}" for check in outcome.checks)
    checks.extend(game.checks)
    return checks
