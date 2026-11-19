import pandas as pd
from typing import Dict, Any, List, Optional

from modules.analysis import strip_accents

def generate_business_solutions(
    insights: List[Dict[str, Any]],
    kpis: Dict[str, Any],
    anomalies: List[Dict[str, Any]],
    custom_query: str = "",
    df: Optional[pd.DataFrame] = None,
    mapping: Optional[Dict[str, Any]] = None,
    business_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Tạo đề xuất giải pháp kinh doanh toàn diện dựa trên dữ liệu thực tế, các bất thường phát hiện được và yêu cầu định hướng của người dùng."""
    mapping = mapping or {}
    business_profile = business_profile or {}
    rev_col = mapping.get("revenue_col")
    chan_col = mapping.get("channel_col")
    seg_col = mapping.get("segment_col")
    date_col = mapping.get("date_col")
    prof_col = mapping.get("profit_col")
    disc_col = mapping.get("discount_col")
    ret_col = mapping.get("return_col")

    industry = (business_profile.get("industry") or "").lower()
    biz_goal = (business_profile.get("primary_goal") or "").lower()
    biz_desc = (business_profile.get("description") or "").lower()
    
    cols = df.columns.tolist() if df is not None else []
    cols_norm = [strip_accents(str(c)).lower() for c in cols]
    
    # Nhận diện ngành Sản xuất / Dây chuyền / Lỗi sản phẩm
    is_manufacturing = (
        any(w in industry for w in ['san xuat', 'sản xuất', 'nha may', 'nhà máy', 'gia cong', 'chế tạo', 'co khi', 'det may', 'dien tu']) or
        any(w in biz_desc for w in ['san xuat', 'sản xuất', 'ty le loi', 'tỷ lệ lỗi', 'day chuyen', 'dây chuyền', 'ca lam', 'ca kíp']) or
        any(k in cols_norm for k in ['ca', 'ca kip', 'day chuyen', 'ma lo', 'so loi', 'ty le loi', 'san luong dat', 'thoi gian chay'])
    )

    solutions_list = []

    # -----------------------------------------------------------------------------------------
    # KỊCH BẢN A: NGÀNH SẢN XUẤT / NHÀ MÁY / TỶ LỆ LỖI (KHÔNG ÁP GIẢI PHÁP BÁN LẺ HAY VOUCHER)
    # -----------------------------------------------------------------------------------------
    if is_manufacturing:
        # 1. Bóc tách dữ liệu thực tế theo Ca hoặc Dây chuyền
        shift_col = next((c for c in cols if any(w in strip_accents(c).lower() for w in ['ca', 'ca kip', 'shift'])), None)
        line_col = next((c for c in cols if any(w in strip_accents(c).lower() for w in ['day chuyen', 'line', 'chuyen', 'may'])), None)
        defect_col = next((c for c in cols if any(w in strip_accents(c).lower() for w in ['ty le loi', 'so loi', 'loi', 'defect', 'phe pham'])), None)
        out_col = next((c for c in cols if any(w in strip_accents(c).lower() for w in ['san luong', 'san luong dat', 'output', 'qty'])), None)

        # Giải pháp 1 (Ưu tiên P1): Theo yêu cầu người dùng (Ví dụ Phân tích theo ca)
        shift_evidence = ""
        worst_shift = "Ca có tỷ lệ lỗi cao"
        if df is not None and shift_col and defect_col:
            try:
                num_def = pd.to_numeric(df[defect_col].astype(str).str.replace(r'[%₫$,]', '', regex=True).str.strip(), errors='coerce')
                t_df = df.copy()
                t_df['_def'] = num_def
                agg = t_df.groupby(shift_col)['_def'].mean().dropna().sort_values(ascending=False)
                if not agg.empty:
                    worst_shift = str(agg.index[0])
                    worst_val = agg.iloc[0]
                    best_shift = str(agg.index[-1])
                    val_str = f"{worst_val*100:.2f}%" if worst_val <= 1 else f"{worst_val:.2f}%"
                    shift_evidence = f"Dữ liệu cho thấy '{worst_shift}' ghi nhận tỷ lệ lỗi trung bình cao nhất ({val_str}), trong khi '{best_shift}' vận hành ổn định nhất."
            except Exception:
                pass

        q_user = custom_query.strip() if custom_query else "Phân tích và kiểm soát chất lượng theo ca"
        solutions_list.append({
            "priority": "Tuần 1–2 • Ưu tiên P1",
            "title": f"Chuẩn Hóa Quy Trình Thao Tác (SOP) & Giám Sát Chất Lượng Theo {shift_col or 'Ca Làm Việc'}",
            "target": f"Giải quyết trực tiếp yêu cầu: '{q_user}'",
            "details": f"{shift_evidence} Triển khai ngay bảng kiểm bàn giao ca (Shift Handover Checklist) tại {worst_shift}. Bố trí kỹ thuật viên giám sát chặt chẽ các công đoạn đầu ca và cuối ca để hạn chế lỗi do mệt mỏi hoặc thiếu đồng bộ.",
            "raci": "Quản Đốc Phân Xưởng & Trưởng Ca Sản Xuất",
            "kpi_commitment": "Kéo giảm tỷ lệ lỗi ca làm việc xuống < 1.0%, nâng tỷ lệ sản phẩm đạt chuẩn > 98.5%",
            "timeline": "2 tuần",
            "impact": "Giảm thiểu phế phẩm xuất xưởng và bảo toàn năng suất ca"
        })

        # Giải pháp 2: Bảo trì thiết bị và cân chỉnh dây chuyền
        line_name = line_col or "Dây Chuyền Sản Xuất"
        solutions_list.append({
            "priority": "Tuần 2–3 • Kỹ thuật & Máy móc",
            "title": f"Bảo Trì Phòng Ngừa (Preventive Maintenance) & Hiệu Chuẩn {line_name}",
            "target": "Giảm thiểu thời gian dừng máy (Downtime) và ổn định thông số kỹ thuật",
            "details": f"Rà soát định kỳ toàn bộ cảm biến, khuôn dao dập và hệ thống truyền động trên các {line_name}. Thiết lập lịch bảo dưỡng phòng ngừa trước giờ vào ca thay vì bảo trì khi đã phát sinh sự cố.",
            "raci": "Trưởng Phòng Cơ Điện & Đội Ngũ Bảo Trì Thiết Bị",
            "kpi_commitment": "Khống chế thời gian dừng chuyền sự cố (Unplanned Downtime) < 15 phút/ca",
            "timeline": "3 tuần",
            "impact": "Tối ưu hóa thời gian chạy máy hữu ích (OEE > 88%)"
        })

        # Giải pháp 3: Chốt chặn kiểm soát lỗi tại nguồn (Poka-Yoke & SPC)
        solutions_list.append({
            "priority": "Tuần 3–4 • Quản lý chất lượng QA/QC",
            "title": "Thiết Lập Chốt Chặn Kiểm Soát Lỗi Tại Nguồn (Poka-Yoke & SPC)",
            "target": "Ngăn chặn 100% sản phẩm lỗi lọt sang công đoạn kế tiếp và kho thành phẩm",
            "details": "Lắp đặt cảm biến tự động cảnh báo phôi lỗi tại các vị trí xung yếu; áp dụng nguyên tắc kiểm tra chéo giữa các tổ đội; đào tạo nâng cao tay nghề thao tác chuẩn cho công nhân định kỳ.",
            "raci": "Trưởng Phòng Quản Lý Chất Lượng (QA/QC Lead)",
            "kpi_commitment": "Tỷ lệ sản phẩm đạt chuẩn xuất xưởng đạt tối thiểu 99.5%",
            "timeline": "1 tháng",
            "impact": "Triệt tiêu rủi ro thu hồi lô hàng và bảo vệ uy tín nhà máy"
        })

        # Giải pháp 4: Tối ưu nhịp độ chu kỳ & kế hoạch điều độ
        solutions_list.append({
            "priority": "Dài hạn • Điều độ sản xuất",
            "title": "Cân Bằng Chuyền (Line Balancing) & Tối Ưu Hóa Nhịp Độ Sản Xuất (Takt Time)",
            "target": "Loại bỏ nút thắt cổ chai và đảm bảo tiến độ giao hàng",
            "details": "Phân tích thời gian chạy máy thực tế giữa các mã lô để tái phân bổ nhân lực; thiết lập hệ thống cảnh báo tiến độ theo thời gian thực trên màn hình phân xưởng.",
            "raci": "Giám Đốc Sản Xuất & Bộ Phận Kế Hoạch Điều Độ",
            "kpi_commitment": "Hoàn thành 100% kế hoạch sản lượng theo tiến độ cam kết",
            "timeline": "1-2 tháng",
            "impact": "Tăng năng suất tổng thể toàn xưởng thêm +12-15%"
        })

    # -----------------------------------------------------------------------------------------
    # KỊCH BẢN B: CÁC NGÀNH KHÁC (BÁN LẺ, THƯƠNG MẠI, DỊCH VỤ, V.V.)
    # -----------------------------------------------------------------------------------------
    else:
        if custom_query and custom_query.strip():
            q_clean = custom_query.strip()
            details_parts = []
            if chan_col and chan_col in df.columns and rev_col and rev_col in df.columns:
                ch_agg = df.groupby(chan_col)[rev_col].sum().sort_values(ascending=False)
                top_ch, bot_ch = ch_agg.index[0], ch_agg.index[-1]
                details_parts.append(f"Đóng gói quy trình tư vấn và kinh nghiệm từ kênh dẫn đầu '{top_ch}' để chuyển giao sang kênh '{bot_ch}', áp dụng chính sách chăm sóc riêng để thu hẹp khoảng cách doanh số.")
            if seg_col and seg_col in df.columns and rev_col and rev_col in df.columns:
                reg_agg = df.groupby(seg_col)[rev_col].sum().sort_values(ascending=False)
                top_reg, bot_reg = reg_agg.index[0], reg_agg.index[-1]
                details_parts.append(f"Tăng cường nguồn lực marketing địa phương tại khu vực '{bot_reg}' để nâng cao độ nhận diện và mở rộng thị phần tương đương khu vực '{top_reg}'.")

            solutions_list.append({
                "priority": "Tuần 1–2 • Ưu tiên P1",
                "title": f"Chiến Lược Hành Động Trọng Tâm: {q_clean}",
                "target": f"Giải quyết trực tiếp định hướng: '{q_clean}'",
                "details": " ".join(details_parts) if details_parts else f"Triển khai kế hoạch hành động cụ thể để xử lý yêu cầu '{q_clean}', rà soát các chỉ số thực tế trong bảng dữ liệu để tối ưu hiệu quả.",
                "raci": "Ban Giám Đốc Điều Hành (COO) & Trưởng Bộ Phận Kinh Doanh",
                "kpi_commitment": "Tối ưu hóa phân bổ nguồn lực theo đúng định hướng",
                "timeline": "2 tuần",
                "impact": "Tăng trưởng đồng đều giữa các kênh và khu vực"
            })

        # -------------------------------------------------------------
        # GIẢI PHÁP THEO CÁC BẤT THƯỜNG THỰC TẾ TRONG DỮ LIỆU BÁN LẺ/DỊCH VỤ
        # -------------------------------------------------------------
        # Bất thường Kênh bán
        chan_anomaly = next((a for a in anomalies if "KÊNH" in str(a.get("type", "")).upper()), None)
        if chan_anomaly:
            solutions_list.append({
                "priority": "Tuần 2–3 • Kích cầu kênh bán",
                "title": f"Tái Cấu Trúc & Kích Hoạt Kênh Bán Yếu Thế ({chan_anomaly.get('type')})",
                "target": f"Cải thiện doanh thu kênh yếu: {chan_anomaly.get('metric')}",
                "details": f"Đánh giá lại danh mục hàng hóa và chính sách bán hàng trên kênh này. Thiết kế chiến dịch kích cầu trực tuyến kết hợp ưu đãi độc quyền để kéo lưu lượng truy cập và tỷ lệ chốt đơn.",
                "raci": "Trưởng Bộ Phận Bán Hàng (Head of Sales) & Marketing",
                "kpi_commitment": "Tăng trưởng doanh thu kênh yếu tối thiểu +20%",
                "timeline": "3 tuần",
                "impact": chan_anomaly.get("impact")
            })

        # Bất thường Khu vực / Vùng miền
        reg_anomaly = next((a for a in anomalies if "VÙNG MIỀN" in str(a.get("type", "")).upper() or "KHU VỰC" in str(a.get("type", "")).upper()), None)
        if reg_anomaly:
            solutions_list.append({
                "priority": "Tuần 3–4 • Phát triển thị trường",
                "title": f"Chiến Lược Mở Rộng Thị Phần & Cân Bằng Khu Vực ({reg_anomaly.get('type')})",
                "target": f"Khắc phục điểm nghẽn vùng miền: {reg_anomaly.get('metric')}",
                "details": "Tận dụng các thế mạnh từ khu vực dẫn đầu để hỗ trợ khu vực tụt hậu; hợp tác với đối tác phân phối tại chỗ và tối ưu chính sách vận chuyển theo từng địa bàn.",
                "raci": "Giám Đốc Thương Mại (CCO) & Đội Ngũ Kinh Doanh Địa Bàn",
                "kpi_commitment": "Thu hẹp khoảng cách doanh thu giữa các khu vực",
                "timeline": "1 tháng",
                "impact": reg_anomaly.get("impact")
            })

        # Bất thường Chu kỳ / Sụt giảm theo tháng
        period_anomaly = next((a for a in anomalies if "CHU KỲ" in str(a.get("type", "")).upper() or "ĐIỂM TRŨNG" in str(a.get("type", "")).upper()), None)
        if period_anomaly:
            solutions_list.append({
                "priority": "Định kỳ • Kích cầu theo mùa",
                "title": f"Kế Hoạch San Phẳng Điểm Trũng Doanh Số ({period_anomaly.get('type')})",
                "target": f"Hạn chế sụt giảm chu kỳ: {period_anomaly.get('metric')}",
                "details": "Lên lịch trước các chiến dịch flash sale, chương trình tri ân khách hàng cũ vào các tháng thấp điểm trong năm để giữ vững nhịp độ dòng tiền kinh doanh.",
                "raci": "Phòng Marketing & Quản Lý Sản Phẩm (PM)",
                "kpi_commitment": "San phẳng độ lệch doanh số giữa các kỳ",
                "timeline": "Theo chu kỳ tháng",
                "impact": period_anomaly.get("impact")
            })

        # Bán lỗ / Lợi nhuận âm
        loss_anomaly = next((a for a in anomalies if "LỖ" in str(a.get("type", "")).upper() and "LỖI" not in str(a.get("type", "")).upper()), None)
        if loss_anomaly and prof_col:
            rent_col_f = next((c for c in (df.columns if df is not None else []) if any(w in str(c).lower() for w in ['thue', 'thuê', 'mat_bang', 'mặt bằng'])), None)
            sal_col_f = next((c for c in (df.columns if df is not None else []) if any(w in str(c).lower() for w in ['nhan_su', 'nhân sự', 'luong', 'lương'])), None)
            
            if rent_col_f or sal_col_f:
                solutions_list.append({
                    "priority": "Khẩn cấp P1 • Bảo toàn dòng tiền",
                    "title": "Tái Cấu Trúc Chi Phí Mặt Bằng & Nhân Sự Tại Các Điểm Bán Âm Lợi Nhuận",
                    "target": f"Khắc phục {loss_anomaly.get('count')} giao dịch có lợi nhuận âm",
                    "details": "Đàm phán lại biểu phí thuê mặt bằng, xem xét điều chỉnh diện tích kinh doanh tại các điểm bán đang bị lỗ; đồng thời rà soát lại định biên nhân sự theo doanh thu thực tế để hạ thấp điểm hòa vốn.",
                    "raci": "Ban Giám Đốc Điều Hành (COO) & Trưởng Phòng Vận Hành Chuỗi",
                    "kpi_commitment": "Đưa 100% điểm bán về ngưỡng hòa vốn và có lãi",
                    "timeline": "2 tuần",
                    "impact": loss_anomaly.get("impact")
                })
            else:
                solutions_list.append({
                    "priority": "Khẩn cấp P1 • Bảo toàn biên lãi",
                    "title": "Thiết Lập Ngưỡng Giá Sàn & Kiểm Soát Giá Vốn",
                    "target": f"Xử lý {loss_anomaly.get('count')} giao dịch âm lợi nhuận",
                    "details": "Rà soát lại cơ cấu giá vốn hàng bán và thiết lập ngưỡng giá bán tối thiểu để đảm bảo mỗi giao dịch đều có biên lợi nhuận ròng dương.",
                    "raci": "Ban Giám Đốc Tài Chính (CFO) & Bộ Phận Kinh Doanh",
                    "kpi_commitment": "Ngăn chặn hoàn toàn các giao dịch âm lợi nhuận",
                    "timeline": "1 tuần",
                    "impact": loss_anomaly.get("impact")
                })

        # Chiết khấu sâu (CHỈ KHI CÓ CỘT CHIẾT KHẤU THỰC TẾ)
        disc_anomaly = next((a for a in anomalies if "CHIẾT KHẤU" in str(a.get("type", "")).upper()), None)
        if disc_anomaly and disc_col:
            solutions_list.append({
                "priority": "Ưu tiên P2 • Tối ưu chính sách giá",
                "title": "Chuyển Đổi Hình Thức Giảm Giá Trực Tiếp Sang Voucher Mua Lại",
                "target": f"Kiểm soát chiết khấu sâu: {disc_anomaly.get('metric')}",
                "details": "Thay vì giảm giá trực tiếp vào giá bán, tặng voucher hoàn tiền cho đơn hàng tiếp theo nhằm giữ vững giá niêm yết và thúc đẩy tần suất quay lại của khách hàng.",
                "raci": "Bộ Phận Marketing & Chính Sách Giá",
                "kpi_commitment": "Bảo toàn biên lợi nhuận niêm yết",
                "timeline": "2 tuần",
                "impact": disc_anomaly.get("impact")
            })

        # Hoàn trả (CHỈ KHI CÓ CỘT HOÀN TRẢ THỰC TẾ)
        ret_anomaly = next((a for a in anomalies if "HOÀN" in str(a.get("type", "")).upper()), None)
        if ret_anomaly and ret_col:
            solutions_list.append({
                "priority": "Tối ưu vận hành • Logistics",
                "title": "Quy Trình Xác Thực Đơn Hàng & Giảm Thiểu Hoàn Hủy",
                "target": f"Kéo tỷ lệ hoàn hủy {ret_anomaly.get('metric')} về dưới ngưỡng an toàn",
                "details": "Tự động gửi thông báo xác nhận đơn hàng qua SMS/Zalo trước khi đóng gói; nâng cấp quy chuẩn bảo quản và đóng gói để hạn chế hư hỏng trong quá trình vận chuyển.",
                "raci": "Đội Vận Hành Kho & Dịch Vụ Khách Hàng (CSKH)",
                "kpi_commitment": "Giảm tỷ lệ hoàn hàng xuống dưới 5%",
                "timeline": "2 tuần",
                "impact": ret_anomaly.get("impact")
            })

    # -------------------------------------------------------------
    # 3. NẾU DANH SÁCH GIẢI PHÁP CHƯA ĐỦ (DỮ LIỆU SẠCH HOẶC ĐƠN GIẢN)
    # BỔ SUNG CÁC GIẢI PHÁP CHUẨN DỰA TRÊN QUY MÔ DOANH SỐ
    # -------------------------------------------------------------
    if len(solutions_list) < 3:
        solutions_list.append({
            "priority": "Dài hạn • Mở rộng quy mô",
            "title": "Chuẩn Hóa Quy Trình Bán Hàng & Đa Dạng Hóa Kênh Tiếp Cận",
            "target": "Nâng cao độ phủ và tối ưu chi phí tiếp cận khách hàng",
            "details": "Đánh giá hiệu quả từng điểm tiếp xúc của khách hàng, tích hợp các kênh truyền thông số và tối ưu hóa trải nghiệm mua sắm từ đầu đến cuối.",
            "raci": "Giám Đốc Vận Hành (COO) & Đội Ngũ Kinh Doanh",
            "kpi_commitment": "Tăng trưởng doanh thu toàn diện +15-20%",
            "timeline": "1-2 tháng",
            "impact": f"Bảo toàn quy mô doanh thu {kpis.get('total_revenue', 0):,.0f} ₫"
        })
    if len(solutions_list) < 4:
        solutions_list.append({
            "priority": "Trung hạn • Tối ưu vận hành",
            "title": "Thiết Lập Hệ Thống Giám Sát Chỉ Số Hiệu Quả (KPI Dashboard)",
            "target": "Cập nhật số liệu kinh doanh định kỳ và cảnh báo sớm",
            "details": "Tự động hóa báo cáo doanh số theo từng kênh và khu vực theo tuần/tháng để ban điều hành kịp thời ra quyết định điều phối nguồn lực.",
            "raci": "Bộ Phận Phân Tích Dữ Liệu & IT",
            "kpi_commitment": "Rút ngắn thời gian ra quyết định quản trị",
            "timeline": "2 tuần",
            "impact": "Giảm thiểu rủi ro chậm trễ thông tin điều hành"
        })

    # Đóng gói kết quả ma trận giải pháp
    quick_wins = [s for s in solutions_list if any(k in s['priority'] for k in ['Tuần 1', 'Tuần 2', '1 tuần', 'Khẩn cấp', 'P1'])]
    strategic = [s for s in solutions_list if any(k in s['priority'] for k in ['Dài hạn', 'Trung hạn', 'Tháng', 'P2', 'Chiến Lược'])]
    operational = [s for s in solutions_list if s not in quick_wins and s not in strategic]

    return {
        "solutions_list": solutions_list,
        "quick_wins": quick_wins if quick_wins else solutions_list[:1],
        "strategic_projects": strategic if strategic else solutions_list[1:2],
        "operational_fixes": operational if operational else solutions_list[2:]
    }

def generate_llm_solutions(
    api_key: str,
    insights_text: str,
    kpis: Dict[str, Any]
) -> Optional[str]:
    """Tạo đề xuất giải pháp bằng LLM chuyên sâu."""
    try:
        from google import genai
        if api_key.startswith("AQ."):
            client = genai.Client(vertexai=True, api_key=api_key)
        else:
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
1. CHIẾN LƯỢC ĐỊNH GIÁ & TỐI ƯU HÓA BIÊN LỢI NHUẬN (Pricing & Margin Optimization): Cách giải quyết triệt để vấn đề chiết khấu và lợi nhuận âm.
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

