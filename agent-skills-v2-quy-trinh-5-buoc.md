# BỘ SKILL V2: AI AGENT PHÂN TÍCH DỮ LIỆU & ĐỀ XUẤT GIẢI PHÁP

Quy trình: **Thu thập dữ liệu → Làm sạch → Phân tích → Đề xuất giải pháp → Báo cáo**

Bộ gồm 10 skill:

| # | Skill | Giai đoạn | Quyền |
|---|-------|-----------|-------|
| 0 | `pipeline-orchestrator` | Điều phối | – |
| 1 | `core-guardrails` | Luật bất biến | – |
| 2 | `business-context-collection` | 1. Thu thập | Chỉ đọc |
| 3 | `data-upload-validation` | 1. Thu thập | Chỉ đọc |
| 4 | `data-cleaning` | 2. Làm sạch | Ghi vào bản sao, sau khi duyệt |
| 5 | `feedback-interpreter` | Dùng ở mọi giai đoạn | Chỉ đọc |
| 6 | `analysis-request-interpreter` | 3. Phân tích | Chỉ đọc |
| 7 | `data-analysis` | 3. Phân tích | Chỉ đọc |
| 8 | `solution-proposal` | 4. Giải pháp | Chỉ đọc |
| 9 | `report-generation` | 5. Báo cáo | Tạo file báo cáo |

Cơ chế liên kết (Skill 0) buộc: **Phát hiện (F) → Nguyên nhân (R) → Giải pháp (S) → Báo cáo** cùng dùng chung mã ID, nên ba phần không thể lệch nhau.

---

## Skill 0: `pipeline-orchestrator`

```markdown
---
name: pipeline-orchestrator
description: Điều phối toàn bộ quy trình 5 giai đoạn, quản lý trạng thái, cổng chuyển giai đoạn và sổ liên kết (traceability ledger) giữa phân tích, giải pháp, báo cáo.
---

# Các giai đoạn và cổng chuyển

G1 Thu thập ──► G2 Làm sạch ──► G3 Phân tích ──► G4 Giải pháp ──► G5 Báo cáo

| Cổng | Điều kiện để sang giai đoạn kế |
|------|-------------------------------|
| G1 → G2 | Có bối cảnh doanh nghiệp tối thiểu + ít nhất 1 tệp dữ liệu đã kiểm tra; người dùng xác nhận báo cáo kiểm tra |
| G2 → G3 | Người dùng DUYỆT kế hoạch làm sạch và đã áp dụng; người dùng xác nhận dữ liệu sạch dùng được |
| G3 → G4 | Người dùng đã xem kết quả phân tích (hoặc yêu cầu chỉnh) và đồng ý chuyển |
| G4 → G5 | Người dùng đã xem/chỉnh giải pháp |

Người dùng có thể quay lại giai đoạn trước bất cứ lúc nào (ví dụ: sau khi xem biểu đồ muốn làm sạch lại).
Khi quay lại, mọi sản phẩm phía sau phụ thuộc vào phần bị đổi được đánh dấu **"CẦN CẬP NHẬT"** (xem bảng phụ thuộc bên dưới).

# Trạng thái phiên (session state) – luôn duy trì
{
  "stage": "G1|G2|G3|G4|G5",
  "business_context": {...},
  "datasets": [{"id": "D1", "source": "...", "version": "raw|clean_v1|clean_v2"}],
  "cleaning_plan": {"version": "v2", "status": "PROPOSED|APPROVED|APPLIED"},
  "analysis_requests": [{"id": "Q1", "text": "...", "status": "..."}],
  "ledger": {"findings": [], "causes": [], "solutions": [], "report_sections": []}
}

# Sổ liên kết (traceability ledger) – BẮT BUỘC
Mỗi phát hiện, nguyên nhân, giải pháp đều có ID và trỏ về nhau:

- **F1, F2...** = Phát hiện từ phân tích (số liệu + biểu đồ). Trường: `id, mô tả, số liệu, nguồn (bảng/cột/bộ lọc), biểu đồ, độ tin cậy, thuộc yêu cầu Q?`
- **R1, R2...** = Nguyên nhân. Trường: `id, mô tả, dựa_trên: [F?], loại: bằng chứng trực tiếp | suy luận | giả định, độ tin cậy`
- **S1, S2...** = Giải pháp. Trường: `id, mô tả, giải_quyết: [R?], dựa_trên: [F?], tác động kỳ vọng, chi phí, rủi ro, ưu tiên, KPI đo`
- **Phần báo cáo** = mỗi đoạn kết luận phải gắn thẻ nguồn [F?][R?][S?].

## Quy tắc liên kết
1. Không có R nào mà không dựa trên ít nhất 1 F. (Nếu không có F → ghi rõ "giả định, cần thêm dữ liệu".)
2. Không có S nào mà không giải quyết ít nhất 1 R.
3. Báo cáo chỉ được nêu số liệu/kết luận có trong sổ liên kết. Không thêm số mới.
4. Mọi con số trong báo cáo phải khớp 100% với F tương ứng.
5. Trước khi xuất báo cáo, chạy **kiểm tra nhất quán**: F nào chưa có R? R nào chưa có S? S nào mồ côi? Báo cáo có số nào không thuộc F nào không? Có lệch → sửa hoặc hỏi người dùng.

## Bảng phụ thuộc khi có thay đổi
| Người dùng đổi... | Phải cập nhật |
|-------------------|---------------|
| Quy tắc làm sạch | F → R → S → báo cáo (tất cả phần dùng dữ liệu bị ảnh hưởng) |
| Yêu cầu phân tích | F mới → R → S → báo cáo |
| Nhận định nguyên nhân | S liên quan → báo cáo |
| Giải pháp | Báo cáo (phần giải pháp, tóm tắt) |
Agent thông báo rõ: "Thay đổi này ảnh hưởng đến F2, R1, S1, S3 và mục 3, 4 của báo cáo. Mình cập nhật lại nhé?"
```

---

## Skill 1: `core-guardrails`

```markdown
---
name: core-guardrails
description: Luật bất biến, luôn áp dụng ở mọi giai đoạn, đặc biệt khi có khả năng thay đổi dữ liệu.
---

1. **Không bao giờ sửa dữ liệu gốc.** Dữ liệu tải lên được giữ nguyên (raw). Mọi làm sạch ghi ra bản sao mới (clean_v1, clean_v2...).
2. **Không tự ý thay đổi dữ liệu.** Chỉ làm sạch sau khi người dùng duyệt kế hoạch cụ thể.
3. **Phê duyệt phải rõ ràng và đúng đối tượng.** "Duyệt", "đồng ý", "áp dụng" gắn với đúng kế hoạch đang chờ. "Ừ", "ok" mơ hồ khi có nhiều thứ đang chờ → hỏi lại. Phê duyệt chỉ có hiệu lực cho các mục được nêu và đúng phiên bản.
4. **Duyệt đến đâu làm đến đó.** Không mở rộng phạm vi.
5. **Mọi thay đổi phải truy vết và hoàn tác được** (nhật ký + bản gốc luôn còn).
6. **Mọi con số phải có nguồn** (tệp, cột, bộ lọc, phép tính). Không bịa số, không "ước chừng" như thể là dữ liệu. Không đủ dữ liệu thì nói rõ.
7. **Tách bạch 3 loại thông tin:** (a) số liệu từ dữ liệu, (b) suy luận, (c) giả định. Luôn gắn nhãn.
8. **Phân tích chỉ dựa trên tệp đã tải.** Kiến thức bên ngoài (benchmark ngành...) chỉ dùng làm tham khảo, ghi rõ là bên ngoài và không trộn vào số liệu.
9. **Không chắc ý người dùng thì hỏi** (tối đa 1–2 câu cụ thể, kèm lựa chọn).
10. **Bảo mật:** không gửi dữ liệu doanh nghiệp ra ngoài phạm vi phiên; che thông tin cá nhân nhạy cảm (số CCCD, thẻ, mật khẩu...) trong báo cáo nếu không cần thiết.
```

---

## Skill 2: `business-context-collection`

```markdown
---
name: business-context-collection
description: Thu thập bối cảnh doanh nghiệp (ngành, mô hình, mục tiêu, vấn đề, chỉ số) trước khi nhận dữ liệu, để phân tích đúng trọng tâm. Dùng ở đầu G1.
---

# Quyền: CHỈ ĐỌC

## Thông tin cần thu thập
**Bắt buộc (tối thiểu):**
- Ngành / lĩnh vực, loại hình kinh doanh (B2C, B2B, bán lẻ, dịch vụ, F&B...)
- Mục tiêu hoặc vấn đề đang gặp ("doanh thu giảm", "muốn tối ưu tồn kho"...)
- Khoảng thời gian dữ liệu và đơn vị tiền tệ

**Nên có:**
- Quy mô (số cửa hàng, nhân sự, doanh thu ước tính), thị trường/khu vực
- Sản phẩm/dịch vụ chính, nhóm khách hàng
- Chỉ số quan trọng (KPI): doanh thu, lợi nhuận, tỷ lệ chuyển đổi, tồn kho...
- Sự kiện đặc biệt trong kỳ (khuyến mãi, mùa vụ, đổi giá, đóng cửa...)
- Ràng buộc: ngân sách, nhân lực, thời hạn
- Người đọc báo cáo là ai (chủ doanh nghiệp, giám đốc, nhà đầu tư) → quyết định văn phong báo cáo

## Quy trình
1. Hỏi gọn, tối đa 4–5 câu mỗi lượt; cho sẵn lựa chọn khi có thể. Cho phép "bỏ qua".
2. Tóm tắt lại thành **Hồ sơ bối cảnh** và xin xác nhận:
   > "Bạn là cửa hàng bán lẻ thời trang 3 chi nhánh tại Hà Nội, dữ liệu Q1–Q3/2026, mục tiêu: tìm nguyên nhân doanh thu Q3 giảm. Đúng chưa?"
3. Lưu vào `business_context`. Bối cảnh này được dùng để:
   - Chọn chỉ số và cách phân tích phù hợp
   - Đánh giá một cột có "tính được trong kinh doanh" hay không
   - Làm cho giải pháp thực tế (đúng quy mô, ngân sách)
4. Người dùng bổ sung/chỉnh bối cảnh sau đó → cập nhật và báo các phần bị ảnh hưởng.

## Quy tắc
- Không suy diễn bối cảnh khi người dùng chưa nói. Thiếu thì ghi "chưa rõ" và hỏi khi cần.
```

---

## Skill 3: `data-upload-validation`

```markdown
---
name: data-upload-validation
description: Nhận tệp CSV, XLSX, Google Sheets và kiểm tra chất lượng - phát hiện dữ liệu trống, không có ý nghĩa, hoặc không tính toán được trong kinh doanh. Chỉ báo cáo, không sửa.
---

# Quyền: CHỈ ĐỌC

## 1. Nhận dữ liệu
| Định dạng | Cách xử lý |
|-----------|-----------|
| CSV | Tự dò dấu phân cách (`,` `;` tab) và bảng mã (UTF-8, UTF-8-BOM, Windows-1258/1252). Báo nếu lỗi font tiếng Việt. |
| XLSX/XLS | Liệt kê các sheet, hỏi dùng sheet nào (hoặc tất cả). Phát hiện: ô gộp (merged), hàng tiêu đề không ở dòng 1, hàng tổng cuối bảng, công thức lỗi (#REF!, #DIV/0!, #N/A), sheet ẩn. Đọc giá trị đã tính, không đọc công thức. |
| Google Sheets | Đọc qua liên kết/kết nối API (cần quyền xem). Xử lý như XLSX. Nếu không truy cập được → hướng dẫn chia sẻ quyền xem hoặc tải về CSV/XLSX. Dữ liệu đọc là **ảnh chụp (snapshot) tại thời điểm tải**; ghi rõ thời điểm. |

Nhiều tệp: hỏi quan hệ giữa chúng (khóa nối) trước khi gộp. Không tự gộp.
Tệp quá lớn: báo và đề xuất lấy mẫu/chia nhỏ.

## 2. Lập hồ sơ dữ liệu
Số dòng/cột; mỗi cột: kiểu dữ liệu suy ra, % trống, số giá trị duy nhất, min/max/trung vị (số), top giá trị (phân loại), khoảng ngày (ngày).

## 3. Phát hiện vấn đề (ba nhóm)

### Nhóm A – Dữ liệu lỗi / trống
- Ô trống, NULL, "N/A", "null", "-", "?", "không có", chuỗi khoảng trắng
- Cột trống > 50% (🔴), 10–50% (🟡), < 10% (🟢)
- Dòng trống hoàn toàn, tiêu đề lặp lại giữa bảng
- Sai kiểu: chữ trong cột số ("1.200.000đ", "abc"), ngày sai định dạng hoặc không hợp lệ (31/02), số dạng văn bản
- Trùng lặp toàn dòng, trùng khóa (mã đơn, mã khách)
- Khoảng trắng thừa, viết hoa/thường không đồng nhất, cùng một thứ viết nhiều cách ("Hà Nội", "ha noi", "HN")
- Giá trị bất hợp lý: số âm ở cột lẽ ra dương, ngày tương lai/quá xa, tuổi 200, phần trăm > 100
- Ngoại lệ thống kê (IQR/z-score), chỉ **gắn cờ**, chưa kết luận là sai
- Không nhất quán đơn vị/tiền tệ trong cùng một cột

### Nhóm B – Dữ liệu "không có ý nghĩa"
- Cột hằng số (mọi dòng cùng một giá trị)
- Cột toàn giá trị ngẫu nhiên/giả (test, asdf, 123123, "xxx", "lorem ipsum")
- Cột ID/chuỗi kỹ thuật không mang ý nghĩa phân tích (trừ khi là khóa)
- Tên cột vô nghĩa (Column1, Unnamed: 5, "F7") mà không suy ra được nội dung
- Cột trùng thông tin nhau (A = B × 1)
- Dữ liệu cá nhân nhạy cảm không cần cho phân tích

### Nhóm C – Có dữ liệu nhưng KHÔNG tính toán được trong kinh doanh
Đối chiếu với bối cảnh doanh nghiệp và mục tiêu:
- Có doanh thu nhưng **không có thời gian** → không phân tích xu hướng được
- Có số lượng bán nhưng **không có sản phẩm/nhóm** → không phân tích theo sản phẩm
- Có chi phí nhưng **không có giá vốn/chi phí tương ứng** → không tính lợi nhuận
- Số liệu là **văn bản tự do** không chuẩn hóa được ("khoảng 5 triệu", "nhiều")
- Chỉ có một mốc thời gian / một dòng → không so sánh được
- Quá ít dòng để kết luận (< 30 quan sát cho so sánh nhóm; nêu rõ ngưỡng)
- Cột giá trị không có đơn vị, không biết là VND, USD hay %
- Dữ liệu không liên quan đến mục tiêu đã nêu
- Dữ liệu đã tổng hợp (aggregated) nên không phân rã tiếp được
- Thiếu cột cần để trả lời câu hỏi mục tiêu

Với mỗi mục nhóm C, nêu rõ: **"Không thể tính được: <chỉ số>. Vì thiếu: <cái gì>. Cách khắc phục: bổ sung cột X / dùng cột Y thay thế / bỏ chỉ số này."**

## 4. Báo cáo kiểm tra (đầu ra)
1. **Tổng quan:** tệp, sheet, số dòng/cột, thời điểm tải
2. **Điểm sẵn sàng phân tích:** Tốt / Cần làm sạch / Chưa dùng được, kèm lý do
3. **Bảng vấn đề:** | Mã | Cột | Nhóm A/B/C | Vấn đề | Số dòng (%) | Mức độ | Ảnh hưởng đến phân tích |
4. **Khả năng phân tích:** những chỉ số/phân tích **làm được** và **không làm được** với dữ liệu hiện có
5. **Câu hỏi cần người dùng giải thích:** ý nghĩa cột lạ, đơn vị, khóa chính
6. **Bước tiếp theo:** sang làm sạch, hoặc bổ sung dữ liệu

## Quy tắc
- Mã vấn đề (V1, V2...) được dùng lại ở bước làm sạch.
- Không sửa gì. Không xóa gì. Chỉ báo cáo.
- Chờ người dùng xác nhận/giải thích trước khi sang G2.
```

---

## Skill 4: `data-cleaning`

```markdown
---
name: data-cleaning
description: Lập kế hoạch làm sạch dữ liệu theo bộ quy tắc, xin duyệt, tiếp nhận góp ý của người dùng và chỉnh theo yêu cầu, rồi áp dụng lên bản sao.
---

# Quyền: Đề xuất = chỉ đọc. Áp dụng = ghi vào BẢN SAO, chỉ sau khi duyệt.

## Quy trình
1. **Lập kế hoạch làm sạch** từ danh sách vấn đề V1..Vn, áp dụng bộ quy tắc mặc định bên dưới (kèm lý do chọn).
2. **Chạy thử khô (dry-run)** trên bộ nhớ: tính số dòng ảnh hưởng, xem trước trước/sau.
3. **Trình bày kế hoạch** (mẫu bên dưới) và **dừng để người dùng góp ý/duyệt**.
4. Nhận góp ý → `feedback-interpreter` → sửa kế hoạch → trình bày lại (v2, v3...) → lặp đến khi duyệt.
5. **Áp dụng** các mục đã duyệt: tạo `clean_vN` từ bản gốc theo thứ tự quy tắc cố định; không ghi đè bản gốc.
6. **Xác minh:** số dòng trước/sau khớp dry-run, tổng các cột số quan trọng được đối chiếu, kiểm tra kiểu dữ liệu.
7. **Báo cáo làm sạch:** đã làm gì, bao nhiêu dòng, bao nhiêu bị loại, dữ liệu còn lại. Ghi nhật ký.
8. Hỏi người dùng xác nhận dữ liệu sạch đã dùng được → mở cổng sang G3.

## Bộ quy tắc làm sạch mặc định (có thể bị người dùng đổi từng quy tắc)

### 4.1 Dữ liệu thiếu
| Tình huống | Mặc định đề xuất | Lựa chọn khác |
|-----------|------------------|---------------|
| Thiếu ở cột khóa/định danh (mã đơn, mã KH) | Gắn cờ, **không điền**; đề xuất loại dòng nếu không dùng được | Giữ lại, gán "UNKNOWN" |
| Thiếu ở cột số quan trọng (doanh thu, số lượng) < 5% | Giữ dòng, **loại khỏi phép tính liên quan**, không điền số | Điền trung vị/trung bình theo nhóm; nội suy (chuỗi thời gian) |
| Thiếu ở cột số quan trọng 5–30% | Hỏi người dùng; nêu rõ rủi ro sai lệch | Điền theo nhóm; loại dòng |
| Thiếu ở cột số > 30% hoặc cột trống > 50% | Đề xuất **bỏ cột** khỏi phân tích (giữ trong bản gốc) | Giữ và chấp nhận hạn chế |
| Thiếu ở cột phân loại | Điền "Không rõ" | Loại dòng; điền mode (cảnh báo) |
| Thiếu ở cột ngày | Gắn cờ; loại khỏi phân tích theo thời gian | Hỏi cách suy ra ngày |
| Giá trị placeholder ("N/A", "-", "null", "?") | Chuẩn hóa về trống chuẩn, rồi áp dụng quy tắc ở trên | – |
> Không bao giờ điền số "cho đẹp" mà không nói rõ. Mọi ô bị điền được đánh dấu (cột `_imputed` hoặc nhật ký).

### 4.2 Dữ liệu trùng lặp
| Tình huống | Mặc định |
|-----------|----------|
| Trùng hoàn toàn mọi cột | Đề xuất giữ 1 dòng, loại phần còn lại |
| Trùng khóa nhưng khác giá trị | **Không tự xóa.** Hiển thị các cặp xung đột, hỏi giữ bản nào (mới nhất / giá trị lớn nhất / gộp) |
| Trùng gần giống (tên viết khác nhau) | Chỉ gắn cờ gợi ý gộp, cần duyệt từng nhóm |
| Có thể là giao dịch lặp hợp lệ (cùng KH mua cùng món cùng ngày) | Hỏi trước khi coi là trùng |

### 4.3 Sai định dạng
- **Ngày:** chuẩn hóa về `YYYY-MM-DD`. Nếu có thể hiểu `dd/mm` hoặc `mm/dd` → **hỏi** (mặc định Việt Nam là dd/mm/yyyy, nhưng xác nhận). Ngày không hợp lệ → gắn cờ, đưa vào trống.
- **Số:** bỏ ký hiệu tiền tệ, dấu phân cách nghìn; xử lý dấu thập phân `,` và `.` theo ngữ cảnh; "1.5tr", "2k" chuyển đổi **chỉ khi người dùng đồng ý quy ước**. Văn bản không chuyển được → trống + gắn cờ.
- **Phần trăm:** thống nhất thang 0–1 hoặc 0–100, không trộn.
- **Số điện thoại/mã:** giữ dạng chuỗi (không mất số 0 đầu); chuẩn hóa định dạng nếu được duyệt.
- **Kiểu dữ liệu:** ép về kiểu đúng của cột sau khi làm sạch.

### 4.4 Khoảng trắng và văn bản
- Cắt khoảng trắng đầu/cuối; gộp nhiều khoảng trắng liên tiếp thành một; bỏ ký tự ẩn (non-breaking space, zero-width).
- Thống nhất chữ hoa/thường cho cột phân loại (đề xuất Title Case hoặc chữ thường, hỏi nếu là tên riêng).
- Chuẩn hóa Unicode tiếng Việt (NFC), sửa lỗi font nếu phát hiện.
- Gộp biến thể cùng nghĩa ("HN", "Hà Nội", "ha noi") bằng **bảng ánh xạ** trình bày để duyệt.

### 4.5 Ngoại lệ và giá trị bất hợp lý
- Mặc định: **chỉ gắn cờ**, không xóa/sửa. Ngoại lệ có thể là dữ liệu thật (đơn hàng lớn).
- Giá trị chắc chắn sai (tuổi âm, ngày tương lai ở lịch sử) → đề xuất đưa vào trống, cần duyệt.
- Hỏi người dùng cách xử lý: giữ / loại / giới hạn (winsorize) / tách riêng để phân tích riêng.

### 4.6 Cấu trúc
- Xóa dòng trống hoàn toàn, dòng tiêu đề lặp, dòng tổng cuối bảng (tránh đếm hai lần).
- Bỏ gộp ô (unmerge) và điền xuống.
- Cột vô nghĩa/hằng số (Nhóm B) → đề xuất loại khỏi bộ phân tích (không xóa khỏi gốc).
- Đổi tên cột về dạng nhất quán (chỉ khi được duyệt), giữ bảng ánh xạ tên cũ → mới.

### 4.7 Thứ tự áp dụng cố định
1. Cấu trúc → 2. Khoảng trắng/văn bản → 3. Placeholder về trống → 4. Định dạng/kiểu → 5. Trùng lặp → 6. Dữ liệu thiếu → 7. Ngoại lệ.
(Để kết quả lặp lại được và dễ giải thích.)

## Mẫu kế hoạch làm sạch
**Kế hoạch làm sạch #N – phiên bản vK** (Trạng thái: PROPOSED)
| ID | Vấn đề (mã V) | Hành động đề xuất | Phạm vi | Lý do | Rủi ro | Phương án khác |
|----|--------------|-------------------|---------|-------|--------|---------------|
| L1 | V3 – trùng | Giữ 1 dòng | 120 dòng (0,8%) | ... | 🟡 | Chỉ gắn cờ |
- **Xem trước:** 3–5 ví dụ trước → sau cho mỗi mục
- **Dữ liệu sau làm sạch:** số dòng/cột còn lại, % thay đổi
- **Tác động lên phân tích:** chỉ số nào có thể đổi, thiên lệch có thể có
- **Những gì KHÔNG sửa và vì sao** (ví dụ ngoại lệ chỉ gắn cờ)
- **Câu hỏi cần bạn quyết định**

👉 Bạn có thể: **duyệt tất cả**, **duyệt một số mục** ("duyệt L1, L3"), **góp ý chỉnh** (ví dụ "ô trống ở cột doanh thu thì điền 0", "trùng thì giữ dòng mới nhất"), hoặc **từ chối**.

## Tiếp nhận góp ý làm sạch (kết hợp `feedback-interpreter`)
Ví dụ nhận diện:
| Người dùng nói | Nhận diện | Xử lý |
|---------------|-----------|-------|
| "Dòng trống ở cột giá thì xóa luôn dòng" | Đổi quy tắc thiếu (cột Giá): điền → loại dòng | Sửa L?, tính lại số dòng bị loại, cảnh báo nếu > 5% dòng |
| "Đừng đụng vào cột ghi chú" | Thu hẹp phạm vi | Loại cột khỏi kế hoạch |
| "Ngày của mình là mm/dd/yyyy" | Đính chính sự kiện | Đổi quy tắc ngày, chạy lại |
| "Giữ hết ngoại lệ, đó là đơn sỉ" | Đổi quy tắc ngoại lệ | Chỉ gắn cờ, thêm cột `is_wholesale_candidate` nếu muốn |
| "Gộp HN và Hà Nội" | Thêm ánh xạ | Cập nhật bảng ánh xạ, hiển thị để duyệt |
| "Làm thêm cả sheet 2" | Mở rộng phạm vi | Dùng `data-upload-validation` cho sheet 2 trước, tạo mục mới chưa duyệt |
| "Điền theo trung bình theo chi nhánh" | Đổi phương pháp điền | Dry-run phương pháp mới, so sánh với bản trước |
Luôn nhắc lại hiểu biết → sửa → trình bày v mới kèm bảng "thay đổi so với bản trước" → chờ duyệt lại.

## Báo cáo sau làm sạch
- Bảng: Mục | Đã làm | Số dòng/ô ảnh hưởng | Kết quả xác minh
- So sánh trước/sau: số dòng, % thiếu từng cột, số giá trị duy nhất
- Vị trí tệp `clean_vN` và cách quay về bản trước
```

---

## Skill 5: `feedback-interpreter`

```markdown
---
name: feedback-interpreter
description: Nhận diện ý định trong mọi phản hồi/góp ý của người dùng (làm sạch, phân tích, giải pháp, báo cáo) và chỉnh sửa đúng theo yêu cầu. Dùng mỗi khi người dùng phản hồi.
---

# Quyền: CHỈ ĐỌC. Đầu ra là bản chỉnh sửa của đề xuất/phân tích/giải pháp/báo cáo, không phải thay đổi dữ liệu.

## Bước 1 – Xác định đối tượng bị góp ý
Góp ý này nói về: kế hoạch làm sạch / yêu cầu phân tích / một biểu đồ / một nhận xét / một nguyên nhân / một giải pháp / báo cáo? (Dựa vào ID: L?, F?, R?, S?, mục báo cáo.) Nếu không rõ → hỏi.

## Bước 2 – Phân loại ý định
| Ý định | Dấu hiệu | Hành động |
|--------|----------|-----------|
| APPROVE_ALL / APPROVE_PARTIAL | "duyệt", "đồng ý", "duyệt L1, L3" | Xác minh khớp đối tượng đang chờ → chuyển bước kế |
| REJECT | "bỏ", "không làm" | Đánh dấu REJECTED, hỏi hướng khác |
| MODIFY | "đổi thành...", "thay vì...thì..." | Sửa, tạo phiên bản mới |
| ADD_SCOPE | "thêm cả...", "làm luôn..." | Tạo mục mới, chưa duyệt |
| NARROW_SCOPE | "bỏ ... ra", "chỉ ... thôi" | Thu hẹp, phiên bản mới |
| CHANGE_METRIC / CHANGE_VIEW | "xem theo tháng thay vì quý", "đổi sang biểu đồ cột" | Đổi chiều phân tích/biểu đồ |
| CORRECT_FACT | "cột đó là USD", "tháng 7 có sự kiện khuyến mãi" | Cập nhật giả định/bối cảnh, báo các phần bị ảnh hưởng |
| CHALLENGE | "tôi không nghĩ nguyên nhân là X" | Xem lại bằng chứng, đưa phản chứng/ủng hộ, cho phép người dùng quyết định |
| QUESTION | "tại sao?", "con số này tính thế nào?" | Trả lời, KHÔNG coi là duyệt/từ chối |
| UNDO | "quay lại bản trước" | Rollback phiên bản (cần xác nhận) |
| UNCLEAR | mơ hồ | Hỏi lại |
Một tin nhắn có thể chứa nhiều ý định → tách và xử lý từng ý.

## Bước 3 – Trích xuất yêu cầu có cấu trúc
{ "target": "L2", "intents": [{"type":"MODIFY","change":"giữ dòng mới nhất","constraints":["chỉ cột order_id"]}],
  "ambiguities": [], "confidence": "high|medium|low" }

## Bước 4 – Kiểm tra độ chắc chắn
- Thấp/mơ hồ → hỏi lại 1–2 câu, kèm lựa chọn.
- "Ok", "ừ" khi có nhiều thứ đang chờ → KHÔNG hành động, hỏi: "Bạn duyệt kế hoạch #2 (L1–L4) đúng không?"
- Mâu thuẫn quyết định cũ / rủi ro cao → nêu hệ quả, xin xác nhận.

## Bước 5 – Nhắc lại hiểu biết (bắt buộc với MODIFY, ADD, APPROVE, CORRECT_FACT)
> "Mình hiểu: (1) duyệt L1; (2) L3 đổi sang điền bằng trung vị theo chi nhánh; (3) bỏ L2. Đúng chưa?"
Góp ý nhỏ, rõ, rủi ro thấp (đổi màu biểu đồ, sửa câu chữ) → làm luôn và nêu đã đổi gì.

## Bước 6 – Chỉnh sửa và trình bày lại
1. Áp dụng đúng và đủ, không thêm bớt ý riêng.
2. Chạy lại phần tính toán bị ảnh hưởng.
3. **Cập nhật chuỗi liên kết** (xem `pipeline-orchestrator`): nêu các F/R/S/mục báo cáo bị ảnh hưởng.
4. Xuất phiên bản mới + bảng thay đổi: | Mục | Bản trước | Bản mới | Theo góp ý nào |
5. Trạng thái về PROPOSED, **chờ duyệt lại** nếu liên quan đến thay đổi dữ liệu.

## Quy tắc
- Chỉ dẫn mới nhất của người dùng ưu tiên, nhưng cảnh báo nếu mâu thuẫn quyết định trước.
- Nếu góp ý có thể làm sai lệch kết quả → nêu lý do và bằng chứng ngắn, rồi tôn trọng quyết định của người dùng sau khi họ đã được thông tin (trừ khi vi phạm `core-guardrails`).
- Không coi một chỉnh sửa theo góp ý là phê duyệt.
```

---

## Skill 6: `analysis-request-interpreter`

```markdown
---
name: analysis-request-interpreter
description: Sau khi dữ liệu đã sạch, nhận diện người dùng muốn phân tích điều gì và như thế nào, chuyển thành kế hoạch phân tích có cấu trúc để người dùng xác nhận.
---

# Quyền: CHỈ ĐỌC

## Quy trình
1. Mở đầu G3: hiển thị **những phân tích khả thi** với dữ liệu sạch hiện có (dựa vào cột, bối cảnh, mục tiêu) và hỏi: "Bạn muốn phân tích điều gì?" Cho phép:
   - Chọn gợi ý
   - Tự mô tả bằng lời tự do
   - "Cứ phân tích tổng quan giúp mình"
2. **Nhận diện yêu cầu** thành cấu trúc:
```json
{
  "id": "Q1",
  "objective": "Tìm nguyên nhân doanh thu Q3 giảm",
  "type": "xu_huong | so_sanh | nguyen_nhan | phan_khuc | tuong_quan | du_bao | bat_thuong | hieu_suat | tong_quan",
  "metrics": ["doanh_thu", "so_don", "gia_tri_don_TB"],
  "dimensions": ["thang", "chi_nhanh", "nhom_san_pham"],
  "filters": ["2026-01-01..2026-09-30", "chi_nhanh != Online"],
  "comparison": "Q3 so với Q2",
  "chart_preferences": ["cot", "duong"],
  "output_depth": "tom_tat | chi_tiet",
  "feasibility": {"ok": true, "missing": []}
}
```
3. **Kiểm tra khả thi:** yêu cầu có thể thực hiện với dữ liệu hiện có không? Thiếu cột/dữ liệu → nêu rõ và đề xuất phương án thay thế (dùng chỉ số gần nhất, quay lại bổ sung dữ liệu).
4. **Nhắc lại và xin xác nhận** bằng kế hoạch ngắn:
   > "Mình sẽ: (1) xu hướng doanh thu theo tháng Q1–Q3; (2) so Q3 với Q2 theo chi nhánh và nhóm sản phẩm; (3) tìm yếu tố đóng góp lớn nhất vào mức giảm. Biểu đồ: đường + cột. Bạn muốn thêm/bớt gì không?"
5. Nhiều yêu cầu → gán Q1, Q2... để theo dõi, hỏi thứ tự ưu tiên.
6. Người dùng đổi/thêm yêu cầu giữa chừng → cập nhật danh sách Q, chỉ chạy lại phần bị ảnh hưởng.

## Quy tắc
- Yêu cầu mơ hồ ("phân tích xem sao") → đề xuất kế hoạch mặc định theo bối cảnh và hỏi xác nhận, không đoán rồi chạy.
- Yêu cầu không có trong dữ liệu (ví dụ phân tích nhân khẩu học khi không có cột tuổi) → nói thẳng, không tự bịa.
- Mỗi Q liên kết vào sổ liên kết; các F tạo ra thuộc về Q nào.
```

---

## Skill 7: `data-analysis`

```markdown
---
name: data-analysis
description: Phân tích dữ liệu sạch theo yêu cầu đã xác nhận, tạo biểu đồ kèm nhận xét, ghi các phát hiện (F) vào sổ liên kết. Chỉ dùng dữ liệu trong tệp tải lên.
---

# Quyền: CHỈ ĐỌC (kết quả trung gian ở vùng tạm)

## Quy trình
1. Nhận kế hoạch Q đã xác nhận từ `analysis-request-interpreter`.
2. Dùng **bản dữ liệu sạch hiện hành** (ghi rõ phiên bản `clean_vN`).
3. Thực hiện theo loại phân tích (bên dưới). Chọn phương pháp đơn giản nhất đủ trả lời.
4. Với mỗi kết quả chính tạo **một phát hiện F** + biểu đồ + nhận xét.
5. Kiểm tra độ tin cậy; ghi giới hạn.
6. Trình bày; mời người dùng góp ý (xem `feedback-interpreter`).

## Gợi ý phương pháp theo loại phân tích
| Loại | Cách làm | Biểu đồ phù hợp |
|------|----------|-----------------|
| Xu hướng | Chuỗi thời gian, trung bình trượt, tăng trưởng % kỳ trước/cùng kỳ, mùa vụ | Đường |
| So sánh nhóm | Tổng/TB/trung vị theo nhóm, chênh lệch tuyệt đối và %, tỷ trọng | Cột, cột ngang, cột chồng |
| Cơ cấu | Tỷ trọng, Pareto (80/20) | Tròn/donut (≤ 5 nhóm), Pareto |
| Nguyên nhân thay đổi | Phân rã (volume × price × mix), đóng góp từng nhóm vào mức thay đổi | Waterfall, cột |
| Tương quan | Hệ số tương quan, phân tán; nhắc tương quan ≠ nhân quả | Phân tán, heatmap |
| Phân phối | Histogram, boxplot, bách phân vị | Histogram, boxplot |
| Phân khúc | RFM, nhóm theo hành vi/giá trị | Cột, bubble |
| Bất thường | Điểm vượt ngưỡng (IQR/z-score), điểm gãy xu hướng | Đường có đánh dấu |
| Hiệu suất | Chỉ số so với mục tiêu/kỳ trước | Bullet, cột + đường mục tiêu |
| Dự báo (nếu yêu cầu) | Mô hình đơn giản; luôn nêu khoảng tin cậy và giả định | Đường + vùng bất định |

## Quy tắc biểu đồ
- Mỗi biểu đồ có: **tiêu đề nêu kết luận** (không chỉ "Doanh thu theo tháng"), nhãn trục kèm đơn vị, chú thích, nguồn dữ liệu (`clean_vN`, bộ lọc).
- Chọn loại biểu đồ đúng mục đích; tránh tròn khi > 5 nhóm; tránh trục cắt cụt gây hiểu lầm; tránh 3D.
- Không quá nhiều biểu đồ: mỗi Q 2–5 biểu đồ có ý nghĩa.
- Màu nhất quán xuyên báo cáo; không dựa vào màu duy nhất để truyền thông tin.

## Mẫu cho mỗi phát hiện
**F3 – Doanh thu Q3 giảm 12,4% so với Q2** (thuộc Q1, dữ liệu clean_v2)
- **Biểu đồ:** [đường doanh thu theo tháng]
- **Nhận xét biểu đồ (3 phần):**
  1. *Quan sát:* điều thấy trực tiếp (doanh thu tăng đến tháng 5, đạt 1,82 tỷ; giảm liên tục từ tháng 6; tháng 8 thấp nhất 1,31 tỷ)
  2. *Ý nghĩa:* điều đó cho biết gì (mức giảm tập trung từ giữa Q2, không phải đột ngột cuối kỳ)
  3. *Lưu ý:* hạn chế (thiếu dữ liệu 5 ngày đầu tháng 9; chưa xác định nguyên nhân)
- **Số liệu & cách tính:** doanh thu Q2 = ..., Q3 = ..., (Q3 − Q2)/Q2 = −12,4%
- **Nguồn:** bảng `orders`, cột `revenue`, `order_date`; lọc: bỏ đơn hủy
- **Độ tin cậy:** Cao/Trung bình/Thấp + lý do
- **Nhãn:** [Số liệu từ dữ liệu] | [Suy luận] | [Giả định]

## Kết thúc phần phân tích
1. **Tóm tắt phát hiện chính** (bảng F: ID | phát hiện | mức quan trọng | độ tin cậy)
2. **Những gì phân tích chưa trả lời được** và cần dữ liệu gì
3. Hỏi: "Bạn muốn chỉnh/đào sâu phân tích nào, hay sang bước đề xuất giải pháp?"
4. Ghi toàn bộ F vào sổ liên kết.

## Quy tắc
- Chỉ dùng dữ liệu trong tệp. Tham khảo bên ngoài phải ghi rõ nguồn và tách riêng.
- Không kết luận nhân quả từ tương quan. Dùng "có liên quan với", "khớp về thời điểm với".
- Không báo kết quả có ý nghĩa nếu mẫu quá nhỏ; nói rõ.
- Mọi con số phải tái tính được. Chạy lại nếu có nghi ngờ.
- Không "tối ưu hóa" biểu đồ theo hướng làm đẹp số liệu.
```

---

## Skill 8: `solution-proposal`

```markdown
---
name: solution-proposal
description: Từ các phát hiện F, xác định nguyên nhân (R) và đề xuất giải pháp (S), mỗi nguyên nhân và giải pháp đều liên kết trở lại bằng chứng trong phân tích.
---

# Quyền: CHỈ ĐỌC

## Quy trình
1. Nạp sổ liên kết: danh sách F, bối cảnh doanh nghiệp (quy mô, ngân sách, ràng buộc), mục tiêu.
2. **Xác định nguyên nhân (R)** từ các F:
   - Mỗi R ghi `dựa_trên: [F?]`
   - Phân loại: **Bằng chứng trực tiếp** (dữ liệu cho thấy rõ) / **Suy luận** (hợp lý nhưng chưa kiểm chứng) / **Giả định** (cần xác minh)
   - Nếu có nhiều cách giải thích, nêu giả thuyết cạnh tranh và dữ liệu nào phân biệt được chúng
   - Với nguyên nhân thuộc loại suy luận/giả định, ghi **cần kiểm chứng bằng gì**
3. **Đề xuất giải pháp (S)** cho từng R quan trọng:
   - Mỗi S ghi `giải_quyết: [R?]`, `dựa_trên: [F?]`
   - Đưa 1–3 phương án cho vấn đề lớn, có so sánh
   - Phù hợp quy mô và ràng buộc (không đề xuất chiến dịch 500 triệu cho cửa hàng nhỏ)
4. **Xếp ưu tiên** theo tác động × khả thi ÷ chi phí (ma trận 2×2: Làm ngay / Lên kế hoạch / Thử nghiệm nhỏ / Hoãn).
5. Trình bày; mời người dùng góp ý.

## Mẫu nguyên nhân
**R1 – Chi nhánh Cầu Giấy giảm mạnh nhất, kéo xuống phần lớn mức giảm chung**
- Dựa trên: F3 (doanh thu Q3 −12,4%), F5 (Cầu Giấy đóng góp 68% mức giảm), F6 (số đơn giảm, giá trị đơn TB ổn định)
- Loại: Bằng chứng trực tiếp (về *vị trí* của vấn đề); Suy luận (về *nguyên nhân sâu*: lượng khách giảm)
- Độ tin cậy: Trung bình
- Chưa kiểm chứng: có đối thủ mới/đổi giờ mở cửa không → dữ liệu hiện chưa có

## Mẫu giải pháp
**S1 – Chạy thử chương trình kéo khách quay lại tại Cầu Giấy**
- Giải quyết: R1 | Dựa trên: F3, F5, F6
- Hành động cụ thể: ...
- Tác động kỳ vọng: (định lượng dựa trên F; ví dụ "phục hồi 1/3 mức giảm ≈ X triệu/tháng", ghi rõ cách tính và giả định)
- Chi phí/nguồn lực/thời gian: ...
- Rủi ro và cách giảm: ...
- Điều kiện thành công: ...
- KPI đo hiệu quả: số đơn/ngày tại Cầu Giấy, tỷ lệ khách quay lại; mốc kiểm tra sau 4 tuần
- Ưu tiên: Làm ngay / ...

## Bảng liên kết bắt buộc cuối phần
| Phát hiện (F) | Nguyên nhân (R) | Giải pháp (S) | Ưu tiên |
|---|---|---|---|
| F3, F5, F6 | R1 | S1, S2 | Làm ngay |
Kiểm tra: không R nào thiếu F; không S nào thiếu R; F quan trọng nào chưa có R/S thì nêu lý do (ví dụ "chỉ là thông tin, không cần hành động").

## Quy tắc
- Ước tính tác động phải có công thức và giả định; không đưa con số "lấy từ trời".
- Không hứa chắc kết quả; dùng khoảng/kịch bản (thận trọng – cơ sở – lạc quan) nếu cần.
- Giải pháp ngoài khả năng chứng minh bằng dữ liệu hiện có → gắn nhãn "đề xuất kiểm chứng" thay vì "kết luận".
- Người dùng góp ý (ví dụ "ngân sách chỉ 20 triệu", "nguyên nhân thật là đối thủ mở bên cạnh") → `feedback-interpreter`: cập nhật bối cảnh/R, chỉnh S liên quan, báo phần báo cáo bị ảnh hưởng.
```

---

## Skill 9: `report-generation`

```markdown
---
name: report-generation
description: Tổng hợp báo cáo kết quả từ sổ liên kết (phân tích F, nguyên nhân R, giải pháp S) và bối cảnh doanh nghiệp. Mọi nội dung trong báo cáo phải truy được về F/R/S.
---

# Quyền: tạo tệp báo cáo (không đụng đến dữ liệu)

## Điều kiện trước khi viết
1. Có sổ liên kết với F, R, S và người dùng đã xem/chỉnh.
2. **Chạy kiểm tra nhất quán:**
   - F nào chưa được dùng/giải thích? R nào thiếu F? S nào thiếu R?
   - Mọi số trong báo cáo khớp với F gốc? Cùng một chỉ số có đúng một giá trị xuyên suốt?
   - Biểu đồ trong báo cáo khớp số liệu và phiên bản dữ liệu (`clean_vN`)?
   - Có phần nào đã lỗi thời do góp ý gần nhất chưa cập nhật?
   Có lệch → sửa hoặc hỏi người dùng. Không xuất báo cáo khi còn lệch.
3. Hỏi (nếu chưa biết): người đọc là ai, độ dài mong muốn, định dạng (Word/PDF/slide/trang web), ngôn ngữ.

## Cấu trúc báo cáo mặc định
1. **Tóm tắt điều hành** (≤ 1 trang): bối cảnh, 3–5 phát hiện chính, nguyên nhân chính, 3 hành động ưu tiên. Mỗi ý gắn [F?][R?][S?].
2. **Bối cảnh & mục tiêu:** từ hồ sơ bối cảnh và các yêu cầu Q.
3. **Dữ liệu & làm sạch:** nguồn dữ liệu, kỳ dữ liệu, tóm tắt làm sạch (đã loại/sửa gì, bao nhiêu), giới hạn dữ liệu.
4. **Kết quả phân tích:** theo từng Q: biểu đồ + nhận xét (quan sát / ý nghĩa / lưu ý), mã F.
5. **Nguyên nhân:** từng R, liên kết F, ghi mức độ chắc chắn (trực tiếp/suy luận/giả định).
6. **Giải pháp đề xuất:** từng S, liên kết R/F, ưu tiên, chi phí, rủi ro, KPI, lộ trình (ngắn/trung/dài hạn).
7. **Bảng truy vết:** F → R → S (như ở solution-proposal).
8. **Hạn chế & bước tiếp theo:** dữ liệu cần bổ sung, giả định cần kiểm chứng, kế hoạch đo lường.
9. **Phụ lục:** nhật ký làm sạch, định nghĩa chỉ số và công thức, bảng số liệu chi tiết.

## Quy tắc viết
- Mở đầu bằng kết luận, rồi mới đến bằng chứng. Câu ngắn, dùng ngôn ngữ người đọc dễ hiểu theo hồ sơ bối cảnh.
- **Phân biệt rõ** "dữ liệu cho thấy" (F), "chúng tôi cho rằng" (R suy luận), "cần kiểm chứng" (giả định). Không nói nhân quả như sự thật khi mới là suy luận.
- Không thêm số liệu, biểu đồ, kết luận mới chưa có trong sổ liên kết. Muốn thêm → quay lại G3/G4.
- Đơn vị, định dạng số, tiền tệ nhất quán toàn báo cáo.
- Biểu đồ trong báo cáo lấy từ phân tích (cùng số liệu), có tiêu đề nêu kết luận và nguồn.
- Che/ẩn thông tin cá nhân nhạy cảm nếu không cần.
- Tiêu đề báo cáo ghi: tên doanh nghiệp, kỳ dữ liệu, ngày tạo, phiên bản dữ liệu `clean_vN`, phiên bản báo cáo.

## Chỉnh sửa báo cáo theo góp ý
Người dùng góp ý (ví dụ "ngắn lại còn 2 trang", "bỏ phần X", "nhấn mạnh giải pháp S2", "đổi sang giọng văn cho chủ cửa hàng"):
1. `feedback-interpreter` nhận diện: chỉnh hình thức (làm luôn) hay chỉnh nội dung có ảnh hưởng đến số liệu/liên kết (cập nhật chuỗi F/R/S trước).
2. Nhắc lại hiểu biết, xuất phiên bản mới (báo cáo v2...), nêu đã đổi gì.
3. Chạy lại kiểm tra nhất quán trước khi gửi.

## Bàn giao
- Gửi tệp báo cáo cùng 3–4 câu tóm tắt.
- Nhắc phiên bản dữ liệu và báo cáo, các hạn chế chính.
- Hỏi người dùng muốn chỉnh gì hoặc xuất định dạng khác.
```

---

## Ví dụ luồng ngắn (minh họa liên kết)

1. **Thu thập:** Bối cảnh: chuỗi 3 cửa hàng thời trang, mục tiêu tìm nguyên nhân doanh thu Q3 giảm. Tải `orders.xlsx`. Báo cáo kiểm tra: 4,2% ô trống ở `region`; 120 dòng trùng; cột `note` vô nghĩa (Nhóm B); không có cột giá vốn nên không tính được lợi nhuận (Nhóm C).
2. **Làm sạch:** Agent đề xuất L1–L5. Người dùng: "Trùng thì giữ dòng mới nhất, còn ô trống `region` đừng điền, loại luôn." → Agent nhận diện MODIFY L1 + MODIFY L3, nhắc lại, trình bày v2, người dùng duyệt, Agent tạo `clean_v2`.
3. **Yêu cầu phân tích:** "Xem doanh thu giảm do chi nhánh nào, sản phẩm nào" → Q1 (nguyên nhân thay đổi; metrics doanh thu; dimensions chi nhánh, nhóm sản phẩm; so sánh Q3 vs Q2).
4. **Phân tích:** F1 doanh thu Q3 −12,4%; F2 Cầu Giấy chiếm 68% mức giảm; F3 nhóm áo khoác giảm 35%.
5. **Giải pháp:** R1 (dựa trên F2: vấn đề tập trung ở Cầu Giấy), R2 (dựa trên F3: giảm nhóm áo khoác, có thể do mùa vụ, **suy luận**). S1 giải quyết R1; S2 giải quyết R2.
6. **Báo cáo:** mỗi đoạn mang thẻ [F2][R1][S1]; bảng truy vết ở mục 7; kiểm tra nhất quán đạt rồi mới xuất.

## Gợi ý triển khai kỹ thuật
1. **Lưu trạng thái ở backend** (session state + sổ liên kết dạng JSON/DB), không chỉ trong ngữ cảnh chat. Đây là nền để các giai đoạn khớp nhau.
2. **Công cụ ghi tách riêng và cần `approval_token`** do UI sinh khi người dùng bấm "Duyệt kế hoạch làm sạch". Công cụ phân tích chỉ có quyền đọc.
3. **Tính toán bằng code (pandas/SQL), không để LLM tự tính nhẩm.** Mỗi F lưu kèm đoạn code/truy vấn tạo ra nó để tái tính.
4. **Biểu đồ sinh từ code** (matplotlib/plotly) với dữ liệu thật; LLM chỉ viết nhận xét dựa trên số liệu đã tính.
5. **Bộ kiểm thử:** tệp có ô trống toàn bộ, cột vô nghĩa, ngày lẫn dd/mm và mm/dd, trùng khóa nhưng khác giá trị, "ok" mơ hồ khi có 2 kế hoạch đang chờ, đổi quy tắc làm sạch sau khi đã có báo cáo (kiểm tra F/R/S/báo cáo có được đánh dấu cập nhật không).
6. **Google Sheets:** dùng OAuth quyền chỉ đọc; chụp snapshot khi tải; không ghi ngược vào Sheet gốc.
