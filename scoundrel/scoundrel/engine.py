import pygame
import json
from pathlib import Path
from collections import deque
from .cards.deck import Deck, Card
from typing import Any, Optional, List, Dict

# UI atlas and widgets (optional best-effort imports)
# Annotate as Any first so static type checkers don't treat these as
# immutable types when we fall back to `None` on import failure.
UIAtlas: Any = None
NinePatchButton: Any = None
try:
    from .utils.ui_atlas import UIAtlas as _UIAtlas
    UIAtlas = _UIAtlas
except Exception:
    UIAtlas = None
try:
    # Perform a runtime dynamic import to avoid static analyzers failing on
    # relative imports when the optional UI package isn't present.
    import importlib

    _mod = None
    if __package__:
        try:
            # Try a relative import using the current package context
            _mod = importlib.import_module(".ui.widgets", package=__package__)
        except Exception:
            # Fallback: try importing using the package root as an absolute path
            try:
                root = __package__.split(".")[0]
                _mod = importlib.import_module(f"{root}.ui.widgets")
            except Exception:
                _mod = None
    else:
        # No package context; try importing a top-level module name if available
        try:
            _mod = importlib.import_module("ui.widgets")
        except Exception:
            _mod = None

    if _mod is not None:
        _NinePatchButton = getattr(_mod, "NinePatchButton", None)
        NinePatchButton = _NinePatchButton
    else:
        NinePatchButton = None
except Exception:
    NinePatchButton = None


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
from .utils.assets import CardArtManager


class GameEngine:
    # Instance attributes (typed for static analysis)
    deck: Deck
    discard: List[Card]
    equipped_weapon: Optional[Dict[str, Any]]
    room: List[Card]
    def __init__(self, screen, card_size=(120, 180)):
        # `display` is the real window surface. We will render into a virtual buffer
        # at a pixel-perfect virtual resolution and scale that buffer to the display.
        self.display = screen
        # art manager - choose default pack (if present)
        self.art = CardArtManager(pack_name="ClassicCards")
        self.card_size = card_size
        # right padding used for weapon/discard placement
        self.right_pad = 8
        self.pending_combat = None  # {'index': int, 'card': Card}
        self.room_rects = []
        self.weapon_rect = None
        self.ui_buttons = {}
        self.clock = pygame.time.Clock()
        self.reset_state()
        # remember last weapon position so animations can start even if the
        # rect isn't populated at the exact moment of an action
        self._last_weapon_pos = (0, 0)  # Initialize to a default position

        # compute a virtual render size based on card size and layout used in render()
        cw, ch = self.card_size
        # left margin + 4 cards (with spacing) + gap + weapon + right margin
        self.virtual_w = 16 + (cw + 16) * 4 + 16 + cw + 16
        # ensure enough height for instructions and padding; pick a sensible minimum
        self.virtual_h = max(640, 150 + ch + 200)
        # try to load tiled background (optional)
        try:
            # assets/ is located at the package root (one level up from this module)
            bg_path = Path(__file__).resolve().parents[1] / "assets" / "backgrounds" / "ClassicBackground.png"
            if bg_path.exists():
                # load as opaque surface (background tile should be opaque)
                self._bg_tile = pygame.image.load(str(bg_path)).convert()
            else:
                self._bg_tile = None
        except Exception:
            self._bg_tile = None
        # try to load a card-back image for the deck display
        try:
            back_path = Path(__file__).resolve().parents[1] / "assets" / "backsides" / "LightClassic.png"
            if back_path.exists():
                raw = pygame.image.load(str(back_path)).convert()
                # scale to the configured card size for the virtual render
                try:
                    self._backside = pygame.transform.scale(raw, (cw, ch))
                except Exception:
                    self._backside = raw
            else:
                self._backside = None
        except Exception:
            self._backside = None
        # cache for background tiles scaled to integer multiples
        self._bg_tile_scaled_cache = {}
        # input mapping helpers
        self._last_scale = None
        self._last_offset = (0, 0)
        # animation queue: FIFO of pending animations and the active animation
        # each animation is a dict with keys: type, card, surf, start, end, frames_left, total
        self._anim_queue = deque()
        self._active_anim = None
        # try to load simple sfx (optional). Best-effort attempt to initialize mixer first.
        try:
            sfx_path = Path(__file__).resolve().parents[1] / "assets" / "sfx" / "cardFlip.wav"
            # If the mixer isn't initialized, try to initialize it (best-effort).
            try:
                if not pygame.mixer.get_init():
                    try:
                        pygame.mixer.init()
                    except Exception:
                        # mixer couldn't initialize; continue without sound
                        pass
            except Exception:
                pass

            if sfx_path.exists() and pygame.mixer.get_init():
                try:
                    # load primary flip sound and also prepare map for other sfx
                    self._card_flip_sound = pygame.mixer.Sound(str(sfx_path))
                    try:
                        self._card_flip_sound.set_volume(0.9)
                    except Exception:
                        pass
                except Exception:
                    self._card_flip_sound = None
            else:
                self._card_flip_sound = None
        except Exception:
            self._card_flip_sound = None

        # load additional sfx files into a dict for use throughout the engine
        self._sfx = {}
        try:
            sfx_dir = Path(__file__).resolve().parents[1] / "assets" / "sfx"
            def _try_load(name):
                p = sfx_dir / f"{name}.wav"
                if p.exists() and pygame.mixer.get_init():
                    try:
                        s = pygame.mixer.Sound(str(p))
                        try:
                            s.set_volume(0.9)
                        except Exception:
                            pass
                        return s
                    except Exception:
                        return None
                return None

            self._sfx["monsterHit"] = _try_load("monsterHit")
            self._sfx["potionUse"] = _try_load("potionUse")
            self._sfx["weaponEquip"] = _try_load("weaponEquip")
            # cardFlip also available via _card_flip_sound for legacy usage
            if "cardFlip" not in self._sfx:
                self._sfx["cardFlip"] = self._card_flip_sound
        except Exception:
            # best-effort; leave _sfx possibly empty
            pass

        # try to locate a bundled UI font (DungeonFont.ttf) in assets/ui
        try:
            fp = Path(__file__).resolve().parents[1] / "assets" / "ui" / "DungeonFont.ttf"
            if fp.exists():
                self._font_path = str(fp)
            else:
                self._font_path = None
        except Exception:
            self._font_path = None
        # simple cache for pygame.font.Font objects by size
        self._font_cache = {}
        # try to load UI atlas and semantic mapping for spritesheet-backed widgets
        self._ui_atlas = None
        self._ui_mapping = {}
        # cache for extracted atlas surfaces and created UI widget instances
        self._atlas_surface_cache = {}
        self._ui_buttons_cache = {}
        try:
            if UIAtlas is not None:
                atlas_img = Path(__file__).resolve().parents[1] / "assets" / "ui" / "BlackGreyUISheet.png"
                atlas_json = Path(__file__).resolve().parents[1] / "assets" / "ui" / "BlackGreyUISheet.json"
                mapping_json = Path(__file__).resolve().parents[1] / "assets" / "ui" / "BlackGreyUISheet_mapping.json"
                if atlas_img.exists():
                    ua = UIAtlas(atlas_img, atlas_json if atlas_json.exists() else None)
                    try:
                        ua.load_image()
                    except Exception:
                        pass
                    if atlas_json.exists():
                        try:
                            ua.load_descriptor(atlas_json)
                        except Exception:
                            pass
                    self._ui_atlas = ua
                if mapping_json.exists():
                    try:
                        self._ui_mapping = json.loads(mapping_json.read_text())
                    except Exception:
                        self._ui_mapping = {}
        except Exception:
            self._ui_atlas = None
            self._ui_mapping = {}

    # --- UI atlas helpers ---
    def _get_atlas_tile(self, semantic_name: str):
        """Return (Surface, inset_tuple) for a semantic tile name, or (None, None).

        Uses self._ui_mapping to find the tile id, then extracts and caches the surface.
        """
        try:
            if not self._ui_atlas:
                return None, None
            tid = self._ui_mapping.get(semantic_name)
            if not tid:
                return None, None
            # cached by tile id
            if tid in self._atlas_surface_cache:
                t, inset = self._atlas_surface_cache[tid]
                return t, inset
            tile = self._ui_atlas.tiles.get(tid)
            if not tile:
                return None, None
            tx, ty, tw, th = tile.get("x"), tile.get("y"), tile.get("w"), tile.get("h")
            try:
                surf = self._ui_atlas.image.subsurface(pygame.Rect(tx, ty, tw, th)).copy().convert_alpha()
            except Exception:
                return None, None
            inset = tuple(tile.get("ninepatch", [4, 4, 4, 4]))
            self._atlas_surface_cache[tid] = (surf, inset)
            return surf, inset
        except Exception:
            return None, None

    def _get_or_create_ninepatch_button(self, cache_key: str, semantic_tile: str, pos, size, text, font):
        """Return a cached NinePatchButton instance for given key, creating it if missing or out-of-date."""
        try:
            # check cache
            existing = self._ui_buttons_cache.get(cache_key)
            if existing:
                btn, meta = existing
                # meta: (pos, size, text)
                if meta == (pos, size, text):
                    # update rect in case pos changed slightly
                    btn.rect.topleft = (pos[0], pos[1])
                    return btn
            # Try to assemble a state->surface mapping for buttons (normal/hover/pressed)
            surf_map = None
            try:
                # If the semantic_tile is a button base name, look up alternate states
                if semantic_tile.startswith("button"):
                    states = ["button_normal", "button_hover", "button_pressed"]
                    sm = {}
                    found = False
                    for sname in states:
                        s_surf, s_inset = self._get_atlas_tile(sname)
                        if s_surf is not None:
                            sm_key = sname.replace("button_", "")
                            sm[sm_key] = s_surf
                            inset = s_inset
                            found = True
                    if found:
                        surf_map = sm
                # fallback: single tile
                if surf_map is None:
                    surf, inset = self._get_atlas_tile(semantic_tile)
                    if surf is None or NinePatchButton is None:
                        return None
                    btn = NinePatchButton(surf, inset, pos, size, font=font, text=text)
                else:
                    # use the assembled state map and pass the inset we discovered
                    btn = NinePatchButton(surf_map, inset, pos, size, font=font, text=text)
            except Exception:
                # if any error building the surf_map fallback, continue to return None
                return None
            self._ui_buttons_cache[cache_key] = (btn, (pos, size, text))
            return btn
        except Exception:
            return None

    def get_font(self, size: int):
        """Return a cached pygame.font.Font at the requested size. Falls back to SysFont on error."""
        try:
            if getattr(self, "_font_cache", None) is None:
                self._font_cache = {}
            if size in self._font_cache:
                return self._font_cache[size]
            if getattr(self, "_font_path", None):
                try:
                    f = pygame.font.Font(self._font_path, size)
                    self._font_cache[size] = f
                    return f
                except Exception:
                    pass
            # fallback to default pygame font if no bundled font is available
            f = pygame.font.Font(None, size)
            self._font_cache[size] = f
            return f
        except Exception:
            return pygame.font.Font(None, size)

    def _play_sfx(self, key: str):
        """Play a named sfx if available (safe/no-raise)."""
        try:
            snd = self._sfx.get(key) if hasattr(self, "_sfx") else None
            if snd:
                try:
                    snd.play()
                except Exception:
                    pass
        except Exception:
            pass
    # --- Animation / layout helpers ---
    def _compute_layout(self):
        """Compute and return layout positions used by render so other code
        can enqueue animations with reliable start/end positions.

        Returns dict with: room_positions (list of 4 (x,y)), deck_pos (x,y), weapon_pos (x,y)
        """
        card_w, card_h = self.card_size
        spacing = 16
        total_width = card_w * 4 + spacing * 3
        x_start = (self.virtual_w - total_width) // 2
        # weapon is placed near the top-right; reserve that space
        right_pad = self.right_pad
        wx = self.virtual_w - card_w - right_pad
        wy = 16
        preferred_y = self.virtual_h // 2 - (card_h // 2) + 40
        min_y = wy + card_h + 16
        max_y = self.virtual_h - card_h - 160
        y_room = max(min_y, min(preferred_y, max_y))

        room_positions = []
        x = x_start
        for i in range(4):
            room_positions.append((x, y_room))
            x += card_w + spacing

        deck_x = x_start + (total_width - card_w) // 2
        deck_y = y_room - card_h - 16

        return {
            "room_positions": room_positions,
            "deck_pos": (deck_x, deck_y),
            "weapon_pos": (wx, wy),
        }

    def _enqueue_animation(self, anim: dict):
        """Add an animation dict to the queue or start it immediately if idle.

        anim must include: type, card, surf (optional), start, end, total
        """
        # ensure surf exists
        if "surf" not in anim or anim.get("surf") is None:
            try:
                c = anim.get("card")
                if c and self.art:
                    anim["surf"] = self.art.get_card(c.suit, c.rank, size=self.card_size)
            except Exception:
                anim["surf"] = None

        anim.setdefault("frames_left", anim.get("total", 12))

        # Deduplicate conflicting animations for the same card. In particular,
        # prevent a 'to_weapon' and a 'discard' for the same card both being
        # queued (which causes the snap-to-weapon-then-discard glitch).
        try:
            c = anim.get("card")
            if c is not None:
                cid = id(c)
                def keep(a):
                    try:
                        ac = a.get("card")
                        if ac is None:
                            return True
                        aid = id(ac)
                        # If this queued anim targets the same card and is the
                        # opposite of the new anim (discard <-> to_weapon), drop it.
                        if aid == cid:
                            t_new = anim.get("type")
                            t_old = a.get("type")
                            if (t_new == "to_weapon" and t_old == "discard") or (t_new == "discard" and t_old == "to_weapon"):
                                return False
                        return True
                    except Exception:
                        return True
                self._anim_queue = deque([a for a in self._anim_queue if keep(a)])
        except Exception:
            pass

        if getattr(self, "_debug", False):
            try:
                at = anim.get("type")
                ac = anim.get("card")
                aid = id(ac) if ac is not None else None
                print(f"[DEBUG] enqueue_animation type={at} card_id={aid} start={anim.get('start')} end={anim.get('end')} total={anim.get('total')}")
            except Exception:
                pass

        if self._active_anim is None:
            self._active_anim = anim
            # play sfx for start
            try:
                typ = anim.get("type")
                if typ in ("draw", "discard"):
                    self._play_sfx("cardFlip")
                elif typ == "equip":
                    self._play_sfx("weaponEquip")
                elif typ == "to_weapon":
                    # using weapon on monster => attack sound
                    self._play_sfx("monsterHit")
            except Exception:
                pass
        else:
            self._anim_queue.append(anim)

    def _start_next_animation_if_needed(self):
        if self._active_anim is None and self._anim_queue:
            self._active_anim = self._anim_queue.popleft()
            try:
                typ = self._active_anim.get("type")
                if typ in ("draw", "discard"):
                    self._play_sfx("cardFlip")
                elif typ == "equip":
                    self._play_sfx("weaponEquip")
                elif typ == "to_weapon":
                    self._play_sfx("monsterHit")
            except Exception:
                pass

    def _on_animation_complete(self, anim: dict):
        typ = anim.get("type")
        card = anim.get("card")
        if getattr(self, "_debug", False):
            try:
                cid = id(card) if card is not None else None
                print(f"[DEBUG] animation_complete type={typ} card_id={cid}")
            except Exception:
                pass
        # finalise state changes
        try:
            if typ == "draw":
                # draw animations are visual-only; clear pending mark so the
                # card is rendered at its slot from now on
                try:
                    pid = id(card) if card is not None else None
                    if pid is not None and hasattr(self, "_pending_draw_ids"):
                        self._pending_draw_ids.discard(pid)
                except Exception:
                    pass
            elif typ == "discard":
                try:
                    if getattr(self, "_debug", False):
                        try:
                            print(f"[DEBUG] appending to discard card_id={id(card) if card is not None else None}")
                        except Exception:
                            pass
                    # Only append if it looks like a Card instance
                    if isinstance(card, Card):
                        self.discard.append(card)
                except Exception:
                    # Ensure discard is a list before appending; defensive fallback
                    cur = getattr(self, "discard", None)
                    if not isinstance(cur, list):
                        self.discard = []
                    else:
                        self.discard = cur
                    if isinstance(card, Card):
                        self.discard.append(card)
            elif typ == "equip":
                # set equipped weapon (new card). keep stack if replaced already handled
                self.equipped_weapon = {"card": card, "stack": [], "last_monster": None}
            elif typ == "to_weapon":
                # add monster to equipped stack
                if not self.equipped_weapon:
                    self.equipped_weapon = {"card": None, "stack": [], "last_monster": None}
                try:
                    # Only append and update last_monster when card is a Card
                    if isinstance(card, Card):
                        self.equipped_weapon["stack"].append(card)
                        mv = getattr(card, "value", None)
                        if mv is not None:
                            self.equipped_weapon["last_monster"] = mv
                except Exception:
                    pass
        except Exception:
            pass

        # clear active and start next
        # If the completed animation moved a card onto the weapon stack,
        # ensure there are no stray discard animations queued for the same
        # card (this can happen if fallbacks/enqueue order race). Remove
        # any pending discard anims for this exact card to avoid it
        # snapping to weapon then immediately sliding to discard.
        try:
            if anim.get("type") == "to_weapon" and anim.get("card") is not None:
                cid = id(anim.get("card"))
                try:
                    # filter out queued discard animations for this card
                    self._anim_queue = deque([a for a in self._anim_queue if not (a.get("type") == "discard" and id(a.get("card")) == cid)])
                except Exception:
                    pass
        except Exception:
            pass

        self._active_anim = None
        if self._anim_queue:
            self._active_anim = self._anim_queue.popleft()
            # ensure frames_left exists for newly started anim
            try:
                self._active_anim.setdefault("frames_left", self._active_anim.get("total", 12))
            except Exception:
                pass
            try:
                typ = self._active_anim.get("type")
                if typ in ("draw", "discard"):
                    self._play_sfx("cardFlip")
                elif typ == "equip":
                    self._play_sfx("weaponEquip")
                elif typ == "to_weapon":
                    self._play_sfx("monsterHit")
            except Exception:
                pass

    # compatibility wrapper: replace old immediate discard starter with queueing
    def _move_to_discard(self, card: Card, start_pos=None):
        sp = start_pos
        if sp is None:
            sp = getattr(self, "_last_weapon_pos", None)
        if sp is None:
            try:
                cw, ch = self.card_size
                pad = getattr(self, "right_pad", 8)
                sp = (self.virtual_w - cw - pad, 16)
            except Exception:
                sp = (0, 0)
        end = self._get_discard_pos()
        try:
            anim = {"type": "discard", "card": card, "start": sp, "end": end, "total": 14}
            self._enqueue_animation(anim)
        except Exception:
            if isinstance(card, Card):
                self.discard.append(card)
            else:
                pass

    def reset_state(self):
        self.deck = Deck()
        self.deck.shuffle()
        # typed container of discarded Card objects
        self.discard: List[Card] = []
        self.health = 20
        self.starting_health = 20
        self.last_potion_value = 0
        # equipped_weapon holds a dict with keys: card, stack, last_monster
        self.equipped_weapon: Optional[Dict[str, Any]] = None
        # face-up cards (list of Card)
        self.room: List[Card] = []
        self.previous_avoided = False
        self.used_potion_this_turn = False
        self.pending_combat = None
        self.room_rects = []
        self.weapon_rect = None
        self.ui_buttons = {}
        self.turn_in_progress = False
        # whether the player has interacted with any card in the current room
        # (once True, the player may not 'avoid' the room with the A key)
        self.room_interacted = False
        # paused state and simple settings-mode flag used by the pause menu
        self.paused = False
        self.in_settings = False
        # history of last-interacted cards (most recent appended at end)
        self._interaction_history: List[Card] = []
        # reset animation queue state
        self._anim_queue = deque()
        self._active_anim = None
        # track card object ids that are drawn but whose visual animation is
        # still running. While pending, the card is reserved in `self.room`
        # but will not be rendered at its slot until its draw animation
        # completes.
        self._pending_draw_ids = set()
        # developer debug flag: set True to get lightweight console traces
        # for animation and potion-related events
        self._debug = False

    def _reset_used_potion_flag(self, reason: Optional[str] = None):
        """Reset the per-room potion-used flag. When debugging, emit a trace
        including an optional reason to help diagnose timing/order issues.
        """
        try:
            self.used_potion_this_turn = False
            if getattr(self, "_debug", False):
                m = f"[DEBUG] reset used_potion_this_turn"
                if reason:
                    m += f" (reason={reason})"
                print(m)
        except Exception:
            try:
                self.used_potion_this_turn = False
            except Exception:
                pass


    # Save/load functionality has been removed. Game state is not persisted.

    def _weapon_to_dict(self, w):
        if not w:
            return None
        return {
            "card": w["card"].to_dict(),
            "stack": [c.to_dict() for c in w["stack"]],
            "last_monster": w.get("last_monster"),
        }

    def _get_discard_pos(self):
        """Return the top-left (x,y) virtual coordinates of the discard pile."""
        card_w, card_h = self.card_size
        pad = self.right_pad
        x = self.virtual_w - card_w - pad
        y = self.virtual_h - card_h - pad
        return (x, y)

    # old single-discard animator removed; animations are queued via _enqueue_animation

    def _weapon_from_dict(self, d):
        if not d:
            return None
        return {
            "card": Card.from_dict(d["card"]),
            "stack": [Card.from_dict(c) for c in d.get("stack", [])],
            "last_monster": d.get("last_monster"),
        }

    # -- game actions --
    def prepare_room(self):
        # fill room to 4 cards by enqueueing one-at-a-time draw animations
        # preparing a new room resets the 'interacted' flag
        try:
            self.room_interacted = False
        except Exception:
            pass
        layout = self._compute_layout()
        deck_pos = layout.get("deck_pos")
        # compute how many to draw
        while len(self.room) < 4:
            c = self.deck.draw()
            if c is None:
                break
            # Determine the target slot index before appending so animations
            # end at the correct position (avoid off-by-one).
            room_positions = layout.get("room_positions", [])
            target_idx = len(self.room)
            if target_idx < len(room_positions):
                target_pos = room_positions[target_idx]
            else:
                target_pos = room_positions[-1] if room_positions else deck_pos

            # Append card to room immediately so the draw loop doesn't keep draining the deck.
            try:
                self.room.append(c)
            except Exception:
                self.room = getattr(self, "room", [])
                self.room.append(c)

            # enqueue a draw animation (visual only) and mark card as pending so
            # it isn't rendered at its slot until the animation completes.
            anim = {"type": "draw", "card": c, "start": deck_pos, "end": target_pos, "total": 12}
            try:
                self._pending_draw_ids.add(id(c))
            except Exception:
                pass
            self._enqueue_animation(anim)

    def avoid_room(self):
        if self.previous_avoided:
            return False
        # move all four cards to bottom
        if len(self.room) < 4:
            return False
        cards = self.room[:4]
        self.room = []
        self.deck.add_to_bottom(cards)
        # mark that we've avoided this room and reset potion-use flag
        try:
            self.previous_avoided = True
        except Exception:
            self.previous_avoided = True
        try:
            self._reset_used_potion_flag("avoid_room")
        except Exception:
            try:
                self._reset_used_potion_flag("avoid_room_fallback")
            except Exception:
                try:
                    self.used_potion_this_turn = False
                except Exception:
                    pass
        return True

    def face_card(self, index, prefer_weapon=None, start_pos=None):
        """Face a card at room[index] (0-based). Returns a dict describing the event.

        prefer_weapon: None (auto), True(force weapon), False(force barehand)
        """
        if index < 0 or index >= len(self.room):
            return {"error": "invalid index"}
        # mark that the player is interacting with the room (prevents skipping)
        try:
            self.room_interacted = True
        except Exception:
            pass

        # determine a reasonable start position for animations if not provided
        if start_pos is None:
            try:
                if index < len(self.room_rects):
                    start_pos = self.room_rects[index].topleft
            except Exception:
                start_pos = None
        # prevent interacting with a card that is still pending its draw animation
        try:
            ctmp = self.room[index]
            if hasattr(self, "_pending_draw_ids") and (id(ctmp) in self._pending_draw_ids):
                return {"error": "card not ready"}
        except Exception:
            pass

        card = self.room.pop(index)
        # record this interaction (used to show the discard pile as the last
        # card the player interacted with). We append before resolving so the
        # interaction is recorded even if the card becomes equipped.
        try:
            self._interaction_history.append(card)
        except Exception:
            # defensive: if history missing for some reason, create it
            self._interaction_history = [card]
        # reset avoid flag when you engage
        self.previous_avoided = False
        if card.suit in ("clubs", "spades"):
            # Monster
            result = self._resolve_monster(card, prefer_weapon=prefer_weapon, start_pos=start_pos)
            result["card"] = card
            return result
        elif card.suit == "diamonds":
            # Weapon: equip it
            # prefer to animate equip from the start_pos into the weapon slot
            self._equip_weapon(card, start_pos=start_pos)
            return {"card": card, "action": "equip"}
        elif card.suit == "hearts":
            # potion: always restore health up to starting_health when used.
            # Any overflow is lost (cap at starting_health).
            add = 0
            try:
                add = min(self.starting_health - self.health, card.value)
            except Exception:
                add = 0
            try:
                if add and add > 0:
                    self.health += add
            except Exception:
                pass
            # mark potion used flag (kept for compatibility) and record last value
            try:
                self.used_potion_this_turn = True
            except Exception:
                self.used_potion_this_turn = True
            self.last_potion_value = card.value
            if getattr(self, "_debug", False):
                try:
                    print(f"[DEBUG] potion used (always): +{add} hp -> health={self.health}; used_potion_this_turn={self.used_potion_this_turn}")
                except Exception:
                    pass
            try:
                self._play_sfx("potionUse")
            except Exception:
                pass
            # animate the potion moving to discard so the player sees the
            # card slide away from its slot into the discard pile.
            try:
                self._move_to_discard(card, start_pos)
            except Exception:
                try:
                    if isinstance(card, Card):
                        self.discard.append(card)
                except Exception:
                    pass
            return {"card": card, "action": "potion_used", "added": add}

    def _equip_weapon(self, card: Card, start_pos=None):
        # When equipping a new weapon, animate any previous weapon+stack to discard
        # first, then animate the new weapon moving into the weapon slot.
        if self.equipped_weapon:
            prev_card = self.equipped_weapon.get("card")
            if prev_card is not None:
                try:
                    wrect = getattr(self, "weapon_rect", None)
                    start = wrect.topleft if wrect is not None else None
                    # enqueue previous weapon discard if it looks like a Card
                    if isinstance(prev_card, Card):
                        self._move_to_discard(prev_card, start)
                    else:
                        # fallback: only append if it actually looks like a Card
                        try:
                            if isinstance(prev_card, Card):
                                self.discard.append(prev_card)
                        except Exception:
                            pass
                except Exception:
                    try:
                        self.discard.append(prev_card)
                    except Exception:
                        pass
            # enqueue stacked monsters to discard as well
            if isinstance(self.equipped_weapon, dict):
                stack = list(self.equipped_weapon.get("stack", []))
            else:
                stack = []
            for m in stack:
                try:
                    # only move objects that look like Card instances
                    if isinstance(m, Card):
                        self._move_to_discard(m)
                    else:
                        # non-Card fallback: only append if it's actually a Card
                        try:
                            if isinstance(m, Card):
                                self.discard.append(m)
                        except Exception:
                            pass
                except Exception:
                    try:
                        self.discard.append(m)
                    except Exception:
                        pass
        # enqueue equip animation to move new weapon from start_pos (room) to weapon_pos
        layout = self._compute_layout()
        weapon_pos = layout.get("weapon_pos")
        sp = start_pos if start_pos is not None else getattr(self, "_last_weapon_pos", weapon_pos)
        try:
            anim = {"type": "equip", "card": card, "start": sp, "end": weapon_pos, "total": 14}
            self._enqueue_animation(anim)
        except Exception:
            # fallback: set immediately
            self.equipped_weapon = {"card": card, "stack": [], "last_monster": None}

    def _resolve_monster(self, card: Card, prefer_weapon: bool | None = None, start_pos=None):
        # choose behavior based on prefer_weapon flag
        monster_value = card.value
        if prefer_weapon is True:
            # force weapon
            if self.equipped_weapon:
                last = self.equipped_weapon.get("last_monster")
                # last_monster should be an int or None; guard against bad values
                if last is None or isinstance(last, int):
                    allowed = (last is None) or (monster_value <= last)
                else:
                    allowed = False
                if allowed:
                    weapon_value = self.equipped_weapon["card"].value
                    remaining = monster_value - weapon_value
                    damage = remaining if remaining > 0 else 0
                    self.health -= damage
                    # enqueue animation to move monster onto weapon stack
                    layout = self._compute_layout()
                    weapon_pos = layout.get("weapon_pos")
                    # prefer an explicit start_pos when provided (from face_card)
                    sp = start_pos
                    # choose reasonable start position from recent room rects if not provided
                    if sp is None:
                        try:
                            if hasattr(self, "room_rects") and self.room_rects:
                                sp = self.room_rects[0].topleft
                        except Exception:
                            sp = None
                    if sp is None:
                        sp = getattr(self, "_last_weapon_pos", weapon_pos)
                    try:
                        anim = {"type": "to_weapon", "card": card, "start": sp, "end": weapon_pos, "total": 12}
                        self._enqueue_animation(anim)
                    except Exception:
                        # fallback: append immediately (guard type)
                        try:
                            if isinstance(card, Card) and isinstance(self.equipped_weapon, dict):
                                self.equipped_weapon["stack"].append(card)
                                self.equipped_weapon["last_monster"] = monster_value
                        except Exception:
                            pass
                    # update last_monster even if animation pending
                    try:
                        self.equipped_weapon["last_monster"] = monster_value
                    except Exception:
                        pass
                    return {"action": "weapon_used", "damage": damage}
            # fallthrough to barehand if not allowed
        elif prefer_weapon is False:
            # force barehand
            self.health -= monster_value
            try:
                # animate + sound for discard
                # prefer to start the discard animation from the card's visual
                # slot when provided via start_pos; fall back to default otherwise
                self._move_to_discard(card, start_pos)
            except Exception:
                try:
                    if isinstance(card, Card):
                        self.discard.append(card)
                except Exception:
                    pass
            try:
                # play hit sound
                self._play_sfx("monsterHit")
            except Exception:
                pass
            return {"action": "barehand", "damage": monster_value}

        # prefer_weapon is None: auto behavior
        if self.equipped_weapon:
            last = self.equipped_weapon.get("last_monster")
            # last_monster should be an int or None; guard against bad values
            if last is None or isinstance(last, int):
                allowed = (last is None) or (monster_value <= last)
            else:
                allowed = False
            if allowed:
                weapon_value = self.equipped_weapon["card"].value
                remaining = monster_value - weapon_value
                damage = remaining if remaining > 0 else 0
                self.health -= damage
                # enqueue animation to move monster onto weapon stack
                layout = self._compute_layout()
                weapon_pos = layout.get("weapon_pos")
                # prefer an explicit start_pos when provided (from face_card)
                sp = start_pos
                # choose reasonable start position from recent room rects if not provided
                if sp is None:
                    try:
                        if hasattr(self, "room_rects") and self.room_rects:
                            sp = self.room_rects[0].topleft
                    except Exception:
                        sp = None
                if sp is None:
                    sp = getattr(self, "_last_weapon_pos", weapon_pos)
                try:
                    anim = {"type": "to_weapon", "card": card, "start": sp, "end": weapon_pos, "total": 12}
                    self._enqueue_animation(anim)
                except Exception:
                    try:
                        if isinstance(card, Card) and isinstance(self.equipped_weapon, dict):
                            self.equipped_weapon["stack"].append(card)
                            self.equipped_weapon["last_monster"] = monster_value
                    except Exception:
                        pass
                try:
                    if isinstance(self.equipped_weapon, dict):
                        self.equipped_weapon["last_monster"] = monster_value
                except Exception:
                    pass
                try:
                    self._play_sfx("monsterHit")
                except Exception:
                    pass
                return {"action": "weapon_used", "damage": damage}
        # otherwise fight barehanded
        self.health -= monster_value
        # when monster is discarded (barehanded), animate if possible
        try:
            # find a reasonable start position from room_rects if available
            # prefer explicit start_pos passed into resolver
            if start_pos is None:
                start_pos = None
                if hasattr(self, "room_rects"):
                    for r in getattr(self, "room_rects", []):
                        start_pos = r.topleft
                        break
        except Exception:
            start_pos = None
        if start_pos is not None:
            try:
                self._move_to_discard(card, start_pos)
            except Exception:
                try:
                    if isinstance(card, Card):
                        self.discard.append(card)
                except Exception:
                    pass
        else:
            try:
                self._move_to_discard(card)
            except Exception:
                try:
                    if isinstance(card, Card):
                        self.discard.append(card)
                except Exception:
                    pass
        return {"action": "barehand", "damage": monster_value}

    def is_game_over(self):
        return self.health <= 0 or (len(self.deck) == 0 and len(self.room) == 0)

    def compute_score(self):
        if self.health <= 0:
            # find remaining monsters in dungeon (deck + room)
            total = 0
            for c in self.deck.cards:
                if c.suit in ("clubs", "spades"):
                    total += c.value
            for c in self.room:
                if c.suit in ("clubs", "spades"):
                    total += c.value
            return self.health - total
        else:
            # finished dungeon
            if self.health == self.starting_health and self.last_potion_value:
                return self.health + self.last_potion_value
            return self.health

    # -- rendering / simple UI helpers --
    def render(self):
        # We'll draw everything into a virtual surface and scale that to the real display.
        surf = pygame.Surface((self.virtual_w, self.virtual_h))
        # tile background if available, otherwise fill with solid color
        tile = getattr(self, "_bg_tile", None)
        if tile is not None:
            tw, th = tile.get_size()
            for yy in range(0, self.virtual_h, th):
                for xx in range(0, self.virtual_w, tw):
                    surf.blit(tile, (xx, yy))
        else:
            surf.fill((24, 24, 24))
        # Health
        font = self.get_font(28)
        big = self.get_font(40)
        h_surf = big.render(f"Health: {self.health}", False, (220, 220, 220))
        surf.blit(h_surf, (16, 16))
        # (Removed: top-left dungeon/discard counts and weapon text per UI change)

        # Room display (render card art when available)
        card_w, card_h = self.card_size
        spacing = 16
        # center four room cards horizontally within the virtual surface
        total_width = card_w * 4 + spacing * 3
        x_start = (self.virtual_w - total_width) // 2
        # compute a dynamic vertical position for the room so cards sit lower
        # and avoid overlapping the weapon at the top or the UI at the bottom.
        sw, sh = surf.get_size()
        # weapon is placed near the top-right; reserve that space
        # nudge weapon and discard slightly closer to the right edge
        right_pad = self.right_pad
        wx = sw - card_w - right_pad
        wy = 16
        # prefer to center room around mid-screen but nudge it down by 40px
        preferred_y = self.virtual_h // 2 - (card_h // 2) + 40
        min_y = wy + card_h + 16
        max_y = self.virtual_h - card_h - 160
        # clamp preferred to available range
        y_room = max(min_y, min(preferred_y, max_y))
        x = x_start
        y = y_room

        self.room_rects = []
        for i, c in enumerate(self.room):
            rect = pygame.Rect(x, y, card_w, card_h)
            pygame.draw.rect(surf, (50, 50, 50), rect)
            pygame.draw.rect(surf, (120, 120, 120), rect, 2)
            # If this card was just appended and has a pending draw animation,
            # don't render its artwork at the slot yet — the animation will show
            # it moving from the deck to this position.
            pending = False
            try:
                pending = hasattr(self, "_pending_draw_ids") and (id(c) in self._pending_draw_ids)
            except Exception:
                pending = False
            if pending:
                # draw a subtle placeholder (empty slot) and skip art/text
                pygame.draw.rect(surf, (30, 30, 30), rect)
            else:
                art_surf = self.art.get_card(c.suit, c.rank, size=(card_w, card_h)) if self.art else None
                if art_surf:
                    surf.blit(art_surf, rect.topleft)
                else:
                    txt = font.render(f"{i+1}: {c.rank} {c.suit}", False, (240, 240, 240))
                    surf.blit(txt, (x + 8, y + 8))
            self.room_rects.append(rect)
            x += card_w + spacing

        # Skip button (replaces keyboard hint). Use spritesheet-backed NinePatchButton
        bw = 160
        bh = 44
        bx = 16
        by = max(520, self.virtual_h - 120)
        skip_enabled = (len(self.room) >= 4) and (not self.previous_avoided) and (not getattr(self, "room_interacted", False))
        # Attempt to draw from atlas + mapping (best-effort); fall back to plain rect
        skip_rect = pygame.Rect(bx, by, bw, bh)
        # Prefer atlas-backed NinePatchButton when available, but use cached button
        btn = None
        try:
            btn = self._get_or_create_ninepatch_button("skip_room", "button_normal", (bx, by), (bw, bh), "Skip Room", font)
        except Exception:
            btn = None
        if btn is not None:
            btn.draw(surf)
            skip_rect = btn.rect
            self.ui_buttons["skip_room"] = (skip_rect, skip_enabled)
        else:
            color = (40, 120, 40) if skip_enabled else (70, 70, 70)
            pygame.draw.rect(surf, color, skip_rect)
            lbl = font.render("Skip Room", False, (255, 255, 255))
            surf.blit(lbl, (bx + 12, by + (bh - lbl.get_height()) // 2))
            self.ui_buttons["skip_room"] = (skip_rect, skip_enabled)

        # Draw equipped weapon art and stacked monsters
        sw, sh = surf.get_size()
        wx = sw - card_w - right_pad
        wy = 16
        self.weapon_rect = pygame.Rect(wx, wy, card_w, card_h)
        try:
            self._last_weapon_pos = self.weapon_rect.topleft
        except Exception:
            self._last_weapon_pos = (wx, wy)
        if self.equipped_weapon:
            wc = self.equipped_weapon["card"]
            w_art = self.art.get_card(wc.suit, wc.rank, size=(card_w, card_h)) if self.art else None
            if w_art:
                surf.blit(w_art, (wx, wy))
            else:
                wtxt = font.render(f"{wc.rank} {wc.suit}", False, (220, 220, 220))
                pygame.draw.rect(surf, (40, 40, 40), self.weapon_rect)
                surf.blit(wtxt, (wx + 8, wy + 8))

            # draw stacked monsters on top of weapon art
            stack = self.equipped_weapon.get("stack", [])
            small_w = int(card_w * 0.35)
            small_h = int(card_h * 0.35)
            sx = wx + 8
            sy = wy + card_h - small_h - 8
            for idx, m in enumerate(stack):
                m_art = self.art.get_card(m.suit, m.rank, size=(small_w, small_h)) if self.art else None
                offy = sy - (idx * (small_h // 3))
                if m_art:
                    surf.blit(m_art, (sx, offy))
                else:
                    mtxt = font.render(f"{m.rank}", False, (240, 240, 240))
                    pygame.draw.rect(surf, (60, 60, 60), (sx, offy, small_w, small_h))
                    surf.blit(mtxt, (sx + 4, offy + 4))
        # Draw Deck (face-down) and Discard (last-interacted card)
        # Place the deck centered horizontally above the room cards
        deck_x = x_start + (total_width - card_w) // 2
        deck_y = y_room - card_h - 16
        deck_rect = pygame.Rect(deck_x, deck_y, card_w, card_h)
        # deck backside (face-down)
        back = getattr(self, "_backside", None)
        if back is not None:
            try:
                surf.blit(back, deck_rect.topleft)
            except Exception:
                pygame.draw.rect(surf, (30, 30, 30), deck_rect)
        else:
            pygame.draw.rect(surf, (30, 30, 30), deck_rect)
            pygame.draw.rect(surf, (100, 100, 100), deck_rect, 2)

        # overlay deck count to the right of the deck
        cnt_s = font.render(str(len(self.deck)), False, (220, 220, 220))
        cnt_pos = (deck_rect.right + 8, deck_rect.top + (card_h - cnt_s.get_height()) // 2)
        surf.blit(cnt_s, cnt_pos)

        # discard: Prefer the most recent actually-discarded card (from
        # self.discard) so that a card only appears here after the discard
        # animation has completed. Fall back to the last-interaction history
        # if nothing has been discarded yet.
        last = None
        try:
            if getattr(self, "discard", None):
                for c in reversed(self.discard):
                    if self.equipped_weapon and c == self.equipped_weapon.get("card"):
                        continue
                    last = c
                    break
        except Exception:
            last = None

        if last is None:
            # If there is a discard animation in-flight (active or queued)
            # for a given card, avoid showing that card from the interaction
            # history as the discard visual — it will appear in `self.discard`
            # once the animation completes. Build a set of card ids that are
            # currently animating to discard and skip them when falling back
            # to interaction history.
            animating_ids = set()
            try:
                a = getattr(self, "_active_anim", None)
                if a and a.get("type") == "discard" and a.get("card") is not None:
                    animating_ids.add(id(a.get("card")))
            except Exception:
                pass
            try:
                for a in getattr(self, "_anim_queue", ()):  # queued animations
                    if a and a.get("type") == "discard" and a.get("card") is not None:
                        animating_ids.add(id(a.get("card")))
            except Exception:
                pass

            for c in reversed(getattr(self, "_interaction_history", [])):
                if self.equipped_weapon and c == self.equipped_weapon.get("card"):
                    continue
                try:
                    if id(c) in animating_ids:
                        # skip any card that is currently animating into discard
                        continue
                except Exception:
                    pass
                last = c
                break

        # place discard pile at bottom-right of the gameplay area (virtual surface)
        pad = self.right_pad
        discard_x = self.virtual_w - card_w - pad
        discard_y = self.virtual_h - card_h - pad
        discard_rect = pygame.Rect(discard_x, discard_y, card_w, card_h)
        if last is not None:
            d_art = self.art.get_card(last.suit, last.rank, size=(card_w, card_h)) if self.art else None
            if d_art:
                surf.blit(d_art, discard_rect.topleft)
            else:
                pygame.draw.rect(surf, (60, 60, 60), discard_rect)
                lbl = font.render(f"{last.rank} {last.suit}", False, (240, 240, 240))
                surf.blit(lbl, (discard_rect.left + 6, discard_rect.top + 6))
        else:
            # show empty discard slot
            pygame.draw.rect(surf, (24, 24, 24), discard_rect)
            pygame.draw.rect(surf, (80, 80, 80), discard_rect, 2)

        # draw active animation (queued animations are processed sequentially)
        anim = getattr(self, "_active_anim", None)
        if anim:
            frames_left = anim.get("frames_left", anim.get("total", 1))
            total = anim.get("total", 1)
            t = 1.0 - (frames_left / total) if total else 1.0
            sx, sy = anim.get("start", (0, 0))
            ex, ey = anim.get("end", (sx, sy))
            # simple ease-out interpolation
            ease = 1 - (1 - t) * (1 - t)
            ix = int(sx + (ex - sx) * ease)
            iy = int(sy + (ey - sy) * ease)
            try:
                surf_to_draw = anim.get("surf")
                if surf_to_draw is None and anim.get("card") and self.art:
                    surf_to_draw = self.art.get_card(anim["card"].suit, anim["card"].rank, size=self.card_size)
                if surf_to_draw is None:
                    cw, ch = self.card_size
                    surf_to_draw = pygame.Surface((cw, ch))
                    surf_to_draw.fill((60, 60, 60))
                surf.blit(surf_to_draw, (ix, iy))
            except Exception:
                pass
            anim["frames_left"] = frames_left - 1
            if anim["frames_left"] <= 0:
                try:
                    self._on_animation_complete(anim)
                except Exception:
                    # ensure we clear active anim on error
                    self._active_anim = None

        # Draw pause overlay and controls if paused
        if getattr(self, "paused", False):
            overlay = pygame.Surface((self.virtual_w, self.virtual_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surf.blit(overlay, (0, 0))
            # central pause menu (draw framed window if atlas available)
            menu_w = 360
            menu_h = 260
            mx = (self.virtual_w - menu_w) // 2
            my = (self.virtual_h - menu_h) // 2
            # Try to draw a window frame from atlas
            try:
                frame_btn = self._get_or_create_ninepatch_button("pause_frame", "window_frame", (mx - 8, my - 8), (menu_w + 16, menu_h + 16), "", font)
                if frame_btn:
                    frame_btn.draw(surf)
                else:
                    pygame.draw.rect(surf, (30, 30, 30), (mx, my, menu_w, menu_h))
                    pygame.draw.rect(surf, (140, 140, 140), (mx, my, menu_w, menu_h), 2)
            except Exception:
                pygame.draw.rect(surf, (30, 30, 30), (mx, my, menu_w, menu_h))
                pygame.draw.rect(surf, (140, 140, 140), (mx, my, menu_w, menu_h), 2)
            title = big.render("Paused", False, (240, 240, 240))
            surf.blit(title, (mx + (menu_w - title.get_width()) // 2, my + 14))

            btn_w = 260
            btn_h = 44
            btn_x = mx + (menu_w - btn_w) // 2
            btn_y = my + 64
            # Resume / Settings / Main Menu - try to use atlas-backed buttons
            # We'll try to use the same 'button_normal' tile for all, rendering text per-button.
            # Use cached atlas-backed buttons where possible
            resume_btn = self._get_or_create_ninepatch_button("pause_resume", "button_normal", (btn_x, btn_y), (btn_w, btn_h), "Resume", font)
            if resume_btn:
                resume_btn.draw(surf)
                resume_rect = resume_btn.rect
            else:
                resume_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
                pygame.draw.rect(surf, (50, 120, 50), resume_rect)
                r_lbl = font.render("Resume", False, (255, 255, 255))
                surf.blit(r_lbl, (resume_rect.left + (btn_w - r_lbl.get_width()) // 2, resume_rect.top + 10))

            # Settings
            btn_y += btn_h + 12
            settings_btn = self._get_or_create_ninepatch_button("pause_settings", "button_normal", (btn_x, btn_y), (btn_w, btn_h), "Settings", font)
            if settings_btn:
                settings_btn.draw(surf)
                settings_rect = settings_btn.rect
            else:
                settings_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
                pygame.draw.rect(surf, (70, 70, 120), settings_rect)
                s_lbl = font.render("Settings", False, (255, 255, 255))
                surf.blit(s_lbl, (settings_rect.left + (btn_w - s_lbl.get_width()) // 2, settings_rect.top + 10))

            # Main Menu
            btn_y += btn_h + 12
            main_btn = self._get_or_create_ninepatch_button("pause_mainmenu", "button_normal", (btn_x, btn_y), (btn_w, btn_h), "Main Menu", font)
            if main_btn:
                main_btn.draw(surf)
                main_rect = main_btn.rect
            else:
                main_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
                pygame.draw.rect(surf, (140, 40, 40), main_rect)
                m_lbl = font.render("Main Menu", False, (255, 255, 255))
                surf.blit(m_lbl, (main_rect.left + (btn_w - m_lbl.get_width()) // 2, main_rect.top + 10))

            # expose pause buttons for input handling
            self.ui_buttons["pause_resume"] = (resume_rect, True)
            self.ui_buttons["pause_settings"] = (settings_rect, True)
            self.ui_buttons["pause_mainmenu"] = (main_rect, True)

        # If in settings subpage (simple stub), draw page and back button
        if getattr(self, "in_settings", False):
            s_overlay = pygame.Surface((self.virtual_w, self.virtual_h), pygame.SRCALPHA)
            s_overlay.fill((0, 0, 0, 200))
            surf.blit(s_overlay, (0, 0))
            sw = 520
            sh = 320
            sx = (self.virtual_w - sw) // 2
            sy = (self.virtual_h - sh) // 2
            pygame.draw.rect(surf, (28, 28, 28), (sx, sy, sw, sh))
            pygame.draw.rect(surf, (140, 140, 140), (sx, sy, sw, sh), 2)
            t = big.render("Settings", False, (240, 240, 240))
            surf.blit(t, (sx + (sw - t.get_width()) // 2, sy + 16))
            # Back button
            back_rect = pygame.Rect(sx + (sw - 200) // 2, sy + sh - 70, 200, 48)
            pygame.draw.rect(surf, (90, 90, 90), back_rect)
            btxt = font.render("Back", False, (255, 255, 255))
            surf.blit(btxt, (back_rect.left + (200 - btxt.get_width()) // 2, back_rect.top + 10))
            self.ui_buttons["settings_back"] = (back_rect, True)

        # If there's a pending combat choice, draw simple buttons
        if self.pending_combat:
            bw = 180
            bh = 44
            bx = (self.virtual_w - (bw * 2 + 16)) // 2
            by = self.virtual_h - bh - 24
            monster = self.pending_combat.get("card")
            allowed_weapon = False
            if not monster:
                allowed_weapon = False
            elif self.equipped_weapon:
                last = self.equipped_weapon.get("last_monster")
                if last is None:
                    allowed_weapon = True
                else:
                    allowed_weapon = (monster.value <= last)

            use_rect = pygame.Rect(bx, by, bw, bh)
            bare_rect = pygame.Rect(bx + bw + 16, by, bw, bh)
            # Create cached buttons if atlas is available
            btn_use = self._get_or_create_ninepatch_button("pending_use", "button_normal", (use_rect.left, use_rect.top), (bw, bh), "Use Weapon", font)
            btn_bare = self._get_or_create_ninepatch_button("pending_bare", "button_normal", (bare_rect.left, bare_rect.top), (bw, bh), "Barehand", font)
            if btn_use and btn_bare:
                # draw them and update rects
                # visually disable the 'use' button if not allowed by tinting fallback is not implemented; keep enabled flag
                btn_use.draw(surf)
                use_rect = btn_use.rect
                btn_bare.draw(surf)
                bare_rect = btn_bare.rect
            else:
                color = (40, 120, 40) if allowed_weapon else (70, 70, 70)
                pygame.draw.rect(surf, color, use_rect)
                u_txt = font.render("Use Weapon", False, (255, 255, 255))
                surf.blit(u_txt, (bx + 18, by + 12))
                pygame.draw.rect(surf, (120, 40, 40), bare_rect)
                b_txt = font.render("Barehand", False, (255, 255, 255))
                surf.blit(b_txt, (bx + bw + 34, by + 12))

            self.ui_buttons["use_weapon"] = (use_rect, allowed_weapon)
            self.ui_buttons["barehand"] = (bare_rect, True)

        # scale the virtual surface to the actual display using integer scaling when possible
        disp_w, disp_h = self.display.get_size()
        scale = min(disp_w // self.virtual_w, disp_h // self.virtual_h)
        if scale >= 1:
            scaled = pygame.transform.scale(surf, (self.virtual_w * scale, self.virtual_h * scale))
            dx = (disp_w - scaled.get_width()) // 2
            dy = (disp_h - scaled.get_height()) // 2
            # Fill the display background by tiling the (optionally scaled) background
            # tile so gutters show the same pattern as the game area instead of black.
            tile = getattr(self, "_bg_tile", None)
            if tile is not None:
                # help static analyzers: tile is now definitely a Surface
                assert tile is not None
                tw, th = tile.get_size()
                # use cached scaled tile for this integer scale
                cached = self._bg_tile_scaled_cache.get(scale)
                if cached is None:
                    try:
                        cached = pygame.transform.scale(tile, (tw * scale, th * scale))
                    except Exception:
                        cached = tile
                    self._bg_tile_scaled_cache[scale] = cached
                ttw, tth = cached.get_size()
                # Align the display tiling with the scaled game area's origin (dx, dy).
                # This ensures the pattern shown in the gutters matches the game area
                # so there are no visible seams where the letterboxed game sits on top
                # of the tiled background.
                # Compute the first tile origin so that one of the tile origins falls
                # exactly at (dx, dy) modulo tile size. Then start tiling from <= 0
                # so the whole display is covered.
                # Offset within a tile for the game's top-left corner
                off_x = dx % ttw
                off_y = dy % tth
                start_x = off_x
                start_y = off_y
                if start_x > 0:
                    start_x -= ttw
                if start_y > 0:
                    start_y -= tth
                # Tile across the whole display starting from computed start positions
                for yy in range(start_y, disp_h, tth):
                    for xx in range(start_x, disp_w, ttw):
                        self.display.blit(cached, (xx, yy))
            else:
                self.display.fill((0, 0, 0))
            # then blit the scaled game area centered
            self.display.blit(scaled, (dx, dy))
            # store mapping info for input handling
            self._last_scale = scale
            self._last_offset = (dx, dy)
        else:
            # screen smaller than virtual -> fallback to smooth scaling to fit
            scaled = pygame.transform.smoothscale(surf, (disp_w, disp_h))
            self.display.blit(scaled, (0, 0))
            self._last_scale = None
            self._last_offset = (0, 0)

    def run(self):
        # main loop for the game
        running = True
        # prepare first room
        try:
            self.prepare_room()
        except Exception:
            pass
        try:
            self._reset_used_potion_flag("start_run")
        except Exception:
            try:
                self._reset_used_potion_flag("start_run_fallback")
            except Exception:
                try:
                    self.used_potion_this_turn = False
                except Exception:
                    pass
        while running:
            self.clock.tick(30)
            for ev in pygame.event.get():
                # Always allow window close
                if ev.type == pygame.QUIT:
                    return "quit"

                # If an animation is active or queued, lock input unless the
                # game is paused. Allow Q to return to menu and ESC to open
                # the pause menu even while animating.
                animating = (getattr(self, "_active_anim", None) is not None) or bool(getattr(self, "_anim_queue", None))
                if animating and not getattr(self, "paused", False):
                    if ev.type == pygame.KEYDOWN and ev.key == pygame.K_q:
                        return "menu"
                    # allow ESC to be handled so player can pause; otherwise ignore
                    if not (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                        continue

                if ev.type == pygame.KEYDOWN:
                    # If paused, handle pause-specific keys
                    if getattr(self, "paused", False):
                        if ev.key == pygame.K_q:
                            return "menu"
                        if ev.key == pygame.K_ESCAPE:
                            # close settings or resume
                            if getattr(self, "in_settings", False):
                                self.in_settings = False
                            else:
                                self.paused = False
                        # ignore other keys while paused
                        continue

                    # Q returns to the menu. Do NOT map Escape to quitting.
                    if ev.key == pygame.K_q:
                        return "menu"
                    if ev.key == pygame.K_ESCAPE:
                        # toggle pause (open pause menu)
                        self.paused = not getattr(self, "paused", False)
                        # if opening pause, clear any settings view
                        if self.paused:
                            self.in_settings = False
                        continue
                    # 'S' save removed — persistence disabled
                    if ev.key == pygame.K_a:
                        # avoid -- only allowed if the player has not yet interacted
                        # with any card in this room.
                        try:
                            if getattr(self, "room_interacted", False):
                                # ignore avoid when the player already interacted
                                pass
                            else:
                                self.avoid_room()
                                # refill next room
                                self.prepare_room()
                                self._reset_used_potion_flag("key_a_avoid")
                        except Exception:
                            # defensive: fall back to allowing avoid
                            try:
                                self.avoid_room()
                                self.prepare_room()
                                self._reset_used_potion_flag("key_a_avoid_fallback")
                            except Exception:
                                pass
                    if ev.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                        idx = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}[ev.key]
                        if idx < len(self.room):
                            start = None
                            try:
                                if idx < len(self.room_rects):
                                    start = self.room_rects[idx].topleft
                            except Exception:
                                start = None
                            # we don't need the returned value here; call for side-effects
                            self.face_card(idx, start_pos=start)
                            # after facing 3 cards in a turn, fill up for next turn
                            # simplistic approach: if room has exactly 1 card left then end turn
                            # reset potion usage at start of next turn
                            if len(self.room) == 1:
                                self.prepare_room()
                                self._reset_used_potion_flag("key_face_refill")
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    mx, my = ev.pos
                    # map display coords to virtual coords using last render mapping
                    disp_w, disp_h = self.display.get_size()
                    scale = getattr(self, "_last_scale", None)
                    dx, dy = getattr(self, "_last_offset", (0, 0))
                    if scale is None:
                        # scaled to fit; map proportionally
                        if disp_w and disp_h:
                            vx = int(mx * self.virtual_w / disp_w)
                            vy = int(my * self.virtual_h / disp_h)
                        else:
                            vx, vy = mx, my
                    else:
                        # click must be inside the letterboxed scaled region
                        if mx < dx or my < dy or mx >= dx + self.virtual_w * scale or my >= dy + self.virtual_h * scale:
                            continue
                        vx = (mx - dx) // scale
                        vy = (my - dy) // scale

                        # If the pause overlay is open, let pause/settings buttons handle clicks first
                        if getattr(self, "paused", False):
                            # If in settings subpage, check the settings back button
                            if getattr(self, "in_settings", False):
                                back_info = self.ui_buttons.get("settings_back")
                                if back_info:
                                    back_rect, _ = back_info
                                    if back_rect.collidepoint(vx, vy):
                                        self.in_settings = False
                                        continue
                            else:
                                # pause menu buttons
                                resume_info = self.ui_buttons.get("pause_resume")
                                settings_info = self.ui_buttons.get("pause_settings")
                                main_info = self.ui_buttons.get("pause_mainmenu")
                                if resume_info:
                                    rrect, _ = resume_info
                                    if rrect.collidepoint(vx, vy):
                                        self.paused = False
                                        self.in_settings = False
                                        continue
                                if settings_info:
                                    srect, _ = settings_info
                                    if srect.collidepoint(vx, vy):
                                        self.in_settings = True
                                        continue
                                if main_info:
                                    mrect, _ = main_info
                                    if mrect.collidepoint(vx, vy):
                                        return "menu"
                                # clicks while paused that don't hit menu are ignored
                                continue

                        # check skip button before any room interactions
                        skip_info = self.ui_buttons.get("skip_room")
                        if skip_info:
                            srect, senabled = skip_info
                            if srect.collidepoint(vx, vy) and senabled:
                                try:
                                    self.avoid_room()
                                    self.prepare_room()
                                    self._reset_used_potion_flag("mouse_skip_avoid")
                                except Exception:
                                    pass
                                continue

                        # if there's a pending combat, check buttons first (buttons are in virtual coords)
                        if self.pending_combat:
                            use_info = self.ui_buttons.get("use_weapon")
                            bare_info = self.ui_buttons.get("barehand")
                            if use_info:
                                use_rect, allowed = use_info
                                if use_rect.collidepoint(vx, vy) and allowed:
                                    idx = self.pending_combat.get("index")
                                    start = None
                                    try:
                                        if idx is not None and idx < len(self.room_rects):
                                            start = self.room_rects[idx].topleft
                                    except Exception:
                                        start = None
                                    self.face_card(idx, prefer_weapon=True, start_pos=start)
                                    self.pending_combat = None
                                    if len(self.room) == 1:
                                        self.prepare_room()
                                        self._reset_used_potion_flag("pending_use_refill")
                                    continue
                            if bare_info:
                                bare_rect, _ = bare_info
                                if bare_rect.collidepoint(vx, vy):
                                    idx = self.pending_combat.get("index")
                                    start = None
                                    try:
                                        if idx is not None and idx < len(self.room_rects):
                                            start = self.room_rects[idx].topleft
                                    except Exception:
                                        start = None
                                    self.face_card(idx, prefer_weapon=False, start_pos=start)
                                    self.pending_combat = None
                                    if len(self.room) == 1:
                                        self.prepare_room()
                                        self._reset_used_potion_flag("pending_bare_refill")
                                    continue

                    # otherwise check clicks on room cards (virtual coords)
                    for i, r in enumerate(self.room_rects):
                        if r.collidepoint(vx, vy):
                            if i >= len(self.room):
                                break
                            card = self.room[i]
                            # Monster => may need choice
                            if card.suit in ("clubs", "spades"):
                                # check if weapon option exists/allowed
                                allowed_weapon = False
                                if self.equipped_weapon:
                                    last = self.equipped_weapon.get("last_monster")
                                    if last is None:
                                        allowed_weapon = True
                                    else:
                                        allowed_weapon = (card.value <= last)
                                # if both options possible, prompt
                                if self.equipped_weapon and allowed_weapon:
                                    # record that the player interacted with the room by
                                    # clicking the card (now they may not avoid).
                                    try:
                                        self.room_interacted = True
                                    except Exception:
                                        pass
                                    self.pending_combat = {"index": i, "card": card}
                                else:
                                    # resolve immediately, force barehand or weapon
                                    if self.equipped_weapon and allowed_weapon:
                                        start = None
                                        try:
                                            if i < len(self.room_rects):
                                                start = self.room_rects[i].topleft
                                        except Exception:
                                            start = None
                                        self.face_card(i, start_pos=start)
                                    else:
                                        # no allowed weapon -> barehand
                                        start = None
                                        try:
                                            if i < len(self.room_rects):
                                                start = self.room_rects[i].topleft
                                        except Exception:
                                            start = None
                                        self.face_card(i, prefer_weapon=False, start_pos=start)
                                # after any face action that leaves 1 card, refill
                                if len(self.room) == 1:
                                    self.prepare_room()
                                    self._reset_used_potion_flag("mouse_face_refill")
                            else:
                                # non-monster: immediate action
                                start = None
                                try:
                                    if i < len(self.room_rects):
                                        start = self.room_rects[i].topleft
                                except Exception:
                                    start = None
                                self.face_card(i, start_pos=start)
                                if len(self.room) == 1:
                                    self.prepare_room()
                                    self._reset_used_potion_flag("mouse_face_refill_nonmonster")
                            break

            self.render()
            pygame.display.flip()

            if self.is_game_over():
                score = self.compute_score()
                # show final message for a moment and return to menu
                font = self.get_font(48)
                msg = font.render(f"Game Over - Score: {score}", False, (255, 200, 80))
                # draw message directly to the real display (centered)
                disp_w, disp_h = self.display.get_size()
                mx = disp_w // 2 - msg.get_width() // 2
                my = disp_h // 2 - msg.get_height() // 2
                # semi-transparent overlay
                overlay = pygame.Surface((disp_w, disp_h), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 160))
                self.display.blit(overlay, (0, 0))
                self.display.blit(msg, (mx, my))
                pygame.display.flip()
                pygame.time.wait(2500)
                return "menu"
