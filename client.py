import socket
import threading
import json
from time import sleep
import pgzrun
from pgzero.actor import Actor
from pgzero.screen import Screen

COLORS = ['red', 'yellow', 'green', 'blue']

# Define the size of the game screen
WIDTH = 1200
HEIGHT = 800

# Server settings
HOST = '127.0.0.1'  # Server address
PORT = 12345        # Server port

# Game assets
color_imgs = {color: Actor(color) for color in COLORS}
deck_img = Actor('back')

# Initialize game data
game_data = {}

# Global variables for client_socket and screen (will be initialized later)
client_socket = None

def receive_messages():
    """Receive game data from the server and update the game state."""
    global client_socket, game_data
    while True:
        try:
            print("gorgali client")
            # Receive game data from server
            # server_data = client_socket.recv(2048).decode('utf-8')
            # updated_data = json.loads(server_data)
            # print(f"Received gameData from server: {updated_data}")

            # Update local game state with received data
            # game_data.update(updated_data)
            # update_game_display()
        except Exception as e:
            print(f"Error receiving data from server: {e}")
            client_socket.close()
            break

def send_move(selected_card=None, selected_color=None):
    """Send the player's move to the server."""
    move = {
        'selected_card': selected_card,
        'selected_color': selected_color
    }
    client_socket.send(json.dumps(move).encode('utf-8'))

def on_mouse_down(pos):
    """Handle user interactions and send updated game data."""
    if game_data.get('is_current_player', False):
        for i, card in enumerate(game_data['players'][game_data['player_index']]['hand']):
            sprite = Actor(f"{card['color']}_{card['type']}")
            sprite.pos = (130 + i * 80, 330 + game_data['player_index'] * 130)
            if sprite.collidepoint(pos):
                game_data['selected_card'] = i
                print(f"Selected card: {card} at index {i}")
                break
        if deck_img.collidepoint(pos):
            game_data['selected_card'] = None  # Indicate picking up a card
            print("Selected to pick up a card.")
        for color, sprite in color_imgs.items():
            if sprite.collidepoint(pos):
                game_data['selected_color'] = color
                game_data['color_selection_required'] = False
                print(f"Selected color: {color}")

def start_client():
    """Start the chat client."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    print(f"Connected to server at {HOST}:{PORT}")

    # Start threads for receiving and sending messages
    threading.Thread(target=receive_messages, args=(client_socket,), daemon=True).start()

if __name__ == "__main__":
    start_client()
