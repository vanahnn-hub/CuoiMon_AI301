import pandas as pd
import numpy as np
import unicodedata
import re
import os
from typing import Dict, Any, Tuple, Optional, List

def detect_actual_dataset_issues(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Quét dữ liệu và CHỈ trả về danh sách các lỗi THỰC TẾ mà bộ dữ liệu đang gặp phải,
    kèm theo đúng một hướng giải quyết nghiệp vụ tương ứng cho từng lỗi.
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

    # 1. Kiểm tra thiếu ID nhưng có doanh thu
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
                    "title": f'Thiếu mã định danh tại cột "{main_id}"',
                    "badge": f"{missing_id_with_rev} dòng thiếu ID",
                    "severity": "medium",
                    "desc": f'Phát hiện {missing_id_with_rev} dòng phát sinh giao dịch doanh thu nhưng bị bỏ trống mã định danh đơn.',
                    "solution": "Tự động sinh mã định danh tạm thời (TMP_ORD_xxxx) để giữ nguyên số lượng đơn và tổng doanh thu, không tùy tiện xóa bỏ dòng."
                })

    # 2. Kiểm tra ô trống (Missing values) tại từng cột
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
                "title": f'Dữ liệu khuyết thiếu tại cột Chiết khấu "{c}"',
                "badge": f"{cnt} ô trống ({pct}%)",
                "severity": "low",
                "desc": f'Cột chiết khấu / phụ phí "{c}" có {cnt} ô bị bỏ trống ({pct}%).',
                "solution": f'Mặc định điền giá trị 0 cho các ô trống này để phản ánh đúng thực tế giao dịch không phát sinh chiết khấu / phụ phí.'
            })
        elif any(k in c_low for k in ['date', 'time', 'ngay']):
            issues.append({
                "id": f"missing_{c}",
                "category": "missing",
                "icon": "fa-solid fa-calendar-xmark",
                "title": f'Khuyết thiếu mốc thời gian tại cột "{c}"',
                "badge": f"{cnt} ô trống ({pct}%)",
                "severity": "medium",
                "desc": f'Cột thời gian "{c}" có {cnt} ô bị thiếu ({pct}%) làm gián đoạn chuỗi giao dịch.',
                "solution": "Điền nối tiếp theo trình tự thời gian (Forward/Backward Fill) của các bản ghi liền kề để duy trì biểu đồ xu hướng liên tục."
            })
        elif pd.api.types.is_numeric_dtype(df[c]):
            issues.append({
                "id": f"missing_{c}",
                "category": "missing",
                "icon": "fa-solid fa-coins",
                "title": f'Khuyết thiếu chỉ số số liệu tại cột "{c}"',
                "badge": f"{cnt} ô trống ({pct}%)",
                "severity": "medium",
                "desc": f'Cột số liệu "{c}" có {cnt} ô bị khuyết thiếu ({pct}%).',
                "solution": f'Ưu tiên tính toán suy diễn chéo từ các cột liên quan sẵn có; nếu không đủ cơ sở thì tự động điền bằng Trung vị (Median) theo nhóm ngành tương ứng.'
            })
        else:
            # Cột phân loại / chuỗi
            mode_series = df[c].dropna().mode()
            mode_val = mode_series.iloc[0] if len(mode_series) > 0 else "Chưa phân loại"
            if pct < 15.0:
                sol = f'Tự động điền giá trị xuất hiện phổ biến nhất (Mode: "{mode_val}") do tỷ lệ khuyết thấp ({pct}% < 15%).'
                sev = "low"
            else:
                sol = f'Tự động gán nhãn phân loại riêng "Chưa phân loại" cho {cnt} ô này để không làm phóng đại giả tạo nhóm phổ biến.'
                sev = "medium"
            issues.append({
                "id": f"missing_{c}",
                "category": "missing",
                "icon": "fa-solid fa-layer-group",
                "title": f'Khuyết thiếu dữ liệu phân loại tại cột "{c}"',
                "badge": f"{cnt} ô trống ({pct}%)",
                "severity": sev,
                "desc": f'Cột thông tin phân loại "{c}" có {cnt} ô chưa được phân loại ({pct}%).',
                "solution": sol
            })

    # 3. Kiểm tra Dòng trùng lặp (Duplicates)
    dup_cnt = int(df.duplicated().sum())
    if dup_cnt > 0:
        pct = round(dup_cnt / total_rows * 100, 2)
        issues.append({
            "id": "duplicates",
            "category": "duplicate",
            "icon": "fa-solid fa-clone",
            "title": "Dữ liệu bị trùng lặp bản sao (Duplicates)",
            "badge": f"{dup_cnt} dòng trùng ({pct}%)",
            "severity": "high",
            "desc": f'Phát hiện {dup_cnt} bản ghi giống hệt nhau 100% trên tất cả các cột thông tin do lỗi sao chép hoặc trích xuất dữ liệu.',
            "solution": f'Loại bỏ {dup_cnt} bản sao kỹ thuật này, giữ lại duy nhất 1 bản ghi gốc đầu tiên để tránh tính đúp doanh thu.'
        })

    # 4. Kiểm tra Sai lệch logic & dấu âm
    for c in rev_cols:
        if pd.api.types.is_numeric_dtype(df[c]):
            # Kiểm tra trạng thái nếu có
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
                        "title": f'Dấu âm sai lệch tại cột Doanh thu "{c}"',
                        "badge": f"{completed_neg_cnt} đơn âm",
                        "severity": "medium",
                        "desc": f'Có {completed_neg_cnt} đơn hàng trạng thái hoàn thành nhưng lại ghi nhận doanh thu âm do lỗi gõ nhầm dấu khi nhập liệu.',
                        "solution": f'Tự động chuyển {completed_neg_cnt} giá trị này về số dương tuyệt đối để phản ánh đúng thực tế đơn thành công.'
                    })
            else:
                neg_cnt = int((df[c] < 0).sum())
                if neg_cnt > 0:
                    issues.append({
                        "id": f"negative_{c}",
                        "category": "logic",
                        "icon": "fa-solid fa-arrow-trend-down",
                        "title": f'Giá trị âm tại cột Doanh thu "{c}"',
                        "badge": f"{neg_cnt} giá trị âm",
                        "severity": "medium",
                        "desc": f'Cột doanh thu "{c}" có {neg_cnt} đơn mang giá trị âm (< 0).',
                        "solution": f'Chuyển {neg_cnt} giá trị âm về số dương tuyệt đối để tránh làm lệch tổng doanh thu của kỳ báo cáo.'
                    })

    # Kiểm tra Số lượng = 0 nhưng Doanh thu > 0
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
                    "title": "Mâu thuẫn logic: Số lượng bằng 0 nhưng có doanh thu",
                    "badge": f"{zero_qty_cnt} dòng lỗi",
                    "severity": "medium",
                    "desc": f'Ghi nhận {zero_qty_cnt} đơn hàng ghi số lượng = 0 nhưng vẫn phát sinh số tiền bán hàng.',
                    "solution": "Tự động tính ngược số lượng dựa trên đơn giá chuẩn (Số lượng = Doanh thu / Đơn giá) và làm tròn về số nguyên dương tối thiểu (>= 1)."
                })

    # 5. Kiểm tra khoảng trắng thừa tại các cột văn bản
    str_cols = df.select_dtypes(include=['object', 'string']).columns
    space_cols = []
    for c in str_cols:
        s_series = df[c].dropna().astype(str)
        if (s_series.str.startswith(' ') | s_series.str.endswith(' ')).any():
            space_cols.append(c)
    if space_cols:
        sample_str = ", ".join(space_cols[:3])
        issues.append({
            "id": "trailing_spaces",
            "category": "text",
            "icon": "fa-solid fa-spell-check",
            "title": "Khoảng trắng thừa & sai định dạng chuỗi văn bản",
            "badge": f"{len(space_cols)} cột cần chuẩn hóa",
            "severity": "low",
            "desc": f'Phát hiện khoảng trắng thừa ở đầu hoặc cuối chuỗi tại các cột: {sample_str}.',
            "solution": "Tự động cắt bỏ khoảng trắng thừa (Strip), đưa về chuẩn bảng mã tiếng Việt Unicode dựng sẵn (NFC)."
        })

    return issues


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

    # Phát hiện các lỗi THỰC TẾ
    actual_issues = detect_actual_dataset_issues(df)

    return {
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
def apply_user_cleaning_request(df: pd.DataFrame, user_request: str, api_key: Optional[str] = None) -> Tuple[pd.DataFrame, List[str]]:
    """
    Áp dụng các yêu cầu làm sạch tùy chỉnh từ người dùng bằng Agent logic (kết hợp NLP & LLM).
    """
    if not user_request or not user_request.strip():
        return df, []
        
    cleaned_df = df.copy()
    actions = []
    req_lower = user_request.lower()
    
    # 1. Thử dùng Gemini LLM nếu có API key hoặc cấu hình sẵn
    llm_applied = False
    effective_key = api_key or os.environ.get("GEMINI_API_KEY")
    if effective_key:
        try:
            from google import genai
            client = genai.Client(api_key=effective_key)
            prompt = f"""
Bạn là chuyên gia kỹ thuật dữ liệu (Data Engineer Agent).
Người dùng có DataFrame pandas tên `cleaned_df` với các cột: {list(cleaned_df.columns)}.
Dữ liệu mẫu 2 dòng đầu:
{cleaned_df.head(2).to_dict(orient='records')}

Yêu cầu làm sạch từ người dùng: "{user_request}"

Hãy viết đoạn mã Python an toàn sử dụng pandas để biến đổi hoặc lọc `cleaned_df` theo đúng yêu cầu trên.
Chỉ trả về khối mã python, không giải thích:
```python
# code ở đây
```
"""
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if resp and resp.text:
                code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', resp.text, re.DOTALL)
                code_to_exec = code_match.group(1) if code_match else resp.text.strip()
                if not any(bad in code_to_exec for bad in ['import os', 'import sys', 'subprocess', 'eval', 'exec', '__']):
                    local_scope = {'pd': pd, 'np': np, 'cleaned_df': cleaned_df.copy(), 're': re}
                    exec(code_to_exec, {}, local_scope)
                    if isinstance(local_scope.get('cleaned_df'), pd.DataFrame) and len(local_scope['cleaned_df']) > 0:
                        rows_diff = len(cleaned_df) - len(local_scope['cleaned_df'])
                        cleaned_df = local_scope['cleaned_df']
                        actions.append(f"AI Agent đã thực hiện theo yêu cầu: '{user_request}' (Thay đổi: {rows_diff} dòng).")
                        llm_applied = True
        except Exception:
            pass
            
    # 2. Rule-based NLP Agent Engine
    if not llm_applied:
        # Xóa dòng doanh thu âm hoặc lợi nhuận âm
        if any(k in req_lower for k in ['doanh thu âm', 'lợi nhuận âm', 'âm tiền', 'âm', '< 0', 'bán lỗ', 'âm lãi']):
            num_cols = cleaned_df.select_dtypes(include=[np.number]).columns
            rev_cols = [c for c in num_cols if any(k in c.lower() for k in ['rev', 'doanh_thu', 'tien', 'sales', 'profit', 'loi_nhuan', 'lai'])]
            if not rev_cols and len(num_cols) > 0:
                rev_cols = [num_cols[0]]
            for c in rev_cols:
                before = len(cleaned_df)
                cleaned_df = cleaned_df[cleaned_df[c] >= 0].reset_index(drop=True)
                diff = before - len(cleaned_df)
                if diff > 0:
                    actions.append(f"Đã loại bỏ {diff} dòng có giá trị âm tại cột '{c}'.")
                    
        # Xóa số lượng <= 0
        if any(k in req_lower for k in ['số lượng <= 0', 'số lượng bằng 0', 'số lượng âm', 'số lượng = 0', 'qty <= 0']):
            qty_cols = [c for c in cleaned_df.columns if any(k in c.lower() for k in ['qty', 'so_luong', 'quantity', 'unit'])]
            for c in qty_cols:
                if pd.api.types.is_numeric_dtype(cleaned_df[c]):
                    before = len(cleaned_df)
                    cleaned_df = cleaned_df[cleaned_df[c] > 0].reset_index(drop=True)
                    diff = before - len(cleaned_df)
                    if diff > 0:
                        actions.append(f"Đã loại bỏ {diff} dòng có số lượng <= 0 tại cột '{c}'.")
                        
        # Xóa dòng có ô trống / drop na
        if any(k in req_lower for k in ['xóa ô trống', 'xóa dòng trống', 'bỏ ô trống', 'drop na', 'dropna', 'xóa nan']):
            before = len(cleaned_df)
            cleaned_df = cleaned_df.dropna().reset_index(drop=True)
            diff = before - len(cleaned_df)
            actions.append(f"Đã xóa {diff} dòng chứa ô trống (NaN).")
            
        # Điền 0 vào ô trống
        if any(k in req_lower for k in ['điền 0', 'thay 0', 'fillna 0', 'gán 0', 'thay bằng 0']):
            cleaned_df = cleaned_df.fillna(0)
            actions.append("Đã điền giá trị 0 vào tất cả các ô trống còn lại.")
            
        # Xóa dòng trùng lặp
        if any(k in req_lower for k in ['trùng lặp', 'trùng', 'duplicate']):
            before = len(cleaned_df)
            cleaned_df = cleaned_df.drop_duplicates().reset_index(drop=True)
            diff = before - len(cleaned_df)
            actions.append(f"Đã loại bỏ {diff} dòng trùng lặp.")
            
        # Sinh mã tạm cho đơn thiếu ID
        if any(k in req_lower for k in ['sinh mã tạm', 'tạo mã tạm', 'mã định danh tạm', 'tmp_ord']):
            id_cols = [c for c in cleaned_df.columns if any(k in c.lower() for k in ['id', 'order', 'ma_don'])]
            if id_cols:
                c_id = id_cols[0]
                missing_mask = cleaned_df[c_id].isna()
                for idx in cleaned_df[missing_mask].index:
                    cleaned_df.at[idx, c_id] = f"TMP_ORD_{idx+1:04d}"
                actions.append(f"Đã tự động tạo mã định danh tạm thời cho {missing_mask.sum()} đơn thiếu ID.")

        # Lọc theo kênh hoặc danh mục nếu người dùng yêu cầu
        match_channel = re.search(r'(?:chỉ giữ|lọc|chỉ lấy)\s+(?:kênh|danh mục|nhóm)?\s*["\x27]?([a-zA-Z0-9_\s\u00C0-\u024F\u1EA0-\u1EF9-]+)["\x27]?', req_lower)
        if match_channel:
            target_val = match_channel.group(1).strip()
            text_cols = cleaned_df.select_dtypes(include=['object', 'string']).columns
            for c in text_cols:
                matched = cleaned_df[cleaned_df[c].astype(str).str.lower().str.contains(target_val, na=False)]
                if len(matched) > 0 and len(matched) < len(cleaned_df):
                    cleaned_df = matched.reset_index(drop=True)
                    actions.append(f"Đã lọc dữ liệu theo '{target_val}' tại cột '{c}' (giữ lại {len(cleaned_df)} dòng).")
                    break
                    
        if not actions:
            actions.append(f"Agent đã làm sạch và tối ưu dữ liệu theo yêu cầu: '{user_request}'.")
            
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
        cleaned_df.columns = new_cols
        if old_cols != new_cols:
            cleaning_log.append("Đã chuẩn hóa định dạng tên cột (chuẩn snake_case, bảng mã UTF-8 NFC).")

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
    # BƯỚC 2: XỬ LÝ DỮ LIỆU TRÙNG LẶP (DUPLICATES)
    # -----------------------------------------------------------------
    initial_dup_count = int(cleaned_df.duplicated().sum())
    if drop_duplicates and initial_dup_count > 0:
        cleaned_df = cleaned_df.drop_duplicates().reset_index(drop=True)
        cleaning_log.append(f"Đã loại bỏ {initial_dup_count} bản ghi trùng lặp kỹ thuật hoàn toàn (100% các cột).")

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
    # 4.1 Cột khóa chính & mã định danh (ID)
    id_cols = [c for c in cleaned_df.columns if any(k in str(c).lower() for k in ['id', 'order', 'ma_don', 'madon', 'code'])]
    rev_cols = [c for c in cleaned_df.columns if any(k in str(c).lower() for k in ['rev', 'sales', 'doanh_thu', 'amount', 'tien'])]
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
    discount_cols = [c for c in cleaned_df.columns if any(k in str(c).lower() for k in ['discount', 'chiet_khau', 'giam_gia', 'fee', 'phu_phi'])]
    for col in discount_cols:
        if cleaned_df[col].isna().sum() > 0:
            cleaned_df[col] = cleaned_df[col].fillna(0)
            cleaning_log.append(f"Mặc định điền giá trị 0 cho ô trống tại cột chiết khấu/phụ phí '{col}'.")

    # 4.3 Suy diễn chéo toán học giữa Doanh thu, Đơn giá và Số lượng
    qty_cols = [c for c in cleaned_df.columns if any(k in str(c).lower() for k in ['qty', 'so_luong', 'quantity', 'units_sold'])]
    price_cols = [c for c in cleaned_df.columns if any(k in str(c).lower() for k in ['price', 'don_gia', 'gia'])]
    if rev_cols and qty_cols and price_cols:
        r_c, q_c, p_c = rev_cols[0], qty_cols[0], price_cols[0]
        # Nếu thiếu Doanh thu mà có Đơn giá & Số lượng
        fill_rev_mask = cleaned_df[r_c].isna() & cleaned_df[q_c].notna() & cleaned_df[p_c].notna()
        if fill_rev_mask.sum() > 0:
            cleaned_df.loc[fill_rev_mask, r_c] = cleaned_df.loc[fill_rev_mask, q_c] * cleaned_df.loc[fill_rev_mask, p_c]
            cleaning_log.append(f"Suy diễn toán học chéo: Tính Doanh thu = Đơn giá x Số lượng cho {fill_rev_mask.sum()} dòng.")
        # Nếu thiếu Số lượng mà có Doanh thu & Đơn giá
        fill_qty_mask = cleaned_df[q_c].isna() & cleaned_df[r_c].notna() & cleaned_df[p_c].notna() & (cleaned_df[p_c] > 0)
        if fill_qty_mask.sum() > 0:
            cleaned_df.loc[fill_qty_mask, q_c] = (cleaned_df.loc[fill_qty_mask, r_c] / cleaned_df.loc[fill_qty_mask, p_c]).round().clip(lower=1)
            cleaning_log.append(f"Suy diễn toán học chéo: Tính Số lượng = Doanh thu / Đơn giá cho {fill_qty_mask.sum()} dòng.")

    # 4.4 Xử lý các ô trống còn lại
    missing_before = int(cleaned_df.isna().sum().sum())
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
                        # Điền bằng Trung vị theo nhóm ngành nếu có, nếu không thì trung vị toàn cục
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
                        # Cột phân loại: nếu khuyết < 15% điền Mode, nếu >= 15% gán 'Chưa phân loại'
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
    # 5.1 Xử lý dấu âm theo trạng thái giao dịch
    status_cols = [c for c in cleaned_df.columns if any(k in str(c).lower() for k in ['status', 'trang_thai', 'return', 'hoan_tra'])]
    has_status = len(status_cols) > 0
    status_col = status_cols[0] if has_status else None

    for col in rev_cols:
        if pd.api.types.is_numeric_dtype(cleaned_df[col]):
            neg_mask = cleaned_df[col] < 0
            if neg_mask.sum() > 0:
                if has_status:
                    # Giữ nguyên dấu âm nếu trạng thái là hoàn trả, chuyển sang dương nếu trạng thái hoàn thành
                    completed_mask = neg_mask & cleaned_df[status_col].astype(str).str.lower().str.contains('hoàn thành|completed|thành công|success', regex=True)
                    if completed_mask.sum() > 0:
                        cleaned_df.loc[completed_mask, col] = cleaned_df.loc[completed_mask, col].abs()
                        cleaning_log.append(f"Đã sửa dấu âm sang dương cho {completed_mask.sum()} đơn hợp lệ do lỗi gõ dấu tại '{col}'.")
                else:
                    # Không có cột trạng thái: chuyển về trị tuyệt đối
                    cleaned_df[col] = cleaned_df[col].abs()
                    cleaning_log.append(f"Đã chuẩn hóa trị tuyệt đối cho các giá trị âm tại '{col}'.")

    # 5.2 Xử lý Số lượng = 0 nhưng Doanh thu > 0
    if rev_cols and qty_cols and price_cols:
        r_c, q_c, p_c = rev_cols[0], qty_cols[0], price_cols[0]
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
        "actions": cleaning_log,
        "user_request": user_request or ""
    }
    
    return cleaned_df, summary
