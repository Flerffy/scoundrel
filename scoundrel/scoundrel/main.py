import pygame
from pathlib import Path
from typing import Any, cast
from .ui import Menu
from .engine import GameEngine

def main():
    # Improve audio reliability on some systems by pre-initializing the mixer
    # before calling pygame.init(). This sets a sensible buffer/format for sound.
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
    except Exception:
        pass
    pygame.init()
    # apply persisted audio settings (best-effort)
    try:
        import importlib
        apply_music_volume = None
        try:
            # prefer package-qualified import when possible to avoid unresolved leading-dot imports
            if __package__:
                try:
                    mod = importlib.import_module(f"{__package__}.utils.audio_settings")
                except Exception:
                    mod = None
            else:
                # fallback to absolute import when running as a script
                try:
                    mod = importlib.import_module('scoundrel.utils.audio_settings')
                except Exception:
                    mod = None
        except Exception:
            mod = None
        if mod is not None and hasattr(mod, 'apply_music_volume'):
            apply_music_volume = getattr(mod, 'apply_music_volume')
        if apply_music_volume is not None:
            try:
                apply_music_volume()
            except Exception:
                pass
    except Exception:
        pass
    screen = pygame.display.set_mode((960, 640))
    menu = cast(Any, Menu(screen, title="Scoundrel"))
    # try to play menu music on loop (best-effort)
    try:
        bgm_dir = Path(__file__).resolve().parents[1] / "assets" / "bgm"
        menu_music = bgm_dir / "MenuMusic.wav"
        if menu_music.exists():
            try:
                pygame.mixer.music.load(str(menu_music))
                # do not override persisted volume here; apply persisted music volume
                try:
                    from .utils.audio_settings import apply_music_volume
                    apply_music_volume()
                except Exception:
                    # fallback: leave default mixer volume
                    pass
                pygame.mixer.music.play(-1)
            except Exception:
                pass
    except Exception:
        pass

    # Main loop: show menu, run game, return to menu until quit
    while True:
        action = menu.run()
        print("Menu selected:", action)
        if action == "quit" or action is None:
            break
        if action == "new":
            # stop menu music and play game music on loop
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            try:
                bgm_dir = Path(__file__).resolve().parents[1] / "assets" / "bgm"
                game_music = bgm_dir / "GameMusic.wav"
                if game_music.exists():
                    try:
                        pygame.mixer.music.load(str(game_music))
                        try:
                            from .utils.audio_settings import apply_music_volume
                            apply_music_volume()
                        except Exception:
                            pass
                        pygame.mixer.music.play(-1)
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
            continue

if __name__ == "__main__":
    main()