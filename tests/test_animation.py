from pytest import raises
from gtt.exceptions import StatusError
from tests.fixtures import *


def test_load_setup_animation(display: GttDisplay, cli_verify):
    display.load_animation(memory_id=1, file_path='\\Megaman\\Megaman_Running.txt')
    display.setup_animation(display_id=2, memory_id=1, x_pos=0, y_pos=0)
    cli_verify('nothing will happen, the screen will be black(Megaman)')


def test_activate_animation(display: GttDisplay, cli_verify):
    display.load_animation(memory_id=1, file_path='\\Megaman\\Megaman_Running.txt')
    display.setup_animation(display_id=2, memory_id=1, x_pos=0, y_pos=0)
    display.activate_animation(display_id=2)
    cli_verify('a megaman animation will display on the the whole screen')


def test_load_and_play_animation(display: GttDisplay, cli_verify):
    display.clear_animations()
    display.load_and_play_animation(display_id=2, x_pos=0, y_pos=0, file_path='\\Megaman\\Megaman_Running.txt')
    cli_verify('an animation will display on the the whole screen')


def test_set_animation_frame(display: GttDisplay, cli_verify):
    display.clear_animations()
    display.load_and_play_animation(display_id=2, x_pos=0, y_pos=0, file_path='\\Megaman\\Megaman_Running.txt')
    display.activate_animation(display_id=2, play=False)
    display.set_animation_frame(display_id=2, frame=5)
    cli_verify('an animation stop at the sixth frame you have specified')


def test_get_animation_frame(display: GttDisplay, cli_verify):
    display.clear_screen()
    display.load_and_play_animation(display_id=2, x_pos=0, y_pos=0, file_path='\\Megaman\\Megaman_Running.txt')
    display.set_animation_frame(display_id=2, frame=5)
    h = display.get_animation_frame(display_id=2)
    cli_verify(str(h) + ' is frame the animation is currently on')


def test_stop_all_animations(display: GttDisplay, cli_verify):
    display.stop_all_animations()
    cli_verify('all animation have stop on the screen')


def test_resume_all_animations(display: GttDisplay, cli_verify):
    display.resume_all_animations()
    cli_verify('all animation have resume on the screen')


def test_invalid_animation(display: GttDisplay):
    invalid_args_load_and_play = [
        dict(display_id=2, x_pos=0, y_pos=0, file_path='\\Megaman\\'),
        dict(display_id=2, x_pos=0, y_pos=0, file_path='')
    ]
    for kwargs in invalid_args_load_and_play:
        with raises(StatusError):
            display.load_and_play_animation(**kwargs)



