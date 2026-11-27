#!/usr/bin/env python3
r"""Đo thời gian từng bước + RAM đỉnh của dây chuyền ảnh -> nét -> G-code, để so laptop với MiniPC.

    cd backend && .venv\Scripts\python.exe ..\tools\do_thoi_gian.py
    cd backend && .venv\Scripts\python.exe ..\tools\do_thoi_gian.py --image ..\data\meo.jpg --paper a4
    cd backend && .venv\Scripts\python.exe ..\tools\do_thoi_gian.py --styles crosshatch,flow --label mini-pc

Không có --image thì dựng ảnh thử tổng hợp (dải chuyển + đốm tròn + vài khung) để mọi máy đo cùng một đầu vào.
In bảng ra màn hình và ghi 2 tệp vào export/ (không lên Git): do-thoi-gian-<máy>-<ngày>.md và .json.
Cùng một lệnh chạy trên laptop và trên MiniPC rồi gửi 2 tệp để so (docs/11 mục 9).

Đo cái gì: giây của từng bước (đọc ảnh / chỉnh tông / tạo nét / tối ưu nét), giây sinh G-code, số nét, chiều dài nét,
số dòng G-code, RAM đỉnh của CẢ tiến trình (gồm cả lúc nạp numpy / OpenCV nên có thêm dòng RAM nền để trừ).
Chạy trong tiến trình này; lúc dùng thật, bước ảnh -> nét chạy ở tiến trình con (isolated.py) nên có thêm thời gian
khởi động, đo riêng ở dòng "khởi động tiến trình con".
"""
from __future__ import annotations

import argparse
import ctypes
import importlib.metadata as md
import json
import os
import platform
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

KINDS = ("crosshatch", "flow", "wave_am", "spiral", "outline")      # 5 kiểu hiện trên giao diện (spec.UI_STYLES)
PACKAGES = ("numpy", "opencv-python-headless", "scikit-image", "scipy", "pillow", "vpype", "shapely", "pymupdf")

# Số máy = MACHINE trong frontend/js/core/config.js (X 285 · Y 318 · Z 5 · rapid 8000) và ô G-code mặc định
# (Z nhấc 3 / Z hạ 0 / hạ bút 2000). Chỉ dùng để sinh G-code trong lúc đo; không gửi gì xuống máy.
MACHINE = {"work_w": 285.0, "work_h": 318.0, "z_travel": 5.0, "rapid_feed": 8000.0}
GCODE = {"pen_up_z": 3.0, "pen_down_z": 0.0, "pen_down_feed": 2000.0}


# ------------------------------------------------------------------ RAM / máy
class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


def memory_mb() -> tuple[float | None, float | None]:
    """(RAM đỉnh, RAM hiện tại) của tiến trình này, MB. None nếu hệ điều hành không cho đọc."""
    if os.name == "nt":
        try:
            kernel = ctypes.windll.kernel32
            kernel.GetCurrentProcess.restype = ctypes.c_void_p        # trả về con trỏ thật, không phải int -1
            pmc = _PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(_PROCESS_MEMORY_COUNTERS)
            try:
                func = ctypes.windll.psapi.GetProcessMemoryInfo     # Win7+
            except AttributeError:
                func = kernel.K32GetProcessMemoryInfo               # Win10+ cũng có ở kernel32
            func.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
            func.restype = ctypes.c_int
            if func(kernel.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
                return pmc.PeakWorkingSetSize / 2 ** 20, pmc.WorkingSetSize / 2 ** 20
        except (OSError, AttributeError):
            return None, None
        return None, None
    try:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak = peak / 1024 if sys.platform != "darwin" else peak / 2 ** 20   # Linux: KB; macOS: byte
        rss = None
        statm = Path("/proc/self/statm")
        if statm.is_file():
            rss = int(statm.read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 2 ** 20
        return peak, rss
    except (ImportError, OSError, ValueError):
        return None, None


def total_ram_gb() -> float | None:
    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        ms = MEMORYSTATUSEX()
        ms.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
            return round(ms.ullTotalPhys / 2 ** 30, 1)
        return None
    try:
        return round(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 2 ** 30, 1)
    except (ValueError, OSError, AttributeError):
        return None


def cpu_name() -> str:
    if os.name == "nt":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            with key:
                return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        except OSError:
            return platform.processor() or "?"
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(errors="replace").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "?"


def machine_info(label: str) -> dict:
    versions = {}
    for pkg in PACKAGES:
        try:
            versions[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            versions[pkg] = "-"
    return {"label": label, "host": socket.gethostname(), "os": platform.platform(),
            "cpu": cpu_name(), "cores_logical": os.cpu_count(), "ram_gb": total_ram_gb(),
            "python": sys.version.split()[0], "packages": versions}


# ------------------------------------------------------------------ đầu vào
def synthetic_image(w: int = 1000, h: int = 1400) -> bytes:
    """Ảnh thử tổng hợp: dải chuyển ngang + 3 đốm tròn mềm + vài khung (để kiểu Viền có đường mà bám)."""
    import cv2
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    img = 60.0 + 170.0 * (xx / (w - 1))
    for cx, cy, r in ((0.28, 0.25, 0.16), (0.70, 0.45, 0.20), (0.45, 0.78, 0.14)):
        d = np.hypot(xx - cx * w, yy - cy * h) / (r * min(w, h))
        img = img * (1.0 - 0.75 * np.clip(1.0 - d, 0.0, 1.0) ** 1.5)
    gray = np.clip(img, 0, 255).astype(np.uint8)
    for x0, y0, x1, y1 in ((80, 120, 380, 300), (620, 900, 930, 1150), (150, 1050, 450, 1300)):
        local = int(gray[max(0, y0 - 8):y0 + 8, x0:x0 + 8].mean() * 0.35)
        cv2.rectangle(gray, (x0, y0), (x1, y1), local, 6)
    ok, buf = cv2.imencode(".png", cv2.applyColorMap(gray, cv2.COLORMAP_BONE))
    if not ok:
        raise RuntimeError("không dựng được ảnh thử")
    return buf.tobytes()


# ------------------------------------------------------------------ đo
def child_startup_s() -> float | None:
    """Giây để một tiến trình Python mới nạp xong dây chuyền (giống lúc app mở tiến trình con)."""
    t = time.perf_counter()
    try:
        subprocess.run([sys.executable, "-X", "utf8", "-c", "import app.services.drawing.raster"],
                       cwd=str(ROOT / "backend"), capture_output=True, check=True, timeout=300)
    except (OSError, subprocess.SubprocessError):
        return None
    return round(time.perf_counter() - t, 2)


def warm_up() -> None:
    """Nạp trước các thư viện được import muộn (vpype) — nếu không, kiểu ĐẦU BẢNG gánh thêm ~0,7 s vào cột "tối ưu"."""
    import vpype, vpype_cli            # noqa: F401  (optimize.py import muộn, lần đầu rất chậm)
    from app.services.drawing import optimize   # noqa: F401


def run(image: bytes, name: str, kinds: list[str], paper: str, pen: float, refine: int) -> list[dict]:
    from app.services.drawing import raster, service
    warm_up()
    base = memory_mb()[0] or 0.0
    opts = {"raster": {"pen_width_mm": pen}, "style": {"refine_passes": refine},
            "optimize": {}, "palette": {}, "layout": {"paper": paper}}
    rows = []
    for kind in kinds:
        row: dict = {"kind": kind}
        try:
            opts["style"] = {"kind": kind, "refine_passes": refine, "outline_overlay": False}
            t = time.perf_counter()
            layers, _frame, info, warnings = raster.build_raster(image, name, opts)
            create_s = time.perf_counter() - t
            t = time.perf_counter()
            result = service.make_gcode(layers, MACHINE, {"paper": paper}, GCODE)
            gcode_s = time.perf_counter() - t
            after = info["optimize"]["after"]
            row.update({
                "seconds": round(create_s, 3),
                "gcode_seconds": round(gcode_s, 3),
                "steps": info.get("timings", {}),
                "strokes": after["strokes"], "length_mm": after["draw_mm"],
                "gcode_lines": sum(len(f["gcode"].splitlines()) for f in result["files"]),
                "est_draw_minutes": round(sum(f["stats"]["est_seconds"] for f in result["files"]) / 60, 1),
                "warnings": [w.get("code") for w in warnings],
                "ram_peak_mb": round((memory_mb()[0] or 0.0) - base, 1),
            })
        except Exception as exc:                                    # ảnh thử không hợp kiểu (vd Viền không ra nét)
            row.update({"error": f"{type(exc).__name__}: {exc}"[:200]})
        row["rss_mb"] = round(memory_mb()[1] or 0.0, 1)
        rows.append(row)
        print(f"  {kind:12s} {_cell(row)}")
    return rows


def _cell(row: dict) -> str:
    if "error" in row:
        return f"lỗi: {row['error']}"
    st = row["steps"]
    return (f"{row['seconds']:6.2f} s (đọc {st.get('read', 0):5.2f} · tông {st.get('tone', 0):5.2f} · "
            f"tô {st.get('style', 0):6.2f} · tối ưu {st.get('optimize', 0):5.2f}) · G-code {row['gcode_seconds']:5.2f} s "
            f"· {row['strokes']:5d} nét · {row['length_mm'] / 1000:5.1f} m · {row['gcode_lines']:6d} dòng "
            f"· ~{row['est_draw_minutes']:5.1f} ph · RAM đỉnh +{row['ram_peak_mb']:6.1f} MB")


# ------------------------------------------------------------------ báo cáo
def write_report(data: dict, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    host = "".join(c for c in data["machine"]["host"] if c.isalnum() or c in "-_") or "may"
    stem = f"do-thoi-gian-{host}-{stamp}"
    mpath, jpath = out_dir / f"{stem}.md", out_dir / f"{stem}.json"
    jpath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    m, a = data["machine"], data["run"]
    startup = f"{a['child_startup_s']} s" if a["child_startup_s"] is not None else "không đo"
    lines = [f"# Đo thời gian tạo nét — {a['label']}", "",
             f"Ngày {data['date']} · ảnh `{a['image']}` ({a['image_px']}) · khổ **{a['paper'].upper()}** · "
             f"bút {a['pen_mm']} mm · sửa sai {a['refine']} lượt · {a['cores']} luồng", "",
             "| Máy | |", "|---|---|",
             f"| Tên | {a['label']} ({m['host']}) |", f"| CPU | {m['cpu']} |",
             f"| Nhân logic | {m['cores_logical']} |", f"| RAM | {m['ram_gb']} GB |",
             f"| Hệ điều hành | {m['os']} |", f"| Python | {m['python']} |",
             f"| Gói | {', '.join(f'{k} {v}' for k, v in m['packages'].items())} |", "",
             f"RAM nền (đã nạp numpy / OpenCV): **{a['baseline_ram_mb']} MB**. "
             f"Khởi động tiến trình con: **{startup}**. "
             "Thông số lúc sinh G-code: máy 285×318 mm, Z 5, rapid 8000; Z nhấc 3 / hạ 0 / hạ bút 2000 "
             "(= `frontend/js/core/config.js`).", "",
             "| Kiểu | Tạo nét (s) | Đọc | Tông | Tô | Tối ưu | G-code (s) | Số nét | Dài (m) | Dòng G-code "
             "| Vẽ ước tính (ph) | RAM đỉnh thêm (MB) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in data["results"]:
        if "error" in row:
            lines.append(f"| {row['kind']} | lỗi | | | | | | | | | | {row['error']} |")
            continue
        st = row["steps"]
        lines.append(f"| {row['kind']} | {row['seconds']:.2f} | {st.get('read', 0):.2f} | {st.get('tone', 0):.2f} | "
                     f"{st.get('style', 0):.2f} | {st.get('optimize', 0):.2f} | {row['gcode_seconds']:.2f} | "
                     f"{row['strokes']} | {row['length_mm'] / 1000:.1f} | {row['gcode_lines']} | "
                     f"{row['est_draw_minutes']:.1f} | {row['ram_peak_mb']:.1f} |")
    lines += ["", "Cách đọc: **Tạo nét** = tổng thời gian từ lúc bấm nút tới lúc có nét (đọc + tông + tô + tối ưu); "
              "cột **Tô** thường chiếm gần hết. RAM đỉnh là mức tăng so với RAM nền, đo cho cả tiến trình nên là "
              "cận trên. **Vẽ ước tính** là thời gian máy vẽ (có gia tốc), không phải thời gian tính. "
              "So hai máy: chạy cùng lệnh, cùng ảnh; so cột **Tạo nét** và **RAM đỉnh thêm**."]
    mpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return mpath, jpath


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Đo thời gian + RAM đỉnh của dây chuyền ảnh -> nét -> G-code.")
    ap.add_argument("--image", help="ảnh cần đo (mặc định: ảnh thử tổng hợp 1000x1400)")
    ap.add_argument("--styles", default=",".join(KINDS),
                    help=f"các kiểu cần đo, cách nhau dấu phẩy (mặc định {','.join(KINDS)})")
    ap.add_argument("--paper", default="a5", help="khổ giấy: a4 / a5 / a6 / letter (mặc định a5)")
    ap.add_argument("--pen", type=float, default=0.5, help="bề rộng nét trên giấy, mm (mặc định 0,5)")
    ap.add_argument("--refine", type=int, default=1, help="số lượt sửa sai tông (mặc định 1; 0 = tắt)")
    ap.add_argument("--label", default="", help="tên máy ghi vào báo cáo (vd 'laptop' / 'mini-pc')")
    ap.add_argument("--out-dir", default=str(ROOT / "export"), help="thư mục ghi báo cáo (mặc định export/)")
    ap.add_argument("--no-startup", action="store_true", help="bỏ phép đo khởi động tiến trình con")
    args = ap.parse_args()

    from app.services.drawing import spec
    if args.paper not in spec.PAPERS:
        print(f"Khổ '{args.paper}' không có. Chọn: {', '.join(spec.PAPERS)}", file=sys.stderr)
        return 2
    kinds = [k.strip() for k in args.styles.split(",") if k.strip()]
    bad = [k for k in kinds if k not in spec.STYLES]
    if bad:
        print(f"Kiểu không có: {', '.join(bad)}. Chọn: {', '.join(spec.STYLES)}", file=sys.stderr)
        return 2

    label = args.label or socket.gethostname()
    image_path = Path(args.image).expanduser() if args.image else None
    if image_path and not image_path.is_file():
        print(f"Không thấy ảnh {image_path}", file=sys.stderr)
        return 2
    image = image_path.read_bytes() if image_path else synthetic_image()
    name = image_path.name if image_path else "anh-thu-tong-hop.png"
    import cv2                                                    # chỉ để đọc cỡ ảnh ghi vào báo cáo
    probe = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_GRAYSCALE)
    px = f"{probe.shape[1]}x{probe.shape[0]} px"

    print(f"Đo trên {label}: {name} ({px}), khổ {args.paper.upper()}, bút {args.pen} mm, {len(kinds)} kiểu")
    info = machine_info(label)
    print(f"  {info['cpu']} · {info['cores_logical']} luồng · {info['ram_gb']} GB RAM · Python {info['python']}")
    baseline = round(memory_mb()[1] or 0.0, 1)
    startup = None if args.no_startup else child_startup_s()
    startup_txt = f"{startup} s" if startup is not None else "không đo"
    print(f"  RAM nền {baseline} MB · khởi động tiến trình con {startup_txt}")
    results = run(image, name, kinds, args.paper, args.pen, args.refine)
    data = {"date": datetime.now().isoformat(timespec="seconds"), "machine": info,
            "run": {"label": label, "image": name, "image_px": px, "paper": args.paper, "pen_mm": args.pen,
                    "refine": args.refine, "cores": os.cpu_count(), "baseline_ram_mb": baseline,
                    "child_startup_s": startup},
            "results": results}
    mpath, jpath = write_report(data, Path(args.out_dir))
    for p in (mpath, jpath):
        print(f"Đã ghi {p.relative_to(ROOT) if p.is_relative_to(ROOT) else p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
