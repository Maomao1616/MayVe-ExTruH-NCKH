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
import { parseGcode, outOfRange, formatDuration } from "../gcode.js";
import { store, setFile, requestPreview, subscribeStore } from "../jobstore.js";

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

/* ==================== CHUYỂN ĐỔI CHẾ ĐỘ CHẠY G-CODE ==================== */
function initRunModeSwitch() {
    const panel = document.querySelector(".gcode-panel[data-mode]");
    const radios = document.querySelectorAll('input[name="run-mode"]');

    const sync = () => {
        const checked = document.querySelector('input[name="run-mode"]:checked');
        if (panel && checked) panel.dataset.mode = checked.value;
    };

    radios.forEach((radio) => radio.addEventListener("change", sync));
    sync(); // đồng bộ ngay lúc tải trang, kể cả khi trình duyệt nhớ lựa chọn cũ
}

/* ==================== TỆP G-CODE, XEM TRƯỚC, CHẠY, TIẾN TRÌNH ==================== */
function initGcodePanel() {
    const panel = document.querySelector(".gcode-panel[data-mode]");
    const fileInput = $("gcode-file");
    const previewButton = $("preview-gcode-btn");
    const confirmBox = $("run-confirm");
    const runButton = $("run-job-btn");
    const cancelButton = $("cancel-job-btn");
    if (!panel || !fileInput || !previewButton || !confirmBox || !runButton) return;

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

    cancelButton?.addEventListener("click", async () => {
        if (!window.confirm(t("job.confirmCancel"))) return;
        try {
            await api.jobCancel();
        } catch (error) {
            message({ error });
        }
    });

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
        const streaming = panel.dataset.mode === "stream";
        previewButton.disabled = !file;
        confirmBox.disabled = !file || !previewed || active;
        if (confirmBox.disabled && !active) confirmBox.checked = false;

        const canRun = Boolean(file) && !problem && previewed && confirmBox.checked &&
            isConnected() && !isStale() && connection?.motion_unlocked !== false &&
            machineState === "Idle" && !active && streaming;
        runButton.disabled = !canRun;
        runButton.title = streaming ? "" : t("control.gcode.deviceUnsupported");

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
        if (fill) fill.style.width = `${percent}%`;
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
