from typing import Dict, Any, List

def build_evaluation_framework(kpis: Dict[str, Any], anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Xây dựng khung đánh giá, đo lường KPI và cơ chế điều chỉnh giải pháp."""
    current_rev = kpis.get("total_revenue", 0)
    current_profit = kpis.get("total_profit", 0)
    current_margin = kpis.get("profit_margin_pct", 0)
    current_aov = kpis.get("aov", 0)
    
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

