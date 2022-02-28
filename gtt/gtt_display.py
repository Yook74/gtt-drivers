from serial import Serial

from gtt.enums import *
from gtt.byte_formatting import *
from gtt.exceptions import UnexpectedResponse, StatusError


class GttDisplay:
    def __init__(self, port: str, width: int, height: int):
        self._conn = Serial(port, baudrate=115200, rtscts=True, timeout=0.5)
        self.width = width
        self.height = height

    def _validate_x(self, *x_values: int):
        for x_value in x_values:
            if x_value < 0:
                raise ValueError('These arguments would result in a negative x value')

            if x_value >= self.width:
                raise ValueError('These arguments would result in an x value which is too wide to be displayed')

    def _validate_y(self, *y_values: int):
        for y_value in y_values:
            if y_value < 0:
                raise ValueError('These arguments would result in a negative y value')

            if y_value >= self.height:
                raise ValueError('These arguments would result in an y value which is past the bottom of the screen')

    def _receive_status_response(self, *header_ints: int):
        expected_str = ''
        received_str = ''

        for expected_int in header_ints:
            response = self._conn.read(1)
            received_int = int.from_bytes(response, byteorder='big')

            expected_str += f'{expected_int:d} '
            received_str += f'{received_int:d} '

            if response == b'':
                raise TimeoutError('Timed out when receiving a response')

            if received_int != expected_int:
                raise UnexpectedResponse(f'Expected response starting with {expected_str} but got {received_str}')

        status_len = self._conn.read(2)
        if status_len == b'':
            raise UnexpectedResponse('Expected a length byte but got nothing')

        status_codes = [
           int.from_bytes(self._conn.read(1), 'big')
           for _ in range((int.from_bytes(status_len, 'big')))
        ]

        if any(code != 0xfe for code in status_codes):
            raise StatusError(*status_codes)

    def create_plain_bar(self, bar_id: int, value: int, max_value: int, x_pos: int, y_pos: int, width: int, height: int,
                         min_value: int = 0, fg_color_hex='FFFFFF', bg_color_hex='000000',
                         direction: BarDirection = BarDirection.BOTTOM_TO_TOP):
        self._validate_x(x_pos, x_pos + width)
        self._validate_y(y_pos, y_pos + height)
        self._conn.write(
            bytes.fromhex('FE 67') +
            bar_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(min_value, max_value, x_pos, y_pos, width, height) +
            hex_strings_to_bytes(fg_color_hex, bg_color_hex) +
            direction.to_bytes(1, 'big')
        )

        self.update_bar_value(bar_id, value)

    def update_bar_value(self, bar_id: int, value: int):
        self._conn.write(
            bytes.fromhex('FE 69') +
            bar_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(value)
        )

        self._receive_status_response(252, 105)
