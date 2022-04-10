from typing import Dict, Set, Union

import serial

from gtt.enums import *
from gtt.byte_formatting import *
from gtt.exceptions import UnexpectedResponse, StatusError, OutOfIdsError

ID_MAX = 0xff

IdType = Union[int, str]


class GttDisplay:
    """Provides wrappers for some of the serial commands in the GTT 2.7.1 standard.
    One of the key abstractions provided by this class is the mapping of string component IDs onto integers.
    The display does not allow string IDs for components, but you can specify string IDs to the methods in this class
    and they will be mapped to integers automatically.
    """

    def __init__(self, port: str):
        """:param port: a serial port like COM3 or /dev/ttyUSB0"""
        self._conn = serial.Serial(port, baudrate=115200, rtscts=True, timeout=0.5)

        self._conn.write(b'\xfe\x03')
        info_bytes = self._receive_query_response(252, 3)

        self.width: int = int.from_bytes(info_bytes[:2], 'big')
        """The width of this display in pixels"""

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

    def _pick_new_id(self) -> int:
        for integer in range(ID_MAX, 0, -1):
            if integer not in self.ids_in_use:
                return integer

        raise OutOfIdsError('Cannot assign a new integer ID because all possible IDs are in use')

    def _resolve_id(self, unresolved_id: IdType, new=False) -> int:
        """Takes an ID specified by the user, validates it, and converts it to an integer if necessary

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
                int_id = self._pick_new_id()
                self.ids_in_use.add(int_id)
                self._id_map[unresolved_id] = int_id
                return int_id

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

    def enter_mass_storage_mode(self):
        """Allows the USB host to transfer files to the display via a separate USB cable.
        Rebooting seems to be the only way to get the display out of this mode
        """
        self._conn.write(bytes.fromhex('FE 04'))

    def create_plain_bar(self, bar_id: IdType, value: int, max_value: int,
                         x_pos: int, y_pos: int, width: int, height: int,
                         min_value: int = 0, fg_color_hex='FFFFFF', bg_color_hex='000000',
                         direction: BarDirection = BarDirection.BOTTOM_TO_TOP):
        """Creates a bar graph which is really just a single bar.

        :param bar_id: A unique string or integer used to refer to this bar
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
        """Sets the value of the bar given by `bar_id` to value which should be between its min and max values"""
        bar_id = self._resolve_id(bar_id)

        self._conn.write(
            bytes.fromhex('FE 69') +
            bar_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(value)
        )

        self._receive_status_response(252, 105)

    def set_drawing_color(self, hex_color: str):
        """Sets the hex color which is used for drawing things like pixels and rectangles"""
        self._conn.write(bytes.fromhex('FE 63') + hex_colors_to_bytes(hex_color))

    def draw_pixel(self, x_pos: int, y_pos: int):
        """Draws a single pixel. The color can be set by calling set_drawing_color.

        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        """

        self._validate_x(x_pos)
        self._validate_y(y_pos)
        self._conn.write(
            bytes.fromhex('FE 70') +
            ints_to_signed_shorts(x_pos, y_pos)
        )

    def draw_rectangle(self, x_pos: int, y_pos: int, width: int, height: int):
        """Draws an outlined rectangle

        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param width: the width of the rectangle in pixels
        :param height: the height of the rectangle in pixels
        """

        self._validate_x(x_pos, x_pos + width - 1)
        self._validate_y(y_pos, y_pos + height - 1)
        self._conn.write(
            bytes.fromhex('FE 72') +
            ints_to_signed_shorts(x_pos, y_pos, width, height)
        )

    def create_label(self, label_id: IdType, x_pos: int, y_pos: int, width: int, height: int, font_size: int,
                     font: int = 0, rot=0, fg_color_hex='FFFFFF', bg_color_hex='000000', value: str = "Label",
                     vertical_just: FontAlignVertical = FontAlignVertical.TOP,
                     horizontal_just: FontAlignHorizontal = FontAlignHorizontal.LEFT):
        """Creates a text label which can be later updated with new text.
        Many methods (like :meth:`create_button`) don't allow adding text to the UI elements.
        You can get around that by creating a label on top of the UI element.

        :param label_id: A unique string or integer used to refer to the new label
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param width: the width of the label in pixels
        :param height: the height of the label in pixels
        :param rot: the rotation (in degrees) of the text within the label.
        :param vertical_just: the vertical justification of text within the label
        :param horizontal_just: the horizontal justification of text within the label
        :param font: the ID of a previously loaded font to be used for the label.
            By default, there is a font loaded with ID 0
        :param fg_color_hex: a hex color string for the text of the label
        :param bg_color_hex: a hex color string for the background part of the label
        :param value: a string to display within the label. String should be a single line in height.
        :param font_size: Size of the font. NOTE: the default font doesn't support other font sizes.
        """

        self._validate_x(x_pos, x_pos + width - 1)
        self._validate_y(y_pos, y_pos + height - 1)
        label_id = self._resolve_id(label_id, new=True)

        self._conn.write(
            bytes.fromhex('FE 10') +
            label_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos, width, height, rot) +
            vertical_just.to_bytes(1, 'big') +
            horizontal_just.to_bytes(1, 'big') +
            font.to_bytes(1, 'big') +
            hex_colors_to_bytes(fg_color_hex)
        )

        self.update_label(label_id, value)
        self.set_label_font_size(label_id, font_size)
        self.set_label_background_color(label_id, bg_color_hex)

    def update_label(self, label_id: IdType, value: str):
        """Updates string of the label identified by `label_id`"""
        label_id = self._resolve_id(label_id)
        self._conn.write(
            bytes.fromhex('FE 11') +
            label_id.to_bytes(1, 'big') +
            bytes.fromhex('02') +
            value.encode('utf-8') + b'\0'
        )

    def set_label_font_color(self, label_id: IdType, hex_color: str):
        """Sets the font color of an existing label to `hex_color`"""

        label_id = self._resolve_id(label_id)
        self._conn.write(
            bytes.fromhex('FE 15') +
            label_id.to_bytes(1, 'big') +
            hex_colors_to_bytes(hex_color)
        )

        self._receive_status_response(252, 21)

    def set_label_font_size(self, label_id: IdType, size: int):
        """Sets the font size of the label given by `label_id`.

        .. warning::
            The default font does not support resizing.
            You will need to load another font to use this method.
            See :meth:`load_font`.
        """

        label_id = self._resolve_id(label_id)
        self._conn.write(
            bytes.fromhex('FE 17') +
            label_id.to_bytes(1, 'big') +
            size.to_bytes(1, 'big')
        )

        self._receive_status_response(252, 23)

    def set_label_background_color(self, label_id: IdType, hex_color: str):
        """Sets the background color of an existing label"""
        label_id = self._resolve_id(label_id)
        self._conn.write(
            bytes.fromhex('FE 19') +
            label_id.to_bytes(1, 'big') +
            hex_colors_to_bytes(hex_color)
        )

        self._receive_status_response(252, 25)

    def load_font(self, font_id: IdType, file_path: str):
        """Loads a font file from the SD card into a font buffer for use.

        :param font_id: Use this ID to refer to the font after loading it from memory
        :param file_path: font filename, and path from the root folder, of the font file to load.
            Supported font filetypes include .ttf, .fon, and .otf
        """
        font_id = self._resolve_id(font_id, new=True)

        self._conn.write(
            bytes.fromhex('FE 28') +
            font_id.to_bytes(1, 'big') +
            file_path.encode('ascii') + b'\0'
        )

        self._receive_status_response(252, 40)

    def load_bitmap(self, bitmap_id: IdType, file_path: str):
        """Loads a bitmap file from the SD card into a bitmap buffer for use.

        :param bitmap_id: After being loaded into memory, you can use this ID to refer to the bitmap.
        :param file_path: filename, and path from the root folder, of the bitmap file to load (using backslashes).
        """

        bitmap_id = self._resolve_id(bitmap_id, new=True)

        self._conn.write(
            bytes.fromhex('FE 5F') +
            bitmap_id.to_bytes(1, 'big') +
            file_path.encode() + b'\0'
        )

        self._receive_status_response(252, 95)

    def display_bitmap(self, bitmap_id: IdType, x_pos: int, y_pos: int):
        """Displays a bitmap image on the screen from the bitmap buffer.

        :param bitmap_id: the ID of the bitmap in memory (see :meth:`load_bitmap`)
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        """
        bitmap_id = self._resolve_id(bitmap_id)
        self._validate_x(x_pos)
        self._validate_y(y_pos)

        self._conn.write(
            bytes.fromhex('FE 61') +
            bitmap_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos)
        )

        self._receive_status_response(252, 97)

    def load_and_display_bitmap(self, file_path: str, x_pos: int, y_pos: int):
        """Loads the bitmap image at `file_path` and displays it at the given position"""
        bitmap_id = self._pick_new_id()

        self.load_bitmap(bitmap_id, file_path)
        self.display_bitmap(bitmap_id, x_pos, y_pos)

    def set_bitmap_transparency(self, bitmap_id: IdType, transparent_color_hex: str):
        """Map a color on the bitmap to transparency.
        Does not affect previously drawn versions of the specified bitmap.

        :param bitmap_id: A unique string or integer used to identify the bitmap loaded in memory.
        :param transparent_color_hex: If your bitmap has a white background
            but you want it to have a transparent background, set this to 'FFFFFF'.
        """
        bitmap_id = self._resolve_id(bitmap_id)
        self._conn.write(
            bytes.fromhex('FE 62') +
            bitmap_id.to_bytes(1, 'big') +
            hex_colors_to_bytes(transparent_color_hex)
        )

        self._receive_status_response(252, 98)

    def clear_all_traces(self):
        self._conn.write(bytes.fromhex('FE 77'))

    def create_trace(self, trace_id: IdType, x_pos: int, y_pos: int, width: int, height: int,
                     max_value: int, step=1, min_value=0,
                     fg_color_hex='FFFFFF',
                     trace_type: TraceType = TraceType.LINE,
                     x_growth: Direction = Direction.RIGHT, y_growth: Direction = Direction.UP,
                     justify_max=False):
        """Initialize a new graph trace. Upon execution of an update command, the trace region will be shifted by the
        step size, and a line or bar drawn between the previous value and the new one. Individual traces can be updated
        with the update_trace command. This has a transparent background and will show pixels and bitmaps images.

        :param trace_id: used to identify this trace. If a string is supplied, it will be mapped to an integer and
            the mapping will be stored in the instance.
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param width: width of the trace region
        :param height: height of the trace region
        :param min_value: value displayed at the lowest point of the trace
        :param max_value: value displayed at the highest point of the trace
        :param step: Number of pixels shifted when a trace is updated.
        :param fg_color_hex: Intensity of the color, limited to display metrics.
        :param trace_type: value that defines what type of trace is use(Bar, Line, Step, Box)
        :param x_growth: When the trace increments along the x-axis, what direction should it grow?
        :param y_growth: When the y value (the value of the trace) increases, which direction should it move?
        :param justify_max: if set to True,
            the trace will be justified to the max x value which is the right side by default.
        """

        self._validate_x(x_pos, x_pos + width - 1)
        self._validate_y(y_pos, y_pos + height - 1)
        trace_id = self._resolve_id(trace_id, new=True)

        growth_map = {
            Direction.RIGHT: {Direction.UP: 0, Direction.DOWN: 2, Direction.RIGHT: None, Direction.LEFT: None},
            Direction.LEFT: {Direction.UP: 4, Direction.DOWN: 6, Direction.RIGHT: None, Direction.LEFT: None},
            Direction.UP: {Direction.UP: None, Direction.DOWN: None, Direction.RIGHT: 1, Direction.LEFT: 3},
            Direction.DOWN: {Direction.UP: None, Direction.DOWN: None, Direction.RIGHT: 5, Direction.LEFT: 7},
        }

        growth = growth_map[x_growth][y_growth]
        if growth is None:
            raise ValueError('Invalid combination of x_growth and y_growth')

        trace_style = trace_type | growth << 4 | (not justify_max) << 7

        self._conn.write(
            bytes.fromhex('FE 74') +
            trace_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos, width, height, min_value, max_value) +
            step.to_bytes(1, 'big') +
            trace_style.to_bytes(1, 'big') +
            hex_colors_to_bytes(fg_color_hex)
        )

    def update_trace(self, trace_id: IdType, value: int):
        """Update the value of the trace given by `trace_id`"""
        trace_id = self._resolve_id(trace_id)
        self._conn.write(
            bytes.fromhex('FE 75') +
            trace_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(value)
        )

    def create_touch_region(self, region_id: IdType, x_pos: int, y_pos: int, width: int, height: int,
                            up_bitmap_id: IdType, down_bitmap_id: IdType):
        """Create a region of the screen that responds to touch events with a unique message and momentary visual update
        :param region_id: used to identify this touch region in the touch region list. Region 255 is reserved for
        out of region responses. If a string is supplied, it will be mapped to an integer and the mapping will be stored
        in the instance.
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param width: width of the touch region
        :param height: height of the touch region
        :param up_bitmap_id: index of the loaded bitmap displayed when the region is released
        :param down_bitmap_id: index of the loaded bitmap displayed when the region is touched
        """

        self._validate_x(x_pos, x_pos + width - 1)
        self._validate_y(y_pos, y_pos + height - 1)
        region_id = self._resolve_id(region_id, new=True)
        up_bitmap_id = self._resolve_id(up_bitmap_id)
        down_bitmap_id = self._resolve_id(down_bitmap_id)
        self._conn.write(
            bytes.fromhex('FE 84') +
            region_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos) +
            ints_to_unsigned_shorts(width, height) +
            up_bitmap_id.to_bytes(1, 'big') +
            down_bitmap_id.to_bytes(1, 'big')
        )

        # For Andrew TODO
        # 0x04 is associated to region_id
        # response = self._conn.read(6)  # binary value
        # if response == b'\xfc\x87\x00\x02\x00\x04':
        #     print('Contact was made')

    def create_toggle_region(self, region_id: IdType, x_pos: int, y_pos: int, width: int, height: int,
                             off_bitmap_id: IdType, on_bitmap_id: IdType):
        """Create a region of the screen that responds to touch events with a unique message and toggleable visual
        update
        :param region_id: used to identify this touch region in the touch region list. Region 255 is reserved for
        out of region responses. If a string is supplied, it will be mapped to an integer and the mapping will be stored
        in the instance.
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param width: width of the touch region
        :param height: height of the touch region
        :param off_bitmap_id: index of the loaded bitmap displayed when the region is in an inactive state
        :param on_bitmap_id: index of the loaded bitmap displayed when the region is in a toggled state
        """

        self._validate_x(x_pos, x_pos + width - 1)
        self._validate_y(y_pos, y_pos + height - 1)
        region_id = self._resolve_id(region_id, new=True)
        on_bitmap_id = self._resolve_id(on_bitmap_id)
        off_bitmap_id = self._resolve_id(off_bitmap_id)
        self._conn.write(
            bytes.fromhex('FE  96') +
            region_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos) +
            ints_to_unsigned_shorts(width, height) +
            off_bitmap_id.to_bytes(1, 'big') +
            on_bitmap_id.to_bytes(1, 'big')
        )

        self._receive_status_response(252, 150)

        # For Andrew TODO
        # 0x04 is associated to region_id
        # if response == b'\xfc\x87\x00\x02\x00\x04':

    def set_gpo_state(self, pin: int, state: bool):
        """Set the specified General Purpose Output pin on or off,
         Sourcing up to 15mA of current at 5V per pin or ssinking to ground.
         """

        self._conn.write(
            bytes.fromhex('FE  49') +
            pin.to_bytes(1, 'big') +
            state.to_bytes(1, 'big')
        )

    def setup_animation(self, display_id: IdType, memory_id: IdType, x_pos: int, y_pos: int):
        """Displays a loaded animation at the given position.
        Call :meth:`activate_animation` to play the animation.

        :param display_id: a new ID used to refer to this instance of the animation as it is displayed
        :param memory_id: the ID of the animation in memory
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        """
        # TODO Logan there is a bug in this function. Try to find it with tests.
        memory_id = self._resolve_id(memory_id)
        display_id = self._resolve_id(display_id, new=True)

        self._conn.write(
            bytes.fromhex('FE C1') +
            display_id.to_bytes(1, 'big') +
            memory_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos)
        )

    def load_animation(self, memory_id: IdType, file_path: str):
        """Loads an animation file from the SD card into an animation buffer for use.
        To create an animation on the SD card, first save the frames of the animation as jpegs to the SD card,
        then create a text file where each line describes a frame in the animation in the following format

            | <ms to display frame> <frame image path>
            | <ms to display frame> <frame image path>
            | etc

        :param memory_id: a unique string or integer used to refer to the animation in memory.
        :param file_path: The path and filename of the animation text file using backslashes.
        """
        memory_id = self._resolve_id(memory_id, new=True)
        prev_timeout = self._conn.timeout
        self._conn.timeout = 5
        try:
            self._conn.write(
                bytes.fromhex('FE C0') +
                memory_id.to_bytes(1, 'big') +
                file_path.encode('ascii') + b'\0'
            )

            self._receive_status_response(252, 192)
        finally:
            self._conn.timeout = prev_timeout

    def activate_animation(self, display_id: IdType, play=True):
        """Play or stop the animation given by `display_id`

        :param display_id: used to identify this animation instance in the animation list.
        :param play: set to `False` to stop and or `True` to play.
        """
        display_id = self._resolve_id(display_id)
        self._conn.write(
            bytes.fromhex('FE C2') +
            display_id.to_bytes(1, 'big') +
            play.to_bytes(1, 'big')
        )

    def load_and_play_animation(self, display_id: IdType, x_pos: int, y_pos: int, file_path: str):
        """Loads an animation from disk and plays it on the screen in the given position.
        See :meth:`load_animation`, :meth:`setup_animation`, and :meth:`activate_animation` for more details

        :param display_id: You can use this ID to refer to the animation in other methods
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param file_path: the path of the animation text file. See :meth:`load_animation` for details on that file.
        """
        memory_id = self._pick_new_id()

        self.load_animation(memory_id, file_path)
        self.setup_animation(display_id, memory_id, x_pos, y_pos)
        self.activate_animation(display_id)

    def set_animation_frame(self, display_id: IdType, frame: int):
        """Set the current frame of a displayed animation.
        If the frame exceeds the total number present, the animation will be set to the first frame.
        Animation must be loaded and stopped before setting the frame.

        :param display_id: The ID of an animation already on the screen
        :param frame: the index of the frame to display (zero based)
        """

        self._conn.write(
            bytes.fromhex('FE  C3') +
            display_id.to_bytes(1, 'big') +
            frame.to_bytes(1, 'big')
        )

    def get_animation_frame(self, display_id: IdType):
        """Gets the current frame of an existing animation instance

        :param display_id: used to identify this animation instance in the animation list
        """

        self._conn.write(
            bytes.fromhex('FE  C4') +
            display_id.to_bytes(1, 'big')
        )
        response = self._receive_query_response(252, 196)
        return int.from_bytes(response, 'big')

    def stop_all_animations(self):
        """Stops all currently running animation instances at their present frame"""
        self._conn.write(bytes.fromhex('FE C6'))

    def resume_all_animations(self):
        """Resumes all stopped animation instances from their present frame."""
        self._conn.write(bytes.fromhex('FE C9'))

    def clear_animations(self):
        """Clears all animations on the screen"""
        self._conn.write(bytes.fromhex('FE C8'))

    def clear_buffers(self):
        """Clears all animations on the screen"""
        self._conn.write(bytes.fromhex('FE D1'))

