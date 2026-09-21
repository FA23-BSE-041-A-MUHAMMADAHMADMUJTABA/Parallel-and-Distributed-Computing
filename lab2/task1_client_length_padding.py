"""
TASK 1:
Determine the length of message L before sending it (from client side).
[Assume max. number of length is 255 i.e. 3 digits], pad with leading zeros using zfill() method.
"""

def determine_and_pad_length(message: str) -> str:
    L = len(message)
    if L > 255:
        raise ValueError(f"Message length ({L}) exceeds maximum allowed 255 characters!")
    L_padded = str(L).zfill(3)
    return L_padded

if __name__ == '__main__':
    print("=== TASK 1: Message Length Determination & zfill(3) Padding ===")
    test_messages = [
        "Hi",
        "Hello World!",
        "This message is exactly 33 chars!",
        "A" * 150
    ]
    for msg in test_messages:
        padded = determine_and_pad_length(msg)
        print(f"Message: {repr(msg[:25])}... | Length: {len(msg):3d} | Padded (zfill): '{padded}'")
    print("\nTask 1 verification completed successfully.")
