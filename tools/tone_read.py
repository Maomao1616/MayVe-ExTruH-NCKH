r"""Đọc ảnh chụp Thang tông / tờ hiệu chỉnh tông -> độ đậm mắt thấy của 16 ô (docs/07 mục 2b, docs/06 mục 8.12).

    cd backend && .venv\Scripts\python.exe ..\tools\tone_read.py anh.jpg [--paper a6] [--crop x0,y0,x1,y1]
                 [--kind crosshatch_flow] [--out kiem.png] [--json ket_qua.json]

Cách đo (13/11/2026): tìm 3 ô mốc đen (trên phải, dưới trái, dưới phải; ô góc vuông = dưới phải, cạnh dài = phải),
nắn phối cảnh từ 12 góc ô mốc, bù ánh sáng bằng mặt phẳng khớp với giấy ở khe giữa các ô (bỏ điểm dính mực), đọc 60 %
giữa mỗi ô. Cột "mực" = lượng mực (tuyến tính theo ánh sáng), cột "đậm" = độ đậm mắt thấy theo CIE L*, cả hai quy về
0 = giấy, 1 = ô mốc đen. Ảnh lật gương / xoay vẫn đọc được. Ảnh chụp nhiều tờ: cắt từng tờ bằng --crop (điểm ảnh).

--kind: so với đường cong tông đang dùng (styles.TONE_CURVES): ảnh Thang tông vẽ ĐÚNG thì độ đậm ô i ≈ TONE_STEPS[i] ×
V(0,9) ÷ 0,9 (V = độ đậm bảng ở độ phủ 0,9). Có 5 mức nên 16 ô gom ~5 bậc: nhìn độ lệch trung bình, không từng ô.
--out ghi ảnh có khung đỏ từng ô đo + số, để kiểm công cụ đo đúng chỗ. Thử trên ảnh giả lập (méo phối cảnh, đèn lệch,
nhiễu, lật gương) và ảnh thật 13/11 (4 tờ một ảnh, mốc khớp lệch ~0,5 mm).
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.drawing import calibration as cal, styles      # noqa: E402

TOP, GRID, MARK = cal.TONE_TOP, cal.TONE_GRID, cal.TONE_MARK
INNER = 0.6                       # đọc 60 % giữa ô (bỏ mép, chỗ quay đầu nét)
PAPER_DARK_CUT = 0.97             # điểm giấy tối hơn mặt phẳng ánh sáng > 3 % = dính mực, bỏ khi khớp lại


def geometry(paper: str):
    z = cal.TONE_SIZES[paper]
    patch, gap = z["patch"], z["gap"]
    w = GRID * patch + (GRID - 1) * gap
    h = TOP + GRID * patch + (GRID - 1) * gap + 3.0 + MARK
    marks = {"TR": (w - MARK, 0.0), "BL": (0.0, h - MARK), "BR": (w - MARK, h - MARK)}
    return patch, gap, w, h, marks


def srgb_lin(v):
    v = np.asarray(v, float) / 255.0
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def lstar(y):
    y = np.clip(y, 1e-6, None)
    return np.where(y > 0.008856, 116 * np.cbrt(y) - 16, 903.3 * y)


def find_marks(gray, w, h):
    blur = cv2.GaussianBlur(gray, (0, 0), max(1.0, gray.shape[1] / 1500))
    _, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    cnts, _ = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cands = []
    for c in cnts:
        a = cv2.contourArea(c)
        if a < 50:
            continue
        rect = cv2.minAreaRect(c)
        rw, rh = rect[1]
        if min(rw, rh) <= 0 or max(rw, rh) / min(rw, rh) > 1.4 or a / (rw * rh) < 0.8:
            continue
        cands.append((a, rect))
    cands = sorted(cands, key=lambda t: -t[0])[:40]
    want = (h - MARK) / (w - MARK)
    best = None
    for (a1, r1), (a2, r2), (a3, r3) in itertools.combinations(cands, 3):
        areas = np.array([a1, a2, a3])
        if areas.max() / areas.min() > 1.8:
            continue
        rects = (r1, r2, r3)
        pts = [np.array(r[0]) for r in rects]
        for k in range(3):                                   # k = đỉnh góc vuông (ô dưới phải)
            o = [i for i in range(3) if i != k]
            v1, v2 = pts[o[0]] - pts[k], pts[o[1]] - pts[k]
            l1, l2 = np.linalg.norm(v1), np.linalg.norm(v2)
            if min(l1, l2) < 1:
                continue
            cos = abs(v1 @ v2) / (l1 * l2)
            ratio = max(l1, l2) / min(l1, l2)
            size_ratio = np.sqrt(areas.mean()) / max(l1, l2) / (MARK / (h - MARK))
            score = cos * 5 + abs(ratio / want - 1) * 3 + abs(np.log(size_ratio))
            if best is None or score < best[0]:
                tr, bl = (o[0], o[1]) if l1 > l2 else (o[1], o[0])   # cạnh dài = dưới phải -> trên phải
                best = (score, {"BR": rects[k], "TR": rects[tr], "BL": rects[bl]})
    if best is None or best[0] > 1.0:
        raise SystemExit(f"Không tìm thấy 3 ô mốc đen (điểm {None if best is None else round(best[0], 2)}). "
                         "Chụp thấy đủ 3 ô mốc, hoặc cắt từng tờ bằng --crop.")
    return best[1], best[0]


def homography(rects, marks):
    names = ("TR", "BL", "BR")
    centers_mm = np.float32([[marks[n][0] + MARK / 2, marks[n][1] + MARK / 2] for n in names])
    centers_px = np.float32([rects[n][0] for n in names])
    aff = cv2.getAffineTransform(centers_mm, centers_px)
    src, dst = [], []
    for n in names:
        x0, y0 = marks[n]
        corners = cv2.boxPoints(rects[n])
        for cx, cy in ((x0, y0), (x0 + MARK, y0), (x0 + MARK, y0 + MARK), (x0, y0 + MARK)):
            guess = aff @ np.array([cx, cy, 1.0])
            src.append((cx, cy))
            dst.append(corners[np.argmin(np.linalg.norm(corners - guess, axis=1))])
    H, _ = cv2.findHomography(np.float32(src), np.float32(dst))
    err = max(np.linalg.norm((H @ [x, y, 1.0])[:2] / (H @ [x, y, 1.0])[2] - d) for (x, y), d in zip(src, dst))
    return H, float(err)


def sample(gray, H, x0, y0, size, inner=INNER):
    m = size * (1 - inner) / 2
    poly = np.float32([[x0 + m, y0 + m], [x0 + size - m, y0 + m], [x0 + size - m, y0 + size - m], [x0 + m, y0 + size - m]])
    px = cv2.perspectiveTransform(poly[None], H)[0]
    mask = np.zeros(gray.shape, np.uint8)
    cv2.fillPoly(mask, [np.int32(np.round(px))], 255)
    return float(np.mean(srgb_lin(gray[mask > 0]))), px


def paper_plane(gray, H, patch, gap):
    """Ánh sáng trên giấy: mặt phẳng a + b·x + c·y khớp với giấy ở giữa các khe giữa ô."""
    pts, vals = [], []
    step = patch + gap
    for r in range(GRID):
        for c in range(GRID):
            for t in (0.25, 0.5, 0.75):
                if c < GRID - 1:
                    x, y = c * step + patch + gap / 2, TOP + r * step + patch * t
                    pts.append((x, y)); vals.append(sample(gray, H, x - 0.5, y - 0.5, 1.0, 1.0)[0])
                if r < GRID - 1:
                    x, y = c * step + patch * t, TOP + r * step + patch + gap / 2
                    pts.append((x, y)); vals.append(sample(gray, H, x - 0.5, y - 0.5, 1.0, 1.0)[0])
    pts, vals = np.array(pts), np.array(vals)
    A = np.c_[np.ones(len(pts)), pts]
    keep = np.ones(len(vals), bool)
    for _ in range(4):
        coef, *_ = np.linalg.lstsq(A[keep], vals[keep], rcond=None)
        keep = vals >= (A @ coef) * PAPER_DARK_CUT
    return coef, float(np.std((vals - A @ coef)[keep]) / np.mean(vals[keep]))


def expected(kind: str | None) -> list[float] | None:
    if not kind:
        return None
    table = styles.TONE_CURVES.get(styles.TONE_CURVE_STYLES.get(kind, ""))
    if table is None:
        raise SystemExit(f"Kiểu {kind} chưa có đường cong tông (có: {', '.join(styles.TONE_CURVE_STYLES)}).")
    v_max = float(np.interp(styles.MAX_COVERAGE, styles.TONE_COVERS, np.maximum.accumulate(table)))
    return [min(d, styles.MAX_COVERAGE) * v_max / styles.MAX_COVERAGE for d in cal.TONE_STEPS]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--paper", default="a6", choices=sorted(cal.TONE_SIZES), help="hình học tờ (Thang tông luôn a6)")
    ap.add_argument("--crop", help="x0,y0,x1,y1 (điểm ảnh) khi ảnh chụp nhiều tờ")
    ap.add_argument("--kind", help="so với đường cong tông của kiểu này (vd crosshatch_flow, spiral)")
    ap.add_argument("--out", help="ảnh kiểm tra (khung đỏ = chỗ đo)")
    ap.add_argument("--json", help="ghi kết quả")
    a = ap.parse_args()
    img = cv2.imdecode(np.fromfile(a.image, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit("Không đọc được ảnh.")
    if a.crop:
        x0, y0, x1, y1 = (int(v) for v in a.crop.split(","))
        img = img[y0:y1, x0:x1]
    if max(img.shape[:2]) > 4000:
        k = 4000 / max(img.shape[:2])
        img = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    patch, gap, w, h, marks = geometry(a.paper)
    rects, score = find_marks(gray, w, h)
    H, err = homography(rects, marks)
    px_mm = np.linalg.norm(np.array(rects["BR"][0]) - np.array(rects["BL"][0])) / (w - MARK)
    coef, noise = paper_plane(gray, H, patch, gap)

    def white(x, y):
        return coef[0] + coef[1] * x + coef[2] * y

    rb = float(np.mean([sample(gray, H, *marks[n], MARK)[0] / white(marks[n][0] + MARK / 2, marks[n][1] + MARK / 2)
                        for n in ("TR", "BL", "BR")]))
    lb = float(lstar(rb))
    want = expected(a.kind)
    rows, dbg = [], img.copy()
    t = max(1, int(px_mm / 4))
    for i, cover in enumerate(cal.TONE_STEPS):
        r, c = divmod(i, GRID)
        x0, y0 = c * (patch + gap), TOP + r * (patch + gap)
        v, poly = sample(gray, H, x0, y0, patch)
        rel = v / white(x0 + patch / 2, y0 + patch / 2)
        row = {"n": i, "cover": cover, "ink": round((1 - rel) / (1 - rb), 3),
               "dark": round((100 - float(lstar(rel))) / (100 - lb), 3)}
        if want:
            row["want"] = round(want[i], 3)
        rows.append(row)
        cv2.polylines(dbg, [np.int32(np.round(poly))], True, (0, 0, 255), t)
        cv2.putText(dbg, f"{row['dark']:.2f}", tuple(np.int32(poly[0])), cv2.FONT_HERSHEY_SIMPLEX, px_mm / 12, (255, 0, 0), t)
    for n in rects:
        cv2.polylines(dbg, [np.int32(cv2.boxPoints(rects[n]))], True, (0, 200, 0), t)
    print(f"mốc: điểm {score:.2f}, khớp góc lệch {err / px_mm:.2f} mm, {px_mm:.1f} điểm ảnh/mm; "
          f"giấy không đều sau bù sáng {noise * 100:.1f} %; ô mốc: phản xạ {rb:.3f}, L* {lb:.1f}")
    print("ô  phủ/xám  mực    đậm" + ("   muốn   lệch" if want else ""))
    for r in rows:
        extra = f"  {r['want']:.3f}  {r['dark'] - r['want']:+.3f}" if want else ""
        print(f"{r['n']:2d}  {r['cover']:.2f}    {r['ink']:.3f}  {r['dark']:.3f}{extra}")
    mono = all(b["dark"] >= p["dark"] - 0.02 for p, b in zip(rows, rows[1:]))
    print("tăng dần:", "có" if mono else "KHÔNG (xem ảnh kiểm tra / ô lỗi)")
    if want:
        print(f"lệch trung bình so với đường cong: {np.mean([abs(r['dark'] - r['want']) for r in rows]):.3f}")
    if a.out:
        cv2.imwrite(a.out, dbg)
    if a.json:
        Path(a.json).write_text(json.dumps({"black_reflect": rb, "match_err_mm": err / px_mm, "rows": rows},
                                           ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
