import socket
import threading
import json
import time
import traceback

class GameServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #initialisation du socket
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {} # client_id -> socket
        self.players = {} # client_id -> player dict
        self.game_state = {'players': {}, 'timestamp': time.time()}
        self.lock = threading.Lock()
        self.next_client_id = 0 #initialisation du nb de joueurs
        self.running = True

    def start_server(self): #mise en ecoute du serveur sur le port associe
        self.socket.bind((self.host, self.port))
        self.socket.listen(8)
        print(f"Server listening on {self.host}:{self.port}")

        threading.Thread(target=self.game_loop, daemon=True).start()

        try:
            while self.running:
                client_socket, address = self.socket.accept()
                with self.lock:
                    client_id = self.next_client_id
                    self.next_client_id += 1
                    self.clients[client_id] = client_socket
                    self.players[client_id] = {'x': 100 + client_id * 50,'y': 100,'color': [255, 0, 0] if client_id == 0 else [0, 0, 255]}
                print(f"Connection from {address} assigned id {client_id}")

                threading.Thread(target=self.handle_client,args=(client_socket, client_id),daemon=True).start()
        except KeyboardInterrupt:
            print("Shutting down server...")
            self.running = False
            self.shutdown()
        except Exception:
            traceback.print_exc()
            self.shutdown()

    def handle_client(self, client_socket, client_id): #reception du message des joueurs
        buffer = ""
        try:
            while True:
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if not line.strip():
                        continue
                    try:
                        message = json.loads(line)
                        self.process_message(client_id, message)
                    except json.JSONDecodeError:
                        print(f"Invalid JSON from {client_id}: {line}")
        except ConnectionResetError:
            print(f"ConnectionResetError for client {client_id}")
        except Exception:
            print(f"Error handling client {client_id}:")
            traceback.print_exc()
        finally:
            self.disconnect_client(client_id)

    def process_message(self, client_id, message): # traitement du messages recu en fonction du type
        if message.get('type') == 'move':
            with self.lock:
                if client_id in self.players:
                    self.players[client_id]['x'] = message.get('x', self.players[client_id]['x'])
                    self.players[client_id]['y'] = message.get('y', self.players[client_id]['y'])

    def game_loop(self):
        try:
            while self.running:
                with self.lock:
                    players_copy = {str(k): v for k, v in self.players.items()}
                    self.game_state = {'players': players_copy, 'timestamp': time.time()}
                self.broadcast_game_state()
                time.sleep(1/60)
        except Exception:
            traceback.print_exc()

    def broadcast_game_state(self):
        message = json.dumps(self.game_state) + '\n'  # delimitation avec une nouvelle ligne 
        disconnected = []
        with self.lock:
            for client_id, client_socket in list(self.clients.items()):
                try:
                    client_socket.sendall(message.encode('utf-8'))
                except Exception:
                    disconnected.append(client_id)
        for cid in disconnected:
            self.disconnect_client(cid)

    def disconnect_client(self, client_id): #si un joueur se deconnecte
        with self.lock:
            sock = self.clients.pop(client_id, None)
            if sock:
                try:
                    sock.close()
                except:
                    pass
            if client_id in self.players:
                del self.players[client_id]
        print(f"Client {client_id} disconnected")

    def shutdown(self): # fin du socket
        with self.lock:
            for cid, sock in list(self.clients.items()):
                try:
                    sock.close()
                except:
                    pass
            self.clients.clear()
            self.players.clear()
        try:
            self.socket.close()
        except:
            pass

if __name__ == "__main__":
    server = GameServer()
    server.start_server()