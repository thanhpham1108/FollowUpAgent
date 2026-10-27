# Thực hành HTTP: xem API recordings và tải audio

Làm các bước này trong **cùng một terminal trên `ood-master`**. Tự gõ từng lệnh, xem kết quả rồi mới sang bước sau. Các lệnh dưới đây không dùng `scripts/extract_audio_urls.py`: script đó đọc `/deals` và `linkCall`, là nguồn 50 audio cũ.

## Khi muốn chạy tự động

Script riêng `scripts/download_recordings.py` tự lấy đủ các trang của `/recordings`, lưu toàn bộ mã và tải WAV có kiểm tra. Chạy trên `ood-master` sau khi code đã có trên server:

```bash
python scripts/download_recordings.py --out-dir data/recordings_import
```

Lệnh này chỉ tạo `all_call_ids.txt` và `manifest.json`, chưa tải audio. API có 713 bản ghi, nên cần xác nhận **đúng 100 mã mới** trước khi chọn. Nếu bên cung cấp API đưa file chứa 100 mã, mỗi dòng một mã:

Nếu mục tiêu là tải **toàn bộ** mã API đang có, chạy một lệnh sau. Theo response ngày 27/10/2026, tổng là 713; script sẽ đọc lại số hiện tại từ API khi chạy:

```bash
python scripts/download_recordings.py --out-dir data/recordings_import --select all --download
```

Nếu sau này chỉ cần đúng 100 mã đã xác nhận, dùng file chứa mỗi mã trên một dòng:

```bash
python scripts/download_recordings.py --out-dir data/recordings_import \
  --ids-file data/new_recording_ids.txt --download
```

Nếu họ xác nhận mã càng lớn càng mới, có thể dùng `--select highest-id --count 100 --download`; nếu họ xác nhận 100 bản mới ở cuối thứ tự `/recordings`, dùng `--select last --count 100 --download`. Hai giả định này **không được chứng minh** bằng response hiện tại. Script lưu `selected_call_ids.txt`, audio trong `audio/` và mã tải lỗi trong `failed_call_ids.txt`; chạy lại cùng lệnh sẽ bỏ qua WAV đã tải hợp lệ.

Các phần dưới giải thích từng request và từng lệnh shell để học lại sau.

## 1. Hiểu địa chỉ và lệnh GET

| Địa chỉ | Nó trả về gì | Dùng để làm gì |
| --- | --- | --- |
| `http://192.168.25.175:8000` | Địa chỉ gốc của server | Ghép với đường dẫn API |
| `/docs` | Trang HTML Swagger | Đọc hướng dẫn, thử request trong trình duyệt |
| `/openapi.json` | JSON mô tả các endpoint | Liệt kê đường dẫn, tham số và kiểu dữ liệu |
| `/recordings` | JSON danh sách recording | Lấy `call_id` hoặc mã tương ứng |
| `/media/play/{call_id}.wav` | Nội dung audio | Thay `{call_id}` bằng mã thật để tải WAV |

`GET` là phương thức HTTP yêu cầu đọc tài nguyên. Một request gồm phương thức, URL và có thể thêm header. Response có mã trạng thái, header và body. Chẳng hạn `200` là thành công, `401/403` là vấn đề xác thực/quyền, `404` là không tìm thấy. Header `Content-Type: application/json` báo body JSON; `text/html` báo trang web; `audio/wav` hoặc `application/octet-stream` thường là file audio.

Vì vậy, lỗi `Expecting value...` khi đặt `API_BASE=.../docs` có nghĩa chương trình cố đọc **HTML** như **JSON**. Không thể sửa bằng tăng `--limit`: tham số đó chỉ giới hạn số lượng tìm được ở `/deals`.

## 2. Chuẩn bị thư mục riêng cho lần tải này

```bash
cd ~/datacore/FollowUpAgent
API_BASE='http://192.168.25.175:8000'
WORK_DIR="data/recordings_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$WORK_DIR/audio"
printf 'API_BASE=%s\nWORK_DIR=%s\n' "$API_BASE" "$WORK_DIR"
```

- `cd` chuyển thư mục làm việc.
- `API_BASE=...` đặt biến shell cho địa chỉ gốc, **không có `/docs`**.
- `$(date ...)` lấy thời gian hiện tại để tạo thư mục mới; không ghi đè batch cũ.
- `mkdir -p` tạo cả thư mục cha nếu cần; `-p` không báo lỗi khi thư mục đã tồn tại.
- Dấu `"..."` giữ nguyên giá trị biến nếu có khoảng trắng. Các biến chỉ tồn tại trong terminal hiện tại; mở terminal khác thì đặt lại.

## 3. Quan sát API, tương tự `ls`

Mở `$API_BASE/docs` trong trình duyệt để nhìn Swagger. Với terminal, `openapi.json` là bản mô tả máy đọc được:

```bash
curl -fsS "$API_BASE/openapi.json" -o "$WORK_DIR/openapi.json"
python -m json.tool "$WORK_DIR/openapi.json" > /dev/null
jq -r '.paths | keys[]' "$WORK_DIR/openapi.json"
```

- `curl` gửi request HTTP. Không ghi `-X GET` vì GET là mặc định.
- `-f` khiến HTTP lỗi (như 404) làm lệnh thất bại; `-s` tắt thanh tiến độ; `-S` vẫn hiện thông báo lỗi.
- `-o` lưu **body** vào file, thay vì in ra màn hình.
- `python -m json.tool` kiểm tra file là JSON hợp lệ. `/dev/null` là nơi bỏ kết quả in đẹp đi.
- `jq` đọc JSON; `.paths | keys[]` liệt kê các endpoint, giống `ls` cho cấu trúc API. `-r` in chuỗi không kèm dấu ngoặc kép.

Nếu chưa cài `jq`, vẫn xem được bằng `python -m json.tool "$WORK_DIR/openapi.json" | less`; nhấn `q` để thoát. Để liệt kê path bằng Python:

```bash
python -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["paths"]))' "$WORK_DIR/openapi.json"
```

Xem riêng tài liệu của hai route cần dùng:

```bash
jq '.paths["/recordings"].get' "$WORK_DIR/openapi.json" | less
jq '.paths["/media/play/{call_id}.wav"].get' "$WORK_DIR/openapi.json" | less
```

Nhìn vào `parameters` để biết API có `page`, `limit`, `offset`, `cursor` hay tham số lọc nào; nhìn vào `responses` và `security` để biết dạng dữ liệu và yêu cầu xác thực. Nếu đường dẫn liệt kê hơi khác ảnh, dùng đường dẫn **thực tế** trong file JSON.

## 4. Xem response của danh sách recordings

Trước tiên xem header mà không in body ra terminal:

```bash
curl -sS -D - -o /dev/null "$API_BASE/recordings"
```

`-D -` in response headers ra màn hình; `-o /dev/null` bỏ body. Tìm dòng `HTTP/... 200` và `content-type: application/json`. Nếu là `401/403`, xem phần xác thực trong `/docs`; cần dùng token do đơn vị quản lý API cấp. Không ghi token vào lịch sử shell hoặc chia sẻ trên chat.

Lưu một response để đọc từng phần:

```bash
curl -fsS "$API_BASE/recordings" -o "$WORK_DIR/recordings.json"
python -m json.tool "$WORK_DIR/recordings.json" > /dev/null
jq 'type' "$WORK_DIR/recordings.json"
jq 'if type == "array" then length else keys end' "$WORK_DIR/recordings.json"
```

Nếu `type` là `"array"`, xem một phần tử:

```bash
jq '.[0]' "$WORK_DIR/recordings.json"
```

API hiện tại trả object có `count`, `limit`, `offset`, `recordings`. Xem thông tin phân trang và phần tử đầu:

```bash
jq '{count,limit,offset,received:(.recordings | length)}' "$WORK_DIR/recordings.json"
jq '.recordings[0]' "$WORK_DIR/recordings.json"
```

Phần tử đầu là chuỗi mã như `"18483292"`. `received` là số mã trên trang này; `count` là tổng số bản ghi server báo. Nếu `received < count`, phải lấy thêm trang.

Kết quả quan sát ngày 27/10/2026: `count=713`, `limit=100`, `offset=0`, `received=100`. Điều này chỉ chứng minh trang đầu có 100 mã trong 713 mã; **không chứng minh đó là 100 audio mới**. Trước khi tải, xem trong OpenAPI `/recordings` có tham số sắp xếp, ngày tạo hoặc bộ lọc nào:

```bash
jq '.paths["/recordings"].get.parameters' "$WORK_DIR/openapi.json"
jq '{first:.recordings[0],last:.recordings[-1]}' "$WORK_DIR/recordings.json"
```

Nếu API chỉ trả mã, không trả ngày tạo hay thứ tự được mô tả rõ, cần hỏi người cung cấp API cách xác định lô 100 bản mới (ví dụ mốc thời gian, khoảng ID, tham số lọc hoặc danh sách mã). Không dùng `limit=100` để suy ra “100 mới”.

**Phân trang:** nếu tài liệu cho tham số như `page`, `limit`, `offset` hoặc response có `next`, `total`, phải đi hết các trang. Ví dụ `?page=1&limit=50` chỉ đúng **nếu tài liệu xác nhận** đúng tên tham số. `wc -l` ở bước tiếp theo chỉ đếm các mã đã nhận, không chứng minh server chỉ có từng đó.

## 5. Tạo danh sách mã gọi

Với response hiện tại, `.recordings` là mảng chuỗi, nên tạo danh sách mã từ trang đã lấy như sau:

```bash
jq -r '.recordings[]' "$WORK_DIR/recordings.json" | sort -u > "$WORK_DIR/call_ids.txt"
```

Nếu `count` lớn hơn số mã đã nhận, lệnh trên mới lấy **một trang**. Xem tham số phân trang được khai báo trong OpenAPI:

```bash
jq '.paths["/recordings"].get.parameters' "$WORK_DIR/openapi.json"
```

Nếu tài liệu xác nhận dùng `limit` và `offset`, thử trang kế bằng cách thay `OFFSET` bằng `.offset + .limit`:

```bash
LIMIT="$(jq -r '.limit' "$WORK_DIR/recordings.json")"
OFFSET="$(jq -r '.offset + .limit' "$WORK_DIR/recordings.json")"
curl -fsS "$API_BASE/recordings?limit=$LIMIT&offset=$OFFSET" -o "$WORK_DIR/recordings_next.json"
jq '{count,limit,offset,received:(.recordings | length),first:.recordings[0]}' "$WORK_DIR/recordings_next.json"
```

Chỉ khi `offset` trong response kế đúng bằng `$OFFSET`, mới tiếp tục lấy các trang còn lại. `[]` duyệt các phần tử; `-r` bỏ dấu ngoặc kép JSON; `|` đưa đầu ra cho lệnh kế; `sort -u` sắp xếp và bỏ trùng; `>` ghi đè file. Kiểm tra danh sách vừa tạo:

```bash
wc -l "$WORK_DIR/call_ids.txt"
head -n 3 "$WORK_DIR/call_ids.txt"
```

`wc -l` đếm dòng, `head -n 3` in 3 dòng đầu. Nếu số mã thấp hơn `count`, và bạn đã xác nhận `limit`/`offset` hoạt động, lấy tất cả các trang:

```bash
TOTAL="$(jq -r '.count' "$WORK_DIR/recordings.json")"
LIMIT="$(jq -r '.limit' "$WORK_DIR/recordings.json")"
OFFSET=0
: > "$WORK_DIR/call_ids.txt"
while [ "$OFFSET" -lt "$TOTAL" ]; do
  PAGE="$WORK_DIR/recordings_${OFFSET}.json"
  curl -fsS "$API_BASE/recordings?limit=$LIMIT&offset=$OFFSET" -o "$PAGE" || break
  GOT_OFFSET="$(jq -r '.offset' "$PAGE")"
  RECEIVED="$(jq -r '.recordings | length' "$PAGE")"
  if [ "$GOT_OFFSET" -ne "$OFFSET" ] || [ "$RECEIVED" -eq 0 ]; then
    echo "Phân trang lỗi ở offset $OFFSET"
    break
  fi
  jq -r '.recordings[]' "$PAGE" >> "$WORK_DIR/call_ids.txt"
  OFFSET=$((OFFSET + RECEIVED))
done
sort -u "$WORK_DIR/call_ids.txt" -o "$WORK_DIR/call_ids.txt"
wc -l "$WORK_DIR/call_ids.txt"
```

`TOTAL` là tổng server báo; `OFFSET` là vị trí bắt đầu của trang; `RECEIVED` là số mã thực nhận. Vòng lặp tăng `OFFSET` theo số thực nhận, dừng khi đủ `TOTAL`. `: > file` tạo file rỗng để bắt đầu lại; `>>` nối thêm dữ liệu từng trang. Nếu `curl` lỗi hoặc server không đổi offset theo yêu cầu, vòng lặp dừng; hãy xử lý lỗi và kiểm tra số dòng trước khi tải audio. `sort -u ... -o ...` bỏ mã trùng trong chính file đó. Nếu số mã duy nhất ít hơn `TOTAL`, có thể server chứa mã trùng hoặc một trang bị thiếu; kiểm tra các file `recordings_*.json`.

## 6. Thử tải một file trước

```bash
CALL_ID="$(head -n 1 "$WORK_DIR/call_ids.txt")"
printf 'Mã thử: %s\n' "$CALL_ID"
curl -fL -D "$WORK_DIR/sample.headers" -o "$WORK_DIR/audio/${CALL_ID}.wav" "$API_BASE/media/play/${CALL_ID}.wav"
cat "$WORK_DIR/sample.headers"
file "$WORK_DIR/audio/${CALL_ID}.wav"
```

`$(head ...)` lấy mã đầu tiên. Trong URL, shell thay `${CALL_ID}` bằng mã thật. `-L` theo redirect nếu server trả `Location`. `-D file` lưu response headers, `-o file` lưu body; `-f` tránh lưu trang báo lỗi HTTP thành `.wav`. `file` nhận dạng nội dung; nếu báo HTML/JSON thay vì âm thanh, xem headers và kiểm tra mã, URL hoặc xác thực. Có `ffprobe` thì có thể chạy `ffprobe -v error "$WORK_DIR/audio/${CALL_ID}.wav"` để kiểm tra audio sâu hơn.

## 7. Tải hàng loạt và có thể chạy lại

Chỉ chạy sau khi đã xác nhận file thử hợp lệ và danh sách mã đầy đủ:

```bash
while IFS= read -r CALL_ID; do
  case "$CALL_ID" in
    ''|*[!A-Za-z0-9_-]*) echo "Bỏ qua mã bất thường: $CALL_ID"; continue ;;
  esac
  OUT="$WORK_DIR/audio/${CALL_ID}.wav"
  if [ -s "$OUT" ]; then
    echo "Đã có: $CALL_ID"
    continue
  fi
  if curl -fLsS --retry 3 --connect-timeout 10 --max-time 180 \
      -o "$OUT.part" "$API_BASE/media/play/${CALL_ID}.wav"; then
    mv "$OUT.part" "$OUT"
    echo "OK: $CALL_ID"
  else
    echo "Lỗi: $CALL_ID"
  fi
done < "$WORK_DIR/call_ids.txt"
```

- `while IFS= read -r` đọc từng dòng nguyên vẹn trong file; `done < ...` cấp file cho vòng lặp.
- `case` chỉ chấp nhận mã chữ/số, `_`, `-` để tạo tên file và URL an toàn. Nếu mã thật có ký tự khác, dừng và kiểm tra tài liệu thay vì bỏ kiểm tra.
- `[ -s "$OUT" ]` kiểm tra file đã tồn tại và không rỗng để lần chạy lại bỏ qua file thành công.
- `--retry 3` thử lại lỗi mạng tạm thời; hai timeout giới hạn thời gian kết nối và toàn request.
- File tải trước vào `.part`; chỉ `mv` sang `.wav` khi `curl` thành công. File `.part` giúp nhận ra lần tải dở.

Kiểm tra sau khi tải:

```bash
wc -l "$WORK_DIR/call_ids.txt"
find "$WORK_DIR/audio" -maxdepth 1 -type f -name '*.wav' | wc -l
find "$WORK_DIR/audio" -maxdepth 1 -type f -name '*.part'
```

Số WAV nên bằng số mã duy nhất đã chọn. Nếu thiếu, xem các dòng `Lỗi`, kiểm tra `.part`, rồi chạy lại vòng lặp. Nếu mục tiêu là **100 audio mới**, hãy xác định chính xác chúng nằm ở trang nào hoặc dùng bộ lọc được API hỗ trợ trước khi tải; tổng 713 mã có thể gồm nhiều lô.
