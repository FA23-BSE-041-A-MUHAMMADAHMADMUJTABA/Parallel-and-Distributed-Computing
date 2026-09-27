"""
================================================================================
COURSE: Parallel and Distributed Computing (CSC-334)
LAB 03: Socket Programming with Multi-Threading
SCRIPT: server.py (Multi-Threaded TCP Server)
================================================================================
Student Name    : Muhammad Ahmad Mujtaba
Registration No : FA23-BSE-041
Class & Section : BSE 7A (Software Engineering)
================================================================================
Key Features:
- Multi-Threaded: Spawns a dedicated threading.Thread for every incoming client.
- Simultaneous Client Handling: Serves multiple clients concurrently without blocking.
- Real-time Output: Prints Active Thread Name, Client IP, Port Number, and Active Count.
- Thread Synchronization: Uses threading.Lock with explicit acquire() and release()
  to protect shared resources (terminal prints and client registry state).
- Continuous Exchange: Keeps communication open until client sends 'exit' or disconnects.
================================================================================
"""

import socket
import threading
import sys
import time

# Server Network Configuration
HOST = '127.0.0.1'  # Localhost
PORT = 8888         # Port to listen on
BUFFER_SIZE = 1024  # Buffer size for incoming messages

# ------------------------------------------------------------------------------
# Thread Synchronization Locks
# ------------------------------------------------------------------------------
# 1. print_lock: Prevents scrambled/interleaved terminal output from concurrent threads.
# 2. state_lock: Synchronizes access to shared client tracking data structures.
print_lock = threading.Lock()
state_lock = threading.Lock()

# Shared Global State (Protected by state_lock)
connected_clients = {}  # Format: {client_id: {"ip": ip, "port": port, "thread": name}}
client_counter = 0


def safe_print(*args, **kwargs):
    """
    Thread-safe print function using explicit acquire() and release() on print_lock.
    Ensures that messages from multiple concurrent threads do not garble each other.
    """
    print_lock.acquire()
    try:
        print(*args, **kwargs)
        sys.stdout.flush()
    finally:
        print_lock.release()


def handle_client(client_socket, client_address, client_id):
    """
    Client handler function executed in an independent thread for each client.
    Handles continuous two-way communication until the client requests to exit.
    
    Parameters:
        client_socket  : The socket object for the connected client
        client_address : Tuple containing (client_ip, client_port)
        client_id      : Unique sequential integer ID assigned to the client
    """
    current_thread = threading.current_thread()
    thread_name = current_thread.name
    client_ip, client_port = client_address

    # --------------------------------------------------------------------------
    # 1. Thread Synchronization: Register client in shared state
    # --------------------------------------------------------------------------
    state_lock.acquire()
    try:
        connected_clients[client_id] = {
            "ip": client_ip,
            "port": client_port,
            "thread_name": thread_name,
            "connected_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        total_active_clients = len(connected_clients)
    finally:
        state_lock.release()

    # Display connection details with thread info
    safe_print(f"\n{'='*65}")
    safe_print(f"[+] NEW CLIENT CONNECTED SUCCESSFULLY!")
    safe_print(f"    - Active Thread Name  : {thread_name}")
    safe_print(f"    - Client IP Address   : {client_ip}")
    safe_print(f"    - Client Port Number  : {client_port}")
    safe_print(f"    - Client ID Assigned  : #{client_id}")
    safe_print(f"    - Total Active Threads: {threading.active_count()} (Clients Connected: {total_active_clients})")
    safe_print(f"{'='*65}\n")

    # Send welcome acknowledgment to the client
    welcome_msg = (
        f"Server: Welcome Client #{client_id}! Connected via {thread_name} at ({client_ip}:{client_port}).\n"
        f"Type any message to communicate, or type 'exit' / 'quit' to disconnect."
    )
    try:
        client_socket.sendall(welcome_msg.encode('utf-8'))
    except (socket.error, BrokenPipeError):
        pass

    # --------------------------------------------------------------------------
    # 2. Continuous message exchange loop
    # --------------------------------------------------------------------------
    message_count = 0
    try:
        while True:
            # Receive data from client (blocking only on this specific client thread)
            raw_data = client_socket.recv(BUFFER_SIZE)
            
            # If recv returns empty bytes, client has closed the socket connection
            if not raw_data:
                safe_print(f"[-] Client #{client_id} ({client_ip}:{client_port}) disconnected abruptly (EOF).")
                break

            client_message = raw_data.decode('utf-8').strip()
            message_count += 1

            # Log received message with Thread Name, Client IP, and Port
            safe_print(f"[{thread_name}] Message #{message_count} from Client #{client_id} ({client_ip}:{client_port}): {client_message}")

            # Check for termination command from client
            if client_message.lower() in ['exit', 'quit', 'bye']:
                farewell_msg = f"Server: Goodbye Client #{client_id}! Connection closed on {thread_name}."
                try:
                    client_socket.sendall(farewell_msg.encode('utf-8'))
                except (socket.error, BrokenPipeError):
                    pass
                safe_print(f"[*] Client #{client_id} sent exit signal ('{client_message}'). Initiating thread cleanup.")
                break

            # Send response back to the client
            server_response = (
                f"Server ACK [Thread: {thread_name} | Client #{client_id}]: "
                f"Received '{client_message}' (Length: {len(client_message)} chars)"
            )
            client_socket.sendall(server_response.encode('utf-8'))

    except ConnectionResetError:
        safe_print(f"[-] Connection forcibly reset by Client #{client_id} ({client_ip}:{client_port}).")
    except Exception as e:
        safe_print(f"[!] Exception occurred in {thread_name} for Client #{client_id}: {e}")
    finally:
        # ----------------------------------------------------------------------
        # 3. Clean up: Close socket and update shared state using Lock
        # ----------------------------------------------------------------------
        try:
            client_socket.close()
        except Exception:
            pass

        state_lock.acquire()
        try:
            if client_id in connected_clients:
                del connected_clients[client_id]
            remaining_clients = len(connected_clients)
        finally:
            state_lock.release()

        safe_print(f"\n{'-'*65}")
        safe_print(f"[-] THREAD TERMINATED: {thread_name}")
        safe_print(f"    - Client ID: #{client_id} ({client_ip}:{client_port}) has disconnected.")
        safe_print(f"    - Remaining Active Clients: {remaining_clients}")
        safe_print(f"    - Total Living Threads    : {threading.active_count() - 1}")
        safe_print(f"{'-'*65}\n")


def start_server():
    """
    Initializes the TCP Server, binds to HOST:PORT, and enters the accept loop.
    For each incoming connection, instantiates and launches a new threading.Thread.
    """
    global client_counter

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Enable address reuse so server can restart without waiting for OS socket release
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((HOST, PORT))
    except Exception as e:
        print(f"[ERROR] Failed to bind to {HOST}:{PORT} -> {e}")
        sys.exit(1)

    server_socket.listen(10)  # Backlog of 10 incoming connections
    print("=" * 70)
    print("      CSC-334: MULTI-THREADED TCP SERVER STARTED")
    print(f"      Listening on IP: {HOST} | Port: {PORT}")
    print(f"      Main Listener Thread: {threading.current_thread().name}")
    print("      Waiting for incoming client connections... (Press Ctrl+C to stop)")
    print("=" * 70)

    try:
        while True:
            # accept() blocks until a new client connects
            client_socket, client_address = server_socket.accept()
            
            # Increment client counter safely with lock
            state_lock.acquire()
            try:
                client_counter += 1
                assigned_id = client_counter
            finally:
                state_lock.release()

            # Create a dedicated thread for the newly connected client
            thread_name = f"ClientThread-{assigned_id}-Port{client_address[1]}"
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address, assigned_id),
                name=thread_name,
                daemon=True
            )
            
            # Start the thread execution
            client_thread.start()

            safe_print(f"[MAIN THREAD] Spawned and started {thread_name} for {client_address[0]}:{client_address[1]}")

    except KeyboardInterrupt:
        print("\n[!] KeyboardInterrupt received. Shutting down server gracefully...")
    finally:
        server_socket.close()
        print("[!] Server socket closed. Main thread terminated.")


if __name__ == '__main__':
    start_server()
