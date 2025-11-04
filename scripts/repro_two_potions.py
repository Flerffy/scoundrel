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

print("=== Scenario A: Two potions separated by refill (should heal twice) ===")
# Setup: health low, room with one potion, then refill provides another potion
eng.reset_state()
eng.health = 10
# deck arranged so prepare_room will draw a potion after refill
eng.deck = Deck([Card('clubs','2'), Card('hearts','4'), Card('spades','3')])
eng.room = [Card('hearts','5')]
print(f"Initial health={eng.health}, used_potion={eng.used_potion_this_turn}")
res = eng.face_card(0, start_pos=(0,0))
print("face_card returned:", res)
print(f"After face_card: health={eng.health}, used_potion={eng.used_potion_this_turn}, last_potion_value={eng.last_potion_value}")
# simulate refill behavior (engine would call prepare_room when room len == 1 -> after face it becomes 0)
if len(eng.room) == 0:
    print("Room empty; calling prepare_room() to refill")
    eng.prepare_room()
    print(f"After prepare_room: health={eng.health}, used_potion={eng.used_potion_this_turn}, room_len={len(eng.room)}")
# If a potion is now in room, face it
for i, c in enumerate(list(eng.room)):
    if c.suit == 'hearts':
        print(f"Found potion in room at index {i}: {c}")
        res2 = eng.face_card(i, start_pos=(0,0))
        print("face_card (second) returned:", res2)
        print(f"After second face: health={eng.health}, used_potion={eng.used_potion_this_turn}, last_potion_value={eng.last_potion_value}")
        break

print("Discard contains:", [c.to_dict() for c in eng.discard])

print('\n=== Scenario B: Two potions in same room (second should NOT heal) ===')
eng.reset_state()
eng.health = 10
eng.deck = Deck([Card('clubs','2'), Card('spades','3')])
# room has two potions
eng.room = [Card('hearts','3'), Card('hearts','4')]
print(f"Initial health={eng.health}, used_potion={eng.used_potion_this_turn}")
# use first potion
r1 = eng.face_card(0, start_pos=(0,0))
print("face_card first returned:", r1)
print(f"After first: health={eng.health}, used_potion={eng.used_potion_this_turn}")
# use second potion (now at index 0 after pop)
r2 = eng.face_card(0, start_pos=(0,0))
print("face_card second returned:", r2)
print(f"After second: health={eng.health}, used_potion={eng.used_potion_this_turn}")
print("Discard contains:", [c.to_dict() for c in eng.discard])

print("Done")
pygame.quit()
