
   
export function initJobs  () {
    initRunModeSwitch();
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