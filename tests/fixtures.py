import pytest
import serial

from gtt import GttDisplay


class MonitoredSerialConn(serial.Serial):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sent_messages = list()
        self.bytes_received = bytes()

    def write(self, data):
        super().write(data)
        self.sent_messages.append(data)

    def read(self, size=1):
        recv = super().read(size)
        self.bytes_received += recv
        return recv


@pytest.fixture
def display(pytestconfig, monkeypatch):
    monkeypatch.setattr(serial, 'Serial', MonitoredSerialConn)
    display = GttDisplay('/dev/ttyUSB0')
    display.clear_screen()
    return display


class ManualVerifyFailure(Exception):
    """Raised when the person running the test does not think that the driver code is working right"""
    pass


@pytest.fixture
def cli_verify(pytestconfig):
    def check_expectation(expectation: str):
        while True:
            response = input(f'Verify that {expectation} (Y/n): ')
            response = response.lower().strip()

            if response in ['y', '']:
                return
            elif response == 'n':
                raise ManualVerifyFailure(f'The tests expected "{expectation}" but that didn\'t happen')
            else:
                print('Enter "y" or "n"')

    if pytestconfig.getoption('--no-prompts'):
        return lambda expectation: None  # no-op
    else:
        return check_expectation
