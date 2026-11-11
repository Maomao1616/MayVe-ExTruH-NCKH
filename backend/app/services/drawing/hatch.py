"""Lõi tô bằng nét: bản đồ độ đậm -> mặt nạ từng mức -> đường quét song song / xoắn ốc -> các nét (mm).

Mọi hàm thuần numpy / OpenCV, tọa độ ra bằng mm trong khung ảnh (gốc trên trái, Y xuống).
Mỗi dải đậm nhạt (styles.level_plan) có mặt nạ riêng và một lượt gạch với khoảng cách riêng.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

CHUNK_CELLS = 2_000_000          # số mẫu tối đa xử lý một lượt (giới hạn RAM)
MIN_RUN_MM = 0.3                 # đoạn ngắn hơn chừng này bỏ qua (bút không vẽ nổi)
BRIDGE_MM = 3.0                  # khe trắng ngắn hơn chừng này trên xoắn ốc thì vẽ liền (đỡ một lần nhấc bút ≈ 0,6 s)
SPIRAL_BRIDGE_PITCHES = 6.0      # nối qua khe trắng tới chừng này lần bước xoắn
SPIRAL_MIN_PITCHES = 4.0         # bỏ mẩu ngắn hơn chừng này lần bước xoắn
WAVE_POINT_BUDGET = 100_000      # số điểm tối đa mong muốn cho đường sóng của một lớp (G-code giới hạn 200 000 dòng)


@dataclass(frozen=True)
class Field:
    """Bản đồ độ đậm + hệ tọa độ mm của nó."""
    dark: np.ndarray             # float32 (h, w), 0..1
    width_mm: float
    height_mm: float
    rgb: np.ndarray | None = None   # uint8 (h, w, 3) cùng cỡ, chỉ có khi vẽ viền (ranh giới mảng màu)

    @property
    def h(self) -> int:
        return self.dark.shape[0]

    @property
    def w(self) -> int:
        return self.dark.shape[1]

    @property
    def px_mm(self) -> float:
        return min(self.width_mm / self.w, self.height_mm / self.h)


def blur(f: Field, spacing_mm: float) -> np.ndarray:
    """Làm mờ nhẹ (sigma = 0,35 × khoảng cách nét): chi tiết nhỏ hơn khoảng cách nét bút không vẽ nổi."""
    sigma = max(0.0, 0.35 * spacing_mm / f.px_mm)
    return cv2.GaussianBlur(f.dark, (0, 0), sigma) if sigma >= 0.5 else f.dark


def threshold_mask(d: np.ndarray, threshold: float, spacing_mm: float, px_mm: float) -> np.ndarray:
    """Mặt nạ bool từ ảnh đã làm mờ: ngưỡng, nối khe hẹp, bỏ đốm nhỏ hơn khoảng cách nét."""
    m = (d >= threshold).astype(np.uint8)
    k = int(max(1, round(spacing_mm / px_mm)))
    if k >= 2:
        kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k | 1, k | 1))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kern)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, kern)
    return m.astype(bool)


def level_mask(f: Field, threshold: float, spacing_mm: float) -> np.ndarray:
    """Mặt nạ bool: làm mờ nhẹ, ngưỡng, nối khe hẹp, bỏ đốm nhỏ hơn khoảng cách nét (bút không vẽ nổi)."""
    return threshold_mask(blur(f, spacing_mm), threshold, spacing_mm, f.px_mm)


# --- chuyển mức mềm: mỗi dòng gạch một ngưỡng hơi lệch -----------------------------------
DITHER_RANKS = 8                 # 8 độ lệch khác nhau, lặp lại mỗi 8 dòng


def dither_offsets(spread: float) -> list[float]:
    """Độ lệch ngưỡng của dòng thứ i (dùng phần tử i % 8), trải đều trong [-spread, +spread].

    Thứ tự đảo bit (0, 4, 2, 6, 1, 5, 3, 7): hai dòng kề nhau luôn lệch xa nhau, nên ở chỗ giáp hai mức đậm nhạt
    các dòng kết thúc so le như răng lược thay vì cùng dừng trên một đường. Trong dải giáp ranh, phần dòng của mức
    nhạt giảm dần còn phần dòng của mức đậm tăng dần: độ đậm chuyển liền thay vì nhảy bậc."""
    out = []
    for i in range(DITHER_RANKS):
        rev = ((i & 1) << 2) | (i & 2) | ((i & 4) >> 2)
        out.append(spread * ((rev + 0.5) / DITHER_RANKS * 2.0 - 1.0))
    return out


def _mask_rows(masks, f: Field, rows: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Tra mặt nạ cho từng dòng: `masks` là một mặt nạ, hoặc danh sách (dòng i dùng masks[i % len])."""
    if isinstance(masks, np.ndarray):
        return _lookup(masks, f, x, y)
    on = np.zeros(x.shape, dtype=bool)
    k = len(masks)
    for r in range(k):
        sel = (rows % k) == r
        if sel.any():
            on[sel] = _lookup(masks[r], f, x[sel], y[sel])
    return on


def _lookup(mask: np.ndarray, f: Field, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    ix = np.floor(x * (f.w / f.width_mm)).astype(np.int32)
    iy = np.floor(y * (f.h / f.height_mm)).astype(np.int32)
    ok = (ix >= 0) & (ix < f.w) & (iy >= 0) & (iy < f.h)
    out = np.zeros(x.shape, dtype=bool)
    out[ok] = mask[iy[ok], ix[ok]]
    return out


def _runs(on: np.ndarray):
    """Các đoạn True liên tiếp theo hàng: (hàng, cột đầu, cột cuối-bao-gồm)."""
    pad = np.zeros((on.shape[0], on.shape[1] + 2), dtype=np.int8)
    pad[:, 1:-1] = on
    d = np.diff(pad, axis=1)
    s = np.argwhere(d == 1)
    e = np.argwhere(d == -1)
    return s[:, 0], s[:, 1], e[:, 1] - 1


# --- đường quét song song ------------------------------------------------------------
def scan_runs(mask, f: Field, angle_deg: float, spacing_mm: float, phase: float = 0.0):
    """Trả (u_hướng, v_pháp, danh sách theo dòng các (u0, u1)) trên các dòng cách nhau spacing_mm.
    `mask`: một mặt nạ, hoặc danh sách mặt nạ (dòng i dùng mask[i % len], xem dither_offsets)."""
    a = math.radians(angle_deg)
    d = np.array([math.cos(a), math.sin(a)])
    n = np.array([-math.sin(a), math.cos(a)])
    corners = np.array([[0, 0], [f.width_mm, 0], [0, f.height_mm], [f.width_mm, f.height_mm]])
    us, vs = corners @ d, corners @ n
    umin, umax = float(us.min()), float(us.max())
    vmin = float(vs.min()) + (phase % 1.0) * spacing_mm
    n_lines = int((float(vs.max()) - vmin) / spacing_mm) + 1
    du = max(f.px_mm * 0.7, 1e-3)
    n_u = int((umax - umin) / du) + 1
    u = umin + np.arange(n_u) * du
    lines: list[list[tuple[float, float]]] = [[] for _ in range(n_lines)]
    rows_per = max(1, CHUNK_CELLS // n_u)
    for r0 in range(0, n_lines, rows_per):
        r1 = min(n_lines, r0 + rows_per)
        idx = np.arange(r0, r1)
        v = vmin + idx[:, None] * spacing_mm
        x = u[None, :] * d[0] + v * n[0]
        y = u[None, :] * d[1] + v * n[1]
        on = _mask_rows(mask, f, idx, x, y)
        rows, c0, c1 = _runs(on)
        for r, a0, a1 in zip(rows.tolist(), c0.tolist(), c1.tolist()):
            u0, u1 = umin + a0 * du, umin + a1 * du
            if u1 - u0 >= MIN_RUN_MM:
                lines[r0 + r].append((u0, u1))
    return d, n, vmin, lines


TURN_POINTS = 7                  # nửa vòng tròn quay đầu: 7 điểm = 6 đoạn, mỗi chỗ rẽ ~30° (máy giữ được ~24 mm/s)


def serpentine(d, n, vmin, lines, spacing_mm: float, shape=None, round_turns: bool = True):
    """Nối các đoạn của dòng kề nhau thành nét liền kiểu zigzag (đi - về). shape(u0,u1,v)->mảng (k,2) tùy biến.

    Chỉ nối khi đầu vào của đoạn mới ở gần cuối đoạn trước (theo hướng quét): ít nhấc bút nhất mà
    đường nối không băng qua vùng trắng xa.

    round_turns: chỗ quay đầu là NỬA VÒNG TRÒN bán kính spacing / 2 (đỉnh vòng tròn đúng tại mép đoạn), không phải
    hai góc vuông. Hai góc vuông ép máy giảm tốc gần về 0 (junction_deviation 0,01 mm: ~7 mm/s) và bút đứng lâu ở mép
    nên mực loang thành giọt; nửa vòng tròn giữ ~24 mm/s và đỡ chậm hơn nhiều.
    """
    jump = max(2.5 * spacing_mm, 0.8)
    r = spacing_mm / 2.0

    def make(a, b, v):
        return shape(a, b, v) if shape else np.array([[a, v], [b, v]])

    # nét = {"parts": [mảng uv...], "last": (a_dùng, v) của đoạn cuối}
    strokes: list[dict] = []
    open_prev: list[tuple[float, dict, float]] = []             # (u cuối, nét, hướng ±1) của dòng trước
    for i, runs in enumerate(lines):
        v = vmin + i * spacing_mm
        forward = (i % 2 == 0)
        taken: set[int] = set()
        open_now: list[tuple[float, dict, float]] = []
        for u0, u1 in (runs if forward else reversed(runs)):
            a, b = (u0, u1) if forward else (u1, u0)             # đi từ a tới b
            sgn = 1.0 if b > a else -1.0
            best, bd = -1, jump
            for k, (ue, _, _) in enumerate(open_prev):
                if k not in taken and abs(ue - a) <= bd:
                    best, bd = k, abs(ue - a)
            if best < 0:
                stroke = {"parts": [make(a, b, v)], "last": (a, v)}
                strokes.append(stroke)
            else:
                taken.add(best)
                ue, stroke, psgn = open_prev[best]
                a_prev, v_prev = stroke["last"]
                apex = (ue + a) / 2.0
                cut = apex - psgn * r                            # hai đầu cung nằm cùng u, đỉnh cung tại apex
                turn = (round_turns and abs(ue - a) <= 0.7 * r
                        and (cut - a_prev) * psgn >= r and (b - cut) * sgn >= 2 * r)
                if turn:
                    stroke["parts"][-1] = make(a_prev, cut, v_prev)
                    t = np.linspace(-math.pi / 2, math.pi / 2, TURN_POINTS)
                    stroke["parts"].append(np.stack([cut + psgn * r * np.cos(t),
                                                     (v_prev + v) / 2 + (v - v_prev) / 2 * np.sin(t)], axis=1))
                    a = cut
                stroke["parts"].append(make(a, b, v))
                stroke["last"] = (a, v)
            open_now.append((b, stroke, sgn))
        open_prev = open_now
    out = []
    for st in strokes:
        uv = np.concatenate(st["parts"])
        xy = np.stack([uv[:, 0] * d[0] + uv[:, 1] * n[0], uv[:, 0] * d[1] + uv[:, 1] * n[1]], axis=1)
        out.append(xy)
    return out


def sine_shape(amplitude: float, wavelength: float, step: float):
    """Hàm tạo đường sóng dọc theo đoạn (pha cố định theo u nên các dòng kề nhau song song nhau)."""
    def shape(a: float, b: float, v: float) -> np.ndarray:
        length = abs(b - a)
        k = max(2, int(length / step) + 1)
        uu = np.linspace(a, b, k)
        vv = v + amplitude * np.sin(2 * math.pi * uu / wavelength)
        return np.stack([uu, vv], axis=1)
    return shape


# --- sóng biến thiên: một lưới sóng phủ cả ảnh, độ đậm đổi liền theo độ dài nét ------------------
# Đường sóng v = A·sin(2πu/λ) dài gấp F(k) lần đường thẳng, k = 2πA/λ. Nét rộng w cách nhau s phủ w·F/s.
# Muốn độ phủ c thì F = c·s/w -> tra ngược ra k -> chọn λ, A. Không có ngưỡng nên không có ranh giới mức.
_K_TAB = np.linspace(0.0, 14.0, 281)
_F_TAB = np.sqrt(1.0 + (_K_TAB[:, None] * np.cos(np.linspace(0.0, math.pi / 2, 256))[None, :]) ** 2).mean(axis=1)
AM_WAVE_POINTS = 8               # điểm mỗi bước sóng khi sóng thưa (mắt thấy rõ độ cong)
AM_TIGHT_POINTS = 4              # sóng dày (λ ngắn): 4 điểm = đỉnh + qua gốc, nhỏ hơn bề rộng nét nên không thấy góc
AM_TIGHT_MM = 2.0                # λ ngắn hơn chừng này coi là sóng dày


def sine_k_for_length(F: np.ndarray) -> np.ndarray:
    """F (độ dài đường sóng ÷ đường thẳng, >= 1) -> k = 2πA/λ."""
    return np.interp(F, _F_TAB, _K_TAB)


def sine_length_factor(k: np.ndarray) -> np.ndarray:
    return np.interp(k, _K_TAB, _F_TAB)


def _sample(img: np.ndarray, f: Field, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    ix = np.clip(np.floor(x * (f.w / f.width_mm)).astype(np.int32), 0, f.w - 1)
    iy = np.clip(np.floor(y * (f.h / f.height_mm)).astype(np.int32), 0, f.h - 1)
    return img[iy, ix]


def _clean_1d(on: np.ndarray, gap: int, run: int) -> np.ndarray:
    """Lấp khe ngắn hơn `gap` mẫu rồi bỏ đoạn ngắn hơn `run` mẫu (ngưỡng chập chờn sinh nét vụn)."""
    _, s, e = _runs(on[None, :])
    out = np.zeros_like(on)
    merged: list[list[int]] = []
    for a0, a1 in zip(s.tolist(), e.tolist()):
        if merged and a0 - merged[-1][1] - 1 < gap:
            merged[-1][1] = a1
        else:
            merged.append([a0, a1])
    for a0, a1 in merged:
        if a1 - a0 + 1 >= run:
            out[a0:a1 + 1] = True
    return out


def am_wave_rows(cov: np.ndarray, f: Field, angle_deg: float, spacing_mm: float, row_threshold, local_cover,
                 amp_cap: float, wave_min: float, wave_max: float, min_run_mm: float, tight_points: bool = False):
    """Các dòng sóng biến thiên. `cov` = độ phủ mong muốn (đã làm mờ), `row_threshold(i)` = độ phủ tối thiểu để dòng i
    có mặt (dòng thưa / dày, xem styles.wave_am_groups), `local_cover(c)` = độ phủ của các dòng thẳng đang có mặt ở độ
    phủ c. Trả (d, n, rows): rows[i] = danh sách mảng uv (k, 2) theo chiều u tăng."""
    a = math.radians(angle_deg)
    d = np.array([math.cos(a), math.sin(a)])
    n = np.array([-math.sin(a), math.cos(a)])
    corners = np.array([[0, 0], [f.width_mm, 0], [0, f.height_mm], [f.width_mm, f.height_mm]])
    us, vs = corners @ d, corners @ n
    umin, umax = float(us.min()), float(us.max())
    vmin = float(vs.min()) + spacing_mm / 2
    n_lines = int((float(vs.max()) - vmin) / spacing_mm) + 1
    du = min(max(f.px_mm * 0.7, 1e-3), wave_min / AM_WAVE_POINTS)
    u = umin + np.arange(int((umax - umin) / du) + 1) * du
    min_run = max(2, int(round(min_run_mm / du)))
    min_gap = max(1, int(round(0.5 * min_run_mm / du)))
    rows: list[list[np.ndarray]] = []
    for i in range(n_lines):
        v = vmin + i * spacing_mm
        x, y = u * d[0] + v * n[0], u * d[1] + v * n[1]
        inside = (x >= 0) & (x <= f.width_mm) & (y >= 0) & (y <= f.height_mm)
        c = np.where(inside, _sample(cov, f, x, y), 0.0)
        on = _clean_1d(inside & (c >= row_threshold(i)), min_gap, min_run)
        if not on.any():
            rows.append([])
            continue
        F = np.maximum(1.0, c / np.maximum(local_cover(c), 1e-6))
        k = sine_k_for_length(F)
        if wave_max <= wave_min:
            # bước sóng cố định, pha tính từ cùng một gốc u cho mọi đường: các đường sóng song song, không cắt nhau
            lam = np.full_like(u, wave_min)
            phi = 2 * math.pi * (u - umin) / wave_min
        else:
            lam = np.clip(2 * math.pi * amp_cap / np.maximum(k, 1e-9), wave_min, wave_max)
            phi = np.cumsum(2 * math.pi / lam * du)             # pha cộng dồn: λ đổi dần mà sóng không bị gãy
        amp = np.minimum(k * lam / (2 * math.pi), amp_cap)
        offset = amp * np.sin(phi)
        per_wave = np.where(tight_points | (lam < AM_TIGHT_MM), AM_TIGHT_POINTS, AM_WAVE_POINTS)
        q = np.floor(phi / (2 * math.pi) * per_wave)              # điểm giữ lại: mỗi khi pha qua 1/4 hoặc 1/8 bước sóng
        _, s, e = _runs(on[None, :])
        runs = []
        for a0, a1 in zip(s.tolist(), e.tolist()):
            idx = np.arange(a0, a1 + 1)
            keep = np.zeros(len(idx), dtype=bool)
            keep[0] = keep[-1] = True
            keep[1:] |= q[idx[1:]] != q[idx[:-1]]
            idx = idx[keep]
            runs.append(np.stack([u[idx], v + offset[idx]], axis=1))
        rows.append(runs)
    return d, n, rows


def _turn(p: np.ndarray, q: np.ndarray, sgn: float, points: int) -> np.ndarray:
    """Nửa vòng tròn từ p tới q (không gồm hai đầu), phình về phía u tăng nếu sgn > 0."""
    r = float(np.linalg.norm(q - p)) / 2
    if r < 1e-6:
        return np.empty((0, 2))
    e = (q - p) / (2 * r)
    out = np.array([e[1], -e[0]])
    if out[0] * sgn < 0:
        out = -out
    t = np.linspace(-math.pi / 2, math.pi / 2, points)[1:-1]
    return (p + q) / 2 + r * (np.sin(t)[:, None] * e + np.cos(t)[:, None] * out)


def _trim_turn(prev: np.ndarray, seg: np.ndarray, sgn: float):
    """prev đi theo chiều sgn rồi quay đầu sang seg (đi chiều ngược lại). Cắt (hoặc nối dài chút ít) hai đầu tại `cut`
    sao cho đỉnh nửa vòng tròn nằm ở giữa hai đầu cũ, như `serpentine`: vòng quay không lòi ra ngoài đầu dòng (ở mép
    ảnh sẽ bị ép vào khung thành vệt dọc mép). Trả (prev mới, cung, seg mới), hoặc None nếu một đoạn ngắn hơn bán kính."""
    def v_at(arr: np.ndarray, u: float) -> float:
        order = np.argsort(arr[:, 0])
        return float(np.interp(u, arr[order, 0], arr[order, 1]))

    r = abs(seg[0, 1] - prev[-1, 1]) / 2
    if r < 1e-6:
        return None
    cut = (prev[-1, 0] + seg[0, 0]) / 2 - sgn * r
    if (cut - prev[0, 0]) * sgn < r or (cut - seg[-1, 0]) * sgn < r:
        return None
    p_end = np.array([cut, v_at(prev, cut)])
    s_start = np.array([cut, v_at(seg, cut)])
    new_prev = np.vstack([prev[(prev[:, 0] - cut) * sgn < 0], p_end])
    new_seg = np.vstack([s_start, seg[(seg[:, 0] - cut) * sgn < 0]])
    return new_prev, _turn(p_end, s_start, sgn, TURN_POINTS), new_seg


def join_rows(rows: list[list[np.ndarray]], spacing_mm: float, max_gap_rows: int = 4, max_turn_mm: float | None = None,
              fixed_reach: bool = False, reach_mm: float | None = None, turn_only: bool = False) -> list[np.ndarray]:
    """Nối các đoạn của những dòng gần nhau thành nét liền (kiểu zigzag) khi lưới có dòng thưa, dòng dày.

    Khác `serpentine`: dòng trước có thể cách 1–max_gap_rows dòng (dòng ở giữa vắng mặt), và chiều đi của mỗi đoạn
    tự chọn theo đầu gần chỗ bút đang đứng. Quay đầu bằng nửa vòng tròn.
    `max_turn_mm`: vòng quay đầu cao tối đa (khoảng cách hai dòng); `fixed_reach`: hai đầu chỉ được lệch nhau
    max(2,5 × khoảng cách, 0,8 mm) dù cách mấy dòng (không thì nới theo số dòng cách); `reach_mm` đặt thẳng mức lệch
    tối đa. `turn_only`: chỉ nối khi đoạn mới đi ngược chiều (quay đầu), không nối chéo kiểu bậc thang.
    Đoạn nối dài là mực thừa."""
    strokes: list[list[np.ndarray]] = []
    open_ends: list[tuple[int, np.ndarray, int, float]] = []      # (dòng, điểm cuối, nét, chiều đi ±1)
    for i, runs in enumerate(rows):
        taken: set[int] = set()
        fresh: list[tuple[int, np.ndarray, int, float]] = []
        for run in runs:
            best = None
            for k, (row, pt, _, _) in enumerate(open_ends):
                if k in taken:
                    continue
                gap = i - row
                if max_turn_mm is not None and gap > 1 and gap * spacing_mm > max_turn_mm:
                    continue
                reach = reach_mm if reach_mm is not None else max(2.5 * (1 if fixed_reach else gap) * spacing_mm, 0.8)
                psgn = open_ends[k][3]
                for rev in (False, True):
                    if turn_only and (-1.0 if rev else 1.0) == psgn:     # đoạn mới phải đi ngược chiều nét trước
                        continue
                    du = abs((run[-1] if rev else run[0])[0] - pt[0])
                    if du <= reach and (best is None or (gap, du) < best[0]):
                        best = ((gap, du), k, rev)
            if best is None:
                strokes.append([run])
                fresh.append((i, run[-1], len(strokes) - 1, 1.0 if run[-1][0] >= run[0][0] else -1.0))
                continue
            _, k, rev = best
            taken.add(k)
            _, pt, sid, sgn = open_ends[k]
            seg = run[::-1] if rev else run
            new_sgn = 1.0 if seg[-1][0] >= seg[0][0] else -1.0
            turn = _trim_turn(strokes[sid][-1], seg, sgn) if new_sgn != sgn else None
            if turn is not None:                                 # quay đầu: nửa vòng tròn, đỉnh ở giữa hai đầu cũ
                strokes[sid][-1], arc, seg = turn
                strokes[sid].append(arc)
            strokes[sid].append(seg)                             # không quay được (đoạn quá ngắn) / cùng chiều: nối thẳng
            fresh.append((i, seg[-1], sid, new_sgn))
        open_ends = [e for k, e in enumerate(open_ends) if k not in taken and i + 1 - e[0] <= max_gap_rows] + fresh
    return [np.concatenate(parts) for parts in strokes]


def uv_to_xy(d, n, uv: np.ndarray) -> np.ndarray:
    return np.stack([uv[:, 0] * d[0] + uv[:, 1] * n[0], uv[:, 0] * d[1] + uv[:, 1] * n[1]], axis=1)


# --- xoắn ốc --------------------------------------------------------------------------
def spiral_runs(mask, f: Field, pitch_mm: float, phase: float = 0.0):
    """Xoắn ốc Archimedes từ tâm ảnh, bước pitch_mm; cắt theo mặt nạ. Mỗi đoạn True là một nét.

    Mỗi nét tốn một lần nhấc + hạ bút (~0,25 s = ~20 mm vẽ ở 5000 mm/min), nên nối qua khe trắng tới
    6 × bước (tối thiểu BRIDGE_MM) và bỏ mẩu ngắn hơn 4 × bước (gần như không thấy)."""
    cx, cy = f.width_mm / 2, f.height_mm / 2
    r_max = math.hypot(cx, cy) + pitch_mm
    step = max(f.px_mm * 0.7, 1e-3)
    total = math.pi * r_max * r_max / pitch_mm                  # chiều dài xấp xỉ
    n = int(total / step) + 1
    strokes = []
    bridge = max(BRIDGE_MM, SPIRAL_BRIDGE_PITCHES * pitch_mm)
    min_run = max(MIN_RUN_MM, SPIRAL_MIN_PITCHES * pitch_mm)
    for k0 in range(0, n, CHUNK_CELLS):
        k = np.arange(k0, min(n, k0 + CHUNK_CELLS + 1), dtype=np.float64)    # chồng 1 mẫu để không đứt nét
        theta = np.sqrt(4 * math.pi * k * step / pitch_mm)
        r = pitch_mm * theta / (2 * math.pi) + phase * pitch_mm
        x, y = cx + r * np.cos(theta), cy + r * np.sin(theta)
        turns = np.floor(theta / (2 * math.pi)).astype(np.int64)          # vòng xoắn thứ mấy = "dòng" thứ mấy
        on = _mask_rows(mask, f, turns, x, y)[None, :]
        _, s, e = _runs(on)
        runs = list(zip(s.tolist(), e.tolist()))
        merged: list[list[int]] = []
        for a0, a1 in runs:
            if merged and (a0 - merged[-1][1]) * step <= bridge:
                merged[-1][1] = a1                              # nối qua khe trắng ngắn
            else:
                merged.append([a0, a1])
        for a0, a1 in merged:
            if (a1 - a0) * step >= min_run:
                strokes.append(np.stack([x[a0:a1 + 1], y[a0:a1 + 1]], axis=1))
    return strokes
