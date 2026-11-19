import io
import re
import requests
import pandas as pd
from typing import Optional, Tuple

def parse_google_sheet_url(url: str) -> Optional[str]:
    """
    Trích xuất link export CSV từ URL Google Sheet thông thường.
    Hỗ trợ các định dạng:
    - https://docs.google.com/spreadsheets/d/{ID}/edit#gid={GID}
    - https://docs.google.com/spreadsheets/d/{ID}/view
    """
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if not match:
        return None
    sheet_id = match.group(1)
    
    # Tìm gid nếu có
    gid_match = re.search(r"[#&?]gid=([0-9]+)", url)
    gid = gid_match.group(1) if gid_match else "0"
    
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return export_url

def load_google_sheet(url: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Tải dữ liệu từ URL Google Sheet với thông báo lỗi chi tiết và chính xác."""
    try:
        export_url = parse_google_sheet_url(url)
        if not export_url:
            return None, "Lỗi Định Dạng URL: Đường link Google Sheet không hợp lệ. Vui lòng kiểm tra lại cấu trúc URL (dạng docs.google.com/spreadsheets/d/...)."
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(export_url, headers=headers, timeout=15)
        
        if response.status_code == 404:
            return None, "Lỗi Không Tìm Thấy (HTTP 404): Không tìm thấy bảng tính Google Sheet này. Bảng tính có thể đã bị xóa hoặc sai ID trong đường dẫn."
        elif response.status_code == 403:
            return None, "Lỗi Bị Từ Chối Truy Cập (HTTP 403): Bảng tính Google Sheet bị chặn xuất dữ liệu hoặc hạn chế bởi chính sách bảo mật nội bộ của tổ chức."
        elif response.status_code != 200:
            return None, f"Lỗi Máy Chủ Phản Hồi (HTTP {response.status_code}): Không thể tải dữ liệu từ Google Sheet. Mã phản hồi máy chủ: {response.status_code}."
            
        # Kiểm tra nếu Google chuyển hướng sang trang đăng nhập (Sheet Private)
        if "accounts.google.com" in response.url or "ServiceLogin" in response.url:
            return None, "Lỗi Quyền Truy Cập (Sheet Riêng Tư - Private): Bảng tính Google Sheet này chưa được mở quyền chia sẻ công khai. Vui lòng mở quyền 'Bất kỳ ai có đường liên kết đều có thể xem'."
            
        content = response.content.decode('utf-8', errors='replace')
        if content.strip().startswith("<!DOCTYPE") or "<html" in content[:300].lower():
            return None, "Lỗi Xác Thực Tài Khoản: Google Sheet yêu cầu đăng nhập tài khoản. Vui lòng chuyển quyền chia sẻ thành 'Bất kỳ ai có liên kết đều có thể xem' (Anyone with the link can view)."
            
        try:
            df = pd.read_csv(io.StringIO(content), on_bad_lines='skip', sep=None, engine='python')
        except Exception:
            try:
                df = pd.read_csv(io.StringIO(content), on_bad_lines='skip')
            except Exception as e:
                return None, f"Không thể đọc nội dung bảng tính: {str(e)}"

        ok, err = validate_dataframe_has_data(df)
        if not ok:
            return None, err
        return df, None
    except requests.exceptions.Timeout:
        return None, "Lỗi Hết Thời Gian Chờ (Timeout): Máy chủ phản hồi quá lâu khi tải bảng tính từ Google. Vui lòng kiểm tra lại đường truyền mạng và thử lại."
    except requests.exceptions.ConnectionError:
        return None, "Lỗi Kết Nối Mạng (Network Connection Error): Không thể kết nối tới máy chủ Google Docs. Vui lòng kiểm tra kết nối Internet của bạn."
    except Exception as e:
        return None, f"Lỗi Xử Lý Google Sheet: {str(e)}"

def validate_dataframe_has_data(df: Optional[pd.DataFrame]) -> Tuple[bool, Optional[str]]:
    """
    Kiểm định tệp dữ liệu đầu vào theo ĐÚNG 6 trường hợp người dùng quy định:
    1. File rỗng (0 dòng, 0 cột, hoặc toàn bộ là ô trống)
    2. Vượt quá 20.000 dòng
    3. Vượt quá 200 cột
    4. Dữ liệu không có ý nghĩa (bảng chỉ có 1 dòng, hoặc toàn bộ ô chứa 1 giá trị duy nhất không có biến thiên)
    5. Sai định dạng (được kiểm tra ở tầng đọc file)
    6. Chưa mở quyền truy cập (được kiểm tra ở tầng đọc file/URL)

    Ngoài 6 trường hợp trên, mọi tệp hợp lệ khác ĐỀU ĐƯỢC CHẤP NHẬN.
    """
    # 1. Kiểm tra File rỗng
    if df is None or df.empty or len(df.columns) == 0 or len(df) == 0:
        return False, "Lỗi Tệp Rỗng: Tệp tải lên hoàn toàn không có dữ liệu (0 dòng hoặc 0 cột)."

    # 2. Kiểm tra Vượt quá 200 cột
    MAX_ALLOWED_COLS = 200
    if len(df.columns) > MAX_ALLOWED_COLS:
        return False, (
            f"Lỗi Vượt Quá 200 Cột: Tệp chứa {len(df.columns)} cột, "
            f"vượt quá giới hạn tối đa cho phép ({MAX_ALLOWED_COLS} cột)."
        )

    # 3. Kiểm tra Vượt quá 20.000 dòng
    MAX_ALLOWED_ROWS = 20000
    if len(df) > MAX_ALLOWED_ROWS:
        return False, (
            f"Lỗi Vượt Quá 20.000 Dòng: Tệp chứa {len(df):,} dòng dữ liệu, "
            f"vượt quá giới hạn tối đa cho phép ({MAX_ALLOWED_ROWS:,} dòng)."
        )

    # 4. Kiểm tra dữ liệu rỗng sau khi loại bỏ dòng trống
    non_empty = df.dropna(how='all')
    if non_empty.empty or len(non_empty) == 0:
        return False, "Lỗi Tệp Rỗng: Tất cả các dòng trong bảng tính đều là ô trống (không có dữ liệu)."

    # 5. Kiểm tra Dữ liệu không có ý nghĩa
    # a. Quá ít dòng (chỉ có 1 dòng dữ liệu duy nhất, không thể tạo phân tích/so sánh)
    if len(non_empty) < 2:
        return False, (
            f"Lỗi Dữ Liệu Không Có Ý Nghĩa: Bảng chỉ có {len(non_empty)} dòng dữ liệu, "
            "không đủ số lượng tối thiểu để phân tích (yêu cầu tối thiểu từ 2 dòng trở lên)."
        )

    # b. Toàn bộ các ô trong toàn bảng chỉ chứa giá trị rỗng/khoảng trắng
    invalid_tokens = {"", "nan", "none", "null", "undefined", "n/a", "na"}
    all_values_list = []
    for c in non_empty.columns:
        col_vals = non_empty[c].dropna()
        for val in col_vals:
            s_val = str(val).strip().lower()
            if s_val not in invalid_tokens:
                all_values_list.append(s_val)

    if len(all_values_list) == 0:
        return False, "Lỗi Dữ Liệu Không Có Ý Nghĩa: Toàn bộ các ô trong tệp đều là khoảng trắng hoặc không có giá trị."

    # c. Toàn bộ bảng chỉ chứa cùng 1 giá trị lặp lại (không có bất kỳ biến thiên nào)
    unique_vals = set(all_values_list)
    if len(unique_vals) <= 1:
        val_sample = list(unique_vals)[0] if unique_vals else ""
        return False, (
            f"Lỗi Dữ Liệu Không Có Ý Nghĩa: Toàn bộ dữ liệu trong bảng đều là cùng một giá trị lặp lại "
            f"('{val_sample}'), không có sự biến thiên để phân tích kinh doanh."
        )

    # Đạt toàn bộ kiểm định hợp lệ!
    return True, None

def load_uploaded_file(uploaded_file, filename: str = "") -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Đọc dữ liệu từ file upload (CSV, XLSX, XLS) với thông báo lỗi chi tiết theo đúng 6 quy chuẩn."""
    try:
        fname = (filename or getattr(uploaded_file, "filename", "") or getattr(uploaded_file, "name", "") or "")
        fname = str(fname).lower().strip()

        # 1. Kiểm tra File rỗng (0 bytes)
        if hasattr(uploaded_file, "seek") and hasattr(uploaded_file, "tell"):
            uploaded_file.seek(0, 2)
            fsize = uploaded_file.tell()
            uploaded_file.seek(0)
            if fsize == 0:
                return None, "Lỗi Tệp Rỗng (0 Bytes): Tệp tải lên hoàn toàn không có dữ liệu (kích thước tệp bằng 0 bytes)."

        # 2. Kiểm tra Sai định dạng (phần mở rộng)
        if not fname.endswith(('.csv', '.xlsx', '.xls')):
            return None, (
                f"Lỗi Sai Định Dạng Tệp ({fname}): Hệ thống chỉ chấp nhận tệp bảng tính hợp lệ (.CSV, .XLSX hoặc .XLS). "
                "Vui lòng kiểm tra lại định dạng tệp trước khi tải lên."
            )

        df = None
        if fname.endswith('.csv'):
            try:
                for enc in ['utf-8-sig', 'utf-8', 'utf-16', 'cp1258', 'latin1']:
                    try:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, encoding=enc, sep=None, engine='python', on_bad_lines='skip')
                        if not df.empty and len(df.columns) >= 1:
                            break
                    except (pd.errors.EmptyDataError, Exception):
                        continue
                else:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, encoding='latin1', on_bad_lines='skip')
            except pd.errors.EmptyDataError:
                return None, "Lỗi Tệp Rỗng: Tệp CSV không chứa bất kỳ cột hoặc dòng dữ liệu nào."
            except PermissionError:
                return None, "Lỗi Chưa Mở Quyền Truy Cập: Tệp đang bị khóa hoặc hệ thống không được cấp quyền đọc tệp này."
            except Exception as e:
                err_str = str(e).lower()
                if any(k in err_str for k in ['permission', 'access denied', 'unauthorized', 'lock']):
                    return None, "Lỗi Chưa Mở Quyền Truy Cập: Tệp đang bị khóa quyền truy cập. Vui lòng mở quyền đọc và thử lại."
                return None, f"Lỗi Sai Định Dạng: Không thể đọc cấu trúc tệp CSV do tệp bị hỏng hoặc sai định dạng ({str(e)})."
        elif fname.endswith(('.xlsx', '.xls')):
            try:
                uploaded_file.seek(0)
                df = pd.read_excel(uploaded_file)
            except PermissionError:
                return None, "Lỗi Chưa Mở Quyền Truy Cập: Tệp Excel đang bị khóa quyền truy cập từ hệ thống."
            except Exception as e:
                err_str = str(e).lower()
                if any(k in err_str for k in ['password', 'encrypt', 'protect', 'permission', 'unauthorized', 'lock']):
                    return None, "Lỗi Chưa Mở Quyền Truy Cập: Tệp Excel bị khóa mật khẩu hoặc chưa mở quyền truy cập. Vui lòng gỡ mật khẩu và thử lại."
                return None, f"Lỗi Sai Định Dạng: Không thể đọc cấu trúc tệp Excel do tệp bị hỏng hoặc sai định dạng ({str(e)})."
        
        ok, err = validate_dataframe_has_data(df)
        if not ok:
            return None, err
            
        return df, None
    except PermissionError:
        return None, "Lỗi Chưa Mở Quyền Truy Cập: Tệp đang bị khóa mật khẩu hoặc quyền truy cập bị từ chối."
    except Exception as e:
        err_str = str(e).lower()
        if any(k in err_str for k in ['password', 'encrypt', 'protect', 'permission', 'unauthorized', 'lock']):
            return None, "Lỗi Chưa Mở Quyền Truy Cập: Tệp đang bị khóa mật khẩu hoặc chưa mở quyền truy cập."
        return None, f"Lỗi Sai Định Dạng: Không thể đọc tệp dữ liệu ({str(e)})."

