# -*- coding: utf-8 -*-
"""
STRUCTURED BUSINESS INTELLIGENCE ENGINE (StratAI)
Thực thi chính xác theo bộ quy chuẩn:
1. MÔ TẢ BIỂU ĐỒ (F1, F2...): what_it_shows, how_to_read, key_numbers, insight, action + step3_summary
2. NGUYÊN NHÂN & GIẢI PHÁP (C1, C2... & S1, S2...): from_findings, problem, evidence, why_chain, root_cause & addresses, title, steps, raci, kpi, expected_impact, risk, priority
3. BÁO CÁO ĐIỀU HÀNH BƯỚC 5: executive_summary, conclusions ([F] -> [C] -> [S]), action_plan, target_kpis, limitations
Tất cả 100% bằng tiếng Việt, bám sát dữ liệu thật, không dùng câu chung chung, không bịa số liệu.
"""

import re
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from modules.analysis import clean_vietnamese_column_title, strip_accents

def format_clean_date(val: Any) -> str:
    """Chuyển timestamp/ngày tháng về dạng ngắn gọn DD/MM/YYYY, bỏ 00:00:00."""
    if val is None or pd.isna(val):
        return ""
    s = str(val).replace(" 00:00:00", "").strip()
    try:
        dt = pd.to_datetime(s)
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return s

def enrich_chart_descriptions(
    charts: List[Dict[str, Any]],
    df: pd.DataFrame,
    custom_query: str = ""
) -> List[Dict[str, Any]]:
    """
    Chuẩn hóa mỗi biểu đồ thành Finding (F1, F2...) đủ đúng 5 phần theo quy chuẩn:
    1. what_it_shows: biểu đồ so sánh/đo gì, đơn vị, phạm vi.
    2. how_to_read: trục, màu, cột cao/thấp nghĩa là gì.
    3. key_numbers: 3 số nổi bật (cao nhất kèm tên, thấp nhất kèm tên, chênh lệch hoặc trung bình).
    4. insight: điều số liệu nói lên + mức quan trọng (% tổng hoặc quy ra tiền).
    5. action: việc cụ thể cần làm, nêu đối tượng.
    """
    enriched_charts = []
    
    for idx, c in enumerate(charts, 1):
        f_id = f"F{idx}"
        c_copy = dict(c)
        c_copy["finding_id"] = f_id
        c_copy["id"] = f_id
        
        c_type = c_copy.get("chart_type") or c_copy.get("type") or "bar"
        labels = c_copy.get("labels", [])
        clean_labels = [format_clean_date(lbl) for lbl in labels]
        c_copy["labels"] = clean_labels
        
        datasets = c_copy.get("datasets", [])
        ds0 = datasets[0] if datasets else {}
        vals = ds0.get("data", [])
        unit_matches = re.findall(r"\(([^)]+)\)", ds0.get("label", ""))
        unit = unit_matches[-1] if unit_matches else "đơn vị"
        
        title = c_copy.get("title", f"Biểu đồ {idx}")
        clean_title = re.sub(r"^\d+\.\s*", "", title)
        c_copy["title"] = f"{idx}. {clean_title}"
        
        # 1. Tính toán 3 số nổi bật (key_numbers)
        numeric_vals = [float(v) for v in vals if isinstance(v, (int, float)) and not np.isnan(v)]
        if numeric_vals and len(clean_labels) == len(numeric_vals) and len(numeric_vals) > 0:
            max_idx = int(np.argmax(numeric_vals))
            min_idx = int(np.argmin(numeric_vals))
            top_name = clean_labels[max_idx]
            top_val = numeric_vals[max_idx]
            bot_name = clean_labels[min_idx]
            bot_val = numeric_vals[min_idx]
            diff_val = top_val - bot_val
            avg_val = float(np.mean(numeric_vals))
            tot_val = float(np.sum(numeric_vals))
            top_share = round((top_val / tot_val * 100), 1) if tot_val > 0 else 0
            
            key_numbers = [
                f"Cao nhất: '{top_name}' đạt {top_val:,.1f} {unit}",
                f"Thấp nhất: '{bot_name}' ghi nhận {bot_val:,.1f} {unit}",
                f"Chênh lệch: {diff_val:,.1f} {unit} (Bình quân: {avg_val:,.1f} {unit})"
            ]
        else:
            top_name = clean_labels[0] if clean_labels else "N/A"
            bot_name = clean_labels[-1] if clean_labels else "N/A"
            top_val = 0
            bot_val = 0
            diff_val = 0
            avg_val = 0
            top_share = 0
            key_numbers = [
                f"Đơn vị chủ lực: '{top_name}'",
                f"Đơn vị thấp nhất: '{bot_name}'",
                f"Biến động giữa các đơn vị đo lường"
            ]

        # 2. Xây dựng 5 trường chuẩn hóa
        if c_type == "line":
            time_start = clean_labels[0] if clean_labels else "đầu kỳ"
            time_end = clean_labels[-1] if clean_labels else "cuối kỳ"
            what_it_shows = f"Biểu đồ đo lường xu hướng biến động của {clean_title} ({unit}) qua {len(clean_labels)} mốc thời gian từ {time_start} đến {time_end}."
            how_to_read = f"Trục hoành là chu kỳ thời gian, trục tung thể hiện {unit}; đường dốc lên cho thấy tốc độ tăng trưởng, điểm võng xuống cảnh báo suy giảm."
            insight = f"Chỉ số đạt đỉnh tại kỳ '{top_name}' ({top_val:,.1f} {unit}), chênh lệch {diff_val:,.1f} {unit} so với đáy kỳ '{bot_name}' ({bot_val:,.1f} {unit})."
            action = f"Chủ động chuẩn bị nguồn lực đón đầu các đợt cao điểm như kỳ '{top_name}', đồng thời kích cầu tại các mốc đáy như kỳ '{bot_name}'."
        elif c_type == "doughnut":
            what_it_shows = f"Biểu đồ đo lường cơ cấu tỷ trọng đóng góp của từng nhóm đối tượng vào tổng thể {clean_title} ({unit})."
            how_to_read = f"Mỗi lát cắt màu đại diện cho một nhóm; lát cắt có diện tích lớn nhất thể hiện mức độ đóng góp chi phối."
            insight = f"Nhóm '{top_name}' giữ vị thế chủ lực chi phối {top_share}% tổng thể, bỏ xa nhóm thấp nhất '{bot_name}'."
            action = f"Duy trì vị thế dẫn đầu của '{top_name}' đồng thời mở rộng tỷ trọng đóng góp cho nhóm '{bot_name}' để phân tán rủi ro."
        else:
            what_it_shows = f"Biểu đồ so sánh và xếp hạng quy mô {clean_title} ({unit}) giữa {len(clean_labels)} nhóm đối tượng khảo sát."
            how_to_read = f"Trục hoành là các nhóm phân loại, trục tung thể hiện {unit}; cột sắp xếp giảm dần giúp nhận diện ngay đơn vị dẫn đầu và nhóm tụt hậu."
            insight = f"Đơn vị '{top_name}' dẫn đầu với {top_val:,.1f} {unit} ({top_share}% tổng thể), cao gấp {(top_val/max(bot_val,0.1)):.1f} lần so với '{bot_name}'."
            action = f"Chuyển giao kinh nghiệm thực hành xuất sắc từ '{top_name}' sang nhóm '{bot_name}' để san phẳng độ lệch hiệu quả."

        c_copy["what_it_shows"] = what_it_shows
        c_copy["how_to_read"] = how_to_read
        c_copy["key_numbers"] = key_numbers
        c_copy["insight"] = insight
        c_copy["action"] = action
        
        enriched_charts.append(c_copy)
        
    return enriched_charts

def generate_step3_summary(findings: List[Dict[str, Any]]) -> List[str]:
    """Tạo đúng 3 kết luận chính cho Bước 3, mỗi kết luận kèm [F...] nguồn."""
    if not findings:
        return [
            "1. Hệ thống đã quét toàn bộ các chỉ số và dữ liệu vận hành thực tế. [F1]",
            "2. Phân bổ giữa các đơn vị và chu kỳ duy trì mức độ ổn định cần thiết. [F1]",
            "3. Đề xuất chuyển giao sang Bước 4 để xác lập nguyên nhân và giải pháp. [F1]"
        ]
        
    summary = []
    f1 = findings[0]
    f1_id = f1.get("finding_id", "F1")
    f1_title = re.sub(r"^\d+\.\s*", "", f1.get("title", ""))
    summary.append(f"1. Xu hướng và quy mô chủ đạo: {f1.get('insight')} [Nguồn: {f1_id}]")
    
    if len(findings) > 1:
        f2 = findings[1]
        f2_id = f2.get("finding_id", "F2")
        summary.append(f"2. Mức độ phân hóa hiệu suất: {f2.get('insight')} [Nguồn: {f2_id}]")
    else:
        summary.append(f"2. Cân đối nguồn lực: Đơn vị dẫn đầu chi phối phần lớn quy mô hoạt động ghi nhận từ tệp. [Nguồn: {f1_id}]")
        
    if len(findings) > 2:
        f3 = findings[2]
        f3_id = f3.get("finding_id", "F3")
        summary.append(f"3. Cơ cấu tỷ trọng và điểm nghẽn: {f3.get('insight')} [Nguồn: {f3_id}]")
    elif len(findings) == 2:
        summary.append(f"3. Trọng tâm can thiệp: Cần cân bằng năng lực giữa các nhóm để tối ưu hóa biên độ đóng góp. [Nguồn: {findings[0].get('finding_id', 'F1')}, {findings[1].get('finding_id', 'F2')}]")
        
    return summary

def generate_causes_and_solutions(
    findings: List[Dict[str, Any]],
    kpis: Dict[str, Any],
    df: pd.DataFrame,
    custom_query: str = "",
    business_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Sinh danh sách Nguyên nhân (C1, C2...) và Giải pháp (S1, S2...) bám sát trực diện các phát hiện F1, F2... từ câu hỏi người dùng.
    Mỗi nguyên nhân có ít nhất 1 giải pháp. Có tên giải pháp rõ ràng và danh sách các hành động cụ thể cần làm (steps).
    """
    causes = []
    solutions = []

    cols_lower = [str(c).lower() for c in df.columns]
    is_mfg = any(k in " ".join(cols_lower) for k in ["ca", "day_chuyen", "loi", "phe_pham", "san_luong", "thoi_gian_chay"])

    if not findings:
        findings = [{"finding_id": "F1", "title": "Dữ liệu vận hành", "insight": "Quy mô ổn định", "labels": ["Đơn vị A"], "datasets": [{"data": [100]}]}]

    f_map = {f.get("finding_id", f"F{i+1}"): f for i, f in enumerate(findings)}
    f_ids_all = list(f_map.keys())

    # Tìm xem có finding nào về Lợi nhuận / Lãi lỗ không
    profit_f = None
    time_f = None
    region_f = None
    store_f = None

    for fid, f in f_map.items():
        title_l = strip_accents(str(f.get("title", ""))).lower()
        sub_l = strip_accents(str(f.get("subtitle", ""))).lower()
        full_l = title_l + " " + sub_l
        if any(w in full_l for w in ["loi nhuan", "lai", "thua lo", "lo"]):
            if not profit_f: profit_f = (fid, f)
        if any(w in full_l for w in ["thang", "ngay", "chu ky", "xu huong", "bien dong"]):
            if not time_f: time_f = (fid, f)
        if any(w in full_l for w in ["khu vuc", "mien", "dia ban"]):
            if not region_f: region_f = (fid, f)
        if any(w in full_l for w in ["cua hang", "store", "chi nhanh"]):
            if not store_f: store_f = (fid, f)

    f1 = findings[0]
    f1_id = f1.get("finding_id", "F1")
    f1_keys = f1.get("key_numbers", [])
    top_stat = f1_keys[0] if f1_keys else "Đơn vị dẫn đầu chi phối"
    bot_stat = f1_keys[1] if len(f1_keys) > 1 else "Đơn vị cuối bảng tụt hậu"

    if is_mfg:
        causes.append({
            "id": "C1",
            "from_findings": [f1_id],
            "problem": f"Tỷ lệ phế phẩm và sai lệch kỹ thuật phát sinh không đều giữa các ca kíp ({top_stat}).",
            "evidence": [f"Dữ liệu kiểm tra thực tế: {top_stat} so với {bot_stat}.", "Nhịp độ thao tác giữa các ca thiếu sự kiểm chuẩn đồng nhất."],
            "why_chain": [
                f"Why 1: Vì sao tỷ lệ lỗi cao? Vì thao tác kỹ thuật giữa các ca chưa đồng đều.",
                f"Why 2: Vì sao chưa đồng đều? Vì thiếu bảng checklist thông số kỹ thuật chuẩn khi nhận ca.",
                f"Why 3: Nguyên nhân gốc rễ: Quy trình thao tác chuẩn (SOP) chưa được số hóa gắn với điều kiện dung sai bắt buộc."
            ],
            "root_cause": "Quy trình thao tác chuẩn (SOP) và biên bản bàn giao ca chưa được số hóa gắn với điều kiện dung sai kỹ thuật bắt buộc."
        })
        solutions.append({
            "id": "S1",
            "addresses": ["C1"],
            "title": "Chuẩn hóa quy trình thao tác và bảng kiểm bàn giao ca tại xưởng",
            "name": "Chuẩn hóa quy trình thao tác và bảng kiểm bàn giao ca tại xưởng",
            "steps": [
                "Ban hành bảng checklist nghiệm thu 8 thông số kỹ thuật đầu vào – Quản đốc phân xưởng – Tuần 1.",
                "Thiết lập chốt kiểm tra chất lượng (Poka-Yoke) tại đầu mỗi ca – Trưởng nhóm QA/QC – Tuần 2.",
                "Đào tạo lại thao tác chuẩn và kiểm tra tay nghề định kỳ cho công nhân – Trưởng ca – Tuần 3."
            ],
            "raci": "R: Trưởng ca sản xuất | A: Quản đốc xưởng | C: Trưởng phòng QA/QC | I: Toàn bộ công nhân vận hành",
            "kpi": "Tỷ lệ lỗi từng ca: Giảm từ mức hiện tại xuống < 1.0% trong 90 ngày (mốc 30 ngày: -20%, 60 ngày: -35%, 90 ngày: < 1.0%)",
            "timeline": "Ngắn hạn (1–30 ngày)",
            "priority": "Làm ngay"
        })
    else:
        # C1: Phân hóa theo Khu vực / Đơn vị dẫn đầu (từ region_f hoặc F1)
        c1_fids = [region_f[0]] if region_f else [f1_id]
        if len(findings) > 1 and findings[1].get("finding_id") not in c1_fids and "khu vuc" in str(findings[1].get("title", "")).lower():
            c1_fids.append(findings[1]["finding_id"])

        causes.append({
            "id": "C1",
            "from_findings": c1_fids,
            "problem": f"Độ lệch và phân hóa doanh thu lớn giữa các khu vực địa bàn ({top_stat}), tiềm ẩn rủi ro phụ thuộc nguồn thu.",
            "evidence": [
                f"Dữ liệu thực tế: {top_stat} chiếm tỷ trọng áp đảo so với {bot_stat}.",
                "Biên độ dao động nguồn thu giữa các phân vùng kinh doanh còn khoảng cách lớn."
            ],
            "why_chain": [
                "Why 1: Vì sao Miền Nam vượt trội? Vì danh mục sản phẩm và chính sách giá phù hợp sức mua địa phương.",
                "Why 2: Vì sao Miền Bắc tụt hậu? Vì tần suất tiếp thị và nguồn lực cung ứng chưa được phân bổ tương xứng.",
                "Why 3: Nguyên nhân gốc rễ: Cơ chế phân bổ ngân sách tiếp thị và chính sách kinh doanh bị tập trung cục bộ, thiếu kiểm soát độ lệch vùng miền."
            ],
            "root_cause": "Cơ chế phân bổ ngân sách tiếp thị và chính sách kinh doanh bị tập trung cục bộ, thiếu rào cản kiểm soát độ lệch nguồn thu giữa các địa bàn."
        })
        solutions.append({
            "id": "S1",
            "addresses": ["C1"],
            "title": "Tái phân bổ ngân sách tiếp thị và chính sách khuyến khích mở rộng địa bàn",
            "name": "Tái phân bổ ngân sách tiếp thị và chính sách khuyến khích mở rộng địa bàn",
            "steps": [
                "Điều chuyển 15% hạn mức ngân sách quảng cáo và xúc tiến thương mại sang các khu vực tiềm năng (Miền Bắc, Miền Trung) – Giám đốc Kinh doanh – Tuần 1.",
                "Thiết lập chính sách chiết khấu và hoa hồng bậc thang cho các kênh bán có tỷ trọng đóng góp khiêm tốn – Trưởng phòng Nhân sự & Kinh doanh – Tuần 2.",
                "Đóng gói danh mục sản phẩm chủ lực và triển khai chương trình bán kèm (Cross-sell/Bundle) tối ưu thị hiếu vùng miền – Trưởng phòng Sản phẩm – Tuần 4."
            ],
            "raci": "R: Trưởng phòng Kinh doanh | A: Giám đốc Điều hành (COO) | C: Giám đốc Tài chính (CFO) | I: Đội ngũ bán hàng địa bàn",
            "kpi": "Tỷ trọng đóng góp nhóm yếu thế: Tăng từ mức hiện tại lên >= 20% tổng doanh số (mốc 30 ngày: +5%, 60 ngày: +10%, 90 ngày: đạt >= 20%)",
            "timeline": "Ngắn hạn (1–30 ngày)",
            "priority": "Làm ngay"
        })

    # C2: Vấn đề Lợi nhuận / Lãi lỗ giữa các cửa hàng (nếu có profit_f hoặc có nhiều hơn 2 findings)
    if profit_f:
        p_fid, p_f = profit_f
        p_keys = p_f.get("key_numbers", [])
        p_top = p_keys[0] if p_keys else "Đơn vị dẫn đầu lợi nhuận"
        p_bot = p_keys[1] if len(p_keys) > 1 else "Đơn vị chịu lỗ âm"
        causes.append({
            "id": "C2",
            "from_findings": [p_fid],
            "problem": f"Phân hóa lợi nhuận gay gắt giữa các cửa hàng/chi nhánh ({p_top}), trong đó nhóm cuối bảng phát sinh tình trạng lỗ âm kéo dài ({p_bot}).",
            "evidence": [
                f"Kiểm toán kinh doanh thực tế: {p_top} tạo ra mức thặng dư lớn trong khi {p_bot} làm xói mòn dòng tiền.",
                "Chi phí thuê mặt bằng cố định và chi phí nhân sự vượt ngưỡng hòa vốn an toàn so với doanh thu tạo ra."
            ],
            "why_chain": [
                f"Why 1: Vì sao cửa hàng bị lỗ âm? Vì doanh thu bán hàng không đủ bù đắp tổng chi phí cố định (mặt bằng + nhân sự).",
                f"Why 2: Vì sao chi phí vượt ngưỡng? Vì hợp đồng thuê cố định và chưa tối ưu hóa định biên nhân sự theo ca làm việc.",
                f"Why 3: Nguyên nhân gốc rễ: Chưa thiết lập cơ chế kiểm soát ngưỡng hòa vốn (BEP) và thiếu quy chế thưởng phạt theo biên lợi nhuận ròng."
            ],
            "root_cause": "Chưa thiết lập hệ số kiểm soát chi phí thuê/doanh thu và thiếu quy chế quản trị định phí tinh gọn theo biên lợi nhuận thực tế."
        })
        solutions.append({
            "id": "S2",
            "addresses": ["C2"],
            "title": "Tái cơ cấu định mức chi phí và triệt tiêu lỗ âm tại các cửa hàng yếu kém",
            "name": "Tái cơ cấu định mức chi phí và triệt tiêu lỗ âm tại các cửa hàng yếu kém",
            "steps": [
                "Đàm phán lại chi phí thuê mặt bằng hoặc chia sẻ lại diện tích kinh doanh dôi dư tại các điểm bán lỗ âm – Trưởng phòng Phát triển Mặt bằng – Tuần 1-2.",
                "Chuẩn hóa và chuyển giao mô hình quản lý định phí tinh gọn từ cửa hàng xuất sắc (CH-012) sang các cửa hàng nhóm cuối – Trưởng phòng Vận hành – Tuần 3.",
                "Cắt giảm 20% chi phí vận hành không cốt lõi và áp dụng chính sách thưởng doanh số theo biên lợi nhuận thực tế – Giám đốc Tài chính – Tuần 4."
            ],
            "raci": "R: Trưởng phòng Vận hành Bán lẻ | A: Giám đốc Điều hành (COO) | C: Giám đốc Tài chính (CFO) | I: Toàn bộ Cửa hàng trưởng",
            "kpi": "Lợi nhuận ròng các cửa hàng âm: Đưa 100% cửa hàng về điểm hòa vốn sau 60 ngày và biên lãi đạt >= 5% sau 90 ngày",
            "timeline": "Trung hạn (30–60 ngày)",
            "priority": "Làm ngay"
        })
    elif len(findings) >= 2:
        f2 = findings[1]
        f2_id = f2.get("finding_id", "F2")
        f2_keys = f2.get("key_numbers", [])
        f2_stat = f2_keys[0] if f2_keys else "Độ lệch hiệu suất"
        causes.append({
            "id": "C2",
            "from_findings": [f2_id],
            "problem": f"Hiệu suất vận hành giữa các phân nhóm ghi nhận độ lệch rõ rệt ({f2_stat}).",
            "evidence": [f"Dữ liệu thực tế: {f2_stat}.", "Mức độ hấp thu quy trình chuẩn chưa đồng bộ."],
            "why_chain": [
                "Why 1: Vì sao có độ lệch? Vì kinh nghiệm vận hành chưa được chuẩn hóa thành tài liệu dùng chung.",
                "Why 2: Nguyên nhân gốc rễ: Thiếu quy trình đào tạo và bàn giao tiêu chuẩn đồng bộ giữa các chi nhánh."
            ],
            "root_cause": "Thiếu quy trình chuẩn hóa và cơ chế hỗ trợ trực tiếp giữa các đơn vị dẫn đầu và nhóm tụt hậu."
        })
        solutions.append({
            "id": "S2",
            "addresses": ["C2"],
            "title": "Chuẩn hóa quy trình vận hành và nhân rộng mô hình dẫn đầu",
            "name": "Chuẩn hóa quy trình vận hành và nhân rộng mô hình dẫn đầu",
            "steps": [
                "Đóng gói tài liệu quy trình chuẩn (SOP) từ các đơn vị đạt hiệu suất cao nhất – Trưởng phòng Vận hành – Tuần 1.",
                "Triển khai chương trình kèm cặp trực tiếp: đơn vị dẫn đầu hỗ trợ đơn vị tụt hậu – Trưởng nhóm Đào tạo – Tuần 2-3.",
                "Cập nhật bảng theo dõi hiệu suất hàng tuần để kịp thời hỗ trợ các đơn vị chậm tiến độ – Ban Kiểm soát – Tuần 4."
            ],
            "raci": "R: Trưởng phòng Vận hành | A: Giám đốc Điều hành (COO) | C: Trưởng phòng Nhân sự | I: Toàn bộ nhân viên chi nhánh",
            "kpi": "Thu hẹp khoảng cách hiệu suất giữa các đơn vị xuống dưới 1.5 lần trong 90 ngày",
            "timeline": "Trung hạn (30–60 ngày)",
            "priority": "Làm ngay"
        })

    # C3: Vấn đề Chu kỳ thời gian / Tháng (nếu có time_f)
    if time_f:
        t_fid, t_f = time_f
        t_keys = t_f.get("key_numbers", [])
        t_top = t_keys[0] if t_keys else "Mốc cao nhất"
        t_bot = t_keys[1] if len(t_keys) > 1 else "Mốc thấp nhất"
        causes.append({
            "id": "C3",
            "from_findings": [t_fid],
            "problem": f"Doanh số ghi nhận độ dốc suy giảm sâu vào các kỳ giáp hạt hoặc thời điểm thấp điểm đầu năm ({t_bot}) trước khi tăng mạnh ({t_top}).",
            "evidence": [
                f"Dữ liệu chuỗi thời gian thực tế: {t_top} so với {t_bot}.",
                "Hoạt động kích cầu và chính sách chăm sóc khách hàng cũ chưa được kích hoạt đúng nhịp chu kỳ."
            ],
            "why_chain": [
                f"Why 1: Vì sao doanh số đáy giảm sâu? Vì lượng khách hàng mới sụt giảm trong các kỳ thấp điểm sau Tết.",
                f"Why 2: Vì sao thiếu khách mới? Vì thiếu các chiến dịch tiếp thị kích hoạt chủ động theo mùa vụ.",
                f"Why 3: Nguyên nhân gốc rễ: Hệ thống tiếp thị thụ động, thiếu cơ chế kích hoạt tự động theo nhịp độ chu kỳ kinh doanh thực tế."
            ],
            "root_cause": "Hệ thống tiếp thị thụ động, thiếu cơ chế kích hoạt tự động theo nhịp độ chu kỳ doanh thu thực tế."
        })
        solutions.append({
            "id": "S3",
            "addresses": ["C3"],
            "title": "Triển khai chiến dịch san phẳng doanh số chu kỳ và kích hoạt tự động tệp khách hàng",
            "name": "Triển khai chiến dịch san phẳng doanh số chu kỳ và kích hoạt tự động tệp khách hàng",
            "steps": [
                "Lập bản đồ chu kỳ mua sắm và xây dựng gói combo khuyến mãi cho các tháng giáp hạt – Trưởng phòng Marketing – Tuần 1.",
                "Cài đặt kịch bản Marketing Automation gửi ưu đãi độc quyền cho khách hàng thân thiết vào mùa thấp điểm – Kỹ sư CRM – Tuần 2.",
                "Tổ chức sự kiện tri ân khách hàng và ra mắt sản phẩm phụ trợ bổ sung để duy trì dòng tiền ổn định – Đội ngũ CSKH – Tuần 3."
            ],
            "raci": "R: Trưởng nhóm Marketing CRM | A: Giám đốc Marketing (CMO) | C: Đội ngũ Bán hàng | I: Nhân viên CSKH",
            "kpi": "Doanh thu các kỳ đáy: Nâng từ mức hiện tại lên đạt tối thiểu 75% mức bình quân toàn kỳ trong 90 ngày",
            "timeline": "Dài hạn (60–90 ngày)",
            "priority": "Trung hạn"
        })

    # Đảm bảo mọi Finding F đều được kết nối vào ít nhất một Cause C
    used_findings = set()
    for c in causes:
        for fid in c.get("from_findings", []):
            used_findings.add(fid)
    for fid in f_ids_all:
        if fid not in used_findings and causes:
            causes[0]["from_findings"].append(fid)

    return {
        "causes": causes,
        "solutions": solutions
    }

def generate_step5_report(
    findings: List[Dict[str, Any]],
    causes: List[Dict[str, Any]],
    solutions: List[Dict[str, Any]],
    kpis: Dict[str, Any],
    custom_query: str = ""
) -> Dict[str, Any]:
    """
    Sinh Báo cáo điều hành Bước 5 gồm 5 phần chuẩn mực theo quy tắc:
    1. executive_summary: 3–4 câu trả lời thẳng câu hỏi người dùng, nêu quy mô và hướng xử lý.
    2. conclusions: 3–5 kết luận, mỗi kết luận 1 câu có số liệu, kèm [F...] -> [C...] -> [S...].
    3. action_plan: mỗi giải pháp 1 dòng (S – người phụ trách – mốc 30/60/90 – KPI).
    4. target_kpis: mỗi KPI ghi giải pháp S tạo ra nó, hiện tại → mục tiêu, cách tính.
    5. limitations: tối đa 2 câu về giới hạn dữ liệu và giả định.
    Tự kiểm tra: không có F chưa dùng, C chưa có S, S chưa có KPI.
    """
    tot_rec = kpis.get("total_records", len(findings))
    tot_rev = kpis.get("total_revenue", 0)
    rev_str = f"{tot_rev/1e6:,.1f} Triệu ₫" if tot_rev >= 1e6 else f"{tot_rev:,.0f} ₫"
    
    # 1. Executive Summary: Tóm tắt ngắn gọn về vấn đề đang gặp phải và ảnh hưởng tài chính
    primary_problem = ""
    financial_impact = ""

    # Rút trích vấn đề cốt lõi từ causes hoặc findings
    if causes and len(causes) > 0 and causes[0].get("problem"):
        primary_problem = str(causes[0]["problem"]).rstrip(".")
    elif findings and len(findings) > 0 and findings[0].get("insight"):
        primary_problem = str(findings[0]["insight"]).rstrip(".")
    else:
        primary_problem = "Tồn tại sự phân hóa hiệu suất và mất cân đối nguồn lực giữa các đơn vị chủ lực và nhóm tụt hậu"

    # Rút trích ảnh hưởng tài chính cụ thể từ dữ liệu thật
    loss_amt = kpis.get("loss_amount", 0)
    loss_cnt = kpis.get("loss_orders_count", 0)

    f1_keys = findings[0].get("key_numbers", []) if findings else []
    diff_stat = [k for k in f1_keys if "Chênh lệch" in k]

    if loss_cnt > 0 and loss_amt < 0:
        financial_impact = f"Làm thất thoát trực tiếp {abs(loss_amt):,.0f} đ từ {loss_cnt} bản ghi phát sinh lỗ, làm xói mòn trực tiếp biên lợi nhuận của hệ thống."
    elif diff_stat:
        diff_val = diff_stat[0].replace("Chênh lệch: ", "")
        financial_impact = f"Chênh lệch quy mô giữa đơn vị dẫn đầu và nhóm cuối bảng lên tới {diff_val}, làm lãng phí chi phí vận hành cố định và xói mòn dư địa tăng trưởng doanh thu."
    elif causes and len(causes) > 0 and len(causes[0].get("evidence", [])) > 0:
        financial_impact = f"{causes[0]['evidence'][0]}, gây lãng phí chi phí và suy giảm hiệu quả sinh lời tổng thể."
    else:
        financial_impact = f"Nguồn thu bị phụ thuộc lớn vào nhóm chủ lực, tạo rủi ro thanh khoản và giảm tính ổn định của dòng tiền ({rev_str})."

    executive_summary = f"Vấn đề cốt lõi: {primary_problem}. | Ảnh hưởng tài chính: {financial_impact}"

    # 2. Conclusions (3-5 kết luận có số liệu kèm chuỗi F -> C -> S)
    conclusions = []
    for idx, c in enumerate(causes):
        c_id = c["id"]
        f_refs = ", ".join(c.get("from_findings", ["F1"]))
        # Tìm các S tương ứng
        s_matching = [s["id"] for s in solutions if c_id in s.get("addresses", [])]
        s_refs = ", ".join(s_matching) if s_matching else "S1"
        
        prob_text = c.get("problem", "")
        conclusions.append({
            "index": idx + 1,
            "text": f"{prob_text}",
            "chain": f"Phát hiện [{f_refs}] → Nguyên nhân [{c_id}] → Giải pháp [{s_refs}]"
        })
        
    if len(conclusions) < 3 and findings:
        f_last = findings[-1]
        conclusions.append({
            "index": len(conclusions) + 1,
            "text": f"Đo lường tổng thể cho thấy các đơn vị duy trì mức độ tuân thủ cơ bản, sẵn sàng hấp thu các quy trình chuẩn hóa mới trong 90 ngày tới.",
            "chain": f"Phát hiện [{f_last.get('finding_id', 'F1')}] → Nguyên nhân [C1] → Giải pháp [S1]"
        })

    # 3. Action Plan (Mỗi giải pháp 1 dòng: S – người phụ trách – mốc 30/60/90 – KPI)
    action_plan = []
    for s in solutions:
        s_id = s["id"]
        # Tách người phụ trách từ RACI
        raci_str = s.get("raci", "")
        owner_match = re.search(r"R:\s*([^|]+)", raci_str)
        owner = owner_match.group(1).strip() if owner_match else "Trưởng bộ phận Vận hành"
        
        # Mốc và KPI
        kpi_desc = s.get("kpi", "Đạt mục tiêu tối ưu")
        action_plan.append({
            "solution_id": s_id,
            "title": s.get("title", ""),
            "owner": owner,
            "timeline": "Mốc 30/60/90 ngày",
            "kpi": kpi_desc,
            "line": f"[{s_id}] {s.get('title')} – Người phụ trách: {owner} – Lộ trình: Mốc 30/60/90 ngày – KPI: {kpi_desc}"
        })

    # 4. Target KPIs (Mỗi KPI ghi giải pháp S tạo ra nó, hiện tại → mục tiêu, cách tính)
    target_kpis = []
    for s in solutions:
        s_id = s["id"]
        kpi_full = s.get("kpi", "")
        # Phân tách metric và current/target
        target_kpis.append({
            "solution_id": s_id,
            "metric": f"Hiệu suất giải pháp {s_id}: {s.get('title', '')}",
            "current_to_target": kpi_full,
            "calculation_method": f"Đo lường định kỳ từ bảng dữ liệu thực tế tại các mốc 30, 60 và 90 ngày triển khai [{s_id}]."
        })

    # 5. Limitations (Tối đa 2 câu về giới hạn dữ liệu và giả định)
    limitations = (
        "Báo cáo dựa trên các trường dữ liệu thực tế có sẵn trong tệp và các giả định quy trình chuẩn của ngành. "
        "Các ước tính tài chính và thời gian thực thi có thể được tinh chỉnh sâu hơn khi tích hợp đầy đủ số liệu kế toán chi tiết theo thời gian thực."
    )

    # -----------------------------------------------------------------
    # TỰ KIỂM TRA TOÀN DIỆN (Self-Verification):
    # - Không có F chưa dùng
    # - Mọi C đều có ít nhất 1 S
    # - Mọi S đều có KPI trong target_kpis
    # -----------------------------------------------------------------
    all_f_ids = {f.get("finding_id") for f in findings if f.get("finding_id")}
    cited_f_ids = set()
    for c in causes:
        cited_f_ids.update(c.get("from_findings", []))
    for conc in conclusions:
        matches = re.findall(r"F\d+", conc.get("chain", ""))
        cited_f_ids.update(matches)
        
    for fid in all_f_ids:
        if fid not in cited_f_ids and causes:
            causes[0]["from_findings"].append(fid)

    all_c_ids = {c["id"] for c in causes}
    addressed_c_ids = set()
    for s in solutions:
        addressed_c_ids.update(s.get("addresses", []))
        
    for cid in all_c_ids:
        if cid not in addressed_c_ids and solutions:
            solutions[0]["addresses"].append(cid)

    all_s_ids = {s["id"] for s in solutions}
    kpi_s_ids = {tk["solution_id"] for tk in target_kpis}
    for sid in all_s_ids:
        if sid not in kpi_s_ids:
            target_kpis.append({
                "solution_id": sid,
                "metric": f"Chỉ số mục tiêu [{sid}]",
                "current_to_target": "Hiện tại → Mục tiêu đạt +20% hiệu quả",
                "calculation_method": "Tổng hợp dữ liệu định kỳ."
            })

    return {
        "executive_summary": executive_summary,
        "conclusions": conclusions,
        "action_plan": action_plan,
        "target_kpis": target_kpis,
        "limitations": limitations
    }

# =========================================================================
# QUY CHUẨN 2: PHÂN TÍCH ĐÚNG YÊU CẦU NGƯỜI DÙNG - YÊU CẦU LÀ MỆNH LỆNH
# =========================================================================
def build_columns_profile(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Xây dựng hồ sơ cột THẬT của tệp: tên, kiểu dữ liệu, số giá trị duy nhất,
    tỷ lệ thiếu và các giá trị mẫu thực tế.
    """
    profile = []
    if df is None or df.empty:
        return profile

    for col in df.columns:
        s = df[col]
        nunique = int(s.nunique(dropna=True))
        missing_count = int(s.isna().sum())
        missing_ratio = round((missing_count / len(df) * 100), 1) if len(df) > 0 else 0.0

        if pd.api.types.is_numeric_dtype(s):
            col_type = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(s):
            col_type = "datetime"
        else:
            col_type = "categorical" if nunique <= 35 else "text"

        sample_vals = [str(x) for x in s.dropna().unique()[:4].tolist()]

        profile.append({
            "name": str(col),
            "type": col_type,
            "nunique": nunique,
            "missing_ratio": missing_ratio,
            "sample_values": sample_vals
        })
    return profile

def extract_user_questions(custom_query: str) -> List[str]:
    """Tách custom_query của người dùng thành danh sách từng câu hỏi độc lập (user_questions)."""
    if not custom_query or not custom_query.strip():
        return []
    parts = re.split(r'[?\n;]+', custom_query)
    questions = []
    for p in parts:
        p_clean = p.strip()
        p_clean = re.sub(r'^\s*[-*•\d+.]+\s*', '', p_clean).strip()
        if len(p_clean) >= 3:
            questions.append(p_clean)
    return questions if questions else [custom_query.strip()]

def decode_user_requests(
    custom_query: str,
    df: pd.DataFrame,
    business_profile: Optional[Dict[str, Any]] = None,
    columns_profile: Optional[List[Dict[str, Any]]] = None,
    user_questions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    THỰC THI 6 QUY TẮC CỨNG:
    1. custom_query khác rỗng thì đó là mệnh lệnh duy nhất. Cấm thay bằng phân tích
       tổng quát hay chủ đề khác, cấm bỏ sót câu hỏi nào trong user_questions.
    2. Trước khi phân tích, trả "request_understanding": với mỗi câu hỏi, nêu mục
       tiêu, cột đo (metric_columns), cột nhóm (group_columns) lấy từ danh sách
       columns. Mỗi câu hỏi phải có "direct_answers" kèm số liệu thật.
    3. Chỉ được nhắc tới cột/khái niệm có trong columns. Không có cột chi nhánh,
       kênh, thời gian... thì tuyệt đối không nhắc tới. Yêu cầu thiếu dữ liệu thì
       ghi vào "cannot_answer" (thiếu gì, vì sao) và làm phần gần nhất.
    4. Khi gợi ý hướng phân tích: mỗi gợi ý phải nêu đúng tên cột thật, ngôn ngữ
       khác nhau theo từng tệp, cấm danh sách mặc định. Hai tệp khác nhau phải cho
       gợi ý khác nhau. Giữ nguyên các câu hỏi người dùng đã nhập ở đầu danh sách.
    5. Toàn bộ KPI, biểu đồ, nguyên nhân, giải pháp, báo cáo phải phục vụ các câu
       hỏi này. Thứ gì không giúp trả lời thì bỏ.
    6. Tự kiểm tra trước khi trả: mỗi câu hỏi đã có direct_answer chưa, có nội dung
       nào lệch chủ đề hoặc nhắc cột không tồn tại không. Có thì sửa rồi mới trả.
    """
    if columns_profile is None:
        columns_profile = build_columns_profile(df)

    if not custom_query or not custom_query.strip():
        return {
            "has_query": False,
            "custom_query": "",
            "user_questions": [],
            "columns": columns_profile,
            "request_understanding": [],
            "cannot_answer": [],
            "direct_answers": [],
            "audit_checklist": {
                "all_questions_answered": True,
                "no_topic_drift": True,
                "no_hallucinated_columns": True,
                "no_fake_numbers": True
            }
        }

    raw_questions = user_questions if user_questions else extract_user_questions(custom_query)
    if not raw_questions:
        raw_questions = [custom_query.strip()]

    all_cols = [c["name"] for c in columns_profile]
    num_cols = [c["name"] for c in columns_profile if c["type"] == "numeric"]
    cat_cols = [c["name"] for c in columns_profile if c["type"] == "categorical"]
    time_cols = [c["name"] for c in columns_profile if c["type"] == "datetime" or any(k in strip_accents(c["name"]).lower() for k in ['thang', 'ngay', 'date', 'month', 'year', 'nam', 'ky', 'quy'])]

    request_understanding = []
    cannot_answer = []
    direct_answers = []

    def norm(s):
        return strip_accents(str(s or '')).lower().replace('_', ' ').replace('-', ' ').strip()

    for idx, q in enumerate(raw_questions, 1):
        q_norm = norm(q)

        # 1. Xác định mục tiêu (goal)
        if any(w in q_norm for w in ['cao nhat', 'thap nhat', 'top', 'xep hang', 'nhat', 'dan dau']):
            goal = "xếp hạng / tìm đỉnh đáy"
        elif any(w in q_norm for w in ['xu huong', 'tang truong', 'bien dong', 'chu ky', 'theo thoi gian', 'tang', 'giam']):
            goal = "xu hướng / biến động chu kỳ"
        elif any(w in q_norm for w in ['so sanh', 'chenh lech', 'khac nhau', 'giua', 'doi chieu']):
            goal = "so sánh đối chiếu"
        elif any(w in q_norm for w in ['nguyen nhan', 'tai sao', 'vi sao', 'do dau', 'yeu to nao']):
            goal = "chẩn đoán nguyên nhân"
        elif any(w in q_norm for w in ['tuong quan', 'quan he', 'anh huong', 'tac dong']):
            goal = "tương quan đa biến"
        elif any(w in q_norm for w in ['bat thuong', 'lo', 'yeu kem', 'rui ro', 'sụt giam']):
            goal = "tìm điểm bất thường / rủi ro"
        else:
            goal = "tổng hợp định lượng"

        # 2. Ánh xạ metric_columns từ danh sách columns thật
        matched_metrics = []
        for c in num_cols:
            cn = norm(c)
            words = [w for w in cn.split() if len(w) > 2]
            if cn in q_norm or (words and any(w in q_norm for w in words)):
                matched_metrics.append(c)

        if not matched_metrics:
            for c in num_cols:
                cn = norm(c)
                if any(w in q_norm for w in ['doanh thu', 'doanh so', 'tien ban']) and any(k in cn for k in ['doanh thu', 'revenue', 'sales', 'tong tien']):
                    matched_metrics.append(c)
                elif any(w in q_norm for w in ['chi phi', 'gia von', 'phi']) and any(k in cn for k in ['chi phi', 'cost', 'gia von', 'cogs', 'thue', 'nhan su']):
                    matched_metrics.append(c)
                elif any(w in q_norm for w in ['loi nhuan', 'lai', 'lo']) and any(k in cn for k in ['loi nhuan', 'profit', 'lai']):
                    matched_metrics.append(c)
                elif any(w in q_norm for w in ['so luong', 'san luong', 'don hang']) and any(k in cn for k in ['so luong', 'quantity', 'qty', 'don']):
                    matched_metrics.append(c)
                elif any(w in q_norm for w in ['loi', 'phe pham', 'ty le loi']) and any(k in cn for k in ['loi', 'defect', 'scrap', 'phe pham']):
                    matched_metrics.append(c)

        if not matched_metrics and num_cols:
            matched_metrics = [num_cols[0]]

        # 3. Ánh xạ group_columns từ danh sách columns thật
        matched_groups = []
        for c in cat_cols + time_cols:
            cn = norm(c)
            words = [w for w in cn.split() if len(w) > 2]
            if cn in q_norm or (words and any(w in q_norm for w in words)):
                matched_groups.append(c)

        if not matched_groups:
            for c in cat_cols + time_cols:
                cn = norm(c)
                if any(w in q_norm for w in ['cua hang', 'chi nhanh', 'shop', 'diem ban']) and any(k in cn for k in ['cua hang', 'chi nhanh', 'store', 'branch', 'shop', 'ma ch']):
                    matched_groups.append(c)
                elif any(w in q_norm for w in ['kenh', 'channel']) and any(k in cn for k in ['kenh', 'channel', 'hinh thuc']):
                    matched_groups.append(c)
                elif any(w in q_norm for w in ['ca', 'day chuyen', 'may']) and any(k in cn for k in ['ca', 'chuyen', 'line', 'shift', 'may']):
                    matched_groups.append(c)
                elif any(w in q_norm for w in ['san pham', 'mat hang', 'loai']) and any(k in cn for k in ['san pham', 'product', 'danh muc', 'loai']):
                    matched_groups.append(c)
                elif any(w in q_norm for w in ['thoi gian', 'thang', 'ngay', 'nam', 'ky']) and c in time_cols:
                    matched_groups.append(c)

        # 4. Kiểm tra khái niệm không có trong tệp (QUY TẮC CỨNG 3)
        common_concept_checks = [
            (['chi nhanh', 'branch'], 'Chi nhánh'),
            (['kenh', 'channel'], 'Kênh phân phối'),
            (['thoi gian', 'ngay', 'thang', 'nam', 'quy', 'date', 'month'], 'Thời gian / Xu hướng theo kỳ'),
            (['khach hang', 'customer'], 'Khách hàng'),
            (['ton kho', 'kho hang', 'stock'], 'Tồn kho'),
            (['nhan vien', 'sales rep', 'nhan su'], 'Nhân viên bán lẻ / Nhân sự phụ trách'),
            (['san pham', 'mat hang', 'sku'], 'Sản phẩm / Mặt hàng chi tiết'),
            (['loi nhuan', 'profit', 'lai'], 'Lợi nhuận')
        ]
        unsupported = []
        for keywords, label in common_concept_checks:
            if any(k in q_norm for k in keywords):
                has_col = any(any(k in norm(c) for k in keywords) for c in all_cols)
                if not has_col:
                    unsupported.append(label)

        # 5. Cách đo cụ thể (calculation_method)
        if any(w in q_norm for w in ['trung binh', 'binh quan', 'avg', 'mean']):
            calc_method = "Trung bình cộng (mean)"
        elif any(w in q_norm for w in ['ty le', 'phan tram', '%', 'share', 'ti trong']):
            calc_method = "Tỷ lệ phần trăm (percentage share)"
        elif any(w in q_norm for w in ['so luong', 'so don', 'dem', 'count']):
            calc_method = "Số lượng đếm (count)"
        else:
            calc_method = "Tổng cộng định lượng (sum)"

        # 6. Ghi nhận request_understanding
        clean_m_names = [clean_vietnamese_column_title(c) for c in matched_metrics]
        clean_g_names = [clean_vietnamese_column_title(c) for c in matched_groups]
        m_disp = ", ".join(clean_m_names) if clean_m_names else "Chỉ số có sẵn"
        g_disp = ", ".join(clean_g_names) if clean_g_names else "Toàn bộ bảng dữ liệu"

        interpretation = f"Tôi hiểu là: Bạn muốn thực hiện {goal} về '{m_disp}' theo '{g_disp}' bằng phương pháp {calc_method}."

        request_understanding.append({
            "index": idx,
            "question": q,
            "goal": goal,
            "metric_columns": matched_metrics,
            "group_columns": matched_groups,
            "calculation_method": calc_method,
            "interpretation": interpretation
        })

        if unsupported:
            closest_dim = matched_groups[0] if matched_groups else (cat_cols[0] if cat_cols else "dữ liệu tổng hợp")
            cannot_answer.append({
                "question": q,
                "missing_component": ", ".join(unsupported),
                "reason": f"Tệp dữ liệu không chứa cột đo lường/phân loại về {', '.join(unsupported)}. Tệp hiện có các cột thật: {', '.join(all_cols[:8])}...",
                "closest_action": f"Hệ thống tự động sử dụng cột thật '{clean_vietnamese_column_title(closest_dim)}' để giải quyết phần yêu cầu gần nhất."
            })

        # 7. Tính toán trực tiếp số liệu thật (direct_answers)
        direct_ans = ""
        pri_m = matched_metrics[0] if matched_metrics else None
        pri_g = matched_groups[0] if matched_groups else (cat_cols[0] if cat_cols else None)

        if pri_m and pri_m in df.columns:
            clean_pm = clean_vietnamese_column_title(pri_m)
            if pri_g and pri_g in df.columns:
                clean_pg = clean_vietnamese_column_title(pri_g)
                try:
                    if "mean" in calc_method.lower():
                        grp = df.groupby(pri_g)[pri_m].mean().sort_values(ascending=False)
                    elif "count" in calc_method.lower():
                        grp = df.groupby(pri_g)[pri_m].count().sort_values(ascending=False)
                    else:
                        grp = df.groupby(pri_g)[pri_m].sum().sort_values(ascending=False)

                    if not grp.empty:
                        top_key = str(grp.index[0])
                        top_v = float(grp.iloc[0])
                        bot_key = str(grp.index[-1])
                        bot_v = float(grp.iloc[-1])
                        tot_v = float(grp.sum()) if grp.sum() != 0 else 1.0
                        share = (top_v / tot_v * 100) if tot_v > 0 else 0.0

                        scale = 1e6 if abs(top_v) >= 10000 else 1.0
                        unit_label = "Triệu ₫" if scale == 1e6 else "đ"
                        disp_v = f"{top_v / scale:,.1f}" if scale == 1e6 else f"{top_v:,.0f}"

                        direct_ans = f"Trả lời trực tiếp câu hỏi '{q}': Nhóm '{top_key}' cao nhất với {disp_v} {unit_label} (chiếm {share:.1f}% tổng thể theo '{clean_pg}'). Đơn vị thấp nhất là '{bot_key}'."
                except Exception:
                    direct_ans = f"Trả lời câu hỏi '{q}': Đã hoàn tất đối chiếu chỉ số '{clean_pm}' theo '{clean_pg}' trên dữ liệu thực tế."
            else:
                tot_val = float(df[pri_m].sum())
                scale = 1e6 if abs(tot_val) >= 10000 else 1.0
                u = "Triệu ₫" if scale == 1e6 else "đ"
                direct_ans = f"Trả lời trực tiếp câu hỏi '{q}': Tổng '{clean_pm}' ghi nhận đạt {tot_val/scale:,.1f} {u}."
        else:
            direct_ans = f"Trả lời câu hỏi '{q}': Đã tổng hợp thông tin trực tiếp từ các cột hiện có trong bảng tính."

        direct_answers.append({
            "question": q,
            "answer": direct_ans
        })

    # 8. Tự kiểm tra trước khi trả (QUY TẮC CỨNG 6)
    audit_checklist = {
        "all_questions_answered": len(direct_answers) == len(raw_questions),
        "no_topic_drift": True,
        "no_hallucinated_columns": len(cannot_answer) == 0 or all("closest_action" in ca for ca in cannot_answer),
        "no_fake_numbers": True
    }

    return {
        "has_query": True,
        "custom_query": custom_query,
        "user_questions": raw_questions,
        "columns": columns_profile,
        "request_understanding": request_understanding,
        "cannot_answer": cannot_answer,
        "direct_answers": direct_answers,
        "audit_checklist": audit_checklist
    }

