import unittest
from scoundrel.game import Game

class TestGame(unittest.TestCase):

    def setUp(self):
        self.game = Game()

    def test_initial_score(self):
        self.assertEqual(self.game.score, 0)

    def test_unlock_card_types(self):
        self.game.score = 100
        self.game.check_unlock_card_types()
        self.assertIn('Advanced', self.game.unlocked_card_types)

        self.game.score = 500
        self.game.check_unlock_card_types()
        self.assertIn('Expert', self.game.unlocked_card_types)

        self.game.score = 1000
        self.game.check_unlock_card_types()
        self.assertIn('Master', self.game.unlocked_card_types)

    def test_score_multiplier(self):
        self.game.difficulty = 'Easy'
        self.assertEqual(self.game.get_score_multiplier(), 1.5)

        self.game.difficulty = 'Medium'
        self.assertEqual(self.game.get_score_multiplier(), 1.0)

        self.game.difficulty = 'Hard'
        self.assertEqual(self.game.get_score_multiplier(), 0.75)

if __name__ == '__main__':
    unittest.main()