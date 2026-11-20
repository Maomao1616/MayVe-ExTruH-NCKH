// views/drawing/presets.js — bộ thông số dựng sẵn cho tiền xử lý ảnh + kiểu nét (chỉ là dữ liệu).
// Khóa = id ô trong index.html; giá trị = chuỗi/boolean ghi thẳng vào ô (params.setValues).
// Ô không có trong preset giữ nguyên giá trị người dùng đang để. Chỉnh dần theo ảnh thật: sửa đúng file này
// (cách thử: docs/07_THU_NGHIEM.md). 🧪 Mới thử bằng ảnh mẫu, chưa in ra giấy.
const BASE = {                   // mặc định chung, từng preset ghi đè
    "image-auto-levels": true, "image-clahe": false, "image-denoise": false,
    "image-black-point": "0", "image-white-point": "255", "image-gamma": "1", "image-contrast": "1", "image-sharpen": "0",
    "style-levels": "5", "style-angle": "45", "style-spacing": "", "style-amplitude": "",
    "style-outline": false, "style-outline-detail": "medium", "style-xdog": false, "style-invert": false, "style-soft": true, "style-am-fill": false, "palette-mode": "mono"
};

// 14/11/2026 (chủ dự án): còn 4 preset — Chân dung (ảnh người thật), Ảnh 2D, Phong cảnh, Schematic. Bỏ Cận cảnh và Phác họa:
// chủ dự án tự chọn kiểu khi tiền xử lý không đặc thù.
export const PRESETS = {
    // 14/11/2026 (chủ dự án): Chân dung = ẢNH NGƯỜI THẬT: sóng biến thiên (tông da mượt), KHÔNG viền (viền bắt vệt bóng mềm
    // trên da thành nét cứng), mức đen 20 (tóc đen sâu), tương phản 1,3 (thử 1 / 1,3 / 1,6: 1,3 mặt tách nền, da còn tông;
    // 1,6 da trắng), góc 135°. Bộ số chủ dự án chỉnh trên ảnh cô gái, xem bản thảo.
    portrait: {                  // chân dung / ảnh người chụp thật
        ...BASE, "image-black-point": "20", "image-contrast": "1.3",
        "style-kind": "wave_am", "style-angle": "135", "style-am-fill": true
    },
    // 14/11/2026 giữ nguyên: thử ảnh chùa + hồ A4: sóng + CLAHE nhiều sắc độ trời nhất; thêm viền -> cây cối vụn; gạch chéo +
    // viền, tương phản 1,2 -> tiền cảnh đen kịt.
    // 18/11/2026 (chủ dự án): bỏ CLAHE, thêm tương phản 1,4 + mức đen 15, không viền. Ảnh bưu điện A5: CLAHE làm phẳng tông từng chỗ
    // nên không nhận ra vòm cổng; bản mới "đẹp phết" (xem xem trước, chưa in giấy). Ảnh chùa / trời mây từng hợp CLAHE: nếu mất sắc độ trời thì bật lại tay.
    landscape: {                 // phong cảnh, trời mây, nhà cửa, cảnh đêm: sóng biên độ cho tông mượt, tương phản cao
        ...BASE, "image-contrast": "1.4", "image-black-point": "15", "image-sharpen": "1.5",
        "style-kind": "wave_am", "style-angle": "30"
    },
    // 14/11/2026 (chủ dự án): ảnh 2D = gạch chéo + lớp viền FDoG (thử ảnh hoạt hình A4: đẹp nhất; trước: chỉ nét viền).
    // Khử nhiễu bớt vệt nén JPEG của ảnh chụp màn hình. Cận cảnh (xoắn ốc) bỏ: chủ dự án tự chọn xoắn ốc khi cần.
    flat2d: {                    // ảnh 2D: hình vẽ, hoạt hình, truyện tranh, sticker
        ...BASE, "image-denoise": true,
        "style-kind": "crosshatch", "style-levels": "5", "style-outline": true
    },
    // 19/11/2026 (chủ dự án): "Siêu chi tiết" = đan chéo BỎ hết lọc bớt râu (giữ mẩu 0,5 mm, dải đậm hẹp), 8 mức,
    // khoảng cách nét 0,9 × bút (0,45 cho bút 0,5), sửa sai 2 lượt, không đơn giản hoá / không bỏ nét ngắn.
    // Đo ảnh mèo A4 bút 0,5: 40,8 m / ~8,4 phút (kiểu thường 20,8 m / 3,4 phút). Bút khác: spacing = 0,9 × bút.
    detail: {
        ...BASE, "style-kind": "crosshatch_detail", "style-levels": "8", "style-spacing": "0.45",
        "style-refine": "2", "simplify-tolerance": "0", "min-path-length": "0"
    },
    schematic: {                 // schematic / bản vẽ kỹ thuật, ảnh scan nền xám: cắt nền xám, chỉ viền
        ...BASE, "image-black-point": "60", "image-white-point": "200",
        "style-kind": "outline", "style-outline-detail": "medium"
    }
};

export const presetValues = (name) => PRESETS[name] ?? null;
