from threading import Thread
from queue import Queue
from collections import namedtuple
from typing import Callable, Dict

from serial import Serial, PortNotOpenError

from gtt.exceptions import StatusError, UnexpectedResponse

GttMessage = namedtuple('GttMessage', ['response_code', 'payload'])


class GttConnection(Serial):
    def __init__(self, port):
        """:param port: a serial port like COM3 or /dev/ttyUSB0"""
        super().__init__(port, baudrate=115200, rtscts=True)

        self.message_queue: Queue[GttMessage] = Queue()
        """the payloads of meesages from the display are placed on this queue.
        Use this attrbute to access messages from the display instad of read()
        """

        self.touch_callback_dict: Dict[int, Callable] = {}
        """When the GTT sends a message indicating that a button or togggle has been touched,
        the function associated in this dictionary with the ID of the touch region will be called.
        """

        self._parsing_thread = Thread(target=self.parse_messages_forever)
        self._parsing_thread.start()

    def parse_messages_forever(self):
        """call self.parse_message() until the port is closed"""
        try:
            while True:
                self.parse_message()

        except PortNotOpenError:
            return

    def parse_message(self):
        """Blocks until a single message has been read off the serial interface.
        If the message indicates a touch event, the corresponding callback is invoked.
        Otherwise the mesage is put on the message queue
        """
        first_byte = self.read(1)
        if first_byte[0] != 252:
            raise UnexpectedResponse(f'Got message that starts with {first_byte[0]} instad of 252.')

        response_code = self.read(1)[0]

        payload_len = self.read(2)
        payload_len = int.from_bytes(payload_len, 'big', signed=False)
        payload = self.read(payload_len)

        if response_code == 135:
            touch_id = payload[1]
            if touch_id in self.touch_callback_dict:
                self.touch_callback_dict[touch_id]()
        else:
            self.message_queue.put(GttMessage(response_code, payload))

    def check_status_response(self, response_code: int, timeout=1):
        """For some commands, the GTT will respond with 252, a response_code, a length short
        and finally one or more status bytes.
        This method tries to receive those bytes and then raises an exception if the status bytes are not happy.

        :param response_code: An exception will be raised if the second byte of the response does not match this value
        :param timeout: How long (in seconds) should we wait to get the response?
        """
        status_bytes = self.get_response_payload(response_code, timeout)
        status_codes = [byte for byte in status_bytes]

        if any(code != 0xfe for code in status_codes):
            raise StatusError(*status_codes)

    def get_response_payload(self, response_code, timeout=1) -> bytes:
        """For some commands (mostly queries), the GTT will respond with 252, a response code, a length short
        and finally one or more payload bytes
        This method tries to receive those bytes and return the payload.

        :param response_code: An exception will be raised if the second byte of the response does not match this value
        :param timeout: How long (in seconds) should we wait to get the response?
        :return: the payload of the response to the query in bytes
        """
        message = self.message_queue.get(block=True, timeout=timeout)
        if message.response_code != response_code:
            raise UnexpectedResponse(f'Expected message with code {response_code} but got {message.response_code}')

        return message.payload
