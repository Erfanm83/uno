import socket
import threading
import json
from time import sleep
from random import shuffle, choice
from itertools import product, repeat, chain

# Constants
RECV_BUFFER = 1024
MAXCLIENTS = 0  # To be set dynamically when the server starts
HOST = 'localhost'
PORT = 12345
COLORS = ['red', 'yellow', 'green', 'blue']
NUMBERS = list(range(10)) + list(range(1, 10))
SPECIAL_CARD_TYPES = ['skip', 'reverse', '+2']
COLOR_CARD_TYPES = NUMBERS + SPECIAL_CARD_TYPES * 2
BLACK_CARD_TYPES = ['wildcard', '+4']
CARD_TYPES = NUMBERS + SPECIAL_CARD_TYPES + BLACK_CARD_TYPES

class UnoCard:
    """
    Represents a single Uno Card.
    """
    def __init__(self, color, card_type):
        self.color = color
        self.card_type = card_type
        self.temp_color = None
    
    def __repr__(self):
        return f"<UnoCard object: {self.color} {self.card_type}>"

    def playable(self, other):
        """
        Return True if the other card is playable on top of this card.
        """
        return (
            self.color == other.color or
            self.card_type == other.card_type or
            other.color == 'black'
        )

    def to_dict(self):
        """
        Convert the UnoCard object into a dictionary for JSON serialization.
        """
        return {
            'color': self.color,
            'type': self.card_type
        }

    @staticmethod
    def from_dict(data):
        """
        Create a UnoCard object from a dictionary.
        """
        return UnoCard(data['color'], data['type'])


class UnoPlayer:
    """
    Represents a player in the Uno game.
    """
    def __init__(self, player_name, player_socket):
        self.player_name = player_name
        self.socket = player_socket
        self.hand = []
        self.turn = False

    def to_dict(self):
        """
        Convert the UnoPlayer object into a dictionary for JSON serialization.
        """
        return {
            'name': self.player_name,
            'hand': [card.to_dict() for card in self.hand]  # Convert each card to a dict
        }

    @staticmethod
    def from_dict(data):
        """
        Create an UnoPlayer object from a dictionary.
        """
        player = UnoPlayer(data['name'], None)  # socket is not needed here
        player.hand = [UnoCard.from_dict(card) for card in data['hand']]
        return player

class UnoGame:
    """
    Represents an Uno game. Handles the logic for card play and player turns.
    """
    def __init__(self, players):
        self.players = players
        self.deck = self._create_deck()
        self.card_pile = []
        self.current_player_index = 0
        self.winner = None

    def to_dict(self):
        """
        Convert the UnoGame object into a dictionary for JSON serialization.
        """
        return {
            'current_card': self.card_pile[-1].to_dict() if self.card_pile else None,  # Convert current card
            'players': [player.to_dict() for player in self.players]  # Convert each player
        }

    @staticmethod
    def from_dict(data):
        """
        Create an UnoGame object from a dictionary.
        """
        game = UnoGame([])
        game.card_pile = [UnoCard.from_dict(data['current_card'])] if data['current_card'] else []
        game.players = [UnoPlayer.from_dict(player) for player in data['players']]
        return game

    def _create_deck(self):
        """
        Create a shuffled deck of Uno cards.
        """
        color_cards = product(COLORS, COLOR_CARD_TYPES)
        black_cards = product(repeat('black', 4), BLACK_CARD_TYPES)
        all_cards = chain(color_cards, black_cards)
        deck = [UnoCard(color, card_type) for color, card_type in all_cards]
        shuffle(deck)
        return deck

    def start_game(self):
        """
        Start the game by dealing cards and setting the first card.
        """
        first_card = self.deck.pop()
        if first_card.card_type in ['wildcard', '+4']:
            first_card.color = choice(COLORS)  # Randomly choose color for wildcards
        self.card_pile.append(first_card)

        for player in self.players:
            for _ in range(7):  # Deal 7 cards to each player
                card = self.deck.pop()
                player.hand.append(card)
        
        self.players[0].turn = True  # First player starts

    def next_turn(self):
        """
        Move to the next player's turn.
        """
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        for player in self.players:
            player.turn = False
        self.players[self.current_player_index].turn = True

    def process_card(self, player, card_index, new_color=None):
        """
        Process a player's card play.
        """
        card = player.hand[card_index]
        if not self.card_pile[-1].playable(card):
            return False  # Card cannot be played

        player.hand.pop(card_index)
        self.card_pile.append(card)

        # Special cards processing
        if card.card_type == 'skip':
            self.next_turn()  # Skip the next player
        elif card.card_type == 'reverse':
            self.players.reverse()  # Reverse the order
        elif card.card_type == '+2':
            self.next_turn()
            self.draw_cards(self.players[self.current_player_index], 2)  # Draw 2 cards
        elif card.card_type == '+4':
            self.next_turn()
            self.draw_cards(self.players[self.current_player_index], 4)  # Draw 4 cards
        elif card.card_type == 'wildcard':
            if new_color:
                card.color = new_color  # Set the new color for wild card

        return True

    def draw_cards(self, player, num):
        """
        Draw cards from the deck.
        """
        for _ in range(num):
            if self.deck:
                player.hand.append(self.deck.pop())

    def check_winner(self):
        """
        Check if any player has won.
        """
        for player in self.players:
            if len(player.hand) == 0:
                self.winner = player
                return True
        return False

    def get_game_state(self):
        """
        Return the current game state as a dictionary.
        """
        game_state = {
            'current_card': self.card_pile[-1],
            'players': [
                {
                    'player_name': player.player_name,
                    'hand': [{'color': card.color, 'type': card.card_type} for card in player.hand],
                    'turn': player.turn
                } for player in self.players
            ]
        }
        return game_state


class UnoServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []
        self.max_clients = 0
        self.game = None

    def start_server(self, max_clients):
        """
        Start the server and accept connections.
        """
        self.max_clients = max_clients
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen(self.max_clients)

        print(f"Server started on {HOST}:{PORT} with max {self.max_clients} clients.")
        while len(self.clients) < self.max_clients:
            client_socket, addr = self.server_socket.accept()
            print(f"Connection from {addr}")

            # Receive the player name from the client
            player_name = client_socket.recv(RECV_BUFFER).decode()
            print(f"Player {player_name} connected.")

            # Create a new UnoPlayer instance for the client
            player = UnoPlayer(player_name, client_socket)
            self.clients.append(player)

        # Start the game when all players are connected
        self.start_game()

        for player in self.clients:
            threading.Thread(target=self.handle_client, args=(player.socket, player)).start()

    def handle_client(self, client_socket, player):
        """
        Handle communication with a single client.
        """
        print(f"Handling client: {player.player_name}")
        while not self.game.winner:  # Ensure self.game is initialized
            try:
                message = client_socket.recv(RECV_BUFFER).decode()
                if message:
                    move_data = json.loads(message)
                    print(f"Received move from {player.player_name}: {move_data}")
                    self.process_move(player, move_data)
            except Exception as e:
                print(f"Error handling client {player.player_name}: {e}")
                break

    def start_game(self):
        """
        Initialize and start the Uno game.
        """
        self.game = UnoGame(self.clients)
        self.game.start_game()
        self.broadcast_game_state()

    def process_move(self, player, move_data):
        """
        Process a player's move and update the game state.
        """
        card_index = move_data.get('card_index')
        new_color = move_data.get('new_color')

        # Process the card play
        success = self.game.process_card(player, card_index, new_color)
        if success:
            # Check for winner after each move
            if self.game.check_winner():
                self.broadcast_winner()
            else:
                # Send updated game state to all clients
                self.broadcast_game_state()
                self.game.next_turn()

    def broadcast_game_state(self):
        """
        Send the current game state to all clients.
        """
        game_state = self.game.to_dict()  # Get the game state as a dictionary
        for client in self.clients:
            client.socket.send(json.dumps(game_state).encode())

    def broadcast_winner(self):
        """
        Send the winner message to all clients.
        """
        winner = self.game.winner
        for client in self.clients:
            client.socket.send(json.dumps({"winner": winner.player_name}).encode())
        print(f"Game over! {winner.player_name} wins!")


if __name__ == "__main__":
    server = UnoServer()

    # Ask for maximum number of clients
    MAXCLIENTS = int(input("Enter maximum number of players: "))
    server.start_server(MAXCLIENTS)
