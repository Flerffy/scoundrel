#!/usr/bin/env python3
"""
Demo script showing Scoundrel game features in headless mode
"""

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from scoundrel import ScoreSystem, UnlockSystem, CardType, Difficulty


def demo():
    """Demonstrate game features"""
    print("=" * 70)
    print("SCOUNDREL CARD GAME - Feature Demo")
    print("=" * 70)
    
    # Score System Demo
    print("\n📊 SCORE SYSTEM")
    print("-" * 70)
    score = ScoreSystem()
    print(f"Current Score: {score.current_score}")
    print(f"High Score: {score.high_score}")
    print(f"Games Played: {score.games_played}")
    
    print("\nAdding 150 points...")
    score.add_points(150)
    print(f"Current Score: {score.current_score}")
    print(f"High Score: {score.high_score}")
    
    # Unlock System Demo
    print("\n🔓 UNLOCK SYSTEM")
    print("-" * 70)
    unlock = UnlockSystem(score)
    
    for card_type in CardType:
        unlocked = unlock.is_unlocked(card_type)
        threshold = unlock.unlock_thresholds[card_type]
        status = "✓ UNLOCKED" if unlocked else "✗ LOCKED"
        print(f"{status} - {card_type.value.capitalize():<10} (requires {threshold} points)")
    
    next_unlock, points_needed = unlock.get_next_unlock()
    if next_unlock:
        print(f"\nNext unlock: {next_unlock.value.capitalize()} in {points_needed} points")
    else:
        print("\n🎉 All card types unlocked!")
    
    # Difficulty Demo
    print("\n⚙️  DIFFICULTY SETTINGS")
    print("-" * 70)
    base_value = 10
    for difficulty in [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]:
        if difficulty == Difficulty.EASY:
            multiplier = 1.5
            points = int(base_value * multiplier)
        elif difficulty == Difficulty.MEDIUM:
            multiplier = 1.0
            points = int(base_value * multiplier)
        else:  # HARD
            multiplier = 0.75
            points = int(base_value * multiplier)
        
        print(f"{difficulty.name:<8} - Card value {base_value} → {points} points (×{multiplier})")
    
    # Assets Demo
    print("\n📁 ASSETS STRUCTURE")
    print("-" * 70)
    assets_dirs = ['sfx', 'music', 'backgrounds', 'cards']
    for asset_dir in assets_dirs:
        print(f"assets/{asset_dir}/ - Ready for {asset_dir.replace('_', ' ')} files")
    
    print("\n" + "=" * 70)
    print("Demo complete! Run 'python scoundrel.py' to play the full game.")
    print("=" * 70)


if __name__ == "__main__":
    demo()
