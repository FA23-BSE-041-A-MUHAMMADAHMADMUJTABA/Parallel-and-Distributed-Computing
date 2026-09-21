import socket
import sys

HOST = '127.0.0.1'
PORT = 8888

def recvall(sock, length):
    """
    Helper function to reliably read exactly 'length' bytes from socket.
    """
    data = b''
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise EOFError(f'Socket closed with {len(data)} bytes received out of {length} expected bytes')
        data += more
    return data

def run_client(message=None):
    # Create TCP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    print(f'Client has been assigned socket name: {s.getsockname()}')

    # Message input selection:
    # 1. From function parameter
    # 2. From command line argument
    # 3. From interactive prompt
    # 4. Default demonstration message
    if message is None:
        if len(sys.argv) > 1:
            message = " ".join(sys.argv[1:])
        else:
            try:
                user_in = input("Enter message to send (max 255 chars, press Enter for default): ").strip()
                message = user_in if user_in else "Hello Server! This message has variable length greater than 16 chars."
            except EOFError:
                message = "Hello Server! This message has variable length greater than 16 chars."

    print(f"\nOriginal message: {repr(message)}")

    # -------------------------------------------------------------
    # Task 1: Determine the length of message L before sending it (from client side).
    # [Assume max. number of length is 255 i.e. 3 digits], pad with leading zeros using zfill() method.
    # -------------------------------------------------------------
    L = len(message)
    if L > 255:
        raise ValueError(f"Message length is {L}, which exceeds the 255 maximum allowed length!")

    # Pad length L with leading zeros to make it exactly 3 digits
    L_padded = str(L).zfill(3)
    print(f"[Task 1] Message length L = {L}. Padded with zfill(3): '{L_padded}'")

    # -------------------------------------------------------------
    # Task 2: Add L at the beginning of message.
    # -------------------------------------------------------------
    full_message = L_padded + message
    print(f"[Task 2] Full formatted message with prefix: '{full_message}'")

    # -------------------------------------------------------------
    # Task 3: Send that message to server.
    # -------------------------------------------------------------
    s.sendall(full_message.encode('utf-8'))
    print(f"[Task 3] Sent {len(full_message)} bytes (3 bytes header + {L} bytes body) to server.")

    # Receive 16-octet reply from server
    reply = recvall(s, 16)
    print(f'THE SERVER SAID: {repr(reply.decode("utf-8"))}')

    s.close()
    print('Client connection closed.\n')

if __name__ == '__main__':
    run_client()
