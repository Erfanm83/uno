import socket
import threading
import json
import os
# import uno_pgz  # This imports the uno_pgz.py file but doesn't run pgzrun.go()

# You can call functions from uno_pgz here if needed
# For example, if you want to trigger specific logic from uno_pgz, you can access the functions defined there.
# uno_pgz.update() or uno_pgz.draw(), if those functions were designed for that purpose.

# Server settings
HOST = '127.0.0.1'  # localhost
PORT = 12345        # Port for the server

# List to keep track of connected clients
clients = []
# Maximum number of clients allowed
MAX_CLIENTS = int(input("Enter the maximum number of clients: "))

# File to store client details
CLIENTS_FILE = "clients_data.json"

# Load existing client data
if os.path.exists(CLIENTS_FILE):
    with open(CLIENTS_FILE, 'r') as file:
        client_data = json.load(file)
else:
    client_data = {} # declare as a dictionary

def save_client_data():
    """Save client data to a file."""
    with open(CLIENTS_FILE, 'w') as file:
        json.dump(client_data, file, indent=4)

def broadcast(message, sender_socket=None):
    """Broadcast a message to all clients except the sender."""
    for client in clients:
        if client != sender_socket:
            try:
                client.send(message)
            except Exception as e:
                print(f"Error sending message: {e}")
                clients.remove(client)

def handle_client(client_socket, user_id):
    """Handle a single client connection."""
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
        if user_id in client_data:
            client_data[user_id]['total_played'] += 1
        print(f"Client {user_id} disconnected")
        clients.remove(client_socket)
        client_socket.close()
        save_client_data()

def start_game():
    """Start the Uno game when all clients are connected."""
    print("Starting Uno Game...")
    os.system('pgzrun uno_pgz.py')

def start_server():
    """Start the chat server."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Server listening on {HOST}:{PORT}")

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
                client_data[username] = {
                    'user_id': user_id,
                    'total_played': 0,
                    'total_wins': 0,
                    'total_defeats': 0
                }

            client_socket.send(f"Welcome {username}! Your User ID is {user_id}.\n".encode('utf-8'))
            clients.append(client_socket)
            client_socket.send(f"Wait for other players to Start Game...\n".encode('utf-8'))
            
            # Start the game when all clients are connected
            if len(clients) == MAX_CLIENTS:
                print("All players connected. Starting the game...")
                threading.Thread(target=start_game).start()

            threading.Thread(target=handle_client, args=(client_socket, user_id)).start()

if __name__ == "__main__":
    start_server()
