from .BaseWeapon  import BaseWeapon
from .BaseballBat import BaseballBat
from .Magnet      import Magnet

__all__ = ['BaseWeapon', 'BaseballBat', 'Magnet', 'make_weapon']

# Registry: weapon name (as used in Baseballers.yaml) → class
_REGISTRY = {
    'baseball_bat': BaseballBat,
    'magnet':       Magnet,
}


def make_weapon(name: str) -> BaseWeapon:
    """Return a fresh weapon instance for the given weapon name string.
    Falls back to BaseballBat for unknown names."""
    cls = _REGISTRY.get(name, BaseballBat)
    return cls()
