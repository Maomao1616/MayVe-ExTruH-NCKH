# 04 — Giao tiếp với chủ dự án

- **Tiếng Việt, lời thường trước, kỹ thuật sau.** Thư viện hoặc cơ chế mới phải giải thích bằng ví dụ đời thường.
- Ngắn, thẳng, dùng **bảng** khi so sánh. Chỉ đưa đoạn thay đổi, không dán lại cả tệp.
- Báo kèm sau mỗi việc: lỗi / điểm tối ưu tìm thấy trong lúc làm, tiến độ, và những bài thử còn phải làm.
- Khi đề xuất đổi thuật toán hoặc thông số: nêu **số trước / sau**; nói rõ cái gì đã đo, cái gì chỉ suy luận.
- Chủ dự án thử trên giấy rồi gửi ảnh và số; AI sửa mã và tài liệu theo đó. Đừng suy diễn khi thiếu dữ kiện: hỏi một câu ngắn.
- Tài liệu `docs/01–11` viết cho người không học code: giữ văn phong (lời thường, khối rõ, từ nhỏ đến lớn, bảng). Tệp chỉ cho AI đặt tiền tố `AI_` và ghi "FOR AI" ở dòng đầu.

## Ngữ cảnh sản phẩm
- Mục tiêu: sản phẩm máy vẽ tích hợp IoT chạy thật; tối ưu tối đa cho sản phẩm, báo cáo đề tài để sau.
- Demo **không phụ thuộc Internet** (máy tự phát Wi-Fi). Mọi tính năng phải chạy được offline.
- Ưu tiên: **vẽ ra đẹp** hơn là nhanh; thời gian xử lý không quan trọng. Tốc độ chỉ cần tối ưu, không đổi lấy nét xấu.
- Bút / giấy hiện tại (11/11/2026): Sakura 0,4 và Uniball 150 trên giấy Ivory 250 g/m²; ô "Bút vẽ" chọn theo tên bút và ghi thẳng nét đo trên giấy (đo 12/11/2026: UB-155 0,38, UM-100 0,40, Sakura 0,50; `LINE_WIDTH_RATIO` = 1,0). Chữ: bút bi 0,5, Word cỡ 14–16.
- Máy thật đang chạy: vẽ 8000 mm/phút (10000 ở đoạn dài), gia tốc 3000, junction 0,05, Z3, chờ 0,02, SpreadCycle.

## Xuất mã gọn cho AI khác (tiết kiệm token)
`python tools/export_context.py --list` liệt kê các gói; ví dụ `python tools/export_context.py docs` (~12 000 token), `draw-backend --budget 35000`, `--files <tệp>`. Kết quả ở `export/` (gitignored). Đừng gửi cả `index.html` (~28 000 token): dùng `--html panel-<tab>`.
