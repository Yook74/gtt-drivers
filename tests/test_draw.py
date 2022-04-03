from pytest import raises

from tests.fixtures import *


def test_top_left_pixel(display: GttDisplay, cli_verify):
    display.draw_pixel(x_pos=0, y_pos=0)
    cli_verify('A white pixel at the top-left of the screen will appear')


def test_top_right_pixel(display: GttDisplay, cli_verify):
    display.draw_pixel(x_pos=320 - 1, y_pos=0)
    cli_verify('A white pixel at the top-right of the screen will appear')


def test_bottom_right_pixel(display: GttDisplay, cli_verify):
    display.draw_pixel(x_pos=320 - 1, y_pos=240 - 1)
    cli_verify('A white pixel at the bottom-right of the screen will appear')


def test_bottom_left_pixel(display: GttDisplay, cli_verify):
    display.draw_pixel(x_pos=0, y_pos=240 - 1)
    cli_verify('A white pixel at the bottom-left of the screen will appear')


def test_random_pixel(display: GttDisplay, cli_verify):
    display.draw_pixel(x_pos=41, y_pos=30)
    cli_verify('A white pixel at in the top left area of the screen will appear')


def test_invalid_draw_pixel(display: GttDisplay):
    invalid_args = [
        dict(x_pos=display.width + 1, y_pos=0),
        dict(x_pos=-1, y_pos=0),
        dict(x_pos=0, y_pos=display.height + 1),
        dict(x_pos=0, y_pos=-1)
    ]

    for kwargs in invalid_args:
        with raises(ValueError):
            display.draw_pixel(**kwargs)


def test_draw_rectangle(display: GttDisplay, cli_verify):
    display.draw_rectangle(x_pos=0, y_pos=0, width=100, height=100)
    cli_verify('A white rectangle at in the top left area of the screen will appear')


def test_invalid_draw_rect(display: GttDisplay):
    invalid_args = [
        dict(x_pos=display.width + 1, y_pos=0, width=100, height=100),
        dict(x_pos=-1, y_pos=0, width=100, height=100),
        dict(x_pos=0, y_pos=0, width=display.width + 1, height=100),
        dict(x_pos=0, y_pos=0, width=100, height=-1),
    ]

    for kwargs in invalid_args:
        with raises(ValueError):
            display.draw_rectangle(**kwargs)
