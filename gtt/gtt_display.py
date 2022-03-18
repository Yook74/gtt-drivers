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

    def create_pixel(self, x_pos: int, y_pos: int):
        """Creates a pixel
        :param x_pos: the distance from the left edge of the screen in pixel
        :param y_pos: the distance from the top edge of the screen in pixel
        """

        self._validate_x(x_pos)
        self._validate_y(y_pos)
        self._conn.write(
            bytes.fromhex('FE 70') +
            ints_to_signed_shorts(x_pos, y_pos)
        )

    def clear_all_traces(self):
        self._conn.write(
            bytes.fromhex('FE 77')
        )

    def draw_rectangle(self, x_pos: int, y_pos: int, width: int, height: int):
        """Creates a rectangle which is really and outline rectangle
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

    def create_label(self, label_id: IdType, x_pos: int, y_pos: int, width: int, height: int, font: int,
                     font_size: int, rot: int, fg_color_hex='FFFFFF', bg_color_hex='000000', value: str = "Label",
                     VJst: FontAlignVertical = FontAlignVertical.TOP,
                     HJst: FontAlignHorizontal = FontAlignHorizontal.LEFT):
        """Creates a label in a portion of the screen
        :param label_id: index used to identify this label in the label list
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param width: the width of the bar in pixels
        :param height: the height of the bar in pixels
        :param rot: the rotation of the text within the label.
        :param VJst: the vertical justification of text within the label
        :param HJst: the horizontal justification of text within the label
        :param font: the Font index of a previously loaded font to be used for the label.
        :param fg_color_hex: a hex color string for the filled part of the label
        :param bg_color_hex: a hex color string for the unfilled part of the label
        :param value: New UTF-8 string to display within the label. String should be a single line in height
        :param font_size: Size of the font
        """

        self._validate_x(x_pos, x_pos + width - 1)
        self._validate_y(y_pos, y_pos + height - 1)
        label_id = self._resolve_id(label_id, new=True)

        self._conn.write(
            bytes.fromhex('FE 10') +
            label_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos, width, height, rot) +
            VJst.to_bytes(1, 'big') +
            HJst.to_bytes(1, 'big') +
            font.to_bytes(1, 'big') +
            hex_colors_to_bytes(fg_color_hex)
        )

        self.update_label(label_id, value)
        self.set_label_font_color(label_id, fg_color_hex)
        self.set_label_font_size(label_id, font_size)
        self.set_label_background_color(label_id, bg_color_hex)

    def update_label(self, label_id: IdType, value: str = "Label"):
        """Updates string of the label identified by label_id"""
        label_id = self._resolve_id(label_id)
        self._conn.write(
            bytes.fromhex('FE 11') +
            label_id.to_bytes(1, 'big') +
            b'\x02' +
            value.encode('utf-8') + b'\0'
        )

    def set_label_font_color(self, label_id: IdType, fg_color_hex='FFFFFF'):
        """Sets the font  color of the label given by the RGB
        :param label_id: index used to identify this label in the label list
        :param fg_color_hex: a hex color string for the filled part of the label
        """
        label_id = self._resolve_id(label_id)
        self._conn.write(
            bytes.fromhex('FE 15') +
            label_id.to_bytes(1, 'big') +
            hex_colors_to_bytes(fg_color_hex)
        )

        self._receive_status_response(252, 21)

    def set_label_font_size(self, label_id: IdType, size: int):
        """Sets the font size of the label given by the label_id variable
        :param label_id: index used to identify this label in the label list
        :param size: Size of the font
        """
        label_id = self._resolve_id(label_id)
        self._conn.write(
            bytes.fromhex('FE 17') +
            label_id.to_bytes(1, 'big') +
            size.to_bytes(1, 'big')
        )

        self._receive_status_response(252, 23)

    def set_label_background_color(self, label_id: IdType, bg_color_hex='000000'):
        """""Set the background color of an existing label by the RB, GB, and BB
        :param label_id: index used to identify this label in the label list
        :param bg_color_hex: a hex color string for the unfilled part of the label
        """

        label_id = self._resolve_id(label_id)
        self._conn.write(
            bytes.fromhex('FE 19') +
            label_id.to_bytes(1, 'big') +
            hex_colors_to_bytes(bg_color_hex)
        )

        self._receive_status_response(252, 25)

    def load_font(self, font_id: IdType, fileName: str):
        """Load a font file from the SD card into a font buffer for use.
        :param font_id: Index used to identify the font. Has to be an int.
        :param fileName: filename, and path from the root folder, of the animation file to load.
        """
        font_id = self._resolve_id(font_id, new=True)

        self._conn.write(
            bytes.fromhex('FE 28') +
            font_id.to_bytes(1, 'big') +
            fileName.encode('ascii') + b'\0'
        )

        self._receive_status_response(252, 40)

    def load_bitmap(self, bitmap_id: IdType, fileName: str):
        """Load a bitmap file from the SD card into a bitmap buffer for use.
        :param bitmap_id: index used to identify the bitmap. Specific to bitmaps, and screen rectangles
        :param fileName: filename, and path from the root folder, of the bitmap file to load
        """
        bitmap_id = self._resolve_id(bitmap_id, new=True)

        self._conn.write(
            bytes.fromhex('FE 5F') +
            bitmap_id.to_bytes(1, 'big') +
            fileName.encode() + b'\0'
        )

        self._receive_status_response(252, 95)

    def display_bitmap(self, bitmap_id: IdType, x_pos: int, y_pos: int):
        """Display a bitmap image on the screen, from the bitmap buffer
        :param bitmap_id: Index used to identify the desired file in the bitmap buffer
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

    def set_bitmap_transparency(self, bitmap_id: IdType, R: int, G: int, B: int):
        """Set the transparent color for all future renderings of a specific bitmap index. Does not affect previously
        drawn versions of the specified bitmap
        :param bitmap_id: the image index used to identify the desired file in the bitmap buffer.
        :param R: Intensity of red, 0 to 255, limited to display metrics.
        :param G: Intensity of green, 0 to 255, limited to display metrics.
        :param B: Intensity of blue, 0 to 255, limited to display metrics.
        """
        bitmap_id = self._resolve_id(bitmap_id)
        self._conn.write(
            bytes.fromhex('FE 62') +
            bitmap_id.to_bytes(1, 'big') +
            R.to_bytes(1, 'big') +
            G.to_bytes(1, 'big') +
            B.to_bytes(1, 'big')
        )

        self._receive_status_response(252, 98)

    def initialize_trace(self, trace_id: IdType, x_pos: int, y_pos: int, width: int, height: int,
                         min_value: int, max_value: int, step: int, R: int, G: int, B: int,
                         value: int, style: int = 129):
        """Initialize a new graph trace. Upon execution of an update command, the trace region will be shifted by the
        step size, and a line or bar drawn between the previous value and the new one. Individual traces can be updated
        with the update_trace command.
        :param trace_id: index used to identify this trace in the trace list
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param width: width of the trace region
        :param height: height of the trace region
        :param min_value: value displayed at the lowest point of the trace
        :param max_value: value displayed at the highest point of the trace
        :param step: Number of pixels shifted when a trace is updated.
        :param R: Intensity of red for trace color, 0 to 255, limited to display metrics.
        :param G: Intensity of green for trace color, 0 to 255, limited to display metrics.
        :param B: Intensity of blue for trace color, 0 to 255, limited to display metrics.
        :param value: current value of the specified trace.
        :param style: Orientation and Direction of the trace, as per eTraceType and Direction Values. A style is
        created by summing values of individual attributes.
        """

        self._validate_x(x_pos, x_pos + width - 1)
        self._validate_y(y_pos, y_pos + height - 1)
        trace_id = self._resolve_id(trace_id, new=True)

        self._conn.write(
            bytes.fromhex('FE 74') +
            trace_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos, width, height, min_value, max_value) +
            step.to_bytes(1, 'big') +
            style.to_bytes(1, 'big') +
            R.to_bytes(1, 'big') +
            G.to_bytes(1, 'big') +
            B.to_bytes(1, 'big')
        )

        self.update_trace(trace_id, value)

    def update_trace(self, trace_id: IdType, value: int):
        """Update the value of the trace at the specified index.
        :param trace_id: Index used to identify this trace in the trace list
        :param value: Current value of the specified trace
        """
        trace_id = self._resolve_id(trace_id)
        self._conn.write(
            bytes.fromhex('FE 75') +
            trace_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(value)

        )

    def create_touch_region(self, region_id: IdType, x_pos: int, y_pos: int, width: int, height: int,
                            up: int, down: int):
        """Create a region of the screen that responds to touch events with a unique message and momentary visual update
        :param region_id: Index used to identify this touch region in the touch region list. Region 255 is reserved for
        out of region responses.
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param width: width of the trace region
        :param height: height of the trace region
        :param up: index of the loaded bitmap displayed when the region is released
        :param down: index of the loaded bitmap displayed when the region is touched
        """

        self._validate_x(x_pos, x_pos + width - 1)
        self._validate_y(y_pos, y_pos + height - 1)
        region_id = self._resolve_id(region_id, new=True)

        self._conn.write(
            bytes.fromhex('FE 84') +
            region_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos) +
            ints_to_unsigned_shorts(width, height) +
            up.to_bytes(1, 'big') +
            down.to_bytes(1, 'big')
        )

        while True:
            response = self._conn.read(6)  # binary value
            if response == b'\xfc\x87\x00\x02\x00\x03':
                print('Contact was made')

    def create_toggle_region(self, region_id: IdType, x_pos: int, y_pos: int, width: int, height: int,
                             off_id: int, on_id: int):
        """Create a region of the screen that responds to touch events with a unique message and toggleable visual
        update
        :param region_id: index used to identify this touch region in the touch region list. Region 255 is reserved for
         out of region responses
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param width: width of the trace region
        :param height: height of the trace region
        :param off_id: index of the loaded bitmap displayed when the region is in an inactive state
        :param on_id: index of the loaded bitmap displayed when the region is in a toggled state
        """

        self._validate_x(x_pos, x_pos + width - 1)
        self._validate_y(y_pos, y_pos + height - 1)
        region_id = self._resolve_id(region_id, new=True)

        self._conn.write(
            bytes.fromhex('FE  96') +
            region_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos) +
            ints_to_unsigned_shorts(width, height) +
            off_id.to_bytes(1, 'big') +
            on_id.to_bytes(1, 'big')
        )

        self._receive_status_response(252, 150)

    def set_GPO_state(self, pin: int, state: bool):
        """Toggle the specified General Purpose Output pin on or off, sourcing up to 15mA current at
        5V per GPO or sinking to ground. This command can be used to control devices, or signal a host device.
        :param pin: GPO to be controlled
        :param state: GPO state, as per eGPOSetting Values
        """

        self._conn.write(
            bytes.fromhex('FE  49') +
            pin.to_bytes(1, 'big') +
            state.to_bytes(1, 'big')
        )

    def setup_animation(self, animation_id: IdType, animation_instance: int, x_pos: int, y_pos: int, fileName: str,
                        play=True):
        """Define a region of the screen to be used for the specified animation. If an animation is already in use
        at that index, it will be overwritten. Multiple Animation Instances can be setup from one buffered animation
        file.
        :param animation_id: index where an animation file has been loaded.
        :param animation_instance: index used to identify this animation instance in the animation list.
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param fileName: filename, and path from the root folder, of the animation file to load.
        :param play: desired animation state
        """
        animation_id = self._resolve_id(animation_id, new=True)
        self._conn.write(
            bytes.fromhex('FE  C1') +
            animation_id.to_bytes(1, 'big') +
            animation_instance.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos)
        )

        self.load_animation(animation_id, fileName, animation_instance, play)

    def load_animation(self, animation_id: IdType, fileName: str, animation_instance: int,
                       play=True):
        """Loads an animation file from the SD card into an animation buffer for use.
        :param animation_id: index used to identify this animation file. Specific to animations.
        :param fileName: filename, and path from the root folder, of the animation file to load.
        :param animation_instance: index used to identify this animation instance in the animation list.
        :param play: desired animation state
        """
        animation_id = self._resolve_id(animation_id)
        prev_timeout = self._conn.timeout
        self._conn.timeout = 5
        try:
            self._conn.write(
                bytes.fromhex('FE  C0') +
                animation_id.to_bytes(1, 'big') +
                fileName.encode('ascii') + b'\0'
            )

            self._receive_status_response(252, 192)
        finally:
            self._conn.timeout = prev_timeout

        self.activate_animation(animation_instance, play)

    def activate_animation(self, animation_instance: int, play=True):
        """
        :param animation_instance: index used to identify this animation instance in the animation list
        :param play: desired animation state
        """

        self._conn.write(
            bytes.fromhex('FE  C2') +
            animation_instance.to_bytes(1, 'big') +
            play.to_bytes(1, 'big')
        )

    def set_animation_frame(self, animation_instance: int, frame: int):
        """Set the current frame of a displayed animation. If the frame exceeds the total number present, the animation
        will be set to the first frame.
        :param animation_instance: index used to identify this animation instance in the animation list
        :param frame: Number of the frame to be displayed. Needs to be less that actual amount ex: input 7 for 8 photos
        :animation must be loaded and stopped before setting frame
        """

        self._conn.write(
            bytes.fromhex('FE  C3') +
            animation_instance.to_bytes(1, 'big') +
            frame.to_bytes(1, 'big')
        )

    def get_animation_frame(self, animation_instance: int):
        """Gets the current frame of an existing animation instance
        :param animation_instance: index used to identify this animation instance in the animation list
        """

        self._conn.write(
            bytes.fromhex('FE  C4') +
            animation_instance.to_bytes(1, 'big')
        )
        response = self._conn.read(6)
        response = response[4]
        return response
        # self._receive_status_response(252, 196)

    def stop_all_animation(self):
        """Stops all currently running animation instances at their present frame
        """
        self._conn.write(
            bytes.fromhex('FE  C6')
        )

    def resume_all_animation(self):
        """Resumes all stopped animation instances from their present frame.
        """
        self._conn.write(
            bytes.fromhex('FE  C9')
        )
