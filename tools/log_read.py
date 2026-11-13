r"""Đọc nhật ký chạy máy data/job_logs/<id>.csv (services/joblog.py): hàng đợi cạn lúc nào, tốc độ thật, từng vùng.

    cd backend && .venv\Scripts\python.exe ..\tools\log_read.py ..\data\job_logs\<id>.csv [--split-x 5]

- "Cạn" = bf_planner bằng số khối trống lớn nhất từng thấy (không còn lệnh nào trong máy). Cần `$10=3` mới có Bf.
- Tốc độ thật tính bằng quãng đường X/Y giữa hai mẫu ÷ thời gian, KHÔNG dùng cột feed (`FS:`): máy CoreXY báo cao hơn
  thật tới 1,41 lần tùy hướng (docs/02 F15).
- --split-x: tách các đoạn bút xuống theo khe X lớn hơn số mm này (bài 7.6: 5 vòng tròn xếp ngang), mỗi đoạn một dòng.
Dùng 13/11/2026 cho tờ 7.6 (đoạn 1 / 0,5 / 0,25 / 0,1 mm: 6,0 / 11,6 / 23,3 / 60,7 s, ~125 dòng/giây; G2 5,7 s).
"""
from __future__ import annotations

import argparse
import csv
import math
import sys

PEN_DOWN_TOL = 0.3        # Z cách Z thấp nhất không quá chừng này = bút xuống


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--split-x", type=float, help="tách đoạn bút xuống theo khe X (mm)")
    a = ap.parse_args()
    with open(a.csv, encoding="utf-8") as fh:
        rows = [{k: (r[k] if k == "state" else num(r[k])) for k in r} for r in csv.DictReader(fh)]
    if not rows:
        raise SystemExit("Tệp rỗng.")
    zs = [r["z"] for r in rows if r["z"] is not None]
    zdown = min(zs) + PEN_DOWN_TOL if zs else 0.0
    bfs = [r["bf_planner"] for r in rows if r["bf_planner"] is not None]
    top = max(bfs) if bfs else None
    for p, q in zip(rows, rows[1:]):                      # tốc độ thật giữa hai mẫu (mm/phút)
        dt = (q["t"] or 0) - (p["t"] or 0)
        q["v"] = (60 * math.hypot(q["x"] - p["x"], q["y"] - p["y"]) / dt
                  if dt > 0 and None not in (p["x"], p["y"], q["x"], q["y"]) else None)
    rows[0]["v"] = None
    run = [r for r in rows if r["state"].startswith("Run")]
    sent = [r["sent"] for r in rows if r["sent"] is not None]
    print(f"{len(rows)} mẫu, {rows[-1]['t']:.1f} s, dòng đã gửi {int(max(sent)) if sent else '?'}, "
          f"~{(max(sent) / rows[-1]['t']) if sent and rows[-1]['t'] else 0:.0f} dòng/giây trung bình")
    if top is None:
        raise SystemExit("Không có Bf (chưa gõ $10=3?).")
    down = [r for r in run if r["z"] is not None and r["z"] <= zdown]
    up = [r for r in run if r["z"] is not None and r["z"] > zdown]
    for name, rs in (("bút xuống", down), ("bút lên", up)):
        if rs:
            starve = sum(r["bf_planner"] >= top for r in rs if r["bf_planner"] is not None)
            vs = [r["v"] for r in rs if r["v"]]
            print(f"{name}: {len(rs)} mẫu, cạn {100 * starve / len(rs):.1f} %, tốc độ thật tb {sum(vs) / max(1, len(vs)):.0f} mm/phút")
    events, cur = [], None
    for r in run:
        s = r["bf_planner"] is not None and r["bf_planner"] >= top
        if s and cur is None:
            cur = [r["t"], r["t"], r["z"] is not None and r["z"] <= zdown]
        elif s:
            cur[1] = r["t"]
        elif cur:
            events.append(cur)
            cur = None
    if cur:
        events.append(cur)
    print(f"số lần cạn: {len(events)} ({sum(1 for e in events if e[2])} lúc bút xuống)")
    for e in events[:15]:
        print(f"  t {e[0]:.1f}–{e[1]:.1f} s  {'bút xuống' if e[2] else 'bút lên'}")
    if a.split_x and down:
        xs = sorted(down, key=lambda r: r["x"])
        groups, g = [], [xs[0]]
        for r in xs[1:]:
            if r["x"] - g[-1]["x"] > a.split_x:
                groups.append(g)
                g = []
            g.append(r)
        groups.append(g)
        print("đoạn  x (mm)         t (s)  tốc độ thật tb  cạn %  dòng/giây")
        for i, g in enumerate(groups, 1):
            g.sort(key=lambda r: r["t"])
            dur = g[-1]["t"] - g[0]["t"]
            vs = [r["v"] for r in g if r["v"]]
            st = 100 * sum(r["bf_planner"] >= top for r in g) / len(g)
            lines = (g[-1]["sent"] - g[0]["sent"]) / dur if dur > 0 and g[0]["sent"] is not None else 0
            print(f"{i:4d}  {min(r['x'] for r in g):6.1f}–{max(r['x'] for r in g):6.1f}  {dur:6.1f}  {sum(vs) / max(1, len(vs)):10.0f}  "
                  f"{st:5.0f}  {lines:8.0f}")


if __name__ == "__main__":
    main()
