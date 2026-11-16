import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

def auto_detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Tự động phân loại các cột quan trọng phục vụ phân tích kinh doanh."""
    cols_map = {
        "date_col": None,
        "revenue_col": None,
        "profit_col": None,
        "cost_col": None,
        "quantity_col": None,
        "category_col": None,
        "segment_col": None,
        "channel_col": None,
        "discount_col": None,
        "return_col": None
    }
    
    col_names_lower = {c: str(c).lower() for c in df.columns}
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category', 'string']).columns.tolist()
    date_cols = df.select_dtypes(include=['datetime64', 'datetime']).columns.tolist()
    
    # 1. Date Col
    if date_cols:
        cols_map["date_col"] = date_cols[0]
    else:
        for c, cl in col_names_lower.items():
            if any(k in cl for k in ['date', 'ngày', 'time', 'ngay', 'thang', 'month']):
                cols_map["date_col"] = c
                break
                
    # 2. Revenue / Sales
    for c, cl in col_names_lower.items():
        if c in numeric_cols and any(k in cl for k in ['revenue', 'doanh_thu', 'doanhthu', 'sales', 'total_amount', 'tien_hang', 'amount', 'tong_tien', 'thanh_tien', 'gia_tri', 'price', 'gia']):
            cols_map["revenue_col"] = c
            break
    if not cols_map["revenue_col"] and numeric_cols:
        cols_map["revenue_col"] = numeric_cols[0]
            
    # 3. Profit
    for c, cl in col_names_lower.items():
        if c in numeric_cols and any(k in cl for k in ['profit', 'loi_nhuan', 'loinhuan', 'gross_profit', 'margin', 'lai']):
            cols_map["profit_col"] = c
            break

    # 4. Cost
    for c, cl in col_names_lower.items():
        if c in numeric_cols and any(k in cl for k in ['cost', 'cogs', 'chi_phi', 'chiphi', 'gia_von', 'expense']):
            cols_map["cost_col"] = c
            break

    # 5. Quantity
    for c, cl in col_names_lower.items():
        if c in numeric_cols and any(k in cl for k in ['qty', 'quantity', 'so_luong', 'soluong', 'units_sold', 'units']):
            cols_map["quantity_col"] = c
            break

    # 6. Discount
    for c, cl in col_names_lower.items():
        if c in numeric_cols and any(k in cl for k in ['discount', 'chiet_khau', 'chietkhau', 'giam_gia']):
            cols_map["discount_col"] = c
            break

    # 7. Category
    for c, cl in col_names_lower.items():
        if c in categorical_cols and any(k in cl for k in ['category', 'danh_muc', 'nganh_hang', 'product_category', 'loai_sp']):
            cols_map["category_col"] = c
            break
    if not cols_map["category_col"] and categorical_cols:
        cols_map["category_col"] = categorical_cols[0]

    # 8. Segment / Customer / Region
    for c, cl in col_names_lower.items():
        if c in categorical_cols and any(k in cl for k in ['segment', 'customer', 'khach_hang', 'branch', 'chi_nhanh', 'region', 'khuvuc']):
            cols_map["segment_col"] = c
            break

    # 9. Channel
    for c, cl in col_names_lower.items():
        if c in categorical_cols and any(k in cl for k in ['channel', 'kenh_ban', 'source', 'platform', 'marketing_channel']):
            cols_map["channel_col"] = c
            break

    # 10. Return / Status
    for c, cl in col_names_lower.items():
        if any(k in cl for k in ['return', 'tra_hang', 'status', 'trang_thai', 'churn']):
            cols_map["return_col"] = c
            break

    return cols_map

def calculate_kpis(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> Dict[str, Any]:
    """Tính toán các chỉ số kinh doanh chủ chốt (Core KPIs)."""
    kpis = {
        "total_records": len(df),
        "total_revenue": 0.0,
        "total_profit": 0.0,
        "profit_margin_pct": 0.0,
        "total_cost": 0.0,
        "total_units": 0,
        "aov": 0.0
    }
    
    rev_col = mapping.get("revenue_col")
    prof_col = mapping.get("profit_col")
    cost_col = mapping.get("cost_col")
    qty_col = mapping.get("quantity_col")
    
    if rev_col and rev_col in df.columns:
        kpis["total_revenue"] = float(df[rev_col].sum())
        kpis["aov"] = float(df[rev_col].mean())
        
    if prof_col and prof_col in df.columns:
        kpis["total_profit"] = float(df[prof_col].sum())
    elif rev_col and cost_col and cost_col in df.columns:
        kpis["total_cost"] = float(df[cost_col].sum())
        kpis["total_profit"] = kpis["total_revenue"] - kpis["total_cost"]
        
    if cost_col and cost_col in df.columns:
        kpis["total_cost"] = float(df[cost_col].sum())
        
    if kpis["total_revenue"] > 0 and kpis["total_profit"] != 0:
        kpis["profit_margin_pct"] = round((kpis["total_profit"] / kpis["total_revenue"]) * 100, 2)
        
    if qty_col and qty_col in df.columns:
        kpis["total_units"] = int(df[qty_col].sum())
        
    return kpis

def analyze_trends(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> Optional[pd.DataFrame]:
    """Phân tích biến động theo chuỗi thời gian."""
    date_col = mapping.get("date_col")
    rev_col = mapping.get("revenue_col")
    
    if not date_col or not rev_col or date_col not in df.columns or rev_col not in df.columns:
        return None
        
    temp_df = df.dropna(subset=[date_col, rev_col]).copy()
    if not pd.api.types.is_datetime64_any_dtype(temp_df[date_col]):
        temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors='coerce')
    temp_df = temp_df.dropna(subset=[date_col])
    
    if temp_df.empty:
        return None
        
    # Group theo ngày hoặc tuần
    temp_df['period'] = temp_df[date_col].dt.to_period('D').dt.to_timestamp()
    
    agg_dict = {rev_col: 'sum'}
    prof_col = mapping.get("profit_col")
    if prof_col and prof_col in temp_df.columns:
        agg_dict[prof_col] = 'sum'
        
    trend_df = temp_df.groupby('period').agg(agg_dict).reset_index()
    trend_df = trend_df.sort_values('period')
    
    # Tính đường trung bình động (Moving average 7 periods) và % tăng trưởng
    trend_df['revenue_ma7'] = trend_df[rev_col].rolling(window=7, min_periods=1).mean()
    trend_df['growth_rate_pct'] = trend_df[rev_col].pct_change() * 100
    
    return trend_df

def analyze_breakdowns(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> Dict[str, pd.DataFrame]:
    """Phân tích doanh thu & lợi nhuận theo danh mục, phân khúc, kênh bán."""
    breakdowns = {}
    rev_col = mapping.get("revenue_col")
    prof_col = mapping.get("profit_col")
    
    if not rev_col or rev_col not in df.columns:
        return breakdowns
        
    for key, label in [("category_col", "Category"), ("segment_col", "Segment"), ("channel_col", "Channel")]:
        dim_col = mapping.get(key)
        if dim_col and dim_col in df.columns:
            agg_funcs = {rev_col: ['sum', 'count']}
            if prof_col and prof_col in df.columns:
                agg_funcs[prof_col] = ['sum']
                
            grouped = df.groupby(dim_col).agg(agg_funcs)
            grouped.columns = ['_'.join(c).strip() for c in grouped.columns]
            grouped = grouped.reset_index()
            
            # Đổi tên cho trực quan
            grouped = grouped.rename(columns={
                dim_col: label,
                f"{rev_col}_sum": "Revenue",
                f"{rev_col}_count": "Orders_Count",
                f"{prof_col}_sum": "Profit" if prof_col else "Revenue"
            })
            
            grouped["Revenue_Share_Pct"] = round(grouped["Revenue"] / grouped["Revenue"].sum() * 100, 2)
            if "Profit" in grouped.columns:
                grouped["Margin_Pct"] = round(grouped["Profit"] / grouped["Revenue"] * 100, 2)
                
            grouped = grouped.sort_values(by="Revenue", ascending=False)
            breakdowns[label] = grouped
            
    return breakdowns

def detect_anomalies(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> List[Dict[str, Any]]:
    """Phát hiện các điểm bất thường và rủi ro kinh doanh."""
    anomalies = []
    rev_col = mapping.get("revenue_col")
    prof_col = mapping.get("profit_col")
    disc_col = mapping.get("discount_col")
    ret_col = mapping.get("return_col")
    
    # 1. Phát hiện đơn hàng bán lỗ (Negative Profit)
    if prof_col and prof_col in df.columns:
        loss_orders = df[df[prof_col] < 0]
        if len(loss_orders) > 0:
            total_loss = abs(float(loss_orders[prof_col].sum()))
            anomalies.append({
                "type": "CẢNH BÁO LỢI NHUẬN ÂM (BÁN LỖ)",
                "severity": "HIGH",
                "count": len(loss_orders),
                "metric": f"{round(len(loss_orders)/len(df)*100, 1)}% tổng số đơn",
                "impact": f"Tổng mức lỗ ghi nhận: {total_loss:,.0f}",
                "description": f"Phát hiện {len(loss_orders)} đơn hàng có biên lợi nhuận âm. Nguyên nhân thường do chiết khấu quá mức hoặc chi phí vốn bị đội giá."
            })

    # 2. Phát hiện chiết khấu quá cao (Excessive Discount)
    if disc_col and disc_col in df.columns:
        high_disc = df[df[disc_col] > 30] # Chiết khấu > 30%
        if len(high_disc) > 0:
            anomalies.append({
                "type": "CHIẾT KHẤU / GIẢM GIÁ ĐỘT BIẾN",
                "severity": "MEDIUM",
                "count": len(high_disc),
                "metric": f"{round(len(high_disc)/len(df)*100, 1)}% đơn áp mã giảm sâu >30%",
                "impact": f"Giá trị chiết khấu trung bình: {high_disc[disc_col].mean():.1f}%",
                "description": f"Có {len(high_disc)} đơn hàng chịu mức giảm giá vượt ngưỡng an toàn (>30%), làm bào mòn nghiêm trọng lợi nhuận ròng."
            })

    # 3. Phát hiện tỷ lệ hoàn huỷ hàng cao (Return / Churn Spike)
    if ret_col and ret_col in df.columns:
        ret_series = df[ret_col].astype(str).str.lower()
        is_return = ret_series.str.contains(r'return|huỷ|tra|refund|cancel|yes|true|1', regex=True)
        return_cnt = int(is_return.sum())
        if return_cnt > 0:
            ret_rate = round(return_cnt / len(df) * 100, 2)
            severity = "HIGH" if ret_rate > 10 else "MEDIUM"
            anomalies.append({
                "type": "TỶ LỆ HOÀN TRẢ / HỦY ĐƠN ĐÁNG CHÚ Ý",
                "severity": severity,
                "count": return_cnt,
                "metric": f"Tỷ lệ hoàn trả: {ret_rate}%",
                "impact": f"{return_cnt} đơn hàng không hoàn tất",
                "description": f"Tỷ lệ hoàn huỷ đạt {ret_rate}%. Cần rà soát chất lượng sản phẩm, đối tác giao vận hoặc lỗi thông tin sản phẩm trên website."
            })

    # 4. Phát hiện Outlier doanh thu (Z-score > 3 hoặc sụt giảm đột ngột)
    if rev_col and rev_col in df.columns and len(df) > 10:
        mean_rev = df[rev_col].mean()
        std_rev = df[rev_col].std()
        if std_rev > 0:
            outliers_high = df[df[rev_col] > mean_rev + 3 * std_rev]
            if len(outliers_high) > 0:
                anomalies.append({
                    "type": "GIAO DỊCH GIÁ TRỊ ĐỘT BIẾN (OUTLIER)",
                    "severity": "LOW",
                    "count": len(outliers_high),
                    "metric": f"{len(outliers_high)} giao dịch VIP",
                    "impact": f"Doanh thu từ các đơn này: {outliers_high[rev_col].sum():,.0f}",
                    "description": "Các giao dịch có giá trị cực lớn vượt 3 độ lệch chuẩn so với trung bình, đóng góp đáng kể nhưng có thể gây méo mó dự báo."
                })

    return anomalies

def calculate_correlations(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Tính ma trận tương quan giữa các biến định lượng."""
    numeric_df = df.select_dtypes(include=[np.number])
    if len(numeric_df.columns) < 2:
        return None
    return numeric_df.corr().round(3)

