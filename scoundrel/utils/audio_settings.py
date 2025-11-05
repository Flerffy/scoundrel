"""Simple runtime audio settings shared by menu and engine.

Stores master/bgm/sfx volumes (0.0-1.0) and provides helpers to apply
the settings to pygame.mixer.music and per-sfx channels.
"""
from typing import Callable
import pygame
import json
from pathlib import Path

# Default volumes
_master_volume = 1.0
_bgm_volume = 0.5
_sfx_volume = 0.9

# persistent settings file under repo data/ directory
# compute project data dir relative to this file
try:
    DATA_DIR = Path(__file__).resolve().parents[2] / "data"
except Exception:
    DATA_DIR = Path("data")
SETTINGS_FILE = DATA_DIR / "settings.json"


def _ensure_data_dir():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _clamp(v: float) -> float:
    try:
        if v < 0.0:
            return 0.0
        if v > 1.0:
            return 1.0
        return float(v)
    except Exception:
        return 0.0


def set_master(v: float) -> None:
    global _master_volume
    _master_volume = _clamp(v)
    apply_music_volume()
    # persist
    try:
        save_settings()
    except Exception:
        pass


def set_bgm(v: float) -> None:
    global _bgm_volume
    _bgm_volume = _clamp(v)
    apply_music_volume()
    try:
        save_settings()
    except Exception:
        pass


def set_sfx(v: float) -> None:
    global _sfx_volume
    _sfx_volume = _clamp(v)
    try:
        save_settings()
    except Exception:
        pass


def get_master() -> float:
    return _master_volume


def get_bgm() -> float:
    return _bgm_volume


def get_sfx() -> float:
    return _sfx_volume


def apply_music_volume() -> None:
    """Apply current master*bgm to pygame.mixer.music (best-effort)."""
    try:
        vol = _master_volume * _bgm_volume
        try:
            pygame.mixer.music.set_volume(vol)
        except Exception:
            pass
    except Exception:
        pass


def load_settings() -> None:
    """Load persisted settings from data/settings.json if present."""
    global _master_volume, _bgm_volume, _sfx_volume
    try:
        if SETTINGS_FILE.exists():
            try:
                raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                _master_volume = _clamp(raw.get("master", _master_volume))
                _bgm_volume = _clamp(raw.get("bgm", _bgm_volume))
                _sfx_volume = _clamp(raw.get("sfx", _sfx_volume))
            except Exception:
                pass
    except Exception:
        pass


def save_settings() -> None:
    """Persist current settings to data/settings.json (best-effort)."""
    try:
        _ensure_data_dir()
        d = {"master": _master_volume, "bgm": _bgm_volume, "sfx": _sfx_volume}
        try:
            SETTINGS_FILE.write_text(json.dumps(d, indent=2), encoding="utf-8")
        except Exception:
            # fallback: open/write
            try:
                with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
                    json.dump(d, fh, indent=2)
            except Exception:
                pass
    except Exception:
        pass


# At import time, try to load settings and apply music volume
try:
    load_settings()
    apply_music_volume()
except Exception:
    pass


def apply_sfx_to_channel(channel: "pygame.mixer.Channel", base_volume: float = 1.0) -> None:
    """Adjust a mixer Channel's volume according to master and sfx settings.

    base_volume is the intended per-sound baseline (0.0-1.0) that the sound
    was loaded with; the channel volume will be set to master * sfx * base.
    """
    try:
        if channel is None:
            return
        vol = float(_master_volume) * float(_sfx_volume) * float(base_volume)
        try:
            # channel may support left,right volumes but set_volume accepts one value
            channel.set_volume(vol)
        except Exception:
            pass
    except Exception:
        pass
