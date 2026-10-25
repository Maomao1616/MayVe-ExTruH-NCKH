
import {
    setLanguage,
    getLanguage,
    t,
    applyTranslations
} from "./i18n.js";

import { startPolling, subscribe, state } from "./state.js";

import { api, ApiError } from "./api.js";

async function initApp() {
    try {
        initTabs();
        await initLanguageSelector();
        initThemeSelector();
        initConnection();
        initRunModeSwitch();

        
        console.log("ExtruXY đã khởi động.");
        console.log("Ngôn ngữ hiện tại:", getLanguage());
        console.log("Kiểm tra i18n:", t("nav.control"));

        startPolling();
        initLiveDashboard();
        initTerminalAndSafetyControls();
        
    } catch (error) {
        console.error("Không thể khởi tạo ExtruXY:", error);
    }
}

initApp();

/* ==================== TAB ==================== */
function initTabs() {
    const tabs = document.querySelectorAll(".nav-tab");
    const panels = document.querySelectorAll(".tab-panel");

    tabs.forEach((tab) => {
        tab.addEventListener("click", (event) => {
            const targetSelector = tab.getAttribute("href");

            if (!targetSelector?.startsWith("#")) return;

            const targetPanel = document.querySelector(targetSelector);
            if (!targetPanel) return;

            event.preventDefault();

            tabs.forEach((item) => {
                item.classList.remove("is-active");
                item.setAttribute("aria-selected", "false");
            });

            panels.forEach((panel) => {
                panel.classList.remove("is-active");
            });

            tab.classList.add("is-active");
            tab.setAttribute("aria-selected", "true");
            targetPanel.classList.add("is-active");

            history.replaceState(null, "", targetSelector);
        });
    });
}

/* ==================== NGÔN NGỮ ==================== */
async function initLanguageSelector() {
    const selector = document.getElementById("language-select");
    if (!selector) return;

    const savedLanguage = localStorage.getItem("extruxy-language");
    const language = savedLanguage === "en" ? "en" : "vi";

    try {
        await setLanguage(language);
        selector.value = language;
        applyTranslations();

        selector.addEventListener("change", async () => {
            try {
                const selectedLanguage =
                    selector.value === "en" ? "en" : "vi";

                await setLanguage(selectedLanguage);
                localStorage.setItem(
                    "extruxy-language",
                    selectedLanguage
                );
                applyTranslations();
            } catch (error) {
                console.error("Không thể đổi ngôn ngữ:", error);
            }
        });
    } catch (error) {
        console.error("Không thể khởi tạo ngôn ngữ:", error);
    }
}

/* ==================== THEME ==================== */
function initThemeSelector() {
    const selector = document.getElementById("theme-select");
    if (!selector) return;

    const savedTheme = localStorage.getItem("extruxy-theme") || "dark";

    document.documentElement.dataset.theme = savedTheme;
    selector.value = savedTheme;

    selector.addEventListener("change", () => {
        const theme = selector.value === "light" ? "light" : "dark";

        document.documentElement.dataset.theme = theme;
        localStorage.setItem("extruxy-theme", theme);
    });
}

/* ==================== KẾT NỐI BACKEND ==================== */
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

    const originalPortOption = portSelect.options[0]?.cloneNode(true);

    function setMessage(key, fallback) {
        const translated = t(key);
        help.textContent =
            translated && translated !== key ? translated : fallback;
    }

    function setBusy(value) {
        busy = value;
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
            console.error("Không thể tải danh sách cổng:", error);
            setMessage(
                "settings.connection.portsFailed",
                "Không thể tải danh sách cổng COM."
            );
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
        updateControls();
    })();
}


/* ==================== GIÁM SÁT TRẠNG THÁI THẬT ==================== */
function initLiveDashboard() {
    const $ = (id) => document.getElementById(id);

    const formatNumber = (value) => {
        if (value === null || value === undefined || value === "") {
            return "—";
        }

        const number = Number(value);
        return Number.isFinite(number)
            ? number.toFixed(3)
            : "—";
    };

    const setText = (id, value) => {
        const element = $(id);
        if (element) element.textContent = value;
    };

    const formatTime = (timestamp) => {
        if (!Number.isFinite(timestamp)) return "—";

        return new Date(timestamp).toLocaleTimeString(
            getLanguage() === "en" ? "en-GB" : "vi-VN"
        );
    };

    const displayStatus = (snapshot) => {
        const status = snapshot.status;
        const machine = status?.machine;
        const connection = status?.connection;

        // Backend lỗi: không để số liệu cũ trông như dữ liệu trực tiếp.
        if (!snapshot.backendOnline || !status || !machine) {
            for (const id of [
                "workspace-x", "workspace-y", "workspace-z",
                "machine-x", "machine-y", "machine-z",
                "machine-feed", "planner-free", "rx-free",
                "last-update-time"
            ]) {
                setText(id, "—");
            }

            setText(
                "controller-state",
                t("common.status.unavailable") !== "common.status.unavailable"
                    ? t("common.status.unavailable")
                    : "Backend không khả dụng"
            );

            setText(
                "coordinate-source",
                t("common.status.noData") || "Chưa có dữ liệu"
            );

            setText("terminal-connection-label", "—");
            return;
        }

        const connected = connection?.connected === true;

        // GRBL thường cung cấp mpos, wpos và wco dưới dạng mảng XYZ.
        const mpos = Array.isArray(machine.mpos) ? machine.mpos : null;
        const wpos = Array.isArray(machine.wpos) ? machine.wpos : null;

        ["x", "y", "z"].forEach((axis, index) => {
            setText(
                `machine-${axis}`,
                mpos ? formatNumber(mpos[index]) : "—"
            );

            setText(
                `workspace-${axis}`,
                wpos ? formatNumber(wpos[index]) : "—"
            );
        });

        const machineState =
            machine.state ?? machine.status ?? null;

        setText(
            "controller-state",
            machineState == null ? "—" : String(machineState)
        );

        setText(
            "machine-feed",
            machine.feed == null
                ? "—"
                : `${formatNumber(machine.feed)} mm/min`
        );

        setText(
            "planner-free",
            machine.planner_free == null
                ? "—"
                : String(machine.planner_free)
        );

        setText(
            "rx-free",
            machine.rx_free == null
                ? "—"
                : String(machine.rx_free)
        );

        setText(
            "homed-indicator",
            typeof status.homed_guess === "boolean"
                ? (
                    status.homed_guess
                        ? (getLanguage() === "en" ? "Yes (estimated)" : "Có (ước đoán)")
                        : (getLanguage() === "en" ? "No / unconfirmed" : "Chưa xác nhận")
                )
                : (getLanguage() === "en" ? "Unknown" : "Chưa biết")
        );

        setText(
            "last-alarm",
            status.last_alarm == null ? "—" : String(status.last_alarm)
        );

        setText(
            "last-error",
            status.last_error == null ? "—" : String(status.last_error)
        );

        setText("last-update-time", formatTime(snapshot.lastUpdatedAt));

        setText(
            "coordinate-source",
            connected
                ? (getLanguage() === "en" ? "Live data" : "Dữ liệu trực tiếp")
                : (getLanguage() === "en" ? "Disconnected" : "Chưa kết nối")
        );

        const modeLabel = $("active-connection-mode");
        if (modeLabel) {
            const modeText = connected
                ? (connection.mode === "sim"
                    ? (getLanguage() === "en" ? "Simulation" : "Mô phỏng")
                    : connection.mode === "serial"
                        ? (getLanguage() === "en" ? "Serial" : "Cổng nối tiếp")
                        : (connection.mode ?? "Connected"))
                : (getLanguage() === "en" ? "Disconnected" : "Chưa kết nối");

            modeLabel.textContent = modeText;
        }

        setText(
            "terminal-connection-label",
            connected
                ? (getLanguage() === "en" ? "Connected" : "Đã kết nối")
                : (getLanguage() === "en" ? "Disconnected" : "Chưa kết nối")
        );

        const readonlyBanner = $("readonly-banner");
        if (readonlyBanner) {
            readonlyBanner.hidden = !(
                connected &&
                connection.mode === "serial" &&
                connection.motion_unlocked === false
            );
        }

        // Firmware chưa có trong hợp đồng status hiện tại.
        setText("firmware-version", "—");

        // API hiện tại chưa cung cấp tiến trình công việc.
        setText("progress-job-name", t("control.progress.noJob"));
        setText("job-progress-percent", "—");
        setText("job-progress-lines", "—");
        setText("job-progress-eta", "—");

        const progressFill = $("job-progress-fill");
        if (progressFill) progressFill.style.width = "0%";

        const progressTrack = $("job-progress-track");
        if (progressTrack) progressTrack.setAttribute("aria-valuenow", "0");
    };

    const displayLogs = (snapshot) => {
        const terminal = $("terminal-output");
        if (!terminal) return;

        if (!snapshot.backendOnline) {
            terminal.textContent =
                getLanguage() === "en"
                    ? "Backend unavailable. Waiting for connection..."
                    : "Backend không khả dụng. Đang chờ kết nối...";
            return;
        }

        if (!snapshot.logs.length) {
            terminal.textContent =
                getLanguage() === "en"
                    ? "No log entries received yet."
                    : "Chưa nhận được dòng log nào.";
            return;
        }

        terminal.textContent = snapshot.logs.map((entry) => {
            const time = formatTime(
                typeof entry.t === "number"
                    ? entry.t * 1000
                    : Date.parse(entry.t)
            );

            const direction = entry.dir ?? "—";
            const source = entry.source ? ` [${entry.source}]` : "";
            const message = entry.text ?? "";

            return `[${time}] ${direction}${source} ${message}`;
        }).join("\n");

        // Giữ Terminal tự cuộn xuống dòng mới nhất.
        terminal.scrollTop = terminal.scrollHeight;
    };

    subscribe((snapshot) => {
        displayStatus(snapshot);
        displayLogs(snapshot);
    });

    // Nút xóa chỉ xóa log trên màn hình, không xóa log ở backend.
    $("clear-terminal-btn")?.addEventListener("click", () => {
        const terminal = $("terminal-output");
        if (terminal) terminal.textContent = "";
    });
}


/* ==================== TERMINAL VÀ ĐIỀU KHIỂN AN TOÀN ==================== */
function initTerminalAndSafetyControls() {
  const form = document.getElementById('terminal-form');
  const input = document.getElementById('terminal-command');
  const sendButton = document.getElementById('terminal-send-btn');
  const output = document.getElementById('terminal-output');
  const clearButton = document.getElementById('clear-terminal-btn');
  const connectionLabel = document.getElementById('terminal-connection-label');

  const pauseButton = document.getElementById('pause-btn');
  const resumeButton = document.getElementById('resume-btn');
  const resetButton = document.getElementById('reset-btn');
  const unlockButton = document.getElementById('unlock-btn');

  if (!form || !input || !sendButton || !output) {
    console.warn('Terminal: thiếu phần tử HTML cần thiết.');
    return;
  }

  function appendTerminalMessage(message) {
    output.textContent += `${message}\n`;
    output.scrollTop = output.scrollHeight;
  }

  function renderTerminalState(state) {
    const status = state.status;
    const connected = Boolean(
      state.backendOnline &&
      status?.connection?.connected
    );

    const stale = !state.lastUpdatedAt ||
        Date.now() - state.lastUpdatedAt > 2000;
    const canSend = connected && !stale;

    input.disabled = !canSend;
    sendButton.disabled = !canSend;

    if (connectionLabel) {
      connectionLabel.textContent = !state.backendOnline
        ? t('terminal.backendOffline')
        : !connected
          ? t('terminal.notConnected')
          : stale
            ? t('terminal.statusStale')
            : t('terminal.connected');
    }

    const machineState = status?.machine?.state;

    if (pauseButton) {
      pauseButton.disabled = !connected || stale ||
        !['Run', 'Jog'].includes(machineState);
    }

    if (resumeButton) {
      resumeButton.disabled = !connected || stale ||
        machineState !== 'Hold';
    }

    if (resetButton) {
      resetButton.disabled = !connected;
    }

    if (unlockButton) {
      unlockButton.disabled = !connected || stale ||
        machineState !== 'Alarm';
    }
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const line = input.value.trim();
    if (!line) return;

    const currentState = state;
    if (
            !currentState.backendOnline ||
            !currentState.status?.connection?.connected
            ) {
            appendTerminalMessage(t('terminal.notConnected'));
            return;
            }

            const stale = !currentState.lastUpdatedAt ||
            Date.now() - currentState.lastUpdatedAt > 2000;

            if (stale) {
            appendTerminalMessage(t('terminal.statusStale'));
            return;
        }

    sendButton.disabled = true;

    try {
      await api.command(line);
      input.value = '';
    } catch (error) {
      let message = t('terminal.sendFailed');

      if (error instanceof ApiError) {
        const translated = t(`error.${error.code}`);

        // Nếu chưa có bản dịch cho mã lỗi, hiển thị mã lỗi
        // để dễ xác định nguyên nhân.
        message = translated || `${t('terminal.sendFailed')} (${error.code})`;
      }

      appendTerminalMessage(message);
    } finally {
      sendButton.disabled = false;
    }
  });

  clearButton?.addEventListener('click', () => {
    output.textContent = '';
  });

  pauseButton?.addEventListener('click', async () => {
    try {
      await api.realtime('hold');
    } catch (error) {
      appendTerminalMessage(t('terminal.sendFailed'));
    }
  });

  resumeButton?.addEventListener('click', async () => {
    try {
      await api.realtime('resume');
    } catch (error) {
      appendTerminalMessage(t('terminal.sendFailed'));
    }
  });

  resetButton?.addEventListener('click', async () => {
    if (!window.confirm(t('safety.confirmReset'))) return;

    try {
      await api.realtime('reset');
    } catch (error) {
      appendTerminalMessage(t('terminal.sendFailed'));
    }
  });

  unlockButton?.addEventListener('click', async () => {
    try {
      await api.command('$X');
    } catch (error) {
      appendTerminalMessage(t('terminal.sendFailed'));
    }
  });

  subscribe((currentState) => {
  renderTerminalState(currentState);
});
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