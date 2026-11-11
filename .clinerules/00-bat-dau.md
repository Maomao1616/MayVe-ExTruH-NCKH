# 00 — Bắt đầu (đọc trước mọi việc)

Dự án **VMU PlotterPen (ExtruXY)**: phần mềm điều khiển máy vẽ bút CoreXY. Mạch MKS DLC32, firmware FluidNC 4.1.1 (không sửa). Backend Python 3.12 / FastAPI. Frontend JS thuần (không framework, không bước build). Chủ dự án là sinh viên điện tử, **không phải lập trình viên**.

## Việc đầu tiên mỗi phiên
1. Đọc `docs/AI_START.md` (~2 500 token): nguồn chi tiết của mọi luật. Các tệp trong `.clinerules/` và `CLAUDE.md` chỉ là bản rút gọn; mâu thuẫn thì `AI_START.md` và **mã** thắng.
2. Đọc `docs/11_VIEC_CAN_LAM.md`: cái gì xong, cái gì chưa kiểm chứng, việc tiếp.
3. Tìm tệp cần sửa bằng `docs/AI_CODEMAP.md`. **Không quét cả kho** (~380 000 token); mở đúng tệp.

## Tài liệu nào mở khi nào
| Việc | Tài liệu |
|---|---|
| Đổi hành vi đã chốt | `docs/09_QUYET_DINH_THIET_KE.md` **trước** |
| Tab Điều khiển, chạy G-code, dừng an toàn | `docs/04_TAB_DIEU_KHIEN.md` |
| Tab Tạo bản vẽ, hợp đồng API | `docs/05_TAB_TAO_BAN_VE.md` |
| Thuật toán ảnh → nét | `docs/06_THUAT_TOAN_XU_LY_ANH.md` |
| Phần cứng, firmware | `docs/02_PHAN_CUNG_MAY.md` |
| Cấu trúc thư mục, tầng, quy tắc phụ thuộc | `docs/03_CAU_TRUC_PHAN_MEM.md` |
| Thử trên giấy | `docs/07_THU_NGHIEM.md` |
| Đóng gói, phân quyền, mạng, MiniPC | `docs/08_TRIEN_KHAI.md` |
