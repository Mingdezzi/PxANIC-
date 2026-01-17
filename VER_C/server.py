import socket
import threading
import pickle
import time
from settings import NETWORK_PORT, BUFFER_SIZE

class GameServer:
    def __init__(self):
        self.host = "0.0.0.0"
        self.port = NETWORK_PORT
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.clients = {} # {socket: addr}
        # players: {player_id: {'name': str, 'role': str, 'x': int, 'y': int, 'alive': bool}}
        self.players = {} 
        self.next_id = 0
        self.game_started = False
        self.running = True

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            print(f"[SERVER] Running on {self.host}:{self.port}")

            while self.running:
                client_sock, addr = self.server_socket.accept()
                print(f"[SERVER] New connection: {addr}")
                
                # Assign ID
                pid = self.next_id
                self.next_id += 1
                
                self.clients[client_sock] = pid
                self.players[pid] = {
                    'id': pid,
                    'name': f"Player {pid+1}",
                    'role': 'CITIZEN',
                    'group': 'PLAYER', # Added missing key
                    'type': 'PLAYER',  # Added missing key
                    'x': 100, 'y': 100,
                    'alive': True
                }

                # Start handling thread
                thread = threading.Thread(target=self.handle_client, args=(client_sock, pid))
                thread.daemon = True
                thread.start()
                
        except Exception as e:
            print(f"[SERVER] Critical Error: {e}")
        finally:
            self.server_socket.close()

    def handle_client(self, sock, pid):
        # 1. Send Welcome Packet (My ID)
        self.send_to(sock, {"type": "WELCOME", "my_id": pid})
        
        # 2. Broadcast Updated Player List to ALL (Lobby Sync)
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

                payload = pickle.loads(data)
                self.process_packet(pid, payload)

        except Exception as e:
            print(f"[SERVER] Error with Player {pid}: {e}")
        finally:
            print(f"[SERVER] Player {pid} Disconnected")
            self.remove_client(sock, pid)

    def remove_client(self, sock, pid):
        if sock in self.clients:
            del self.clients[sock]
        if pid in self.players:
            del self.players[pid]
        try:
            sock.close()
        except:
            pass
        # Broadcast updated list
        self.broadcast_player_list()

    def process_packet(self, pid, data):
        ptype = data.get('type')

        if ptype == 'UPDATE_ROLE':
            # Lobby role change
            new_role = data.get('role')
            if pid in self.players:
                self.players[pid]['role'] = new_role
                self.broadcast_player_list()

        elif ptype == 'START_GAME':
            # Only Host (ID 0) can start
            if pid == 0:
                self.game_started = True
                print("[SERVER] Game Starting...")
                self.broadcast({"type": "GAME_START", "players": self.players})

        elif ptype == 'ADD_BOT':
            # Only Host can add bots
            if pid == 0:
                bot_id = self.next_id
                self.next_id += 1
                self.players[bot_id] = {
                    'id': bot_id,
                    'name': f"Bot {bot_id}",
                    'role': 'RANDOM',
                    'group': 'PLAYER',
                    'type': 'BOT',
                    'x': 100, 'y': 100,
                    'alive': True
                }
                print(f"[SERVER] Bot Added: {bot_id}")
                self.broadcast_player_list()

        elif ptype == 'MOVE':
            # In-game movement
            if pid in self.players:
                self.players[pid]['x'] = data['x']
                self.players[pid]['y'] = data['y']
                self.players[pid]['facing'] = data.get('facing', (0, 1))
                self.players[pid]['is_moving'] = data.get('is_moving', False)
                # Relay to others immediately
                self.broadcast(data, exclude_pid=pid)

    def broadcast_player_list(self):
        # Send simple list for Lobby
        participant_list = []
        for p in self.players.values():
            participant_list.append(p)
        self.broadcast({"type": "PLAYER_LIST", "participants": participant_list})

    def send_to(self, sock, data):
        try:
            serialized = pickle.dumps(data)
            length = len(serialized).to_bytes(4, byteorder='big')
            sock.sendall(length + serialized)
        except:
            pass

    def broadcast(self, data, exclude_pid=None):
        serialized = pickle.dumps(data)
        length = len(serialized).to_bytes(4, byteorder='big')
        packet = length + serialized
        
        for sock, pid in self.clients.items():
            if pid == exclude_pid: continue
            try:
                sock.sendall(packet)
            except:
                pass

if __name__ == "__main__":
    server = GameServer()
    server.start()