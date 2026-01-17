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
        # 플레이어가 관전자일 경우 일부 위젯만 그리거나 스킵하는 로직은 각 위젯 내부에서 처리하도록 함
        # 여기서는 순서대로 그리기만 함
        for widget in self.widgets:
            widget.draw(screen)
