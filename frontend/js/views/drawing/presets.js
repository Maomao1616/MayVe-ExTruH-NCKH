// views/drawing/presets.js — bộ thông số dựng sẵn cho tiền xử lý ảnh + kiểu nét (chỉ là dữ liệu).
// Khóa = id ô trong index.html; giá trị = chuỗi/boolean ghi thẳng vào ô (params.setValues).
// Ô không có trong preset giữ nguyên giá trị người dùng đang để. Chỉnh dần theo ảnh thật: sửa đúng file này.
export const PRESETS = {
    portrait: {                  // chân dung: mịn, nhiều mức, viền phác mắt/mũi/miệng
        "image-auto-levels": true, "image-clahe": false, "image-denoise": true,
        "image-black-point": "0", "image-white-point": "255", "image-gamma": "1.15",
        "style-kind": "zigzag", "style-levels": "5", "style-angle": "45", "style-spacing": "",
        "style-outline": true, "style-invert": false, "palette-mode": "mono"
    },
    landscape: {                 // phong cảnh: tăng chi tiết cục bộ, nét sóng cho mảng trời/nước
        "image-auto-levels": true, "image-clahe": true, "image-denoise": false,
        "image-black-point": "0", "image-white-point": "255", "image-gamma": "1",
        "style-kind": "wave", "style-levels": "4", "style-angle": "30", "style-spacing": "",
        "style-outline": false, "style-invert": false, "palette-mode": "mono"
    },
    circuit: {                   // mạch điện / bản vẽ kỹ thuật, ảnh scan nền xám: chỉ lấy nét viền
        "image-auto-levels": true, "image-clahe": false, "image-denoise": false,
        "image-black-point": "60", "image-white-point": "200", "image-gamma": "1",
        "style-kind": "outline", "style-levels": "4", "style-angle": "45", "style-spacing": "",
        "style-outline": false, "style-invert": false, "palette-mode": "mono"
    }
};

export const presetValues = (name) => PRESETS[name] ?? null;
