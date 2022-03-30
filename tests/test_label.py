from pytest import raises

from tests.fixtures import *
from gtt.enums import FontAlignHorizontal, FontAlignVertical


# Label
def test_label_load_font(display: GttDisplay, cli_verify):
    display.load_font(font_id=1, file_path=r'\Lorge\Fonts\time-roman-normal\TimeRomanNormal.ttf')
    cli_verify('Nothing will happen, the text will load into the font buffer but the screen will be the same as before '
               'the test was executed')


def test_label(display: GttDisplay, cli_verify):
    display.load_font(font_id=1, file_path=r'\Lorge\Fonts\time-roman-normal\TimeRomanNormal.ttf')
    display.create_label(label_id=2, x_pos=0, y_pos=0, width=100, height=100, font_size=12, font=1, rot=0,
                         fg_color_hex='FFFFFF', bg_color_hex='000000', value="Label",
                         vertical_just=FontAlignVertical.TOP, horizontal_just=FontAlignHorizontal.LEFT)
    cli_verify('A label with text will appear at the top-left of the screen')


def test_label_color(display: GttDisplay, cli_verify):
    display.create_label(label_id=3, x_pos=0, y_pos=0, width=100, height=100, font_size=12, font=1, rot=0,
                         fg_color_hex='FFFFFF', bg_color_hex='000000', value="Label",
                         vertical_just=FontAlignVertical.TOP, horizontal_just=FontAlignHorizontal.LEFT)
    display.set_label_font_color(label_id=3, hex_color='00FFFF')
    cli_verify('The label with text at the top-left of the screen will change to a new color')


def test_label_size(display: GttDisplay, cli_verify):
    display.create_label(label_id=4, x_pos=0, y_pos=0, width=200, height=200, font_size=12, font=1, rot=0,
                         fg_color_hex='FFFFFF', bg_color_hex='000000', value="Label",
                         vertical_just=FontAlignVertical.TOP, horizontal_just=FontAlignHorizontal.LEFT)
    display.set_label_font_size(label_id=4, size=36)
    cli_verify('The label with text at the top-left of the screen will change the font')


def test_invalid_label(display: GttDisplay):
    invalid_args = [
        dict(label_id=1, x_pos=0, y_pos=0, width=100, height=100, font_size=12, font=1, rot=0, fg_color_hex='feet',
             bg_color_hex='000000', value="Label",
             vertical_just=FontAlignVertical.TOP, horizontal_just=FontAlignHorizontal.LEFT),
        dict(label_id=1, x_pos=0, y_pos=0, width=100, height=100, font_size=12, font=1, rot=0, fg_color_hex='FFFFFF',
             bg_color_hex='00000G', value="Label",
             vertical_just=FontAlignVertical.TOP, horizontal_just=FontAlignHorizontal.LEFT),
        dict(label_id=1, x_pos=0, y_pos=0, width=100, height=100, font_size=12, font=1, rot=0, fg_color_hex='FFFFFF',
             bg_color_hex='000000', value="",
             vertical_just=FontAlignVertical.TOP, horizontal_just=FontAlignHorizontal.LEFT),
        dict(label_id=1, x_pos=0, y_pos=0, width=100, height=100, font_size=12, font=1, rot=0, fg_color_hex='FFFFFF',
             bg_color_hex='000000', value="Label",
             vertical_just=100, horizontal_just=FontAlignHorizontal.LEFT),
        dict(label_id=1, x_pos=0, y_pos=0, width=100, height=100, font_size=12, font=1, rot=0, fg_color_hex='FFFFFF',
             bg_color_hex='000000', value="Label",
             vertical_just=FontAlignVertical.TOP, horizontal_just=10)
    ]

    for kwargs in invalid_args:
        with raises(ValueError):
            display.create_label(**kwargs)
#
