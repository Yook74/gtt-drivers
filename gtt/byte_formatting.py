def ints_to_signed_shorts(*ints: int) -> bytes:
    return b''.join([
        int_.to_bytes(2, 'big', signed=True)
        for int_ in ints
    ])


def ints_to_unsigned_shorts(*ints: int) -> bytes:
    return b''.join([
        int_.to_bytes(2, 'big', signed=False)
        for int_ in ints
    ])


def hex_colors_to_bytes(*hex_colors: str) -> bytes:
    out = b''
    for hex_color in hex_colors:
        if len(hex_color) != 6:
            raise ValueError('Hex colors must be 6 characters long')

        out += bytes.fromhex(hex_color)

    return out
