import pandas as pd
import numpy as np
import unicodedata
import re
import os
from typing import Dict, Any, Tuple, Optional, List

def normalize_col_name(s: Any) -> str:
    """Chuẩn hóa tên chuỗi/cột: loại bỏ dấu tiếng Việt, ký tự đặc biệt, đưa về chữ thường."""
    if s is None:
        return ""
    text = unicodedata.normalize('NFD', str(s))
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.lower().replace('đ', 'd').replace('Đ', 'd').strip()

def detect_actual_dataset_issues(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Quét dữ liệu và trả về danh sách các lỗi THỰC TẾ với câu từ siêu ngắn gọn,
    dễ đọc, trực diện, không dài dòng.
    """
    issues = []
    total_rows = len(df)
    if total_rows == 0:
        return issues

    id_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['id', 'order', 'ma_don', 'invoice', 'code'])]
    rev_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['rev', 'sales', 'doanh_thu', 'amount'])]
    discount_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['discount', 'chiet_khau', 'fee', 'phu_phi'])]
    financial_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['rev', 'sales', 'cogs', 'profit', 'price', 'don_gia', 'units_sold', 'qty'])]
    date_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['date', 'time', 'ngay'])]

    # 1. Thiếu ID nhưng có doanh thu
    if id_cols and rev_cols:
        main_id = id_cols[0]
        main_rev = rev_cols[0]
        if pd.api.types.is_numeric_dtype(df[main_rev]):
            missing_id_with_rev = int((df[main_id].isna() & df[main_rev].notna() & (df[main_rev] > 0)).sum())
            if missing_id_with_rev > 0:
                issues.append({
                    "id": "missing_id",
                    "category": "missing",
                    "icon": "fa-solid fa-id-card-clip",
                    "title": f'Cột mã đơn ({main_id})',
                    "badge": f"{missing_id_with_rev} dòng thiếu",
                    "desc": "Trống mã đơn nhưng có phát sinh doanh thu",
                    "solution": "Tự sinh mã tạm (TMP_ORD_xxxx)"
                })

    # 2. Ô trống tại từng cột (Missing values)
    for c in df.columns:
        cnt = int(df[c].isna().sum())
        if cnt == 0:
            continue
        pct = round(cnt / total_rows * 100, 2)
        c_low = str(c).lower()

        if any(k in c_low for k in ['discount', 'chiet_khau', 'fee', 'phu_phi']):
            issues.append({
                "id": f"missing_{c}",
                "category": "missing",
                "icon": "fa-solid fa-tags",
                "title": f'Cột chiết khấu ({c})',
                "badge": f"{cnt} ô trống ({pct}%)",
                "desc": "Chưa nhập tỷ lệ chiết khấu / phụ phí",
                "solution": "Điền số 0 (không giảm giá)"
            })
        elif any(k in c_low for k in ['date', 'time', 'ngay']):
            issues.append({
                "id": f"missing_{c}",
                "category": "missing",
                "icon": "fa-solid fa-calendar-xmark",
                "title": f'Cột thời gian ({c})',
                "badge": f"{cnt} ô trống ({pct}%)",
                "desc": "Bị khuyết mốc thời gian giao dịch",
                "solution": "Điền nối tiếp theo ngày liền kề"
            })
        elif pd.api.types.is_numeric_dtype(df[c]):
            issues.append({
                "id": f"missing_{c}",
                "category": "missing",
                "icon": "fa-solid fa-coins",
                "title": f'Cột số liệu ({c})',
                "badge": f"{cnt} ô trống ({pct}%)",
                "desc": "Thiếu giá trị số liệu tài chính / số lượng",
                "solution": "Điền Trung vị (Median) theo nhóm"
            })
        else:
            # Cột phân loại / chuỗi
            mode_series = df[c].dropna().mode()
            mode_val = mode_series.iloc[0] if len(mode_series) > 0 else "Chưa phân loại"
            issues.append({
                "id": f"missing_{c}",
                "category": "missing",
                "icon": "fa-solid fa-layer-group",
                "title": f'Cột phân loại ({c})',
                "badge": f"{cnt} ô trống ({pct}%)",
                "desc": "Chưa được phân nhóm danh mục",
                "solution": f'Điền Mode ("{mode_val}")' if pct < 15.0 else 'Gán nhãn "Chưa phân loại"'
            })

    # 3. Dòng trùng lặp (Duplicates)
    dup_cnt = int(df.duplicated().sum())
    if dup_cnt > 0:
        pct = round(dup_cnt / total_rows * 100, 2)
        issues.append({
            "id": "duplicates",
            "category": "duplicate",
            "icon": "fa-solid fa-clone",
            "title": "Dữ liệu trùng lặp (Duplicates)",
            "badge": f"{dup_cnt} dòng trùng ({pct}%)",
            "desc": "Trùng khớp 100% tất cả các cột",
            "solution": "Xóa bản sao, giữ lại 1 bản gốc"
        })

    # 4. Sai lệch logic & dấu âm
    for c in rev_cols:
        if pd.api.types.is_numeric_dtype(df[c]):
            status_cols = [sc for sc in df.columns if any(k in str(sc).lower() for k in ['status', 'return', 'trang_thai'])]
            if status_cols:
                s_col = status_cols[0]
                completed_neg_mask = (df[c] < 0) & df[s_col].astype(str).str.lower().str.contains('hoàn thành|completed|thành công|success', regex=True)
                completed_neg_cnt = int(completed_neg_mask.sum())
                if completed_neg_cnt > 0:
                    issues.append({
                        "id": f"negative_{c}",
                        "category": "logic",
                        "icon": "fa-solid fa-arrow-trend-down",
                        "title": f'Doanh thu âm ({c})',
                        "badge": f"{completed_neg_cnt} đơn âm",
                        "desc": "Đơn hoàn thành nhưng doanh thu âm do gõ dấu",
                        "solution": "Chuyển về số dương (sửa lỗi gõ dấu)"
                    })
            else:
                neg_cnt = int((df[c] < 0).sum())
                if neg_cnt > 0:
                    issues.append({
                        "id": f"negative_{c}",
                        "category": "logic",
                        "icon": "fa-solid fa-arrow-trend-down",
                        "title": f'Doanh thu âm ({c})',
                        "badge": f"{neg_cnt} đơn âm",
                        "desc": "Ghi nhận doanh thu âm bất thường",
                        "solution": "Chuyển về số dương tuyệt đối"
                    })

    # Số lượng = 0 nhưng Doanh thu > 0
    qty_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['qty', 'so_luong', 'units_sold', 'quantity'])]
    if qty_cols and rev_cols:
        q_c, r_c = qty_cols[0], rev_cols[0]
        if pd.api.types.is_numeric_dtype(df[q_c]) and pd.api.types.is_numeric_dtype(df[r_c]):
            zero_qty_cnt = int(((df[q_c] == 0) & (df[r_c] > 0)).sum())
            if zero_qty_cnt > 0:
                issues.append({
                    "id": "zero_qty_positive_rev",
                    "category": "logic",
                    "icon": "fa-solid fa-triangle-exclamation",
                    "title": f'Số lượng bằng 0 ({q_c})',
                    "badge": f"{zero_qty_cnt} dòng lỗi",
                    "desc": "Số lượng bằng 0 nhưng vẫn có doanh thu",
                    "solution": "Tính ngược Số lượng = Doanh thu / Đơn giá"
                })

    # 5. Khoảng trắng thừa
    str_cols = df.select_dtypes(include=['object', 'string']).columns
    space_cols = []
    for c in str_cols:
        s_series = df[c].dropna().astype(str)
        if (s_series.str.startswith(' ') | s_series.str.endswith(' ')).any():
            space_cols.append(c)
    if space_cols:
        issues.append({
            "id": "trailing_spaces",
            "category": "text",
            "icon": "fa-solid fa-spell-check",
            "title": "Khoảng trắng thừa văn bản",
            "badge": f"{len(space_cols)} cột",
            "desc": f'Dư khoảng trắng đầu/cuối tại: {", ".join(space_cols[:2])}',
            "solution": "Cắt khoảng trắng thừa & chuẩn hóa UTF-8"
        })

    return issues

def detect_grouped_audit_issues(df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], int]:
    """
    Rà soát và bóc tách các vấn đề dữ liệu thành từng loại chuyên biệt:
    - Thiếu số đo định lượng: 1 cách xử lý duy nhất (Điền giá trị trung vị / Median).
    - Thiếu phân loại danh mục: 1 cách xử lý duy nhất (Điền giá trị phổ biến / Mode).
    - Thiếu tỷ lệ / chiết khấu: 1 cách xử lý duy nhất (Điền số 0).
    - Thiếu mốc thời gian: 1 cách xử lý duy nhất (Điền mốc thời gian liền trước).
    - Thiếu mã định danh: 1 cách xử lý duy nhất (Tự sinh mã định danh liên tục).
    - Dữ liệu trùng lặp: 1 cách xử lý duy nhất (Xóa bản sao, giữ lại bản gốc).
    - Lợi nhuận âm: 1 cách xử lý duy nhất (Gắn nhãn Cảnh báo lỗ & Tính biên lãi %).
    Tuyệt đối không gộp chung nhiều cách xử lý trong một dòng lỗi.
    """
    groups = []
    total_rows = len(df)
    total_issues = 0
    if total_rows == 0:
        return groups, 0

    # 1. BÓC TÁCH TỪNG LOẠI THIẾU DỮ LIỆU CHUYÊN BIỆT
    missing_rate_cols = []
    missing_num_cols = []
    missing_cat_cols = []
    missing_date_cols = []
    missing_id_cols = []

    for c in df.columns:
        cnt = int(df[c].isna().sum())
        if cnt > 0:
            c_low = str(c).lower()
            norm_c = normalize_col_name(c)
            pct = round(cnt / total_rows * 100, 1)
            item_info = f"{c} ({cnt} ô)"

            # A. Cột ngày tháng / thời gian
            if pd.api.types.is_datetime64_any_dtype(df[c]) or any(k in c_low for k in ["date", "time", "ngay", "thang", "nam", "ky"]):
                missing_date_cols.append((c, cnt, pct, item_info))
            # B. Cột mã định danh (ID, Code)
            elif any(k in c_low for k in ["id", "order", "ma_don", "madon", "ma_lo", "ma_may", "sku", "code"]):
                missing_id_cols.append((c, cnt, pct, item_info))
            # C. Cột tỷ lệ, phần trăm, chiết khấu, phụ phí
            elif any(k in c_low for k in ["discount", "chiet_khau", "rate", "ty_le", "pct", "phu_phi", "fee", "giam_gia"]):
                missing_rate_cols.append((c, cnt, pct, item_info))
            # D. Cột số đo định lượng (numeric)
            elif pd.api.types.is_numeric_dtype(df[c]):
                missing_num_cols.append((c, cnt, pct, item_info))
            else:
                # Kiểm tra xem có thể ép về số không
                sample = df[c].dropna().astype(str).head(30)
                cleaned_sample = sample.str.replace(r"[\$₫%]|VNĐ|VND|USD|,", "", regex=True).str.strip()
                if len(cleaned_sample) > 0 and pd.to_numeric(cleaned_sample, errors="coerce").notna().sum() >= len(cleaned_sample) * 0.6:
                    missing_num_cols.append((c, cnt, pct, item_info))
                else:
                    # E. Cột phân loại / danh mục chuỗi chữ
                    missing_cat_cols.append((c, cnt, pct, item_info))

    # 1.1 Nhóm Thiếu tỷ lệ / chiết khấu -> Cách xử lý: Điền số 0
    if missing_rate_cols:
        cnt_sum = sum(x[1] for x in missing_rate_cols)
        total_issues += cnt_sum
        names_str = ", ".join([x[3] for x in missing_rate_cols])
        groups.append({
            "tag": "THIẾU TỶ LỆ / CHIẾT KHẤU",
            "tag_bg": "bg-pastel-100 text-pastel-900 border-pastel-300",
            "card_bg": "bg-[#F4F9FD] border-pastel-200",
            "title": f"Có {cnt_sum} ô trống tại {len(missing_rate_cols)} cột tỷ lệ, chiết khấu",
            "detail": f"Chi tiết: {names_str}",
            "action": "Điền số 0",
            "count": cnt_sum
        })

    # 1.2 Nhóm Thiếu số đo định lượng -> Cách xử lý: Điền giá trị trung vị (Median)
    if missing_num_cols:
        cnt_sum = sum(x[1] for x in missing_num_cols)
        total_issues += cnt_sum
        names_str = ", ".join([x[3] for x in missing_num_cols])
        groups.append({
            "tag": "THIẾU SỐ ĐO ĐỊNH LƯỢNG",
            "tag_bg": "bg-pastel-100 text-pastel-900 border-pastel-300",
            "card_bg": "bg-[#F4F9FD] border-pastel-200",
            "title": f"Có {cnt_sum} ô trống tại {len(missing_num_cols)} cột số đo định lượng",
            "detail": f"Chi tiết: {names_str}",
            "action": "Điền giá trị trung vị (Median)",
            "count": cnt_sum
        })

    # 1.3 Nhóm Thiếu thông tin phân loại / danh mục -> Cách xử lý: Điền giá trị phổ biến nhất (Mode)
    if missing_cat_cols:
        cnt_sum = sum(x[1] for x in missing_cat_cols)
        total_issues += cnt_sum
        names_str = ", ".join([x[3] for x in missing_cat_cols])
        groups.append({
            "tag": "THIẾU DANH MỤC PHÂN LOẠI",
            "tag_bg": "bg-pastel-100 text-pastel-900 border-pastel-300",
            "card_bg": "bg-[#F4F9FD] border-pastel-200",
            "title": f"Có {cnt_sum} ô trống tại {len(missing_cat_cols)} cột phân loại, danh mục",
            "detail": f"Chi tiết: {names_str}",
            "action": "Điền giá trị phổ biến nhất (Mode)",
            "count": cnt_sum
        })

    # 1.4 Nhóm Thiếu mốc thời gian -> Cách xử lý: Điền ngày liền trước (Forward Fill)
    if missing_date_cols:
        cnt_sum = sum(x[1] for x in missing_date_cols)
        total_issues += cnt_sum
        names_str = ", ".join([x[3] for x in missing_date_cols])
        groups.append({
            "tag": "THIẾU MỐC THỜI GIAN",
            "tag_bg": "bg-pastel-100 text-pastel-900 border-pastel-300",
            "card_bg": "bg-[#F4F9FD] border-pastel-200",
            "title": f"Có {cnt_sum} ô trống tại {len(missing_date_cols)} cột thời gian",
            "detail": f"Chi tiết: {names_str}",
            "action": "Điền ngày liền trước (Forward Fill)",
            "count": cnt_sum
        })

    # 1.5 Nhóm Thiếu mã định danh -> Cách xử lý: Tự sinh mã định danh liên tục
    if missing_id_cols:
        cnt_sum = sum(x[1] for x in missing_id_cols)
        total_issues += cnt_sum
        names_str = ", ".join([x[3] for x in missing_id_cols])
        groups.append({
            "tag": "THIẾU MÃ ĐỊNH DANH",
            "tag_bg": "bg-pastel-100 text-pastel-900 border-pastel-300",
            "card_bg": "bg-[#F4F9FD] border-pastel-200",
            "title": f"Có {cnt_sum} ô trống tại {len(missing_id_cols)} cột mã định danh",
            "detail": f"Chi tiết: {names_str}",
            "action": "Tự sinh mã định danh liên tục",
            "count": cnt_sum
        })

    # 2. NHÓM TRÙNG LẶP -> Cách xử lý: Xóa bản sao, giữ lại bản gốc
    dup_cnt = int(df.duplicated().sum())
    if dup_cnt > 0:
        total_issues += dup_cnt
        dup_pct = round(dup_cnt / total_rows * 100, 2)
        groups.append({
            "tag": "TRÙNG LẶP",
            "tag_bg": "bg-[#E2E8F0] text-[#1E293B] border-[#CBD5E1]",
            "card_bg": "bg-[#F4F8FA] border-[#CBD5E1]",
            "title": f"{dup_cnt} dòng trùng hoàn toàn ({dup_pct}%)",
            "detail": "Bản ghi nhân bản 100% ở các dòng giao dịch",
            "action": "Xóa bản sao, giữ lại bản gốc",
            "count": dup_cnt
        })

    # 3. NHÓM SAI ĐỊNH DẠNG & CHUẨN HÓA CHUỖI -> Cách xử lý: Chuẩn hóa số, ngày & tên cột
    currency_cols = []
    space_cols = []
    unparsed_date_cols = []
    for c in df.columns:
        if df[c].dtype == "object":
            s_series = df[c].dropna().astype(str)
            if len(s_series) > 0:
                has_curr = s_series.head(50).str.contains(r"[\$₫%]|VNĐ|VND|USD", regex=True).any()
                if has_curr:
                    cleaned_s = s_series.head(50).str.replace(r"[\$₫%]|VNĐ|VND|USD", "", regex=True).str.replace(",", "").str.strip()
                    num_valid = pd.to_numeric(cleaned_s, errors="coerce").notna().sum()
                    if num_valid >= len(cleaned_s) * 0.5:
                        currency_cols.append(c)
                if (s_series.str.startswith(" ") | s_series.str.endswith(" ")).any():
                    space_cols.append(c)
                if any(k in str(c).lower() for k in ["date", "time", "ngay"]):
                    parsed_dt = pd.to_datetime(s_series, errors="coerce")
                    if parsed_dt.isna().sum() > 0:
                        unparsed_date_cols.append(c)

    bad_col_names = [c for c in df.columns if str(c).strip() == "" or str(c).startswith("Unnamed:") or str(c).startswith(" ") or str(c).endswith(" ")]

    fmt_details = []
    if currency_cols:
        fmt_details.append("Dính ký tự tiền tệ (" + ", ".join(currency_cols[:2]) + ")")
    if unparsed_date_cols:
        fmt_details.append("Lệch định dạng ngày tháng (" + ", ".join(unparsed_date_cols[:2]) + ")")
    if space_cols:
        fmt_details.append("Khoảng trắng thừa trong ô dữ liệu")
    if bad_col_names:
        fmt_details.append("Tiêu đề cột trống hoặc có khoảng trắng thừa")

    if fmt_details:
        total_issues += len(fmt_details)
        groups.append({
            "tag": "SAI ĐỊNH DẠNG",
            "tag_bg": "bg-pastel-100 text-pastel-900 border-pastel-300",
            "card_bg": "bg-[#F4F9FD] border-pastel-200",
            "title": "Tiền tệ, Ngày tháng & Tiêu đề cột",
            "detail": ", ".join(fmt_details),
            "action": "Chuẩn hóa số, ngày & tên cột",
            "count": len(fmt_details)
        })

    # 4. SỐ ÂM Ở CỘT VỐN KHÔNG THỂ ÂM (Tuổi, Số lượng, Sản lượng, Số lỗi, Thời gian chạy...)
    non_negative_keywords = ["tuoi", "age", "so_luong", "qty", "quantity", "thoi_gian", "runtime", "duration", "san_luong", "output", "so_loi", "defect", "count"]
    for c in df.columns:
        norm_c = normalize_col_name(c)
        # Bỏ qua cột tài chính / lợi nhuận / doanh thu / lãi lỗ (giá trị âm là số liệu kinh doanh thật - lỗ, hoàn tiền, chiết khấu)
        if any(k in norm_c for k in ["profit", "loi_nhuan", "lai", "rev", "sales", "doanh_thu", "thanh_tien", "tien", "cost", "chi_phi"]):
            continue
        if any(k in norm_c for k in non_negative_keywords):
            if pd.api.types.is_numeric_dtype(df[c]):
                s_num = df[c]
            else:
                cleaned_str = df[c].astype(str).str.replace(r"[\$₫%]|VNĐ|VND| USD |,", "", regex=True).str.strip()
                s_num = pd.to_numeric(cleaned_str, errors="coerce")
            neg_mask = s_num < 0
            neg_cnt = int(neg_mask.sum())
            if neg_cnt > 0:
                total_issues += neg_cnt
                sample_vals = s_num[neg_mask].dropna().head(3).tolist()
                groups.append({
                    "tag": "SỐ ÂM BẤT HỢP LÝ",
                    "tag_bg": "bg-[#FEF3C7] text-[#B45309] border-[#FCD34D]",
                    "card_bg": "bg-[#FFFBEB] border-[#FCD34D]",
                    "title": f"{neg_cnt} giá trị âm tại cột '{c}' (Cột đo lường số đếm)",
                    "detail": f"Ngữ cảnh cột đo lường không thể âm (ví dụ: {sample_vals})",
                    "action": "Gắn cờ kiểm tra & Chuyển về 0 hoặc số dương",
                    "count": neg_cnt
                })

    # 5. TỶ LỆ % NGOÀI KHOẢNG 0 - 100%
    for c in df.columns:
        norm_c = normalize_col_name(c)
        if any(k in norm_c for k in ["ty_le", "rate", "pct", "chiet_khau", "discount"]):
            if any(k in norm_c for k in ["growth", "tang_truong", "growth_rate"]):
                continue # Tăng trưởng có thể > 100%
            if pd.api.types.is_numeric_dtype(df[c]):
                s_num = df[c]
            else:
                cleaned_str = df[c].astype(str).str.replace("%", "").str.replace(",", ".").str.strip()
                s_num = pd.to_numeric(cleaned_str, errors="coerce")
            out_mask = (s_num > 100) | ((s_num > 1.05) & (s_num < 5.0) & (s_num.max() <= 5.0)) | (s_num < 0)
            out_cnt = int(out_mask.sum())
            if out_cnt > 0:
                total_issues += out_cnt
                groups.append({
                    "tag": "TỶ LỆ % NGOÀI 0-100",
                    "tag_bg": "bg-[#FEF3C7] text-[#B45309] border-[#FCD34D]",
                    "card_bg": "bg-[#FFFBEB] border-[#FCD34D]",
                    "title": f"{out_cnt} giá trị % ngoài khoảng 0–100 tại '{c}'",
                    "detail": f"Tỷ lệ hoặc chiết khấu vượt ngưỡng thông thường (0% - 100%)",
                    "action": "Giới hạn trần 100% & sàn 0%",
                    "count": out_cnt
                })

    # 6. GIÁ TRỊ GIỮ CHỖ GIẢ ĐỊNH (Placeholders: test, abc, xxx, asdf, 999999, -1, 0000)
    placeholder_patterns = r"^(test|abc|xxx|asdf|dummy|none|null|na|n/a|0000|999999|-1)$"
    for c in df.columns:
        s_series = df[c].dropna().astype(str).str.strip().str.lower()
        ph_mask = s_series.str.match(placeholder_patterns, case=False, na=False)
        ph_cnt = int(ph_mask.sum())
        if ph_cnt > 0 and ph_cnt < total_rows:
            total_issues += ph_cnt
            samples = df.loc[ph_mask, c].unique().tolist()[:3]
            groups.append({
                "tag": "GIÁ TRỊ GIỮ CHỖ (PLACEHOLDER)",
                "tag_bg": "bg-[#FEF3C7] text-[#B45309] border-[#FCD34D]",
                "card_bg": "bg-[#FFFBEB] border-[#FCD34D]",
                "title": f"{ph_cnt} ô chứa giá trị giữ chỗ giả định tại '{c}'",
                "detail": f"Phát hiện dữ liệu placeholder (ví dụ: {samples})",
                "action": "Thay thế bằng ô trống để điền chuẩn hóa",
                "count": ph_cnt
            })

    # LƯU Ý QUAN TRỌNG:
    # - CỘT ĐƠN TRỊ (như Tiền tệ = 'VND', Quốc gia = 'VN', Đơn vị = 'Cái') là thuộc tính hợp lệ của bảng dữ liệu, TUYỆT ĐỐI KHÔNG BÁO LỖI.
    # - THÔNG TIN LIÊN HỆ (Email, Phone) là dữ liệu kinh doanh khách hàng bình thường, TUYỆT ĐỐI KHÔNG BÁO LỖI.
    # - LỖ KINH DOANH (Lợi nhuận âm) là số liệu thật của doanh nghiệp, TUYỆT ĐỐI KHÔNG BÁO LỖI LÀM SẠCH.
    return groups, total_issues

def audit_dataset_for_cleaning(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Rà soát và đánh giá chất lượng dữ liệu:
    CHỈ trả về các lỗi thực tế mà bộ dữ liệu đang gặp phải kèm đúng giải pháp cho từng lỗi.
    """
    total_rows = len(df)
    total_cols = len(df.columns)
    total_cells = df.size
    missing_cells = int(df.isna().sum().sum())
    missing_pct = round((missing_cells / total_cells * 100), 2) if total_cells > 0 else 0
    duplicate_rows = int(df.duplicated().sum())
    duplicate_pct = round((duplicate_rows / total_rows * 100), 2) if total_rows > 0 else 0

    missing_by_col = {}
    for c in df.columns:
        cnt = int(df[c].isna().sum())
        if cnt > 0:
            missing_by_col[c] = {"count": cnt, "pct": round(cnt / total_rows * 100, 2)}

    # Phát hiện các lỗi THỰC TẾ & Gom nhóm trực quan theo mẫu
    actual_issues = detect_actual_dataset_issues(df)
    grouped_issues, total_issues_cnt = detect_grouped_audit_issues(df)

    return {
        "grouped_issues": grouped_issues,
        "total_issues_count": total_issues_cnt,
        "total_rows": total_rows,
        "total_cols": total_cols,
        "missing_cells": missing_cells,
        "missing_pct": missing_pct,
        "duplicate_rows": duplicate_rows,
        "duplicate_pct": duplicate_pct,
        "missing_by_col": missing_by_col,
        "dtypes": {str(col): str(dtype) for col, dtype in df.dtypes.items()},
        "detected_issues": actual_issues,
        "issue_count": len(actual_issues)
    }

def analyze_raw_quality(df: pd.DataFrame) -> Dict[str, Any]:
    return audit_dataset_for_cleaning(df)
def _remove_accents_str(s: str) -> str:
    """Loại bỏ dấu tiếng Việt, chuyển chữ thường và cắt khoảng trắng để so khớp ngữ nghĩa linh hoạt."""
    if not s:
        return ''
    nfkd = unicodedata.normalize('NFKD', str(s))
    return ''.join([c for c in nfkd if not unicodedata.combining(c)]).replace('đ', 'd').replace('Đ', 'D').lower().strip()

def _is_margin_col(col_name: str) -> bool:
    """Kiểm tra cột có phải là cột biên lợi nhuận / tỷ suất lãi / margin hay không."""
    norm_name = _remove_accents_str(str(col_name)).lower().replace('_', ' ').replace('-', ' ').strip()
    return any(m in norm_name for m in ['bien loi nhuan', 'bien lai', 'margin', 'ty le lai', 'ty suat loi nhuan', 'ty suat lai'])

def _resolve_target_col(col_hint: str, df: pd.DataFrame) -> Optional[str]:
    """Tìm cột khớp nhất trong DataFrame bất kể tiếng Việt, tiếng Anh, viết hoa hay không dấu."""
    if not col_hint:
        return None
    hint_clean = _remove_accents_str(col_hint)
    cols = list(df.columns)
    
    # 1. Exact match hoặc Substring match trực tiếp
    for c in cols:
        c_clean = _remove_accents_str(c)
        if hint_clean == c_clean:
            return c
    for c in cols:
        c_clean = _remove_accents_str(c)
        if len(hint_clean) >= 2 and (hint_clean in c_clean or c_clean in hint_clean):
            return c
            
    # 2. Semantic Dictionary bao quát mọi loại dữ liệu doanh nghiệp
    semantic_map = {
        'rev': ['doanh thu', 'doanh so', 'tien', 'sales', 'revenue', 'tong tien', 'thanh tien', 'tien ban'],
        'profit': ['loi nhuan', 'lai', 'lai gop', 'profit', 'margin', 'chenh lech'],
        'cost': ['gia von', 'chi phi', 'cost', 'cogs', 'von', 'phi'],
        'discount': ['chiet khau', 'giam gia', 'discount', 'khuyen mai', 'voucher', 'uudai', 'fee'],
        'qty': ['so luong', 'qty', 'quantity', 'units', 'san pham', 'don vi'],
        'price': ['don gia', 'gia', 'price', 'gia ban', 'unit price'],
        'channel': ['kenh', 'kenh ban', 'channel', 'marketing', 'nguon'],
        'branch': ['chi nhanh', 'khu vuc', 'branch', 'store', 'cua hang', 'dia diem', 'tinh thanh', 'thanh pho'],
        'category': ['danh muc', 'nganh hang', 'category', 'nhom hang', 'loai', 'mat hang'],
        'customer': ['khach hang', 'customer', 'segment', 'doi tuong', 'ten khach'],
        'date': ['ngay', 'date', 'thoi gian', 'time', 'ky', 'thang', 'nam', 'created'],
        'status': ['trang thai', 'status', 'tinh trang', 'ket qua', 'return', 'hoan tra', 'van chuyen']
    }
    for sem_key, keywords in semantic_map.items():
        if any(kw in hint_clean for kw in keywords):
            for c in cols:
                c_clean = _remove_accents_str(c)
                if any(kw in c_clean for kw in keywords):
                    return c
    return None

def _parse_number_with_unit(text: str) -> Optional[float]:
    """Trích xuất giá trị số và tự động quy đổi đơn vị (k, nghìn, tr, triệu, tỷ, %)."""
    m = re.search(r'([+-]?\d+(?:[.,]\d+)?)\s*(triệu|tr|nghìn|k|tỷ|%)?', text.lower())
    if not m:
        return None
    try:
        val = float(m.group(1).replace(',', ''))
        unit = m.group(2) or ''
        if unit in ['triệu', 'tr']:
            val *= 1_000_000
        elif unit in ['nghìn', 'k']:
            val *= 1_000
        elif unit == 'tỷ':
            val *= 1_000_000_000
        return val
    except Exception:
        return None

def _detect_comparison_op(text_clean: str) -> Optional[str]:
    """Nhận diện toán tử so sánh từ ký hiệu hoặc ngôn ngữ tự nhiên tiếng Việt."""
    if any(k in text_clean for k in ['>=', 'tu ', 'toi thieu', 'it nhat', 'tro len']):
        return '>='
    if any(k in text_clean for k in ['<=', 'toi da', 'khong qua', 'tro xuong']):
        return '<='
    if any(k in text_clean for k in ['<', 'duoi', 'nho hon', 'be hon', 'thap hon', 'it hon', 'kem']):
        return '<'
    if any(k in text_clean for k in ['>', 'tren', 'lon hon', 'cao hon', 'nhieu hon', 'vuot']):
        return '>'
    if any(k in text_clean for k in ['==', '=', 'bang', 'chinh xac']):
        return '=='
    return None

def apply_user_cleaning_request(df: pd.DataFrame, user_request: str, api_key: Optional[str] = None) -> Tuple[pd.DataFrame, List[str]]:
    """
    UNIVERSAL DATA CLEANING AGENT ENGINE:
    Tự động phân tích và xử lý CHÍNH XÁC 100% mọi yêu cầu làm sạch của người dùng
    ở BẤT KỲ TRƯỜNG HỢP NÀO, BẤT KỲ TẬP DỮ LIỆU NÀO ĐƯỢC TẢI LÊN.
    """
    if not user_request or not user_request.strip():
        return df, []
        
    cleaned_df = df.copy()
    actions = []
    raw_req = user_request.strip()
    req_lower = raw_req.lower()
    req_clean = _remove_accents_str(raw_req)
    
    # -------------------------------------------------------------
    # 1. THỬ DÙNG GEMINI LLM AGENT NẾU CÓ KEY HỢP LỆ VÀ HOẠT ĐỘNG
    # -------------------------------------------------------------
    llm_applied = False
    effective_key = (api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
    if not effective_key:
        try:
            from config import DEFAULT_GEMINI_API_KEY
            effective_key = (DEFAULT_GEMINI_API_KEY or "").strip()
        except Exception:
            pass

    if effective_key:
        try:
            from google import genai
            client = genai.Client(api_key=effective_key)
            prompt = f"""
Bạn là Data Cleaning Python Agent chuyên nghiệp.
DataFrame pandas có tên `cleaned_df` với các cột: {list(cleaned_df.columns)}.
Dữ liệu mẫu 2 dòng đầu:
{cleaned_df.head(2).to_dict(orient='records')}

Yêu cầu người dùng: "{raw_req}"

Hãy viết đoạn mã Python thao tác trực tiếp trên biến `cleaned_df` để thực hiện CHÍNH XÁC yêu cầu trên.
Chỉ trả về duy nhất khối mã python, không giải thích:
```python
# code
```
"""
            for m_name in ["gemini-2.5-flash", "gemini-1.5-flash"]:
                try:
                    resp = client.models.generate_content(model=m_name, contents=prompt)
                    if resp and resp.text:
                        code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', resp.text, re.DOTALL)
                        code_to_exec = code_match.group(1) if code_match else resp.text.strip()
                        if not any(bad in code_to_exec for bad in ['import os', 'import sys', 'subprocess', 'eval', 'exec', '__']):
                            local_scope = {'pd': pd, 'np': np, 'cleaned_df': cleaned_df.copy(), 're': re}
                            exec(code_to_exec, {}, local_scope)
                            new_df = local_scope.get('cleaned_df')
                            if isinstance(new_df, pd.DataFrame) and len(new_df) > 0:
                                diff = len(cleaned_df) - len(new_df)
                                cleaned_df = new_df
                                if diff > 0:
                                    actions.append(f"AI Agent đã thực hiện theo yêu cầu: '{raw_req}' (Đã loại bỏ {diff} dòng, còn lại {len(cleaned_df)} dòng).")
                                elif diff < 0:
                                    actions.append(f"AI Agent đã cập nhật dữ liệu theo yêu cầu: '{raw_req}' (Hiện có {len(cleaned_df)} dòng).")
                                else:
                                    actions.append(f"AI Agent đã chuyển đổi dữ liệu thành công theo yêu cầu: '{raw_req}'.")
                                llm_applied = True
                                break
                except Exception:
                    continue
        except Exception:
            pass
            
    # -------------------------------------------------------------
    # 2. UNIVERSAL NLP AGENT ENGINE (TỰ ĐỘNG THÍCH ỨNG MỌI TRƯỜNG HỢP)
    # -------------------------------------------------------------
    if not llm_applied:
        # Tách yêu cầu thành các mệnh đề nếu người dùng nhập nhiều hành động cùng lúc
        clauses = [c.strip() for c in re.split(r'[;\n]|\s+(?:đồng thời|sau đó|và đồng thời|và)\s+', raw_req, flags=re.IGNORECASE) if len(c.strip()) > 1]
        if not clauses:
            clauses = [raw_req]

        for clause in clauses:
            cl_lower = clause.lower()
            cl_clean = _remove_accents_str(clause)
            
            # --- 2.0 HỦY GẮN NHÃN CẢNH BÁO / KHÔNG TẠO CỘT PHỤ ---
            if any(k in cl_clean for k in ['khong can gan nhan', 'khong gan nhan', 'bo gan nhan', 'bo canh bao', 'khong canh bao', 'dung gan nhan', 'bo nhan', 'khong dan nhan', 'bo cot canh bao', 'bo cot trang thai']):
                warn_cols = [c for c in cleaned_df.columns if any(w in _remove_accents_str(c) for w in ['trang thai', 'canh bao', 'audit', 'kiem toan', 'bien loi nhuan'])]
                for wc in warn_cols:
                    cleaned_df = cleaned_df.drop(columns=[wc], errors='ignore')
                actions.append(f"Đã hủy bỏ gắn nhãn cảnh báo lỗ và giữ nguyên dữ liệu gốc theo đúng yêu cầu: '{clause}'.")
                continue

            # --- 2.0.1 KHÔNG TÍNH BIÊN LÃI / BỎ CỘT BIÊN LỢI NHUẬN ---
            if any(k in cl_clean for k in ['khong tinh bien lai', 'khong tinh bien loi nhuan', 'bo bien lai', 'bo cot bien lai', 'bo bien loi nhuan', 'khong can bien lai', 'khong tinh lai', 'bo cot loi nhuan', 'khong can loi nhuan']):
                margin_cols = [c for c in cleaned_df.columns if any(m in _remove_accents_str(c) for m in ['bien loi nhuan', 'bien lai', 'margin', 'ty le lai'])]
                for mc in margin_cols:
                    cleaned_df = cleaned_df.drop(columns=[mc], errors='ignore')
                actions.append(f"Đã hủy bỏ tính toán và loại bỏ cột biên lợi nhuận theo đúng yêu cầu của bạn: '{clause}'.")
                continue

            # --- 2.1 GIỮ NGUYÊN TOÀN BỘ DỮ LIỆU ---
            if any(k in cl_clean for k in ['giu nguyen', 'khong thay doi', 'khong lam sach', 'de nguyen', 'giu tat ca', 'khong xoa gi', 'khong sua gi']):
                actions.append(f"Đã giữ nguyên toàn bộ dữ liệu gốc theo đúng yêu cầu: '{clause}'.")
                return cleaned_df, actions

            # --- 2.2 XÓA CỘT (DROP COLUMNS) ---
            drop_col_match = re.search(r'(?:xóa|bỏ|loại bỏ|không cần)\s+cột\s+[\x22\x27]?([^\x22\x27,;.\n]+?)[\x22\x27]?(?:\s|$|,|\.)', cl_lower)
            if drop_col_match:
                target_hint = drop_col_match.group(1).strip()
                matched_col = _resolve_target_col(target_hint, cleaned_df)
                if matched_col and matched_col in cleaned_df.columns:
                    cleaned_df = cleaned_df.drop(columns=[matched_col])
                    actions.append(f"Đã xóa cột '{matched_col}' theo yêu cầu.")
                    continue

            # --- 2.3 ĐỔI TÊN CỘT (RENAME COLUMNS) ---
            rename_match = re.search(r'(?:đổi tên cột|đổi cột|sửa tên cột|sửa cột)\s+[\x22\x27]?(.+?)(?:[\x22\x27]?\s+(?:thành|sang|bằng)\s+)[\x22\x27]?([^\x22\x27\n,;]+?)[\x22\x27]?(?:\s|$|,|\.)', clause, re.IGNORECASE)
            if rename_match:
                old_h = rename_match.group(1).strip()
                new_name = rename_match.group(2).strip()
                matched_old = _resolve_target_col(old_h, cleaned_df)
                if matched_old and matched_old in cleaned_df.columns:
                    cleaned_df = cleaned_df.rename(columns={matched_old: new_name})
                    actions.append(f"Đã đổi tên cột '{matched_old}' thành '{new_name}' theo yêu cầu.")
                    continue

            # --- 2.4 THAY THẾ GIÁ TRỊ CHUỖI (REPLACE VALUES) ---
            rep_match = re.search(r'(?:thay|đổi|chuyển|thay thế)\s+[\x22\x27]?([^\x22\x27]+?)[\x22\x27]?\s+(?:thành|bằng|sang)\s+[\x22\x27]?([^\x22\x27]+?)[\x22\x27]?(?:\s|$|,|\.)', clause, re.IGNORECASE)
            if rep_match:
                from_v = rep_match.group(1).strip()
                to_v = rep_match.group(2).strip()
                rep_count = 0
                for c in cleaned_df.columns:
                    if not pd.api.types.is_numeric_dtype(cleaned_df[c]):
                        mask = cleaned_df[c].astype(str).str.lower().str.contains(re.escape(from_v.lower()))
                        cnt = int(mask.sum())
                        if cnt > 0:
                            cleaned_df[c] = cleaned_df[c].astype(str).str.replace(from_v, to_v, case=False, regex=False)
                            rep_count += cnt
                if rep_count > 0:
                    actions.append(f"Đã thay thế '{from_v}' thành '{to_v}' ({rep_count} vị trí).")
                    continue

            # --- 2.5 CHUYỂN GIÁ TRỊ ÂM VỀ 0 HOẶC DƯƠNG ---
            if any(k in cl_clean for k in ['ve 0', 'thanh 0', 'sang 0', 'bang 0', 'gan 0']) and any(k in cl_clean for k in ['am', 'lo', 'thua lo']):
                num_cols = cleaned_df.select_dtypes(include=[np.number]).columns
                target_neg_cols = [c for c in num_cols if any(k in _remove_accents_str(c) for k in ['profit', 'loi nhuan', 'lai', 'rev', 'doanh thu'])]
                if not target_neg_cols and len(num_cols) > 0:
                    target_neg_cols = list(num_cols)
                total_converted = 0
                for c in target_neg_cols:
                    neg_mask = cleaned_df[c] < 0
                    cnt = int(neg_mask.sum())
                    if cnt > 0:
                        cleaned_df.loc[neg_mask, c] = 0
                        total_converted += cnt
                if total_converted > 0:
                    actions.append(f"Đã chuyển {total_converted} giá trị âm về 0 theo đúng yêu cầu: '{clause}'.")
                    continue

            # --- 2.6 XỬ LÝ Ô TRỐNG (DROP NA HOẶC FILLNA) ---
            if any(k in cl_clean for k in ['xoa o trong', 'xoa dong trong', 'bo o trong', 'drop na', 'dropna', 'khong lay o trong']):
                before = len(cleaned_df)
                cleaned_df = cleaned_df.dropna().reset_index(drop=True)
                diff = before - len(cleaned_df)
                actions.append(f"Đã xóa {diff} dòng chứa ô trống (NaN).")
                continue
            elif any(k in cl_clean for k in ['dien 0', 'thay 0', 'fillna 0', 'gan 0', 'dien so 0']):
                cleaned_df = cleaned_df.fillna(0)
                actions.append("Đã điền giá trị 0 vào các ô trống còn lại.")
                continue
            elif any(k in cl_clean for k in ['trung vi', 'median']):
                num_cols = cleaned_df.select_dtypes(include=[np.number]).columns
                for c in num_cols:
                    if cleaned_df[c].isna().sum() > 0:
                        cleaned_df[c] = cleaned_df[c].fillna(cleaned_df[c].median())
                actions.append("Đã điền giá trị trung vị vào các ô trống số đo định lượng.")
                continue
            elif any(k in cl_clean for k in ['trung binh', 'mean', 'average']):
                num_cols = cleaned_df.select_dtypes(include=[np.number]).columns
                for c in num_cols:
                    if cleaned_df[c].isna().sum() > 0:
                        cleaned_df[c] = cleaned_df[c].fillna(cleaned_df[c].mean())
                actions.append("Đã điền giá trị trung bình vào các ô trống số đo định lượng.")
                continue

            # --- 2.7 XÓA DÒNG TRÙNG LẶP ---
            if any(k in cl_clean for k in ['trung lap', 'trung', 'duplicate']) and any(k in cl_clean for k in ['xoa', 'bo', 'loai']):
                before = len(cleaned_df)
                cleaned_df = cleaned_df.drop_duplicates().reset_index(drop=True)
                diff = before - len(cleaned_df)
                actions.append(f"Đã loại bỏ {diff} dòng trùng lặp.")
                continue

            # --- 2.8 XÓA DÒNG DOANH THU ÂM HOẶC LỖ CHUNG ---
            if any(k in cl_clean for k in ['loi nhuan am', 'doanh thu am', 'am tien', 'ban lo', 'thua lo', 'dong lo', 'don lo']) and any(k in cl_clean for k in ['xoa', 'bo', 'loai', 'loc', 'khu', 'cat', 'bo lo']):
                num_cols = cleaned_df.select_dtypes(include=[np.number]).columns
                profit_cols = [c for c in num_cols if any(k in _remove_accents_str(c) for k in ['profit', 'loi nhuan', 'lai'])]
                rev_cols = [c for c in num_cols if any(k in _remove_accents_str(c) for k in ['rev', 'doanh thu', 'tien', 'sales'])]
                target_cols = profit_cols if profit_cols else rev_cols
                if not target_cols and len(num_cols) > 0:
                    target_cols = [num_cols[0]]
                for c in target_cols:
                    before = len(cleaned_df)
                    cleaned_df = cleaned_df[cleaned_df[c] >= 0].reset_index(drop=True)
                    diff = before - len(cleaned_df)
                    if diff > 0:
                        actions.append(f"Đã loại bỏ {diff} dòng kinh doanh lỗ (< 0) tại cột '{c}' theo yêu cầu.")
                continue

            # --- 2.9 LỌC DỮ LIỆU SỐ HỌC TOÀN DIỆN (> < >= <= ==) ---
            op = _detect_comparison_op(cl_clean)
            num_val = _parse_number_with_unit(cl_lower)
            if op and num_val is not None:
                is_delete_action = any(k in cl_clean for k in ['xoa', 'bo', 'loai', 'khu', 'cat', 'khong lay', 'tru'])
                # Tìm cột số mục tiêu
                num_cols = cleaned_df.select_dtypes(include=[np.number]).columns
                target_col = None
                
                # 1. Tìm cột khớp trực tiếp tên
                for c in num_cols:
                    c_cl = _remove_accents_str(c)
                    if c_cl in cl_clean and len(c_cl) >= 3:
                        target_col = c
                        break
                        
                # 2. Phân loại theo ngữ nghĩa đơn vị (Tiền tệ vs Số lượng)
                is_currency = any(u in cl_lower for u in ['triệu', 'tr', 'nghìn', 'k', 'tỷ', 'vnd', 'đ', 'dong', 'đồng']) or (num_val >= 1000 and '%' not in cl_lower)
                is_quantity = any(q in cl_clean for q in ['so luong', 'san pham', 'don vi', 'cai', 'chiec', 'kg', 'qty', 'units'])
                
                if not target_col:
                    if is_quantity:
                        qty_candidates = [c for c in num_cols if any(k in _remove_accents_str(c) for k in ['qty', 'so luong', 'quantity', 'units'])]
                        if qty_candidates:
                            target_col = qty_candidates[0]
                    elif is_currency:
                        rev_candidates = [c for c in num_cols if any(k in _remove_accents_str(c) for k in ['rev', 'doanh thu', 'sales', 'tien', 'amount'])]
                        if rev_candidates:
                            target_col = rev_candidates[0]
                            
                if not target_col:
                    target_col = _resolve_target_col(cl_clean, cleaned_df)
                    if target_col and not pd.api.types.is_numeric_dtype(cleaned_df[target_col]):
                        target_col = None
                        
                if not target_col and len(num_cols) > 0:
                    # Ưu tiên cột doanh thu nếu có đơn vị tiền tệ
                    rev_cols = [c for c in num_cols if any(k in _remove_accents_str(c) for k in ['rev', 'doanh thu', 'tien', 'sales', 'amount'])]
                    target_col = rev_cols[0] if (is_currency and rev_cols) else num_cols[0]

                if target_col and target_col in cleaned_df.columns:
                    before = len(cleaned_df)
                    # Tạo mask thỏa mãn điều kiện
                    if op == '>': cond = cleaned_df[target_col] > num_val
                    elif op == '>=': cond = cleaned_df[target_col] >= num_val
                    elif op == '<': cond = cleaned_df[target_col] < num_val
                    elif op == '<=': cond = cleaned_df[target_col] <= num_val
                    elif op == '==': cond = cleaned_df[target_col] == num_val
                    else: cond = pd.Series(True, index=cleaned_df.index)

                    if is_delete_action:
                        # Người dùng yêu cầu XÓA các dòng thỏa mãn điều kiện
                        cleaned_df = cleaned_df[~cond].reset_index(drop=True)
                        diff = before - len(cleaned_df)
                        actions.append(f"Đã loại bỏ {diff} dòng có {target_col} {op} {num_val:,.0f} theo yêu cầu (còn lại {len(cleaned_df)} dòng).")
                    else:
                        # Người dùng yêu cầu GIỮ LẠI các dòng thỏa mãn điều kiện
                        cleaned_df = cleaned_df[cond].reset_index(drop=True)
                        actions.append(f"Đã lọc giữ lại {len(cleaned_df)} dòng có {target_col} {op} {num_val:,.0f} theo yêu cầu.")
                    continue

            # --- 2.10 LỌC BỎ DÒNG THEO GIÁ TRỊ PHÂN LOẠI (CATEGORICAL EXCLUDE) ---
            is_exclude = any(k in cl_clean for k in ['bo', 'xoa', 'loai', 'khu', 'tru', 'khong lay']) and not any(k in cl_clean for k in ['cot', 'thanh', 'sang', 'bang', 'o trong', 'trung'])
            if is_exclude:
                stops_ex = r'\b(?:xoa|bo|loai bo|loai|khu|tru|loai tru|khong lay|kenh|chi nhanh|danh muc|nhom|san pham|cot|cac don|cac dong|dong|hang|don|tat ca)\b'
                extracted_kw = re.sub(r'\s+', ' ', re.sub(stops_ex, ' ', cl_clean)).strip()
                matched_ex = False
                for c in cleaned_df.columns:
                    if not pd.api.types.is_numeric_dtype(cleaned_df[c]) and not pd.api.types.is_datetime64_any_dtype(cleaned_df[c]):
                        unique_vals = [v for v in cleaned_df[c].dropna().unique() if len(str(v).strip()) > 1]
                        for v in unique_vals:
                            v_clean = _remove_accents_str(v)
                            # Khớp nếu giá trị nằm trong câu hoặc từ khóa tách được nằm trong giá trị
                            is_hit = False
                            if len(v_clean) >= 2 and (v_clean in cl_clean or cl_clean in v_clean):
                                is_hit = True
                            elif len(extracted_kw) >= 2 and (extracted_kw in v_clean or v_clean in extracted_kw):
                                is_hit = True

                            if is_hit:
                                before = len(cleaned_df)
                                cleaned_df = cleaned_df[~cleaned_df[c].astype(str).str.strip().str.lower().str.contains(re.escape(str(v).lower()))].reset_index(drop=True)
                                diff = before - len(cleaned_df)
                                if diff > 0:
                                    actions.append(f"Đã loại bỏ {diff} dòng có {c} = '{v}' theo đúng yêu cầu (còn lại {len(cleaned_df)} dòng).")
                                    matched_ex = True
                                    break
                        if matched_ex:
                            break
                if matched_ex:
                    continue

            # --- 2.11 CHỈ GIỮ LẠI THEO GIÁ TRỊ PHÂN LOẠI (CATEGORICAL INCLUDE) ---
            is_include = any(k in cl_clean for k in ['chi lay', 'chi giu', 'giu lai', 'loc', 'chi xem', 'chi chon', 'lay moi']) and not is_exclude
            if is_include:
                stops_inc = r'\b(?:chi lay|chi giu|giu lai|chi xem|chi chon|lay moi|loc|kenh|chi nhanh|danh muc|nhom|san pham|cot|cac don|cac dong|dong|hang|don|tat ca)\b'
                extracted_kw = re.sub(r'\s+', ' ', re.sub(stops_inc, ' ', cl_clean)).strip()
                matched_inc = False
                for c in cleaned_df.columns:
                    if not pd.api.types.is_numeric_dtype(cleaned_df[c]) and not pd.api.types.is_datetime64_any_dtype(cleaned_df[c]):
                        unique_vals = [v for v in cleaned_df[c].dropna().unique() if len(str(v).strip()) > 1]
                        for v in unique_vals:
                            v_clean = _remove_accents_str(v)
                            is_hit = False
                            if len(v_clean) >= 2 and (v_clean in cl_clean or cl_clean in v_clean):
                                is_hit = True
                            elif len(extracted_kw) >= 2 and (extracted_kw in v_clean or v_clean in extracted_kw):
                                is_hit = True

                            if is_hit:
                                before = len(cleaned_df)
                                cleaned_df = cleaned_df[cleaned_df[c].astype(str).str.strip().str.lower().str.contains(re.escape(str(v).lower()))].reset_index(drop=True)
                                diff = before - len(cleaned_df)
                                if len(cleaned_df) > 0:
                                    actions.append(f"Đã lọc giữ lại {len(cleaned_df)} dòng có {c} chứa '{v}' theo yêu cầu.")
                                    matched_inc = True
                                    break
                        if matched_inc:
                            break
                if matched_inc:
                    continue

            # --- 2.12 SẮP XẾP DỮ LIỆU (SORT) ---
            if any(k in cl_clean for k in ['sap xep', 'xep theo', 'sort']):
                asc = not any(k in cl_clean for k in ['giam dan', 'cao xuong thap', 'tu cao den thap', 'moi nhat', 'lon den nho'])
                target_col = _resolve_target_col(cl_clean, cleaned_df)
                if not target_col and len(cleaned_df.select_dtypes(include=[np.number]).columns) > 0:
                    target_col = cleaned_df.select_dtypes(include=[np.number]).columns[0]
                if target_col and target_col in cleaned_df.columns:
                    cleaned_df = cleaned_df.sort_values(by=target_col, ascending=asc).reset_index(drop=True)
                    order_label = "tăng dần" if asc else "giảm dần"
                    actions.append(f"Đã sắp xếp dữ liệu theo cột '{target_col}' ({order_label}).")
                    continue

            # --- 2.13 LẤY TOP / GIỚI HẠN SỐ DÒNG (HEAD / LIMIT) ---
            head_match = re.search(r'(?:lấy|top|giữ|limit)\s+(\d+)\s+(?:dòng|bản ghi|hàng|đơn)?', cl_lower)
            if head_match:
                n_rows = int(head_match.group(1))
                if 0 < n_rows < len(cleaned_df):
                    cleaned_df = cleaned_df.head(n_rows).reset_index(drop=True)
                    actions.append(f"Đã lấy {n_rows} dòng đầu tiên theo yêu cầu.")
                    continue

        if not actions:
            actions.append(f"Đã tiếp nhận và thực thi hoàn tất yêu cầu của bạn: '{raw_req}'.")
            
    return cleaned_df, actions

def clean_and_integrate_data(
    df: pd.DataFrame,
    handle_missing: str = "impute", # "impute", "drop", "keep"
    drop_duplicates: bool = True,
    standardize_columns: bool = True,
    parse_dates: bool = True,
    user_request: Optional[str] = None,
    api_key: Optional[str] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Thực hiện quy trình làm sạch & chuẩn hóa dữ liệu toàn diện theo đúng 5 nhóm trường hợp nghiệp vụ.
    """
    cleaned_df = df.copy()
    cleaning_log = []
    initial_rows = len(cleaned_df)
    
    # -----------------------------------------------------------------
    # BƯỚC 1: CHUẨN HÓA VĂN BẢN, TÊN CỘT & BẢNG MÃ TIẾNG VIỆT (NFC)
    # -----------------------------------------------------------------
    if standardize_columns:
        old_cols = list(cleaned_df.columns)
        new_cols = []
        for c in old_cols:
            clean_c = unicodedata.normalize('NFC', str(c).strip())
            clean_c = re.sub(r'\s+', '_', clean_c)
            clean_c = re.sub(r'[^\w_]', '', clean_c)
            new_cols.append(clean_c)
            
        # Đảm bảo tên cột không bị trùng lặp sau khi chuẩn hóa
        dedup_cols = []
        counts = {}
        for c in new_cols:
            if c in counts:
                counts[c] += 1
                dedup_cols.append(f"{c}_{counts[c]}")
            else:
                counts[c] = 0
                dedup_cols.append(c)
        cleaned_df.columns = dedup_cols
        if old_cols != dedup_cols:
            cleaning_log.append("Đã chuẩn hóa định dạng tên cột (chuẩn snake_case, bảng mã UTF-8 NFC, đảm bảo tên cột duy nhất).")

    # Chuẩn hóa giá trị chuỗi (cắt khoảng trắng, chuẩn hóa Unicode NFC, loại bỏ ký tự tiền tệ)
    string_cols = cleaned_df.select_dtypes(include=['object', 'string']).columns
    for col in string_cols:
        cleaned_df[col] = cleaned_df[col].apply(
            lambda x: unicodedata.normalize('NFC', str(x).strip()) if (pd.notna(x) and isinstance(x, str)) else x
        )
        # Ánh xạ viết tắt phổ biến để tránh phân mảnh
        def _standardize_category(val):
            if not isinstance(val, str):
                return val
            v_low = val.strip().lower()
            if v_low in ['tp hcm', 'tp. hcm', 'tp.hcm', 'hcm', 'ho chi minh', 'tp ho chi minh']:
                return 'TP. Hồ Chí Minh'
            if v_low in ['hn', 'ha noi', 'tp ha noi', 'tp. ha noi']:
                return 'Hà Nội'
            if v_low in ['web', 'website', 'online']:
                return 'Website'
            return val
        cleaned_df[col] = cleaned_df[col].apply(_standardize_category)

    # Chuyển đổi các chuỗi chứa tiền tệ/phần trăm về dạng số
    for col in cleaned_df.columns:
        if cleaned_df[col].dtype == 'object':
            sample = cleaned_df[col].dropna().astype(str).head(30)
            if len(sample) > 0 and sample.str.contains(r'[$₫%]|VNĐ|VND|\bUSD\b', regex=True).any():
                try:
                    cleaned_num = cleaned_df[col].astype(str).str.replace(r'[$₫%]|VNĐ|VND|\bUSD\b', '', regex=True)
                    cleaned_num = cleaned_num.str.replace(',', '').str.strip()
                    cleaned_df[col] = pd.to_numeric(cleaned_num, errors='coerce')
                    cleaning_log.append(f"Chuyển đổi cột '{col}' từ chuỗi tiền tệ/phần trăm sang số thực (numeric).")
                except Exception:
                    pass

    # -----------------------------------------------------------------
    # PHÂN TÍCH Ý ĐỊNH NGƯỜI DÙNG TỪ YÊU CẦU LÀM SẠCH (NẾU CÓ)
    # -----------------------------------------------------------------
    req_l = user_request.lower().strip() if user_request else ""
    user_wants_no_warning = any(k in req_l for k in [
        "không cần gắn nhãn", "không gắn nhãn", "bỏ gắn nhãn", "bỏ cảnh báo", "không cảnh báo", 
        "đừng gắn nhãn", "ko cần gắn nhãn", "ko gắn nhãn", "bỏ nhãn", "không dán nhãn", 
        "không cần cảnh báo", "bỏ cột cảnh báo", "bỏ cột trạng thái"
    ])
    user_wants_keep_raw = any(k in req_l for k in ["giữ nguyên", "không thay đổi", "không làm sạch", "để nguyên", "giữ tất cả", "không xóa gì", "không sửa gì"])
    user_wants_drop_na = any(k in req_l for k in ["ô trống", "dòng trống", "drop na", "dropna", "chứa ô trống", "có ô trống"]) and any(k in req_l for k in ["xóa", "bỏ", "loại"])
    user_wants_fill_zero = any(k in req_l for k in ["điền 0", "thay 0", "gán 0", "fillna 0", "thay bằng 0", "0 vào", "điền số 0"])
    user_wants_fill_median = any(k in req_l for k in ["trung vị", "median", "định lượng"])
    user_wants_fill_mode = any(k in req_l for k in ["giá trị phổ biến", "mode", "nhiều nhất", "phổ biến"])
    user_wants_ffill = any(k in req_l for k in ["liền trước", "forward fill", "ffill", "thời gian", "ngày trước"])
    user_wants_gen_id = any(k in req_l for k in ["mã định danh", "sinh mã", "tự sinh mã", "tạo mã"])
    user_wants_keep_dup = any(k in req_l for k in ["giữ nguyên dòng lặp", "giữ dòng lặp", "không xóa trùng", "giữ lại trùng", "không loại bỏ trùng"])
    user_wants_drop_dup = any(k in req_l for k in ["xóa dòng lặp", "xóa trùng", "bỏ trùng", "loại bỏ trùng", "xóa lặp", "bỏ lặp", "bản ghi trùng lặp", "xóa bản sao"])
    user_wants_drop_neg = any(k in req_l for k in ["lợi nhuận âm", "doanh thu âm", "âm tiền", "dòng âm", "bán lỗ", "thua lỗ", "lỗ", "< 0", "âm"]) and any(k in req_l for k in ["xóa", "bỏ", "loại", "loc", "lọc", "khử", "chỉ lấy lãi", "bỏ lỗ", "cắt"])
    user_wants_zero_neg = any(k in req_l for k in ["về 0", "thành 0", "sang 0", "bằng 0", "gán 0"]) and any(k in req_l for k in ["âm", "lỗ", "lợi nhuận âm", "doanh thu âm"])

    if user_wants_keep_raw:
        summary = {
            "initial_rows": initial_rows,
            "final_rows": initial_rows,
            "removed_rows": 0,
            "missing_before": int(df.isna().sum().sum()),
            "missing_after": int(df.isna().sum().sum()),
            "duplicates_removed": 0,
            "negative_profit_rows": 0,
            "total_loss_amount": 0.0,
            "profit_status_tagged": False,
            "actions": [f"Hệ thống đã giữ nguyên 100% dữ liệu gốc theo yêu cầu của bạn: '{user_request}'."],
            "user_request": user_request or ""
        }
        return df.copy(), summary

    # -----------------------------------------------------------------
    # BƯỚC 2: XỬ LÝ DỮ LIỆU TRÙNG LẶP (DUPLICATES)
    # -----------------------------------------------------------------
    initial_dup_count = int(cleaned_df.duplicated().sum())
    should_drop_dup = (drop_duplicates or user_wants_drop_dup) and not user_wants_keep_dup
    if should_drop_dup and initial_dup_count > 0:
        cleaned_df = cleaned_df.drop_duplicates().reset_index(drop=True)
        cleaning_log.append(f"Đã loại bỏ {initial_dup_count} bản ghi trùng lặp kỹ thuật hoàn toàn (100% các cột).")
    elif user_wants_keep_dup:
        cleaning_log.append("Giữ nguyên các dòng trùng lặp theo yêu cầu của bạn.")

    # -----------------------------------------------------------------
    # BƯỚC 3: CHUẨN HÓA THỜI GIAN & CHUỖI GIAO DỊCH
    # -----------------------------------------------------------------
    if parse_dates:
        for col in cleaned_df.columns:
            col_lower = str(col).lower()
            if any(k in col_lower for k in ['date', 'ngày', 'time', 'ngay', 'created_at', 'order_date']):
                try:
                    cleaned_df[col] = pd.to_datetime(cleaned_df[col], dayfirst=True, errors='coerce')
                    # Sắp xếp theo chuỗi thời gian để hỗ trợ điền liên tục và biểu đồ
                    if cleaned_df[col].notna().sum() > 0:
                        cleaned_df = cleaned_df.sort_values(by=col).reset_index(drop=True)
                    cleaning_log.append(f"Đã chuẩn hóa cột thời gian '{col}' về định dạng chuẩn ISO Datetime.")
                except Exception:
                    pass

    # -----------------------------------------------------------------
    # BƯỚC 4: XỬ LÝ DỮ LIỆU BỊ THIẾU (MISSING VALUES / NULL)
    # -----------------------------------------------------------------
    id_cols = [c for c in cleaned_df.columns if any(k in str(c).lower() for k in ['id', 'order', 'ma_don', 'madon', 'code'])]
    rev_cols = [c for c in cleaned_df.columns if any(k in str(c).lower() for k in ['rev', 'sales', 'doanh_thu', 'amount', 'tien'])]
    qty_cols = [c for c in cleaned_df.columns if any(k in str(c).lower() for k in ['qty', 'so_luong', 'quantity', 'units_sold'])]
    price_cols = [c for c in cleaned_df.columns if any(k in str(c).lower() for k in ['price', 'don_gia', 'gia'])]
    discount_cols = [c for c in cleaned_df.columns if any(k in str(c).lower() for k in ['discount', 'chiet_khau', 'giam_gia', 'fee', 'phu_phi'])]

    missing_before = int(cleaned_df.isna().sum().sum())

    if user_wants_drop_na:
        # Người dùng yêu cầu xóa dòng có ô trống
        rows_before = len(cleaned_df)
        cleaned_df = cleaned_df.dropna().reset_index(drop=True)
        diff = rows_before - len(cleaned_df)
        cleaning_log.append(f"Đã xóa {diff} dòng chứa ô trống (NaN) theo yêu cầu của bạn.")
    elif user_wants_fill_zero:
        # Người dùng yêu cầu điền 0 vào ô trống / chiết khấu
        if "chiết khấu" in req_l or "discount" in req_l:
            for col in discount_cols:
                if cleaned_df[col].isna().sum() > 0:
                    cnt = int(cleaned_df[col].isna().sum())
                    cleaned_df[col] = cleaned_df[col].fillna(0)
                    cleaning_log.append(f"Đã điền 0 vào {cnt} ô trống tại cột chiết khấu '{col}' theo yêu cầu.")
            # Các cột số còn lại điền median, chuỗi điền Chưa phân loại
            num_cols = cleaned_df.select_dtypes(include=[np.number]).columns
            for col in num_cols:
                if cleaned_df[col].isna().sum() > 0:
                    cleaned_df[col] = cleaned_df[col].fillna(cleaned_df[col].median())
            cleaned_df = cleaned_df.fillna("Chưa phân loại")
        else:
            # Điền 0 vào tất cả các ô số trống
            num_cols = cleaned_df.select_dtypes(include=[np.number]).columns
            for col in num_cols:
                if cleaned_df[col].isna().sum() > 0:
                    cleaned_df[col] = cleaned_df[col].fillna(0)
            cleaned_df = cleaned_df.fillna("Chưa phân loại")
            cleaning_log.append("Đã điền giá trị 0 vào các ô trống theo yêu cầu của bạn.")
    elif user_wants_fill_mode:
        # Người dùng yêu cầu điền giá trị phổ biến nhất (Mode) cho danh mục
        for col in cleaned_df.columns:
            if cleaned_df[col].isna().sum() > 0:
                m = cleaned_df[col].mode()
                mode_val = m.iloc[0] if len(m) > 0 else (0 if pd.api.types.is_numeric_dtype(cleaned_df[col]) else "Chưa phân loại")
                cleaned_df[col] = cleaned_df[col].fillna(mode_val)
        cleaning_log.append("Đã điền giá trị xuất hiện nhiều nhất (Mode) vào các ô trống danh mục theo yêu cầu của bạn.")
    elif user_wants_fill_median:
        # Người dùng yêu cầu điền trung vị (Median) cho số đo định lượng
        num_cols = cleaned_df.select_dtypes(include=[np.number]).columns
        for col in num_cols:
            if cleaned_df[col].isna().sum() > 0:
                med_val = cleaned_df[col].median()
                cleaned_df[col] = cleaned_df[col].fillna(med_val)
                cleaning_log.append(f"Đã điền giá trị trung vị ({med_val:,.1f}) cho ô trống tại cột số '{col}'.")
    elif user_wants_ffill:
        # Người dùng yêu cầu điền mốc thời gian liền trước (Forward Fill)
        for col in cleaned_df.columns:
            if any(k in str(col).lower() for k in ['date', 'time', 'ngay', 'thang', 'nam', 'ky']):
                if cleaned_df[col].isna().sum() > 0:
                    cleaned_df[col] = cleaned_df[col].ffill().bfill()
                    cleaning_log.append(f"Đã điền mốc thời gian liền trước (Forward Fill) cho cột '{col}'.")
    elif user_wants_gen_id:
        # Người dùng yêu cầu tự sinh mã định danh liên tục
        for col in id_cols:
            if cleaned_df[col].isna().sum() > 0:
                for idx in cleaned_df[cleaned_df[col].isna()].index:
                    cleaned_df.at[idx, col] = f"ID_{idx+1:04d}"
                cleaning_log.append(f"Đã tự sinh mã định danh liên tục cho cột '{col}'.")
    else:
        # Quy trình làm sạch chuẩn mặc định (sinh mã tạm, điền suy diễn, điền median/mode)
        # 4.1 Cột khóa chính & mã định danh (ID)
        if id_cols and rev_cols:
            main_id = id_cols[0]
            main_rev = rev_cols[0]
            missing_id_mask = cleaned_df[main_id].isna() & cleaned_df[main_rev].notna() & (cleaned_df[main_rev] > 0)
            missing_id_count = int(missing_id_mask.sum())
            if missing_id_count > 0:
                for idx in cleaned_df[missing_id_mask].index:
                    cleaned_df.at[idx, main_id] = f"TMP_ORD_{idx+1:04d}"
                cleaning_log.append(f"Tự động sinh {missing_id_count} mã định danh tạm thời (TMP_ORD_xxx) để bảo toàn doanh thu.")

        # 4.2 Cột chiết khấu và chi phí phụ: Mặc định điền 0
        for col in discount_cols:
            if cleaned_df[col].isna().sum() > 0:
                cleaned_df[col] = cleaned_df[col].fillna(0)
                cleaning_log.append(f"Mặc định điền giá trị 0 cho ô trống tại cột chiết khấu/phụ phí '{col}'.")

        # 4.3 Suy diễn chéo toán học giữa Doanh thu, Đơn giá và Số lượng
        if rev_cols and qty_cols and price_cols:
            r_c, q_c, p_c = rev_cols[0], qty_cols[0], price_cols[0]
            fill_rev_mask = cleaned_df[r_c].isna() & cleaned_df[q_c].notna() & cleaned_df[p_c].notna()
            if fill_rev_mask.sum() > 0:
                cleaned_df.loc[fill_rev_mask, r_c] = cleaned_df.loc[fill_rev_mask, q_c] * cleaned_df.loc[fill_rev_mask, p_c]
                cleaning_log.append(f"Suy diễn toán học chéo: Tính Doanh thu = Đơn giá x Số lượng cho {fill_rev_mask.sum()} dòng.")
            fill_qty_mask = cleaned_df[q_c].isna() & cleaned_df[r_c].notna() & cleaned_df[p_c].notna() & (cleaned_df[p_c] > 0)
            if fill_qty_mask.sum() > 0:
                cleaned_df.loc[fill_qty_mask, q_c] = (cleaned_df.loc[fill_qty_mask, r_c] / cleaned_df.loc[fill_qty_mask, p_c]).round().clip(lower=1)
                cleaning_log.append(f"Suy diễn toán học chéo: Tính Số lượng = Doanh thu / Đơn giá cho {fill_qty_mask.sum()} dòng.")

        # 4.4 Xử lý các ô trống còn lại
        if missing_before > 0:
            if handle_missing == "drop":
                rows_before_drop = len(cleaned_df)
                cleaned_df = cleaned_df.dropna().reset_index(drop=True)
                dropped_rows = rows_before_drop - len(cleaned_df)
                cleaning_log.append(f"Đã loại bỏ {dropped_rows} dòng chứa dữ liệu trống (NaN).")
            elif handle_missing == "impute":
                category_cols = [c for c in cleaned_df.columns if any(k in str(c).lower() for k in ['category', 'nhom', 'danh_muc', 'segment', 'branch'])]
                group_col = category_cols[0] if category_cols else None

                for col in cleaned_df.columns:
                    if cleaned_df[col].isna().sum() > 0:
                        cnt = int(cleaned_df[col].isna().sum())
                        pct = (cnt / len(cleaned_df)) * 100

                        if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                            if group_col and cleaned_df[group_col].nunique() > 1:
                                try:
                                    group_median = cleaned_df.groupby(group_col)[col].transform('median')
                                    cleaned_df[col] = cleaned_df[col].fillna(group_median)
                                except Exception:
                                    pass
                            median_val = cleaned_df[col].median()
                            if pd.notna(median_val):
                                cleaned_df[col] = cleaned_df[col].fillna(median_val)
                                cleaning_log.append(f"Điền Trung vị ({round(median_val, 2)}) cho cột số '{col}'.")
                        elif pd.api.types.is_datetime64_any_dtype(cleaned_df[col]):
                            cleaned_df[col] = cleaned_df[col].ffill().bfill()
                            cleaning_log.append(f"Điền nối tiếp theo chuỗi thời gian cho cột '{col}'.")
                        else:
                            if pct < 15.0:
                                mode_val = cleaned_df[col].mode().iloc[0] if len(cleaned_df[col].mode()) > 0 else "Chưa phân loại"
                                cleaned_df[col] = cleaned_df[col].fillna(mode_val)
                                cleaning_log.append(f"Điền giá trị phổ biến (Mode: '{mode_val}') cho cột phân loại '{col}'.")
                            else:
                                cleaned_df[col] = cleaned_df[col].fillna("Chưa phân loại")
                                cleaning_log.append(f"Gán nhãn 'Chưa phân loại' cho cột '{col}' do tỷ lệ khuyết cao ({round(pct, 1)}% >= 15%).")

    # -----------------------------------------------------------------
    # BƯỚC 5: XỬ LÝ SAI LỆCH LOGIC, DẤU ÂM & ĐỘT BIẾN TOÁN HỌC
    # -----------------------------------------------------------------
    # 5.1 Xử lý dấu âm
    profit_cols = [c for c in cleaned_df.columns if pd.api.types.is_numeric_dtype(cleaned_df[c]) and any(k in normalize_col_name(c) for k in ['profit', 'loi_nhuan', 'lai_gop', 'lai'])]
    rev_profit_cols = [c for c in cleaned_df.columns if pd.api.types.is_numeric_dtype(cleaned_df[c]) and any(k in normalize_col_name(c) for k in ['rev', 'sales', 'doanh_thu', 'tien', 'profit', 'loi_nhuan', 'lai'])]
    if not rev_profit_cols and len(cleaned_df.select_dtypes(include=[np.number]).columns) > 0:
        rev_profit_cols = [cleaned_df.select_dtypes(include=[np.number]).columns[0]]

    neg_profit_total_cnt = 0
    total_loss_amount = 0.0
    has_neg_profit = False

    if user_wants_drop_neg:
        # Người dùng yêu cầu xóa dòng có giá trị âm / bán lỗ
        target_drop_cols = profit_cols if profit_cols else rev_profit_cols
        for c in target_drop_cols:
            before = len(cleaned_df)
            cleaned_df = cleaned_df[cleaned_df[c] >= 0].reset_index(drop=True)
            diff = before - len(cleaned_df)
            if diff > 0:
                cleaning_log.append(f"Đã loại bỏ {diff} dòng kinh doanh lỗ / âm tiền (< 0) tại cột '{c}' theo yêu cầu của bạn.")
    elif user_wants_zero_neg:
        # Người dùng yêu cầu chuyển giá trị âm về 0
        target_zero_cols = profit_cols if profit_cols else rev_profit_cols
        for c in target_zero_cols:
            neg_mask = cleaned_df[c] < 0
            cnt = int(neg_mask.sum())
            if cnt > 0:
                cleaned_df.loc[neg_mask, c] = 0
                cleaning_log.append(f"Đã chuyển {cnt} giá trị âm về 0 tại cột '{c}' theo đúng yêu cầu của bạn.")
    elif user_wants_no_warning:
        # Người dùng yêu cầu không gắn nhãn cảnh báo: Giữ nguyên dữ liệu số, không tạo cột cảnh báo
        cleaning_log.append(f"Đã hủy bỏ gắn nhãn cảnh báo lỗ theo đúng yêu cầu của bạn: '{user_request}'.")
    else:
        # Xử lý dấu âm theo trạng thái giao dịch chuẩn
        status_cols = [c for c in cleaned_df.columns if any(k in str(c).lower() for k in ['status', 'trang_thai', 'return', 'hoan_tra'])]
        has_status = len(status_cols) > 0
        status_col = status_cols[0] if has_status else None

        for col in rev_cols:
            if col in cleaned_df.columns and pd.api.types.is_numeric_dtype(cleaned_df[col]):
                neg_mask = cleaned_df[col] < 0
                if neg_mask.sum() > 0:
                    if has_status:
                        completed_mask = neg_mask & cleaned_df[status_col].astype(str).str.lower().str.contains('hoàn thành|completed|thành công|success', regex=True)
                        if completed_mask.sum() > 0:
                            cleaned_df.loc[completed_mask, col] = cleaned_df.loc[completed_mask, col].abs()
                            cleaning_log.append(f"Đã sửa dấu âm sang dương cho {completed_mask.sum()} đơn hợp lệ do lỗi gõ dấu tại '{col}'.")
                    else:
                        cleaned_df[col] = cleaned_df[col].abs()
                        cleaning_log.append(f"Đã chuẩn hóa trị tuyệt đối cho các giá trị âm tại '{col}'.")

        # Xử lý Lợi nhuận âm: Tự động phân loại, gắn nhãn kiểm toán và làm giàu dữ liệu để người dùng thấy rõ sự khác biệt
        for p_col in profit_cols:
            neg_p_mask = cleaned_df[p_col] < 0
            cnt = int(neg_p_mask.sum())
            if cnt > 0:
                has_neg_profit = True
                neg_profit_total_cnt += cnt
                loss_val = abs(float(cleaned_df.loc[neg_p_mask, p_col].sum()))
                total_loss_amount += loss_val
                
                # Bổ sung cột phân loại trạng thái lợi nhuận nếu chưa có
                if 'Trạng_thái_lợi_nhuận' not in cleaned_df.columns:
                    cleaned_df['Trạng_thái_lợi_nhuận'] = np.where(cleaned_df[p_col] < 0, 'Lợi nhuận âm', 'Có lãi')
                
                # KIỂM TRA: Nếu tệp ĐÃ CÓ cột biên lợi nhuận rồi thì TUYỆT ĐỐI KHÔNG sinh thêm cột mới!
                existing_margin_cols = [c for c in cleaned_df.columns if _is_margin_col(c)]
                if not existing_margin_cols:
                    if rev_cols and rev_cols[0] in cleaned_df.columns and pd.api.types.is_numeric_dtype(cleaned_df[rev_cols[0]]):
                        r_col = rev_cols[0]
                        cleaned_df['Biên_lợi_nhuận_%'] = np.where(
                            cleaned_df[r_col] > 0,
                            (cleaned_df[p_col] / cleaned_df[r_col] * 100).round(1),
                            0.0
                        )
                        cleaning_log.append(f"Phát hiện {cnt} dòng kinh doanh lỗ tại cột '{p_col}' (Tổng lỗ: {loss_val:,.0f} ₫). Hệ thống ghi nhận trạng thái 'Lợi nhuận âm' (số liệu hợp lệ theo công thức) và bổ sung cột 'Biên_lợi_nhuận_%' để khoanh vùng và tối ưu.")
                    else:
                        cleaning_log.append(f"Phát hiện {cnt} dòng kinh doanh lỗ tại cột '{p_col}' (Tổng lỗ: {loss_val:,.0f} ₫). Hệ thống ghi nhận trạng thái 'Lợi nhuận âm' (số liệu hợp lệ theo công thức).")
                else:
                    cleaning_log.append(f"Phát hiện {cnt} dòng kinh doanh lỗ tại cột '{p_col}' (Tổng lỗ: {loss_val:,.0f} ₫). Đã gắn nhãn kiểm toán và sử dụng cột biên lợi nhuận sẵn có '{existing_margin_cols[0]}'.")

        # KHỬ TRÙNG LẶP: Nếu xuất hiện nhiều hơn 1 cột biên lợi nhuận trong bảng, giữ lại cột có dữ liệu thực tế và xóa cột thừa
        margin_cols = [c for c in cleaned_df.columns if _is_margin_col(c)]
        if len(margin_cols) > 1:
            best_mc = None
            max_valid = -1
            for mc in margin_cols:
                s_vals = cleaned_df[mc].astype(str).str.replace('%', '').str.strip()
                valid_cnt = (pd.to_numeric(s_vals, errors='coerce').fillna(0) != 0).sum()
                if valid_cnt > max_valid:
                    max_valid = valid_cnt
                    best_mc = mc
            if best_mc is None:
                best_mc = margin_cols[0]
            for mc in margin_cols:
                if mc != best_mc:
                    cleaned_df = cleaned_df.drop(columns=[mc], errors='ignore')

    # 5.2 Xử lý Số lượng = 0 nhưng Doanh thu > 0
    if rev_cols and qty_cols and price_cols:
        r_c, q_c, p_c = rev_cols[0], qty_cols[0], price_cols[0]
        if r_c in cleaned_df.columns and q_c in cleaned_df.columns and p_c in cleaned_df.columns:
            zero_qty_mask = (cleaned_df[q_c] == 0) & (cleaned_df[r_c] > 0) & (cleaned_df[p_c] > 0)
            if zero_qty_mask.sum() > 0:
                cleaned_df.loc[zero_qty_mask, q_c] = (cleaned_df.loc[zero_qty_mask, r_c] / cleaned_df.loc[zero_qty_mask, p_c]).round().clip(lower=1)
                cleaning_log.append(f"Đã khắc phục lỗi số lượng = 0 bằng cách tính ngược từ doanh thu cho {zero_qty_mask.sum()} dòng.")

    # -----------------------------------------------------------------
    # BƯỚC 6: ÁP DỤNG YÊU CẦU CHỈNH SỬA TÙY BIẾN TỪ NGƯỜI DÙNG
    # -----------------------------------------------------------------
    if user_request and user_request.strip():
        cleaned_df, custom_actions = apply_user_cleaning_request(cleaned_df, user_request.strip(), api_key)
        cleaning_log.extend(custom_actions)

    missing_after = int(cleaned_df.isna().sum().sum())
    
    summary = {
        "initial_rows": initial_rows,
        "final_rows": len(cleaned_df),
        "removed_rows": initial_rows - len(cleaned_df),
        "missing_before": missing_before,
        "missing_after": missing_after,
        "duplicates_removed": initial_dup_count,
        "negative_profit_rows": neg_profit_total_cnt,
        "total_loss_amount": total_loss_amount,
        "profit_status_tagged": has_neg_profit,
        "actions": cleaning_log,
        "user_request": user_request or ""
    }
    
    return cleaned_df, summary
