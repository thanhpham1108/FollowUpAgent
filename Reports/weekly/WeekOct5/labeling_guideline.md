# Hướng dẫn Đánh nhãn Dữ liệu (Ground Truth Labeling) - Dự án FollowUpAgent

## 1. Tóm tắt nhanh: Bạn cần điền cái gì vào đâu?

Trong file Excel, bạn **CHỈ ĐIỀN VÀO 2 CỘT CUỐI CÙNG**:
- **Cột `Human_Status_Group (Điền tay)`**: Điền **1 chữ số duy nhất** từ `1` đến `5`.
- **Cột `Human_Reason_Code (Điền tay)`**: Copy chính xác **Mã lý do** tương ứng với số nhóm đó (xem bảng tra cứu bên dưới).

---

## 2. BẢNG TRA CỨU ĐIỀN NHÃN (COPY - PASTE CHUẨN)

| Điền vào `Human_Status_Group` | Điền vào `Human_Reason_Code` | Ý nghĩa nghiệp vụ | Khi nào điền cặp này? (Tình huống thực tế khi bạn nghe audio) |
| :---: | :--- | :---: | :--- |
| **1** | `TU_CHOI_LUON` | 🛑 Đóng hồ sơ | Ứng viên nói thẳng: "Anh đi làm chỗ khác rồi" hoặc "Không có nhu cầu tìm việc". |
| **1** | `KNM_DAP_MAY` | 🛑 Đóng hồ sơ | Vừa nghe HR chào 1-2 giây là bấm dập máy ngang (tút tút tút), không làm phiền thêm. |
| **1** | `SAI_SO_NHAM_SO` | 🛑 Đóng hồ sơ | Người nhấc máy bảo: "Nhầm số rồi", "Không phải tên đó đâu" rồi cúp máy. |
| **2** | `KHACH_BAN` | 📞 Cần gọi lại | Ứng viên bắt máy nhưng bảo: "Đang đi đường / đang bận họp, gọi lại sau nhé". |
| **2** | `CUOC_GOI_RONG` | 📞 Cần gọi lại | Tiếng hộp thư thoại/thuê bao, hoặc chỉ có tiếng nhân viên tự alo thử mic rồi tắt. |
| **2** | `LOI_AM_THANH` | 📞 Cần gọi lại | Bật file lên chỉ thấy tiếng xì xèo, rè rè, mất tiếng, rớt mạng, im lặng hoàn toàn. |
| **3** | `SUY_NGHI_THEM` | 💬 Chăm sóc | Chê lương thấp, hỏi xong bảo: "Để anh xem lại / suy nghĩ thêm rồi báo sau". |
| **3** | `CHUA_CHOT_NGAY` | 💬 Chăm sóc | Rất muốn đi làm/phỏng vấn nhưng vướng việc bận, chưa hẹn được ngày cụ thể. |
| **3** | `CHO_GIAY_TO` | 💬 Chăm sóc | Muốn đi làm nhưng thiếu giấy tờ: "Đang chờ công an cấp lại CCCD", chờ giấy khám SK. |
| **3** | `HEN_XA` | 💬 Chăm sóc | Hẹn rất lâu mới đi được: "Nửa tháng nữa / tháng sau mới về quê lên xin việc được". |
| **4** | `HEN_PHONG_VAN` | 🗓️ Lịch hẹn | Đã chốt ngày giờ cụ thể: "9h sáng mai em lên công ty nộp hồ sơ phỏng vấn". |
| **5** | `DI_LAM` | 🎉 Thành công | Đã trúng tuyển / đã chốt ngày đi làm: "Thứ 2 tuần sau anh tới công ty nhận ca làm". |

---

## 3. Quy trình 3 bước cho người đánh nhãn

1. **Bước 1:** Mở file `.wav` tương ứng với tên file ở Cột A (`File_Name`) để nghe bằng tai.
2. **Bước 2:** Xác định cuộc gọi thuộc tình huống nào trong Bảng tra cứu ở Mục 2.
3. **Bước 3:** 
   - Điền số nhóm (1-5) vào cột `Human_Status_Group`.
   - Copy đúng mã chữ in hoa (ví dụ: `TU_CHOI_LUON`) dán vào cột `Human_Reason_Code`.

> **Lưu ý:**
> - Tuyệt đối không gõ sai chính tả hoặc thêm dấu cách thừa.
> - Số ở cột Status Group và Mã ở cột Reason Code phải đi cùng một dòng trong bảng tra cứu (Ví dụ: Đã điền nhóm `1` thì reason code chỉ có thể là `LOI_AM_THANH`, `CUOC_GOI_RONG` hoặc `SAI_SO_NHAM_SO`, không thể điền mã của nhóm khác).
