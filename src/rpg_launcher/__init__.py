"""RPG session launcher."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("rpg-launcher")
except PackageNotFoundError:  # running from a source checkout
    __version__ = "0+source"
