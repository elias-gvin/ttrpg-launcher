"""A component added from outside works without changes to the launcher."""

import unittest
from unittest import mock

from helpers import MINIMAL_GAME, PresetCase
from test_cli import run

from rpg_launcher import components
from rpg_launcher.components.base import WARN, Component, Finding, Outcome, Status
from rpg_launcher.launcher import Launcher, manual_checks
from rpg_launcher.schema import PresetError


class Bell(Component):
    """A made-up component: starts a bell program."""

    key = "bell"
    app_options = {"bell": ("tone",)}

    def parse(self, top):
        data = top.table("bell")
        if data is None:
            return None
        reader = top.child("bell", data)
        label = reader.text("label", default="Bell")
        reader.done()
        return label

    def start(self, settings, context):
        app = context.machine.app("bell")
        command = [*app.command, app.options.get("tone", "low")]
        spawned = context.spawn("bell", app, command)
        yield Outcome(
            settings, spawned.status, spawned.detail, checks=("Listen for it",), command=tuple(command)
        )

    def needed_apps(self, settings):
        return ["bell"]

    def diagnose(self, settings, machine):
        return [Finding(WARN, "bells are loud")]


GAME = MINIMAL_GAME + '\n[bell]\nlabel = "Session bell"\n\n[obs]\n'


class AddedComponent(PresetCase):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(
            components, "COMPONENTS", (*components.COMPONENTS, Bell())
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_its_table_is_read_from_the_game_preset(self):
        self.write_game("game", GAME)
        self.assertEqual(self.store.load_game("game").parts["bell"], "Session bell")

    def test_mistakes_in_its_table_are_reported_like_any_other(self):
        self.write_game("game", MINIMAL_GAME + "\n[bell]\nlabl = 'x'\n")
        with self.assertRaises(PresetError) as caught:
            self.store.load_game("game")
        self.assertEqual(
            caught.exception.problems,
            ["games/game.toml: bell.labl: unknown key (did you mean 'label'?)"],
        )

    def test_it_declares_its_own_machine_settings(self):
        self.write_machine("m", '[apps.bell]\ncommand = ["ring"]\ntone = "high"\n')
        self.assertEqual(self.store.load_machine("m").app("bell").options, {"tone": "high"})

        self.write_machine("m", '[apps.obs]\ntone = "high"\n')
        with self.assertRaises(PresetError) as caught:
            self.store.load_machine("m")
        self.assertIn("machines/m.toml: apps.obs.tone: unknown key", caught.exception.problems[0])

    def test_it_is_launched_after_the_built_in_components(self):
        self.write_game("game", GAME)
        self.write_machine("m", '[apps.bell]\ncommand = ["ring"]\ntone = "high"\n')
        machine = self.store.load_machine("m")
        game = self.store.load_game("game", machine)
        outcomes = list(Launcher(game, machine, dry_run=True, running=set()).run())
        self.assertEqual([outcome.label for outcome in outcomes], ["OBS", "Session bell"])
        self.assertIs(outcomes[1].status, Status.PLANNED)
        self.assertEqual(outcomes[1].command, ("ring", "high"))
        self.assertIn("Session bell: Listen for it", manual_checks(game, outcomes))

    def test_doctor_runs_its_checks_and_looks_for_its_application(self):
        self.write_game("game", GAME)
        self.write_machine("m", '[apps.bell]\ncommand = ["no-such-bell-rpg"]\n[apps.obs]\ncommand = ["sh"]\n')
        code, out, _ = run("--presets", str(self.root), "--machine", "m", "doctor")
        self.assertEqual(code, 1)
        self.assertIn("warn  Minimal: bells are loud", out)
        self.assertIn("bell: 'no-such-bell-rpg' was not found", out)


class WithoutIt(PresetCase):
    def test_an_unregistered_table_is_an_unknown_key(self):
        self.write_game("game", GAME)
        with self.assertRaises(PresetError) as caught:
            self.store.load_game("game")
        self.assertEqual(caught.exception.problems, ["games/game.toml: bell: unknown key"])


if __name__ == "__main__":
    unittest.main()
