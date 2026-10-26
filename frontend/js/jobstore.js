// jobstore.js — tệp G-code đang nạp ở trình duyệt. jobs.js ghi, preview.js đọc.
// Chỉ giữ dữ liệu, không đụng DOM, không gọi mạng.

export const store = {
    file: null,         // { name, parsed } (parsed: kết quả parseGcode) hoặc null
    previewToken: 0     // tăng mỗi khi người dùng bấm "Xem trước"
};

const listeners = new Set();

function notify() {
    for (const listener of listeners) {
        try { listener(store); } catch (error) { console.error("Job store listener:", error); }
    }
}

export function setFile(file) {
    store.file = file;
    notify();
}

export function requestPreview() {
    store.previewToken += 1;
    notify();
}

export function subscribeStore(listener) {
    listeners.add(listener);
    listener(store);
    return () => listeners.delete(listener);
}
