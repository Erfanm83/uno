import socket
import threading

# Server settings
HOST = '127.0.0.1'  # Server address
PORT = 12345        # Server port

def receive_messages(client_socket):
    """Receive messages from the server."""
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if message:
                print(message)
        except:
            print("Disconnected from the server.")
            client_socket.close()
            break

def send_messages(client_socket):
    """Send messages to the server."""
    while True:
        message = input()
        try:
            client_socket.send(message.encode('utf-8'))
        except:
            print("Disconnected from the server.")
            client_socket.close()
            break

def start_client():
    """Start the chat client."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    print(f"Connected to server at {HOST}:{PORT}")

    # Start threads for receiving and sending messages
    threading.Thread(target=receive_messages, args=(client_socket,), daemon=True).start()
    send_messages(client_socket)

if __name__ == "__main__":
    start_client()
