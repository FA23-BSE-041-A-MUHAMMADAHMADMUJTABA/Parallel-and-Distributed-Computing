"""
================================================================================
COURSE: Parallel and Distributed Computing (CSC-334)
LAB 03: Socket Programming with Multi-Threading
SCRIPT: client.py (Continuous Interactive TCP Client)
================================================================================
Student Name    : Muhammad Ahmad Mujtaba
Registration No : FA23-BSE-041
Class & Section : BSE 7A (Software Engineering)
================================================================================
Key Features:
- Connects to Multi-Threaded TCP Server on 127.0.0.1:8888.
- Continuous Communication: Interactively sends messages in a continuous loop.
- Termination: Exits cleanly when user inputs 'exit' or 'quit'.
- Displays local IP/Port and Server responses in real time.
================================================================================
"""

import socket
import sys

# Network Configuration
HOST = '127.0.0.1'  # Server IP
PORT = 8888         # Server Port
BUFFER_SIZE = 1024  # Buffer size for receiving data


def run_client():
    """
    Connects to the multi-threaded server and enters a continuous communication loop.
    Allows user to send multiple messages until typing 'exit' or 'quit'.
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        print(f"[*] Attempting to connect to server at {HOST}:{PORT}...")
        client_socket.connect((HOST, PORT))
        local_ip, local_port = client_socket.getsockname()

        print(f"\n{'='*65}")
        print(f"[+] CONNECTED TO SERVER SUCCESSFULLY!")
        print(f"    - Assigned Local Socket : {local_ip}:{local_port}")
        print(f"    - Connected to Server   : {HOST}:{PORT}")
        print(f"{'='*65}\n")

        # Receive and display the initial welcome banner from server
        try:
            welcome_msg = client_socket.recv(BUFFER_SIZE).decode('utf-8')
            print(f"{welcome_msg}\n")
        except socket.error:
            pass

        print("Enter messages to send to the server.")
        print("Type 'exit' or 'quit' anytime to disconnect.\n")

        # Continuous message exchange loop
        while True:
            try:
                user_msg = input("Enter message > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[!] Disconnection requested by user.")
                user_msg = "exit"

            # Skip empty inputs
            if not user_msg:
                continue

            # Send the message to server
            try:
                client_socket.sendall(user_msg.encode('utf-8'))
            except (socket.error, BrokenPipeError) as e:
                print(f"[!] Error sending data to server: {e}")
                break

            # Handle termination condition
            if user_msg.lower() in ['exit', 'quit', 'bye']:
                try:
                    farewell = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                    if farewell:
                        print(f"\n{farewell}")
                except socket.error:
                    pass
                print("[*] Disconnected successfully. Exiting client...")
                break

            # Receive and display the server's response
            try:
                response = client_socket.recv(BUFFER_SIZE)
                if not response:
                    print("\n[-] Server closed the connection unexpectedly.")
                    break
                print(f"[SERVER REPLY] {response.decode('utf-8')}\n")
            except socket.error as e:
                print(f"[!] Error receiving response from server: {e}")
                break

    except ConnectionRefusedError:
        print(f"[ERROR] Could not connect to server at {HOST}:{PORT}.")
        print("        Please ensure 'server.py' is running before starting the client.")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
    finally:
        client_socket.close()
        print("[*] Client socket closed.")


if __name__ == '__main__':
    run_client()
