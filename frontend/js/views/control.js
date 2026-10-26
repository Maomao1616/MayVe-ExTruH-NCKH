// views/control.js — Tab Điều khiển.
//  - initStatusPanel : bảng vị trí / trạng thái (chỉ đọc)
//  - initMotionControls: jog, bút, Zero, Home, XY 0, hủy jog (gửi lệnh)
// Terminal và các nút Tạm dừng/Tiếp tục/Reset/Mở khóa thuộc về views/terminal.js.
// Mọi lệnh đi qua api.js; giao diện không tự suy đoán trạng thái máy.

import { t, getLanguage } from "../i18n.js";
import { api } from "../api.js";
import { MACHINE } from "../config.js";
import { subscribe, isConnected, isStale } from "../state.js";

const $ = (id) => document.getElementById(id);

const setText = (id, value) => {
    const element = $(id);
    if (element) element.textContent = value;
};

const formatNumber = (value) => {
    if (value === null || value === undefined || value === "") return "—";
    const number = Number(value);
    return Number.isFinite(number) ? number.toFixed(3) : "—";
};

const formatTime = (ms) => {
    if (!Number.isFinite(ms)) return "—";
    return new Date(ms).toLocaleTimeString(
        getLanguage() === "en" ? "en-GB" : "vi-VN"
    );
};

// Mã alarm/lỗi do firmware báo: dịch theo `alarm.<mã>` / `error.<mã>`.
// Thiếu bản dịch thì hiện mã trần (ví dụ "ALARM 14").
const codeText = (prefix, item) => {
    if (item?.code == null) return "—";
    const key = `${prefix}.${item.code}`;
    const text = t(key);
    return text === key
        ? `${prefix.toUpperCase()} ${item.code}`
        : `${text} (${item.code})`;
};

export function initControl() {
    initStatusPanel();
    initMotionControls();
}

/* ==================== BẢNG VỊ TRÍ / TRẠNG THÁI ==================== */

const STATUS_FIELDS = [
    "workspace-x", "workspace-y", "workspace-z",
    "machine-x", "machine-y", "machine-z",
    "machine-feed", "planner-free", "rx-free",
    "last-update-time", "homed-indicator",
    "last-alarm", "last-error"
];

function initStatusPanel() {
    const displayStatus = (snapshot) => {
        const status = snapshot.status;
        const machine = status?.machine;
        const connection = status?.connection;
        const connected =
            snapshot.backendOnline && connection?.connected === true;

        // Mất backend, chưa kết nối, hoặc chưa có báo cáo nào: không để số liệu cũ
        // (backend giữ lại số cuối sau khi ngắt) trông như dữ liệu trực tiếp.
        if (!connected || !machine) {
            for (const id of STATUS_FIELDS) setText(id, "—");

            const label = t(
                snapshot.backendOnline
                    ? "common.status.disconnected"
                    : "common.status.unavailable"
            );
            setText("controller-state", label);
            setText("coordinate-source", label);
            setText("active-connection-mode", t("common.status.disconnected"));

            const banner = $("readonly-banner");
            if (banner) banner.hidden = true;

            return;
        }

        // mpos / wpos là mảng [X, Y, Z] hoặc null.
        const mpos = Array.isArray(machine.mpos) ? machine.mpos : null;
        const wpos = Array.isArray(machine.wpos) ? machine.wpos : null;

        ["x", "y", "z"].forEach((axis, index) => {
            setText(`machine-${axis}`, mpos ? formatNumber(mpos[index]) : "—");
            setText(`workspace-${axis}`, wpos ? formatNumber(wpos[index]) : "—");
        });

        setText("controller-state", machine.state ?? "—");

        setText("machine-feed", machine.feed == null
            ? "—"
            : `${formatNumber(machine.feed)} mm/min`);
        setText("planner-free", machine.planner_free ?? "—");
        setText("rx-free", machine.rx_free ?? "—");

        setText("homed-indicator", typeof status.homed_guess === "boolean"
            ? t(status.homed_guess
                ? "control.controller.homed"
                : "control.controller.notHomed")
            : t("common.status.unknown"));

        // Alarm chỉ có nghĩa khi máy đang ở trạng thái Alarm
        // (backend không tự xóa last_alarm). Lỗi giữ kèm giờ xảy ra.
        setText("last-alarm", machine.state === "Alarm"
            ? codeText("alarm", status.last_alarm)
            : "—");

        const lastError = status.last_error;
        setText("last-error", lastError?.code == null
            ? "—"
            : `${codeText("error", lastError)} · ${formatTime(lastError.at * 1000)}`);

        setText("last-update-time", formatTime(snapshot.lastUpdatedAt));
        setText("coordinate-source", t("common.status.live"));

        setText("active-connection-mode", connection.mode === "sim"
            ? t("settings.connection.sim")
            : connection.mode === "serial"
                ? t("settings.connection.serial")
                : String(connection.mode ?? "—"));

        const banner = $("readonly-banner");
        if (banner) {
            banner.hidden = !(
                connection.mode === "serial" &&
                connection.motion_unlocked === false
            );
        }

        setText("firmware-version", "—");   // chưa có trong API status
        
    };

    subscribe(displayStatus);
}

/* ==================== ĐIỀU KHIỂN CHUYỂN ĐỘNG ==================== */

// Báo lỗi API cho terminal (terminal.js nghe sự kiện này và tự dịch ra tiếng Anh).
const reportError = (error) => {
    window.dispatchEvent(new CustomEvent("extruxy:message", { detail: { error } }));
};

// Rút gọn số để không sinh "0.30000000000000004".
const trim = (value) => String(Number(value.toFixed(3)));

function initMotionControls() {
    const jogButtons = document.querySelectorAll("[data-jog-axis]");
    const commandButtons = document.querySelectorAll(
        ".coordinates-panel [data-command]"      // không gồm nút Mở khóa (của terminal.js)
    );
    const jogCancel = $("jog-cancel-btn");
    const centerButton = $("jog-center-btn");
    const penUp = $("pen-up-btn");
    const penDown = $("pen-down-btn");

    const readJogSettings = () => {
        const distance = Number($("jog-distance")?.value);
        const feed = Number($("jog-feed")?.value);
        return distance > 0 && feed > 0 ? { distance, feed } : null;
    };

    const sendCommand = async (line) => {
        try {
            await api.command(line);
        } catch (error) {
            reportError(error);
        }
    };

    // Jog tương đối: $J=G91 G21 <trục><±bước> F<tốc độ>
    jogButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const settings = readJogSettings();
            if (!settings) return;

            const axis = button.dataset.jogAxis.toUpperCase();
            const direction = Number(button.dataset.jogDirection);
            sendCommand(
                `$J=G91 G21 ${axis}${trim(direction * settings.distance)} F${settings.feed}`
            );
        });
    });

    // Về gốc làm việc (X0 Y0). Dùng jog tuyệt đối nên chạy được cả khi chưa Home.
    centerButton?.addEventListener("click", () => {
        const settings = readJogSettings();
        if (!settings) return;
        sendCommand(`$J=G90 G21 X0 Y0 F${settings.feed}`);
    });

    // Bút lên/xuống: hằng số trong config.js (Z5/Z0 là giả định, chưa thử máy thật).
    penUp?.addEventListener("click", () => {
        sendCommand(`$J=G90 G21 Z${MACHINE.penUpZ} F${MACHINE.penFeed}`);
    });
    penDown?.addEventListener("click", () => {
        sendCommand(`$J=G90 G21 Z${MACHINE.penDownZ} F${MACHINE.penFeed}`);
    });

    // Zero (G10 L20 P1 ...) và Home ($H, $HX, $HY): lệnh nằm sẵn trong data-command.
    commandButtons.forEach((button) => {
        button.addEventListener("click", () => sendCommand(button.dataset.command));
    });

    jogCancel?.addEventListener("click", async () => {
        try {
            await api.realtime(jogCancel.dataset.realtime ?? "jog_cancel");
        } catch (error) {
            reportError(error);
        }
    });

    // Bật/tắt theo trạng thái thật. Backend và firmware vẫn là lớp kiểm tra cuối.
    const updateControls = (snapshot) => {
        const connection = snapshot.status?.connection;
        const machineState = snapshot.status?.machine?.state;

        const canMove =
            isConnected() && !isStale() && connection?.motion_unlocked !== false;
        const idle = canMove && machineState === "Idle";
        const canHome = canMove && (machineState === "Idle" || machineState === "Alarm");

        jogButtons.forEach((button) => { button.disabled = !idle; });
        [centerButton, penUp, penDown].forEach((button) => {
            if (button) button.disabled = !idle;
        });

        commandButtons.forEach((button) => {
            const isHome = button.dataset.command.startsWith("$H");
            button.disabled = !(isHome ? canHome : idle);
        });

        if (jogCancel) {
            jogCancel.disabled =
                !(isConnected() && !isStale() && machineState === "Jog");
        }
    };

    subscribe(updateControls);
}
