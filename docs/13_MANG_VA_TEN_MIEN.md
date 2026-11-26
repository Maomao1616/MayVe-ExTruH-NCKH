# 13 — Mạng và tên miền: mở giao diện cho máy khác (Cloudflare Tunnel + mã QR)

> Viết cho người không học mạng. Trạng thái 26/11/2026: **đã chạy thật**: tên miền Active, đường ống `plotter` chạy bằng launcher, chủ dự án mở được giao diện từ điện thoại bằng 4G. Chưa đặt PIN, chưa bật Cloudflare Access.
> Phần chạy trên MiniPC (Docker, USB cố định): [08](08_TRIEN_KHAI.md) mục E, F. Tài liệu này là đường **chạy ngay trên laptop**.

## 1. Bức tranh một dòng

```
Điện thoại / máy khác ──► https://plotter.tenmien.com ──► Cloudflare ══(đường ống)══► laptop: cloudflared ──► phần mềm (cổng 8000)
```

Laptop **tự gọi ra** Cloudflare và giữ một đường ống. Người ngoài vào địa chỉ trên, Cloudflare chuyển qua đường ống về phần mềm. **Không mở cổng router, không cần IP công cộng, có sẵn HTTPS (khóa).**

## 2. Các từ sẽ gặp (lời thường)

| Từ | Nghĩa |
|---|---|
| **Tên miền** (`tenmien.com`) | "Tên nhà" trên Internet. Bạn lấy `.tech` miễn phí 1 năm từ Student Pack; hết năm phải trả tiền gia hạn nếu muốn giữ. |
| **Tên con** (subdomain, `plotter.`) | Phần đứng **trước** tên miền: `plotter.tenmien.com`. Giống một "phòng" trong nhà. Một tên miền tạo được vô số tên con miễn phí. Ta dùng riêng `plotter.` cho máy vẽ, để tên miền gốc còn trống cho việc khác (vd trang giới thiệu). Tên con đặt gì cũng được (`ve.`, `may.`…), miễn **khớp ở mọi chỗ** (mục 5). |
| **DNS** | "Danh bạ" Internet: đổi tên chữ thành địa chỉ máy. |
| **Nameserver** | Máy giữ danh bạ của tên miền bạn. Ta đổi sang của Cloudflare để Cloudflare được tạo mục `plotter.` và nối vào đường ống. |
| **Cloudflare** | Công ty cung cấp đường ống miễn phí (gói Free). |
| **`cloudflared`** | Chương trình nhỏ trên laptop, tạo và giữ đường ống. |
| **Tunnel (đường ống)** | Kết nối do laptop mở **ra ngoài**; vì vậy không cần mở cổng vào. |
| **Host** | Tên người ta gõ để vào. Phần mềm chỉ nhận Host nằm trong danh sách cho phép (chống trang lạ giả mạo); `data\mang.txt` thêm tên của bạn vào danh sách. |

## 3. Đã làm xong những gì

| Việc | Ở đâu |
|---|---|
| Tên miền đưa vào Cloudflare (gói Free) | trang Cloudflare ✅ |
| Đổi nameserver ở nhà đăng ký `.tech` sang `<tên-1>.ns.cloudflare.com` + `<tên-2>.ns.cloudflare.com` | trang nhà đăng ký ✅ (đã lan ra, tên miền Active) |
| Cài `cloudflared` | laptop ✅ |
| Launcher đọc `data\mang.txt` (thêm tên miền, giữ server không tự tắt, bật đường ống, đặt địa chỉ cho QR); `stop` tắt luôn đường ống | `launcher/start.ps1`, `stop.ps1` ✅ (đã chạy thật 24/11/2026, mở được từ 4G) |
| Máy chủ nhận tên miền con dạng `.trycloudflare.com` (dấu chấm đầu = mọi tên con) | `backend/app/main.py` |
| **Nút QR trên header**: hiện 2 mã, địa chỉ Internet và địa chỉ trong mạng nhà (điện thoại cùng Wi-Fi). **Khách cũng thấy nút**, nhưng chỉ nhận mã địa chỉ Internet (IP mạng nhà chỉ cho quản lý). Hộp thoại vừa màn điện thoại, có hiệu ứng mở (tắt khi máy bật chế độ giảm chuyển động) | `api/share.py`, `services/share.py`, `views/share.js`, `polish.css` |

## 4. Các bước đã làm (24/11/2026, tên miền đã **Active**; giữ lại để làm lại ở máy khác)

Tên miền Active khi Cloudflare báo email "is now active" hoặc trang tên miền hiện chữ Active.

**Bước C: tạo đường ống** (PowerShell, mỗi lệnh một lần):
1. `cloudflared tunnel login` → trình duyệt mở ra, chọn tên miền `tenmien.com`, bấm Authorize. Ghi một tệp `cert.pem` vào `%USERPROFILE%\.cloudflared\`.
2. `cloudflared tunnel create plotter` → tạo đường ống tên `plotter`, in ra một **mã dài** (Tunnel ID) và tệp `<mã>.json` (chìa khóa đường ống, **bí mật**, không đưa lên Git hay gửi cho ai).
3. `cloudflared tunnel route dns plotter plotter.tenmien.com` → tạo mục `plotter.` trong danh bạ, trỏ vào đường ống.

**Bước D: tệp cấu hình** `%USERPROFILE%\.cloudflared\config.yml`:
```yaml
tunnel: <mã dài ở bước C2>
credentials-file: C:\Users\ducwt\.cloudflared\<mã dài>.json
ingress:
  - hostname: plotter.tenmien.com
    service: http://localhost:8000
  - service: http_status:404
```
Hai dòng `ingress` nghĩa là: tên `plotter.…` thì chuyển vào phần mềm (cổng 8000), tên khác thì trả 404.

**Tệp `data\mang.txt`** (không lên Git):
```
host=plotter.tenmien.com
url=https://plotter.tenmien.com
giu_bat=1
tunnel=plotter
```
| Dòng | Tác dụng |
|---|---|
| `host=` | thêm tên vào danh sách Host được phép |
| `url=` | địa chỉ hiện ở mã QR Internet |
| `giu_bat=1` | server không tự tắt sau 10 phút đóng trang (có dòng `tunnel=` thì **tự coi như `giu_bat=1`**, nếu không server tắt mà đường ống mồ côi; tắt bằng icon **Tắt**) |
| `tunnel=` | launcher chạy `cloudflared tunnel run plotter` cùng server |

**Bước E: thử.** Tắt rồi bật lại phần mềm bằng icon (launcher chỉ đọc `mang.txt` khi bật server mới). Tắt Wi-Fi trên điện thoại, dùng 4G, quét mã QR "Từ bất kỳ đâu". Lỗi đường ống: `data\tunnel-loi.txt`; lỗi server: `data\server-loi.txt`.

**Chỉ cần thử nhanh, không tên miền** (địa chỉ đổi mỗi lần): `host=.trycloudflare.com` trong `mang.txt`, rồi chạy tay `cloudflared tunnel --url http://localhost:8000` và mở địa chỉ `https://….trycloudflare.com` mà nó in ra.

## 5. Chỗ dễ sai

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| "Host không được phép" (403, `bad_host`) | tên trong `host=` không khớp tên đang gõ; chưa tắt / bật lại launcher |
| Vào được nhưng không đăng nhập được | đang vào bằng `http://` mà không phải `https://`; hoặc PIN chưa đặt (xem mục 6) |
| Không vào được từ 4G, trong nhà vẫn vào | đường ống chưa chạy (`tunnel-loi.txt`), hoặc laptop ngủ |
| Hộp thoại "Đường hầm Cloudflare bị tắt ngay lúc khởi động" (hoặc `tunnel-loi.txt` có `panic` / `0xc0000005`) | cloudflared sập khi khởi động trên máy mượn (25/11/2026, chưa rõ nguyên nhân: USB thiếu dòng, máy quá cũ, hay diệt virus). Launcher đã tự chép `cloudflared.exe` sang thư mục tạm của máy rồi chạy ở đó (loại trừ USB đọc sai) và báo bằng hộp thoại. Kiểm: `Get-FileHash` tệp phải khớp bản chính thức cùng số bản; chạy `cloudflared.exe --version` |
| Chạy được vài phút rồi mất | laptop vào chế độ ngủ: Cài đặt Windows → Nguồn → không ngủ khi cắm sạc |
| QR chỉ hiện "Chưa có địa chỉ" | không bật bằng launcher (icon), hoặc `mang.txt` thiếu dòng `url=` |
| QR mạng nhà không quét được | điện thoại không cùng Wi-Fi; hoặc Windows xếp mạng là Public (đổi sang Private, [08](08_TRIEN_KHAI.md) mục C) |

## 6. An toàn (đọc kỹ)

- Chủ dự án **chọn không bắt buộc PIN** khi mở ra ngoài. Hệ quả: **chưa đặt PIN thì bất kỳ ai có địa chỉ đều là quản lý và mở khóa được máy**, kể cả cho máy chạy G-code. Tên `plotter.…` không bí mật (địa chỉ web bị lộ qua lịch sử, ảnh chụp màn hình, mã QR).
- Máy thật vẫn mặc định **chỉ đọc**; chạy được là sau khi mở khóa chuyển động (tự khóa lại sau 15 phút). Nên **đặt PIN trước khi nhờ người khác thử**: dòng `admin=<số>` và `unlock=<số>` trong `data\pin.txt`.
- Trước khi cho **người ngoài** vào lâu dài, nên bật thêm **Cloudflare Access** (đăng nhập bằng email; có gói miễn phí cho nhóm nhỏ, số người chưa kiểm): lớp khóa thứ hai trước cả PIN. Chưa làm.
- Chìa khóa đường ống (`<mã>.json`, `cert.pem` trong `%USERPROFILE%\.cloudflared\`) nằm **ngoài** thư mục dự án; đừng chép vào repo.

## 7. Tắt

Bấm icon **Tắt**: dừng server và dừng đường ống (chỉ tiến trình `cloudflared` chạy đúng tên trong dòng `tunnel=`, không đụng đường ống khác). Tắt hẳn việc mở ra ngoài: xóa `data\mang.txt` rồi bật lại. Ngắt hẳn từ phía Cloudflare: xóa mục DNS `plotter` hoặc `cloudflared tunnel delete plotter`.

## 8. Giới hạn đã biết

- Laptop phải bật, có mạng và **không ngủ**; MiniPC sẽ thay chỗ này ([08](08_TRIEN_KHAI.md) mục E).
- Mỗi trang hỏi `/api/status` 10 lần/giây: nhiều người cùng xem thì nên giãn nhịp ([08](08_TRIEN_KHAI.md) mục F).
- Đã thử (24/11/2026): mở giao diện từ điện thoại qua 4G thành công. Chưa thử: đăng nhập PIN và thao tác ghi qua tên miền (Origin / cookie), nhiều người cùng lúc, laptop ngủ rồi bật lại.

## 9. Mang theo bằng SSD, dùng máy mượn (ghi 24/11/2026; **làm 25/11/2026: launcher đã chạy được ở máy chính; chưa thử máy thứ hai**)

Bối cảnh: chủ dự án không có laptop, mượn máy; ổ SSD ngoài sau này gắn MiniPC. Làm từ 25/11 (việc: [11](11_VIEC_CAN_LAM.md) mục 4.4).

| Quyết định | Lý do |
|---|---|
| Mỗi máy chỉ **chạy** đường ống `plotter` bằng **chìa khóa `.json`** (không cần `cert.pem`, không đăng nhập tài khoản Cloudflare trên máy mượn) | `cert.pem` chỉ cần khi **tạo** đường ống; chìa khóa cho phép chạy |
| `launcher\cloudflared.exe` mang theo, không cài | máy mượn không cài gì |
| Chìa khóa để ở `data\cloudflared\` (Git bỏ qua) | cùng chỗ với `data\` |
| **Chỉ bật đường ống trên một máy một lúc** | hai máy cùng giữ chìa khóa và cùng chạy thì Cloudflare chia người vào cho cả hai |
| SSD định dạng **exFAT**; clone **kho gốc** vào SSD; `git pull` để cập nhật | exFAT cả Windows và Ubuntu đọc được; `origin` là kho gốc nên pull không liên quan tới fork |
| **`data\` trên SSD là bản duy nhất** | Git bỏ qua `data\`; sao lưu định kỳ, **không đưa lên Git** (có PIN) |
| Python: **mang theo thư mục `Python\`** (bản không cần cài, 3.12 x64, ~590 MB, đủ thư viện): cố định, không phụ thuộc máy mượn, không cần Internet. **Không chép `.venv`**; `Cai may moi.bat` (tạo lại venv bằng Python 3.12 của máy) chỉ là đường dự phòng. Launcher thử chạy thật `.venv` rồi `Python\`; không cái nào chạy được thì báo chạy `Cai may moi.bat`. Muốn chạy test trên máy mượn: một lần `Python\python.exe -m pip install -r backend\requirements-dev.txt`. Khi `requirements.txt` đổi: cập nhật một lần vào `Python\` trên SSD (cần Internet) | `.venv` ghi cứng đường dẫn Python của máy đã tạo nó (`pyvenv.cfg`: `home = …`), sang máy khác thì hỏng; thư viện cài vào venv của dự án nên Python hệ thống của máy mượn vẫn sạch. Đã sửa 25/11/2026 (bỏ ý `libs\`) |
| Sửa mã ở máy mượn: **fork** kho gốc, clone fork, push lên fork, **Pull Request** về kho gốc; kho gốc duyệt rồi gộp; trên SSD `git pull` | đăng nhập GitHub trên máy mượn phải là tài khoản sở hữu fork; **đăng xuất sau khi dùng** (Credential Manager nhớ) |
| MiniPC sau này: Docker (`git pull` + `docker compose up -d --build`); `data\` chép sang; chìa khóa dùng được trên Linux | [08](08_TRIEN_KHAI.md) mục E |

**Cái cần mang theo SSD (đều bị Git bỏ qua):** `Python\`, `data\` (~5 MB: bản thảo, hồ sơ, `pin.txt`, `mang.txt`, `cloudflared\` chứa chìa khóa `.json`) và `launcher\cloudflared.exe` (tải từ Cloudflare). **Không cần:** `backend\.venv` (~580 MB, tạo lại nếu cần), `export\` (~570 MB: kết quả đo, ảnh thử, phiếu giao việc; chép riêng thư mục nào cần), `.playwright-mcp\`, `__pycache__\`. Ngoài kho: ghi nhớ của Claude nằm ở `~\.claude\projects\…\memory` của từng máy.

**Đã thử (25/11/2026, máy chính):** tạm đổi tên thư mục `.cloudflared` của người dùng (không còn `config.yml`, `cert.pem`), bật bằng icon với `launcher\cloudflared.exe` + chìa khóa trong `data\cloudflared\` → mở được giao diện từ 4G. Chưa thử trên máy thứ hai. Chưa kiểm: "dubious ownership" của Git trên ổ ngoài; Docker đọc ghi thư mục `data` trên exFAT; Zero Trust gói Free có đòi thẻ khi đăng ký không (nếu đòi thì **không dùng**, cách USB vẫn đủ).
