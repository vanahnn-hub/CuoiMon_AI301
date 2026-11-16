import os
import pandas as pd
from typing import Dict, Any, List, Optional

def extract_rule_based_insights(
    kpis: Dict[str, Any],
    breakdowns: Dict[str, pd.DataFrame],
    anomalies: List[Dict[str, Any]],
    trend_df: Optional[pd.DataFrame]
) -> List[Dict[str, Any]]:
    """Trích xuất các Insight kinh doanh then chốt dựa trên dữ liệu phân tích."""
    insights = []
    
    # 1. Insight về Hiệu suất Tài chính & Biên lợi nhuận
    profit_margin = kpis.get("profit_margin_pct", 0)
    rev = kpis.get("total_revenue", 0)
    profit = kpis.get("total_profit", 0)
    
    if rev > 0:
        if profit_margin < 15:
            insights.append({
                "title": "Biên lợi nhuận gộp đang ở mức báo động (< 15%)",
                "tag": "Tài chính & Giá vốn",
                "importance": "CRITICAL",
                "icon": "⚠️",
                "finding": f"Biên lợi nhuận toàn hệ thống chỉ đạt {profit_margin}%, thấp hơn nhiều so với chuẩn ngành bán lẻ (25% - 35%).",
                "root_cause": "Nguyên nhân cốt lõi do chính sách giảm giá/chiết khấu không kiểm soát hoặc giá vốn hàng bán (COGS) tăng cao mà chưa thể chuyển giao chi phí vào giá bán.",
                "evidence": f"Tổng doanh thu: {rev:,.0f} nhưng lợi nhuận thực chỉ giữ lại {profit:,.0f}."
            })
        else:
            insights.append({
                "title": f"Biên lợi nhuận ổn định ({profit_margin}%)",
                "tag": "Tài chính & Giá vốn",
                "importance": "POSITIVE",
                "icon": "✅",
                "finding": f"Hệ thống duy trì biên lợi nhuận lành mạnh ở mức {profit_margin}%.",
                "root_cause": "Danh mục sản phẩm chủ lực có giá trị thặng dư tốt và chi phí kiểm soát chặt chẽ.",
                "evidence": f"Lợi nhuận đạt {profit:,.0f} trên tổng doanh thu {rev:,.0f}."
            })

    # 2. Insight về Phân bổ Doanh thu (Pareto 80/20)
    for dim_name in ["Category", "Segment", "Channel"]:
        if dim_name in breakdowns and not breakdowns[dim_name].empty:
            df_dim = breakdowns[dim_name]
            top_item = df_dim.iloc[0]
            top_share = top_item.get("Revenue_Share_Pct", 0)
            dim_val = top_item.get(dim_name, "N/A")
            
            if top_share >= 40:
                insights.append({
                    "title": f"Mức độ phụ thuộc rủi ro cao vào {dim_name} '{dim_val}' ({top_share}%)",
                    "tag": f"Phân khúc & Tập trung ({dim_name})",
                    "importance": "WARNING",
                    "icon": "📊",
                    "finding": f"Nhóm '{dim_val}' chiếm tới {top_share}% tổng doanh thu toàn doanh nghiệp.",
                    "root_cause": "Chiến lược kinh doanh đang bị lệch trọng tâm (rủi ro tập trung). Khi phân khúc/kênh này gặp biến động hoặc đối thủ cạnh tranh gia nhập, tổng doanh số sẽ bị tổn thương nặng nề.",
                    "evidence": f"Doanh số từ '{dim_val}' đạt {top_item.get('Revenue', 0):,.0f} trên tổng số {len(df_dim)} nhóm."
                })
            break

    # 3. Insight về Các đơn hàng lỗ và lãng phí chiết khấu
    loss_anomaly = next((a for a in anomalies if "LỖ" in a.get("type", "")), None)
    disc_anomaly = next((a for a in anomalies if "CHIẾT KHẤU" in a.get("type", "")), None)
    
    if loss_anomaly:
        insights.append({
            "title": f"Thất thoát trực tiếp từ {loss_anomaly.get('count')} đơn hàng bán dưới giá vốn",
            "tag": "Vận hành & Định giá",
            "importance": "CRITICAL",
            "icon": "💸",
            "finding": loss_anomaly.get("description"),
            "root_cause": "Hệ thống thiếu cơ chế 'Giá sàn tự động' (Price Floor Guardrail) khi nhân viên sale áp dụng khuyến mãi cộng dồn (Stacking discounts).",
            "evidence": f"{loss_anomaly.get('impact')} - Chiếm {loss_anomaly.get('metric')}."
        })
    elif disc_anomaly:
        insights.append({
            "title": "Chính sách khuyến mãi đang làm suy giảm giá trị thương hiệu",
            "tag": "Chính sách Giá",
            "importance": "WARNING",
            "icon": "🏷️",
            "finding": disc_anomaly.get("description"),
            "root_cause": "Doanh nghiệp đang lạm dụng giảm giá giá sốc để kéo GMV thay vì xây dựng giá trị sản phẩm và lòng trung thành của khách hàng.",
            "evidence": disc_anomaly.get("impact")
        })

    # 4. Insight về Xu hướng tăng trưởng & biến động
    if trend_df is not None and len(trend_df) >= 7:
        first_half = trend_df.iloc[:len(trend_df)//2]
        second_half = trend_df.iloc[len(trend_df)//2:]
        rev_col = [c for c in trend_df.columns if 'revenue' in c.lower() or 'doanh_thu' in c.lower()][0]
        
        avg_h1 = first_half[rev_col].mean()
        avg_h2 = second_half[rev_col].mean()
        
        if avg_h1 > 0:
            growth = ((avg_h2 - avg_h1) / avg_h1) * 100
            if growth < -5:
                insights.append({
                    "title": f"Tốc độ tăng trưởng doanh số có xu hướng suy giảm ({growth:.1f}%)",
                    "tag": "Xu hướng Tăng trưởng",
                    "importance": "WARNING",
                    "icon": "📉",
                    "finding": f"Doanh số nửa sau chu kỳ theo dõi sụt giảm {abs(growth):.1f}% so với nửa đầu.",
                    "root_cause": "Lượng khách hàng mới suy giảm hoặc tần suất mua lại của tệp khách hàng cũ thấp (Retention drop).",
                    "evidence": f"Doanh thu trung bình kỳ giảm từ {avg_h1:,.0f} xuống {avg_h2:,.0f}."
                })
            elif growth > 5:
                insights.append({
                    "title": f"Quỹ đạo tăng trưởng tích cực (+{growth:.1f}%)",
                    "tag": "Xu hướng Tăng trưởng",
                    "importance": "POSITIVE",
                    "icon": "📈",
                    "finding": f"Doanh số nửa sau chu kỳ tăng trưởng bứt phá +{growth:.1f}%.",
                    "root_cause": "Các chiến dịch bán hàng gần đây đạt hiệu quả lan tỏa và tỷ lệ chuyển đổi cao.",
                    "evidence": f"Doanh thu trung bình kỳ tăng từ {avg_h1:,.0f} lên {avg_h2:,.0f}."
                })

    # 5. Insight về Tỷ lệ hoàn hủy
    ret_anomaly = next((a for a in anomalies if "HOÀN TRẢ" in a.get("type", "")), None)
    if ret_anomaly:
        insights.append({
            "title": f"Tỷ lệ hoàn hủy đơn cao gây chi phí vận hành ẩn",
            "tag": "Dịch vụ Khách hàng & Logistics",
            "importance": "CRITICAL" if ret_anomaly.get("severity") == "HIGH" else "WARNING",
            "icon": "📦",
            "finding": ret_anomaly.get("description"),
            "root_cause": "Sự chênh lệch giữa kỳ vọng của khách hàng với sản phẩm thực tế, đóng gói thiếu chỉn chu hoặc thời gian giao hàng kéo dài.",
            "evidence": ret_anomaly.get("impact")
        })

    return insights

def generate_llm_insights(
    api_key: str,
    kpis: Dict[str, Any],
    breakdowns_summary: str,
    anomalies: List[Dict[str, Any]],
    rule_insights: List[Dict[str, Any]]
) -> Optional[str]:
    """Sử dụng Gemini API để mở rộng insight chuyên sâu từ góc nhìn Chuyên gia Tư vấn Chiến lược Cấp cao."""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
Bạn là Chuyên gia Tư vấn Chiến lược Cấp cao & Trí tuệ Kinh doanh (Chief Strategy Officer & Business AI Agent).
Nhiệm vụ của bạn là phân tích dữ liệu kinh doanh sau đây và rút ra các INSIGHT chiến lược sắc bén:

[TỔNG QUAN CHỈ SỐ KINH DOANH]
- Tổng số bản ghi/đơn hàng: {kpis.get('total_records')}
- Tổng doanh thu: {kpis.get('total_revenue'):,.0f}
- Tổng lợi nhuận: {kpis.get('total_profit'):,.0f}
- Tỷ suất lợi nhuận (Profit Margin): {kpis.get('profit_margin_pct')}%
- Giá trị trung bình đơn hàng (AOV): {kpis.get('aov'):,.0f}

[PHÂN TÍCH ĐÓNG GÓP & CƠ CẤU]
{breakdowns_summary}

[CÁC ĐIỂM BẤT THƯỜNG & NGUY CƠ PHÁT HIỆN ĐƯỢC]
{str(anomalies)}

[CÁC INSIGHT BƯỚC ĐẦU TỪ HỆ THỐNG]
{str(rule_insights)}

YÊU CẦU ĐẦU RA:
Hãy viết báo cáo RÚT RA INSIGHT CHUYÊN SÂU bằng Tiếng Việt gồm:
1. ĐÁNH GIÁ SỨC KHỎE DOANH NGHIỆP TỔNG THỂ (Executive Summary): 2-3 câu ngắn gọn, trực diện.
2. 3 ĐIỂM NGHẼN CỐT LÕI (Core Bottlenecks & Root Causes): Phân tích nguyên nhân gốc rễ (sử dụng tư duy 5 Whys / MECE).
3. 2 CƠ HỘI ĐỘT PHÁ DOANH SỐ (Growth Levers): Những mỏ vàng chưa được khai thác triệt để từ dữ liệu.

Trình bày định dạng Markdown chuyên nghiệp, có bullet points rõ ràng, lập luận chặt chẽ.
"""
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Lỗi gọi Gemini API: {str(e)}"

