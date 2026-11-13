// views/drawing/presets.js — bộ thông số dựng sẵn cho tiền xử lý ảnh + kiểu nét (chỉ là dữ liệu).
// Khóa = id ô trong index.html; giá trị = chuỗi/boolean ghi thẳng vào ô (params.setValues).
// Ô không có trong preset giữ nguyên giá trị người dùng đang để. Chỉnh dần theo ảnh thật: sửa đúng file này
// (cách thử: docs/07_THU_NGHIEM.md). 🧪 Mới thử bằng ảnh mẫu, chưa in ra giấy.
const BASE = {                   // mặc định chung, từng preset ghi đè
    "image-auto-levels": true, "image-clahe": false, "image-denoise": false,
    "image-black-point": "0", "image-white-point": "255", "image-gamma": "1",
    "style-levels": "5", "style-angle": "45", "style-spacing": "", "style-amplitude": "",
    "style-outline": false, "style-outline-detail": "medium", "style-xdog": false, "style-invert": false, "style-soft": true, "palette-mode": "mono"
};

// 12/11/2026 (in thật Sakura / UB-155 trên Ivory, 8000 mm/min): viền tắt ở mọi preset tô (thêm nhấc bút, ít khi cần);
// Chân dung đổi sang đan chéo (ra giống ảnh thật nhất), Phong cảnh sang sóng biên độ (chuyển tông mượt nhất).
export const PRESETS = {
    // 13/11/2026: Chân dung = đan chéo + theo dáng (in thật: đan chéo thuần cứng, mắt / mũi không tách khỏi nền), gamma 1
    // vì đường cong tông (backend styles.TONE_CURVES) đã bù vùng trung bình trông nhạt (trước phải hạ gamma bằng tay).
    portrait: {                  // chân dung / ảnh tự chụp: đan chéo + theo dáng ở viền, mịn, nhiều mức
        ...BASE, "image-denoise": true, "image-gamma": "1",
        "style-kind": "crosshatch_flow", "style-levels": "5"
    },
    landscape: {                 // phong cảnh, trời mây, nhà cửa, cảnh đêm: tăng chi tiết cục bộ, sóng biên độ cho tông mượt
        ...BASE, "image-clahe": true,
        "style-kind": "wave_am", "style-angle": "30"
    },
    // 13/11/2026: gamma 1,25 -> 1: đường cong tông xoắn ốc (xoắn ốc trông đậm nhanh hơn độ phủ) đã làm nhạt vùng trung bình
    closeup: {                   // cận cảnh: đồ ăn, cốc, đồ vật: xoắn ốc mềm
        ...BASE, "image-gamma": "1",
        "style-kind": "spiral", "style-levels": "4"
    },
    // 13/11/2026: ảnh chụp chỉ vẽ nét viền, ranh giới mảng bằng XDoG (rõ mắt / mũi / miệng hơn Canny, kể cả ảnh tối)
    sketch: {                    // phác họa ảnh chụp: chỉ nét viền, XDoG, khử nhiễu (bớt lấm tấm ở vùng tối)
        ...BASE, "image-denoise": true,
        "style-kind": "outline", "style-outline-detail": "medium", "style-xdog": true
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
