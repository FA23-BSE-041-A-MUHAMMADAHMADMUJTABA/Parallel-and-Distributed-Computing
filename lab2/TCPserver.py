import socket
import sys

# Define host and port
HOST = '127.0.0.1'
PORT = 8888

def recvall(sock, length):
    """
    Helper function to ensure exactly 'length' bytes are received from the socket.
    TCP is a stream-oriented protocol, so data can arrive in chunks.
    """
    data = b''
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise EOFError(f'Socket closed with {len(data)} bytes received out of {length} expected bytes')
        data += more
    return data

def run_server():
    # Create TCP socket (AF_INET = IPv4, SOCK_STREAM = TCP)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Allow socket address reuse immediately after closing
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind socket to HOST and PORT
    s.bind((HOST, PORT))
    # Listen for incoming connections (queue size 1)
    s.listen(1)
    print(f'Server listening at {s.getsockname()}...')

    while True:
        try:
            sc, sockname = s.accept()
            print(f'\nWe have accepted a connection from {sockname}')
            print(f'Socket connects {sc.getsockname()} and {sc.getpeername()}')

            # -------------------------------------------------------------
            # Task 4: Server extracts the length of message (first 3 characters)
            # and reads the rest of message with proper length.
            # -------------------------------------------------------------
            # Step 4a: Read the first 3 bytes (the length header)
            header_bytes = recvall(sc, 3)
            length_str = header_bytes.decode('utf-8')
            msg_length = int(length_str)
            print(f'[Task 4] Extracted 3-digit length header: {length_str} -> Length is {msg_length} characters')

            # Step 4b: Read the rest of the message with proper length (msg_length bytes)
            message_bytes = recvall(sc, msg_length)
            message = message_bytes.decode('utf-8')
            print(f'[Task 4] The incoming message ({msg_length} octets/chars) says: {repr(message)}')

            # Reply to the client
            reply = b'BYE BYE CLIENT..'
            sc.sendall(reply)
            sc.close()
            print('Reply sent, socket closed.')

        except KeyboardInterrupt:
            print('\nServer stopped by user.')
            break
        except Exception as e:
            print(f'Error occurred: {e}')

    s.close()

if __name__ == '__main__':
    run_server()
