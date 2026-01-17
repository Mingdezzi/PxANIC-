import pygame
from core.ecs_manager import ECSManager
from core.event_bus import EventBus
from components.common import Transform, Velocity, Animation
from components.status import StatusEffects
from components.interaction import InteractionState
from components.identity import Identity
from world.map_manager import MapManager
from settings import TILE_SIZE, SPEED_WALK, SPEED_RUN, SPEED_CROUCH, POLICE_SPEED_MULTI, NOISE_RADIUS
from world.tiles import check_collision, BED_TILES, HIDEABLE_TILES
from core.game_state_manager import GameStateManager

class MovementSystem:
    def __init__(self, ecs: ECSManager, event_bus: EventBus, map_manager: MapManager):
        self.ecs = ecs
        self.event_bus = event_bus
        self.map_manager = map_manager
        self.game_state = GameStateManager.get_instance()

    def update(self, dt):
        entities = self.ecs.get_entities_with(Transform, Velocity, StatusEffects, Animation, Identity)
        
        for entity_id in entities:
            transform = self.ecs.get_component(entity_id, Transform)
            velocity = self.ecs.get_component(entity_id, Velocity)
            status = self.ecs.get_component(entity_id, StatusEffects)
            anim = self.ecs.get_component(entity_id, Animation)
            identity = self.ecs.get_component(entity_id, Identity)

            interaction = self.ecs.get_component(entity_id, InteractionState)
            if status.stun_timer > pygame.time.get_ticks(): continue
            if interaction and interaction.is_working: continue
            if status.is_hiding: continue

            if velocity.dx == 0 and velocity.dy == 0: continue

            if velocity.speed_modifier >= 1.5: base_speed = SPEED_RUN; move_state = "RUN"
            elif velocity.speed_modifier <= 0.5: base_speed = SPEED_CROUCH; move_state = "CROUCH"
            else: base_speed = SPEED_WALK; move_state = "WALK"
            
            final_speed = self._calculate_speed(entity_id, base_speed, status, identity)
            
            move_x = velocity.dx * final_speed
            move_y = velocity.dy * final_speed
            
            if velocity.dx > 0: anim.facing_dir = (1, 0)
            elif velocity.dx < 0: anim.facing_dir = (-1, 0)
            elif velocity.dy > 0: anim.facing_dir = (0, 1)
            elif velocity.dy < 0: anim.facing_dir = (0, -1)

            transform.x += move_x; self._handle_collision(transform, True)
            transform.y += move_y; self._handle_collision(transform, False)
            
            map_w_px = self.map_manager.width * TILE_SIZE
            map_h_px = self.map_manager.height * TILE_SIZE
            transform.x = max(0, min(transform.x, map_w_px - transform.width))
            transform.y = max(0, min(transform.y, map_h_px - transform.height))

            # 발소리 생성
            if self.event_bus:
                self._generate_footstep_sound(entity_id, move_state, transform, status, identity)

    def _generate_footstep_sound(self, entity_id, move_state, transform, status, identity):
        now = pygame.time.get_ticks()
        
        step_interval = 600 if move_state == "WALK" else (300 if move_state == "RUN" else 800)
        
        if now > status.sound_timers['FOOTSTEP']:
            status.sound_timers['FOOTSTEP'] = now + step_interval
            
            s_type = "THUD" if move_state == "RUN" else ("RUSTLE" if move_state == "CROUCH" else "FOOTSTEP")
            radius = NOISE_RADIUS.get(move_state, 0)
            
            if status.buffs['SILENT']: radius *= 0.7
            if self.game_state.current_weather == 'RAIN': radius *= 0.8
            
            if radius > 0:
                self.event_bus.publish("PLAY_SOUND", (s_type, transform.x + transform.width//2, transform.y + transform.height//2, radius, identity.role))

    def _calculate_speed(self, entity_id, base_speed, status, identity):
        multiplier = 1.0
        
        if self.game_state.current_weather == 'SNOW': multiplier *= 0.8
        
        emotions = status.emotions
        if 'HAPPINESS' in emotions: multiplier += 0.10
        if 'DOPAMINE' in emotions: multiplier += [0, 0.05, 0.10, 0.15, 0.20, 0.30][min(5, emotions['DOPAMINE'])]
        if 'RAGE' in emotions: multiplier += [0, 0.05, 0.10, 0.15, 0.20, 0.30][min(5, emotions['RAGE'])]
        if 'FEAR' in emotions: multiplier -= 0.30
        if 'FATIGUE' in emotions: multiplier -= [0, 0.05, 0.10, 0.15, 0.20, 0.30][min(5, emotions['FATIGUE'])]
        if 'PAIN' in emotions and not status.buffs['NO_PAIN']: multiplier -= [0, 0.05, 0.10, 0.15, 0.20, 0.30][min(5, emotions['PAIN'])]
        
        if identity.role == "POLICE": multiplier *= POLICE_SPEED_MULTI
        if status.buffs['FAST_WORK']: multiplier *= 1.2
        return base_speed * max(0.2, multiplier)

    def _handle_collision(self, transform, horizontal):
        rect = transform.rect
        start_gx = max(0, rect.left // TILE_SIZE); end_gx = min(self.map_manager.width, (rect.right // TILE_SIZE) + 1)
        start_gy = max(0, rect.top // TILE_SIZE); end_gy = min(self.map_manager.height, (rect.bottom // TILE_SIZE) + 1)
        
        for y in range(start_gy, end_gy):
            for x in range(start_gx, end_gx):
                if self.map_manager.check_any_collision(x, y):
                    tile_rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if rect.colliderect(tile_rect):
                        if horizontal:
                            if rect.centerx < tile_rect.centerx: transform.x = tile_rect.left - transform.width
                            else: transform.x = tile_rect.right
                        else:
                            if rect.centery < tile_rect.centery: transform.y = tile_rect.top - transform.height
                            else: transform.y = tile_rect.bottom
                        rect = transform.rect