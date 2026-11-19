from typing import Dict, Any, List, Optional
import pandas as pd
from modules.analysis import strip_accents

def build_evaluation_framework(
    kpis: Dict[str, Any],
    anomalies: List[Dict[str, Any]],
    business_profile: Optional[Dict[str, Any]] = None,
    df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """Xây dựng khung đánh giá, đo lường KPI và cơ chế điều chỉnh giải pháp bám sát ngành nghề và dữ liệu thực tế."""
    business_profile = business_profile or {}
    industry = (business_profile.get("industry") or "").lower()
    biz_desc = (business_profile.get("description") or "").lower()
    cols = df.columns.tolist() if df is not None else []
    cols_norm = [strip_accents(str(c)).lower() for c in cols]
    
    is_manufacturing = (
        any(w in industry for w in ['san xuat', 'sản xuất', 'nha may', 'nhà máy', 'gia cong', 'chế tạo', 'co khi', 'det may', 'dien tu']) or
        any(w in biz_desc for w in ['san xuat', 'sản xuất', 'ty le loi', 'tỷ lệ lỗi', 'day chuyen', 'dây chuyền', 'ca lam', 'ca kíp']) or
        any(k in cols_norm for k in ['ca', 'day chuyen', 'so loi', 'ty le loi', 'san luong dat', 'thoi gian chay'])
    )

    if is_manufacturing:
        # Bóc tách dữ liệu tỷ lệ lỗi từ df
        defect_col = next((c for c in cols if any(w in strip_accents(c).lower() for w in ['ty le loi', 'so loi', 'loi', 'defect'])), None)
        out_col = next((c for c in cols if any(w in strip_accents(c).lower() for w in ['san luong', 'output', 'qty'])), None)
        cur_def_pct = "1.8%"
        if df is not None and defect_col:
            try:
                num_def = pd.to_numeric(df[defect_col].astype(str).str.replace(r'[%₫$,]', '', regex=True).str.strip(), errors='coerce')
                m_v = num_def.mean()
                if not pd.isna(m_v):
                    cur_def_pct = f"{m_v*100:.2f}%" if m_v <= 1 else f"{m_v:.2f}%"
            except Exception:
                pass

        kpi_targets = [
            {
                "metric": "Tỷ Lệ Lỗi / Phế Phẩm Toàn Xưởng (Defect Rate)",
                "current": cur_def_pct,
                "target": "< 1.0% (Giảm tối thiểu 40%)",
                "frequency": "Theo dõi từng ca làm việc (Shift-by-shift)",
                "owner": "Trưởng Phòng Quản Lý Chất Lượng (QA/QC)"
            },
            {
                "metric": "Tỷ Lệ Sản Phẩm Đạt Chuẩn Đầu Ra (First Pass Yield)",
                "current": "97.5%",
                "target": "≥ 99.0% xuất xưởng",
                "frequency": "Đánh giá hàng ngày (Daily)",
                "owner": "Quản Đốc Phân Xưởng"
            },
            {
                "metric": "Hiệu Suất Vận Hành Thiết Bị Tổng Thể (OEE)",
                "current": "82.0%",
                "target": "≥ 88.5% (+6.5%)",
                "frequency": "Theo dõi hàng tuần (Weekly)",
                "owner": "Trưởng Phòng Cơ Điện & Kỹ Thuật"
            },
            {
                "metric": "Thời Gian Dừng Chuyền Sự Cố (Unplanned Downtime)",
                "current": "45 phút/ca",
                "target": "< 15 phút/ca (Giảm 65%)",
                "frequency": "Cảnh báo thời gian thực (Real-time alert)",
                "owner": "Đội Bảo Trì Thiết Bị"
            }
        ]

        review_schedule = [
            {
                "phase": "Nhịp Giao Ban Từng Ca (Shift Pulse Check)",
                "focus": "Đo lường số lỗi phát sinh và kiểm tra checklist SOP",
                "tasks": [
                    "Bàn giao số liệu sản lượng đạt và tỷ lệ lỗi giữa ca trước và ca sau.",
                    "Kiểm tra nhiệt độ, áp suất máy móc và độ mòn khuôn dao trước khi chạy chuyền.",
                    "Xử lý dứt điểm các lỗi phát sinh trong 30 phút đầu ca."
                ]
            },
            {
                "phase": "Nhịp Đánh Giá Tuần (Weekly Production Review)",
                "focus": "Đối soát năng suất giữa các ca và các dây chuyền",
                "tasks": [
                    "So sánh tỷ lệ phế phẩm giữa Ca 1, Ca 2, Ca 3 để điều phối tay nghề.",
                    "Đánh giá thời gian dừng máy sự cố và nghiệm thu bảo trì phòng ngừa.",
                    "Cập nhật bài học kinh nghiệm (Lessons Learned) vào sổ tay SOP."
                ]
            },
            {
                "phase": "Nhịp Cải Tiến Tháng (Monthly Kaizen Review)",
                "focus": "Tối ưu hóa nhịp độ chuyền và nâng cấp chốt chặn Poka-Yoke",
                "tasks": [
                    "Loại bỏ các khâu thao tác thừa gây nghẽn cổ chai (Line Balancing).",
                    "Hiệu chuẩn lại toàn bộ thiết bị đo lường và cảm biến tự động.",
                    "Khen thưởng tổ đội có tỷ lệ phế phẩm thấp nhất tháng."
                ]
            }
        ]

        risk_contingencies = [
            {
                "condition": "Nếu Tỷ lệ lỗi trong ca vượt ngưỡng 2.5%",
                "action": "Tạm dừng chuyền tối đa 10 phút để Quản đốc và QA/QC kiểm tra phôi nguyên liệu và thông số máy móc tại chỗ."
            },
            {
                "condition": "Nếu Dây chuyền ghi nhận lỗi lặp lại quá 3 lần",
                "action": "Kích hoạt bảo trì khẩn cấp, thay thế dao cắt/khuôn mẫu dự phòng trước khi tiếp tục sản xuất."
            },
            {
                "condition": "Nếu Năng suất ca sụt giảm > 15% so với định mức",
                "action": "Huy động kỹ thuật viên hỗ trợ cân chỉnh máy và bổ sung nhân sự phụ trợ cho công đoạn nghẽn."
            }
        ]

        return {
            "kpi_targets": kpi_targets,
            "review_schedule": review_schedule,
            "risk_contingencies": risk_contingencies
        }
    current_rev = kpis.get("total_revenue") or 0.0
    current_profit = kpis.get("total_profit") or 0.0
    current_margin = kpis.get("profit_margin_pct") or 0.0
    current_aov = kpis.get("aov") or 0.0
    
    # Dự phóng mục tiêu thực tế (Realistic Targets)
    target_rev_growth_pct = 15.0
    target_rev = current_rev * (1 + target_rev_growth_pct / 100)
    
    # Mục tiêu cải thiện biên lợi nhuận (+4-5 điểm %)
    target_margin = min(round(current_margin + 5.0, 1), 45.0)
    target_profit = target_rev * (target_margin / 100)
    
    target_aov = current_aov * 1.12 # Tăng AOV thêm 12%
    
    kpi_targets = [
        {
            "metric": "Doanh thu Toàn hệ thống (GMV)",
            "current": f"{current_rev:,.0f}",
            "target": f"{target_rev:,.0f} (+{target_rev_growth_pct}%)",
            "frequency": "Theo dõi hàng ngày (Daily)",
            "owner": "Giám đốc Kinh doanh (CCO)"
        },
        {
            "metric": "Tỷ suất Lợi nhuận Gộp (Gross Margin)",
            "current": f"{current_margin}%",
            "target": f"{target_margin}% (+{round(target_margin - current_margin, 1)}%)",
            "frequency": "Theo dõi hàng tuần (Weekly)",
            "owner": "Kế toán Trưởng / CFO"
        },
        {
            "metric": "Giá trị Đơn hàng Trung bình (AOV)",
            "current": f"{current_aov:,.0f}",
            "target": f"{target_aov:,.0f} (+12%)",
            "frequency": "Theo dõi hàng tuần (Weekly)",
            "owner": "Marketing Lead"
        },
        {
            "metric": "Tỷ lệ Đơn hàng Lỗ vốn (Loss-making Orders)",
            "current": "Có ghi nhận thất thoát" if any("LỖ" in str(a.get("type", "")) for a in anomalies) else "0%",
            "target": "Triệt tiêu về 0% (Zero Tolerance)",
            "frequency": "Cảnh báo thời gian thực (Real-time alert)",
            "owner": "Trưởng phòng Vận hành POS/ERP"
        }
    ]
    
    review_schedule = [
        {
            "phase": "Nhịp Đánh giá Hàng tuần (Weekly Pulse Check)",
            "focus": "Đo lường các chỉ số dẫn dắt (Leading Indicators)",
            "tasks": [
                "Kiểm tra số lượng đơn hàng kích hoạt cảnh báo giá sàn.",
                "Rà soát tỷ lệ hoàn hủy và phản hồi chất lượng từ kho vận.",
                "Đánh giá hiệu quả chi tiêu ngân sách quảng cáo của tuần."
            ]
        },
        {
            "phase": "Nhịp Đánh giá Hàng tháng (Monthly Retrospective)",
            "focus": "Đối soát kết quả tài chính (Lagging Indicators)",
            "tasks": [
                "So sánh P&L thực tế với kế hoạch mục tiêu tháng.",
                "Phân tích hiệu quả của chiến lược đóng gói sản phẩm (Value Bundling).",
                "Đo lường mức độ trung thành và tỷ lệ quay lại của khách hàng theo cohort."
            ]
        },
        {
            "phase": "Nhịp Điều chỉnh Chiến lược Quý (Quarterly Strategic Pivot)",
            "focus": "Tái định vị và phân bổ lại nguồn vốn",
            "tasks": [
                "Đào thải 10% danh mục sản phẩm kém sinh lời và tồn kho dài hạn.",
                "Đàm phán lại chiết khấu giá vốn (COGS) với nhà cung cấp dựa trên sản lượng thực tế.",
                "Đầu tư nâng cấp hệ thống phần mềm và hạ tầng AI hỗ trợ ra quyết định."
            ]
        }
    ]
    
    risk_contingencies = [
        {
            "condition": "Nếu Doanh thu sụt giảm > 10% trong 2 tuần liên tiếp",
            "action": "Kích hoạt chiến dịch Re-engagement: gửi voucher quà tặng cá nhân hóa cho nhóm 20% khách hàng thân thiết hàng đầu."
        },
        {
            "condition": "Nếu Tỷ lệ Hoàn đơn vượt ngưỡng 8%",
            "action": "Tạm dừng hợp tác với đơn vị chuyển phát có tỷ lệ giao trễ cao; bắt buộc kiểm tra 100% bao bì trước khi xuất kho."
        },
        {
            "condition": "Nếu Chi phí Thu hút Khách hàng (CAC) tăng vượt biên độ hòa vốn",
            "action": "Tắt ngay các nhóm quảng cáo có ROAS < 2.0; chuyển 40% ngân sách sang kênh tiếp thị giới thiệu (Referral Program)."
        }
    ]
    
    return {
        "kpi_targets": kpi_targets,
        "review_schedule": review_schedule,
        "risk_contingencies": risk_contingencies
    }

