import sys
from pathlib import Path
import pygame
# ensure repo root on sys.path so package imports work when running scripts/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scoundrel.scoundrel.engine import GameEngine
from scoundrel.scoundrel.cards.deck import Card, Deck

pygame.init()
# headless surface
screen = pygame.Surface((800, 600))
eng = GameEngine(screen)
eng._debug = True
# reduce health so potion can actually restore
eng.health = 15

# Prepare a small deterministic deck so prepare_room draws predictable cards
# Put a few non-heart cards after so we can draw
eng.deck = Deck([Card('clubs','2'), Card('spades','3'), Card('diamonds','4'), Card('hearts','6'), Card('clubs','5')])

# Build a room of two cards where the second is a potion (hearts)
eng.room = [Card('clubs','7'), Card('hearts','5')]
print(f"Initial health={eng.health}, used_potion={eng.used_potion_this_turn}")

# Simulate clicking the potion at index 1
res = eng.face_card(1, start_pos=(0,0))
print("face_card returned:", res)
print(f"After face_card: health={eng.health}, used_potion={eng.used_potion_this_turn}, last_potion_value={eng.last_potion_value}")

# Now simulate the run-loop behaviour which calls prepare_room when len(room)==1
if len(eng.room) == 1:
    print("Room has 1 card; calling prepare_room() to refill")
    eng.prepare_room()
    print(f"After prepare_room: health={eng.health}, used_potion={eng.used_potion_this_turn}, room_len={len(eng.room)}")

# Print discard contents
print("Discard contains:", [c.to_dict() for c in eng.discard])

# Exit
print("Done")
pygame.quit()
