"""Tab Tạo bản vẽ: ảnh/SVG -> đường nét -> G-code. Lõi thuần Python, không gọi máy.

Dây chuyền (mỗi bước một file, một hàm thuần):
  spec.py      khai báo tham số MỘT chỗ (mặc định, giới hạn) + kiểm tra đầu vào
  layout.py    đặt đường nét vào khung vẽ (mm): kích thước, lề, căn giữa, lật, đảo thứ tự
  gcode.py     đường nét (mm) -> dòng G-code + thống kê
  service.py   ghép các bước, trả kết quả cho routes_draw.py
  registry.py  sổ đăng ký kiểu vector hóa (thêm kiểu mới = 1 file + 1 dòng đăng ký)
Giai đoạn sau thêm: loader, preprocess, vectorize/, optimize.
"""
from .errors import DrawError
from .service import make_gcode
from .spec import describe

__all__ = ["DrawError", "make_gcode", "describe"]
