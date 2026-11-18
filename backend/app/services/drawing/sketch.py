"""Kiểu "Phác chì" (18/11/2026): chân dung (người và động vật) như bản phác chì, vẽ bằng nét uốn theo dáng ảnh.

Chủ dự án (18/11) đưa ảnh mẫu phác chì: ít nét, nét mượt, bóng chỉ ở tóc / má. Kiểu gạch, đan chéo, viền FDoG không ra được.
Hai mô hình đã thử:
  - Informative Drawings: nét sạch nhưng "làm già mặt", nét AI thêm vào kiểu khác chỉ làm xấu thêm (chủ dự án bỏ 18/11).
  - U²-Net Portrait (Qin và cộng sự; huấn luyện trên bộ APDrawing: ảnh chân dung -> bản vẽ chì): sợi tóc và mặt tự nhiên hơn hẳn. Đang dùng.
Cách dùng mô hình: ảnh chì có đậm nhạt (không phải nét mảnh). Ép nó thành đường làm mảnh (skeletonize) thì mất hết kết cấu chì, tóc
thành lưới đa giác. Thay vào đó coi ảnh chì là BẢN ĐỒ ĐỘ ĐẬM và vẽ bằng kiểu "theo dáng ảnh" (flow.py): nét uốn dọc sợi tóc, dày ở chỗ đậm,
thưa ở chỗ nhạt, đường viền mặt / mắt / mũi vẫn ra. Thử trên ảnh chân dung và ảnh chó corgi: cả hai ra hình.

Các bước:
  1. Ảnh màu của khung (Field.rgb) -> khung vuông 512 px (đệm trắng) -> mô hình ONNX (CPU, onnxruntime) -> ảnh chì (đen trên trắng).
  2. Phóng về cỡ xử lý của khung, tăng đậm nhẹ (SKETCH_GAIN) -> Field -> styles.flow_groups.
  3. Bỏ nét thẳng đứng / nằm ngang dài ở nền (rèm, mép tường).
Mô hình hợp ĐẦU (người hoặc thú) chiếm gần hết khung (tác giả: đầu cỡ 512 px trở lên): dùng ô Cắt ảnh cắt sát đầu.
Mô hình là DỮ LIỆU ngoài (176 MB), để ở data/models/, KHÔNG vào Git, không vào gói zip (xem docs/06 mục 8.15).
"""
from __future__ import annotations

import cv2
import numpy as np

from ... import paths
from .errors import DrawError
from .hatch import Field
from .shapes import Stroke

MODEL_NAME = "u2net-portrait.onnx"         # data/models/<tên>: ONNX opset 10 do ailia-models đăng (storage.googleapis.com/ailia-models/u2net_portrait/), 176 282 629 byte
SKETCH_INPUT_PX = 512                      # mô hình nhận đúng 512 × 512
SKETCH_THREADS = 2                         # chừa CPU cho việc điều khiển máy (MiniPC i5-6100T: 2 nhân vật lý)
SKETCH_GAIN = 1.15                         # nhân độ đậm ảnh chì (cắt ở 1): nét chì mảnh nhạt dễ rơi dưới ngưỡng trắng của flow (FLOW_WHITE)
SKETCH_RULER_MM = 30.0                     # nét thẳng đứng / nằm ngang dài hơn chừng này là vạch nền (rèm, mép tường), bỏ
SKETCH_RULER_STRAIGHT = 0.99               # "thẳng" = khoảng cách hai đầu / chiều dài nét ≥ mức này
SKETCH_RULER_AXIS_DEG = 6.0                # "đứng / nằm" = lệch trục dưới chừng này (vạch xiên như cổ áo chữ V vẫn giữ)
_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], np.float32)


def model_path():
    return paths.data_file(f"models/{MODEL_NAME}")


_SESSION = None


def _session():
    global _SESSION
    if _SESSION is None:
        path = model_path()
        if not path.is_file():
            raise DrawError("model_missing", f"Chưa có mô hình phác chì: đặt {MODEL_NAME} vào data/models/ (xem docs/06 mục 8.15).")
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise DrawError("model_missing", "Chưa cài gói onnxruntime (pip install onnxruntime).") from exc
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = SKETCH_THREADS
        _SESSION = ort.InferenceSession(str(path), opts, providers=["CPUExecutionProvider"])
    return _SESSION


def line_drawing(rgb: np.ndarray) -> np.ndarray:
    """Ảnh màu uint8 (h, w, 3) -> ảnh chì 0..1 (1 = nét đen, có đậm nhạt), cạnh dài 512 px, đúng tỷ lệ ảnh vào (đã bỏ phần đệm)."""
    h, w = rgb.shape[:2]
    k = SKETCH_INPUT_PX / max(h, w)
    nh, nw = max(1, round(h * k)), max(1, round(w * k))
    small = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
    square = np.full((SKETCH_INPUT_PX, SKETCH_INPUT_PX, 3), 255, np.uint8)               # đệm trắng cho thành khung vuông
    y0, x0 = (SKETCH_INPUT_PX - nh) // 2, (SKETCH_INPUT_PX - nw) // 2
    square[y0:y0 + nh, x0:x0 + nw] = small
    x = square.astype(np.float32)
    x = x / max(float(x.max()), 1e-6)                                                    # như u2net_portrait_demo: chia cho giá trị lớn nhất, rồi chuẩn hóa ImageNet
    x = (x - _IMAGENET_MEAN) / _IMAGENET_STD
    sess = _session()
    y = np.squeeze(sess.run(None, {sess.get_inputs()[0].name: x.transpose(2, 0, 1)[None].astype(np.float32)})[0])
    y = (y - y.min()) / max(float(y.max() - y.min()), 1e-6)                              # đầu ra: min-max (lớn = nét đen, như mô hình gốc ghi)
    return (y[y0:y0 + nh, x0:x0 + nw]).astype(np.float32)


def _is_ruler(stroke: Stroke) -> bool:
    """Vạch thẳng, dài, đúng trục dọc / ngang: nền chứ không phải người (rèm, cạnh tường, khung cửa)."""
    pts = np.asarray(stroke, np.float64)
    length = float(np.hypot(*np.diff(pts, axis=0).T).sum())
    if length < SKETCH_RULER_MM:
        return False
    chord = pts[-1] - pts[0]
    if float(np.hypot(*chord)) / length < SKETCH_RULER_STRAIGHT:
        return False
    ang = np.degrees(np.arctan2(abs(chord[1]), abs(chord[0])))               # 0 = nằm, 90 = đứng
    return min(ang, 90.0 - ang) <= SKETCH_RULER_AXIS_DEG


def sketch_groups(f: Field, style, pen_mm: float, ctx=None, angle: float | None = None) -> list[list[Stroke]]:
    from . import styles

    if f.rgb is None:
        raise DrawError("model_missing", "Phác chì cần ảnh màu (nội bộ: Field.rgb trống).")
    pencil = line_drawing(f.rgb)
    if ctx:
        ctx.check()
    dark = np.clip(cv2.resize(pencil, (f.w, f.h), interpolation=cv2.INTER_CUBIC) * SKETCH_GAIN, 0.0, 1.0).astype(np.float32)
    groups = styles.flow_groups(Field(dark, f.width_mm, f.height_mm), style, pen_mm, ctx, angle)
    return [[s for s in g if not _is_ruler(s)] for g in groups]
