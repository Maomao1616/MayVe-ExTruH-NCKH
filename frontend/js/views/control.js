// views/control.js — Tab Điều khiển.
//  - initStatusPanel : bảng vị trí / trạng thái (chỉ đọc)
//  - initMotionControls: jog, thanh bút 3 nấc, Zero, Home, XY 0 (gửi lệnh)
//  - initGcodePanel  : tệp G-code, cảnh báo gốc vị trí, chạy, tiến trình, hủy tác vụ
//  - initFeedOverride: ghi đè tốc độ (% của F trong tệp) khi đang vẽ
// Terminal và các nút Tạm dừng/Tiếp tục/Reset/Mở khóa thuộc về views/terminal.js.
// Mọi lệnh đi qua api.js; giao diện không tự suy đoán trạng thái máy.

import { t, getLanguage } from "../core/i18n.js";
import { api } from "../core/api.js";
import { MACHINE, PREFS } from "../core/config.js";
import { subscribe, isConnected, isStale, firmwareLabel } from "../core/state.js";
import { parseGcode, outOfRange, formatDuration } from "../lib/gcode.js";
import { store, setFile, requestPreview, subscribeStore } from "../stores/jobstore.js";
import { refreshDrafts } from "../stores/draftstore.js";
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
   // Tính lúc dùng: hồ sơ bút (Cài đặt → Cấu hình máy) có thể đổi sau khi tải trang.
   const parseOptions = () => ({
       penUpZ: MACHINE.penUpZ,
       penDownZ: MACHINE.penDownZ,
       rapidFeed: MACHINE.rapidFeed ?? 6000
   });
   const message = (detail) => window.dispatchEvent(new CustomEvent("extruxy:message", { detail }));


export function initControl() {
    initStatusPanel();
    initMotionControls();
    initGcodePanel();
    initFeedOverride();
    initPreview();
    initMotionLock();
}

/* ==================== GHI ĐÈ TỐC ĐỘ (feed override) ==================== */
// Lệnh tức thời của FluidNC: tính theo % của F trong tệp (F3000 ở 80% = 2400 mm/phút).
// Không làm máy bắt đầu chạy nên backend luôn cho gửi, kể cả khi máy thật đang khóa.
function initFeedOverride() {
    const buttons = document.querySelectorAll("[data-feed]");
    const value = $("feed-override-value");
    buttons.forEach((button) => {
        button.addEventListener("click", async () => {
            try {
                await api.realtime(button.dataset.feed);
            } catch (error) {
                reportError(error);
            }
        });
    });
    subscribe((snapshot) => {
        const canSend = isConnected() && !isStale();
        buttons.forEach((button) => { button.disabled = !canSend; });
        const feed = snapshot.status?.machine?.overrides?.[0];
        if (value) {
            value.textContent = canSend && Number.isFinite(feed) ? `${feed}%` : "—";
            value.classList.toggle("is-changed", canSend && Number.isFinite(feed) && feed !== 100);
        }
    });
}

/* ==================== BẢNG VỊ TRÍ / TRẠNG THÁI ==================== */

const STATUS_FIELDS = [
    "workspace-x", "workspace-y", "workspace-z",
    "machine-x", "machine-y", "machine-z",
    "machine-feed", "planner-free", "rx-free",
    "last-update-time", "homed-indicator",
    "last-alarm", "last-error", "pen-state", "firmware-version"
];

const PEN_TOL_MM = 0.05;    // cùng sai số backend dùng để xác nhận nâng bút

// Ba nấc bút (data-pen) -> trường Z trong MACHINE (Cài đặt ghi đè, xem views/settings.js).
const PEN_LEVELS = { up: "penUpZ", mid: "penMidZ", down: "penDownZ" };

const workZ = (wpos) => (Array.isArray(wpos) ? Number(wpos[2]) : NaN);

// Nấc bút đang ở (up/mid/down) theo Z làm việc, hoặc null nếu không khớp nấc nào.
function penLevel(wpos) {
    const z = workZ(wpos);
    if (!Number.isFinite(z)) return null;
    return Object.keys(PEN_LEVELS)
        .find((level) => Math.abs(z - MACHINE[PEN_LEVELS[level]]) <= PEN_TOL_MM) ?? null;
}

function penText(wpos) {
    const z = workZ(wpos);
    if (!Number.isFinite(z)) return "—";
    const level = penLevel(wpos);
    return level ? t(`control.pen.${level}`) : `Z ${trim(z)}`;
}

// Gửi $I một lần mỗi phiên kết nối khi chưa biết firmware: board thật không reset khi
// mở cổng nên thường không có banner. $I là lệnh chỉ đọc, được phép cả khi máy đang khóa.
let askedFirmwareFor = null;
function askFirmwareOnce(snapshot) {
    const status = snapshot.status;
    const connection = status?.connection;
    const key = connection?.connected ? `${connection.mode}:${connection.port}` : null;
    if (key === null) { askedFirmwareFor = null; return; }
    if (askedFirmwareFor === key || firmwareLabel() || isStale()) return;
    const job = status.job?.state;
    if (job === "running" || job === "finishing" || status.stopping) return;
    askedFirmwareFor = key;
    api.command("$I").catch(() => { askedFirmwareFor = null; });
}

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

            askedFirmwareFor = null;      // lần kết nối sau hỏi lại $I
            return;
        }

        // mpos / wpos là mảng [X, Y, Z] hoặc null.
        const mpos = Array.isArray(machine.mpos) ? machine.mpos : null;
        const wpos = Array.isArray(machine.wpos) ? machine.wpos : null;

        ["x", "y", "z"].forEach((axis, index) => {
            setText(`machine-${axis}`, mpos ? formatNumber(mpos[index]) : "—");
            setText(`workspace-${axis}`, wpos ? formatNumber(wpos[index]) : "—");
        });
        setText("pen-state", penText(wpos));

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

        const alarmText = machine.state === "Alarm"
            ? (status.last_alarm?.code != null
                ? codeText("alarm", status.last_alarm)
                : t("control.controller.alarmNoCode"))
            : "—";
        setText("last-alarm", alarmText);


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

        setText("firmware-version", firmwareLabel() ?? "—");
        askFirmwareOnce(snapshot);
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
    const penButtons = document.querySelectorAll(".pen-bar [data-pen]");
    const jogDistance = $("jog-distance");

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

    // Thanh bút 3 nấc: jog tuyệt đối tới Z của nấc (đã khớp WebUI FluidNC trên máy thật).
    penButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const z = MACHINE[PEN_LEVELS[button.dataset.pen]];
            sendCommand(`$J=G90 G21 Z${trim(z)} F${trim(MACHINE.penFeed)}`);
        });
    });

    // Hồ sơ máy đổi (Cài đặt): ghi lại số Z trên nút, ẩn bước jog lớn hơn mức tối đa.
    const applyProfile = () => {
        for (const [level, field] of Object.entries(PEN_LEVELS)) {
            setText(`pen-${level}-z`, `Z${trim(MACHINE[field])}`);
        }
        if (!jogDistance) return;
        for (const option of jogDistance.options) {
            option.hidden = option.disabled = Number(option.value) > MACHINE.jogMaxStep;
        }
        if (jogDistance.selectedOptions[0]?.disabled) {
            const allowed = [...jogDistance.options].filter((o) => !o.disabled);
            if (allowed.length) jogDistance.value = allowed[allowed.length - 1].value;
        }
    };
    applyProfile();
    window.addEventListener("extruxy:profile-changed", applyProfile);

    // Zero (G10 L20 P1 ...) và Home ($H, $HX, $HY): lệnh nằm sẵn trong data-command.
    // Home hỏi lại trước nếu bật "Xác nhận trước khi Home" (Cài đặt → Hoạt động).
    const homeModal = $("custom-home-modal");
    let pendingHome = null;
    const closeHomeModal = () => { if (homeModal) homeModal.hidden = true; pendingHome = null; };
    $("modal-home-cancel-btn")?.addEventListener("click", closeHomeModal);
    $("modal-home-confirm-btn")?.addEventListener("click", () => {
        const command = pendingHome;
        closeHomeModal();
        if (command) sendCommand(command);
    });

    commandButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const command = button.dataset.command;
            if (command.startsWith("$H") && PREFS.confirmHome && homeModal) {
                pendingHome = command;
                setText("modal-home-command", command);
                homeModal.hidden = false;
                $("modal-home-cancel-btn")?.focus();
                return;
            }
            sendCommand(command);
        });
    });

    // Jog bằng phím mũi tên (Cài đặt → Hoạt động → Phím tắt, mặc định tắt).
    // Chỉ "bấm hộ" nút jog tương ứng, nên mọi điều kiện khóa của nút vẫn áp dụng.
    const KEY_TO_JOG = {
        ArrowLeft: ["x", "-1"], ArrowRight: ["x", "1"],
        ArrowUp: ["y", "-1"], ArrowDown: ["y", "1"]     // khớp bàn jog: ↑ là Y−
    };
    document.addEventListener("keydown", (event) => {
        const target = KEY_TO_JOG[event.key];
        if (!target || !PREFS.shortcuts) return;
        if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.repeat) return;
        if (event.target.closest?.("input, textarea, select, [contenteditable]")) return;
        if (!$("panel-control")?.classList.contains("is-active")) return;
        if (document.querySelector(".glass-modal-overlay:not([hidden])")) return;
        const button = document.querySelector(
            `[data-jog-axis="${target[0]}"][data-jog-direction="${target[1]}"]`);
        if (!button || button.disabled) return;
        event.preventDefault();         // không cuộn trang
        button.click();
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
        if (centerButton) centerButton.disabled = !idle;

        // Nấc đang ở được tô sáng theo Z thật máy báo (không theo nút vừa bấm).
        const level = isConnected() ? penLevel(snapshot.status?.machine?.wpos) : null;
        penButtons.forEach((button) => {
            button.disabled = !idle;
            const active = button.dataset.pen === level;
            button.classList.toggle("is-active", active);
            button.setAttribute("aria-pressed", String(active));
        });

        commandButtons.forEach((button) => {
            const isHome = button.dataset.command.startsWith("$H");
            button.disabled = !(isHome ? canHome : idle);
        });

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

    const saveDraftButton = $("save-gcode-draft-btn");
    const resumeBox = $("resume-box");
    const resumeRun = $("resume-run-btn");
    const resumeDiscard = $("resume-discard-btn");
    let resume = { available: false };   // điểm dừng đang lưu ở backend (GET /api/jobs/resume)
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
            const parsed = parseGcode(await chosen.text(), parseOptions());
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

    // Một tệp = một bản thảo: gửi các dòng đã làm sạch lên máy chủ (nó kiểm lại, dựng ảnh minh họa, lưu).
    saveDraftButton?.addEventListener("click", async () => {
        const file = store.file;
        if (!file) return;
        saveDraftButton.disabled = true;
        try {
            const { draft } = await api.drawGcodeImport(file.name, file.parsed.lines, MACHINE.travelX, MACHINE.travelY);
            await refreshDrafts();
            message({ text: `Saved to drafts: ${draft.name}` });
        } catch (error) {
            message({ error });
        }
        render();
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

    /* --- tiếp tục từ điểm dừng (hủy / lỗi / mất kết nối) --- */
    async function refreshResume() {
        try { resume = await api.jobResumeInfo(); } catch { return; }      // lỗi mạng: giữ bản đang có
        render();
    }

    // Hộp xác nhận (thay cho window.confirm): tóm tắt điểm dừng, nhắc 3 việc cần kiểm, phải tick mới bấm được.
    const modal = $("resume-modal");
    const ack = $("resume-modal-ack");
    const modalConfirm = $("resume-modal-confirm");
    const fill = (template, vars) => Object.entries(vars).reduce((s, [k, v]) => s.replace(`{${k}}`, String(v)), template);

    function closeResumeModal() {
        modal?.setAttribute("hidden", "");
        if (ack) ack.checked = false;
        if (modalConfirm) modalConfirm.disabled = true;
    }

    function openResumeModal() {
        if (!modal || !resume.resumable) return;
        setText("resume-modal-name", resume.name);
        setText("resume-modal-done", fill(t("control.resume.factDone"), { done: resume.done, total: resume.total }));
        setText("resume-modal-line", String(resume.resume_line));
        setText("resume-modal-back", fill(t("control.resume.factBack"), { n: resume.rewound }));
        const wco = $("resume-modal-wco");
        if (wco) wco.hidden = !resume.wco_changed;
        if (ack) ack.checked = false;
        if (modalConfirm) modalConfirm.disabled = true;
        modal.removeAttribute("hidden");
        ack?.focus();
    }

    resumeRun?.addEventListener("click", openResumeModal);
    ack?.addEventListener("change", () => { if (modalConfirm) modalConfirm.disabled = !ack.checked; });
    $("resume-modal-cancel")?.addEventListener("click", closeResumeModal);
    modal?.addEventListener("click", (event) => { if (event.target === modal) closeResumeModal(); });
    window.addEventListener("keydown", (event) => { if (event.key === "Escape" && modal && !modal.hidden) closeResumeModal(); });

    modalConfirm?.addEventListener("click", async () => {
        if (!ack?.checked) return;
        const acceptChange = resume.wco_changed === true;          // đã thấy cảnh báo trong hộp và vẫn tick
        closeResumeModal();
        resumeRun.disabled = true;
        try {
            await api.jobResume(acceptChange);
        } catch (error) {
            message({ error });
        }
        refreshResume();
    });

    // Hộp xác nhận bỏ điểm dừng (thay cho window.confirm)
    const discardModal = $("discard-modal");
    const closeDiscardModal = () => discardModal?.setAttribute("hidden", "");

    resumeDiscard?.addEventListener("click", () => {
        if (!discardModal) return;
        setText("discard-modal-name", resume.name ?? "—");
        setText("discard-modal-done", fill(t("control.resume.factDone"), { done: resume.done ?? 0, total: resume.total ?? 0 }));
        discardModal.removeAttribute("hidden");
        $("discard-modal-cancel")?.focus();            // mặc định là "Giữ lại": bấm Enter nhầm cũng an toàn
    });
    $("discard-modal-cancel")?.addEventListener("click", closeDiscardModal);
    discardModal?.addEventListener("click", (event) => { if (event.target === discardModal) closeDiscardModal(); });
    window.addEventListener("keydown", (event) => { if (event.key === "Escape" && discardModal && !discardModal.hidden) closeDiscardModal(); });
    $("discard-modal-confirm")?.addEventListener("click", async () => {
        closeDiscardModal();
        try { await api.jobResumeDiscard(); } catch (error) { message({ error }); }
        refreshResume();
    });

    function renderResume(job, snapshot) {
        if (!resumeBox) return;
        const active = isActive(job) || snapshot?.status?.stopping;
        resumeBox.hidden = !resume.available || Boolean(active);
        if (resumeBox.hidden) return;
        const state = t(`control.resume.state.${resume.state}`);
        let text;
        if (resume.resumable) {
            text = t("control.resume.text").replace("{name}", resume.name).replace("{state}", state)
                .replace("{done}", String(resume.done)).replace("{total}", String(resume.total))
                .replace("{line}", String(resume.resume_line));
        } else {
            text = `${resume.name} (${state}): ${resume.message ?? t("control.resume.notResumable")}`;
        }
        setText("resume-text", text);
        const connection = snapshot?.status?.connection;
        const ready = isConnected() && !isStale() && connection?.motion_unlocked !== false &&
            snapshot?.status?.machine?.state === "Idle";
        resumeRun.disabled = !(resume.resumable && ready);
        resumeRun.title = resume.resumable && !ready ? t("control.resume.needIdle") : "";
    }

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

            const cancelWith = async (mode) => {
                customCancelModal.setAttribute("hidden", "");
                try {
                    await api.jobCancel(mode, MACHINE.penUpZ, MACHINE.penFeed);
                } catch (error) {
                    window.dispatchEvent(new CustomEvent("extruxy:message", { detail: { error } }));
                }
            };
                modalCancelJobConfirm.addEventListener("click", () => cancelWith("soft"));
                $("modal-cancel-job-btn-hard")?.addEventListener("click", () => cancelWith("hard"));
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

    let seenFile = null;         // tệp đã xem trước/xác nhận là của tệp NÀY; tệp mới (kể cả từ bản thảo) làm lại từ đầu

    function render() {
        const snapshot = lastSnapshot;
        const file = store.file;
        if (file !== seenFile) {
            seenFile = file;
            previewed = false;
            confirmBox.checked = false;
        }
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
        if (saveDraftButton) saveDraftButton.disabled = !file;
        confirmBox.disabled = !file || !previewed || active;
        if (confirmBox.disabled && !active) confirmBox.checked = false;

        const canRun = Boolean(file) && !problem && previewed && confirmBox.checked &&
            isConnected() && !isStale() && connection?.motion_unlocked !== false &&
            machineState === "Idle" && !active;
        runButton.disabled = !canRun;

        // Sau $X máy chạy được G-code dù chưa Home (MACHINE.md A3): nhắc kiểm tra gốc vị trí.
        const originWarning = $("gcode-origin-warning");
        if (originWarning) {
            originWarning.hidden = !(file && isConnected() && snapshot?.status?.homed_guess === false);
        }

        if (cancelButton) {
            cancelButton.hidden = !active;
            cancelButton.disabled = !active;
        }

        renderProgress(job);
        renderResume(job, snapshot);
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
        if (job.state === "done" || job.state === "failed" || job.state === "cancelled") {
            setTimeout(refreshResume, 600);       // backend ghi/xóa điểm dừng ở luồng riêng, chờ một chút
        }
        if (job.state === "done") {
            message({ text: `Job finished: ${job.name} (${formatDuration(job.elapsed_s)}).` });
        } else if (job.state === "failed") {
            const e = job.error ?? {};
            const where = e.line ? ` at line ${e.line}` : "";
            message({ text: `Job failed${where}: ${e.text ?? e.code ?? "unknown"}. Check the machine before continuing.` });
        } else if (job.state === "cancelled") {
            message({ text: "Job cancelled." });
        }
    }

    subscribeStore(() => render());
    subscribe((snapshot) => { lastSnapshot = snapshot; render(); });
    refreshResume();
}
