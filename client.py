import socket
import threading
import json
from threading import Thread
from time import sleep

def run_game(player_id, state):
    from pgzero.screen import Screen

    WIDTH = 1200
    HEIGHT = 800

    def draw():
        screen.clear()
        screen.fill((255, 255, 255))
        screen.draw.text(f"Player {player_id}", midtop=(WIDTH // 2, 10), color="black")
        screen.draw.text(f"Current Card: {state['current_card']}", midtop=(WIDTH // 2, 50), color="black")

    screen = Screen()
    while True:
        draw()
        sleep(0.1)

def receive_messages(client):
    while True:
        data = client.recv(1024).decode()
        if not data:
            break
        message = json.loads(data)

        if message["type"] == "wait":
            print(message["message"])
        elif message["type"] == "start":
            print(f"Game started! You are Player {message['player_id']}.")
            Thread(target=run_game, args=(message["player_id"], message)).start()
        elif message["type"] == "state_update":
            print(f"Game state updated: {message}")
        elif message["type"] == "game_over":
            print(f"Game over! Winner: Player {message['winner']}")

if __name__ == "__main__":
    host = '127.0.0.1'
    port = 12345

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))

    Thread(target=receive_messages, args=(client,)).start()

    while True:
        action = input("Enter your action (e.g., play 0 red or pick): ")
        try:
            client.sendall(json.dumps({"type": "play", "card": 0, "new_color": "red"}).encode())
        except Exception as e:
            print(f"Error: {e}")
            break
