import pygame
from ui.widgets.status import PlayerStatusWidget
from ui.widgets.environment import EnvironmentWidget
from ui.widgets.controls import ControlsWidget
from ui.widgets.bars import ActionBarsWidget
from ui.widgets.minimap import MinimapWidget
from ui.widgets.panels import EmotionPanelWidget
from ui.widgets.tools import SpecialToolsWidget

class HUD:
    def __init__(self, game):
        self.game = game
        self.widgets = [
            PlayerStatusWidget(game),
            EnvironmentWidget(game),
            ControlsWidget(game),
            ActionBarsWidget(game),
            MinimapWidget(game),
            EmotionPanelWidget(game),
            SpecialToolsWidget(game)
        ]

    def draw(self, screen):
        for widget in self.widgets:
            widget.draw(screen)

    def get_minimap_rect(self):
        # MinimapWidget is the 5th widget (index 4)
        return self.widgets[4].rect
