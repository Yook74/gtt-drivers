def ints_to_signed_shorts(*ints: int) -> bytes:
    return b''.join([
        int_.to_bytes(2, 'big', signed=True)
        for int_ in ints
    ])


def hex_strings_to_bytes(*hex_strings: str) -> bytes:
    return b''.join([
        bytes.fromhex(hex_string)
        for hex_string in hex_strings
    ])
