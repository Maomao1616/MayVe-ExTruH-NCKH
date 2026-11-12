// views/drawing/presets.js — bộ thông số dựng sẵn cho tiền xử lý ảnh + kiểu nét (chỉ là dữ liệu).
// Khóa = id ô trong index.html; giá trị = chuỗi/boolean ghi thẳng vào ô (params.setValues).
// Ô không có trong preset giữ nguyên giá trị người dùng đang để. Chỉnh dần theo ảnh thật: sửa đúng file này
// (cách thử: docs/07_THU_NGHIEM.md). 🧪 Mới thử bằng ảnh mẫu, chưa in ra giấy.
const BASE = {                   // mặc định chung, từng preset ghi đè
    "image-auto-levels": true, "image-clahe": false, "image-denoise": false,
    "image-black-point": "0", "image-white-point": "255", "image-gamma": "1",
    "style-levels": "5", "style-angle": "45", "style-spacing": "", "style-amplitude": "",
    "style-outline": false, "style-outline-detail": "medium", "style-invert": false, "style-soft": true, "palette-mode": "mono"
};

// 12/11/2026 (in thật Sakura / UB-155 trên Ivory, 8000 mm/min): viền tắt ở mọi preset tô (thêm nhấc bút, ít khi cần);
// Chân dung đổi sang đan chéo (ra giống ảnh thật nhất), Phong cảnh sang sóng biên độ (chuyển tông mượt nhất).
export const PRESETS = {
    portrait: {                  // chân dung / ảnh tự chụp: đan chéo, mịn, nhiều mức
        ...BASE, "image-denoise": true, "image-gamma": "1.15",
        "style-kind": "crosshatch", "style-levels": "5"
    },
    landscape: {                 // phong cảnh, trời mây, nhà cửa, cảnh đêm: tăng chi tiết cục bộ, sóng biên độ cho tông mượt
        ...BASE, "image-clahe": true,
        "style-kind": "wave_am", "style-angle": "30"
    },
    closeup: {                   // cận cảnh: đồ ăn, cốc, đồ vật: xoắn ốc mềm
        ...BASE, "image-gamma": "1.25",
        "style-kind": "spiral", "style-levels": "4"
    },
    flat2d: {                    // ảnh 2D: hình vẽ, sticker, hoạt hình, truyện tranh (kể cả dán lên ảnh chụp): chỉ viền
        ...BASE,
        "style-kind": "outline", "style-outline-detail": "medium"
    },
    schematic: {                 // schematic / bản vẽ kỹ thuật, ảnh scan nền xám: cắt nền xám, chỉ viền
        ...BASE, "image-black-point": "60", "image-white-point": "200",
        "style-kind": "outline", "style-outline-detail": "medium"
    }
};

export const presetValues = (name) => PRESETS[name] ?? null;
