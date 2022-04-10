from enum import IntEnum, Enum


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


class Direction(Enum):
    DOWN = 0
    UP = 1
    LEFT = 2
    RIGHT = 3
