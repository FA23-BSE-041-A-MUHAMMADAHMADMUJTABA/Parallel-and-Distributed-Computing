"""
TASK 3:
Send that message to server.
(Client connects to server, prepares the message with 3-digit length prefix, and sends it)
"""

import socket
import sys

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

def task3_send():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    print(f"[Client] Connected to server at {(HOST, PORT)}")

    if len(sys.argv) > 1:
        raw_msg = " ".join(sys.argv[1:])
    else:
        raw_msg = "Hello Server from Task 3! This is a test message of custom length."

    # Task 1: Determine length & pad with zfill(3)
    L = len(raw_msg)
    L_padded = str(L).zfill(3)

    # Task 2: Add L at beginning of message
    framed_msg = L_padded + raw_msg

    print(f"[Client] Message to send: '{raw_msg}'")
    print(f"[Client] Padded Length Prefix: '{L_padded}'")
    print(f"[Client] Framed Message: '{framed_msg}'")

    # Task 3: Send message to server
    s.sendall(framed_msg.encode('utf-8'))
    print(f"[Task 3] Successfully sent framed message ({len(framed_msg)} bytes) to server.")

    reply = recvall(s, 16)
    print(f"[Client] Server replied: {repr(reply.decode('utf-8'))}")
    s.close()
    print("[Client] Connection closed.")

if __name__ == '__main__':
    task3_send()
