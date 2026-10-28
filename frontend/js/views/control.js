// views/control.js — Tab Điều khiển.
//  - initStatusPanel : bảng vị trí / trạng thái (chỉ đọc)
//  - initMotionControls: jog, bút, Zero, Home, XY 0, hủy jog (gửi lệnh)
// Terminal và các nút Tạm dừng/Tiếp tục/Reset/Mở khóa thuộc về views/terminal.js.
// Mọi lệnh đi qua api.js; giao diện không tự suy đoán trạng thái máy.

import { t, getLanguage } from "../i18n.js";
import { api } from "../api.js";
import { MACHINE } from "../config.js";
import { subscribe, isConnected, isStale } from "../state.js";
import { parseGcode, outOfRange, formatDuration } from "../gcode.js";
import { store, setFile, requestPreview, subscribeStore } from "../jobstore.js";
import { initPreview } from "./preview.js";

const $ = (id) => document.getElementById(id);

let lastConnection = null;

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

   const MAX_FILE_BYTES = 20 * 1024 * 1024;
   const PARSE_OPTIONS = {
       penUpZ: MACHINE.penUpZ,
       penDownZ: MACHINE.penDownZ,
       rapidFeed: MACHINE.rapidFeed ?? 6000
   };
   const message = (detail) => window.dispatchEvent(new CustomEvent("extruxy:message", { detail }));


export function initControl() {
    initStatusPanel();
    initMotionControls();
    initGcodePanel();
    initPreview();
    initMotionLock();
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


        lastConnection = connection;
        const liveBanner = $("motion-live-banner");
        if (liveBanner) {
            liveBanner.hidden = !(connection.mode === "serial" && connection.motion_unlocked === true);
            const left = connection.unlock_seconds_left;
            setText("motion-live-timer", Number.isFinite(left)
                ? `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}` : "—");
            const relock = $("relock-motion-btn");
            if (relock) relock.hidden = connection.motion_permanent === true;
        }
        const unlock = $("unlock-motion-btn");
        if (unlock) unlock.disabled = connection.unlock_available === false;

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

/* ==================== MỞ KHÓA / KHÓA CHUYỂN ĐỘNG ==================== */

function initMotionLock() {
    const setMotion = async (on) => {
        try {
            let pin = null;
            if (on && lastConnection?.unlock_needs_pin) {
                pin = window.prompt(t("control.motion.pin_prompt"));
                if (pin === null) return;
            }
            await api.motion(on, pin);
            message({ text: on ? "Motion unlocked." : "Motion locked." });
        } catch (error) { reportError(error); }
    };
    $("unlock-motion-btn")?.addEventListener("click", () => setMotion(true));
    $("relock-motion-btn")?.addEventListener("click", () => setMotion(false));
}



/* ==================== TỆP G-CODE, XEM TRƯỚC, CHẠY, TIẾN TRÌNH ==================== */
function initGcodePanel() {
    const fileInput = $("gcode-file");
    const previewButton = $("preview-gcode-btn");
    const confirmBox = $("run-confirm");
    const runButton = $("run-job-btn");
    const cancelButton = $("cancel-job-btn");
    if ( !fileInput || !previewButton || !confirmBox || !runButton) return;

    let previewed = false;       // đã bấm Xem trước cho tệp hiện tại
    let lastSnapshot = null;
    let lastJob = { id: null, state: null };

    /* --- nạp tệp --- */
    fileInput.addEventListener("change", async () => {
        const chosen = fileInput.files?.[0];
        fileInput.value = "";                        // cho phép chọn lại đúng tệp đó
        if (!chosen) return;

        if (chosen.size > MAX_FILE_BYTES) {
            message({ text: `File too large (${Math.round(chosen.size / 1048576)} MB, limit 20 MB).` });
            return;
        }
        try {
            const parsed = parseGcode(await chosen.text(), PARSE_OPTIONS);
            if (parsed.lineCount === 0) {
                message({ text: "File has no G-code lines." });
                return;
            }
            previewed = false;
            confirmBox.checked = false;
            setFile({ name: chosen.name, parsed });
        } catch (error) {
            console.error("Không đọc được tệp G-code:", error);
            message({ text: "Cannot read this file." });
        }
    });

    previewButton.addEventListener("click", () => {
        if (!store.file) return;
        previewed = true;
        requestPreview();
        render();
    });

    confirmBox.addEventListener("change", render);

    runButton.addEventListener("click", async () => {
        const file = store.file;
        if (!file) return;
        runButton.disabled = true;
        try {
            await api.jobStart(file.name, file.parsed.lines);
            confirmBox.checked = false;              // lần chạy sau phải xác nhận lại
        } catch (error) {
            message({ error });
        }
        render();
    });

    // --- XỬ LÝ NÚT VÀ HỘP THOẠI HỦY TÁC VỤ (Đặt trong initPreview) ---
    const cancelJobBtn = document.getElementById("cancel-job-btn");
    const customCancelModal = document.getElementById("custom-cancel-modal");
    const modalCancelJobClose = document.getElementById("modal-cancel-job-btn-close");
    const modalCancelJobConfirm = document.getElementById("modal-cancel-job-btn-confirm");

    if (cancelJobBtn && customCancelModal) {
        cancelJobBtn.addEventListener("click", () => {
            customCancelModal.removeAttribute("hidden");
        });

        modalCancelJobClose.addEventListener("click", () => {
            customCancelModal.setAttribute("hidden", "");
        });

        modalCancelJobConfirm.addEventListener("click", async () => {
            customCancelModal.setAttribute("hidden", "");
            try {
                // Gọi API hủy / dừng tác vụ
                await api.jobCancel();   // backend tự Reset sau khi đánh dấu hủy
            } catch (error) {
                console.error("Lỗi khi gửi lệnh Hủy tác vụ:", error);
                // Bắn event thông báo lỗi ra ngoài nếu cần hiển thị lên terminal
                window.dispatchEvent(new CustomEvent("extruxy:message", { detail: { error } }));
            }
        });
    }

    /* --- tính trạng thái hiện tại từ dữ liệu backend --- */
    const jobOf = (snapshot) => snapshot?.status?.job ?? null;
    const isActive = (job) => job && (job.state === "running" || job.state === "finishing");

    function fileProblem(snapshot) {
        const machine = snapshot?.status?.machine;
        const offset = Array.isArray(machine?.wco) ? machine.wco : [0, 0, 0];
        return store.file &&
            outOfRange(store.file.parsed.bboxAll, MACHINE.travelX, MACHINE.travelY, offset)
            ? "outOfRange" : null;
    }

    function render() {
        const snapshot = lastSnapshot;
        const file = store.file;
        const job = jobOf(snapshot);
        const active = isActive(job);
        const problem = fileProblem(snapshot);

        // thông tin tệp
        if (file) {
            const p = file.parsed;
            const size = p.bbox ? `${p.bbox.width.toFixed(1)} × ${p.bbox.height.toFixed(1)} mm` : "—";
            const parts = [`${p.lineCount} ${t("control.gcode.lines")}`, size, `~${formatDuration(p.seconds)}`];
            if (p.warnings.length) parts.push(`⚠ ${p.warnings.length}`);
            if (problem) parts.push(t("control.gcode.outOfRange"));
            setText("gcode-selected-name", file.name);
            setText("gcode-selected-info", parts.join(" · "));
            const info = $("gcode-selected-info");
            if (info) info.title = p.warnings.slice(0, 8)
                .map((w) => `${w.line}: ${w.key}${w.detail ? ` (${w.detail})` : ""}`).join("\n");
        } else {
            setText("gcode-selected-name", "—");
            setText("gcode-selected-info", "—");
        }

        // nút
        const connection = snapshot?.status?.connection;
        const machineState = snapshot?.status?.machine?.state;
        previewButton.disabled = !file;
        confirmBox.disabled = !file || !previewed || active;
        if (confirmBox.disabled && !active) confirmBox.checked = false;

        const canRun = Boolean(file) && !problem && previewed && confirmBox.checked &&
            isConnected() && !isStale() && connection?.motion_unlocked !== false &&
            machineState === "Idle" && !active;
        runButton.disabled = !canRun;

        if (cancelButton) {
            cancelButton.hidden = !active;
            cancelButton.disabled = !active;
        }

        renderProgress(job);
        reportJobTransitions(job);
    }

    function renderProgress(job) {
        if (!job) {
            setText("progress-job-name", t("control.progress.noJob"));
            setText("job-progress-percent", "—");
            setText("job-progress-lines", t("control.progress.lines"));
            setText("job-progress-eta", t("control.progress.eta"));
            setText("job-state", t("dynamic.noJob"));
            setBar(0);
            return;
        }
        const ratio = job.total > 0 ? job.acked / job.total : 0;
        const percent = job.state === "done" ? 100 : Math.min(99, Math.floor(ratio * 100));
        const eta = job.state === "running" && ratio >= 0.02
            ? formatDuration((job.elapsed_s * (1 - ratio)) / ratio) : "—";

        setText("progress-job-name", `${job.name} · ${t(`job.state.${job.state}`)}`);
        setText("job-progress-percent", `${percent}%`);
        setText("job-progress-lines", `${t("control.progress.linesLabel")}: ${job.acked} / ${job.total}`);
        setText("job-progress-eta", `${t("control.progress.etaLabel")}: ${eta}`);
        setText("job-state", t(`job.state.${job.state}`));
        setBar(percent);
    }

    function setBar(percent) {
        const fill = $("job-progress-fill");
        if (fill) {
            fill.style.width = `${percent}%`;
            // Tự động bật class hiệu ứng sọc chéo khi đang chạy, tắt khi xong
            if (percent > 0 && percent < 100) {
                fill.classList.add("is-active");
            } else {
                fill.classList.remove("is-active");
            }
        }
        $("job-progress-track")?.setAttribute("aria-valuenow", String(percent));
    }

    // Thông báo một lần khi tác vụ kết thúc (hiện ở terminal, tiếng Anh).
    function reportJobTransitions(job) {
        if (!job) { lastJob = { id: null, state: null }; return; }
        if (job.id === lastJob.id && job.state === lastJob.state) return;
        const first = job.id !== lastJob.id;
        lastJob = { id: job.id, state: job.state };
        if (first && job.state === "running") return;   // đã có dòng "Job started" từ backend
        if (job.state === "done") {
            message({ text: `Job finished: ${job.name} (${formatDuration(job.elapsed_s)}).` });
        } else if (job.state === "failed") {
            const e = job.error ?? {};
            const where = e.line ? ` at line ${e.line}` : "";
            message({ text: `Job failed${where}: ${e.text ?? e.code ?? "unknown"}. Check the machine before continuing.` });
        } else if (job.state === "cancelled") {
            message({ text: "Job cancelled. The machine is in Alarm: unlock, then lift the pen." });
        }
    }

    subscribeStore(() => render());
    subscribe((snapshot) => { lastSnapshot = snapshot; render(); });
}
