"""Mô hình gửi G-code qua mạng có trễ (tools/mo_phong_gui_lenh.py): giữ kết luận chọn kho lệnh trên ESP32-S3."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location("mo_phong_gui_lenh", ROOT / "tools" / "mo_phong_gui_lenh.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SEG_S = 0.5 / (8000 / 60)        # nét 0,5 mm ở 8000 mm/phút: trường hợp khó nhất


def test_line_by_line_over_internet_is_far_slower():
    m = load()
    ideal = 1000 * SEG_S
    total, stalls, _ = m.simulate("A", 1000, SEG_S, m.Net(0.13, 1.16, 0.04, seed=1))
    assert total > 20 * ideal and stalls > 900


def test_esp_store_with_defaults_does_not_stall_even_on_bad_network():
    m = load()
    for seed in range(1, 6):
        net = m.Net(0.3, 3.0, 0.08, seed=seed)                 # 4G giật: vọt 3 s, 8 % lần gửi
        total, stalls, _ = m.simulate("C", 3000, SEG_S, net)   # mặc định: kho 5000, gói 1000, nạp trước 2000
        assert stalls == 0, seed
        assert total < 1.6 * 3000 * SEG_S


def test_prefill_never_exceeds_what_the_store_can_hold():
    m = load()
    total, _, _ = m.simulate("C", 3000, SEG_S, m.Net(0.13, 1.16, 0.04, seed=1), chunk=200, esp_lines=500, prefill=500)
    assert total > 3000 * SEG_S                                 # vẫn chạy hết bài, không kẹt ở bước nạp trước


def test_cli_prints_table():
    m = load()
    assert m.main(["--lines", "300", "--esp-lines", "500"]) == 0
