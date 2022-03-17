from enum import IntEnum


class BarDirection(IntEnum):
    BOTTOM_TO_TOP = 0
    LEFT_TO_RIGHT = 1
    RIGHT_TO_LEFT = 2
    TOP_TO_BOTTOM = 3


class FontAlignVertical(IntEnum):
    TOP = 0
    BOTTOM = 1
    CENTER = 2


class FontAlignHorizontal(IntEnum):
    LEFT = 0
    RIGHT = 1
    CENTER = 2


class TraceTypeDirection(IntEnum):
    BAR = 0
    LINE = 1
    STEP = 2
    BOX = 3
    BOTTOM_LEFT = 0
    SHIFT_TOWARD_ORIGIN = 0
    LEFT_UP = 16
    TOP_RIGHT = 32
    RIGHT_DOWN = 48
    BOTTOM_RIGHT = 64
    SHIFT_AWAY_FROM_ORIGIN = 128
    LEFT_DOWN = 80
    TOP_LEFT = 96
    RIGHT_UP = 112
