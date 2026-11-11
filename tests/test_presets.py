import os
import unittest
from unittest import mock

from helpers import EXAMPLES, MINIMAL_GAME, PresetCase

from rpg_launcher.presets import PresetError, PresetStore, find_presets_dir


class ExamplePresets(unittest.TestCase):
    def setUp(self):
        self.store = PresetStore(EXAMPLES)

    def test_every_example_game_loads_on_every_example_machine(self):
        for machine_id in self.store.machine_ids():
            machine = self.store.load_machine(machine_id)
            for game_id in self.store.game_ids():
                self.store.load_game(game_id, machine)

    def test_one_game_file_serves_two_machines(self):
        desktop = self.store.load_game("samosbor", self.store.load_machine("desktop"))
        laptop = self.store.load_game("samosbor", self.store.load_machine("laptop"))
        on_desktop, on_laptop = (
            next(page for page in game.parts["open"] if page.id == "board")
            for game in (desktop, laptop)
        )
        self.assertTrue(on_desktop.window)
        self.assertFalse(on_laptop.window)
        self.assertEqual(on_desktop.url, on_laptop.url)

    def test_machine_does_not_change_the_invitation(self):
        desktop = self.store.load_game("samosbor", self.store.load_machine("desktop"))
        laptop = self.store.load_game("samosbor", self.store.load_machine("laptop"))
        self.assertEqual(desktop.invitation, laptop.invitation)

    def test_flatpak_command_comes_from_the_machine(self):
        desktop = self.store.load_machine("desktop")
        self.assertEqual(desktop.app("obs").command[:2], ("flatpak", "run"))
        self.assertEqual(self.store.load_machine("laptop").app("discord").command, ("discord",))


class GameValidation(PresetCase):
    def problems(self, text):
        self.write_game("game", text)
        with self.assertRaises(PresetError) as caught:
            self.store.load_game("game")
        return caught.exception.problems

    def test_url_is_kept_exactly_as_written(self):
        url = "https://vdo.ninja/?room=R&hash=1&l=%D0%A1%D1%82&sl&q&vd=0&push=01#frag"
        self.write_game("game", f'[open.page]\nurl = "{url}"\n')
        self.assertEqual(self.store.load_game("game").parts["open"][0].url, url)

    def test_misspelled_key_is_named_with_a_suggestion(self):
        problems = self.problems('[open.music]\nulr = "https://example.org"\n')
        self.assertIn("games/game.toml: open.music.ulr: unknown key (did you mean 'url'?)", problems)
        self.assertIn("games/game.toml: open.music: 'url' is required", problems)

    def test_wrong_type_is_reported_with_its_location(self):
        problems = self.problems('[obs]\nrecord = "yes"\n')
        self.assertEqual(problems, ["games/game.toml: obs.record: must be true or false"])

    def test_url_with_a_space_is_rejected(self):
        problems = self.problems('[open.page]\nurl = "https://example.org/a b"\n')
        self.assertEqual(problems, ["games/game.toml: open.page.url: must be a URL without spaces"])

    def test_broken_toml_names_the_file(self):
        problems = self.problems('name = "unterminated\n')
        self.assertTrue(problems[0].startswith("games/game.toml: not valid TOML"))

    def test_all_problems_are_reported_at_once(self):
        problems = self.problems('nmae = "x"\n[open.a]\nwindow = 1\n')
        self.assertEqual(len(problems), 3)

    def test_recording_is_off_unless_asked_for(self):
        self.write_game("game", "[obs]\n")
        self.assertFalse(self.store.load_game("game").parts["obs"].record)


class MachineResolution(PresetCase):
    def setUp(self):
        super().setUp()
        self.write_game("minimal", MINIMAL_GAME)
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("RPG_LAUNCHER_MACHINE", None)

    def test_without_machine_files_builtin_defaults_are_used(self):
        machine = self.store.resolve_machine(hostname="anything")
        self.assertTrue(machine.is_builtin)
        self.assertEqual(machine.app("obs").command, ("obs",))

    def test_hostname_list_and_file_name_both_match(self):
        self.write_machine("desktop", 'hostnames = ["tower"]\n')
        self.write_machine("thinkpad", "")
        self.assertEqual(self.store.resolve_machine(hostname="tower").id, "desktop")
        self.assertEqual(self.store.resolve_machine(hostname="thinkpad").id, "thinkpad")

    def test_explicit_choice_wins_over_hostname(self):
        self.write_machine("desktop", 'hostnames = ["tower"]\n')
        self.write_machine("laptop", "")
        self.assertEqual(self.store.resolve_machine("laptop", hostname="tower").id, "laptop")

    def test_unmatched_hostname_is_an_error_not_a_guess(self):
        self.write_machine("desktop", 'hostnames = ["tower"]\n')
        with self.assertRaises(PresetError) as caught:
            self.store.resolve_machine(hostname="stranger")
        self.assertIn("hostname 'stranger'", caught.exception.problems[0])
        self.assertIn("--machine", caught.exception.problems[0])

    def test_broken_machine_file_does_not_block_the_matching_one(self):
        self.write_machine("desktop", 'hostnames = ["tower"]\n')
        self.write_machine("laptop", "hostnames = 5\n")
        self.assertEqual(self.store.resolve_machine(hostname="tower").id, "desktop")

    def test_machine_settings_replace_only_what_they_name(self):
        self.write_machine("m", '[apps.obs]\ncommand = ["flatpak", "run", "x"]\n')
        machine = self.store.load_machine("m")
        self.assertEqual(machine.app("obs").command, ("flatpak", "run", "x"))
        self.assertTrue(machine.app("obs").enabled)
        self.assertEqual(machine.app("chromium").command, ("chromium",))

    def test_override_for_one_game_leaves_the_rest_inherited(self):
        self.write_game("game", '[open.a]\nurl = "https://a.example"\n[open.b]\nurl = "https://b.example"\n')
        self.write_machine("m", "[overrides.game.open.b]\nenabled = false\n")
        game = self.store.load_game("game", self.store.load_machine("m"))
        pages = game.parts["open"]
        self.assertEqual([(page.id, page.enabled) for page in pages], [("a", True), ("b", False)])
        self.assertEqual(pages[1].url, "https://b.example")


class GameLookup(PresetCase):
    def test_game_is_found_by_file_name_or_display_name(self):
        self.write_game("samosbor", 'name = "Samosbor 2"\n')
        self.assertEqual(self.store.find_game("samosbor"), "samosbor")
        self.assertEqual(self.store.find_game("samosbor 2"), "samosbor")

    def test_unknown_game_lists_what_exists(self):
        self.write_game("samosbor", "")
        with self.assertRaises(PresetError) as caught:
            self.store.find_game("samosbr")
        self.assertIn("Did you mean 'samosbor'?", caught.exception.problems[0])

    def test_missing_presets_directory_explains_what_to_do(self):
        with self.assertRaises(PresetError) as caught:
            find_presets_dir(str(self.root / "nowhere"))
        self.assertIn("--presets", caught.exception.problems[0])


if __name__ == "__main__":
    unittest.main()
