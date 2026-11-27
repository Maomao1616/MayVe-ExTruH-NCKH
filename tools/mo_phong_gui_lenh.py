#!/usr/bin/env python3
r"""Mô phỏng gửi G-code qua mạng có trễ: so 3 cách gửi để chọn cỡ kho lệnh cho ESP32-S3 (docs/07 mục 13).

    python tools/mo_phong_gui_lenh.py                       # bảng mặc định: trễ đo 27/11 (0,13 s, có lần 1,16 s)
    python tools/mo_phong_gui_lenh.py --rtt 0.3 --spike 2.0 --spike-rate 0.05
    python tools/mo_phong_gui_lenh.py --seg 2.0 --lines 5000 --esp-lines 500,2000

Chỉ dùng thư viện chuẩn, không chạm máy, không cần venv. Đây là MÔ HÌNH (giả định ghi ở dưới), không phải số đo:
dùng để so các cách gửi với nhau và chọn cỡ kho lệnh, không dùng làm thời gian vẽ thật.

Kết quả 27/11/2026 (3000 dòng nét 0,5 mm, 8000 mm/phút, lý tưởng 11,2 s):
- trễ đo được (0,13 s, vọt 1,16 s): A 570 s (chậm ~50 lần) · B 48 s (~4 lần, khựng 2 300 lần) · C kho 5000 dòng ~11,6 s, 0 khựng.
- 4G giật (0,3 s, vọt 3 s, 8 %): C gói 200 dòng vẫn khựng 1–3 lần; C gói 1000, kho 5000, nạp trước 2000: 0 khựng ở 5 hạt.
=> Chốt hướng: ESP giữ kho >= 5000 dòng (~100 KB, để trong PSRAM), máy chủ gửi gói ~1000 dòng, nạp trước ~2000 dòng
   (hoặc cả bài nếu ngắn hơn) rồi mới chạy. Số này là của mô hình; đo lại khi có mạch.

Giả định:
- Mạch (FluidNC): bộ đệm nhận BOARD_RX_BYTES; dòng vào hàng đợi chuyển động (PLANNER_BLOCKS khối) thì trả `ok`;
  mỗi khối chạy hết `seg / feed` giây (bỏ qua gia tốc). Hàng đợi cạn giữa bản vẽ = máy khựng ("khựng" trong bảng).
- Mạng: mỗi chiều mất rtt/2; mỗi lần gửi có xác suất spike_rate bị trễ cả lượt thành `spike` giây.
- Cách A "từng dòng qua mạng": máy chủ gửi 1 dòng, chờ `ok` về mới gửi tiếp (như USB hiện nay nhưng qua Internet).
- Cách B "đếm ký tự qua mạng": máy chủ gửi dồn miễn tổng byte chưa có `ok` <= bộ đệm của mạch.
- Cách C "kho lệnh trên ESP": máy chủ gửi từng gói `chunk` dòng vào kho của ESP (tối đa `esp_lines` dòng); ESP nối
  dây UART với mạch, tự gửi đếm ký tự TẠI CHỖ (trễ UART ~ byte * 10 / baud). Kho còn trống >= 1 gói thì xin gói mới.
"""
from __future__ import annotations

import argparse
import heapq
import random
import sys

BOARD_RX_BYTES = 256        # bộ đệm kênh mặc định của FluidNC (Channel.h: 256 - queued_bytes); cổng UART phụ chưa kiểm
PLANNER_BLOCKS = 15         # hàng đợi chuyển động đo 13/11/2026 (docs/02 F13)
LINE_BYTES = 20             # một dòng G-code nét ngắn, vd "G1 X123.45 Y67.89\n"
UART_BAUD = 115200          # ESP32-S3 <-> MKS (chưa chốt); 10 bit mỗi byte
RTT_S = 0.13                # trung vị đo qua Cloudflare 27/11/2026 (docs/07 mục 4)
SPIKE_S = 1.16              # lần vọt cao nhất đo được 27/11/2026
SPIKE_RATE = 0.04           # 1 / 25 lần gọi đo được bị vọt


class Net:
    def __init__(self, rtt, spike, rate, seed):
        self.rtt, self.spike, self.rate = rtt, spike, rate
        self.rng = random.Random(seed)

    def one_way(self):
        if self.rng.random() < self.rate:
            return self.spike / 2 + self.rng.uniform(0, self.spike / 2)
        return self.rtt / 2 * self.rng.uniform(0.85, 1.2)


def simulate(mode, n_lines, seg_s, net, chunk=1000, esp_lines=5000, prefill=2000):
    """Trả (tổng giây, số lần khựng, tổng giây khựng). Mô phỏng sự kiện rời rạc."""
    prefill = min(prefill, max(0, esp_lines - chunk))   # kho chỉ xin gói khi còn trống >= 1 gói: nạp trước không thể đầy hơn
    t = 0.0
    ev = []                                    # (thời điểm, thứ tự, loại, dữ liệu)
    seq = [0]

    def push(at, kind, data=None):
        seq[0] += 1
        heapq.heappush(ev, (at, seq[0], kind, data))

    rx_bytes = 0                               # byte đang nằm trong bộ đệm nhận của mạch
    rx_queue = []                              # các dòng trong bộ đệm nhận (chờ vào hàng đợi)
    planner = 0                                # số khối trong hàng đợi chuyển động
    running_until = None                       # khối đang chạy xong lúc nào
    done = 0
    stalls, stall_s, stall_from = 0, 0.0, None
    sent = 0                                   # dòng máy chủ đã gửi đi
    unacked = 0                                # byte chưa có ok (phía người gửi tới mạch)
    esp_store = 0                              # dòng đang có trong kho ESP
    esp_req_pending = False
    esp_running = False                        # ESP đã bắt đầu gửi xuống mạch chưa (sau khi nạp trước)
    started = False

    uart_line_s = LINE_BYTES * 10 / UART_BAUD

    def board_accept():
        nonlocal rx_bytes, planner, running_until, started
        while rx_queue and planner < PLANNER_BLOCKS:
            rx_queue.pop(0)
            rx_bytes -= LINE_BYTES
            planner += 1
            # ok đi về người gửi trực tiếp với mạch
            back = uart_line_s if mode == "C" else net.one_way()
            push(t + back, "ok")
        if running_until is None and planner > 0:
            running_until = t + seg_s
            started = True
            push(running_until, "block_done")

    def sender_try():
        nonlocal sent, unacked, esp_store, esp_req_pending, esp_running
        if mode == "A":
            if unacked == 0 and sent < n_lines:
                sent += 1
                unacked += LINE_BYTES
                push(t + net.one_way(), "arrive")
        elif mode == "B":
            while sent < n_lines and unacked + LINE_BYTES <= BOARD_RX_BYTES:
                sent += 1
                unacked += LINE_BYTES
                push(t + net.one_way(), "arrive")
        else:
            # ESP: nạp trước `prefill` dòng (hoặc hết bài nếu ngắn hơn) rồi mới bắt đầu gửi xuống mạch
            if not esp_running and (esp_store >= min(prefill, n_lines) or sent >= n_lines):
                esp_running = True
            # ESP: gửi dồn tại chỗ từ kho của nó
            while esp_running and esp_store > 0 and unacked + LINE_BYTES <= BOARD_RX_BYTES:
                esp_store -= 1
                unacked += LINE_BYTES
                push(t + uart_line_s, "arrive")
            # xin gói mới từ máy chủ khi kho còn chỗ
            room = esp_lines - esp_store
            if not esp_req_pending and sent < n_lines and room >= min(chunk, n_lines - sent):
                k = min(chunk, n_lines - sent)
                sent += k
                esp_req_pending = True
                push(t + net.one_way() * 2, "chunk", k)   # xin (một chiều) + gói về (một chiều)

    sender_try()
    while ev:
        t, _, kind, data = heapq.heappop(ev)
        if kind == "arrive":
            rx_queue.append(1)
            rx_bytes += LINE_BYTES
            board_accept()
        elif kind == "ok":
            unacked -= LINE_BYTES
            sender_try()
        elif kind == "chunk":
            esp_store += data
            esp_req_pending = False
            sender_try()
        elif kind == "block_done":
            planner -= 1
            done += 1
            running_until = None
            board_accept()
            if running_until is None and done < n_lines and started:
                if stall_from is None:
                    stall_from = t
                    stalls += 1
        # hàng đợi có lại khối sau khi khựng
        if stall_from is not None and running_until is not None:
            stall_s += t - stall_from
            stall_from = None
        if done >= n_lines:
            break
    return t, stalls, stall_s


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Mô phỏng gửi G-code qua mạng có trễ (docs/07 mục 13).")
    ap.add_argument("--lines", type=int, default=3000, help="số dòng G-code (mặc định 3000)")
    ap.add_argument("--seg", type=float, default=0.5, help="độ dài một đoạn nét, mm (mặc định 0,5: nét nhỏ, khó nhất)")
    ap.add_argument("--feed", type=float, default=8000, help="tốc độ vẽ, mm/phút (mặc định 8000)")
    ap.add_argument("--rtt", type=float, default=RTT_S, help="thời gian đi-về thường, giây")
    ap.add_argument("--spike", type=float, default=SPIKE_S, help="thời gian đi-về lúc vọt, giây")
    ap.add_argument("--spike-rate", type=float, default=SPIKE_RATE, help="tỉ lệ lần gửi bị vọt")
    ap.add_argument("--chunk", type=int, default=1000, help="số dòng mỗi gói máy chủ gửi cho ESP")
    ap.add_argument("--esp-lines", default="500,2000,5000", help="các cỡ kho ESP cần so, phân cách dấu phẩy")
    ap.add_argument("--prefill", type=int, default=2000, help="ESP nạp trước chừng này dòng rồi mới chạy (0 = chạy ngay)")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args(argv)

    seg_s = a.seg / (a.feed / 60.0)
    ideal = a.lines * seg_s
    print(f"{a.lines} dòng, đoạn {a.seg} mm ở {a.feed:g} mm/phút ({seg_s * 1000:.1f} ms/đoạn) → lý tưởng {ideal:.1f} s")
    print(f"Mạng: đi-về {a.rtt:g} s, vọt {a.spike:g} s với tỉ lệ {a.spike_rate:g}. MÔ HÌNH, không phải số đo.\n")
    print(f"{'Cách gửi':38} {'Tổng (s)':>9} {'Chậm x':>7} {'Khựng':>6} {'Giây khựng':>11}")
    rows = [("A  từng dòng chờ ok qua mạng", "A", {}), ("B  đếm ký tự qua mạng", "B", {})]
    for n in [int(x) for x in a.esp_lines.split(",") if x.strip()]:
        for pre in sorted({0, min(a.prefill, max(0, n - min(a.chunk, n)))}):
            rows.append((f"C  kho ESP {n} dòng, nạp trước {pre}", "C",
                         {"esp_lines": n, "chunk": min(a.chunk, n), "prefill": pre}))
    for name, mode, kw in rows:
        total, stalls, stall_s = simulate(mode, a.lines, seg_s, Net(a.rtt, a.spike, a.spike_rate, a.seed), **kw)
        print(f"{name:38} {total:9.1f} {total / ideal:7.2f} {stalls:6d} {stall_s:11.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
