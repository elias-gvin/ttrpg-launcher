import unittest
import warnings

from helpers import EXAMPLES, PresetCase

from rpg_launcher import invitation
from rpg_launcher.launcher import Launcher, Status, manual_checks
from rpg_launcher.presets import PresetStore

GAME = """
apps = ["helper"]

[obs]
profile = "RPG"
collection = "Games"
scene = "Samosbor"
checks = ["Browser source unmuted"]

[open.director]
label = "Director"
url = "https://vdo.ninja/?director=ROOM&password=SECRET"
checks = ["Check the director view"]

[open.music]
label = "Music"
url = "https://www.youtube.com/playlist?list=PL"

[open.board]
label = "Board"
url = "https://app.diagrams.net/#Gfile"
window = true
"""


class Planning(PresetCase):
    """Dry runs: which commands would run, without starting anything."""

    def plan(self, game_text=GAME, machine_text="", running=frozenset()):
        self.write_game("game", game_text)
        config = self.root / "obs-studio"
        if not config.exists():
            config = self.write_obs_config()
        self.write_machine("m", f'[apps.obs]\nconfig_dir = "{config}"\n{machine_text}')
        machine = self.store.load_machine("m")
        game = self.store.load_game("game", machine)
        launcher = Launcher(game, machine, dry_run=True, running=set(running))
        return game, {outcome.label: outcome for outcome in launcher.run()}

    def test_obs_gets_its_own_options_for_the_names_in_the_preset(self):
        _, outcomes = self.plan()
        self.assertEqual(
            outcomes["OBS"].command,
            ("obs", "--profile", "RPG", "--collection", "Games", "--scene", "Samosbor"),
        )
        self.assertEqual(outcomes["OBS"].attention, [])

    def test_recording_starts_only_when_the_preset_asks(self):
        _, outcomes = self.plan()
        self.assertNotIn("--startrecording", outcomes["OBS"].command)
        _, outcomes = self.plan(GAME.replace("[obs]", "[obs]\nrecord = true"))
        self.assertIn("--startrecording", outcomes["OBS"].command)

    def test_tabs_share_one_window_and_marked_pages_get_their_own(self):
        _, outcomes = self.plan()
        tabs = outcomes["Director"].command
        self.assertEqual(
            tabs[-3:],
            (
                "--new-window",
                "https://vdo.ninja/?director=ROOM&password=SECRET",
                "https://www.youtube.com/playlist?list=PL",
            ),
        )
        self.assertEqual(
            outcomes["Board"].command[-2:], ("--new-window", "https://app.diagrams.net/#Gfile")
        )

    def test_pages_open_in_the_dedicated_profile(self):
        _, outcomes = self.plan(machine_text='[apps.chromium]\nuser_data_dir = "/tmp/rpg-profile"\n')
        self.assertIn("--user-data-dir=/tmp/rpg-profile", outcomes["Director"].command)

    def test_running_obs_is_left_alone_and_flagged(self):
        _, outcomes = self.plan(running={"obs"})
        self.assertIs(outcomes["OBS"].status, Status.RUNNING)
        self.assertIn("already running", outcomes["OBS"].attention[0])

    def test_missing_obs_scene_is_flagged_but_does_not_stop_the_launch(self):
        _, outcomes = self.plan(GAME.replace('scene = "Samosbor"', 'scene = "Typo"'))
        self.assertIs(outcomes["OBS"].status, Status.PLANNED)
        self.assertIn("no scene called 'Typo'", outcomes["OBS"].attention[0])
        self.assertIn("'Samosbor', 'Frostpunk'", outcomes["OBS"].attention[0])

    def test_app_disabled_on_the_machine_is_skipped_with_a_reason(self):
        _, outcomes = self.plan(machine_text="enabled = false\n")
        self.assertIs(outcomes["OBS"].status, Status.SKIPPED)
        self.assertIn("machines/m.toml", outcomes["OBS"].detail)
        self.assertIs(outcomes["Director"].status, Status.PLANNED)

    def test_manual_checks_include_the_recording_reminder(self):
        game, outcomes = self.plan()
        checks = manual_checks(game, list(outcomes.values()))
        self.assertIn("OBS: Browser source unmuted", checks)
        self.assertIn("Director: Check the director view", checks)
        self.assertTrue(any("Recording is not started" in check for check in checks))


class Starting(PresetCase):
    """Real processes, using small stand-in commands for the applications."""

    def setUp(self):
        super().setUp()
        # The launcher leaves applications running on purpose; Python warns
        # about that when it forgets a process that has not ended.
        self.enterContext(warnings.catch_warnings())
        warnings.simplefilter("ignore", ResourceWarning)

    def launch(self, apps: dict[str, str], game_text: str):
        self.write_game("game", game_text)
        self.write_machine(
            "m",
            "\n".join(f"[apps.{app_id}]\ncommand = {command}" for app_id, command in apps.items()),
        )
        machine = self.store.load_machine("m")
        game = self.store.load_game("game", machine)
        launcher = Launcher(
            game, machine, log_dir=self.root / "logs", settle=0.3, running=set()
        )
        outcomes = list(launcher.run())
        return game, {outcome.label: outcome for outcome in outcomes}

    def test_each_component_reports_its_own_outcome(self):
        game, outcomes = self.launch(
            {
                "stays": '["sleep", "2"]',
                "handsover": '["true"]',
                "breaks": """["sh", "-c", "echo 'no display' >&2; exit 3"]""",
                "missing": '["no-such-program-rpg"]',
                "chromium": '["true"]',
            },
            'apps = ["stays", "handsover", "breaks", "missing"]\n'
            '[open.page]\nlabel = "Page"\nurl = "https://example.org"\nchecks = ["Look at it"]\n',
        )
        self.assertIs(outcomes["stays"].status, Status.STARTED)
        self.assertEqual(outcomes["stays"].detail, "")
        self.assertIs(outcomes["handsover"].status, Status.STARTED)
        self.assertIn("already running", outcomes["handsover"].detail)

        self.assertIs(outcomes["breaks"].status, Status.FAILED)
        self.assertIn("code 3", outcomes["breaks"].detail)
        self.assertIn("no display", outcomes["breaks"].detail)
        self.assertIn(str(self.root / "logs" / "breaks.log"), outcomes["breaks"].detail)

        self.assertIs(outcomes["missing"].status, Status.FAILED)
        self.assertIn("'no-such-program-rpg' was not found", outcomes["missing"].detail)
        self.assertIn("[apps.missing]", outcomes["missing"].detail)

        # Failures above did not stop the page from opening.
        self.assertIs(outcomes["Page"].status, Status.OPENED)
        self.assertEqual(manual_checks(game, list(outcomes.values())), ["Page: Look at it"])

    def test_checks_of_a_failed_component_are_not_listed(self):
        game, outcomes = self.launch(
            {"chromium": '["no-such-browser-rpg"]'},
            '[open.page]\nurl = "https://example.org"\nchecks = ["Look at it"]\n',
        )
        self.assertIs(outcomes["page"].status, Status.FAILED)
        self.assertEqual(manual_checks(game, list(outcomes.values())), [])


class Privacy(unittest.TestCase):
    def test_gm_pages_never_reach_a_player_message(self):
        store = PresetStore(EXAMPLES)
        for game_id in store.game_ids():
            game = store.load_game(game_id)
            messages = [invitation.message_for_everyone(game.invitation), invitation.overview(game)]
            messages += [
                invitation.message_for_player(game.invitation, player)
                for player in game.invitation.players
            ]
            for item in game.open:
                for message in messages:
                    self.assertNotIn(item.url, message)


if __name__ == "__main__":
    unittest.main()
