import pytest

from app.services.drawing.errors import DrawError
from app.services.drawing.registry import Registry


def test_register_and_get():
    reg = Registry("thử")

    @reg.register("a")
    def a():
        return 1

    assert reg.get("a")() == 1
    assert reg.names() == ["a"]


def test_duplicate_name_is_rejected():
    reg = Registry("thử")
    reg.register("a")(lambda: 1)
    with pytest.raises(ValueError):
        reg.register("a")(lambda: 2)


def test_unknown_name_gives_stable_code():
    with pytest.raises(DrawError) as e:
        Registry("thử").get("zzz")
    assert e.value.code == "unknown_option"
