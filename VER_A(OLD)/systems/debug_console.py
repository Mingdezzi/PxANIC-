import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, ITEMS
from entities.npc import Dummy
from core.world import TILE_SIZE

class DebugConsole:
    def __init__(self, game, play_state):
        self.game = game
        self.play_state = play_state
        self.active = False
        self.input_text = ""
        self.history = []
        self.font = pygame.font.SysFont("consolas", 14)
        self.height = 200
        self.bg_surf = pygame.Surface((SCREEN_WIDTH, self.height))
        self.bg_surf.fill((0, 0, 0))
        self.bg_surf.set_alpha(200)
        
        # Command Registry
        self.commands = {
            'help': self.cmd_help,
            'spawn': self.cmd_spawn,
            'give': self.cmd_give,
            'tp': self.cmd_tp,
            'time': self.cmd_time,
            'god': self.cmd_god,
            'kill': self.cmd_kill,
            'money': self.cmd_money
        }

    def toggle(self):
        self.active = not self.active
        # Clear input when opening
        if self.active:
            self.input_text = ""

    def handle_event(self, event):
        if not self.active:
            return False
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKQUOTE: # Tilde (~)
                self.toggle()
                return True
            elif event.key == pygame.K_RETURN:
                self.execute_command(self.input_text)
                self.input_text = ""
                return True
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
                return True
            else:
                self.input_text += event.unicode
                return True
        return False

    def execute_command(self, cmd_str):
        self.log(f"> {cmd_str}")
        parts = cmd_str.strip().split()
        if not parts: return

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in self.commands:
            try:
                msg = self.commands[cmd](args)
                if msg: self.log(msg)
            except Exception as e:
                self.log(f"Error: {e}")
        else:
            self.log(f"Unknown command: {cmd}")

    def log(self, text):
        self.history.append(text)
        if len(self.history) > 10:
            self.history.pop(0)

    def draw(self, screen):
        if not self.active: return

        screen.blit(self.bg_surf, (0, 0))
        
        # Draw History
        y = 10
        for line in self.history:
            txt = self.font.render(line, True, (200, 200, 200))
            screen.blit(txt, (10, y))
            y += 18
            
        # Draw Input Line
        pygame.draw.line(screen, (100, 100, 100), (0, self.height-25), (SCREEN_WIDTH, self.height-25))
        input_surf = self.font.render(f"$ {self.input_text}", True, (255, 255, 0))
        screen.blit(input_surf, (10, self.height - 20))
        
        # Cursor
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            cx = 10 + input_surf.get_width()
            pygame.draw.rect(screen, (255, 255, 0), (cx, self.height-20, 8, 14))

    # --- Commands ---

    def cmd_help(self, args):
        return "Commands: spawn, give, tp, time, god, kill, money"

    def cmd_spawn(self, args):
        if not args: return "Usage: /spawn [role]"
        role = args[0].upper()
        
        mx, my = pygame.mouse.get_pos()
        # Convert screen to world
        cam = self.play_state.camera
        wx = (mx + cam.x) / self.play_state.zoom_level
        wy = (my + cam.y) / self.play_state.zoom_level
        
        dummy = Dummy(wx, wy, None, 
                      self.play_state.world.map_manager.width, 
                      self.play_state.world.map_manager.height, 
                      name="Spawned", role=role, 
                      zone_map=self.play_state.world.map_manager.zone_map, 
                      map_manager=self.play_state.world.map_manager)
        
        self.play_state.world.register_entity(dummy)
        self.play_state.world.npcs.append(dummy)
        return f"Spawned {role} at ({int(wx)}, {int(wy)})"

    def cmd_give(self, args):
        if not args: return "Usage: /give [item] [count]"
        item = args[0].upper()
        count = int(args[1]) if len(args) > 1 else 1
        
        if item not in ITEMS: return "Invalid item."
        
        self.play_state.player.inventory[item] = self.play_state.player.inventory.get(item, 0) + count
        return f"Gave {count} {item}"

    def cmd_tp(self, args):
        if len(args) < 2: return "Usage: /tp [x] [y]"
        x, y = int(args[0]), int(args[1])
        self.play_state.player.pos_x = x * TILE_SIZE
        self.play_state.player.pos_y = y * TILE_SIZE
        self.play_state.player.rect.x = x * TILE_SIZE
        self.play_state.player.rect.y = y * TILE_SIZE
        return f"Teleported to ({x}, {y})"

    def cmd_time(self, args):
        if not args: return "Usage: /time [phase]"
        phase = args[0].upper()
        if phase in self.play_state.phases:
            self.play_state.time_system.current_phase = phase
            self.play_state.time_system.state_timer = 5 # Set short timer to trigger update
            return f"Time set to {phase}"
        return "Invalid phase."

    def cmd_god(self, args):
        self.play_state.player.buffs['NO_PAIN'] = not self.play_state.player.buffs['NO_PAIN']
        state = "ON" if self.play_state.player.buffs['NO_PAIN'] else "OFF"
        if state == "ON": self.play_state.player.hp = 9999
        return f"God Mode {state}"

    def cmd_kill(self, args):
        self.play_state.player.hp = 0
        return "Suicide."

    def cmd_money(self, args):
        amount = int(args[0]) if args else 100
        self.play_state.player.coins += amount
        return f"Added {amount} coins"
