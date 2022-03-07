from pytest import raises

from tests.fixtures import *
from gtt.enums import BarDirection


def test_simple(display: GttDisplay, cli_verify):
    display.create_plain_bar(1, 5, 10, 0, 0, 10, 100, bg_color_hex='606060', direction=BarDirection.TOP_TO_BOTTOM)
    assert display._conn.sent_messages[-2] == bytes.fromhex('FE 67 01 0000 000A 0000 0000 000A 0064 FFFFFF 606060 03')
    assert display._conn.sent_messages[-1] == bytes.fromhex('FE 69 01 0005')
    cli_verify('A 10x100 top-to-bottom bar at the top right of the screen is half full')

    display.update_bar_value(1, 9)
    assert display._conn.sent_messages[-1] == bytes.fromhex('FE 69 01 0009')
    cli_verify('The bar is now 90% full')


def test_horizontal_bar(display: GttDisplay, cli_verify):
    display.create_plain_bar(
        1, -1, min_value=-3, max_value=3,
        x_pos=0, y_pos=0, width=200, height=40,
        bg_color_hex='000030', fg_color_hex='5050F0',
        direction=BarDirection.LEFT_TO_RIGHT
    )

    cli_verify('There\'s a horizontal blue-on-blue bar which is 30% full and 200 pixels wide')

    display.update_bar_value(1, -4)
    cli_verify('The bar is now empty')


def test_big_bar(display: GttDisplay, cli_verify):
    display.create_plain_bar(
        'fred', 1500, min_value=0, max_value=2000,
        x_pos=0, y_pos=0, width=display.width, height=display.height,
        fg_color_hex='F0A0A0', direction=BarDirection.BOTTOM_TO_TOP
    )
    cli_verify('The bottom 3 quarters of the screen is pink')

    display.update_bar_value('fred', 2000)
    cli_verify('The whole screen is now pink')


def test_right_bar(display: GttDisplay, cli_verify):
    display.create_plain_bar(
        250, 17, 32,
        x_pos=41, y_pos=30, width=75, height=13,
        direction=BarDirection.RIGHT_TO_LEFT
    )

    cli_verify('There is a small rectangle near the middle of the screen')


def test_invalid_create(display: GttDisplay):
    invalid_args = [
        dict(bar_id=3, value=3, max_value=4, x_pos=display.width + 1, y_pos=0, width=1, height=1),
        dict(bar_id=4, value=3, max_value=4, x_pos=0, y_pos=70, width=1, height=display.width),
        dict(bar_id=5, value=2, max_value=3, x_pos=0, y_pos=0, width=1, height=1, bg_color_hex='feet'),
        dict(bar_id=5, value=2, max_value=3, x_pos=0, y_pos=0, width=1, height=1, fg_color_hex='00000G'),
        dict(bar_id=5, value=2, max_value=3, x_pos=0, y_pos=0, width=1, height=1, fg_color_hex='0'),
        dict(bar_id=5, value=2e7, max_value=3, x_pos=0, y_pos=0, width=1, height=1),
    ]

    for kwargs in invalid_args:
        with raises(ValueError):
            display.create_plain_bar(**kwargs)
