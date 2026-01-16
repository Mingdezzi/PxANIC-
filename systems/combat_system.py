import pygame
import math
from .base_system import BaseSystem
from settings import TILE_SIZE

class Bullet:
    def __init__(self, x, y, angle, owner_role):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = 12
        self.radius = 4
        self.alive = True
        self.owner_role = owner_role # "POLICE" or "MAFIA" (Enemy Bullet)

    def update(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

class CombatSystem(BaseSystem):
    def __init__(self, event_bus, map_manager):
        self.event_bus = event_bus
        self.map_manager = map_manager
        self.bullets = []

    def update(self, dt, entities):
        # 1. 투사체 이동 및 충돌 처리
        for b in self.bullets[:]:
            b.update()
            
            # 맵 밖으로 나감
            if not (0 <= b.x < self.map_manager.width * TILE_SIZE and 0 <= b.y < self.map_manager.height * TILE_SIZE):
                b.alive = False
                self.bullets.remove(b)
                continue
                
            # 벽 충돌
            gx, gy = int(b.x // TILE_SIZE), int(b.y // TILE_SIZE)
            if self.map_manager.check_any_collision(gx, gy):
                 b.alive = False
                 self.bullets.remove(b)
                 continue
                 
            # 엔티티 충돌
            bullet_rect = pygame.Rect(b.x-2, b.y-2, 4, 4)
            for e in entities:
                if not e.components['stats'].alive: continue
                # 자기가 쏜 총알에 맞지 않기 (간단히 역할로 구분)
                if e.components['role'].main_role == b.owner_role: continue
                
                if bullet_rect.colliderect(e.transform.rect):
                    self._apply_damage(e, 70, "GUN")
                    b.alive = False
                    if b in self.bullets: self.bullets.remove(b)
                    break

    def handle_attack(self, attacker, target=None):
        # 근접 공격 (마피아, 테이저건 등)
        if not attacker.stats.alive: return
        
        # 쿨타임 체크 등은 Role 컴포넌트나 Stats에서 관리해야 함 (여기선 생략)
        
        if attacker.role.main_role == "MAFIA":
            if not target or not target.stats.alive: return
            dist = math.sqrt((attacker.transform.x - target.transform.x)**2 + (attacker.transform.y - target.transform.y)**2)
            if dist < TILE_SIZE * 1.5:
                if attacker.stats.ap >= 10:
                    attacker.stats.ap -= 10
                    self._apply_damage(target, 70, "STAB")
                    self.event_bus.publish("PLAY_SOUND", {'name': "STAB", 'x': attacker.transform.x, 'y': attacker.transform.y})
                    
        elif attacker.role.main_role == "POLICE":
            # 원거리 공격 (총 발사)
            # 타겟이 없어도 발사 가능 (마우스 방향 등)
            # 여기서는 InputSystem이 바라보는 방향으로 발사 요청을 보냈다고 가정
            if attacker.role.bullets_fired_today >= 1:
                self.event_bus.publish("SHOW_ALERT", {'text': "No ammo left!"})
                return

            attacker.role.bullets_fired_today += 1
            # 발사 로직
            angle = math.atan2(attacker.transform.facing[1], attacker.transform.facing[0])
            new_bullet = Bullet(attacker.transform.x + 16, attacker.transform.y + 16, angle, "POLICE")
            self.bullets.append(new_bullet)
            self.event_bus.publish("PLAY_SOUND", {'name': "GUNSHOT", 'x': attacker.transform.x, 'y': attacker.transform.y})

    def _apply_damage(self, target, amount, damage_type):
        stats = target.stats
        inv = target.inventory
        
        if target.role.main_role == "POLICE": return # 경찰 무적 (기획서 따름)
        
        # 방탄조끼 체크
        if inv.has_item('ARMOR'):
            inv.remove_item('ARMOR')
            self.event_bus.publish("SHOW_ALERT", {'text': "Armor Blocked!"})
            self.event_bus.publish("PLAY_SOUND", {'name': "CLICK", 'x': target.transform.x, 'y': target.transform.y})
            return

        stats.hp -= amount
        if stats.hp <= 0:
            stats.hp = 0
            stats.alive = False
            self.event_bus.publish("ENTITY_DIED", {'entity': target})
            self.event_bus.publish("SHOW_ALERT", {'text': f"{target.name} Died!", 'color': (255, 0, 0)})
