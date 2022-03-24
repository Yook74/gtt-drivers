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


class TraceType(IntEnum):
    BAR = 0
    LINE = 1
    STEP = 2
    BOX = 3


class TraceOriginPosition(IntEnum):
    TOP_RIGHT_DOWN = 0
    BOTTOM_RIGHT = 16
    BOTTOM_LEFT_UP = 32
    TOP_LEFT = 48
    TOP_LEFT_DOWN = 64
    TOP_RIGHT = 80
    BOTTOM_RIGHT_UP = 96
    BOTTOM_LEFT = 112


class TraceOriginShift(IntEnum):
    TOWARD_ORIGIN = False
    AWAY_FROM_ORIGIN = True
