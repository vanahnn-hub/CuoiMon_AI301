import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import io

from modules.ingestion import load_google_sheet, load_uploaded_file
from modules.cleaning import analyze_raw_quality, clean_and_integrate_data
from modules.storage import save_dataframe_to_db, list_stored_datasets, query_database, init_db
from modules.analysis import (
    auto_detect_columns, calculate_kpis, analyze_trends, 
    analyze_breakdowns, detect_anomalies, calculate_correlations
)
from modules.insights import extract_rule_based_insights, generate_llm_insights
from modules.solutions import generate_business_solutions, generate_llm_solutions
from modules.evaluation import build_evaluation_framework

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="AI Agent - Phân Tích & Giải Pháp Kinh Doanh",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS cho giao diện hiện đại, chuyên nghiệp
st.markdown("""
<style>
    /* Styling chính */
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 24px;
        border-radius: 12px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 26px;
        font-weight: 700;
    }
    .main-header p {
        color: #e0e7ff;
        margin: 8px 0 0 0;
        font-size: 14px;
    }
    
    /* Workflow Tracker */
    .step-box {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        transition: all 0.2s;
    }
    .step-box.active {
        background-color: #eff6ff;
        border-color: #3b82f6;
        box-shadow: 0 2px 4px rgba(59, 130, 246, 0.15);
    }
    
    /* KPI Card */
    .kpi-container {
        background: white;
        border-radius: 10px;
        padding: 16px;
        border-left: 5px solid #3b82f6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    
    /* Insight Card */
    .insight-card {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .insight-card.critical {
        border-left: 5px solid #ef4444;
    }
    .insight-card.warning {
        border-left: 5px solid #f59e0b;
    }
    .insight-card.positive {
        border-left: 5px solid #10b981;
    }
    
    /* Solution Card */
    .solution-card {
        background: #fdfdfd;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
        padding: 16px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Khởi tạo Database SQLite
init_db()

# State quản lý dữ liệu trong session
if "raw_df" not in st.session_state:
    st.session_state.raw_df = None
if "cleaned_df" not in st.session_state:
    st.session_state.cleaned_df = None
if "dataset_name" not in st.session_state:
    st.session_state.dataset_name = None
if "source_type" not in st.session_state:
    st.session_state.source_type = None
if "cleaning_summary" not in st.session_state:
    st.session_state.cleaning_summary = None
if "active_step" not in st.session_state:
    st.session_state.active_step = 1

# Header chính
st.markdown("""
<div class="main-header">
    <h1>💼 AI Agent: Phân Tích Dữ Liệu Kinh Doanh & Đề Xuất Giải Pháp</h1>
    <p>Hệ thống tự động hóa chu trình 7 bước: Thu thập ➔ Làm sạch ➔ Lưu trữ SQLite ➔ Phân tích đa chiều ➔ Rút ra Insight ➔ Đề xuất Chiến lược ➔ Đánh giá KPIs</p>
</div>
""", unsafe_allow_html=True)

# Hiển thị Workflow 7 bước trực quan (dựa theo sơ đồ quy trình người dùng cung cấp)
step_cols = st.columns(7)
workflow_steps = [
    ("1. Thu thập", "Google Sheet / File"),
    ("2. Làm sạch", "Chuẩn hóa & Xử lý NaN"),
    ("3. Lưu trữ", "SQLite Database"),
    ("4. Phân tích", "Xu hướng & Bất thường"),
    ("5. Rút Insight", "Nguyên nhân cốt lõi"),
    ("6. Giải pháp", "Kế hoạch hành động"),
    ("7. Đánh giá", "Đo lường KPIs & OKR")
]

for idx, (title, subtitle) in enumerate(workflow_steps):
    step_num = idx + 1
    is_active = (st.session_state.active_step == step_num)
    with step_cols[idx]:
        box_class = "step-box active" if is_active else "step-box"
        status_icon = "🔵" if is_active else ("🟢" if st.session_state.cleaned_df is not None and step_num <= 3 else "⚪")
        st.markdown(f"""
        <div class="{box_class}">
            <div style="font-weight: 600; font-size: 13px;">{status_icon} {title}</div>
            <div style="font-size: 11px; color: #64748b;">{subtitle}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<hr style='margin: 16px 0;'>", unsafe_allow_html=True)

# ================= SIDEBAR CẤU HÌNH =================
with st.sidebar:
    st.header("⚙️ Nguồn Dữ Liệu & AI Agent")
    
    input_method = st.radio(
        "Chọn phương thức nhập dữ liệu:",
        ["📁 Tải file lên (CSV, XLSX)", "🔗 Đường link Google Sheet", "🧪 Dữ liệu kinh doanh mẫu"]
    )
    
    # AI Engine Settings
    st.markdown("---")
    st.subheader("🤖 Cấu hình Trí tuệ Nhân tạo")
    ai_mode = st.selectbox(
        "Chế độ AI Reasoning:",
        ["⚡ AI Phân tích Nội suy Tự động (Quy tắc & Thống kê)", "🧠 Google Gemini API Agent (Mở rộng)"]
    )
    
    gemini_key = ""
    if "Gemini" in ai_mode:
        gemini_key = st.text_input("Nhập Gemini API Key:", type="password", help="Dùng để gọi Gemini sinh phân tích và giải pháp chiến lược chuyên sâu.")
        if not gemini_key and "GEMINI_API_KEY" in os.environ:
            gemini_key = os.environ["GEMINI_API_KEY"]
            st.info("Đã nhận diện API Key từ môi trường hệ thống.")

    st.markdown("---")
    st.caption("📍 Hệ thống đang chạy trực tiếp trên: **localhost:8501**")

# ================= XỬ LÝ NHẬP DỮ LIỆU (BƯỚC 1) =================
if input_method == "📁 Tải file lên (CSV, XLSX)":
    uploaded = st.file_uploader("Chọn file CSV hoặc Excel (.xlsx, .xls) từ máy tính của bạn:", type=["csv", "xlsx", "xls"])
    if uploaded is not None:
        if st.session_state.dataset_name != uploaded.name:
            df, err = load_uploaded_file(uploaded)
            if err:
                st.error(err)
            else:
                st.session_state.raw_df = df
                st.session_state.cleaned_df = None
                st.session_state.dataset_name = uploaded.name
                st.session_state.source_type = f"File Upload ({uploaded.name.split('.')[-1].upper()})"
                st.session_state.active_step = 2
                st.success(f"Đã tải thành công file '{uploaded.name}' ({len(df)} dòng, {len(df.columns)} cột)!")

elif input_method == "🔗 Đường link Google Sheet":
    st.info("💡 **Hướng dẫn:** Đảm bảo link Google Sheet đã được mở quyền 'Bất kỳ ai có liên kết đều có thể xem' (Anyone with the link can view).")
    gsheet_url = st.text_input(
        "Dán link Google Sheet vào đây:",
        placeholder="https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit?usp=sharing"
    )
    col_g1, col_g2 = st.columns([1, 3])
    with col_g1:
        load_gsheet_btn = st.button("📥 Tải Google Sheet", type="primary")
    
    if load_gsheet_btn and gsheet_url:
        with st.spinner("Đang kết nối và tải dữ liệu từ Google Sheet..."):
            df, err = load_google_sheet(gsheet_url)
            if err:
                st.error(err)
            else:
                st.session_state.raw_df = df
                st.session_state.cleaned_df = None
                st.session_state.dataset_name = "Google_Sheet_Import"
                st.session_state.source_type = "Google Sheet"
                st.session_state.active_step = 2
                st.success(f"Đã tải dữ liệu từ Google Sheet thành công ({len(df)} dòng, {len(df.columns)} cột)!")

else: # Dữ liệu kinh doanh mẫu
    st.markdown("Chọn một trong các bộ dữ liệu mẫu thực tế để thử nghiệm ngay lập tức:")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("🛒 Dữ liệu Bán lẻ & Chuỗi Chi nhánh (CSV)"):
            path = "sample_data/retail_sales_sample.csv"
            if os.path.exists(path):
                df = pd.read_csv(path)
                st.session_state.raw_df = df
                st.session_state.cleaned_df = None
                st.session_state.dataset_name = "Retail_Sales_MultiBranch"
                st.session_state.source_type = "Sample Retail Dataset"
                st.session_state.active_step = 2
                st.success("Đã nạp bộ dữ liệu Bán lẻ thành công!")
    with col_s2:
        if st.button("📊 Dữ liệu E-commerce & Marketing (XLSX)"):
            path = "sample_data/ecommerce_sample.xlsx"
            if os.path.exists(path):
                df = pd.read_excel(path, sheet_name="Sales_Transactions")
                st.session_state.raw_df = df
                st.session_state.cleaned_df = None
                st.session_state.dataset_name = "Ecommerce_Campaign_Data"
                st.session_state.source_type = "Sample E-commerce Dataset"
                st.session_state.active_step = 2
                st.success("Đã nạp bộ dữ liệu E-commerce thành công!")

# Nếu chưa có dữ liệu nào được nạp
if st.session_state.raw_df is None:
    st.info("👉 Vui lòng tải lên file dữ liệu kinh doanh, nhập link Google Sheet hoặc bấm vào nút Dữ liệu mẫu ở trên để bắt đầu phân tích.")
    st.stop()

# ================= CÁC TABS ĐIỀU HƯỚNG QUY TRÌNH =================
tabs = st.tabs([
    "1️⃣ Dữ liệu Gốc",
    "2️⃣ Làm sạch & Chuẩn hóa",
    "3️⃣ Lưu trữ SQLite",
    "4️⃣ Phân tích Đa chiều",
    "5️⃣ Rút ra Insight",
    "6️⃣ Đề xuất Giải pháp",
    "7️⃣ Đánh giá & KPIs"
])

# ----------------- TAB 1: DỮ LIỆU GỐC -----------------
with tabs[0]:
    st.subheader(f"1. Thu thập dữ liệu: {st.session_state.dataset_name}")
    st.caption(f"Nguồn: {st.session_state.source_type}")
    
    quality_raw = analyze_raw_quality(st.session_state.raw_df)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng số dòng", f"{quality_raw['total_rows']:,}")
    m2.metric("Tổng số cột", quality_raw['total_cols'])
    m3.metric("Số ô bị khuyết (NaN)", f"{quality_raw['missing_cells']:,} ({quality_raw['missing_pct']}%)")
    m4.metric("Dòng trùng lặp (Duplicates)", f"{quality_raw['duplicate_rows']:,} ({quality_raw['duplicate_pct']}%)")
    
    st.markdown("#### Xem trước 10 dòng đầu tiên của dữ liệu thô:")
    st.dataframe(st.session_state.raw_df.head(10), use_container_width=True)
    
    if quality_raw['missing_by_col']:
        st.warning("⚠️ **Phát hiện dữ liệu khuyết thiếu ở các cột:** " + ", ".join([f"`{c}` ({info['count']} ô - {info['pct']}%)" for c, info in quality_raw['missing_by_col'].items()]))

# ----------------- TAB 2: LÀM SẠCH & CHUẨN HÓA -----------------
with tabs[1]:
    st.subheader("2. Tích hợp và Làm sạch Dữ liệu")
    st.caption("Quy trình tự động: Chuẩn hóa tên cột ➔ Loại bỏ trùng lặp ➔ Điền giá trị thiếu (Imputation) ➔ Nhận diện ngày tháng & số liệu tiền tệ.")
    
    c_opt1, c_opt2, c_opt3 = st.columns(3)
    with c_opt1:
        handle_na_option = st.selectbox(
            "Phương án xử lý ô trống (Missing values):",
            ["impute", "drop", "keep"],
            format_func=lambda x: "Điền tự động (Trung vị/Phổ biến nhất)" if x == "impute" else ("Xóa các dòng chứa NaN" if x == "drop" else "Giữ nguyên NaN")
        )
    with c_opt2:
        drop_dup = st.checkbox("Tự động xóa các dòng trùng lặp (Duplicates)", value=True)
    with c_opt3:
        std_cols = st.checkbox("Chuẩn hóa tên cột (snake_case, không dấu)", value=True)
        
    if st.button("🚀 Thực hiện Làm sạch & Chuẩn hóa ngay", type="primary"):
        with st.spinner("AI Agent đang thực hiện chuẩn hóa và làm sạch..."):
            cleaned_df, summary = clean_and_integrate_data(
                st.session_state.raw_df,
                handle_missing=handle_na_option,
                drop_duplicates=drop_dup,
                standardize_columns=std_cols,
                parse_dates=True
            )
            st.session_state.cleaned_df = cleaned_df
            st.session_state.cleaning_summary = summary
            st.session_state.active_step = 3
            st.success("Đã hoàn tất quy trình làm sạch và chuẩn hóa!")
            
    # Hiển thị kết quả làm sạch nếu đã làm sạch
    if st.session_state.cleaned_df is not None:
        sm = st.session_state.cleaning_summary
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Số dòng sau làm sạch", f"{sm['final_rows']:,}", delta=f"-{sm['removed_rows']} dòng")
        sc2.metric("Số ô NaN đã xử lý", f"{sm['missing_before']} ➔ {sm['missing_after']}")
        sc3.metric("Số dòng trùng đã xóa", sm['duplicates_removed'])
        sc4.metric("Trạng thái", "Sạch 100% & Sẵn sàng", delta="Đạt chuẩn")
        
        st.markdown("#### Nhật ký xử lý dữ liệu (Cleaning Audit Log):")
        for act in sm['actions']:
            st.markdown(f"- ✅ {act}")
            
        st.markdown("#### Bảng dữ liệu đã chuẩn hóa:")
        st.dataframe(st.session_state.cleaned_df.head(10), use_container_width=True)

# ----------------- TAB 3: LƯU TRỮ SQLITE -----------------
with tabs[2]:
    st.subheader("3. Lưu trữ Dữ liệu vào Database")
    st.caption("Dữ liệu sau khi làm sạch được tự động đẩy vào Cơ sở dữ liệu SQLite cục bộ để phục vụ truy vấn tốc độ cao.")
    
    target_df = st.session_state.cleaned_df if st.session_state.cleaned_df is not None else st.session_state.raw_df
    
    col_db1, col_db2 = st.columns([1, 2])
    with col_db1:
        if st.button("💾 Lưu dataset vào Database SQLite"):
            dataset_id, table_name = save_dataframe_to_db(
                target_df,
                st.session_state.dataset_name,
                st.session_state.source_type
            )
            st.success(f"Đã lưu thành công vào bảng: `{table_name}` (ID: {dataset_id})")
            st.session_state.active_step = 4
            
    st.markdown("#### Danh mục các bảng đã lưu trữ trong Database:")
    stored_df = list_stored_datasets()
    if not stored_df.empty:
        st.dataframe(stored_df, use_container_width=True)
        
        st.markdown("#### 🔍 Truy vấn SQL trực tiếp trên Database:")
        latest_table = stored_df.iloc[0]['table_name']
        sql_input = st.text_area("Nhập câu lệnh SQL:", value=f"SELECT * FROM {latest_table} LIMIT 5")
        if st.button("Chạy truy vấn SQL"):
            try:
                res_df = query_database(sql_input)
                st.write(f"Kết quả truy vấn ({len(res_df)} dòng):")
                st.dataframe(res_df, use_container_width=True)
            except Exception as e:
                st.error(f"Lỗi SQL: {str(e)}")
    else:
        st.info("Chưa có dataset nào được lưu trong Database. Hãy bấm nút 'Lưu dataset vào Database SQLite' ở trên.")

# ----------------- TAB 4: PHÂN TÍCH ĐA CHIỀU -----------------
with tabs[3]:
    st.subheader("4. Phân tích Dữ liệu Kinh doanh")
    st.caption("Tìm xu hướng theo chuỗi thời gian, mối quan hệ tương quan, phân khúc đóng góp và phát hiện các điểm bất thường.")
    
    df_to_analyze = st.session_state.cleaned_df if st.session_state.cleaned_df is not None else st.session_state.raw_df
    col_mapping = auto_detect_columns(df_to_analyze)
    
    # Cho phép người dùng tùy chỉnh mapping nếu muốn
    with st.expander("🛠️ Cấu hình Nhận diện Cột dữ liệu (Tự động hoặc Thủ công)"):
        mc1, mc2, mc3, mc4 = st.columns(4)
        all_cols = ["(Không chọn)"] + list(df_to_analyze.columns)
        
        def get_index(col_val):
            return all_cols.index(col_val) if col_val in all_cols else 0
            
        with mc1:
            sel_date = st.selectbox("Cột Ngày tháng:", all_cols, index=get_index(col_mapping["date_col"]))
            sel_rev = st.selectbox("Cột Doanh thu:", all_cols, index=get_index(col_mapping["revenue_col"]))
        with mc2:
            sel_prof = st.selectbox("Cột Lợi nhuận:", all_cols, index=get_index(col_mapping["profit_col"]))
            sel_cost = st.selectbox("Cột Chi phí/Giá vốn:", all_cols, index=get_index(col_mapping["cost_col"]))
        with mc3:
            sel_cat = st.selectbox("Cột Danh mục/Sản phẩm:", all_cols, index=get_index(col_mapping["category_col"]))
            sel_seg = st.selectbox("Cột Phân khúc/Chi nhánh:", all_cols, index=get_index(col_mapping["segment_col"]))
        with mc4:
            sel_chan = st.selectbox("Cột Kênh tiếp thị:", all_cols, index=get_index(col_mapping["channel_col"]))
            sel_disc = st.selectbox("Cột Chiết khấu (%):", all_cols, index=get_index(col_mapping["discount_col"]))
            
        # Cập nhật mapping
        col_mapping["date_col"] = None if sel_date == "(Không chọn)" else sel_date
        col_mapping["revenue_col"] = None if sel_rev == "(Không chọn)" else sel_rev
        col_mapping["profit_col"] = None if sel_prof == "(Không chọn)" else sel_prof
        col_mapping["cost_col"] = None if sel_cost == "(Không chọn)" else sel_cost
        col_mapping["category_col"] = None if sel_cat == "(Không chọn)" else sel_cat
        col_mapping["segment_col"] = None if sel_seg == "(Không chọn)" else sel_seg
        col_mapping["channel_col"] = None if sel_chan == "(Không chọn)" else sel_chan
        col_mapping["discount_col"] = None if sel_disc == "(Không chọn)" else sel_disc

    # 1. Tính toán KPIs
    kpis = calculate_kpis(df_to_analyze, col_mapping)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Tổng Doanh thu", f"{kpis['total_revenue']:,.0f} đ" if kpis['total_revenue'] > 0 else "N/A")
    k2.metric("Tổng Lợi nhuận", f"{kpis['total_profit']:,.0f} đ" if kpis['total_profit'] != 0 else "N/A")
    k3.metric("Biên Lợi nhuận Gộp", f"{kpis['profit_margin_pct']}%" if kpis['profit_margin_pct'] > 0 else "N/A")
    k4.metric("Giá trị Đơn TB (AOV)", f"{kpis['aov']:,.0f} đ" if kpis['aov'] > 0 else f"{kpis['total_records']} đơn")

    st.markdown("---")
    
    # 2. Xu hướng theo thời gian (Trend Analysis)
    st.markdown("#### 📈 Phân tích Xu hướng Doanh thu & Tăng trưởng theo thời gian:")
    trend_df = analyze_trends(df_to_analyze, col_mapping)
    if trend_df is not None:
        rev_c = col_mapping["revenue_col"]
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(x=trend_df['period'], y=trend_df[rev_c], name="Doanh thu thực tế", marker_color="#93c5fd"))
        fig_trend.add_trace(go.Scatter(x=trend_df['period'], y=trend_df['revenue_ma7'], mode='lines', name="Đường TB động (MA 7 ngày)", line=dict(color="#1d4ed8", width=3)))
        fig_trend.update_layout(
            title="Biến động Doanh thu theo chuỗi thời gian",
            xaxis_title="Thời gian",
            yaxis_title="Doanh thu",
            hovermode="x unified",
            height=380
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Chưa thể vẽ đồ thị xu hướng vì dữ liệu thiếu cột Ngày tháng hoặc Doanh thu định dạng số.")

    # 3. Phân bổ cơ cấu đóng góp (Breakdowns)
    st.markdown("#### 📊 Cơ cấu Doanh thu & Lợi nhuận theo Phân khúc:")
    breakdowns = analyze_breakdowns(df_to_analyze, col_mapping)
    if breakdowns:
        b_tabs = st.tabs(list(breakdowns.keys()))
        for idx, (b_name, b_df) in enumerate(breakdowns.items()):
            with b_tabs[idx]:
                col_b1, col_b2 = st.columns([1, 1])
                with col_b1:
                    fig_pie = px.pie(b_df, names=b_name, values="Revenue", title=f"Tỷ trọng Doanh thu theo {b_name}", hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)
                with col_b2:
                    if "Profit" in b_df.columns:
                        fig_bar = px.bar(b_df, x=b_name, y=["Revenue", "Profit"], barmode="group", title=f"So sánh Doanh thu & Lợi nhuận theo {b_name}")
                        st.plotly_chart(fig_bar, use_container_width=True)
                    else:
                        fig_bar = px.bar(b_df, x=b_name, y="Revenue", title=f"Doanh thu theo {b_name}")
                        st.plotly_chart(fig_bar, use_container_width=True)
                st.dataframe(b_df, use_container_width=True)
    else:
        st.info("Không tìm thấy cột phân loại (Category/Branch/Channel) để phân tích cơ cấu.")

    # 4. Phát hiện Bất thường & Nguy cơ (Anomalies)
    st.markdown("#### 🚨 Phát hiện Bất thường & Rủi ro Vận hành (Anomaly Detection):")
    anomalies = detect_anomalies(df_to_analyze, col_mapping)
    if anomalies:
        for a in anomalies:
            color = "#fee2e2" if a["severity"] == "HIGH" else "#fef3c7"
            border = "#ef4444" if a["severity"] == "HIGH" else "#f59e0b"
            st.markdown(f"""
            <div style="background-color: {color}; border-left: 5px solid {border}; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                <div style="font-weight: 700; color: #1f2937;">{a['type']} <span style="font-size: 11px; padding: 2px 6px; background: white; border-radius: 4px;">{a['severity']}</span></div>
                <div style="font-size: 13px; margin-top: 4px; color: #374151;">{a['description']}</div>
                <div style="font-size: 12px; font-weight: 600; margin-top: 4px; color: #111827;">Tác động: {a['impact']} ({a['metric']})</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ Chưa phát hiện bất thường nghiêm trọng nào trong dữ liệu kinh doanh hiện tại.")

    # 5. Ma trận Tương quan (Correlation)
    corr_df = calculate_correlations(df_to_analyze)
    if corr_df is not None:
        with st.expander("🔗 Xem Ma trận Tương quan giữa các biến số định lượng"):
            fig_corr = px.imshow(corr_df, text_auto=True, aspect="auto", color_continuous_scale="Blues", title="Correlation Heatmap")
            st.plotly_chart(fig_corr, use_container_width=True)

# ----------------- TAB 5: RÚT RA INSIGHT -----------------
with tabs[4]:
    st.subheader("5. Rút ra Insight & Nguyên nhân Cốt lõi của Vấn đề")
    st.caption("AI Agent phân tích sâu để tìm ra đâu là điểm nghẽn kìm hãm doanh nghiệp và nguyên nhân thực sự đằng sau các con số.")
    
    df_to_analyze = st.session_state.cleaned_df if st.session_state.cleaned_df is not None else st.session_state.raw_df
    col_mapping = auto_detect_columns(df_to_analyze)
    kpis = calculate_kpis(df_to_analyze, col_mapping)
    breakdowns = analyze_breakdowns(df_to_analyze, col_mapping)
    anomalies = detect_anomalies(df_to_analyze, col_mapping)
    trend_df = analyze_trends(df_to_analyze, col_mapping)
    
    # 1. Trích xuất Rule-Based Insights
    rule_insights = extract_rule_based_insights(kpis, breakdowns, anomalies, trend_df)
    
    st.markdown("#### 💡 Các Insight Chiến Lược Cốt Lõi Được Phát Hiện:")
    for ins in rule_insights:
        card_type = ins["importance"].lower()
        if card_type not in ["critical", "warning", "positive"]:
            card_type = "warning"
            
        st.markdown(f"""
        <div class="insight-card {card_type}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 700; font-size: 16px;">{ins['icon']} {ins['title']}</span>
                <span style="font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; background: #f1f5f9;">{ins['tag']}</span>
            </div>
            <div style="margin-top: 8px; font-size: 14px; color: #1e293b;">
                <strong>Phát hiện:</strong> {ins['finding']}
            </div>
            <div style="margin-top: 6px; font-size: 14px; color: #991b1b; background: #fff1f2; padding: 6px 10px; border-radius: 4px;">
                <strong>Nguyên nhân gốc rễ (Root Cause):</strong> {ins['root_cause']}
            </div>
            <div style="margin-top: 6px; font-size: 12px; color: #475569;">
                <em>Bằng chứng dữ liệu:</em> {ins['evidence']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    # 2. Nếu có cấu hình LLM (Gemini)
    if "Gemini" in ai_mode:
        st.markdown("---")
        st.markdown("#### 🧠 Báo cáo Phân tích từ Trợ lý Giám đốc Chiến lược (Gemini AI Agent):")
        if gemini_key:
            if st.button("🔮 Kích hoạt Gemini Agent phân tích Insight chuyên sâu"):
                with st.spinner("AI Agent đang tổng hợp mô hình MECE và viết báo cáo chiến lược..."):
                    summary_text = ""
                    for k, b_df in breakdowns.items():
                        summary_text += f"\n--- {k} ---\n" + b_df.head(5).to_string()
                    llm_res = generate_llm_insights(gemini_key, kpis, summary_text, anomalies, rule_insights)
                    st.markdown(llm_res)
        else:
            st.warning("Vui lòng nhập Gemini API Key ở thanh Sidebar bên trái để sử dụng tính năng Generative AI Agent.")

# ----------------- TAB 6: ĐỀ XUẤT & TRIỂN KHAI GIẢI PHÁP -----------------
with tabs[5]:
    st.subheader("6. Đề Xuất & Triển Khai Giải Pháp Kinh Doanh")
    st.caption("Chuyển hóa Insights thành Kế hoạch Hành động cụ thể (Actionable Playbook) theo Ma trận Tác động - Nỗ lực (Impact/Effort).")
    
    solutions = generate_business_solutions(rule_insights, kpis, anomalies)
    
    col_qw, col_sp = st.columns(2)
    with col_qw:
        st.markdown("### ⚡ Quick Wins (Tác động Cao - Làm ngay)")
        st.caption("Các hành động can thiệp tức thì trong vòng 1-2 tuần đầu để chặn đứng thất thoát.")
        for item in solutions["quick_wins"]:
            st.markdown(f"""
            <div class="solution-card" style="border-left: 5px solid #10b981;">
                <div style="font-weight: 700; color: #065f46; font-size: 15px;">{item['title']}</div>
                <div style="font-size: 12px; margin: 4px 0; color: #047857;">⏱️ Thời gian: <b>{item['timeline']}</b> | 🎯 Hiệu quả kỳ vọng: <b>{item['impact']}</b></div>
                <div style="font-size: 13px; color: #374151; margin-top: 6px;">{item['details']}</div>
                <div style="font-size: 11px; color: #6b7280; margin-top: 4px;">Độ phức tạp: {item['effort']}</div>
            </div>
            """, unsafe_allow_html=True)
            
    with col_sp:
        st.markdown("### 🎯 Dự Án Chiến Lược (Strategic Bets)")
        st.caption("Các giải pháp tái cấu trúc trung và dài hạn để tạo đà tăng trưởng bền vững.")
        for item in solutions["strategic_projects"]:
            st.markdown(f"""
            <div class="solution-card" style="border-left: 5px solid #3b82f6;">
                <div style="font-weight: 700; color: #1e40af; font-size: 15px;">{item['title']}</div>
                <div style="font-size: 12px; margin: 4px 0; color: #2563eb;">⏱️ Thời gian: <b>{item['timeline']}</b> | 🎯 Hiệu quả kỳ vọng: <b>{item['impact']}</b></div>
                <div style="font-size: 13px; color: #374151; margin-top: 6px;">{item['details']}</div>
                <div style="font-size: 11px; color: #6b7280; margin-top: 4px;">Độ phức tạp: {item['effort']}</div>
            </div>
            """, unsafe_allow_html=True)

    if solutions["operational_fixes"]:
        st.markdown("### 🛠️ Cải Tiến Vận Hành & Chuỗi Cung Ứng")
        for item in solutions["operational_fixes"]:
            st.markdown(f"""
            <div class="solution-card" style="border-left: 5px solid #f59e0b;">
                <div style="font-weight: 700; color: #92400e; font-size: 15px;">{item['title']}</div>
                <div style="font-size: 12px; margin: 4px 0; color: #b45309;">⏱️ Thời gian: <b>{item['timeline']}</b> | 🎯 Hiệu quả kỳ vọng: <b>{item['impact']}</b></div>
                <div style="font-size: 13px; color: #374151; margin-top: 6px;">{item['details']}</div>
            </div>
            """, unsafe_allow_html=True)
            
    # Hỗ trợ LLM Solutions
    if "Gemini" in ai_mode and gemini_key:
        st.markdown("---")
        if st.button("📝 Yêu cầu Gemini AI lập Kế hoạch Hành động & Ma trận RACI chi tiết"):
            with st.spinner("AI đang soạn thảo Kế hoạch hành động chi tiết..."):
                ins_str = "\n".join([f"- {i['title']}: {i['root_cause']}" for i in rule_insights])
                sol_llm = generate_llm_solutions(gemini_key, ins_str, kpis)
                st.markdown(sol_llm)

# ----------------- TAB 7: ĐÁNH GIÁ & KPIS -----------------
with tabs[6]:
    st.subheader("7. Đánh Giá Kết Quả & Khung Đo Lường KPIs")
    st.caption("Thiết lập hệ thống chỉ số đo lường hiệu quả (OKRs/KPIs) và lịch trình đánh giá, điều chỉnh giải pháp định kỳ.")
    
    eval_framework = build_evaluation_framework(kpis, anomalies)
    
    # Bảng mục tiêu KPI
    st.markdown("#### 🎯 Bảng Chỉ Số Mục Tiêu Cải Thiện (Target KPIs & OKRs):")
    st.table(pd.DataFrame(eval_framework["kpi_targets"]))
    
    st.markdown("---")
    
    col_ev1, col_ev2 = st.columns(2)
    with col_ev1:
        st.markdown("#### 🗓️ Lịch Trình Đánh Giá & Kiểm Soát (Review Cadence):")
        for sc in eval_framework["review_schedule"]:
            st.markdown(f"**{sc['phase']}**")
            st.caption(f"Trọng tâm: {sc['focus']}")
            for t in sc["tasks"]:
                st.markdown(f"- 📌 {t}")
            st.markdown("<br>", unsafe_allow_html=True)
            
    with col_ev2:
        st.markdown("#### ⚠️ Kịch Bản Dự Phòng & Điều Chỉnh Khi Có Rủi Ro:")
        for r in eval_framework["risk_contingencies"]:
            st.markdown(f"""
            <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px; margin-bottom: 8px;">
                <div style="font-weight: 600; color: #b91c1c; font-size: 13px;">🚨 {r['condition']}</div>
                <div style="font-size: 13px; color: #1e293b; margin-top: 4px;">➔ <b>Hành động điều chỉnh:</b> {r['action']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    # Export Báo cáo Tổng thể
    st.markdown("#### 📥 Xuất Toàn Bộ Báo Cáo Chẩn Đoán & Giải Pháp Kinh Doanh:")
    
    def generate_report_markdown():
        report = f"""# BÁO CÁO PHÂN TÍCH KINH DOANH & ĐỀ XUẤT CHIẾN LƯỢC
Tên Dataset: {st.session_state.dataset_name} | Nguồn: {st.session_state.source_type}

## 1. CHỈ SỐ KINH DOANH CHỦ CHỐT (CORE KPIS)
- Tổng Doanh thu: {kpis.get('total_revenue', 0):,.0f} đ
- Tổng Lợi nhuận: {kpis.get('total_profit', 0):,.0f} đ
- Tỷ suất Lợi nhuận Gộp: {kpis.get('profit_margin_pct', 0)}%
- Giá trị Đơn hàng Trung bình (AOV): {kpis.get('aov', 0):,.0f} đ

## 2. CÁC INSIGHT VÀ NGUYÊN NHÂN CỐT LÕI
"""
        for i, ins in enumerate(rule_insights, 1):
            report += f"\n### {i}. {ins['title']}\n"
            report += f"- **Phát hiện:** {ins['finding']}\n"
            report += f"- **Nguyên nhân gốc rễ:** {ins['root_cause']}\n"
            report += f"- **Bằng chứng dữ liệu:** {ins['evidence']}\n"
            
        report += "\n## 3. ĐỀ XUẤT GIẢI PHÁP & KẾ HOẠCH HÀNH ĐỘNG\n"
        report += "\n### Quick Wins (Triển khai ngay):\n"
        for q in solutions.get("quick_wins", []):
            report += f"- **{q['title']}**: {q['details']} (Kỳ vọng: {q['impact']})\n"
            
        report += "\n### Dự án Chiến lược (Dài hạn):\n"
        for s in solutions.get("strategic_projects", []):
            report += f"- **{s['title']}**: {s['details']} (Kỳ vọng: {s['impact']})\n"
            
        report += "\n## 4. KHUNG ĐO LƯỜNG & ĐÁNH GIÁ (KPIS)\n"
        for k in eval_framework.get("kpi_targets", []):
            report += f"- **{k['metric']}**: Hiện tại `{k['current']}` ➔ Mục tiêu `{k['target']}` (Đơn vị đo: {k['frequency']})\n"
            
        return report

    report_md = generate_report_markdown()
    st.download_button(
        label="📄 Tải Xuống Báo Cáo Chiến Lược (Markdown .md)",
        data=report_md,
        file_name=f"Business_Strategy_Report_{pd.Timestamp.now().strftime('%Y%m%d')}.md",
        mime="text/markdown"
    )

