// views/settings.js — Tab Cài đặt. Một hàm vào cửa, mỗi khối trên giao diện một hàm:
//   1. initConnection     Kết nối máy (sim / cổng COM)
//   2. initBehavior       Hoạt động: nhịp cập nhật, xác nhận Home, phím tắt (trình duyệt -> PREFS)
//   3. initFirmwareInfo   Cấu hình máy: dòng Firmware
//      initMachineConfig  Cấu hình máy: YAML trên mạch + hồ sơ phần mềm (backend -> MACHINE)
// Các view khác KHÔNG import file này: chúng đọc MACHINE / PREFS trong core/config.js.
// (Ngôn ngữ và sáng/tối ở khối "Giao diện chung" do app.js lo vì phải chạy trước mọi view.)
import { api, ApiError } from "../core/api.js";
import { MACHINE, PREFS } from "../core/config.js";
import { t } from "../core/i18n.js";
import { subscribe, setPollInterval, firmwareLabel, isConnected, isStale } from "../core/state.js";

export function initSettings() {
    initConnection();
    initBehavior();
    initFirmwareInfo();
    initMachineConfig();
}

/* ==================== 1. KẾT NỐI MÁY (sim / cổng COM) ==================== */
function initConnection() {
    const form = document.getElementById("connection-form");
    const modeSelect = document.getElementById("connection-mode");
    const portSelect = document.getElementById("serial-port");
    const baudSelect = document.getElementById("serial-baud");
    const refreshButton = document.getElementById("refresh-ports-btn");
    const connectButton = document.getElementById("connect-btn");
    const disconnectButton = document.getElementById("disconnect-btn");
    const help = document.getElementById("connection-help");

    if (
        !form || !modeSelect || !portSelect || !baudSelect ||
        !refreshButton || !connectButton || !disconnectButton || !help
    ) {
        console.error("Không tìm thấy đầy đủ phần tử kết nối trong HTML.");
        return;
    }

    let busy = false;
    let backendAvailable = false;
    let connected = false;
    let currentMode = null;
    let lastActionAt = 0;

    const originalPortOption = portSelect.options[0]?.cloneNode(true);

    function setMessage(key, fallback) {
        const translated = t(key);
        help.textContent =
            translated && translated !== key ? translated : fallback;
    }

    function setBusy(value) {
    busy = value;
    if (!value) lastActionAt = Date.now();
    updateControls();
}

    function updateControls() {
        const isSerial = modeSelect.value === "serial";

        modeSelect.disabled = busy || connected;
        portSelect.disabled =
            busy || connected || !backendAvailable ||
            !isSerial || portSelect.options.length <= 1;

        baudSelect.disabled = busy || connected || !isSerial;
        refreshButton.disabled = busy || !backendAvailable || !isSerial;
        connectButton.disabled = busy || connected || !backendAvailable;
        disconnectButton.disabled = busy || !connected;
    }

    function showError(error) {
        console.error("Lỗi kết nối:", error);

        const code = error instanceof ApiError ? error.code : "";
        const keys = {
            backend_unreachable: [
                "error.backendUnavailable",
                "Không thể kết nối backend."
            ],
            already_connected: [
                "error.already_connected",
                "Bộ điều khiển đã được kết nối."
            ],
            not_connected: [
                "error.not_connected",
                "Bộ điều khiển chưa được kết nối."
            ],
            link_error: [
                "error.link_error",
                "Không thể mở cổng kết nối hoặc kết nối đã bị mất."
            ],
            pyserial_missing: [
                "error.pyserial_missing",
                "Backend chưa có thư viện pyserial."
            ],
            validation_error: [
                "error.validation",
                "Dữ liệu kết nối không hợp lệ."
            ]
        };

        const [key, fallback] = keys[code] || [
            "error.connectionFailed",
            "Kết nối thất bại. Hãy kiểm tra backend và cấu hình."
        ];

        setMessage(key, fallback);
    }

    function updateConnectionDisplay(data) {
        // Chỉ cập nhật khi API thực sự trả về trạng thái kết nối.
        if (!data || typeof data !== "object") return;

        const isConnected =
            data.connected ??
            data.is_connected ??
            data.connection?.connected;

        if (typeof isConnected !== "boolean") return;

        connected = isConnected;

        const mode =
            data.mode ??
            data.connection?.mode ??
            currentMode;

        if (connected) {
            currentMode = mode;
            if (mode === "sim" || mode === "serial") {
                modeSelect.value = mode;
            }
            setMessage(
                "settings.connection.connected",
                `Đã kết nối${mode ? ` (${mode})` : ""}.`
            );
        } else {
            currentMode = null;
            setMessage(
                "settings.connection.disconnected",
                "Chưa kết nối bộ điều khiển."
            );
        }

        updateControls();
    }

    function syncFromState(snapshot) {
        // Chưa có kết quả thăm dò đầu tiên, hoặc đang/vừa bấm nút: bỏ qua
        // để không ghi đè kết quả của thao tác bằng dữ liệu thăm dò cũ.
        if (!snapshot.backendOnline && !snapshot.error) return;
        if (busy || Date.now() - lastActionAt < 800) return;

        const wasAvailable = backendAvailable;
        const wasConnected = connected;
        const connection = snapshot.status?.connection;

        backendAvailable = snapshot.backendOnline;
        connected = backendAvailable && connection?.connected === true;

        if (connected && (connection.mode === "sim" || connection.mode === "serial")) {
            currentMode = connection.mode;
            modeSelect.value = connection.mode;
        }
        if (!connected) currentMode = null;

        // Chỉ đổi thông báo khi trạng thái thật sự đổi, để không ghi đè mỗi 0,4 giây.
        if (!backendAvailable) {
            if (wasAvailable) {
                setMessage("error.backendUnavailable", "Không thể kết nối backend.");
            }
        } else if (!wasAvailable || connected !== wasConnected) {
            setMessage(
                connected
                    ? "settings.connection.connected"
                    : "settings.connection.disconnected",
                connected ? "Đã kết nối." : "Chưa kết nối bộ điều khiển."
            );
        }

        updateControls();
    }

    async function checkBackend() {
        try {
            await api.health();
            backendAvailable = true;
            return true;
        } catch (error) {
            backendAvailable = false;
            connected = false;
            currentMode = null;
            showError(error);
            updateControls();
            return false;
        }
    }

    async function loadPorts() {
        if (busy || !backendAvailable) return;

        refreshButton.disabled = true;

        try {
            const result = await api.ports();

            // Hỗ trợ phản hồi dạng mảng hoặc {ports: [...]}
            const ports = Array.isArray(result)
                ? result
                : Array.isArray(result?.ports)
                    ? result.ports
                    : null;

            if (!ports) {
                throw new Error("API danh sách cổng không đúng định dạng.");
            }

            portSelect.replaceChildren();

            if (ports.length === 0) {
                const option = document.createElement("option");
                option.value = "";
                option.textContent = t("settings.connection.noPort");
                portSelect.append(option);
            } else {
                for (const item of ports) {
                    const device =
                        typeof item === "string"
                            ? item
                            : item?.device ?? item?.port ?? item?.name;

                    if (typeof device !== "string" || !device) continue;

                    const option = document.createElement("option");
                    option.value = device;

                    const description =
                        typeof item === "object"
                            ? item.description
                            : null;

                    option.textContent = description
                        ? `${device} — ${description}`
                        : device;

                    portSelect.append(option);
                }

                if (portSelect.options.length === 0) {
                    const option = document.createElement("option");
                    option.value = "";
                    option.textContent = t("settings.connection.noPort");
                    portSelect.append(option);
                }
            }

            setMessage(
                "settings.connection.portsLoaded",
                `Đã tải danh sách cổng: ${portSelect.options.length} mục.`
            );
        } catch (error) {
                    if (error instanceof ApiError) {
                    showError(error);
                } else {
                    setMessage("settings.connection.portsFailed", "Không thể tải danh sách cổng COM.");
                }
        } finally {
            updateControls();
        }
    }

    async function refreshConnection() {
        try {
            const result = await api.connection();
            updateConnectionDisplay(result);
        } catch (error) {
            console.error("Không thể đọc trạng thái kết nối:", error);
            // Không tự giả định đã kết nối nếu API không đọc được.
        }
    }

    modeSelect.addEventListener("change", async () => {
        updateControls();

        if (modeSelect.value === "serial" && backendAvailable) {
            await loadPorts();
        } else {
            setMessage(
                "settings.connection.help",
                "Hãy kiểm tra chế độ và cổng kết nối trước khi điều khiển máy thật."
            );
        }
    });

    refreshButton.addEventListener("click", loadPorts);

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        if (busy || connected) return;

        setBusy(true);

        try {
            if (!await checkBackend()) return;

            const mode = modeSelect.value;
            const port = mode === "serial" ? portSelect.value : null;
            const baud = Number(baudSelect.value);

            if (mode === "serial" && !port) {
                setMessage(
                    "settings.connection.selectPort",
                    "Hãy chọn cổng COM trước khi kết nối."
                );
                return;
            }

            if (!Number.isFinite(baud) || baud <= 0) {
                setMessage(
                    "settings.connection.invalidBaud",
                    "Baud rate không hợp lệ."
                );
                return;
            }

            // Dùng đúng API hiện có; không tự tạo endpoint.
            const result = await api.connect(mode, port, baud);

            updateConnectionDisplay(result);

            // Một số backend có thể trả về phản hồi không chứa trạng thái.
            // Đọc lại trạng thái thật trước khi kết luận.
            await refreshConnection();

            if (!connected) {
                setMessage(
                    "settings.connection.verifyFailed",
                    "Backend đã nhận yêu cầu nhưng chưa xác nhận trạng thái kết nối."
                );
            }
        } catch (error) {
            showError(error);
        } finally {
            setBusy(false);
        }
    });

    disconnectButton.addEventListener("click", async () => {
        if (busy || !connected) return;

        setBusy(true);

        try {
            await api.disconnect();
            await refreshConnection();

            if (connected) {
                setMessage(
                    "settings.connection.disconnectVerifyFailed",
                    "Đã gửi yêu cầu ngắt kết nối nhưng backend chưa xác nhận."
                );
            }
        } catch (error) {
            showError(error);
            await refreshConnection();
        } finally {
            setBusy(false);
        }
    });

    // Khởi tạo trạng thái thật từ backend.
    updateControls();

    void (async () => {
        if (await checkBackend()) {
            await refreshConnection();

            if (modeSelect.value === "serial") {
                await loadPorts();
            }
        }
        subscribe(syncFromState);
        updateControls();
    })();
}

/* ==================== 2. HOẠT ĐỘNG (lưu ở trình duyệt -> PREFS) ==================== */
const PREFS_KEY = "extruxy-prefs-v1";
const POLL_CHOICES = [300, 500, 1000];

// Đọc tùy chọn đã lưu vào PREFS; giá trị lạ thì giữ mặc định trong config.js.
function loadPrefs() {
    let saved = {};
    try {
        saved = JSON.parse(localStorage.getItem(PREFS_KEY) ?? "{}") ?? {};
    } catch { /* hỏng hoặc bị chặn: dùng mặc định */ }
    if (POLL_CHOICES.includes(Number(saved.pollMs))) PREFS.pollMs = Number(saved.pollMs);
    if (typeof saved.confirmHome === "boolean") PREFS.confirmHome = saved.confirmHome;
    if (typeof saved.shortcuts === "boolean") PREFS.shortcuts = saved.shortcuts;
}

function savePref(key, value) {
    PREFS[key] = value;
    try {
        localStorage.setItem(PREFS_KEY, JSON.stringify(PREFS));
    } catch { /* trình duyệt chặn lưu: vẫn dùng trong phiên này */ }
}

function initBehavior() {
    const poll = document.getElementById("poll-interval");
    const confirmHome = document.getElementById("confirm-home");
    const shortcuts = document.getElementById("shortcuts-enabled");

    loadPrefs();
    setPollInterval(PREFS.pollMs);
    if (poll) poll.value = String(PREFS.pollMs);
    if (confirmHome) confirmHome.value = PREFS.confirmHome ? "on" : "off";
    if (shortcuts) shortcuts.value = PREFS.shortcuts ? "on" : "off";

    poll?.addEventListener("change", () => {
        const ms = Number(poll.value);
        if (!POLL_CHOICES.includes(ms)) return;
        savePref("pollMs", ms);
        setPollInterval(ms);
    });
    confirmHome?.addEventListener("change", () => savePref("confirmHome", confirmHome.value === "on"));
    shortcuts?.addEventListener("change", () => savePref("shortcuts", shortcuts.value === "on"));
}

/* ==================== 3. CẤU HÌNH MÁY ==================== */
// Gộp hai nguồn:
//   "Máy": YAML trên mạch, backend đọc/ghi qua serial (/api/machine/config).
//   "App": hồ sơ phần mềm ở backend (/api/profile): Z bút 3 nấc, tốc độ bút, bước jog tối đa.
// Hồ sơ được ghi vào MACHINE (core/config.js) rồi phát `extruxy:profile-changed`,
// nên control.js / preview.js tự dùng giá trị mới mà không cần import file này.

const PROFILE_TO_MACHINE = {
    pen_up_z: "penUpZ", pen_mid_z: "penMidZ", pen_down_z: "penDownZ",
    pen_feed: "penFeed", jog_max_step: "jogMaxStep"
};
let profileLimits = null;           // {khóa: [min, max]} do backend trả về

const currentProfile = () => Object.fromEntries(
    Object.entries(PROFILE_TO_MACHINE).map(([key, field]) => [key, MACHINE[field]]));

function applyProfile(result) {
    const profile = result?.profile ?? {};
    for (const [key, field] of Object.entries(PROFILE_TO_MACHINE)) {
        if (Number.isFinite(profile[key])) MACHINE[field] = profile[key];
    }
    profileLimits = result?.limits ?? profileLimits;
    window.dispatchEvent(new CustomEvent("extruxy:profile-changed", { detail: currentProfile() }));
}

// Backend chưa chạy: giữ giá trị mặc định trong config.js.
async function loadProfile() {
    try {
        applyProfile(await api.profile());
    } catch (error) {
        console.warn("Chưa đọc được hồ sơ máy, dùng giá trị mặc định:", error);
    }
}

async function saveProfile(partial) {
    applyProfile(await api.profileSave({ ...currentProfile(), ...partial }));
}

// Firmware: lấy từ banner hoặc dòng [VER:...] của $I (state.firmwareLabel).
function initFirmwareInfo() {
    const firmware = document.getElementById("settings-firmware-version");
    if (!firmware) return;
    subscribe(() => {
        firmware.textContent = isConnected()
            ? (firmwareLabel() ?? t("common.status.unknown"))
            : t("common.status.disconnected");
    });
}

const GROUPS = ["x", "y", "z", "general"];
const APP_FIELDS = [
    { key: "pen_up_z", group: "z", unit: "mm" },
    { key: "pen_mid_z", group: "z", unit: "mm" },
    { key: "pen_down_z", group: "z", unit: "mm" },
    { key: "pen_feed", group: "z", unit: "mm/min" },
    { key: "jog_max_step", group: "general", unit: "mm" }
];
const Z_TRAVEL = "axes/z/max_travel_mm";

// "axes/x/homing/seek_mm_per_min" -> khóa dịch "mc.field.homing.seek_mm_per_min"
const boardLabelKey = (path) => `mc.field.${path.replace(/^axes\/[xyz]\//, "").replaceAll("/", ".")}`;
const show = (value) => (Number.isFinite(value) ? String(Number(value.toFixed(6))) : "");

function initMachineConfig() {
    const $ = (id) => document.getElementById(id);
    const groupsBox = $("mc-groups");
    const status = $("mc-status");
    const readBtn = $("mc-read-btn");
    const applyBtn = $("mc-apply-btn");
    const saveBtn = $("mc-save-btn");
    const revertBtn = $("mc-revert-btn");
    const modal = $("custom-config-save-modal");
    if (!groupsBox || !status || !readBtn || !applyBtn || !saveBtn || !revertBtn) return;

    let board = null;            // kết quả /api/machine/config gần nhất (null: chưa đọc)
    let busy = false;
    let snapshot = null;
    let readFor = null;          // phiên kết nối đã tự đọc cấu hình

    const setStatus = (text, kind = "") => {
        status.textContent = text;
        status.className = `mc-status${kind ? ` is-${kind}` : ""}`;
    };
    const errorText = (error) => (error instanceof ApiError ? error.message : String(error));

    /* --- vẽ các ô --- */
    function row({ kind, id, label, unit, min, max, integer }) {
        const wrap = document.createElement("label");
        wrap.className = "mc-row";
        wrap.dataset.kind = kind;
        wrap.dataset.id = id;

        const name = document.createElement("span");
        name.className = "mc-label";
        const text = document.createElement("span");
        text.textContent = label;
        name.append(text);
        if (kind === "app") {           // mục trên mạch là đa số: không gắn nhãn cho đỡ rối
            const badge = document.createElement("span");
            badge.className = "mc-badge mc-badge-app";
            badge.textContent = t("mc.badge.app");
            name.append(badge);
        }

        const input = document.createElement("input");
        input.type = "number";
        input.inputMode = "decimal";
        input.step = integer ? "1" : "any";
        if (Number.isFinite(min)) input.min = String(min);
        if (Number.isFinite(max)) input.max = String(max);
        input.addEventListener("input", refreshState);

        const unitEl = document.createElement("span");
        unitEl.className = "mc-unit";
        unitEl.textContent = unit;

        const flag = document.createElement("span");
        flag.className = "mc-flag";
        flag.title = t("mc.legend.unsaved");
        flag.textContent = "●";

        wrap.append(name, input, unitEl, flag);
        return wrap;
    }

    function render() {
        const fields = board?.fields ?? [];
        groupsBox.replaceChildren();
        for (const group of GROUPS) {
            const set = document.createElement("fieldset");
            set.className = "mc-group";
            const legend = document.createElement("legend");
            legend.textContent = t(`mc.group.${group}`);
            set.append(legend);
            for (const f of fields.filter((item) => item.group === group)) {
                set.append(row({ kind: "board", id: f.path, label: t(boardLabelKey(f.path)),
                    unit: f.unit, min: f.min, max: f.max, integer: f.integer }));
            }
            for (const f of APP_FIELDS.filter((item) => item.group === group)) {
                const [min, max] = profileLimits?.[f.key] ?? [];
                set.append(row({ kind: "app", id: f.key, label: t(`mc.field.${f.key}`),
                    unit: f.unit, min, max }));
            }
            groupsBox.append(set);
        }
        fillInputs();
    }

    const rows = () => [...groupsBox.querySelectorAll(".mc-row")];
    const original = (r) => (r.dataset.kind === "board"
        ? board?.values?.[r.dataset.id]
        : currentProfile()[r.dataset.id]);

    function fillInputs() {
        for (const r of rows()) {
            r.querySelector("input").value = show(original(r));
        }
        refreshState();
    }

    function edits(kind) {
        const out = {};
        for (const r of rows().filter((item) => item.dataset.kind === kind)) {
            const raw = r.querySelector("input").value.trim();
            const value = Number(raw);
            if (raw === "" || !Number.isFinite(value)) continue;
            const before = original(r);
            if (!Number.isFinite(before) || Math.abs(value - before) > 1e-9) out[r.dataset.id] = value;
        }
        return out;
    }

    /* --- bật/tắt theo trạng thái máy --- */
    function boardBlockReason() {
        const s = snapshot?.status;
        if (!isConnected() || isStale()) return t("mc.block.notConnected");
        const job = s.job?.state;
        if (job === "running" || job === "finishing") return t("mc.block.job");
        if (s.stopping) return t("mc.block.stopping");
        if (!["Idle", "Alarm"].includes(s.machine?.state)) return t("mc.block.notIdle");
        if (s.connection?.mode === "serial" && !s.connection?.motion_unlocked) return t("mc.block.locked");
        return null;
    }

    function refreshState() {
        const blocked = boardBlockReason();
        const canRead = isConnected() && !isStale() && !busy;
        const boardEdits = edits("board");
        const appEdits = edits("app");
        const unsaved = new Set(board?.unsaved ?? []);

        for (const r of rows()) {
            const isBoard = r.dataset.kind === "board";
            const input = r.querySelector("input");
            input.disabled = busy || (isBoard && (!board || !isConnected()));
            r.classList.toggle("is-dirty", r.dataset.id in (isBoard ? boardEdits : appEdits));
            r.classList.toggle("is-unsaved", isBoard && unsaved.has(r.dataset.id));
        }

        const dirty = Object.keys(boardEdits).length + Object.keys(appEdits).length;
        readBtn.disabled = !canRead;
        revertBtn.disabled = busy || dirty === 0;
        applyBtn.disabled = busy || dirty === 0 || (Object.keys(boardEdits).length > 0 && blocked !== null);
        // Chỉ lưu khi máy đang chạy giá trị khác tệp và không còn ô "Máy" chưa áp dụng.
        saveBtn.disabled = busy || blocked !== null || unsaved.size === 0 || Object.keys(boardEdits).length > 0;
        $("mc-file").textContent = board?.file ?? "—";
        return blocked;
    }

    /* --- kiểm tra trước khi gửi (backend vẫn kiểm lại) --- */
    function validateEdits(boardEdits, appEdits) {
        const pen = { ...currentProfile(), ...appEdits };
        if (!(pen.pen_down_z < pen.pen_mid_z && pen.pen_mid_z < pen.pen_up_z)) return t("mc.err.penOrder");
        const zTravel = boardEdits[Z_TRAVEL] ?? board?.values?.[Z_TRAVEL];
        if (Number.isFinite(zTravel) && (pen.pen_up_z > zTravel || pen.pen_down_z < 0)) {
            return `${t("mc.err.penTravel")} (0–${show(zTravel)} mm)`;
        }
        return null;
    }

    /* --- thao tác --- */
    async function run(task) {
        busy = true;
        refreshState();
        try {
            await task();
        } catch (error) {
            setStatus(errorText(error), "error");
        } finally {
            busy = false;
            refreshState();
        }
    }

    function useBoard(result) {
        board = result;
        const x = result?.values?.["axes/x/max_travel_mm"];
        const y = result?.values?.["axes/y/max_travel_mm"];
        if (Number.isFinite(x)) MACHINE.travelX = x;      // kiểm vượt vùng khi chạy tệp
        if (Number.isFinite(y)) MACHINE.travelY = y;
        render();
    }

    const readBoard = () => run(async () => {
        setStatus(t("mc.reading"));
        useBoard(await api.machineConfig());
        setStatus(board.unsaved.length ? t("mc.readUnsaved") : t("mc.readOk"),
            board.unsaved.length ? "" : "success");
    });

    readBtn.addEventListener("click", readBoard);

    revertBtn.addEventListener("click", () => {
        fillInputs();
        setStatus("");
    });

    applyBtn.addEventListener("click", () => {
        const boardEdits = edits("board");
        const appEdits = edits("app");
        const problem = validateEdits(boardEdits, appEdits);
        if (problem) { setStatus(problem, "error"); return; }
        run(async () => {
            const done = [];
            if (Object.keys(appEdits).length) {
                await saveProfile(appEdits);
                done.push(t("mc.appliedApp"));
            }
            if (Object.keys(boardEdits).length) {
                setStatus(t("mc.applying"));
                const result = await api.machineConfigApply(boardEdits);
                useBoard(result);
                if (result.failed?.length) {
                    throw new Error(`${t("mc.err.notConfirmed")} ${result.failed.map((f) => f.path).join(", ")}`);
                }
                done.push(t("mc.appliedBoard"));
            }
            fillInputs();
            setStatus(done.join(" "), "success");
        });
    });

    saveBtn.addEventListener("click", () => {
        if (!modal) return;
        $("modal-config-file").textContent = board?.file ?? "—";
        $("modal-config-changes").textContent = (board?.unsaved ?? [])
            .map((path) => `${t(boardLabelKey(path))} (${path.split("/")[1]?.toUpperCase() ?? ""})`)
            .join(", ") || "—";
        modal.hidden = false;
        $("modal-config-cancel-btn")?.focus();
    });
    $("modal-config-cancel-btn")?.addEventListener("click", () => { modal.hidden = true; });
    $("modal-config-confirm-btn")?.addEventListener("click", () => {
        modal.hidden = true;
        run(async () => {
            setStatus(t("mc.saving"));
            const result = await api.machineConfigSave();
            useBoard(await api.machineConfig());
            setStatus(`${result.verified ? t("mc.savedOk") : t("mc.savedMismatch")} ${t("mc.backupAt")} ${result.backup}`,
                result.verified ? "success" : "error");
        });
    });

    window.addEventListener("extruxy:profile-changed", () => { if (!busy) render(); });
    loadProfile();

    subscribe((state) => {
        snapshot = state;
        const connection = state.status?.connection;
        const key = isConnected() ? `${connection.mode}:${connection.port}` : null;
        if (key === null) {
            if (board) { board = null; render(); }
            readFor = null;
        } else if (readFor !== key && !isStale() && !busy) {
            // Tự đọc một lần mỗi phiên kết nối (chỉ đọc, được phép cả khi máy đang khóa).
            const job = state.status?.job?.state;
            if (job !== "running" && job !== "finishing" && !state.status?.stopping) {
                readFor = key;
                readBoard();
            }
        }
        const blocked = refreshState();
        if (!busy && board && blocked && !status.textContent) setStatus(blocked);
    });

    render();
}
