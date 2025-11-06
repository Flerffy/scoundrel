import pygame
from pathlib import Path
from typing import Any, cast
from .ui import Menu
from .engine import GameEngine

def main():
    try:
        print("[scoundrel.main] entered", flush=True)
    except Exception:
        pass
    # Improve audio reliability on some systems by pre-initializing the mixer
    # before calling pygame.init(). This sets a sensible buffer/format for sound.
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
    except Exception:
        pass
    pygame.init()
    # Ensure the mixer is actually initialized. On some systems pre_init may not
    # result in an initialized mixer until after pygame.init() — try to init it
    # explicitly if needed so music.load/play calls work reliably.
    try:
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception:
                # if mixer init fails, continue without sound but print a hint
                try:
                    print("Warning: pygame.mixer failed to initialize; music will be disabled")
                except Exception:
                    pass
    except Exception:
        pass
    # helper to reliably obtain apply_music_volume from the package (best-effort)
    def _get_apply_music_volume():
        try:
            import importlib
            mod = None
            try:
                if __package__:
                    try:
                        mod = importlib.import_module(f"{__package__}.utils.audio_settings")
                    except Exception:
                        mod = None
                if mod is None:
                    try:
                        mod = importlib.import_module('scoundrel.utils.audio_settings')
                    except Exception:
                        mod = None
            except Exception:
                mod = None
            if mod is not None and hasattr(mod, 'apply_music_volume'):
                return getattr(mod, 'apply_music_volume')
        except Exception:
            pass
        return None

    def _apply_all_audio_settings():
        """Import audio_settings under likely names and call load/apply on each

        This avoids a problem where the same logical module is imported under
        different names (e.g. 'scoundrel.utils.audio_settings' vs
        'utils.audio_settings') which leads to multiple module objects with
        different internal state. We attempt both names and call
        load_settings()/apply_music_volume() on any module we find.
        """
        try:
            import importlib, sys
            names = [f"{__package__}.utils.audio_settings" if __package__ else None, "scoundrel.utils.audio_settings", "utils.audio_settings"]
            seen = set()
            for nm in names:
                if not nm:
                    continue
                if nm in seen:
                    continue
                seen.add(nm)
                try:
                    mod = importlib.import_module(nm)
                except Exception:
                    # if import fails, try to find a loaded module with that short name
                    mod = sys.modules.get(nm)
                if not mod:
                    continue
                try:
                    if hasattr(mod, "load_settings"):
                        try:
                            mod.load_settings()
                        except Exception:
                            pass
                    if hasattr(mod, "apply_music_volume"):
                        try:
                            mod.apply_music_volume()
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    # attempt to apply persisted audio settings now (best-effort)
    try:
        _apply_all_audio_settings()
    except Exception:
        pass


    def _set_music_volume_from_settings():
        """Best-effort: read persisted settings and set pygame.mixer.music volume directly.

        This bypasses potential duplicate-module/import issues by computing
        master*bgm from the settings file or the audio_settings module and
        calling pygame.mixer.music.set_volume(value).
        """
        try:
            import importlib, json
            mod = None
            try:
                if __package__:
                    try:
                        mod = importlib.import_module(f"{__package__}.utils.audio_settings")
                    except Exception:
                        mod = None
                if mod is None:
                    try:
                        mod = importlib.import_module("scoundrel.utils.audio_settings")
                    except Exception:
                        try:
                            mod = importlib.import_module("utils.audio_settings")
                        except Exception:
                            mod = None
            except Exception:
                mod = None

            vol = None
            if mod is not None:
                try:
                    if hasattr(mod, "load_settings"):
                        try:
                            mod.load_settings()
                        except Exception:
                            pass
                    if hasattr(mod, "get_master") and hasattr(mod, "get_bgm"):
                        vol = float(mod.get_master()) * float(mod.get_bgm())
                    elif hasattr(mod, "get_bgm"):
                        vol = float(mod.get_bgm())
                except Exception:
                    vol = None

            # fallback: try reading SETTINGS_FILE from the module if available
            if vol is None and mod is not None and hasattr(mod, "SETTINGS_FILE"):
                try:
                    raw = json.loads(getattr(mod, "SETTINGS_FILE").read_text(encoding="utf-8"))
                    vol = float(raw.get("master", 1.0)) * float(raw.get("bgm", 0.5))
                except Exception:
                    vol = None

            if vol is not None:
                try:
                    pygame.mixer.music.set_volume(vol)
                except Exception:
                    pass
        except Exception:
            pass
    screen = pygame.display.set_mode((960, 640))
    try:
        print("[scoundrel.main] creating display", flush=True)
    except Exception:
        pass
    screen = pygame.display.set_mode((960, 640))
    try:
        print(f"[scoundrel.main] display created: {screen}", flush=True)
    except Exception:
        pass
    menu = cast(Any, Menu(screen, title="Scoundrel"))
    try:
        print("[scoundrel.main] Menu instantiated", flush=True)
    except Exception:
        pass
    def _assets_base():
        """Return the base folder where package assets live.

        Handles both development layout (filesystem beside the package)
        and PyInstaller onefile/onedir extraction (sys._MEIPASS).
        """
        try:
            import sys
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                # our --add-data used the destination 'scoundrel/assets', so
                # assets will be under _MEIPASS/scoundrel/assets
                return Path(meipass) / "scoundrel"
        except Exception:
            pass
        return Path(__file__).resolve().parents[1]


    def _start_menu_music():
        """Load and play the menu BGM (best-effort). Safe to call multiple times.

        This central helper ensures the same behavior is used when the menu is
        first shown and when returning to the menu after playing a game.
        """
    try:
        bgm_dir = _assets_base() / "assets" / "bgm"
        menu_music = bgm_dir / "MenuMusic.wav"
        if not menu_music.exists():
            return
        try:
            # double-check mixer availability before attempting to load/play
            if not pygame.mixer.get_init():
                try:
                    pygame.mixer.init()
                except Exception:
                    pass
            pygame.mixer.music.load(str(menu_music))
            try:
                print(f"Loaded menu music: {menu_music}")
            except Exception:
                pass
            # start playback and (re)apply persisted volumes
            try:
                pygame.mixer.music.play(-1)
                _apply_all_audio_settings()
                _set_music_volume_from_settings()
            except Exception:
                try:
                    pygame.mixer.music.play(-1)
                except Exception:
                    pass
        except Exception:
            try:
                print(f"Failed to load menu music: {menu_music}")
            except Exception:
                pass
    except Exception:
        pass

    # start menu music initially
    _start_menu_music()

    while True:
        # run the menu and handle actions; menu.run() should return action strings like "new", "settings", "quit" or None
        try:
            try:
                print("[scoundrel.main] entering menu.run()", flush=True)
            except Exception:
                pass
            action = menu.run()
            try:
                print(f"[scoundrel.main] menu.run() returned: {action}", flush=True)
            except Exception:
                pass
        except Exception:
            break

        if action is None or action == "quit":
            break

        if action == "new":
            # stop menu music and play game music on loop
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            try:
                bgm_dir = _assets_base() / "assets" / "bgm"
                game_music = bgm_dir / "GameMusic.wav"
                if game_music.exists():
                    try:
                        pygame.mixer.music.load(str(game_music))
                        try:
                            pygame.mixer.music.play(-1)
                            _apply_all_audio_settings()
                            _set_music_volume_from_settings()
                        except Exception:
                            try:
                                pygame.mixer.music.play(-1)
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass

            game = GameEngine(screen)
            result = game.run()
            # stop game music and return to menu
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            # ensure menu music restarts when we return
            try:
                _start_menu_music()
            except Exception:
                pass
            # loop back to menu
            continue

        if action == "settings":
            # show settings dialog from the menu, then return to menu
            try:
                if hasattr(menu, "_show_settings"):
                    try:
                        menu._show_settings()
                    except Exception:
                        pass
            except Exception:
                pass
            # if settings changed volumes or music, make sure menu music is playing
            try:
                if not pygame.mixer.music.get_busy():
                    try:
                        _start_menu_music()
                    except Exception:
                        pass
                else:
                    # re-apply volumes in case they changed
                    try:
                        _apply_all_audio_settings()
                        _set_music_volume_from_settings()
                    except Exception:
                        pass
            except Exception:
                pass
            continue

if __name__ == "__main__":
    main()