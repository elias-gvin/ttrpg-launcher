"""The kinds of thing a game can start. See base.py for the interface."""

from rpg_launcher.components.apps import Apps
from rpg_launcher.components.base import Component
from rpg_launcher.components.obs import Obs
from rpg_launcher.components.pages import Pages

# In launch order. To add a component, write its module in this package and
# add it here.
COMPONENTS: tuple[Component, ...] = (Obs(), Apps(), Pages())
