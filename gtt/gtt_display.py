from typing import Dict, Set, Union

import serial

from gtt.enums import *
from gtt.byte_formatting import *
from gtt.exceptions import UnexpectedResponse, StatusError, OutOfIdsError

ID_MAX = 0xff

IdType = Union[int, str]


class GttDisplay:
    def __init__(self, port: str):
        """:param port: a serial port like COM3 or /dev/ttyUSB0"""
        self._conn = serial.Serial(port, baudrate=115200, rtscts=True, timeout=0.5)

        self._conn.write(b'\xfe\x03')
        info_bytes = self._receive_query_response(252, 3)

        self.width: int = int.from_bytes(info_bytes[:2], 'big')
        """The height of this display in pixels"""

        self.height: int = int.from_bytes(info_bytes[2: 4], 'big')
        """The height of this display in pixels"""

        self._id_map: Dict[str, int] = {}
        self.ids_in_use: Set[int] = set()
        """This stores all the integer IDs of the components created by this GttDisplay instance.
        If you use a mix of string and integer IDs to refer to your components, 
        you may want to check whether new integer IDs exist in this set before using them.
        """

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

    def _resolve_id(self, unresolved_id: IdType, new=False) -> int:
        """Takes a string specified by the user, validates it, and converts it to an integer if necessary

        :param unresolved_id: A unique string or integer used to refer to a component
        :param new: Is the given unresolved_id for a new component? Leave False if it is for an existing component.
        :return: a unique integer ID used to refer to a component
        """
        if not isinstance(unresolved_id, (int, str)):
            raise TypeError('IDs must be integers or strings')

        if new:
            if unresolved_id in self._id_map or unresolved_id in self.ids_in_use:
                raise ValueError(f'The ID you specified ({unresolved_id}) for a new component is already in use')

            elif isinstance(unresolved_id, str):
                for integer in range(ID_MAX, 0, -1):
                    if integer not in self.ids_in_use:

                        self.ids_in_use.add(integer)
                        self._id_map[unresolved_id] = integer
                        return integer
                raise OutOfIdsError('Cannot assign a new integer ID because all possible IDs are in use')

            else:
                if unresolved_id < 0 or unresolved_id > ID_MAX:
                    raise ValueError(f'IDs must be greater than zero and less than {ID_MAX}')

                self.ids_in_use.add(unresolved_id)
                return unresolved_id
        else:
            if unresolved_id not in self._id_map and unresolved_id not in self.ids_in_use:
                raise ValueError(f'The ID you specified ({unresolved_id}) does not refer to any existing component')

            elif isinstance(unresolved_id, str):
                return self._id_map[unresolved_id]

            else:
                return unresolved_id

    def _receive_status_response(self, *header_ints: int):
        """For some commands, the GTT will respond with a few header bytes followed by a length short
        and finally one or more status bytes.
        This method tries to receive those header bytes and then raises an exception if the status bytes are not happy.

        :param header_ints: An exception will be raised if the response does not start with these bytes.
        """
        status_bytes = self._receive_query_response(*header_ints)
        status_codes = [byte for byte in status_bytes]

        if any(code != 0xfe for code in status_codes):
            raise StatusError(*status_codes)

    def _receive_query_response(self, *header_ints) -> bytes:
        """Receives the response of a query command which are a few header bytes, a length short, and then a payload.

        :param header_ints: An exception will be raised if the response does not start with these bytes.
        :return: the payload as bytes for the message.
        """
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

        payload_len = self._conn.read(2)
        if payload_len == b'':
            raise UnexpectedResponse('Expected a length byte but got nothing')

        payload_len = int.from_bytes(payload_len, 'big')
        recv = self._conn.read(payload_len)

        if len(recv) != payload_len:
            raise UnexpectedResponse(f'Expected {payload_len} bytes in response but only got {len(recv)}')

        return recv

    def clear_screen(self):
        """Clears everything on the screen and resets insertion cursors"""
        self._conn.write(bytes.fromhex('FE 58'))

    def create_plain_bar(self, bar_id: IdType, value: int, max_value: int,
                         x_pos: int, y_pos: int, width: int, height: int,
                         min_value: int = 0, fg_color_hex='FFFFFF', bg_color_hex='000000',
                         direction: BarDirection = BarDirection.BOTTOM_TO_TOP):
        """Creates a bar graph which is really just a single bar.

        :param bar_id: This will be the unique ID used to refer to the bar in other methods.
            If a string is supplied, it will be mapped to an integer and the mapping will be stored in the instance.
        :param value: the initial value of the bar graph. Should be between min_value and max_value inclusive
        :param max_value: the maximum value which can be shown on the bar graph.
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param width: the width of the bar in pixels
        :param height: the height of the bar in pixels
        :param min_value: the minimum value which can be shown are the bar
        :param fg_color_hex: a hex color string for the filled part of the bar
        :param bg_color_hex: a hex color string for the unfilled part of the bar
        :param direction: Describes how the bar will grow and shrink based on the current value
        """
        self._validate_x(x_pos, x_pos + width - 1)
        self._validate_y(y_pos, y_pos + height - 1)
        bar_id = self._resolve_id(bar_id, new=True)

        self._conn.write(
            bytes.fromhex('FE 67') +
            bar_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(min_value, max_value, x_pos, y_pos, width, height) +
            hex_colors_to_bytes(fg_color_hex, bg_color_hex) +
            direction.to_bytes(1, 'big')
        )

        self.update_bar_value(bar_id, value)

    def update_bar_value(self, bar_id: IdType, value: int):
        """Sets the value of the bar given by bar_id to value which should be between it's min and max values"""
        bar_id = self._resolve_id(bar_id)

        self._conn.write(
            bytes.fromhex('FE 69') +
            bar_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(value)
        )

        self._receive_status_response(252, 105)
