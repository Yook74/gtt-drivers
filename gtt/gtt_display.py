from typing import Dict, Set, Union, Callable

from gtt.enums import *
from gtt.byte_formatting import *
from gtt.connection import GttConnection
from gtt.exceptions import UnexpectedResponse, StatusError, OutOfIdsError

ID_MAX = 0xff

IdType = Union[int, str]


class GttDisplay:
    def __init__(self, port: str):
        """:param port: a serial port like COM3 or /dev/ttyUSB0"""
        self._conn = GttConnection(port)

        self._conn.write(b'\xfe\x03')
        info_bytes = self._conn.get_response_payload(3)

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

    def close(self):
        """Must be called to clean up gracefully"""
        self._conn.close()

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

        self._conn.check_status_response(105)

    def create_pixel(self, x_pos: int, y_pos: int):
        """Creates a single pixel in the position x and y. The default color is white.
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
        """Creates an outlined rectangle
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
        """Creates a label in a portion of the screen
        :param label_id: used to identify this label. If a string is supplied, it will be mapped to an integer and        the mapping will be stored in the instance.
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param width: the width of the label in pixels
        :param height: the height of the label in pixels
        :param rot: the rotation of the text within the label, ranges from 0-360 degrees
        :param vertical_just: the vertical justification of text within the label
        :param horizontal_just: the horizontal justification of text within the label
        :param font: the Font index of a previously loaded font to be used for the label.
        :param fg_color_hex: a hex color string for the text of the label
        :param bg_color_hex: a hex color string for the background part of the label
        :param value: a UTF-8 string to display within the label. String should be a single line in height
        :param font_size: Size of the font. Default font size doesn't support other font sizes.
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
        """Updates string of the label identified by label_id"""
        label_id = self._resolve_id(label_id)
        self._conn.write(
            bytes.fromhex('FE 11') +
            label_id.to_bytes(1, 'big') +
            bytes.fromhex('02') +
            value.encode('utf-8') + b'\0'
        )

    def set_label_font_color(self, label_id: IdType, fg_color_hex: str):
        """Sets the font color of an existing label by fg_color_hex
        :param label_id: used to identify this label. If a string is supplied, it will be mapped to an integer and
        the mapping will be stored in the instance.
        :param fg_color_hex: a hex color string for the text of the label
        """

        label_id = self._resolve_id(label_id)
        self._conn.write(
            bytes.fromhex('FE 15') +
            label_id.to_bytes(1, 'big') +
            hex_colors_to_bytes(fg_color_hex)
        )

        self._conn.check_status_response(21)

    def set_label_font_size(self, label_id: IdType, size: int):
        """Sets the font size of the label given by the label_id variable. Default font size doesn't support other
        font sizes
        :param label_id: used to identify this label. If a string is supplied, it will be mapped to an integer and
        the mapping will be stored in the instance.
        :param size: Size of the font in pixels
        """

        label_id = self._resolve_id(label_id)
        self._conn.write(
            bytes.fromhex('FE 17') +
            label_id.to_bytes(1, 'big') +
            size.to_bytes(1, 'big')
        )

        self._conn.check_status_response(23)

    def set_label_background_color(self, label_id: IdType, bg_color_hex):
        """Sets the background color of an existing label by bg_color_hex
        :param label_id: used to identify this label. If a string is supplied, it will be mapped to an integer and
        the mapping will be stored in the instance.
        :param bg_color_hex: a hex color string for the background of the label
        """

        label_id = self._resolve_id(label_id)
        self._conn.write(
            bytes.fromhex('FE 19') +
            label_id.to_bytes(1, 'big') +
            hex_colors_to_bytes(bg_color_hex)
        )

        self._conn.check_status_response(25)

    def load_font(self, font_id: IdType, file_name: str):
        """Loads a font file from the SD card into a font buffer for use.
        :param font_id: used to identify the font. If a string is supplied, it will be mapped to an integer and
        the mapping will be stored in the instance.
        :param file_name: font filename, and path from the root folder, of the font file to load.
        Font file type that is supported font types include .ttf, .fon, and .otf
        file_name example path: "r'\Lorge\Fonts\arial\arial.ttf'"
        """
        font_id = self._resolve_id(font_id, new=True)

        self._conn.write(
            bytes.fromhex('FE 28') +
            font_id.to_bytes(1, 'big') +
            file_name.encode('ascii') + b'\0'
        )

        self._conn.check_status_response(40)

    def load_bitmap(self, bitmap_id: IdType, file_name: str):
        """Loads a bitmap file from the SD card into a bitmap buffer for use. File must be the same height and width as
        the display ont the module
        :param bitmap_id: used to identify the bitmap. If a string is supplied, it will be mapped to an integer
        and the mapping will be stored in the instance.
        :param file_name: filename, and path from the root folder, of the bitmap file to load, must be a .bmp
        """

        bitmap_id = self._resolve_id(bitmap_id, new=True)

        self._conn.write(
            bytes.fromhex('FE 5F') +
            bitmap_id.to_bytes(1, 'big') +
            file_name.encode() + b'\0'
        )

        self._conn.check_status_response(95)

    def display_bitmap(self, bitmap_id: IdType, x_pos: int, y_pos: int):
        """Displays a bitmap image on the screen, from the bitmap buffer. File must be the same height and width as the
        display ont the module
        :param bitmap_id: used to identify the desired file in the bitmap buffer. If a string is supplied, it will
        be mapped to an integer and the mapping will be stored in the instance.
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

        self._conn.check_status_response(97)

    def load_and_display_bitmap(self, bitmap_id: IdType, file_name: str, x_pos: int, y_pos: int, ):
        """Loads a bitmap file from the SD card into a bitmap buffer for use. File must be the same height and width as
        the display ont the module
        :param bitmap_id: used to identify the bitmap. If a string is supplied, it will be mapped to an integer
        and the mapping will be stored in the instance.
        :param file_name: filename, and path from the root folder, of the bitmap file to load, must be a .bmp
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        """
        # Load Bitmap
        self.load_bitmap(bitmap_id, file_name)

        # Display Bitmap
        self.display_bitmap(bitmap_id, x_pos, y_pos)

    def set_bitmap_transparency(self, bitmap_id: IdType, fg_color_hex='FFFFFF'):
        """Set the transparent color for all future renderings of a specific bitmap index. Does not affect previously
        drawn versions of the specified bitmap
        :param bitmap_id: used to identify the desired file in the bitmap buffer. If a string is
        supplied, it will be mapped to an integer and the mapping will be stored in the instance.
        :param fg_color_hex: Intensity of the color, limited to display metrics.
        """
        bitmap_id = self._resolve_id(bitmap_id)
        self._conn.write(
            bytes.fromhex('FE 62') +
            bitmap_id.to_bytes(1, 'big') +
            hex_colors_to_bytes(fg_color_hex)
        ) # TODO @Yook74 appears to have no affect

        self._conn.check_status_response(98)

    def initialize_trace(self, trace_id: IdType, x_pos: int, y_pos: int, width: int, height: int,
                         max_value: int, value: int, step=1, min_value=0,
                         trace_origin_shift=False, fg_color_hex='FFFFFF',
                         trace_type: TraceType = TraceType.LINE,
                         trace_origin_pos: TraceOriginPosition = TraceOriginPosition.BOTTOM_LEFT,
                         ):
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
        :param value: current value of the specified trace.
        :param trace_type: value that defines what type of trace is use(Bar, Line, Step, Box)
        :param trace_origin_pos: value that defines the origin position of the trace
        :param trace_origin_shift: value that defines the orientation of the trace starting point
        Trace_style is the sum of the trace_type, trace_origin_pos, and trace_origin_shift.
        """

        self._validate_x(x_pos, x_pos + width - 1)
        self._validate_y(y_pos, y_pos + height - 1)
        trace_id = self._resolve_id(trace_id, new=True)
        trace_style = trace_type + trace_origin_shift + trace_origin_pos

        self._conn.write(
            bytes.fromhex('FE 74') +
            trace_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos, width, height, min_value, max_value) +
            step.to_bytes(1, 'big') +
            trace_style.to_bytes(1, 'big') +
            hex_colors_to_bytes(fg_color_hex)
        )

        self.update_trace(trace_id, value)

    def update_trace(self, trace_id: IdType, value: int):
        """Update the value of the trace at the specified index.
        :param trace_id: used to identify this trace. If a string is supplied, it will be mapped to an integer and
        the mapping will be stored in the instance.
        :param value: Current value of the specified trace
        """
        trace_id = self._resolve_id(trace_id)
        self._conn.write(
            bytes.fromhex('FE 75') +
            trace_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(value)
        )

    def create_button(self, region_id: IdType, x_pos: int, y_pos: int, width: int, height: int,
                      up_bitmap_id: IdType, down_bitmap_id: IdType, callback: Callable):
        """Create a region of the screen that responds to touch events with a unique message and momentary visual update

        :param region_id: a string or integer to uniquely identify this button
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param width: width of the touch region in pixels
        :param height: height of the touch region in pixels
        :param up_bitmap_id: index of the loaded bitmap displayed when the region is not touched (released)
        :param down_bitmap_id: index of the loaded bitmap displayed when the region is touched
        :param callback: This function will be called (in a seperate thread) when the button is pressed
        """
        self._validate_x(x_pos, x_pos + width - 1)
        self._validate_y(y_pos, y_pos + height - 1)

        region_id = self._resolve_id(region_id, new=True)
        up_bitmap_id = self._resolve_id(up_bitmap_id)
        down_bitmap_id = self._resolve_id(down_bitmap_id)

        self._conn.touch_callback_dict[region_id] = callback

        self._conn.write(
            bytes.fromhex('FE 84') +
            region_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos) +
            ints_to_unsigned_shorts(width, height) +
            up_bitmap_id.to_bytes(1, 'big') +
            down_bitmap_id.to_bytes(1, 'big')
        )

    def create_toggle(self, region_id: IdType, x_pos: int, y_pos: int, width: int, height: int,
                      off_bitmap_id: IdType, on_bitmap_id: IdType, callback: Callable):
        """Creates a region of the screen that switched between two bitmaps and invokes a callback when touched

        :param region_id: A unique string or integer ID for this toggle
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param width: width of the touch region in pixels
        :param height: height of the touch region in pixels
        :param off_bitmap_id: index of the loaded bitmap displayed when the region is in an inactive state
        :param on_bitmap_id: index of the loaded bitmap displayed when the region is in a toggled state
        """
        self._validate_x(x_pos, x_pos + width - 1)
        self._validate_y(y_pos, y_pos + height - 1)

        region_id = self._resolve_id(region_id, new=True)
        on_bitmap_id = self._resolve_id(on_bitmap_id)
        off_bitmap_id = self._resolve_id(off_bitmap_id)

        self._conn.touch_callback_dict[region_id] = callback

        self._conn.write(
            bytes.fromhex('FE  96') +
            region_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos) +
            ints_to_unsigned_shorts(width, height) +
            off_bitmap_id.to_bytes(1, 'big') +
            on_bitmap_id.to_bytes(1, 'big')
        )

        self._conn.check_status_response(150)

    def set_gpo_state(self, pin: int, state: bool):
        """Set the specified General Purpose Output pin on or off. Sourcing up to 15mA of current at 5V per pin or
        sinking to ground."""

        self._conn.write(
            bytes.fromhex('FE  49') +
            pin.to_bytes(1, 'big') +
            state.to_bytes(1, 'big')
        )

    def setup_animation(self, memory_id: IdType, display_id: IdType, x_pos: int, y_pos: int):
        """Define a region of the screen to be used for the specified animation. If an animation is already in use
        at that index, it will be overwritten. Multiple Animation Instances can be setup from one buffered animation
        file.
        :param memory_id: used to identify this animation file. If a string is supplied, it will be mapped
        to an integer and the mapping will be stored in the instance.
        :param display_id: index used to identify this animation instance in the animation list.
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        """
        memory_id = self._resolve_id(memory_id)
        self._conn.write(
            bytes.fromhex('FE  C1') +
            memory_id.to_bytes(1, 'big') +
            display_id.to_bytes(1, 'big') +
            ints_to_signed_shorts(x_pos, y_pos)
        )

    def load_animation(self, memory_id: IdType, file_name: str):
        """Loads an animation file from the SD card into an animation buffer for use.
        :param memory_id: used to identify this animation file. If a string is supplied, it will be mapped to
        an integer and the mapping will be stored in the instance.
        :param file_name: filename, and path from the root folder, of the animation file to load.
        """
        memory_id = self._resolve_id(memory_id)

        self._conn.write(
            bytes.fromhex('FE C0') +
            memory_id.to_bytes(1, 'big') +
            file_name.encode('ascii') + b'\0'
        )

        self._conn.check_status_response(192, timeout=5)

    def activate_animation(self, display_id: IdType, play=True):
        """
        :param display_id: used to identify this animation instance in the animation list
        :param play: desired animation state
        """

        self._conn.write(
            bytes.fromhex('FE  C2') +
            display_id.to_bytes(1, 'big') +
            play.to_bytes(1, 'big')
        )

    def load_and_play_animation(self, memory_id: IdType, display_id: IdType, x_pos: int, y_pos: int,
                                file_name: str):
        """Define a region of the screen to be used for the specified animation. If an animation is already in use
        at that index, it will be overwritten. Multiple Animation Instances can be setup from one buffered animation
        file.
        :param memory_id: where an animation file has been loaded. If a string is supplied, it will be mapped
        to an integer and the mapping will be stored in the instance.
        :param display_id: index used to identify this animation instance in the animation list.
        :param x_pos: the distance from the left edge of the screen in pixels
        :param y_pos: the distance from the top edge of the screen in pixels
        :param file_name: filename, and path from the root folder, of the animation file to load.
        """
        # For Andrew TODO
        # memory_id = 'Hello'
        memory_id = self._resolve_id(memory_id, new=True)

        # Setup Animation
        self.setup_animation(memory_id, display_id, x_pos, y_pos)

        # Load Animation
        self.load_animation(memory_id, file_name)

        # Activate Animation
        self.activate_animation(display_id)

    def set_animation_frame(self, display_id: IdType, frame: int):
        """Set the current frame of a displayed animation. If the frame exceeds the total number present, the animation
        will be set to the first frame. Animation must be loaded and stopped before setting frame.
        :param display_id: used to identify this animation instance in the animation list
        :param frame: Number of the frame to be displayed. Frame is zero-based. Needs to be less that actual amount
        ex: input 7 for 8 photos
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
        response = self._conn.check_status_response(196)
        return int.from_bytes(response, 'big')

    def stop_all_animation(self):
        """Stops all currently running animation instances at their present frame"""
        self._conn.write(
            bytes.fromhex('FE  C6')
        )

    def resume_all_animation(self):
        """Resumes all stopped animation instances from their present frame."""
        self._conn.write(
            bytes.fromhex('FE  C9')
        )
