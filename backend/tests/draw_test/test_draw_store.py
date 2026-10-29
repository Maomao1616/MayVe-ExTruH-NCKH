import pytest

from app.services.drawing.errors import DrawError
from app.services.drawing.shapes import Layer
from app.services.drawing.store import Parsed, TaskStore


def item(n):
    return Parsed([Layer(str(n), [[(0, 0), (1, 1)]])])


def test_put_get_roundtrip():
    s = TaskStore(3)
    t = s.put(item(1))
    assert s.get(t).layers[0].id == "1"


def test_oldest_is_evicted_beyond_capacity():
    s = TaskStore(2)
    a, b, c = s.put(item(1)), s.put(item(2)), s.put(item(3))
    with pytest.raises(DrawError) as e:
        s.get(a)
    assert e.value.code == "unknown_task" and e.value.status == 404
    assert s.get(b) and s.get(c)


def test_recently_used_survives():
    s = TaskStore(2)
    a, b = s.put(item(1)), s.put(item(2))
    s.get(a)                       # a vừa được dùng -> b sẽ bị loại trước
    s.put(item(3))
    assert s.get(a)
    with pytest.raises(DrawError):
        s.get(b)


def test_drop_is_idempotent():
    s = TaskStore()
    t = s.put(item(1))
    s.drop(t)
    s.drop(t)
    with pytest.raises(DrawError):
        s.get(t)
