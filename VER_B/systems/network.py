import socket
import threading
import pickle
import queue
from settings import NETWORK_PORT, BUFFER_SIZE

class NetworkManager:
    def __init__(self, ip="127.0.0.1", port=NETWORK_PORT):
        self.ip = ip
        self.port = port
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.msg_queue = queue.Queue()
        self.my_id = -1 # Assigned by server

    def connect(self):
        try:
            self.client.connect((self.ip, self.port))
            self.connected = True
            print(f"[NET] Connected to {self.ip}:{self.port}")
            
            thread = threading.Thread(target=self.receive_loop)
            thread.daemon = True
            thread.start()
            return True
        except Exception as e:
            print(f"[NET] Connection Failed: {e}")
            return False

    def receive_loop(self):
        while self.connected:
            try:
                header = self.client.recv(4)
                if not header: break
                msg_len = int.from_bytes(header, byteorder='big')
                
                data = b""
                while len(data) < msg_len:
                    packet = self.client.recv(msg_len - len(data))
                    if not packet: break
                    data += packet
                if not data: break
                
                payload = pickle.loads(data)
                self.msg_queue.put(payload)
            except:
                self.connected = False
                break

    def send(self, data):
        if not self.connected: return
        try:
            # Always attach my_id if available
            if self.my_id != -1 and 'id' not in data:
                data['id'] = self.my_id
                
            serialized = pickle.dumps(data)
            length = len(serialized).to_bytes(4, byteorder='big')
            self.client.sendall(length + serialized)
        except:
            pass

    def get_events(self):
        events = []
        while not self.msg_queue.empty():
            events.append(self.msg_queue.get())
        return events

    # --- Helper Methods ---
    def send_role_change(self, new_role):
        self.send({"type": "UPDATE_ROLE", "role": new_role})

    def send_start_game(self):
        self.send({"type": "START_GAME"})

    def send_add_bot(self):
        self.send({"type": "ADD_BOT"})

    def send_move(self, x, y, is_moving, facing_dir):
        self.send({
            "type": "MOVE",
            "x": x, "y": y,
            "is_moving": is_moving,
            "facing": facing_dir
        })

    def disconnect(self):
        self.connected = False
        self.client.close()