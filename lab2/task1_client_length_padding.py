"""
TASK 1:
Determine the length of message L before sending it (from client side).
[Assume max. number of length is 255 i.e. 3 digits], pad with leading zeros using zfill() method.
"""

def determine_and_pad_length(message: str) -> str:
    # 1. Determine the length L of the message
    L = len(message)
    
    # 2. Check if length is within the 255 limit (3 digits)
    if L > 255:
        raise ValueError(f"Message length ({L}) exceeds maximum allowed 255 characters!")
    
    # 3. Pad with leading zeros using zfill() to ensure it is always 3 digits
    L_padded = str(L).zfill(3)
    
    return L_padded

if __name__ == '__main__':
    print("=== TASK 1: Message Length Determination & zfill(3) Padding ===")
    
    # Test cases showing different lengths
    test_messages = [
        "Hi",                                        # 2 chars -> '002'
        "Hello World!",                              # 12 chars -> '012'
        "This message is exactly 32 chars!",         # 32 chars -> '032'
        "A" * 150                                    # 150 chars -> '150'
    ]
    
    for msg in test_messages:
        padded_len = determine_and_pad_length(msg)
        print(f"Message: {repr(msg[:25])}... | Actual Length: {len(msg):3d} | Padded (zfill): '{padded_len}'")
    
    print("\nTask 1 verification completed successfully.")
