#!/usr/bin/env python3
"""
Test script for Scoundrel game functionality
"""

import os
import sys
import json

# Prevent pygame from displaying a window during tests
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from scoundrel import (
    ScoreSystem, UnlockSystem, Card, CardType, 
    Difficulty, ScoundrelGame
)


def test_score_system():
    """Test the score system"""
    print("Testing ScoreSystem...")
    
    score = ScoreSystem()
    initial_high = score.high_score
    
    # Test adding points
    score.add_points(50)
    assert score.current_score == 50, "Current score should be 50"
    
    score.add_points(30)
    assert score.current_score == 80, "Current score should be 80"
    
    # Test high score update
    if 80 > initial_high:
        assert score.high_score == 80, "High score should be updated"
    
    # Test reset
    score.reset_current_score()
    assert score.current_score == 0, "Current score should be reset to 0"
    assert score.games_played >= 1, "Games played should increment"
    
    print("✓ ScoreSystem tests passed")


def test_unlock_system():
    """Test the unlock system"""
    print("Testing UnlockSystem...")
    
    score = ScoreSystem()
    unlock = UnlockSystem(score)
    
    # Basic should always be unlocked
    assert unlock.is_unlocked(CardType.BASIC), "Basic cards should be unlocked"
    
    # Test unlock thresholds
    score.high_score = 0
    assert not unlock.is_unlocked(CardType.ADVANCED), "Advanced should be locked at 0"
    
    score.high_score = 100
    assert unlock.is_unlocked(CardType.ADVANCED), "Advanced should unlock at 100"
    
    score.high_score = 500
    assert unlock.is_unlocked(CardType.EXPERT), "Expert should unlock at 500"
    
    score.high_score = 1000
    assert unlock.is_unlocked(CardType.MASTER), "Master should unlock at 1000"
    
    # Test next unlock
    score.high_score = 50
    next_type, points = unlock.get_next_unlock()
    assert next_type == CardType.ADVANCED, "Next unlock should be Advanced"
    assert points == 50, "Should need 50 more points"
    
    print("✓ UnlockSystem tests passed")


def test_card():
    """Test card creation"""
    print("Testing Card...")
    
    card = Card(CardType.BASIC, 5, "Test Card")
    assert card.card_type == CardType.BASIC, "Card type should be BASIC"
    assert card.value == 5, "Card value should be 5"
    assert card.name == "Test Card", "Card name should be 'Test Card'"
    assert card.unlocked, "Basic cards should be unlocked"
    
    advanced_card = Card(CardType.ADVANCED, 10, "Advanced Card")
    assert not advanced_card.unlocked, "Advanced cards should start locked"
    
    print("✓ Card tests passed")


def test_difficulty():
    """Test difficulty enum"""
    print("Testing Difficulty...")
    
    assert Difficulty.EASY.value == 1
    assert Difficulty.MEDIUM.value == 2
    assert Difficulty.HARD.value == 3
    
    print("✓ Difficulty tests passed")


def test_game_initialization():
    """Test game initialization"""
    print("Testing ScoundrelGame initialization...")
    
    game = ScoundrelGame()
    
    # Check initial state
    assert game.state == "menu", "Initial state should be menu"
    assert game.difficulty == Difficulty.MEDIUM, "Default difficulty should be MEDIUM"
    assert game.score_system is not None, "Score system should be initialized"
    assert game.unlock_system is not None, "Unlock system should be initialized"
    assert len(game.deck) > 0, "Deck should have cards"
    
    print("✓ ScoundrelGame initialization tests passed")


def test_game_deck():
    """Test deck initialization"""
    print("Testing deck initialization...")
    
    game = ScoundrelGame()
    game.init_deck()
    
    # Should have at least basic cards
    assert len(game.deck) >= 10, "Should have at least 10 basic cards"
    
    # Check that cards are properly created
    has_basic = any(card.card_type == CardType.BASIC for card in game.deck)
    assert has_basic, "Deck should contain basic cards"
    
    print("✓ Deck initialization tests passed")


def test_card_drawing():
    """Test drawing cards"""
    print("Testing card drawing...")
    
    game = ScoundrelGame()
    initial_deck_size = len(game.deck)
    initial_hand_size = len(game.hand)
    
    card = game.draw_card()
    
    if card:
        assert len(game.deck) == initial_deck_size - 1, "Deck should have one less card"
        assert len(game.hand) == initial_hand_size + 1, "Hand should have one more card"
        assert card in game.hand, "Drawn card should be in hand"
    
    print("✓ Card drawing tests passed")


def test_difficulty_multipliers():
    """Test difficulty point multipliers"""
    print("Testing difficulty multipliers...")
    
    game = ScoundrelGame()
    game.start_game()
    
    # Add a card to hand
    test_card = Card(CardType.BASIC, 10, "Test")
    game.hand.append(test_card)
    
    # Test easy
    game.difficulty = Difficulty.EASY
    initial_score = game.score_system.current_score
    game.play_card(test_card)
    easy_points = game.score_system.current_score - initial_score
    assert easy_points == 15, f"Easy should give 15 points (1.5x), got {easy_points}"
    
    # Reset and test medium
    game.score_system.current_score = 0
    test_card2 = Card(CardType.BASIC, 10, "Test2")
    game.hand.append(test_card2)
    game.difficulty = Difficulty.MEDIUM
    game.play_card(test_card2)
    assert game.score_system.current_score == 10, "Medium should give 10 points (1x)"
    
    # Reset and test hard
    game.score_system.current_score = 0
    test_card3 = Card(CardType.BASIC, 10, "Test3")
    game.hand.append(test_card3)
    game.difficulty = Difficulty.HARD
    game.play_card(test_card3)
    assert game.score_system.current_score == 7, "Hard should give 7 points (0.75x)"
    
    print("✓ Difficulty multiplier tests passed")


def test_score_persistence():
    """Test score saving and loading"""
    print("Testing score persistence...")
    
    # Clean up any existing scores file
    if os.path.exists('scores.json'):
        os.remove('scores.json')
    
    # Create score system and set scores
    score1 = ScoreSystem()
    score1.high_score = 999
    score1.games_played = 5
    score1.save_scores()
    
    # Verify file was created
    assert os.path.exists('scores.json'), "Scores file should be created"
    
    # Load in new instance
    score2 = ScoreSystem()
    assert score2.high_score == 999, "High score should persist"
    assert score2.games_played == 5, "Games played should persist"
    
    # Clean up
    if os.path.exists('scores.json'):
        os.remove('scores.json')
    
    print("✓ Score persistence tests passed")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Running Scoundrel Tests")
    print("=" * 60)
    
    try:
        test_score_system()
        test_unlock_system()
        test_card()
        test_difficulty()
        test_game_initialization()
        test_game_deck()
        test_card_drawing()
        test_difficulty_multipliers()
        test_score_persistence()
        
        print("=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
