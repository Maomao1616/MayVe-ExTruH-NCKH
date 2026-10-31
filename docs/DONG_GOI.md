# DONG_GOI — bản mang đi, chuyển máy, cập nhật (Windows)

Dành cho người dùng (không cần biết lập trình) và người đóng gói. MiniPC Ubuntu xem `PLAN_ONLINE.md`.
Ký hiệu: ✅ đã thử · 🧪 chưa thử trên máy sạch.

## 1. Bản mang đi gồm gì
```
ExtruXY/                    (tải từ GitHub sẽ tên là ExtruXY-main/)
├─ Python/                  Python 3.12 embeddable 64-bit + pip + thư viện. KHÔNG lên Git (vài trăm MB)
├─ backend/  frontend/      mã nguồn (lên Git)
├─ launcher/                start.vbs · start.ps1 · stop.vbs · stop.ps1 · tao_bieu_tuong.vbs · cap_nhat.ps1 · icon.ico
├─ data/                    bản thảo, macro, sao lưu cấu hình, hồ sơ. Tự tạo khi chạy lần đầu. KHÔNG lên Git
├─ Cap nhat.bat             cập nhật mã, giữ nguyên Python/ và data/
└─ tools/dong_goi.ps1       (máy phát triển) tạo zip bản cập nhật / bản đầy đủ vào export/
```
Máy dùng **không cần cài Python**, không cần venv, không cần Git. Chỉ chạy trên **Windows 64-bit**.

## 2. Chuẩn bị `Python/` (một lần, trên máy của bạn) ✅
1. Tải *Windows embeddable package (64-bit)* Python **3.12.x** ở python.org, giải nén vào `Python/` (cạnh `backend/`).
2. Sửa `Python/python312._pth` thành đúng 4 dòng:
   ```
   python312.zip
   .
   ..\backend
   import site
   ```
   `..\backend` là bắt buộc: bản embeddable bỏ qua thư mục hiện hành và `PYTHONPATH`; thiếu dòng này thì server và tiến trình con xử lý ảnh (`python -m app.services.drawing.isolated`) không tìm thấy mã. `import site` để Python thấy thư viện trong `Lib\site-packages`.
3. Mở PowerShell ở thư mục gốc. **Đang bật venv cũng được**, miễn là lệnh bắt đầu bằng `.\Python\python.exe` (gõ trần `python`/`pip` sẽ chạy vào venv). Cho chắc: `deactivate` trước.
   ```powershell
   Invoke-WebRequest https://bootstrap.pypa.io/get-pip.py -OutFile .\Python\get-pip.py
   .\Python\python.exe .\Python\get-pip.py
   .\Python\python.exe -m pip install --no-warn-script-location -r backend\requirements.txt
   .\Python\python.exe -c "import fastapi, cv2, vpype; print('ok')"
   ```
   Cảnh báo vàng "Scripts … is not on PATH" bỏ qua được (luôn gọi `python -m pip`). In ra `ok` là xong. Có thể xóa `get-pip.py`.

## 3. Chuyển sang máy Windows khác
Hai cách, chọn một:

| Cách | Gửi gì | Khi nào |
|---|---|---|
| **A. GitHub + zip Python** | Người nhận tải *Code → Download ZIP* trên GitHub; bạn gửi thêm zip thư mục `Python/` (Drive hoặc đính kèm ở GitHub **Releases**) | mã đã push đầy đủ; tiện cập nhật về sau |
| **B. Một zip đầy đủ** | `powershell -ExecutionPolicy Bypass -File tools\dong_goi.ps1 -Kieu daydu` → `export\VMU_PlotterPen_daydu-<ngày>.zip` | gửi một tệp duy nhất, không cần GitHub |

Người nhận làm:
1. **Bỏ chặn zip trước khi giải nén**: chuột phải tệp zip → Properties → tick **Unblock** → OK (làm với mọi zip tải từ mạng). Không làm thì Windows có thể chặn hoặc hỏi cảnh báo khi bấm `.vbs`.
2. Giải nén. Cách A: giải nén zip Python **vào trong** thư mục mã, để `Python\` nằm cạnh `backend\` (tên phải đúng `Python`).
3. Bấm đúp `launcher\tao_bieu_tuong.vbs` **một lần** → có icon **VMU PlotterPen** ngoài Desktop. (Tạo tại chỗ vì icon ghi đường dẫn tuyệt đối; giải nén ở đâu cũng đúng.)
4. Bấm icon. Lần đầu Windows hỏi tường lửa cho `python.exe`: chọn **Mạng riêng tư** (Private).
5. Thử nạp một ảnh ở tab Tạo bản vẽ để chắc phần xử lý ảnh chạy được. 🧪 Máy sạch có thể đòi cài *Microsoft Visual C++ Redistributable* (x64) cho OpenCV.

**Đưa lên GitHub Releases:** trang kho → Releases → *Draft a new release* → đặt tag (vd `v0.2.0`) → kéo thả zip Python (hoặc zip đầy đủ) vào ô đính kèm (tối đa 2 GB/tệp) → Publish. Zip Python chỉ cần tải lại khi đổi phiên bản Python hoặc khi máy người dùng không có Internet để `Cap nhat.bat` tự cài thư viện.

## 4. Dùng hằng ngày
| Việc | Làm gì |
|---|---|
| Bật | Bấm icon. Server chạy ẩn (không có cửa sổ đen), trình duyệt mở `http://<IP LAN>:8000`. Đang chạy rồi thì chỉ mở trình duyệt |
| Tắt | **Không cần**: đóng hết trang 10 phút thì server tự tắt; đang vẽ thì chờ vẽ xong. Chuyển tab / thu nhỏ trình duyệt không làm tắt (trang vẫn báo "còn mở" mỗi 30 s) |
| Tắt ngay | Bấm đúp `launcher\stop.vbs` |
| Máy khác cùng mạng | Mở địa chỉ trình duyệt đang hiện (vd `http://192.168.1.11:8000`). Chỉ dùng ở mạng tin cậy: **chưa có đăng nhập** |
| Đặt PIN mở khóa chuyển động | Mở `launcher\start.ps1`, bỏ `#` ở dòng `$env:EXTRUXY_UNLOCK_PIN = "1234"`, đổi số, lưu; tắt server rồi bật lại |

Cách `start.ps1` chọn IP: card mạng có tuyến ra router ưu tiên cao nhất (giống Windows chọn), bỏ qua `169.254.x.x`; không có mạng thì dùng `localhost`. IP đổi trong lúc server đang chạy → tự mở `localhost`.

## 5. Cập nhật bằng `Cap nhat.bat` ✅
**Người đóng gói (máy của bạn):**
```powershell
powershell -ExecutionPolicy Bypass -File tools\dong_goi.ps1
```
→ `export\VMU_PlotterPen_capnhat-<ngày-giờ>.zip` (khoảng 0,3 MB: `backend/`, `frontend/`, `launcher/`; bỏ `.venv`, `__pycache__`, `tests`).

**Người dùng:**
1. Tải zip bản cập nhật, **Unblock** (mục 3).
2. Chép **nguyên tệp zip, không giải nén** vào thư mục gốc, cạnh `Cap nhat.bat`.
3. Bấm đúp `Cap nhat.bat`, chờ chữ **XONG**, bấm phím bất kỳ để đóng.
4. Bấm icon để chạy bản mới (nhấn Ctrl+F5 trong trình duyệt nếu giao diện còn cũ).

`Cap nhat.bat` làm 5 bước:
| Bước | Việc |
|---|---|
| 1 | Tắt server (nếu đang chạy) |
| 2 | Giải nén zip mới nhất trong thư mục gốc vào thư mục tạm, kiểm có `backend\app\main.py` và `frontend\index.html` |
| 3 | Cất bản đang dùng vào `_ban_cu\` (xóa `_ban_cu` cũ trước) |
| 4 | Thay `backend\`, `frontend\`, `launcher\` cho giống hệt bản mới (tệp thừa bị xóa); **không đụng** `Python\`, `data\`, `backend\.venv`. Chuyển tệp zip đã dùng vào `_ban_cu\` |
| 5 | `requirements.txt` đổi → tự chạy `Python\python.exe -m pip install -r backend\requirements.txt` (**cần Internet**; dùng pip có sẵn trong `Python\`, máy không cần cài Python). Không đổi → bỏ qua |

**Quay lại bản cũ:** tắt server (`launcher\stop.vbs`), xóa `backend\`, `frontend\`, `launcher\`, chép ba thư mục cùng tên trong `_ban_cu\` ra thư mục gốc. Bản mới chạy ổn thì xóa `_ban_cu\` được.

Lưu ý:
- Trong thư mục gốc chỉ nên có **một** zip bản cập nhật (nó lấy tệp mới nhất).
- Nếu bước 5 báo lỗi (mất mạng): bản mới đã chép xong, chỉ thiếu thư viện; nối mạng rồi bấm lại `Cap nhat.bat` hoặc chạy lệnh pip ở mục 2.
- Không có Internet và thư viện đổi: gửi kèm zip `Python/` mới, giải nén đè lên `Python\`.
- `Cap nhat.bat` không tự cập nhật chính nó (cmd đọc tệp .bat dần trong lúc chạy). Bản mới của nó (hiếm khi đổi) chép tay.

## 6. Khi có lỗi
| Hiện tượng | Nguyên nhân / cách xử lý |
|---|---|
| Hộp "Server khong bat len duoc" kèm `No module named ...` | `Python\` thiếu thư viện → chạy lại lệnh pip ở mục 2 |
| `Khong tim thay ...\Python\python.exe` | thư mục `Python` đặt sai chỗ hoặc sai tên (phải nằm cạnh `backend`) |
| Trang báo `bad_host` | mở bằng địa chỉ lạ (tên máy, IP khác): dùng địa chỉ trình duyệt tự mở, hoặc `http://localhost:8000` trên chính máy đó |
| Máy khác không vào được | tường lửa đang chặn `python.exe` (Windows Security → Firewall → Allow an app → tick *Private*), hoặc hai máy khác mạng |
| Bấm `.vbs` bị chặn / hỏi bảo mật | chưa Unblock zip (mục 3) |
| Cổng 8000 bị chương trình khác chiếm | tắt chương trình đó; hoặc sửa `$port` trong `start.ps1` và `stop.ps1` |
| Lỗi khác | xem `data\server-loi.txt` (chỉ ghi lỗi khởi động, ghi đè mỗi lần bật) |

## 7. Ghi chú kỹ thuật (cho người sửa mã)
- Biến môi trường do `start.ps1` đặt: `EXTRUXY_ALLOWED_HOSTS=localhost,127.0.0.1,<IP>`, `EXTRUXY_DATA_DIR=<gốc>\data`, `EXTRUXY_IDLE_EXIT_MIN=10`; uvicorn `--host 0.0.0.0 --port 8000 --no-access-log --log-level warning`, stderr → `data\server-loi.txt`.
- Tự tắt: `backend/app/idle.py` (mỗi yêu cầu HTTP `touch()`, luồng canh 30 s, đang chạy G-code thì không tắt); trang ẩn gửi `/api/health` mỗi 30 s (`frontend/js/core/state.js`). Chạy tay `uvicorn` không đặt biến thì không bao giờ tự tắt.
- `launcher/*.ps1` và `*.vbs` viết **ASCII không dấu** (PowerShell 5.1 đọc UTF-8 không BOM sai dấu tiếng Việt).
- `tools/dong_goi.ps1` ghi zip bằng `ZipArchive` từng tệp với tên dùng `/` (`Compress-Archive` của PowerShell 5.1 ghi `\`, giải nén trên Linux sai cấu trúc).
- `stop.ps1` dùng `taskkill /T` để tắt cả tiến trình con xử lý ảnh.
- ✅ Đã thử (31/10/2026): `Python\` embeddable thật chạy server + nạp ảnh qua tiến trình con; `start.ps1` trong thư mục có dấu cách, lấy đúng IP LAN, máy khác gọi được; tự tắt; `stop.ps1`; đóng gói + `Cap nhat.bat` (giữ `data`, cất bản cũ, dọn tệp thừa). `tao_bieu_tuong.vbs` đã tạo icon trên máy chủ dự án.
- 🧪 Chưa thử: máy sạch không cài gì (Visual C++ của OpenCV), nhánh `pip install` khi `requirements.txt` đổi.
