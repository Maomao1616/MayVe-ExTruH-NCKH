// Hằng số máy và giao diện. Mọi giả định chưa kiểm chứng ghi ở đây để sửa một chỗ.
// Nguồn: ConfigNCKH-16.yaml (X 285, Y 318, Z 5).

export const MACHINE = {
    travelX: 285,        // mm
    travelY: 318,        // mm (yaml 14; bản 13 là 310)
    penUpZ: 5,           // GIẢ ĐỊNH: Z5 = bút lên (chưa thử máy thật)
    penDownZ: 0,         // GIẢ ĐỊNH: Z0 = bút xuống
    penFeed: 3000        // mm/phút
};

export const POLL = {
    statusMs: 400,       // thăm dò /api/status
    logMs: 700,          // thăm dò /api/log
    staleMs: 2000        // quá ngưỡng này coi dữ liệu là cũ -> khóa điều khiển
};

export const DEFAULT_BAUD = 115200;
