import pygame
from ui.widgets.base import UIWidget

class ActionBarsWidget(UIWidget):
    def draw(self, screen):
        self._draw_stamina_bar(screen)
        self._draw_interaction_bar(screen)

    def _draw_interaction_bar(self, screen):
        player = self.game.player
        if player.e_key_pressed:
            now = pygame.time.get_ticks()
            hold_time = now - player.interaction_hold_timer
            ratio = min(1.0, hold_time / 1000.0)
            
            cam_x, cam_y = self.game.camera.x, self.game.camera.y
            zoom = self.game.zoom_level
            
            screen_x = (player.rect.centerx - cam_x) * zoom
            screen_y = (player.rect.centery - cam_y) * zoom
            
            draw_x = screen_x
            draw_y = screen_y - (50 * zoom)
            
            w, h = 40, 6
            pygame.draw.rect(screen, (50, 50, 50), (draw_x - w//2, draw_y, w, h))
            pygame.draw.rect(screen, (255, 255, 0), (draw_x - w//2, draw_y, w * ratio, h))

    def _draw_stamina_bar(self, screen):
        player = self.game.player
        if player.breath_gauge >= 100: return
        
        cam_x, cam_y = self.game.camera.x, self.game.camera.y
        zoom = self.game.zoom_level
        
        screen_x = (player.rect.centerx - cam_x) * zoom
        screen_y = (player.rect.centery - cam_y) * zoom
        
        draw_x = screen_x
        draw_y = screen_y - (60 * zoom)
        
        w, h = 40, 5
        ratio = max(0, player.breath_gauge / 100.0)
        
        pygame.draw.rect(screen, (30, 30, 30), (draw_x - w//2, draw_y, w, h))
        pygame.draw.rect(screen, (100, 200, 255), (draw_x - w//2, draw_y, w * ratio, h))
