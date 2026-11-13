r"""Mô phỏng mực: nét (mm) -> ảnh độ phủ mực với bề rộng nét thật, so với độ đậm mong muốn. Không cần in giấy.

    cd backend && .venv\Scripts\python.exe ..\tools\ink_sim.py

Dựng ảnh thử (dải chuyển liền + đốm tròn mềm), chạy từng kiểu tô, vẽ lại các nét với bề rộng LINE_W rồi làm mờ
~2 mm (mắt nhìn xa) và so với độ đậm mong muốn. In: sai số trung bình (nhỏ = đúng tông hơn), tổng chiều dài nét,
thời gian ước tính (vẽ 5000 mm/min, mỗi nét = một lần nhấc + hạ bút ~0,25 s). Ảnh mô phỏng ghi vào export/ink-sim/.

Giới hạn: ảnh thử tổng hợp, chỉ đo tông ở cỡ ~2 mm, không đo độ sắc nét hay vẻ đẹp; giả định mực không loang thêm
khi hai nét chồng nhau. Dùng để SO SÁNH thuật toán với nhau, không phải để đoán độ đậm tuyệt đối trên giấy.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.drawing import spec, styles          # noqa: E402
from app.services.drawing.hatch import Field           # noqa: E402

W_MM, H_MM, PX = 80.0, 50.0, 0.2          # ảnh nguồn 0,2 mm / điểm
SC = 20                                    # mô phỏng 20 điểm / mm
LINE_W = styles.LINE_WIDTH_RATIO * 0.45    # bề rộng nét Sakura 0,4 trên Ivory (ô "Bút vẽ" mặc định, spec.PENS)
DRAW_FEED, LIFT_S = 5000.0, 0.25


def target() -> np.ndarray:
    h, w = int(H_MM / PX), int(W_MM / PX)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ramp = xx / (w - 1)
    rad = np.clip(1 - np.hypot(xx - w * 0.5, yy - h * 0.5) / (h * 0.45), 0, 1) ** 1.2
    img = np.where(xx < w * 0.55, ramp / 0.55 * 0.9, rad)
    return np.clip(img, 0, 1).astype(np.float32)


def render(strokes) -> np.ndarray:
    canvas = np.zeros((int(H_MM * SC), int(W_MM * SC)), np.uint8)
    for s in strokes:
        pts = (np.asarray(s) * SC).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(canvas, [pts], False, 255, int(round(LINE_W * SC)), cv2.LINE_AA)
    return canvas.astype(np.float32) / 255.0


def metrics(strokes, dark: np.ndarray) -> dict:
    ink = render(strokes)
    sigma = 2.0 * SC
    got = cv2.GaussianBlur(ink, (0, 0), sigma)
    want = cv2.GaussianBlur(cv2.resize(dark, (ink.shape[1], ink.shape[0]), interpolation=cv2.INTER_AREA), (0, 0), sigma)
    length = sum(float(np.hypot(*np.diff(np.asarray(s), axis=0).T).sum()) for s in strokes)
    # "bậc": trên dải chuyển liền (nửa trái, bỏ 3 mm mép trên / dưới), tông nhìn ở ~1 mm nhảy lệch so với mong muốn
    # nhiều nhất bao nhiêu giữa hai cột cách 1 mm. Lớn = thấy rõ ranh giới mức (vệt mảng).
    near = cv2.GaussianBlur(ink, (0, 0), 1.0 * SC)
    band = near[3 * SC:-3 * SC, : int(W_MM * 0.5 * SC)].mean(axis=0)
    ideal = cv2.resize(dark, (ink.shape[1], ink.shape[0]))[3 * SC:-3 * SC, : int(W_MM * 0.5 * SC)].mean(axis=0)
    jump = float(np.abs(np.diff(band[::SC]) - np.diff(ideal[::SC])).max())
    return {"error": float(np.abs(got - want).mean()), "length_mm": length, "strokes": len(strokes), "jump": jump,
            "minutes": (length / (DRAW_FEED / 60) + len(strokes) * LIFT_S) / 60, "ink": ink, "got": got, "want": want}


def eye_error(m: dict, kind: str) -> float:
    """Sai tông MẮT THẤY: mực -> độ đậm nhìn thấy theo đường cong đo trên giấy (styles.TONE_CURVES, 13/11/2026; kiểu
    không có bảng dùng bảng đan chéo làm gần đúng), so với độ đậm ảnh (tỷ lệ với độ đậm thấy được ở MAX_COVERAGE)."""
    table = styles.TONE_CURVES["spiral" if kind == "spiral" else "crosshatch"]
    seen = np.interp(m["got"], styles.TONE_COVERS, table)
    v_max = float(np.interp(styles.MAX_COVERAGE, styles.TONE_COVERS, table))
    want = np.clip(m["want"], 0, styles.MAX_COVERAGE) * v_max / styles.MAX_COVERAGE
    return float(np.abs(seen - want).mean())


def run_style(dark: np.ndarray, pen_mm: float = 0.45, **style) -> list:
    return styles.fill(Field(dark, W_MM, H_MM), spec.parse("style", style), pen_mm, None)


CASES = {
    "zigzag cứng (cũ)": dict(kind="zigzag", soft_levels=False),
    "zigzag mềm": dict(kind="zigzag"),
    "sóng cứng (cũ)": dict(kind="wave", soft_levels=False),
    "sóng mềm": dict(kind="wave"),
    "xoắn ốc mềm": dict(kind="spiral"),
    "gạch chéo mềm": dict(kind="crosshatch"),
    "sóng biến thiên": dict(kind="wave_am"),
    "theo dáng (flow, thô)": dict(kind="flow"),
    "đan chéo + theo dáng": dict(kind="crosshatch_flow"),
}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")           # terminal Windows mặc định cp1252, không in được tiếng Việt
    out = ROOT / "export" / "ink-sim"
    out.mkdir(parents=True, exist_ok=True)
    dark = target()
    cv2.imwrite(str(out / "muc-tieu.png"), (255 * (1 - dark)).astype(np.uint8))
    print(f"{'kiểu tô':24s} {'sai số':>8s} {'sai mắt':>8s} {'bậc':>6s} {'dài mm':>8s} {'số nét':>7s} {'phút':>6s}")
    for i, (name, style) in enumerate(CASES.items()):
        m = metrics(run_style(dark, **style), dark)
        print(f"{name:24s} {m['error']:8.4f} {eye_error(m, style['kind']):8.4f} {m['jump']:6.3f} {m['length_mm']:8.0f}"
              f" {m['strokes']:7d} {m['minutes']:6.2f}")
        cv2.imwrite(str(out / f"{i}.png"), (255 * (1 - m["ink"])).astype(np.uint8))
    print(f"Ảnh mô phỏng ghi vào {out}")


if __name__ == "__main__":
    main()
