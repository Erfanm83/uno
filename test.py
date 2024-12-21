import socket
import threading

# Server settings
HOST = '127.0.0.1'  # localhost
PORT = 12345        # Port for the server

# List to keep track of connected clients
clients = []
# Maximum number of clients allowed
MAX_CLIENTS = int(input("Enter the maximum number of clients: "))

def broadcast(message, sender_socket=None):
    """Broadcast a message to all clients except the sender."""
    for client in clients:
        if client != sender_socket:
            try:
                client.send(message)
            except Exception as e:
                print(f"Error sending message: {e}")
                clients.remove(client)

def handle_client(client_socket):
    """Handle a single client connection."""
    while True:
        try:
            message = client_socket.recv(1024)
            if message:
                print(f"Received: {message.decode('utf-8')}")
                broadcast(message, client_socket)
            else:
                break
        except:
            break

    # Remove the client from the list and close the socket
    print("Client disconnected")
    clients.remove(client_socket)
    client_socket.close()

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
            clients.append(client_socket)
            if len(clients) < MAX_CLIENTS:
                broadcast(b"Wait", client_socket)
            threading.Thread(target=handle_client, args=(client_socket,)).start()

if __name__ == "__main__":
    start_server()
