import pandas as pd
from typing import Dict, Any, List, Optional

def generate_business_solutions(
    insights: List[Dict[str, Any]],
    kpis: Dict[str, Any],
    anomalies: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Tạo đề xuất giải pháp kinh doanh toàn diện dựa trên các insight phát hiện được."""
    
    solutions_matrix = {
        "quick_wins": [],
        "strategic_projects": [],
        "operational_fixes": []
    }
    
    # 1. Rà soát giải pháp cho biên lợi nhuận & bán lỗ
    has_loss = any("LỖ" in str(a.get("type", "")) for a in anomalies)
    has_high_disc = any("CHIẾT KHẤU" in str(a.get("type", "")) for a in anomalies)
    margin = kpis.get("profit_margin_pct", 0)
    
    if has_loss or margin < 20:
        solutions_matrix["quick_wins"].append({
            "title": "Thiết lập Rào cản Giá Sàn Tự động (Price Floor Guardrails)",
            "timeline": "1 tuần",
            "impact": "TĂNG NGAY 5-8% LỢI NHUẬN",
            "effort": "Thấp (Cấu hình phần mềm POS/ERP)",
            "details": "Khóa tính năng tự động cho phép nhân viên sale gộp nhiều voucher nếu tỷ suất lợi nhuận của đơn hàng giảm xuống dưới 12%. Yêu cầu phê duyệt từ Trưởng phòng nếu chiết khấu > 20%."
        })
        solutions_matrix["strategic_projects"].append({
            "title": "Tái cấu trúc Chính sách Bó Sản phẩm (Value Bundling Strategy)",
            "timeline": "1 tháng",
            "impact": "Tăng AOV thêm 18% & xả hàng chậm luân chuyển",
            "effort": "Trung bình (Phòng Kinh doanh & Marketing)",
            "details": "Thay vì giảm giá trực tiếp các mặt hàng bán chạy, hãy ghép cặp sản phẩm 'Hero Product' (biên lợi nhuận cao) với phụ kiện tồn kho thành combo ưu đãi độc quyền."
        })
        
    if has_high_disc:
        solutions_matrix["quick_wins"].append({
            "title": "Thay thế Giảm giá trực tiếp bằng Quà tặng/Voucher mua lại",
            "timeline": "3 ngày",
            "impact": "Bảo vệ biên độ giá & Tăng tần suất quay lại +25%",
            "effort": "Thấp",
            "details": "Chuyển đổi hình thức giảm 15% tiền mặt thành tặng voucher hoàn tiền 20% cho đơn hàng tiếp theo trong vòng 30 ngày."
        })

    # 2. Rà soát giải pháp cho Tỷ lệ Hoàn hủy & Vận chuyển
    has_returns = any("HOÀN TRẢ" in str(a.get("type", "")) for a in anomalies)
    if has_returns:
        solutions_matrix["operational_fixes"].append({
            "title": "Quy trình Xác thực Đơn hàng & Cải tiến Bao bì Đóng gói",
            "timeline": "2 tuần",
            "impact": "Giảm tỷ lệ hoàn đơn xuống dưới 5%",
            "effort": "Trung bình (Đội Vận hành kho & CSKH)",
            "details": "Thiết lập chatbot/nhân viên gọi điện xác nhận đơn cho khách hàng mới trong vòng 15 phút. Nâng cấp quy trình bọc chống sốc và dán seal niêm phong để hạn chế hư hỏng khi vận chuyển."
        })

    # 3. Giải pháp tăng trưởng AOV và Giữ chân khách hàng
    solutions_matrix["strategic_projects"].append({
        "title": "Chương trình Khách hàng Thân thiết & Phân tầng VIP (Tiered Loyalty)",
        "timeline": "4-6 tuần",
        "impact": "Tăng giá trị trọn đời khách hàng (CLV) +35%",
        "effort": "Cao (Tích hợp CRM và kịch bản CSKH tự động)",
        "details": "Phân loại khách hàng theo mô hình RFM (Recency - Frequency - Monetary). Cung cấp quyền lợi miễn phí vận chuyển trọn đời và dịch vụ tư vấn ưu tiên cho Top 10% khách hàng chi tiêu cao nhất."
    })

    # 4. Giải pháp Đa dạng hóa Kênh bán hàng (nếu có rủi ro phụ thuộc)
    solutions_matrix["operational_fixes"].append({
        "title": "Mở rộng Kênh phân phối Đa kênh (Omnichannel Expansion)",
        "timeline": "2 tháng",
        "impact": "Phân tán rủi ro tập trung doanh số",
        "effort": "Trung bình",
        "details": "Đẩy mạnh hiện diện trên các nền tảng Social Commerce (TikTok Shop, Zalo Mini App) song song với kênh bán hàng truyền thống để giảm sự phụ thuộc vào duy nhất một chi nhánh/sàn TMĐT."
    })

    return solutions_matrix

def generate_llm_solutions(
    api_key: str,
    insights_text: str,
    kpis: Dict[str, Any]
) -> Optional[str]:
    """Tạo đề xuất giải pháp bằng LLM chuyên sâu."""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
Bạn là Giám đốc Điều hành Kinh doanh (COO/CMO) kiêm Cố vấn Chuyển đổi Số doanh nghiệp.
Dựa trên các Insight và hiện trạng kinh doanh sau:
{insights_text}
Chỉ số tài chính:
- Doanh thu: {kpis.get('total_revenue'):,.0f}
- Lợi nhuận: {kpis.get('total_profit'):,.0f}
- Biên lợi nhuận: {kpis.get('profit_margin_pct')}%

Hãy xây dựng BẢN KẾ HOẠCH HÀNH ĐỘNG CHIẾN LƯỢC & THỰC THI (ACTIONABLE STRATEGY PLAYBOOK) bằng Tiếng Việt gồm:
1. CHIẾN LƯỢC ĐỊNH GIÁ & TỐI ƯU HÓA BIÊN LỢI NHUẬN (Pricing & Margin Optimization): Cách giải quyết triệt để vấn đề chiết khấu và bán lỗ.
2. CHIẾN LƯỢC TĂNG TRƯỞNG DOANH SỐ ĐỘT PHÁ (Revenue Growth Strategy): 2 chiến dịch cụ thể để kéo GMV và AOV.
3. KẾ HOẠCH TRIỂN KHAI THEO 3 GIAI ĐOẠN (Roadmap):
   - Giai đoạn 1 (Tuần 1-2): Quick Wins & Cầm máu chi phí
   - Giai đoạn 2 (Tháng thứ 2): Tăng tốc chuyển đổi & Nâng cao năng suất
   - Giai đoạn 3 (Tháng thứ 3): Tự động hóa & Khóa chân khách hàng
4. PHÂN BỔ TRÁCH NHIỆM PHÒNG BAN (RACI Matrix rút gọn): Marketing, Bán hàng, Kho vận, Tài chính cần làm gì cụ thể.
"""
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Lỗi gọi Gemini API: {str(e)}"

