import os
import pandas as pd
from typing import Dict, Any, List, Optional
from modules.analysis import strip_accents

def extract_rule_based_insights(
    kpis: Dict[str, Any],
    breakdowns: Dict[str, pd.DataFrame],
    anomalies: List[Dict[str, Any]],
    trend_df: Optional[pd.DataFrame],
    custom_query: str = "",
    df: Optional[pd.DataFrame] = None,
    mapping: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Trích xuất các Insight kinh doanh then chốt dựa trên dữ liệu phân tích và câu hỏi trọng tâm của người dùng."""
    insights = []
    mapping = mapping or {}
    rev_col = mapping.get("revenue_col")
    prof_col = mapping.get("profit_col")
    chan_col = mapping.get("channel_col")
    seg_col = mapping.get("segment_col")
    date_col = mapping.get("date_col")

    # -------------------------------------------------------------
    # 0. NẾU NGƯỜI DÙNG CÓ YÊU CẦU ĐỊNH HƯỚNG RIÊNG (CUSTOM QUERY)
    # TẬP TRUNG TRẢ LỜI TRỰC DIỆN BẰNG CÁC CỘT VÀ SỐ LIỆU THỰC TẾ
    # -------------------------------------------------------------
    if custom_query and custom_query.strip() and df is not None and not df.empty:
        q_lower = custom_query.strip().lower()
        query_findings = []
        query_evidence = []
        
        # 1. Nếu hỏi về Khu vực / Vùng miền
        if any(w in q_lower for w in ['khu vuc', 'khu vực', 'vung', 'vùng', 'mien', 'miền', 'chi nhanh', 'chi nhánh']) and seg_col and seg_col in df.columns and rev_col and rev_col in df.columns:
            reg_agg = df.groupby(seg_col)[rev_col].sum().sort_values(ascending=False)
            total_r = reg_agg.sum()
            top_reg = reg_agg.index[0]
            top_val = reg_agg.iloc[0]
            bot_reg = reg_agg.index[-1]
            bot_val = reg_agg.iloc[-1]
            diff_val = top_val - bot_val
            diff_ratio = round(top_val / bot_val, 1) if bot_val > 0 else 99
            
            query_findings.append(f"Khu vực '{top_reg}' dẫn đầu với doanh thu {top_val:,.0f} ₫ (chiếm {top_val/total_r*100:.1f}%), trong khi khu vực '{bot_reg}' xếp cuối với {bot_val:,.0f} ₫ (chiếm {bot_val/total_r*100:.1f}%), chênh lệch {diff_ratio} lần.")
            query_evidence.append(f"Chi tiết doanh thu theo khu vực: " + ", ".join([f"{idx}: {val:,.0f} ₫ ({val/total_r*100:.1f}%)" for idx, val in reg_agg.items()]))

        # 2. Nếu hỏi về Kênh bán / Kênh phân phối
        if any(w in q_lower for w in ['kenh', 'kênh', 'channel', 'san', 'sàn', 'online', 'offline', 'cua hang', 'cửa hàng']) and chan_col and chan_col in df.columns and rev_col and rev_col in df.columns:
            ch_agg = df.groupby(chan_col)[rev_col].sum().sort_values(ascending=False)
            total_ch = ch_agg.sum()
            top_ch = ch_agg.index[0]
            top_ch_val = ch_agg.iloc[0]
            bot_ch = ch_agg.index[-1]
            bot_ch_val = ch_agg.iloc[-1]
            ch_diff_ratio = round(top_ch_val / bot_ch_val, 1) if bot_ch_val > 0 else 99
            
            query_findings.append(f"Kênh bán '{top_ch}' tạo ra doanh thu cao nhất ({top_ch_val:,.0f} ₫ - {top_ch_val/total_ch*100:.1f}%). Kênh '{bot_ch}' có doanh thu thấp nhất đạt {bot_ch_val:,.0f} ₫ ({bot_ch_val/total_ch*100:.1f}%), kém kênh dẫn đầu {ch_diff_ratio} lần.")
            query_evidence.append(f"Chi tiết doanh thu theo kênh: " + ", ".join([f"{idx}: {val:,.0f} ₫ ({val/total_ch*100:.1f}%)" for idx, val in ch_agg.items()]))

        # 3. Nếu hỏi về Thời gian / Tháng / Tăng trưởng
        if any(w in q_lower for w in ['thang', 'tháng', 'thoi gian', 'thời gian', 'ky', 'kỳ', 'tang truong', 'tăng trưởng', 'xu huong', 'xu hướng']) and date_col and date_col in df.columns and rev_col and rev_col in df.columns:
            d_agg = df.groupby(date_col)[rev_col].sum().sort_index()
            first_p = d_agg.index[0]
            first_v = d_agg.iloc[0]
            last_p = d_agg.index[-1]
            last_v = d_agg.iloc[-1]
            overall_g = round((last_v - first_v) / first_v * 100, 1) if first_v > 0 else 0
            peak_p = d_agg.idxmax()
            peak_v = d_agg.max()
            dip_p = d_agg.idxmin()
            dip_v = d_agg.min()
            
            query_findings.append(f"Doanh thu từ kỳ '{first_p}' ({first_v:,.0f} ₫) đến kỳ '{last_p}' ({last_v:,.0f} ₫) biến động {overall_g:+.1f}%. Kỳ cao nhất là '{peak_p}' ({peak_v:,.0f} ₫), kỳ thấp nhất là '{dip_p}' ({dip_v:,.0f} ₫).")

        # 4. Nếu hỏi về Lợi nhuận âm / Lỗ / Chi phí / Cửa hàng
        prof_c_find = mapping.get("profit_col")
        store_c_find = next((c for c in df.columns if any(w in strip_accents(c) for w in ['cua hang', 'chi nhanh', 'store', 'shop', 'branch'])), None)
        rent_c_find = next((c for c in df.columns if any(w in strip_accents(c) for w in ['thue', 'rent', 'mat bang'])), None)
        if any(w in q_lower for w in ['lo', 'am', 'lỗ', 'âm', 'loi nhuan', 'lợi nhuận', 'chi phi', 'chi phí', 'thue', 'thuê']) and prof_c_find and prof_c_find in df.columns:
            neg_df = df[df[prof_c_find] < 0]
            if not neg_df.empty:
                total_loss = abs(float(neg_df[prof_c_find].sum()))
                if store_c_find:
                    loss_by_st = neg_df.groupby(store_c_find)[prof_c_find].sum().sort_values()
                    top_loss_st = [str(x) for x in loss_by_st.index[:3]]
                    query_findings.append(f"Ghi nhận {len(neg_df)} dòng có lợi nhuận âm với tổng mức lỗ {total_loss:,.0f} ₫, tập trung lớn nhất tại các điểm: {', '.join(top_loss_st)}.")
                    query_evidence.append(f"Danh sách điểm âm lợi nhuận: " + ", ".join([f"{st}: {abs(val):,.0f} ₫" for st, val in loss_by_st.items()]))
                else:
                    query_findings.append(f"Ghi nhận {len(neg_df)} dòng giao dịch bị âm lợi nhuận với tổng mức lỗ {total_loss:,.0f} ₫.")
            if rent_c_find and store_c_find:
                rent_avg = df.groupby(store_c_find)[rent_c_find].mean().sort_values(ascending=False)
                query_findings.append(f"Chi phí thuê bình quân cao nhất tại điểm '{rent_avg.index[0]}' ({rent_avg.iloc[0]:,.0f} ₫/kỳ), tạo áp lực chi phí cố định lớn.")

        # 5. Nếu hỏi về Sản phẩm / Danh mục hàng hóa
        prod_c_find = next((c for c in df.columns if any(w in strip_accents(c) for w in ['san pham', 'mat hang', 'product', 'item', 'danh muc', 'category'])), None)
        if any(w in q_lower for w in ['san pham', 'sản phẩm', 'mat hang', 'mặt hàng', 'danh muc', 'danh mục', 'hang hoa', 'hàng hóa']) and prod_c_find and rev_col and rev_col in df.columns:
            prod_agg = df.groupby(prod_c_find)[rev_col].sum().sort_values(ascending=False)
            top_p = prod_agg.index[0]
            top_pv = prod_agg.iloc[0]
            bot_p = prod_agg.index[-1]
            bot_pv = prod_agg.iloc[-1]
            total_pv = prod_agg.sum()
            query_findings.append(f"Mặt hàng '{top_p}' đóng góp doanh số lớn nhất ({top_pv:,.0f} ₫ - {top_pv/total_pv*100:.1f}%), trong khi '{bot_p}' có doanh số thấp nhất ({bot_pv:,.0f} ₫).")
            query_evidence.append(f"Top 3 sản phẩm chủ lực: " + ", ".join([f"{p}: {v:,.0f} ₫" for p, v in prod_agg.head(3).items()]))

        # 6. Nếu hỏi về Sản xuất: Ca kíp / Mã máy / Tỷ lệ lỗi / Năng suất
        shift_col = next((c for c in df.columns if any(w in strip_accents(c) for w in ['ca', 'ca kip', 'shift'])), None)
        machine_col = next((c for c in df.columns if any(w in strip_accents(c) for w in ['may', 'ma may', 'machine'])), None)
        defect_col = next((c for c in df.columns if any(w in strip_accents(c) for w in ['ty le loi', 'loi', 'defect', 'phe pham'])), None)
        output_col = next((c for c in df.columns if any(w in strip_accents(c) for w in ['san luong', 'so luong', 'output', 'qty'])), None)

        if defect_col and (shift_col or machine_col):
            dim_prod = machine_col or shift_col
            try:
                num_defect = pd.to_numeric(df[defect_col].astype(str).str.replace(r'[%₫$,]', '', regex=True).str.strip(), errors='coerce')
                temp_df = df.copy()
                temp_df['_num_defect'] = num_defect
                def_agg = temp_df.groupby(dim_prod)['_num_defect'].mean().dropna().sort_values(ascending=False)
                if not def_agg.empty:
                    worst_d = def_agg.index[0]
                    worst_val = def_agg.iloc[0]
                    best_d = def_agg.index[-1]
                    best_val = def_agg.iloc[-1]
                    pct_s = f"{worst_val*100:.2f}%" if worst_val <= 1 else f"{worst_val:.2f}%"
                    best_pct_s = f"{best_val*100:.2f}%" if best_val <= 1 else f"{best_val:.2f}%"
                    query_findings.append(f"Tỷ lệ lỗi cao nhất ghi nhận tại '{worst_d}' ({pct_s}), trong khi '{best_d}' vận hành chuẩn xác nhất với tỷ lệ lỗi chỉ {best_pct_s}.")
                    query_evidence.append(f"Chi tiết tỷ lệ lỗi theo {dim_prod}: " + ", ".join([f"{k}: {v*100:.2f}%" if v <= 1 else f"{k}: {v:.2f}%" for k, v in def_agg.items()]))
            except Exception:
                pass
        elif output_col and (shift_col or machine_col):
            dim_prod = machine_col or shift_col
            try:
                num_out = pd.to_numeric(df[output_col].astype(str).str.replace(r'[%₫$,]', '', regex=True).str.strip(), errors='coerce')
                temp_df = df.copy()
                temp_df['_num_out'] = num_out
                out_agg = temp_df.groupby(dim_prod)['_num_out'].sum().dropna().sort_values(ascending=False)
                if not out_agg.empty:
                    query_findings.append(f"Sản lượng hoàn thành cao nhất đạt được tại '{out_agg.index[0]}' ({out_agg.iloc[0]:,.0f} sản phẩm), vượt trội so với '{out_agg.index[-1]}' ({out_agg.iloc[-1]:,.0f} sản phẩm).")
            except Exception:
                pass

        if query_findings:
            insights.append({
                "title": f"Phân Tích Trọng Tâm Theo Yêu Cầu: \"{custom_query.strip()}\"",
                "tag": "Định Hướng Phân Tích Của Bạn",
                "importance": "CRITICAL",
                "finding": " ".join(query_findings),
                "root_cause": "Dữ liệu cho thấy sự phân hóa rõ ràng giữa các nhóm phân loại trong tập dữ liệu thực tế.",
                "evidence": " | ".join(query_evidence) if query_evidence else "Tính toán trực tiếp từ dữ liệu thực tế."
            })

    # 1. Insight về Hiệu suất Tài chính & Biên lợi nhuận (Chỉ tính khi có cột lợi nhuận thực tế)
    profit_margin = kpis.get("profit_margin_pct")
    rev = kpis.get("total_revenue", 0)
    profit = kpis.get("total_profit", 0)
    
    if prof_col and prof_col in (df.columns if df is not None else []):
        if profit_margin < 15:
            insights.append({
                "title": f"Biên lợi nhuận gộp đang ở mức thấp ({profit_margin:.1f}%)",
                "tag": "Tài chính & Lợi nhuận",
                "importance": "CRITICAL",
                "finding": f"Biên lợi nhuận toàn hệ thống ghi nhận {profit_margin:.1f}%, cần kiểm soát chặt chẽ chi phí để cải thiện biên lãi.",
                "root_cause": "Do giá vốn hàng bán và chi phí phân phối chiếm tỷ trọng lớn trong tổng doanh thu.",
                "evidence": f"Tổng doanh thu: {rev:,.0f} ₫, lợi nhuận thực giữ lại: {profit:,.0f} ₫."
            })
        else:
            insights.append({
                "title": f"Biên lợi nhuận gộp duy trì ổn định ({profit_margin:.1f}%)",
                "tag": "Tài chính & Lợi nhuận",
                "importance": "POSITIVE",
                "finding": f"Hệ thống đạt biên lợi nhuận lành mạnh {profit_margin:.1f}%.",
                "root_cause": "Cơ cấu sản phẩm và chính sách giá đang kiểm soát chi phí hiệu quả.",
                "evidence": f"Lợi nhuận đạt {profit:,.0f} ₫ trên tổng doanh thu {rev:,.0f} ₫."
            })
    elif rev > 0 and (not custom_query or not any("Phân Tích" in ins.get("title", "") for ins in insights)):
        insights.append({
            "title": f"Tổng quy mô doanh thu toàn kỳ đạt {rev:,.0f} ₫",
            "tag": "Quy Mô Doanh Số",
            "importance": "POSITIVE",
            "finding": f"Toàn bộ hệ thống ghi nhận tổng doanh thu đạt {rev:,.0f} ₫ qua các kỳ theo dõi.",
            "root_cause": "Tổng hợp từ toàn bộ các dòng giao dịch kinh doanh trong cơ sở dữ liệu đã làm sạch.",
            "evidence": f"Tổng số bản ghi dữ liệu phân tích: {kpis.get('total_records', 0)} dòng."
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
            "finding": loss_anomaly.get("description"),
            "root_cause": "Hệ thống thiếu cơ chế 'Giá sàn tự động' (Price Floor Guardrail) khi nhân viên sale áp dụng khuyến mãi cộng dồn (Stacking discounts).",
            "evidence": f"{loss_anomaly.get('impact')} - Chiếm {loss_anomaly.get('metric')}."
        })
    elif disc_anomaly:
        insights.append({
            "title": "Chính sách khuyến mãi đang làm suy giảm giá trị thương hiệu",
            "tag": "Chính sách Giá",
            "importance": "WARNING",
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
                    "finding": f"Doanh số nửa sau chu kỳ theo dõi sụt giảm {abs(growth):.1f}% so với nửa đầu.",
                    "root_cause": "Lượng khách hàng mới suy giảm hoặc tần suất mua lại của tệp khách hàng cũ thấp (Retention drop).",
                    "evidence": f"Doanh thu trung bình kỳ giảm từ {avg_h1:,.0f} xuống {avg_h2:,.0f}."
                })
            elif growth > 5:
                insights.append({
                    "title": f"Quỹ đạo tăng trưởng tích cực (+{growth:.1f}%)",
                    "tag": "Xu hướng Tăng trưởng",
                    "importance": "POSITIVE",
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
        if api_key.startswith("AQ."):
            client = genai.Client(vertexai=True, api_key=api_key)
        else:
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

