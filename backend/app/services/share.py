"""Địa chỉ để mở giao diện từ máy khác, kèm mã QR (docs/13). Địa chỉ do launcher đặt qua biến môi trường:
EXTRUXY_PUBLIC_URL (tên miền Cloudflare, dòng `url=` của data/mang.txt) và EXTRUXY_LAN_URL (IP trong mạng nhà)."""
from __future__ import annotations

import os

MAX_URL_LEN = 200                       # QR phiên bản thấp, quét dễ; địa chỉ dài hơn thì bỏ
SOURCES = (("public", "EXTRUXY_PUBLIC_URL"), ("lan", "EXTRUXY_LAN_URL"))


def qr_rows(url: str) -> list[str]:
    """Ma trận QR dạng các chuỗi '0' / '1' ('1' = ô đen). Dùng bộ mã hóa QR có sẵn của OpenCV (không thêm thư viện)."""
    import cv2
    try:
        img = cv2.QRCodeEncoder.create().encode(url)
    except Exception:
        return []
    return ["".join("1" if v < 128 else "0" for v in row) for row in img]


def share_items() -> list[dict]:
    items = []
    for kind, env in SOURCES:
        url = (os.environ.get(env) or "").strip()
        if url.startswith(("http://", "https://")) and len(url) <= MAX_URL_LEN:
            qr = qr_rows(url)
            if qr:  # bỏ mục có qr rỗng
                items.append({"kind": kind, "url": url, "qr": qr})
    return items
