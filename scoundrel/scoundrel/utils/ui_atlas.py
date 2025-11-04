from .ui_atlas_clean import UIAtlas

# Thin wrapper to expose a canonical module path `scoundrel.utils.ui_atlas`
# which imports the implemented UIAtlas from ui_atlas_clean. This keeps the
# cleaned implementation separate while providing a stable import location.
__all__ = ["UIAtlas"]