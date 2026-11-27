"""Vòng sửa sai (17/11/2026, docs/06 mục 8.13): vẽ thử → dựng lại mực → so với độ phủ định vẽ → chỉnh ảnh mục tiêu → vẽ lại.

Vì sao cần: mọi kiểu tô đều tính khoảng cách nét từ độ đậm ảnh rồi tin là mực phủ đúng như vậy, nhưng làm tròn số nét,
đầu nét kết thúc so le, vùng chuyển mức... làm mực thật phủ khác ý định (đo trên ảnh thật, bút 0,5: THIẾU 5–8 % độ phủ ở mọi
mức đậm, đúng một chiều). Sai số này có hệ thống nên sửa được bằng phản hồi, không phải đoán thêm một hệ số cho từng kiểu:

  1. Tô như bình thường, dựng ảnh mực (mỗi nét rộng đúng bề rộng bút), làm mờ ~2 mm (mắt nhìn từ xa).
  2. So với độ phủ định vẽ (đã qua đường cong tông của kiểu): thừa chỗ nào, thiếu chỗ nào (bản đồ sai số).
  3. Trừ một phần (REFINE_GAIN) bản đồ sai số khỏi ẢNH MỤC TIÊU rồi tô lại. Chỗ thừa mực thì mục tiêu hạ xuống, nét thưa đi;
     chỗ thiếu thì nâng lên (trường hợp thường gặp: thiếu, nên thường là thêm nét). Cộng dồn qua các lượt nên sai số còn lại nhỏ dần (như bộ điều khiển có thành phần tích phân).
  4. Giữ lượt có sai số nhỏ nhất; dừng sớm khi lượt mới không tốt hơn rõ rệt.

Chỉ cần kiểu tô là hàm "ảnh mục tiêu → các nhóm nét" nên dùng chung cho mọi kiểu (trừ Nét viền). Ý tưởng "làm sáng ảnh làm
việc sau mỗi nét rồi vẽ tiếp" của các phần mềm tô nét ngẫu nhiên, ở đây làm theo lô: toàn bộ nét một lượt, rồi sửa.
"""
from __future__ import annotations

import math
from functools import lru_cache

import cv2
import numpy as np

from .hatch import Field

REFINE_GAIN = 0.8            # mỗi lượt trừ 0,8 × sai số khỏi mục tiêu (1,0 dễ dao động vì mức nét nhảy bậc; 0,5 hội tụ chậm)
REFINE_SIGMA_MM = 2.0        # mắt nhìn tông ở cỡ ~2 mm (cùng tools/ink_sim.py)
REFINE_LINE_PX = 7           # dựng mực: nét thật rộng ~7 điểm ảnh (nhỏ hơn thì làm tròn bề rộng gây sai số lớn hơn)
REFINE_MAX_PIXELS = 16_000_000   # trần số điểm ảnh khi dựng mực (khung rất lớn thì giảm độ phân giải, không ăn hết RAM)
REFINE_GRID_PX_MM = 4.0      # lưới so sánh: 4 ô / mm (làm mờ 2 mm nên thừa mịn)
REFINE_STOP_RATIO = 0.97     # lượt mới phải nhỏ hơn 97 % sai số tốt nhất mới được giữ và đi tiếp
REFINE_RAISE_FROM = 0.15     # chỗ độ phủ gốc dưới mức này là giấy trắng chủ ý (kiểu tô để trắng): sửa sai không nâng lên


@lru_cache(maxsize=None)
def _drawn_width(thick: int) -> int:
    """Bề rộng (điểm ảnh) mà cv2.polylines THỰC SỰ vẽ khi yêu cầu độ dày `thick`: đo bằng một đường ngang trên khung nhỏ."""
    canvas = np.zeros((41, 41), np.uint8)
    cv2.polylines(canvas, [np.array([[5, 20], [35, 20]], np.int32).reshape(-1, 1, 2)], False, 255, thick, cv2.LINE_8)
    return int(np.count_nonzero(canvas[:, 20]))


def _thickness_for(true_px: float) -> int:
    """Độ dày yêu cầu để bề rộng thực vẽ ra gần `true_px` nhất."""
    return min(range(1, int(math.ceil(true_px)) + 3), key=lambda t: abs(_drawn_width(t) - true_px))


def ink_cover(strokes, w_mm: float, h_mm: float, line_w: float) -> tuple[np.ndarray, float]:
    """Độ phủ mực (0..1) trên lưới thô; trả (lưới, cạnh ô mm). Mỗi nét dựng với bề rộng thật `line_w`, hai nét chồng nhau
    chỉ tính một lần (mực không dày thêm), nên chỗ đậm bão hòa đúng như trên giấy.

    Vì sao dựng điểm ảnh kiểu này (đã thử các cách khác ngày 17/11/2026, ghi ở docs/08 P34):
      - OpenCV `polylines` vẽ DÀY HƠN độ dày yêu cầu và làm tròn lên số lẻ (đo: yêu cầu 5 và 6 đều ra 7 điểm, 7 và 8 ra 9),
        nên đo bề rộng thực vẽ ra (`_drawn_width`), chọn độ dày gần nhất rồi nhân bù tỷ lệ bề rộng thật ÷ bề rộng vẽ ra. Kiểm:
        đường song song mọi góc ra độ phủ đúng ±1 %. Cứ vẽ bằng độ dày = bề rộng thì thừa 14–25 %, đổi theo góc / độ phân giải.
      - Cộng chiều dài nét × bề rộng ÷ diện tích sai ở chỗ đậm: hai lớp gạch chồng nhau cộng thẳng ra độ phủ 1,2 > 1."""
    scale = min(REFINE_LINE_PX / line_w, math.sqrt(REFINE_MAX_PIXELS / max(1.0, w_mm * h_mm)))
    true_px = line_w * scale
    thick = _thickness_for(true_px)
    width, height = max(2, int(round(w_mm * scale))), max(2, int(round(h_mm * scale)))
    canvas = np.zeros((height, width), np.uint8)
    for s in strokes:
        if len(s) < 2:
            continue
        pts = np.round(np.asarray(s, np.float64) * (scale * 16.0)).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(canvas, [pts], False, 255, thick, cv2.LINE_8, 4)          # toạ độ 1/16 điểm ảnh (shift 4): đường chéo không bị lượng tử hóa
    k = max(1, int(scale / REFINE_GRID_PX_MM))
    small = cv2.resize(canvas, (max(2, width // k), max(2, height // k)), interpolation=cv2.INTER_AREA)
    cover = small.astype(np.float32) / 255.0 * (true_px / _drawn_width(thick))
    return np.minimum(cover, 1.0), k / scale        # hệ số bù có thể > 1 (khung rất lớn, độ dày hòa nhau): mực không phủ quá 100 %


def coverage_error(strokes, want: np.ndarray, w_mm: float, h_mm: float, line_w: float) -> tuple[float, np.ndarray]:
    """(sai số trung bình tuyệt đối, bản đồ sai số = mực thấy − mong muốn) trên lưới ô, cả hai làm mờ cỡ mắt nhìn."""
    cover, cell = ink_cover(strokes, w_mm, h_mm, line_w)
    sigma = REFINE_SIGMA_MM / cell
    target = cv2.resize(want.astype(np.float32), (cover.shape[1], cover.shape[0]), interpolation=cv2.INTER_AREA)
    err = cv2.GaussianBlur(cover, (0, 0), sigma) - cv2.GaussianBlur(target, (0, 0), sigma)
    return float(np.abs(err).mean()), err


def refine(f: Field, build, want: np.ndarray, line_w: float, passes: int, ctx=None, report: dict | None = None):
    """`build(field) -> các nhóm nét`. `want` = độ phủ định vẽ (cùng cỡ f.dark). Trả các nhóm nét tốt nhất tìm được.
    `report` (nếu có) nhận: error_before, error_after, passes (số lượt đã chạy), strokes_before / strokes_after."""
    groups = build(f)
    strokes = [s for g in groups for s in g]
    if passes <= 0 or not strokes:
        return groups
    err, err_map = coverage_error(strokes, want, f.width_mm, f.height_mm, line_w)
    first_err, first_n = err, len(strokes)
    best_err, best_groups, best_n = err, groups, len(strokes)
    cur = f.dark.astype(np.float32).copy()
    used = 0
    for _ in range(passes):
        if ctx:
            ctx.check()
        fix = cv2.resize(err_map, (cur.shape[1], cur.shape[0]), interpolation=cv2.INTER_AREA)
        step = -REFINE_GAIN * fix
        step = np.where((step > 0) & (f.dark < REFINE_RAISE_FROM), 0.0, step)     # giấy trắng chủ ý: không thêm nét
        cur = np.clip(cur + step, 0.0, 1.0).astype(np.float32)
        groups = build(Field(cur, f.width_mm, f.height_mm, f.rgb))
        strokes = [s for g in groups for s in g]
        used += 1
        if not strokes:
            break
        err, err_map = coverage_error(strokes, want, f.width_mm, f.height_mm, line_w)
        if err < best_err * REFINE_STOP_RATIO:
            best_err, best_groups, best_n = err, groups, len(strokes)
        else:
            if err < best_err:
                best_err, best_groups, best_n = err, groups, len(strokes)
            break
    if report is not None:
        report.update({"error_before": round(first_err, 4), "error_after": round(best_err, 4), "passes": used,
                       "strokes_before": first_n, "strokes_after": best_n})
    return best_groups
