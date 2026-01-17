import pygame
from settings import SPEED_WALK, SPEED_RUN, SPEED_CROUCH, POLICE_SPEED_MULTI

class MovementLogic:
    def __init__(self, player):
        self.p = player

    def get_current_speed(self, weather_type='CLEAR'):
        if self.p.move_state == "RUN": base = SPEED_RUN
        elif self.p.move_state == "CROUCH": base = SPEED_CROUCH
        else: base = SPEED_WALK
        
        multiplier = 1.0
        
        if 'HAPPINESS' in self.p.emotions: multiplier += 0.10
        if 'DOPAMINE' in self.p.emotions:
            level = self.p.emotions['DOPAMINE']
            bonus = [0, 0.05, 0.10, 0.15, 0.20, 0.30]
            multiplier += bonus[level]
        if 'RAGE' in self.p.emotions:
            level = self.p.emotions['RAGE']
            bonus = [0, 0.05, 0.10, 0.15, 0.20, 0.30]
            multiplier += bonus[level]

        if 'FEAR' in self.p.emotions: multiplier -= 0.30
        
        if 'FATIGUE' in self.p.emotions:
            level = self.p.emotions['FATIGUE']
            penalty = [0, 0.05, 0.10, 0.15, 0.20, 0.30]
            multiplier -= penalty[level]
            
        if 'PAIN' in self.p.emotions and not self.p.buffs['NO_PAIN']:
            level = self.p.emotions['PAIN']
            penalty = [0, 0.05, 0.10, 0.15, 0.20, 0.30]
            multiplier -= penalty[level]

        if self.p.role == "POLICE": multiplier *= POLICE_SPEED_MULTI
        if self.p.buffs.get('FAST_WORK'): multiplier *= 1.2
        if weather_type == 'SNOW': multiplier *= 0.8
        
        return base * max(0.2, multiplier)

    def handle_input(self):
        keys = pygame.key.get_pressed(); dx, dy = 0, 0
        if keys[pygame.K_LEFT]: dx = -1
        if keys[pygame.K_RIGHT]: dx = 1
        if keys[pygame.K_UP]: dy = -1
        if keys[pygame.K_DOWN]: dy = 1
        
        infinite_stamina = ('RAGE' in self.p.emotions and self.p.role == "POLICE") or self.p.buffs['INFINITE_STAMINA']
        
        if keys[pygame.K_LSHIFT] and (self.p.breath_gauge > 0 or infinite_stamina): 
            self.p.move_state = "RUN"
        elif keys[pygame.K_LCTRL]: 
            self.p.move_state = "CROUCH"
        else: 
            self.p.move_state = "WALK"
            
        is_moving = False
        if dx != 0 or dy != 0:
            speed = self.get_current_speed(getattr(self.p, 'weather', 'CLEAR'))
            if dx != 0 and dy != 0: speed *= 0.7071
            self.p.move_single_axis(dx * speed, 0); self.p.move_single_axis(0, dy * speed)
            is_moving = True
            if dx != 0: self.p.facing_dir = (dx, 0)
            elif dy != 0: self.p.facing_dir = (0, dy)
            
            # [Optimization] Update Spatial Grid Position
            if hasattr(self.p, 'world') and self.p.world.spatial_grid:
                self.p.world.spatial_grid.update_entity(self.p)

        self.p.is_moving = is_moving
        return is_moving

    def update_stamina(self, is_moving):
        infinite = ('RAGE' in self.p.emotions and self.p.role == "POLICE") or self.p.buffs['INFINITE_STAMINA']
        if self.p.move_state == "RUN" and is_moving and not infinite: self.p.breath_gauge -= 0.5
        elif self.p.move_state != "RUN": self.p.breath_gauge = min(100, self.p.breath_gauge + 0.5)