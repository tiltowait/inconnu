"""Specialty test suite."""
# pylint: disable=too-few-public-methods

import unittest
import warnings

from marshmallow.warnings import RemovedInMarshmallow4Warning

from inconnu.models.vchardocs import VCharTrait

NAME = "Brawl"
RATING = 4
SPECIALTIES = ["Kindred", "StreetFighting"]


def gen_skill(*specialties: str) -> VCharTrait:
    """Shorthand skill generation."""
    skill = VCharTrait(name=NAME, rating=RATING, type=VCharTrait.Type.SKILL)
    skill.add_specialties(specialties)

    return skill


class TestSpecialties(unittest.TestCase):
    """Runs several tests on specialties."""

    def setUp(self):
        """Disable the Marshmallow warning."""
        warnings.simplefilter("ignore", category=RemovedInMarshmallow4Warning)

    def test_basic_skill_matching(self):
        trait = gen_skill()

        matches = trait.matching("b", False)
        self.assertEqual(len(matches), 1)

        match = matches[0]
        self.assertEqual(match.name, NAME)
        self.assertEqual(match.rating, RATING)

        matches = trait.matching("q", False)
        self.assertEqual(len(matches), 0, "'q' shouldn't have matched")

        # Exact matching
        matches = trait.matching("b", True)
        self.assertEqual(len(matches), 0, "Exact matching failed")

        matches = trait.matching(NAME, True)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].name, NAME)
        self.assertEqual(matches[0].rating, RATING)

        matches = trait.matching(NAME.lower(), True)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].name, NAME)
        self.assertEqual(matches[0].rating, RATING)

    def test_specialty_addition(self):
        skill = gen_skill()

        self.assertEqual(len(skill.specialties), 0)

        skill.add_specialties("Kindred")
        self.assertEqual(len(skill.specialties), 1)

        skill.add_specialties("Kindred")
        self.assertEqual(len(skill.specialties), 1, "Two 'Kindred' specs were added")

        skill.add_specialties("StreetFighting")
        self.assertEqual(len(skill.specialties), 2, "StreetFighting wasn't added")

        skill.add_specialties(["One", "Two", "Two"])
        self.assertEqual(len(skill.specialties), 4, "List wasn't added")

    def test_specialty_removal(self):
        skill = gen_skill("One", "Two", "Three")
        self.assertEqual(len(skill.specialties), 3)

        skill.remove_specialties("One")
        self.assertEqual(len(skill.specialties), 2)

        skill.remove_specialties("One")
        self.assertEqual(len(skill.specialties), 2, "Nothing should have been removed")

        skill.remove_specialties(["Two", "Three"])
        self.assertEqual(len(skill.specialties), 0, "Specialties should be gone")

    def test_specialty_matching(self):
        skill = gen_skill("Kindred", "StreetFighting", "Killing")
        self.assertEqual(len(skill.specialties), 3)

        # No match
        matches = skill.matching(":z", False)
        self.assertEqual(len(matches), 0)

        # Partial match -> No match
        matches = skill.matching(":k:z", False)
        self.assertEqual(len(matches), 0)

        # Single match, with skill name
        matches = skill.matching("b:kin", False)
        self.assertEqual(len(matches), 1)

        match = matches[0]
        self.assertEqual(match.name, f"{NAME} (Kindred)")
        self.assertEqual(match.rating, RATING + 1)

        # Single match, no skill name
        matches = skill.matching(":kin", False)
        self.assertEqual(len(matches), 1)

        match = matches[0]
        self.assertEqual(match.name, f"{NAME} (Kindred)")
        self.assertEqual(match.rating, RATING + 1)

        # Multiple matches
        matches = skill.matching(":k", False)
        self.assertEqual(len(matches), 2, str(matches))
