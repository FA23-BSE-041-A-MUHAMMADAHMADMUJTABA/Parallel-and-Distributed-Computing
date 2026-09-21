"""
TASK 4:
Server should extract the length of message (first 3 characters)
and read the rest of message with proper length.
"""

import socket

HOST = '127.0.0.1'
PORT = 8888

def recvall(sock, length):
    data = b''
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise EOFError('Socket closed unexpectedly')
        data += more
    return data

def task4_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    print(f"[Task 4 Server] Listening on {HOST}:{PORT}...")

    while True:
        try:
            conn, addr = s.accept()
            print(f"\n[Task 4 Server] Connection accepted from: {addr}")

            # Step 1: Extract length of message (first 3 characters)
            header = recvall(conn, 3).decode('utf-8')
            message_length = int(header)
            print(f"[Task 4] Extracted 3-digit length header: '{header}' -> Length = {message_length} characters")

            # Step 2: Read rest of message with proper length
            body = recvall(conn, message_length).decode('utf-8')
            print(f"[Task 4] Read message body: {repr(body)}")

            conn.sendall(b'BYE BYE CLIENT..')
            conn.close()
            print("[Task 4 Server] Reply sent, socket closed.")

        except KeyboardInterrupt:
            print("\n[Task 4 Server] Server stopped.")
            break
        except Exception as e:
            print(f"[Task 4 Server] Error: {e}")

    s.close()

if __name__ == '__main__':
    task4_server()
