from pytest import raises
from gtt.exceptions import StatusError
from tests.fixtures import *


def test_load_bitmap(display: GttDisplay, cli_verify):
    display.load_bitmap(bitmap_id=1, file_path=r'\Megaman.bmp')
    cli_verify('nothing has happen, the screen will be black and the file is loaded into the bitmap buffer')


def test_display_bitmap(display: GttDisplay, cli_verify):
    display.load_bitmap(bitmap_id=1, file_path=r'\Megaman.bmp')
    display.display_bitmap(bitmap_id=1, x_pos=0, y_pos=0)
    cli_verify('The bitmap file(Megaman) from the bitmap buffer has been displayed on the screen')


def test_load_and_display_bitmap(display: GttDisplay, cli_verify):
    display.load_and_display_bitmap(file_path=r'\Logo35A.bmp', x_pos=0, y_pos=0)
    cli_verify('The bitmap file(GTT35A Logo) has been loaded into the bitmap buffer and the bitmap buffer has displayed'
               ' it on screen')


def test_invalid_bitmap(display: GttDisplay):
    invalid_args = [
        #dict(file_path=r'\nothing.bmp', x_pos=0, y_pos=0),
        dict(file_path='feet', x_pos=0, y_pos=0),
        #dict(file_path='', x_pos=0, y_pos=0)
       ]

    for kwargs in invalid_args:
        with raises(StatusError):
            display.load_and_display_bitmap(**kwargs)
