import pygame
import math
from .base_system import BaseSystem
from settings import TILE_SIZE

class Bullet:
    def __init__(self, x, y, angle, owner_role):
        self.x, self.y, self.angle, self.owner_role = x, y, angle, owner_role
        self.speed, self.radius, self.alive = 12, 4, True
    def update(self): self.x += math.cos(self.angle) * self.speed; self.y += math.sin(self.angle) * self.speed

class CombatSystem(BaseSystem):
    def __init__(self, event_bus, map_manager):
        self.event_bus = event_bus
        self.map_manager = map_manager
        self.bullets = []
        self.attack_cooldowns = {} # {entity_id: last_attack_time}
        self.curr_entities = []

        # [복구] 스킬 이벤트 구독
        self.event_bus.subscribe("TRIGGER_SIREN", self._on_trigger_siren)
        self.event_bus.subscribe("TRIGGER_BLACKOUT", self._on_trigger_blackout)

    def _on_trigger_siren(self, data):
        # [복구] 경찰 사이렌: 범위 내 마피아 동결
        x, y, radius = data['x'], data['y'], data['radius']
        count = 0
        
        for entity in self.curr_entities:
            if not entity.stats.alive: continue
            if entity.role.main_role == "MAFIA":
                dist = math.sqrt((entity.transform.x - x)**2 + (entity.transform.y - y)**2)
                if dist <= radius:
                    # 마피아 얼리기
                    entity.stats.status_effects['FROZEN'] = True
                    entity.stats.frozen_end_time = pygame.time.get_ticks() + 5000
                    count += 1
        
        self.event_bus.publish("SHOW_ALERT", {'text': f"Siren! {count} Villains Frozen!", 'color': (100, 100, 255)})
        self.event_bus.publish("PLAY_SOUND", {'name': "SIREN", 'x': x, 'y': y})

    def _on_trigger_blackout(self, data):
        # [복구] 마피아 사보타주: 시민 공포 및 은신 해제
        for entity in self.curr_entities:
            if not entity.stats.alive: continue
            if entity.role.main_role in ["CITIZEN", "DOCTOR"]:
                entity.stats.emotions['FEAR'] = 1
                if entity.graphics.is_hiding:
                    entity.graphics.is_hiding = False
                    self.event_bus.publish("SHOW_ALERT", {'text': "Revealed by Panic!", 'color': (255, 50, 50)})

    def update(self, dt, entities):
        self.curr_entities = entities # [중요] 엔티티 리스트 참조 저장
        # 1. 투사체 업데이트
        for b in self.bullets[:]:
            b.update()
            if not (0 <= b.x < self.map_manager.width * TILE_SIZE and 0 <= b.y < self.map_manager.height * TILE_SIZE):
                b.alive = False; self.bullets.remove(b); continue
            gx, gy = int(b.x // TILE_SIZE), int(b.y // TILE_SIZE)
            if self.map_manager.check_any_collision(gx, gy):
                 b.alive = False; self.bullets.remove(b); continue
            bullet_rect = pygame.Rect(b.x-2, b.y-2, 4, 4)
            for e in entities:
                if not e.stats.alive: continue
                if e.role.main_role == b.owner_role: continue
                if bullet_rect.colliderect(e.transform.rect):
                    self._apply_damage(e, 70, "GUN")
                    b.alive = False
                    if b in self.bullets: self.bullets.remove(b)
                    break

    def handle_attack(self, attacker, target=None):
        if not attacker.stats.alive: return
        
        # [복구] 쿨타임 체크 (1초)
        now = pygame.time.get_ticks()
        last_time = self.attack_cooldowns.get(attacker.uid, 0)
        if now - last_time < 1000: return
        
        # [복구] 테이저건 사용 (누구나 가능)
        if attacker.inventory.has_item('TASER'):
            if target and target.stats.alive:
                dist = math.sqrt((attacker.transform.x - target.transform.x)**2 + (attacker.transform.y - target.transform.y)**2)
                if dist < TILE_SIZE * 2:
                    attacker.inventory.remove_item('TASER')
                    target.stats.status_effects['STUNNED'] = True
                    target.stats.stun_end_time = now + 3000
                    self.event_bus.publish("PLAY_SOUND", {'name': "ZAP", 'x': attacker.transform.x, 'y': attacker.transform.y, 'role': attacker.role.main_role})
                    self.event_bus.publish("SHOW_ALERT", {'text': "TASER SHOT!", 'color': (255, 255, 0)})
                    self.attack_cooldowns[attacker.uid] = now
            return

        # 마피아 칼 공격
        if attacker.role.main_role == "MAFIA":
            if not target or not target.stats.alive: return
            dist = math.sqrt((attacker.transform.x - target.transform.x)**2 + (attacker.transform.y - target.transform.y)**2)
            if dist < TILE_SIZE * 1.5:
                if attacker.stats.ap >= 10:
                    attacker.stats.ap -= 10
                    self._apply_damage(target, 70, "STAB")
                    self.event_bus.publish("PLAY_SOUND", {'name': "STAB", 'x': attacker.transform.x, 'y': attacker.transform.y, 'role': "MAFIA"})
                    self.attack_cooldowns[attacker.uid] = now
                    
        # 경찰 총 공격
        elif attacker.role.main_role == "POLICE":
            if attacker.role.bullets_fired_today >= 1:
                self.event_bus.publish("SHOW_ALERT", {'text': "No ammo left!"})
                return
            attacker.role.bullets_fired_today += 1
            angle = math.atan2(attacker.transform.facing[1], attacker.transform.facing[0])
            new_bullet = Bullet(attacker.transform.x + 16, attacker.transform.y + 16, angle, "POLICE")
            self.bullets.append(new_bullet)
            self.event_bus.publish("PLAY_SOUND", {'name': "GUNSHOT", 'x': attacker.transform.x, 'y': attacker.transform.y, 'role': "POLICE"})
            self.attack_cooldowns[attacker.uid] = now

    def handle_heal(self, healer, target=None):
        # [복구] 의사 힐링 스킬
        if healer.role.main_role != "DOCTOR" or not healer.stats.alive: return
        if not target or not target.stats.alive: 
            self.event_bus.publish("SHOW_ALERT", {'text': "No target to heal"})
            return
            
        dist = math.sqrt((healer.transform.x - target.transform.x)**2 + (healer.transform.y - target.transform.y)**2)
        if dist > TILE_SIZE * 2: return

        if healer.stats.ap >= 10:
            healer.stats.ap -= 10
            target.stats.hp = min(target.stats.max_hp, target.stats.hp + 50)
            self.event_bus.publish("PLAY_SOUND", {'name': "GULP", 'x': target.transform.x, 'y': target.transform.y, 'role': "DOCTOR"})
            self.event_bus.publish("SHOW_ALERT", {'text': f"Healed {target.name}!", 'color': (100, 255, 100)})
        else:
            self.event_bus.publish("SHOW_ALERT", {'text': "Not enough AP (10)", 'color': (255, 50, 50)})

    def _apply_damage(self, target, amount, damage_type):
        if target.role.main_role == "POLICE": return
        if target.inventory.has_item('ARMOR'):
            target.inventory.remove_item('ARMOR')
            self.event_bus.publish("SHOW_ALERT", {'text': "Armor Blocked!"})
            self.event_bus.publish("PLAY_SOUND", {'name': "CLICK", 'x': target.transform.x, 'y': target.transform.y, 'role': "NONE"})
            return
        target.stats.hp -= amount
        if target.stats.hp <= 0:
            target.stats.hp = 0; target.stats.alive = False
            self.event_bus.publish("ENTITY_DIED", {'entity': target})
            self.event_bus.publish("SHOW_ALERT", {'text': f"{target.name} Died!", 'color': (255, 0, 0)})