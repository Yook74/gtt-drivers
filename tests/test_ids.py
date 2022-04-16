from pytest import raises

from tests.fixtures import *
from gtt.exceptions import *


def test_id_simple(display):
    assert display._resolve_id(1, new=True) == 1
    assert display.ids_in_use == {1}
    assert display._resolve_id(1) == 1


def test_id_resolution(display):
    assert display._resolve_id('jeff', new=True) == 255
    assert display.ids_in_use == {255}
    assert display._resolve_id('jeff') == 255

    assert display._resolve_id(254, new=True) == 254
    assert display.ids_in_use == {254, 255}
    assert display._resolve_id(254) == 254
    assert display._resolve_id('jeff') == 255

    assert display._resolve_id('jim', new=True) == 253
    assert display._resolve_id(255) == 255


def test_id_limit(display):
    str_id = 'a'

    for idx in range(256//2):
        display._resolve_id(idx, new=True)
        display._resolve_id(str_id, new=True)
        str_id += 'a'

    with raises(OutOfIdsError):
        display._resolve_id('b', new=True)


def test_id_validation(display):
    with raises(ValueError):
        display._resolve_id(300, new=True)

    with raises(ValueError):
        display._resolve_id(200)

    with raises(TypeError):
        display._resolve_id(5.5)

    with raises(ValueError):
        display._resolve_id('fred')

    display._resolve_id('fred', new=True)
    display._resolve_id(5, new=True)

    with raises(IdConflictError):
        display._resolve_id('fred', new=True)

    with raises(IdConflictError):
        display._resolve_id(5, new=True)
