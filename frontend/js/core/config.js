// Hằng số máy và giao diện. Mọi giả định chưa kiểm chứng ghi ở đây để sửa một chỗ.
// Nguồn: ConfigNCKH-16.yaml (X 285, Y 318, Z 5).

export const MACHINE = {
    travelX: 285,        // mm
    travelY: 318,        // mm 
    // Bút: giá trị mặc định; views/settings.js ghi đè bằng hồ sơ ở backend (Cài đặt → Cấu hình máy).
    travelZ: 5,          // mm, hành trình Z trong YAML (tab Tạo bản vẽ dùng để kiểm Z bút)
    penUpZ: 3,           // Z3 = bút lên (đủ khỏi giấy, nhanh hơn Z5; hành trình Z thật là 5)
    penMidZ: 1.5,        // nấc giữa: bút lơ lửng sát giấy
    penDownZ: 0,         // Z0 = bút xuống
    penFeed: 3000,       // mm/phút
    jogMaxStep: 50,      // mm, bước jog lớn nhất được hiện trong ô chọn
    rapidFeed: 6000      // mm/phút khi G0
};

// Tùy chọn "Hoạt động" (Cài đặt). views/settings.js nạp từ trình duyệt và ghi đè các giá trị này.
export const PREFS = {
    pollMs: 500,         // nhịp cập nhật terminal (/api/log)
    confirmHome: true,   // hỏi lại trước $H / $HX / $HY
    shortcuts: false     // jog bằng phím mũi tên (mặc định tắt để tránh bấm nhầm)
};

export const POLL = {
    statusMs: 100,       // thăm dò /api/status: bằng nhịp backend hỏi `?` (MachineService.POLL_S)
    logMs: 500,          // thăm dò /api/log (terminal), theo PREFS.pollMs
    staleMs: 2000        // quá ngưỡng này coi dữ liệu là cũ -> khóa điều khiển
};

export const DEFAULT_BAUD = 115200;

// Chiều hiển thị khung 2D: mặc định gốc (0,0) ở góc trên trái, X sang phải, Y xuống dưới.
// Đổi true nếu thử máy thật thấy ngược chiều.
export const VIEW = { flipX: false, flipY: false };
