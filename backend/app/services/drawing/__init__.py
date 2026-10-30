"""Tab Tạo bản vẽ: ảnh/SVG -> đường nét -> G-code. Không gọi máy.

Dây chuyền (mỗi bước một file, một hàm thuần):
  spec.py      khai báo tham số MỘT chỗ (mặc định, giới hạn) + kiểm tra đầu vào
  svg_in.py    nạp SVG (vpype) -> lớp đường nét (mm)
  optimize.py  tối ưu nét bằng vpype (nối, đơn giản hóa, bỏ nét ngắn, sắp xếp)
  layout.py    đặt đường nét vào khung vẽ trong tờ giấy: kích thước, lề, căn giữa, lật, đảo thứ tự
  gcode.py     đường nét (mm) -> dòng G-code + thống kê
  service.py   ghép layout + gcode, trả kết quả cho api/draw.py
  store.py     bộ nhớ tạm vài bản vẽ đã nạp (đổi tham số không phải nạp lại)
  registry.py  sổ đăng ký kiểu vector hóa (thêm kiểu mới = 1 file + 1 dòng đăng ký)
Giai đoạn sau thêm: loader ảnh, preprocess, vectorize/.
"""
from .errors import DrawError
from .service import make_gcode
from .spec import describe
from . import drafts, preview, raster_in, service, styles, tasks, tone
from .svg_in import import_svg

__all__ = ["DrawError", "make_gcode", "describe", "import_svg"]
