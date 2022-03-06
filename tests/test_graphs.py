from tests.fixtures import *
from gtt.enums import BarDirection


def test_create_simple(display: GttDisplay, cli_verify):
    display.create_plain_bar(1, 5, 10, 0, 0, 10, 100, bg_color_hex='606060', direction=BarDirection.TOP_TO_BOTTOM)
    assert display._conn.sent_messages[-2] == bytes.fromhex('FE 67 01 0000 000A 0000 0000 000A 0064 FFFFFF 606060 03')
    cli_verify('A 10x100 top-to-bottom bar at the top right of the screen is half full')
