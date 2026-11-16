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

        if df is None or df.empty or len(df.columns) == 0:
            return None, "Lỗi Bảng Tính Trống: Bảng tính Google Sheet không chứa hàng hoặc cột dữ liệu nào."
        return df, None
    except requests.exceptions.Timeout:
        return None, "Lỗi Hết Thời Gian Chờ (Timeout): Máy chủ phản hồi quá lâu khi tải bảng tính từ Google. Vui lòng kiểm tra lại đường truyền mạng và thử lại."
    except requests.exceptions.ConnectionError:
        return None, "Lỗi Kết Nối Mạng (Network Connection Error): Không thể kết nối tới máy chủ Google Docs. Vui lòng kiểm tra kết nối Internet của bạn."
    except Exception as e:
        return None, f"Lỗi Xử Lý Google Sheet: {str(e)}"

def load_uploaded_file(uploaded_file, filename: str = "") -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Đọc dữ liệu từ file upload (CSV, XLSX, XLS) với thông báo lỗi chi tiết."""
    try:
        fname = (filename or getattr(uploaded_file, "filename", "") or getattr(uploaded_file, "name", "") or "")
        fname = str(fname).lower()

        if fname.endswith('.csv'):
            for enc in ['utf-8-sig', 'utf-8', 'utf-16', 'cp1258', 'latin1']:
                try:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, encoding=enc, sep=None, engine='python', on_bad_lines='skip')
                    if not df.empty and len(df.columns) >= 1:
                        break
                except Exception:
                    continue
            else:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='latin1', on_bad_lines='skip')
        elif fname.endswith(('.xlsx', '.xls')):
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file)
        else:
            return None, f"Lỗi Định Dạng Tệp ({fname}): Hệ thống chỉ hỗ trợ tệp .csv, .xlsx hoặc .xls. Vui lòng kiểm tra lại định dạng tệp."
        
        if df is None or df.empty:
            return None, "Lỗi Tệp Dữ Liệu Rỗng: Tệp tải lên không chứa hàng dữ liệu nào hoặc tất cả các ô đều trống."
        return df, None
    except Exception as e:
        return None, f"Lỗi Đọc Tệp: {str(e)}"

