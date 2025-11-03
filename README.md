# Scoundrel

A card game built with pygame featuring score tracking, unlockable card types, and difficulty settings.

## Features

- **Score System**: Track your current score and high score across games
- **Unlockable Card Types**: Unlock new card types by reaching score thresholds
  - Basic cards (always available)
  - Advanced cards (unlock at 100 points)
  - Expert cards (unlock at 500 points)
  - Master cards (unlock at 1000 points)
- **Difficulty Settings**: Choose from Easy, Medium, or Hard difficulty
  - Easy: 1.5x points multiplier
  - Medium: Normal points
  - Hard: 0.75x points multiplier

## Installation

1. Install Python 3.7 or higher
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## How to Play

Run the game:
```bash
python scoundrel.py
```

### Controls

**Main Menu:**
- Press `1`, `2`, or `3` to select difficulty (Easy, Medium, Hard)
- Press `SPACE` to start the game

**During Game:**
- Click on a card to select it
- Press `ENTER` to play the selected card
- Press `ESC` to return to menu

**Game Over:**
- Press `SPACE` to return to menu

## Game Rules

1. You start with a hand of 5 cards
2. Select and play cards to earn points
3. Each card has a value based on its type
4. Points are modified by difficulty setting
5. When you play a card, a new one is drawn from the deck
6. Game ends when both deck and hand are empty
7. Reach score thresholds to unlock new card types permanently

## Assets Directory

The `assets/` directory contains subdirectories for game assets:
- `sfx/` - Sound effects
- `music/` - Background music
- `backgrounds/` - Background images
- `cards/` - Card images

## Development

The game saves your high score and games played count in `scores.json`.
