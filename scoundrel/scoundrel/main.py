import pygame
from pathlib import Path
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
    screen = pygame.display.set_mode((960, 640))
    pygame.display.set_caption("Scoundrel")
    menu = Menu(screen, title="Scoundrel")
    # try to play menu music on loop (best-effort)
    try:
        bgm_dir = Path(__file__).resolve().parents[1] / "assets" / "bgm"
        menu_music = bgm_dir / "MenuMusic.wav"
        if menu_music.exists():
            try:
                pygame.mixer.music.load(str(menu_music))
                pygame.mixer.music.set_volume(0.5)
                pygame.mixer.music.play(-1)
            except Exception:
                pass
    except Exception:
        pass

    action = menu.run()
    print("Menu selected:", action)
    if action == "quit" or action is None:
        pygame.quit()
        return
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
                    pygame.mixer.music.set_volume(0.5)
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
        main()
    if action == "settings":
        # TODO: settings screen
        # For now, just go back to menu
        main()

if __name__ == "__main__":
    main()