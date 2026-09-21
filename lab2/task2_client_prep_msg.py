"""
TASK 2:
Add L at the beginning of message.
(Combines the 3-digit padded length L with the message payload)
"""

def prepare_framed_message(message: str) -> str:
    L = len(message)
    if L > 255:
        raise ValueError(f"Message length ({L}) exceeds 255 characters!")
    L_padded = str(L).zfill(3)
    framed_message = L_padded + message
    return framed_message

if __name__ == '__main__':
    print("=== TASK 2: Add Padded Length Prefix at Beginning of Message ===")
    test_messages = [
        "Hello Server!",
        "Parallel and Distributed Computing Lab 2",
        "Short",
        "X" * 60
    ]
    for msg in test_messages:
        framed = prepare_framed_message(msg)
        print(f"Original : '{msg}'")
        print(f"Prefixed : '{framed}' (Header: '{framed[:3]}', Body: '{framed[3:]}')\n")
    print("Task 2 verification completed successfully.")
