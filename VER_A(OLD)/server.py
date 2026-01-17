import socket
import threading
import pickle
import time
from settings import NETWORK_PORT, BUFFER_SIZE, DEFAULT_PHASE_DURATIONS

class GameServer:
    def __init__(self):
        self.host = "0.0.0.0"
        self.port = NETWORK_PORT
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.clients = {} # {socket: pid}
        self.players = {} # {pid: data}
        self.next_id = 0
        self.game_started = False
        self.running = True
        
        # Time Management
        self.phases = ["DAWN", "MORNING", "NOON", "AFTERNOON", "EVENING", "NIGHT"]
        self.current_phase_idx = 0
        self.day_count = 1
        self.state_timer = DEFAULT_PHASE_DURATIONS[self.phases[0]]
        self.last_tick = time.time()

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            print(f"[SERVER] Running on {self.host}:{self.port}")

            threading.Thread(target=self.game_loop, daemon=True).start()

            while self.running:
                client_sock, addr = self.server_socket.accept()
                pid = self.next_id
                self.next_id += 1
                
                self.clients[client_sock] = pid
                self.players[pid] = {
                    'id': pid, 'name': f"Player {pid+1}", 'role': 'CITIZEN',
                    'group': 'PLAYER', 'type': 'PLAYER', 'x': -1000, 'y': -1000, 'alive': True
                }

                thread = threading.Thread(target=self.handle_client, args=(client_sock, pid))
                thread.daemon = True
                thread.start()
        except Exception as e:
            print(f"[SERVER] Critical Error: {e}")
        finally:
            self.server_socket.close()

    def game_loop(self):
        while self.running:
            time.sleep(0.1)
            if not self.game_started: continue
            
            now = time.time()
            dt = now - self.last_tick
            self.last_tick = now
            
            self.state_timer -= dt
            if self.state_timer <= 0:
                self._advance_phase()
                
            if int(now) % 1 == 0:
                self.broadcast({"type": "TIME_SYNC", "phase_idx": self.current_phase_idx, "timer": self.state_timer, "day": self.day_count})

    def _advance_phase(self):
        self.current_phase_idx = (self.current_phase_idx + 1) % len(self.phases)
        new_phase = self.phases[self.current_phase_idx]
        if new_phase == "DAWN": self.day_count += 1 # Day increases at DAWN
        self.state_timer = DEFAULT_PHASE_DURATIONS.get(new_phase, 30)
        self.broadcast({"type": "TIME_SYNC", "phase_idx": self.current_phase_idx, "timer": self.state_timer, "day": self.day_count})

    def handle_client(self, sock, pid):
        self.send_to(sock, {"type": "WELCOME", "my_id": pid})
        self.broadcast_player_list()
        try:
            while self.running:
                header = sock.recv(4)
                if not header: break
                msg_len = int.from_bytes(header, byteorder='big')
                data = b""
                while len(data) < msg_len:
                    packet = sock.recv(msg_len - len(data))
                    if not packet: break
                    data += packet
                if not data: break
                self.process_packet(pid, pickle.loads(data))
        except: pass
        finally:
            self.remove_client(sock, pid)

    def remove_client(self, sock, pid):
        if sock in self.clients: del self.clients[sock]
        if pid in self.players: del self.players[pid]
        try: sock.close()
        except: pass
        self.broadcast_player_list()

    def process_packet(self, pid, data):
        ptype = data.get('type')
        if ptype == 'UPDATE_ROLE':
            if pid in self.players:
                self.players[pid]['role'] = data.get('role'); self.broadcast_player_list()
        elif ptype == 'CHANGE_GROUP':
            tid = data.get('target_id')
            if tid in self.players:
                self.players[tid]['group'] = data.get('group'); self.broadcast_player_list()
        elif ptype == 'ADD_BOT':
            bid = self.next_id; self.next_id += 1
            self.players[bid] = {
                'id': bid, 'name': data.get('name'), 'role': 'RANDOM',
                'group': data.get('group'), 'type': 'BOT', 'x': -1000, 'y': -1000, 'alive': True
            }
            self.broadcast_player_list()
        elif ptype == 'START_GAME':
            if pid == 0:
                self.game_started = True; self.last_tick = time.time()
                self.broadcast({"type": "GAME_START", "players": self.players})
        elif ptype == 'MOVE':
            mid = data.get('id', pid) # Can be bot ID sent by host
            if mid in self.players:
                self.players[mid].update({'x': data['x'], 'y': data['y'], 'facing': data.get('facing'), 'is_moving': data.get('is_moving')})
                self.broadcast(data, exclude_pid=pid)

    def broadcast_player_list(self):
        self.broadcast({"type": "PLAYER_LIST", "participants": list(self.players.values())})

    def send_to(self, sock, data):
        try:
            serialized = pickle.dumps(data)
            sock.sendall(len(serialized).to_bytes(4, 'big') + serialized)
        except: pass

    def broadcast(self, data, exclude_pid=None):
        serialized = pickle.dumps(data)
        packet = len(serialized).to_bytes(4, 'big') + serialized
        for sock, pid in self.clients.items():
            if pid != exclude_pid:
                try: sock.sendall(packet)
                except: pass

if __name__ == "__main__":
    GameServer().start()