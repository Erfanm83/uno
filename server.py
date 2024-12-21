import socket
import threading
import json

class UnoServer:
    def __init__(self, host='127.0.0.1', port=12345):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen()
        print("Server started. Waiting for players...")

        self.clients = []
        self.game = None
        self.current_player = 0

    def broadcast(self, message):
        for client in self.clients:
            try:
                client.sendall(message.encode())
            except:
                self.clients.remove(client)

    def handle_client(self, client, player_id):
        while True:
            try:
                data = client.recv(1024).decode()
                if not data:
                    break

                action = json.loads(data)
                print(f"Player {player_id} action: {action}")

                if action["type"] == "play":
                    try:
                        self.game.play(player=player_id, card=action["card"], new_color=action.get("new_color"))
                    except ValueError as e:
                        client.sendall(json.dumps({"error": str(e)}).encode())
                        continue

                elif action["type"] == "pick":
                    self.game.play(player=player_id, card=None)

                self.current_player = (self.current_player + 1) % len(self.clients)
                self.broadcast(self.get_game_state())

                if self.game.winner:
                    self.broadcast(json.dumps({"type": "game_over", "winner": self.game.players.index(self.game.winner)}))
                    break

            except Exception as e:
                print(f"Error with player {player_id}: {e}")
                self.clients.remove(client)
                break

    def get_game_state(self):
        state = {
            "type": "state_update",
            "current_card": str(self.game.current_card),
            "current_player": self.current_player,
            "players": [
                {"id": i, "hand_count": len(player.hand)} 
                for i, player in enumerate(self.game.players)
            ],
        }
        return json.dumps(state)

    def start(self):
        while len(self.clients) < 2:
            client, address = self.server.accept()
            self.clients.append(client)
            print(f"Player connected from {address}")
            client.sendall(json.dumps({"type": "wait", "message": "Please wait until another client connects to the game."}).encode())

        # Start the game once two clients are connected
        # self.game = UnoGame(len(self.clients))
        # for i, client in enumerate(self.clients):
        #     client.sendall(json.dumps({"type": "start", "player_id": i}).encode())

        # for i, client in enumerate(self.clients):
        #     threading.Thread(target=self.handle_client, args=(client, i)).start()

if __name__ == "__main__":
    UnoServer().start()
