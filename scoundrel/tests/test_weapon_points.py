import unittest
import sys
import os
# Ensure the project root is available on sys.path so package-relative
# imports in `scoundrel` work as expected when running tests directly.
# Ensure the package parent directory is on sys.path so `import scoundrel` works.
pkg_parent = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if pkg_parent not in sys.path:
    sys.path.insert(0, pkg_parent)

from scoundrel.scoundrel.engine import GameEngine
from scoundrel.scoundrel.cards.deck import Card

class TestWeaponPoints(unittest.TestCase):
    def test_compute_points_with_stack(self):
        # Weapon: 10 of diamonds; Monsters: A clubs (14), K spades (13), 10 spades (10)
        weapon = {"card": Card("diamonds", "10"), "stack": [Card("clubs", "A"), Card("spades", "K"), Card("spades", "10")], "last_monster": None}
        engine = GameEngine(screen=None)
        pts = engine._compute_weapon_points(w=weapon)
        # Calculation: (weapon.value + sum(monsters)) * number_of_monsters
        expected = (Card("diamonds", "10").value + Card("clubs", "A").value + Card("spades", "K").value + Card("spades", "10").value) * 3
        self.assertEqual(pts, expected)
        weapon = {"card": Card("diamonds", "10"), "stack": [], "last_monster": None}
        weapon = {"card": Card("diamonds", "10"), "stack": [], "last_monster": None}
        engine = GameEngine(screen=None)
        pts = engine._compute_weapon_points(w=weapon)
        self.assertEqual(pts, 0)
        self.assertEqual(pts, 0)
        self.assertEqual(pts, 0)
if __name__ == '__main__':
    unittest.main()
