# webui/ — mã nguồn trang WebUI nạp vào mạch MKS (FluidNC)

Đây là trang bấm nút có sẵn **trong mạch** (mở `http://fluidnc.local` hoặc `192.168.0.1` khi mạch tự phát Wi-Fi). Nó là đường cứu hộ, **không** thay phần mềm ExtruXY. Giải thích đầy đủ: `docs/07` mục 12.

## Nguồn gốc và giấy phép
| | |
|---|---|
| Gốc | `github.com/MitchBradley/ESP3D-WEBUI`, nhánh `revamp`, commit `028ae9cf` (13/10/2026). Bản FluidNC tách từ ESP3D-WEBUI 2.x của Luc Lebosse |
| Bản trên mạch hiện nay | `@a690c889` (đi kèm FluidNC 4.1.1). `revamp` mới hơn 12 commit, đọc mã thấy vẫn chạy với 4.1.1 khi đặt ở gốc `/` (chưa thử trên mạch) |
| `tablet/` | Repo con `MitchBradley/WebUI-tablet-extension` `v1.22.0`, chép thẳng (không phải submodule) |
| Giấy phép | Phần chính **GPL-3.0** (`LICENSE`); `tablet/` **MIT** (`tablet/LICENSE`). GPL: được sửa và phát hành lại, nhưng **phải công khai mã đã sửa** (chính thư mục này) và giữ giấy phép |
| README gốc | `README-goc.md` (tiếng Anh, giữ nguyên) |

Không lấy ESP3D-WEBUI 3.x (`luc-github/ESP3D-WEBUI`): bản đó chỉ ghi hỗ trợ ESP3D 3.1, grblHAL, không có FluidNC.

## Đóng gói (cần Node.js; đã thử Node 24.22, npm 11.19)
```
cd webui
npm ci --ignore-scripts      # cài đúng phiên bản trong package-lock.json, không chạy script của gói
npx gulp package --lang en   # ra webui/index.html.gz (~121 KB)
```
- `node_modules/`, `dist/`, `index.html.gz` không lên Git (`.gitignore`).
- Dòng phiên bản trong trang: `MitchBradley/ESP3D-WEBUI@028ae9cf+ExtruXY@<commit ExtruXY>` (`gulpfile.js`, hàm `replaceVersion`).
- **Không** chạy `tablet/build.ps1` / `build.sh`: script đó gửi mã lên trang nén trên mạng; gói chính lấy thẳng `tablet/src/tablet/*.js`.

Kiểm 27/11/2026: đóng lại bản `a690c889` bằng cách này ra **cùng 330 hàm, 370 `id`** với tệp tải từ mạch (khác thứ tự ghép JS, lệch 51 byte).

## Luật sửa
- **Chỉ đổi giao diện, giữ nguyên chức năng.** JS tìm phần tử bằng `id(...)` (442 chỗ): **không đổi, không xóa `id` nào**. Hai chỗ dựa vào cha/con: `www/js/tabs.js` dòng 8 và 15 (nút tab và nội dung tab phải nằm trong khối có `id` của thanh tab).
- Ẩn phần không dùng (spindle, laser, trục A B C, macro rỗng) bằng CSS, không xóa HTML.
- Sửa ở `www/sub/*.html` (từng khối), `www/css/*.css`. Ghi mỗi thay đổi so với gốc vào bảng dưới.
- Nạp lên mạch: **chủ dự án tự làm** (tab Tệp của WebUI, tải lên đúng tên `index.html.gz`), giữ `D:\index.html.gz` để trả lại. Trước khi nạp xem bộ nhớ tệp còn trống đủ ~121 KB không.

## Đã sửa so với gốc
| Ngày | Tệp | Sửa gì |
|---|---|---|
| 27/11/2026 | `gulpfile.js` | Dòng phiên bản ghi gốc `@028ae9cf` + commit ExtruXY (trước: ghi commit ExtruXY như thể của MitchBradley) |
