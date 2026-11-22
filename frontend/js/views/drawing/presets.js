// views/drawing/presets.js — bộ thông số dựng sẵn cho tiền xử lý ảnh + kiểu nét (chỉ là dữ liệu).
// Khóa = id ô trong index.html; giá trị = chuỗi/boolean ghi thẳng vào ô (params.setValues).
// Ô không có trong preset giữ nguyên giá trị người dùng đang để. Chỉnh dần theo ảnh thật: sửa đúng file này
// (cách thử: docs/07_THU_NGHIEM.md). 🧪 Mới thử bằng ảnh mẫu, chưa in ra giấy.
const BASE = {                   // mặc định chung, từng preset ghi đè
    "image-auto-levels": true, "image-clahe": false, "image-denoise": false,
    "image-black-point": "0", "image-white-point": "255", "image-gamma": "1", "image-contrast": "1", "image-sharpen": "0",
    "style-levels": "5", "style-angle": "45", "style-spacing": "", "style-amplitude": "",
    "style-outline": false, "style-outline-detail": "medium", "style-xdog": false, "style-invert": false, "style-soft": true, "style-am-fill": false, "style-unlimited": false, "palette-mode": "mono"
};

// 14/11/2026 (chủ dự án): còn 4 preset — Chân dung (ảnh người thật), Ảnh 2D, Phong cảnh, Schematic. Bỏ Cận cảnh và Phác họa:
// chủ dự án tự chọn kiểu khi tiền xử lý không đặc thù.
export const PRESETS = {
    // 14/11/2026 (chủ dự án): Chân dung = ẢNH NGƯỜI THẬT: sóng biến thiên (tông da mượt), KHÔNG viền (viền bắt vệt bóng mềm
    // trên da thành nét cứng), mức đen 20 (tóc đen sâu), tương phản 1,3 (thử 1 / 1,3 / 1,6: 1,3 mặt tách nền, da còn tông;
    // 1,6 da trắng), góc 135°. Bộ số chủ dự án chỉnh trên ảnh cô gái, xem bản thảo.
    portrait: {                  // chân dung / ảnh người chụp thật
        // 22/11/2026 (chủ dự án, ảnh cô gái nền rèm): mắt / mũi / môi chỉ rõ khi tương phản 1,5 + cân bằng sáng cục bộ + làm nét 1,5
        // (xem trước: 1,3 không có làm nét thì mặt chìm). KHÔNG bật Chất lượng tối đa: đan mảng, kém mịn hơn.
        ...BASE, "image-black-point": "20", "image-contrast": "1.5", "image-clahe": true, "image-sharpen": "1.5",
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
        // 22/11/2026 (chủ dự án): ảnh nhân vật 2D tối + sáng lẫn, mắt nhỏ chỉ hiện khi tương phản cao. Thử trên ảnh nhân vật toàn thân:
        // tương phản 1,5 + cân bằng sáng cục bộ + làm nét 1,5 ra mắt, lông mày rõ nhất (chỉ tương phản 1,3 thì mắt chìm vào da). Mức đen 40 / trắng 250: cắt nền xám.
        "image-black-point": "40", "image-white-point": "250", "image-contrast": "1.5", "image-clahe": true, "image-sharpen": "1.5",
        "style-kind": "crosshatch", "style-levels": "5", "style-outline": true
    },
    // 19/11/2026 (chủ dự án), đổi 22/11/2026: "Siêu chi tiết" = Gạch chéo + ô "Bỏ giới hạn" (8 mức, bỏ lọc râu, khoảng cách
    // nét 1,4 × bút, sửa sai >= 2 lượt; backend styles.unlimited_style). Ô Bỏ giới hạn dùng được với Gạch chéo, Theo dáng, Sóng.
    detail: {
        ...BASE, "style-kind": "crosshatch", "style-unlimited": true, "style-refine": "2"
    },
    schematic: {                 // schematic / bản vẽ kỹ thuật, ảnh scan nền xám: cắt nền xám, chỉ viền
        ...BASE, "image-black-point": "60", "image-white-point": "200",
        "style-kind": "outline", "style-outline-detail": "high", "style-xdog": true      // 22/11/2026: FDoG + nhiều chi tiết giữ được nét gạch mảnh, vạch chia trên ảnh scan nhiễu (Canny làm đứt / mất)
    }
};

export const presetValues = (name) => PRESETS[name] ?? null;
