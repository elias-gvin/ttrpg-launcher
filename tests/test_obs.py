import unittest

from helpers import PresetCase

from rpg_launcher.obs import check_references
from rpg_launcher.presets import ObsSettings


def settings(profile=None, collection=None, scene=None) -> ObsSettings:
    return ObsSettings(
        enabled=True, profile=profile, collection=collection, scene=scene, record=False, checks=()
    )


class ObsReferences(PresetCase):
    def setUp(self):
        super().setUp()
        self.config = self.write_obs_config()

    def test_existing_names_pass(self):
        check = check_references(self.config, settings("RPG", "Games", "Frostpunk"))
        self.assertEqual((check.problems, check.unverified), ([], []))

    def test_scene_is_looked_up_in_the_active_collection_when_none_is_named(self):
        check = check_references(self.config, settings(scene="Samosbor"))
        self.assertEqual((check.problems, check.unverified), ([], []))

    def test_missing_profile_lists_the_profiles_that_exist(self):
        check = check_references(self.config, settings(profile="Stream"))
        self.assertEqual(
            check.problems,
            ["OBS has no profile called 'Stream'. Profiles on this machine: 'RPG'."],
        )

    def test_missing_collection_lists_the_collections_that_exist(self):
        check = check_references(self.config, settings(collection="Other", scene="Samosbor"))
        self.assertEqual(len(check.problems), 1)
        self.assertIn("Scene collections on this machine: 'Games'", check.problems[0])

    def test_scene_name_must_match_exactly(self):
        check = check_references(self.config, settings(scene="samosbor"))
        self.assertIn("no scene called 'samosbor'", check.problems[0])

    def test_missing_settings_directory_is_unverified_not_a_pass_or_a_failure(self):
        check = check_references(self.root / "nowhere", settings(scene="Samosbor"))
        self.assertEqual(check.problems, [])
        self.assertIn("could not be checked", check.unverified[0])

    def test_unknown_active_collection_leaves_the_scene_unverified(self):
        (self.config / "user.ini").unlink()
        check = check_references(self.config, settings(scene="Samosbor"))
        self.assertEqual(check.problems, [])
        self.assertEqual(len(check.unverified), 1)

    def test_nothing_named_means_nothing_to_check(self):
        check = check_references(self.root / "nowhere", settings())
        self.assertEqual((check.problems, check.unverified), ([], []))


if __name__ == "__main__":
    unittest.main()
