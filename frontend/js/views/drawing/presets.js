// views/drawing/presets.js — bộ thông số dựng sẵn cho tiền xử lý ảnh + kiểu nét (chỉ là dữ liệu).
// Khóa = id ô trong index.html; giá trị = chuỗi/boolean ghi thẳng vào ô (params.setValues).
// Ô không có trong preset giữ nguyên giá trị người dùng đang để. Chỉnh dần theo ảnh thật: sửa đúng file này
// (cách thử: docs/KIEM_TRA_VE.md). 🧪 Mới thử bằng ảnh mẫu, chưa in ra giấy.
const BASE = {                   // mặc định chung, từng preset ghi đè
    "image-auto-levels": true, "image-clahe": false, "image-denoise": false,
    "image-black-point": "0", "image-white-point": "255", "image-gamma": "1",
    "style-levels": "4", "style-angle": "45", "style-spacing": "", "style-amplitude": "",
    "style-outline": false, "style-outline-detail": "medium", "style-invert": false, "palette-mode": "mono"
};

export const PRESETS = {
    portrait: {                  // chân dung / ảnh tự chụp: mịn, nhiều mức, viền ít (mắt, mũi, miệng, tóc)
        ...BASE, "image-denoise": true, "image-gamma": "1.15",
        "style-kind": "zigzag", "style-levels": "5", "style-outline": true, "style-outline-detail": "low"
    },
    landscape: {                 // phong cảnh, trời mây, nhà cửa, cảnh đêm: tăng chi tiết cục bộ, sóng cho mảng trời
        ...BASE, "image-clahe": true,
        "style-kind": "wave", "style-angle": "30", "style-outline": true, "style-outline-detail": "low"
    },
    closeup: {                   // cận cảnh: đồ ăn, cốc, đồ vật: xoắn ốc mềm + viền khối rõ
        ...BASE, "image-gamma": "1.25",
        "style-kind": "spiral", "style-outline": true, "style-outline-detail": "low"
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
