// views/jobs.js — Khối "Tệp G-code" và tiến trình tác vụ.
//  - Nạp tệp từ máy tính, đọc bằng gcode.js, hiện số dòng / vùng bao / cảnh báo.
//  - "Xem trước": báo cho preview.js phát lại (không gửi gì cho máy).
//  - "Chạy": gửi các dòng đã làm sạch cho backend (POST /api/jobs), backend gửi từng dòng.
//  - Hiện tiến trình ở thanh tiêu đề; nút Hủy tác vụ.
// Chế độ "chạy từ bộ nhớ máy" (thẻ SD / flash) chưa hỗ trợ: nút Chạy tắt ở chế độ đó.

import { t } from "../i18n.js";
import { api } from "../api.js";
import { MACHINE } from "../config.js";
import { subscribe, isConnected, isStale } from "../state.js";


const MAX_FILE_BYTES = 20 * 1024 * 1024;
const PARSE_OPTIONS = {
    penUpZ: MACHINE.penUpZ,
    penDownZ: MACHINE.penDownZ,
    rapidFeed: MACHINE.rapidFeed ?? 6000
};

const $ = (id) => document.getElementById(id);
const setText = (id, value) => { const e = $(id); if (e) e.textContent = value; };

// Báo cho terminal (terminal.js nghe sự kiện này).
const message = (detail) => window.dispatchEvent(new CustomEvent("extruxy:message", { detail }));

export function initJobs() {
    initRunModeSwitch();
    initGcodePanel();
}

