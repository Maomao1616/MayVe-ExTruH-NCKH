// Hằng số máy và giao diện. Mọi giả định chưa kiểm chứng ghi ở đây để sửa một chỗ.
// Nguồn: ConfigNCKH-16.yaml (X 285, Y 318, Z 5).

export const MACHINE = {
    travelX: 285,        // mm
    travelY: 318,        // mm (yaml 14; bản 13 là 310)
    penUpZ: 5,           // GIẢ ĐỊNH: Z5 = bút lên (chưa thử máy thật)
    penDownZ: 0,         // GIẢ ĐỊNH: Z0 = bút xuống
    penFeed: 3000,       // mm/phút
    rapidFeed: 6000      // mm/phút khi G0
};

export const POLL = {
    statusMs: 400,       // thăm dò /api/status
    logMs: 700,          // thăm dò /api/log
    staleMs: 2000        // quá ngưỡng này coi dữ liệu là cũ -> khóa điều khiển
};

export const DEFAULT_BAUD = 115200;

// Chiều hiển thị khung 2D: mặc định gốc (0,0) ở góc trên trái, X sang phải, Y xuống dưới.
// Đổi true nếu thử máy thật thấy ngược chiều.
export const VIEW = { flipX: false, flipY: false };
