import socket
import json
import pygame
from pygame.locals import *
from time import sleep

# Constants
RECV_BUFFER = 1024
HOST = 'localhost'
PORT = 12345
WIDTH, HEIGHT = 800, 600
CARD_WIDTH, CARD_HEIGHT = 100, 150

# Initialize Pygame
pygame.init()

# Colors for pygame
COLORS = {'red': (255, 0, 0), 'yellow': (255, 255, 0), 'green': (0, 255, 0), 'blue': (0, 0, 255), 'black': (0, 0, 0)}

# Font for text rendering
FONT = pygame.font.SysFont('Arial', 24)

class UnoClient:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.player_name = ''
        self.game_state = None
        self.current_card = None
        self.player_hand = []
        self.turn = False
        self.your_turn = False
        self.winner = None

    def create_socket(self, hostname, port):
        """
        Connect to the server and create the socket.
        """
        self.client_socket.connect((hostname, port))
        print(f"Connected to server at {hostname}:{port}")

    def join_game(self, player_name):
        """
        Join the game by sending player name to the server.
        """
        self.player_name = player_name
        self.client_socket.send(player_name.encode())
        print(f"Joined game as {player_name}")

    def start_game(self):
        """
        Start the game by receiving the initial game state.
        """
        print("starting game....")
        game_data = self.client_socket.recv(RECV_BUFFER).decode()
        self.game_state = json.loads(game_data)
        self.update_game_state(self.game_state)

    def update_game_state(self, game_state):
        """
        Update the game state and check if it is the player's turn.
        """
        self.game_state = game_state
        self.current_card = game_state['current_card']
        self.player_hand = game_state['players'][0]['hand']  # Assume the first player is us for now
        # self.turn = game_state['players'][0]['turn']  # Set our turn based on the first player
        # self.your_turn = self.turn  # Set if it's our turn

    def send_card(self, card_index, new_color=None):
        """
        Send the selected card to the server along with the updated hand.
        """
        card = self.player_hand[card_index]
        card_data = {
            'card_index': card_index,
            'hand': self.player_hand,
            'new_color': new_color if card['type'] in ['wildcard', '+4'] else None
        }
        self.client_socket.send(json.dumps(card_data).encode())

    def receive_game_state(self):
        """
        Receive updated game state from the server.
        """
        game_data = self.client_socket.recv(RECV_BUFFER).decode()
        game_state = json.loads(game_data)
        self.update_game_state(game_state)

    # def check_for_winner(self):
    #     """
    #     Check if there is a winner in the game.
    #     """
    #     if self.game_state.get('winner'):
    #         self.winner = self.game_state['winner']
    #         print(f"Game over! {self.winner} wins!")

    def get_current_card(self):
        return self.current_card

    def get_player_hand(self):
        return self.player_hand

class UnoClientGUI:
    def __init__(self):
        self.client = UnoClient()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Uno Game')
        self.clock = pygame.time.Clock()

    def draw_game_state(self):
        """
        Draw the current game state on the screen.
        """
        self.screen.fill((255, 255, 255))  # White background
        self.draw_current_card()
        self.draw_player_hand()
        self.draw_turn_indicator()
        self.draw_game_log()

    def draw_current_card(self):
        """
        Draw the current card on the pile.
        """
        if self.client.get_current_card():
            card = self.client.get_current_card()
            color = COLORS.get(card['color'], (0, 0, 0))  # Default to black if no color
            pygame.draw.rect(self.screen, color, (WIDTH // 2 - CARD_WIDTH // 2, 50, CARD_WIDTH, CARD_HEIGHT))
            text = FONT.render(f'{card["type"]}', True, (255, 255, 255))
            self.screen.blit(text, (WIDTH // 2 - text.get_width() // 2, 50 + CARD_HEIGHT // 2))

    def draw_player_hand(self):
        """
        Draw the player's hand of cards.
        """
        player_hand = self.client.get_player_hand()
        x_offset = 50
        for card in player_hand:
            color = COLORS.get(card['color'], (0, 0, 0))  # Default to black if no color
            pygame.draw.rect(self.screen, color, (x_offset, HEIGHT - CARD_HEIGHT - 50, CARD_WIDTH, CARD_HEIGHT))
            text = FONT.render(f'{card["type"]}', True, (255, 255, 255))
            self.screen.blit(text, (x_offset + (CARD_WIDTH - text.get_width()) // 2, HEIGHT - CARD_HEIGHT - 50 + CARD_HEIGHT // 2))
            x_offset += CARD_WIDTH + 20

    def draw_turn_indicator(self):
        """
        Draw a visual indicator showing whose turn it is.
        """
        if self.client.your_turn:
            turn_text = FONT.render('Your Turn!', True, (0, 255, 0))
        else:
            turn_text = FONT.render('Waiting for other players...', True, (255, 0, 0))
        self.screen.blit(turn_text, (WIDTH // 2 - turn_text.get_width() // 2, HEIGHT - 100))

    def draw_game_log(self):
        """
        Draw a log or status text for the game.
        """
        status_text = FONT.render(f"Current Card: {self.client.get_current_card()['type']}", True, (0, 0, 0))
        self.screen.blit(status_text, (10, 10))

    def handle_events(self):
        """
        Handle user input events.
        """
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                quit()
            if event.type == MOUSEBUTTONDOWN and self.client.your_turn:
                if event.button == 1:  # Left mouse button
                    x, y = event.pos
                    # Check if player clicked on a card in their hand
                    card_index = self.get_card_index_at_position(x, y)
                    if card_index is not None:
                        self.client.send_card(card_index)

    def get_card_index_at_position(self, x, y):
        """
        Determine the card clicked by checking the mouse position.
        """
        player_hand = self.client.get_player_hand()
        x_offset = 50
        for idx, card in enumerate(player_hand):
            card_rect = pygame.Rect(x_offset, HEIGHT - CARD_HEIGHT - 50, CARD_WIDTH, CARD_HEIGHT)
            if card_rect.collidepoint(x, y):
                return idx
            x_offset += CARD_WIDTH + 20
        return None

    def run(self):
        """
        Main loop for the game client.
        """
        while True:
            self.handle_events()

            # Update game state from server if needed
            if self.client.your_turn:
                self.client.receive_game_state()

            # Draw everything
            self.draw_game_state()
            pygame.display.update()

            # Wait a bit to make the game responsive
            self.clock.tick(30)

if __name__ == '__main__':
    # Create the client instance
    client_gui = UnoClientGUI()

    # Ask for the player name
    player_name = input("Enter your username: ")

    # Connect to the server
    client_gui.client.create_socket(HOST, PORT)
    client_gui.client.join_game(player_name)
    client_gui.client.start_game()

    # Run the game loop
    client_gui.run()
