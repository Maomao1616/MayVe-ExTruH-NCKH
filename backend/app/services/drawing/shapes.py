"""Kiểu dữ liệu dùng chung. Tọa độ đường nét: (x, y) tính bằng mm, gốc ở góc trên trái, Y xuống."""
from __future__ import annotations

from dataclasses import dataclass, field

Point = tuple[float, float]
Stroke = list[Point]            # một nét liền = một lần hạ bút, >= 2 điểm


@dataclass
class Layer:
    """Một lớp (một bút). Mặc định chỉ có một lớp; nhiều lớp dùng cho tách màu/mức sáng."""
    id: str
    strokes: list[Stroke] = field(default_factory=list)


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float
