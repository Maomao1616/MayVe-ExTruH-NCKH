"""Kiểu "Phác chì" (sketch.py): ảnh chì do mô hình U²-Net Portrait vẽ, rồi vẽ bằng kiểu theo dáng ảnh. Mô hình là tệp ngoài (data/models/),
không có trong Git: test dùng mô hình thật nếu có, không thì bỏ qua; riêng việc báo thiếu mô hình và các phần không cần mô hình luôn chạy."""
from pathlib import Path

import numpy as np
import pytest

from app.services.drawing import DrawError, sketch, spec, styles
from app.services.drawing.hatch import Field

PEN = 0.5


def style(**kw):
    return spec.parse("style", {"kind": "sketch", "refine_passes": 0, **kw})


def face_like(px=0.25, w_mm=60.0, h_mm=60.0):
    """Ảnh tổng hợp: nền trắng, một hình tròn xám đậm có 'mắt' đen."""
    w, h = int(w_mm / px), int(h_mm / px)
    yy, xx = np.mgrid[:h, :w]
    rgb = np.full((h, w, 3), 235, np.uint8)
    rgb[(yy - h // 2) ** 2 + (xx - w // 2) ** 2 < (h // 3) ** 2] = (120, 90, 80)
    rgb[(abs(yy - h // 2 + 8) < 6) & (abs(abs(xx - w // 2) - 25) < 8)] = (10, 10, 10)
    dark = 1.0 - rgb.mean(axis=2).astype(np.float32) / 255.0
    return Field(dark, w_mm, h_mm, rgb)


def test_missing_model_is_a_clear_error_not_a_crash(monkeypatch, tmp_path):
    monkeypatch.setattr(sketch, "model_path", lambda: tmp_path / "nope.onnx")
    monkeypatch.setattr(sketch, "_SESSION", None)
    with pytest.raises(DrawError) as err:
        styles.fill(face_like(), style(), PEN)
    assert err.value.code == "model_missing"


def test_kind_is_registered_and_listed_for_the_ui():
    assert "sketch" in spec.STYLES and "sketch" in spec.UI_STYLES and "sketch" in styles.GROUPERS
    assert "sketch" not in styles.REFINE_KINDS                              # nét do mô hình vẽ, không có vòng sửa sai tông


def test_pencil_and_strokes_come_out_with_the_real_model_and_stay_in_frame(monkeypatch):
    pytest.importorskip("onnxruntime")
    real = Path(__file__).resolve().parents[3] / "data" / "models" / sketch.MODEL_NAME       # conftest đổi DATA_DIR sang thư mục tạm: trỏ về tệp thật
    if not real.is_file():
        pytest.skip(f"chưa có data/models/{sketch.MODEL_NAME}")
    monkeypatch.setattr(sketch, "model_path", lambda: real)
    monkeypatch.setattr(sketch, "_SESSION", None)
    f = face_like()
    pencil = sketch.line_drawing(f.rgb)
    assert max(pencil.shape) == sketch.SKETCH_INPUT_PX                      # ảnh chì: cạnh dài 512, đúng tỷ lệ ảnh vào
    assert 0.0 <= float(pencil.min()) and float(pencil.max()) <= 1.0
    groups = styles.fill_groups(f, style(), PEN)
    assert groups
    for s in (s for g in groups for s in g):
        assert all(-1e-6 <= x <= f.width_mm + 1e-6 and -1e-6 <= y <= f.height_mm + 1e-6 for x, y in s)


def test_blank_pencil_draws_nothing(monkeypatch):
    """Ảnh chì trắng tinh (mô hình không thấy gì): không có nét (mô hình giả cho khỏi cần tệp thật)."""
    f = face_like()
    monkeypatch.setattr(sketch, "line_drawing", lambda rgb: np.zeros((64, 64), np.float32))
    assert styles.fill(f, style(), PEN) == []


def test_long_straight_axis_lines_are_dropped_as_background_but_slanted_and_curved_ones_stay():
    vertical = [(5.0, 0.0), (5.0, 20.0), (5.1, 45.0)]                       # vạch rèm: dài, thẳng, đứng
    short = [(5.0, 0.0), (5.0, 12.0)]                                       # ngắn: có thể là sợi tóc
    slanted = [(0.0, 0.0), (30.0, 30.0)]                                    # cổ áo chữ V: xiên 45°
    curved = [(0.0, 0.0), (10.0, 20.0), (20.0, 30.0), (22.0, 50.0)]
    assert sketch._is_ruler(vertical)
    assert not sketch._is_ruler(short) and not sketch._is_ruler(slanted) and not sketch._is_ruler(curved)
