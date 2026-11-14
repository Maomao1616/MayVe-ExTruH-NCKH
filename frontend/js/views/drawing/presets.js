// views/drawing/presets.js — bộ thông số dựng sẵn cho tiền xử lý ảnh + kiểu nét (chỉ là dữ liệu).
// Khóa = id ô trong index.html; giá trị = chuỗi/boolean ghi thẳng vào ô (params.setValues).
// Ô không có trong preset giữ nguyên giá trị người dùng đang để. Chỉnh dần theo ảnh thật: sửa đúng file này
// (cách thử: docs/07_THU_NGHIEM.md). 🧪 Mới thử bằng ảnh mẫu, chưa in ra giấy.
const BASE = {                   // mặc định chung, từng preset ghi đè
    "image-auto-levels": true, "image-clahe": false, "image-denoise": false,
    "image-black-point": "0", "image-white-point": "255", "image-gamma": "1", "image-contrast": "1",
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
    landscape: {                 // phong cảnh, trời mây, nhà cửa, cảnh đêm: tăng chi tiết cục bộ, sóng biên độ cho tông mượt
        ...BASE, "image-clahe": true,
        "style-kind": "wave_am", "style-angle": "30"
    },
    // 14/11/2026 (chủ dự án): ảnh 2D = gạch chéo + lớp viền FDoG (thử ảnh hoạt hình A4: đẹp nhất; trước: chỉ nét viền).
    // Khử nhiễu bớt vệt nén JPEG của ảnh chụp màn hình. Cận cảnh (xoắn ốc) bỏ: chủ dự án tự chọn xoắn ốc khi cần.
    flat2d: {                    // ảnh 2D: hình vẽ, hoạt hình, truyện tranh, sticker
        ...BASE, "image-denoise": true,
        "style-kind": "crosshatch", "style-levels": "5", "style-outline": true
    },
    schematic: {                 // schematic / bản vẽ kỹ thuật, ảnh scan nền xám: cắt nền xám, chỉ viền
        ...BASE, "image-black-point": "60", "image-white-point": "200",
        "style-kind": "outline", "style-outline-detail": "medium"
    }
};

export const presetValues = (name) => PRESETS[name] ?? null;
