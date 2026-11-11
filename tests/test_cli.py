import contextlib
import io
import os
import unittest
from unittest import mock

from helpers import EXAMPLES, MINIMAL_GAME, PresetCase

from rpg_launcher.cli import main


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CleanEnvironment(PresetCase):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in ("RPG_LAUNCHER_MACHINE", "RPG_LAUNCHER_PRESETS"):
            os.environ.pop(name, None)


class Invite(CleanEnvironment):
    def examples(self, *argv):
        return run("--presets", str(EXAMPLES), "--machine", "desktop", *argv)

    def test_player_message_has_their_link_then_shared_links_then_the_note(self):
        code, out, _ = self.examples("invite", "samosbor", "--player", "2")
        self.assertEqual(code, 0)
        blocks = out.strip().split("\n\n")
        self.assertEqual(blocks[0], "Samosbor 2 is about to start. Your links:")
        links = blocks[1].splitlines()
        self.assertTrue(links[0].startswith("Join voice and video: https://vdo.ninja/"))
        self.assertTrue(links[0].endswith("&push=02"))
        self.assertTrue(links[1].startswith("Dice channel: https://discord.com/"))
        self.assertEqual(blocks[2], "Please use headphones.")

    def test_player_can_be_named_by_id_name_or_number(self):
        outputs = {
            self.examples("invite", "samosbor", "--player", who)[1]
            for who in ("1", "player1", "Player 1")
        }
        self.assertEqual(len(outputs), 1)

    def test_game_without_per_player_links_gets_one_message(self):
        code, out, _ = self.examples("invite", "frostpunk")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("Join game: https://vdo.ninja/?room=EXAMPLE_FROST"))

    def test_options_are_accepted_after_the_command_too(self):
        code, out, _ = run("invite", "frostpunk", "--presets", str(EXAMPLES), "--machine", "laptop")
        self.assertEqual(code, 0)
        self.assertIn("Join game:", out)

    def test_unknown_player_lists_the_players(self):
        code, _, err = self.examples("invite", "samosbor", "--player", "nobody")
        self.assertEqual(code, 2)
        self.assertIn("player1 (Player 1)", err)

    def test_game_without_links_is_a_configuration_error_not_a_guess(self):
        self.write_game("bare", 'name = "Bare"\n')
        code, out, err = run("--presets", str(self.root), "invite", "bare")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("no player links", err)


class DryRun(CleanEnvironment):
    def test_dry_run_shows_selection_commands_checks_and_invitation(self):
        code, out, _ = run(
            "--presets", str(EXAMPLES), "launch", "samosbor", "--machine", "laptop", "--dry-run"
        )
        self.assertEqual(code, 0)
        self.assertIn("Game:    Samosbor 2", out)
        self.assertIn("Machine: Laptop", out)
        self.assertIn("obs is disabled on this machine", out)
        self.assertIn("$ discord", out)
        self.assertIn("Manual checks (not verified by the launcher):", out)
        self.assertIn("PLAYER INVITATION: Samosbor 2", out)


class Doctor(CleanEnvironment):
    def test_valid_presets_pass_and_missing_program_fails(self):
        self.write_game("minimal", MINIMAL_GAME + '\n[open.page]\nurl = "https://example.org"\n')
        self.write_machine("ok", '[apps.chromium]\ncommand = ["sh"]\n')
        self.write_machine("bad", '[apps.chromium]\ncommand = ["no-such-browser-rpg"]\n')

        code, out, _ = run("--presets", str(self.root), "--machine", "ok", "doctor")
        self.assertEqual(code, 0)
        self.assertIn("chromium: available as 'sh'", out)

        code, out, _ = run("--presets", str(self.root), "--machine", "bad", "doctor")
        self.assertEqual(code, 1)
        self.assertIn("'no-such-browser-rpg' was not found", out)
        self.assertIn("used by Minimal", out)

    def test_every_broken_file_is_reported(self):
        self.write_game("good", MINIMAL_GAME)
        self.write_game("broken", "[open.page]\n")
        self.write_machine("m", "[overrides.ghost]\nname = 'x'\n")
        code, out, _ = run("--presets", str(self.root), "--machine", "m", "doctor")
        self.assertEqual(code, 1)
        self.assertIn("games/broken.toml: open.page: 'url' is required", out)
        self.assertIn("Minimal: preset is valid", out)
        self.assertIn("machines/m.toml: overrides.ghost matches no game", out)

    def test_missing_obs_scene_fails_the_check(self):
        config = self.write_obs_config()
        self.write_game("game", MINIMAL_GAME + '\n[obs]\nscene = "Typo"\n')
        self.write_machine("m", f'[apps.obs]\ncommand = ["sh"]\nconfig_dir = "{config}"\n')
        code, out, _ = run("--presets", str(self.root), "--machine", "m", "doctor")
        self.assertEqual(code, 1)
        self.assertIn("has no scene called 'Typo'", out)

    def test_game_without_player_links_fails_the_check(self):
        self.write_game("bare", 'name = "Bare"\n')
        code, out, _ = run("--presets", str(self.root), "doctor")
        self.assertEqual(code, 1)
        self.assertIn("Bare: no player links", out)


if __name__ == "__main__":
    unittest.main()
