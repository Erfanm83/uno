from random import shuffle, choice, randint
from itertools import product, repeat, chain
from threading import Thread
from time import sleep

import socket
import threading
import json
import os

from pgzero.actor import Actor
from pgzero.screen import Screen

COLORS = ['red', 'yellow', 'green', 'blue']
ALL_COLORS = COLORS + ['black']
NUMBERS = list(range(10)) + list(range(1, 10))
SPECIAL_CARD_TYPES = ['skip', 'reverse', '+2']
COLOR_CARD_TYPES = NUMBERS + SPECIAL_CARD_TYPES * 2
BLACK_CARD_TYPES = ['wildcard', '+4']
CARD_TYPES = NUMBERS + SPECIAL_CARD_TYPES + BLACK_CARD_TYPES

# Server settings
HOST = '127.0.0.1'  # localhost
PORT = 12345        # Port for the server

# List to keep track of connected clients
clients = []

WIDTH = 1200
HEIGHT = 800

# Maximum number of clients allowed
MAX_CLIENTS = int(input("Enter the maximum number of clients: "))

# File to store client details
CLIENTS_FILE = "clients_data.json"

# Global variables
game_data = None
num_players = MAX_CLIENTS
# deck_img = Actor('back')
# color_imgs = {color: Actor(color) for color in COLORS}

class UnoCard:
    """
    Represents a single Uno Card, given a valid color and card type.

    color: string
    card_type: string/int

    >>> card = UnoCard('red', 5)
    """
    def __init__(self, color, card_type):
        self._validate(color, card_type)
        self.color = color
        self.card_type = card_type
        self.temp_color = None
        self.sprite = Actor('{}_{}'.format(color, card_type))

    def __repr__(self):
        return '<UnoCard object: {} {}>'.format(self.color, self.card_type)

    def __str__(self):
        return '{}{}'.format(self.color_short, self.card_type_short)

    def __format__(self, f):
        if f == 'full':
            return '{} {}'.format(self.color, self.card_type)
        else:
            return str(self)

    def __eq__(self, other):
        return self.color == other.color and self.card_type == other.card_type

    def _validate(self, color, card_type):
        """
        Check the card is valid, raise exception if not.
        """
        if color not in ALL_COLORS:
            raise ValueError('Invalid color')
        if color == 'black' and card_type not in BLACK_CARD_TYPES:
            raise ValueError('Invalid card type')
        if color != 'black' and card_type not in COLOR_CARD_TYPES:
            raise ValueError('Invalid card type')

    @property
    def color_short(self):
        return self.color[0].upper()

    @property
    def card_type_short(self):
        if self.card_type in ('skip', 'reverse', 'wildcard'):
            return self.card_type[0].upper()
        else:
            return self.card_type

    @property
    def _color(self):
        return self.temp_color if self.temp_color else self.color

    @property
    def temp_color(self):
        return self._temp_color

    @temp_color.setter
    def temp_color(self, color):
        if color is not None:
            if color not in COLORS:
                raise ValueError('Invalid color')
        self._temp_color = color

    def playable(self, other):
        """
        Return True if the other card is playable on top of this card,
        otherwise return False
        """
        return (
            self._color == other.color or
            self.card_type == other.card_type or
            other.color == 'black'
        )


class UnoPlayer:
    """
    Represents a player in an Uno game. A player is created with a list of 7
    Uno cards.

    cards: list of 7 UnoCards
    player_id: int/str (default: None)

    >>> cards = [UnoCard('red', n) for n in range(7)]
    >>> player = UnoPlayer(cards)
    """
    def __init__(self, cards, player_id=None):
        if len(cards) != 7:
            raise ValueError(
                'Invalid player: must be initalised with 7 UnoCards'
            )
        if not all(isinstance(card, UnoCard) for card in cards):
            raise ValueError(
                'Invalid player: cards must all be UnoCard objects'
            )
        self.hand = cards
        self.player_id = player_id

    def __repr__(self):
        if self.player_id is not None:
            return '<UnoPlayer object: player {}>'.format(self.player_id)
        else:
            return '<UnoPlayer object>'

    def __str__(self):
        if self.player_id is not None:
            return str(self.player_id)
        else:
            return repr(self)

    def can_play(self, current_card):
        """
        Return True if the player has any playable cards (on top of the current
        card provided), otherwise return False
        """
        return any(current_card.playable(card) for card in self.hand)


class UnoGame:
    """
    Represents an Uno game.

    players: int
    random: bool (default: True)

    >>> game = UnoGame(5)
    """
    def __init__(self, players, random=True):
        if not isinstance(players, int):
            raise ValueError('Invalid game: players must be integer')
        if not 2 <= players <= 15:
            raise ValueError('Invalid game: must be between 2 and 15 players')
        self.deck = self._create_deck(random=random)
        self.players = [
            UnoPlayer(self._deal_hand(), n) for n in range(players)
        ]
        self._player_cycle = ReversibleCycle(self.players)
        self._current_player = next(self._player_cycle)
        self._winner = None
        self._check_first_card()

    def __next__(self):
        """
        Iteration sets the current player to the next player in the cycle.
        """
        self._current_player = next(self._player_cycle)

    def _create_deck(self, random):
        """
        Return a list of the complete set of Uno Cards. If random is True, the
        deck will be shuffled, otherwise will be unshuffled.
        """
        color_cards = product(COLORS, COLOR_CARD_TYPES)
        black_cards = product(repeat('black', 4), BLACK_CARD_TYPES)
        all_cards = chain(color_cards, black_cards)
        deck = [UnoCard(color, card_type) for color, card_type in all_cards]
        if random:
            shuffle(deck)
            return deck
        else:
            return list(reversed(deck))

    def _deal_hand(self):
        """
        Return a list of 7 cards from the top of the deck, and remove these
        from the deck.
        """
        return [self.deck.pop() for i in range(7)]

    @property
    def current_card(self):
        return self.deck[-1]

    @property
    def is_active(self):
        return all(len(player.hand) > 0 for player in self.players)

    @property
    def current_player(self):
        return self._current_player

    @property
    def winner(self):
        return self._winner

    def play(self, player, card=None, new_color=None):
        """
        Process the player playing a card.

        player: int representing player index number
        card: int representing index number of card in player's hand

        It must be player's turn, and if card is given, it must be playable.
        If card is not given (None), the player picks up a card from the deck.

        If game is over, raise an exception.
        """
        if not isinstance(player, int):
            raise ValueError('Invalid player: should be the index number')
        if not 0 <= player < len(self.players):
            raise ValueError('Invalid player: index out of range')
        _player = self.players[player]
        if self.current_player != _player:
            raise ValueError('Invalid player: not their turn')
        if card is None:
            self._pick_up(_player, 1)
            next(self)
            return
        _card = _player.hand[card]
        if not self.current_card.playable(_card):
            raise ValueError(
                'Invalid card: {} not playable on {}'.format(
                    _card, self.current_card
                )
            )
        if _card.color == 'black':
            if new_color not in COLORS:
                raise ValueError(
                    'Invalid new_color: must be red, yellow, green or blue'
                )
        if not self.is_active:
            raise ValueError('Game is over')

        played_card = _player.hand.pop(card)
        self.deck.append(played_card)

        card_color = played_card.color
        card_type = played_card.card_type
        if card_color == 'black':
            self.current_card.temp_color = new_color
            if card_type == '+4':
                next(self)
                self._pick_up(self.current_player, 4)
        elif card_type == 'reverse':
            self._player_cycle.reverse()
        elif card_type == 'skip':
            next(self)
        elif card_type == '+2':
            next(self)
            self._pick_up(self.current_player, 2)

        if self.is_active:
            next(self)
        else:
            self._winner = _player
            self._print_winner()

    def _print_winner(self):
        """
        Print the winner name if available, otherwise look up the index number.
        """
        if self.winner.player_id:
            winner_name = self.winner.player_id
        else:
            winner_name = self.players.index(self.winner)
        print("Player {} wins!".format(winner_name))

    def _pick_up(self, player, n):
        """
        Take n cards from the bottom of the deck and add it to the player's
        hand.

        player: UnoPlayer
        n: int
        """
        penalty_cards = [self.deck.pop(0) for i in range(n)]
        player.hand.extend(penalty_cards)

    def _check_first_card(self):
        if self.current_card.color == 'black':
            color = choice(COLORS)
            self.current_card.temp_color = color
            print("Selected random color for black card: {}".format(color))


class ReversibleCycle:
    """
    Represents an interface to an iterable which can be infinitely cycled (like
    itertools.cycle), and can be reversed.

    Starts at the first item (index 0), unless reversed before first iteration,
    in which case starts at the last item.

    iterable: any finite iterable

    >>> rc = ReversibleCycle(range(3))
    >>> next(rc)
    0
    >>> next(rc)
    1
    >>> rc.reverse()
    >>> next(rc)
    0
    >>> next(rc)
    2
    """
    def __init__(self, iterable):
        self._items = list(iterable)
        self._pos = None
        self._reverse = False

    def __next__(self):
        if self.pos is None:
            self.pos = -1 if self._reverse else 0
        else:
            self.pos = self.pos + self._delta
        return self._items[self.pos]

    @property
    def _delta(self):
        return -1 if self._reverse else 1

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, value):
        self._pos = value % len(self._items)

    def reverse(self):
        """
        Reverse the order of the iterable.
        """
        self._reverse = not self._reverse


class GameData:
    def __init__(self):
        self.selected_card = None
        self.selected_color = None
        self.color_selection_required = False
        self.log = ''

    @property
    def selected_card(self):
        selected_card = self._selected_card
        self.selected_card = None
        return selected_card

    @selected_card.setter
    def selected_card(self, value):
        self._selected_card = value

    @property
    def selected_color(self):
        selected_color = self._selected_color
        self.selected_color = None
        return selected_color

    @selected_color.setter
    def selected_color(self, value):
        self._selected_color = value

# game_data = GameData()

class AIUnoGame:
    def __init__(self, players):
        self.game = UnoGame(players)
        self.player = choice(self.game.players)
        self.player_index = self.game.players.index(self.player)
        print('The game begins. You are Player {}.'.format(self.player_index))

    def __next__(self):
        game = self.game
        player = game.current_player
        player_id = player.player_id
        current_card = game.current_card
        if player == self.player:
            played = False
            while not played:
                card_index = None
                while card_index is None:
                    card_index = game_data.selected_card
                new_color = None
                if card_index is not False:
                    card = player.hand[card_index]
                    if not game.current_card.playable(card):
                        game_data.log = 'You cannot play that card'
                        continue
                    else:
                        game_data.log = 'You played card {:full}'.format(card)
                        if card.color == 'black' and len(player.hand) > 1:
                            game_data.color_selection_required = True
                            while new_color is None:
                                new_color = game_data.selected_color
                            game_data.log = 'You selected {}'.format(new_color)
                else:
                    card_index = None
                    game_data.log = 'You picked up'
                game.play(player_id, card_index, new_color)
                played = True
        elif player.can_play(game.current_card):
            for i, card in enumerate(player.hand):
                if game.current_card.playable(card):
                    if card.color == 'black':
                        new_color = choice(COLORS)
                    else:
                        new_color = None
                    game_data.log = "Player {} played {:full}".format(player, card)
                    game.play(player=player_id, card=i, new_color=new_color)
                    break
        else:
            game_data.log = "Player {} picked up".format(player)
            game.play(player=player_id, card=None)


    def print_hand(self):
        print('Your hand: {}'.format(
            ' '.join(str(card) for card in self.player.hand)
        ))

# game = AIUnoGame(MAX_CLIENTS)

def draw_deck():
    deck_img.pos = (130, 70)
    deck_img.draw()
    current_card = game.game.current_card
    current_card.sprite.pos = (210, 70)
    current_card.sprite.draw()
    if game_data.color_selection_required:
        for i, card in enumerate(color_imgs.values()):
            card.pos = (290+i*80, 70)
            card.draw()
    elif current_card.color == 'black' and current_card.temp_color is not None:
        color_img = color_imgs[current_card.temp_color]
        color_img.pos = (290, 70)
        color_img.draw()

def draw_players_hands():
    for p, player in enumerate(game.game.players):
        color = 'red' if player == game.game.current_player else 'black'
        text = 'P{} {}'.format(p, 'wins' if game.game.winner == player else '')
        screen.draw.text(text, (0, 300+p*130), fontsize=100, color=color)
        for c, card in enumerate(player.hand):
            if player == game.player:
                sprite = card.sprite
            else:
                sprite = Actor('back')
            sprite.pos = (130+c*80, 330+p*130)
            sprite.draw()

def show_log():
    screen.draw.text(game_data.log, midbottom=(WIDTH/2, HEIGHT-50), color='black')

def update():
    screen.clear()
    screen.fill((255, 255, 255))
    draw_deck()
    draw_players_hands()
    show_log()

def on_mouse_down(pos):
    if game.player == game.game.current_player:
        for card in game.player.hand:
            if card.sprite.collidepoint(pos):
                game_data.selected_card = game.player.hand.index(card)
                print('Selected card {} index {}'.format(card, game.player.hand.index(card)))
        if deck_img.collidepoint(pos):
            game_data.selected_card = False
            print('Selected pick up')
        for color, card in color_imgs.items():
            if card.collidepoint(pos):
                game_data.selected_color = color
                game_data.color_selection_required = False

# Load existing client data
if os.path.exists(CLIENTS_FILE):
    with open(CLIENTS_FILE, 'r') as file:
        client_data = json.load(file)
else:
    client_data = {} # declare as a dictionary


def save_client_data():
    """Save client data to the JSON file."""
    try:
        with open(CLIENTS_FILE, 'w') as file:
            json.dump(client_data, file, indent=4)
        print("Client data saved.")
    except Exception as e:
        print(f"Error saving client data: {e}")

def update_client_data(username, user_id, played, wins, defeats):
    """Update client data for a user and save it."""
    if username in client_data:
        client_data[username]['total_played'] += 1
    else:
        client_data[username] = {
            'user_id': user_id,
            'total_played': played,
            'total_wins': wins,
            'total_defeats': defeats
        }
    save_client_data()


def broadcast(message, sender_socket=None):
    """Broadcast a message to all clients except the sender."""
    for client in clients:
        if client != sender_socket:
            try:
                client.send(message)
            except Exception as e:
                print(f"Error sending message: {e}")
                clients.remove(client)

def handle_client(client_socket, username):
    """
    Handles communication with a single client.
    """
    user_id = client_data[username]['user_id']
    try:
        while True:
            message = client_socket.recv(1024)

            if message:
                print(f"Received from {user_id}: {message.decode('utf-8')}")
                broadcast(message, client_socket)
            else:
                break
    except:
        pass
    finally:
        # Update client data on exit
        # if user_id in client_data:
        #     print("gorgali")
        #     # update_client_data(user_id, user_id)
        #     # client_data[user_id]['total_played'] += 1
        print(f"Client {user_id} disconnected")
        clients.remove(client_socket)
        client_socket.close()
        # save_client_data()

def start_game():
    """Start the Uno game when all clients are connected."""
    # global game_data, num_players, game

    print("Starting Uno Game...")
    # os.system('pgzrun uno_pgz.py')
    
    # game = AIUnoGame(num_players)

    # deck_img = Actor('back')
    # color_imgs = {color: Actor(color) for color in COLORS}

    # def game_loop():
    #     while game.game.is_active:
    #         sleep(1)
    #         next(game)

    # game_loop_thread = Thread(target=game_loop)
    # game_loop_thread.start()

def start_server():
    """Start the chat server."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(MAX_CLIENTS)
    print(f"UNO Server is listening on {HOST}:{PORT}")

    while True:
        client_socket, client_address = server.accept()

        if len(clients) >= MAX_CLIENTS:
            print(f"Capacity reached. Rejecting connection from {client_address}")
            client_socket.send(b"Server is at full capacity. Please try again later.")
            client_socket.close()
        else:
            print(f"New connection from {client_address}")

            # Ask for username
            client_socket.send(b"Enter your username: ")
            username = client_socket.recv(1024).decode('utf-8').strip()

            # Assign a unique ID
            if username in client_data:
                user_id = client_data[username]['user_id']
            else:
                user_id = str(len(client_data) + 1)
                update_client_data(username, user_id, 1, 0, 0)

            client_socket.send(f"Welcome {username}! Your User ID is {user_id}.\n".encode('utf-8'))
            clients.append(client_socket)
            client_socket.send(f"Wait for other players to Start Game...\n".encode('utf-8'))
            
            # Start the game when all clients are connected
            if len(clients) == MAX_CLIENTS:
                print("All players connected. Starting the game...")
                threading.Thread(target=start_game).start()

            # threading.Thread(target=handle_client, args=(client_socket, user_id)).start()

if __name__ == "__main__":
    start_server()
