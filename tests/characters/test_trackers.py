"""Character tracker tests."""

import unittest

from inconnu.constants import Damage
from tests.characters import gen_char


class TestCharacterTrackers(unittest.TestCase):
    """
    A class for testing various character tracker methods for different splats.
    """

    def test_hunger(self):
        """Test Hunger rating for the different splats."""
        for splat in ["vampire", "ghoul", "mortal", "thin-blood"]:
            char = gen_char(splat)
            if char.is_vampire:
                self.assertEqual(char.hunger, 1)
            else:
                self.assertEqual(char.hunger, 0)
                char.hunger = 4
                self.assertEqual(char.hunger, 0, "Hunger should always be zero")

        char.hunger = 3
        self.assertEqual(char.hunger, 3)
        char.hunger = 30
        self.assertEqual(char.hunger, 5)
        char.hunger = -3
        self.assertEqual(char.hunger, 0)

    def test_apply_damage(self):
        """Test damage application and wrapping."""
        char = gen_char("vampire")

        char.apply_damage("health", Damage.SUPERFICIAL, 3)
        self.assertEqual(char.health, "...///")

        char.apply_damage("health", Damage.AGGRAVATED, 1)
        self.assertEqual(char.health, "..///x")

        char.apply_damage("health", Damage.SUPERFICIAL, 2)
        self.assertEqual(char.health, "/////x")
        self.assertTrue(char.physically_impaired)
        self.assertFalse(char.mentally_impaired)

        char.apply_damage("health", Damage.SUPERFICIAL, 2)
        self.assertEqual(char.health, "///xxx")
        self.assertEqual(char.superficial_hp, 3)
        self.assertEqual(char.aggravated_hp, 3)

        char.apply_damage("willpower", Damage.SUPERFICIAL, 8)
        self.assertEqual(char.willpower, "//xxx")
        self.assertEqual(char.superficial_wp, 2)
        self.assertEqual(char.aggravated_wp, 3)
        self.assertTrue(char.mentally_impaired)

    def test_set_damage(self):
        """Test the set_damage() method."""
        char = gen_char("vampire")

        char.set_damage("health", Damage.SUPERFICIAL, 3)
        self.assertEqual(char.health, "...///")

        char.set_damage("health", Damage.SUPERFICIAL, 20)
        self.assertEqual(char.health, "//////")

        char.set_damage("health", Damage.AGGRAVATED, 1)
        self.assertEqual(char.health, "/////x")

        char.set_damage("health", Damage.AGGRAVATED, 0)
        self.assertEqual(char.health, "./////")

    def test_humanity(self):
        """Test Humanity calculations."""
        char = gen_char("vampire")

        self.assertEqual(char.humanity, 7)
        self.assertEqual(char.stains, 0)

        char.stains += 2
        self.assertEqual(char.humanity, 7)
        self.assertEqual(char.stains, 2)

        self.assertFalse(char.degeneration)

        char.stains += 2
        self.assertTrue(char.degeneration)

        char.humanity -= 1
        self.assertEqual(char.humanity, 6)
        self.assertEqual(char.stains, 0)
