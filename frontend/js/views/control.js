   import { t, getLanguage } from "../i18n.js";
   import { subscribe } from "../state.js";
   import { api } from "../api.js";

    export function initControl() {
            initStatusPanel(); 
    }

 /* ==================== GIÁM SÁT TRẠNG THÁI THẬT ==================== */
    function initStatusPanel() {
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

        const codeText = (prefix, item) => {
        if (item?.code == null) return "—";
        const key = `${prefix}.${item.code}`;
        const text = t(key);
        return text === key
            ? `${prefix.toUpperCase()} ${item.code}`
            : `${text} (${item.code})`;
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

            // Alarm chỉ có ý nghĩa khi máy đang ở trạng thái Alarm (backend không tự xóa last_alarm).
            setText("last-alarm",
                        machineState === "Alarm" ? codeText("alarm", status.last_alarm) : "—");

                    const lastError = status.last_error;
            setText("last-error", lastError?.code == null
                        ? "—"
                        : `${codeText("error", lastError)} · ${formatTime(lastError.at * 1000)}`);

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

            subscribe((snapshot) => {
            displayStatus(snapshot);
        });
        }




