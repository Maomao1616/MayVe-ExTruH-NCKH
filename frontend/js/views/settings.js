import { api, ApiError } from "../api.js";
import { subscribe } from "../state.js";
import { t } from "../i18n.js";

export function initSettings() {
    initConnection();
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
