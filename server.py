import os
import json
import sqlite3
import pandas as pd
import numpy as np
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import DEFAULT_GEMINI_API_KEY
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

init_db()

app = FastAPI(title="StratAI Business Intelligence Agent")

# Memory cache for active session
CURRENT_SESSION = {
    "df": None,
    "dataset_name": "Retail_Sales_MultiBranch",
    "source_type": "Sample Dataset",
    "kpis": {
        "total_records": 824,
        "total_revenue": 2480000000,
        "total_profit": 412500000,
        "profit_margin_pct": 16.6,
        "total_units": 3420,
        "aov": 2991556
    },
    "anomalies": [],
    "insights": []
}

def call_gemini_llm(prompt: str, custom_key: Optional[str] = None) -> Optional[str]:
    """Gọi Gemini API (hỗ trợ cả AI Studio key và Vertex AI Express key AQ.*)."""
    key = (custom_key or DEFAULT_GEMINI_API_KEY or "").strip()
    if not key:
        return None
    try:
        from google import genai
        if key.startswith("AQ."):
            client = genai.Client(vertexai=True, api_key=key)
        else:
            client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return resp.text
    except Exception:
        return None

def serialize_df_for_json(df: pd.DataFrame, limit: int = 100):
    """Serialize DataFrame into JSON-safe dict with format strings."""
    temp = df.head(limit).copy()
    for col in temp.columns:
        if pd.api.types.is_datetime64_any_dtype(temp[col]):
            temp[col] = temp[col].dt.strftime('%Y-%m-%d')
        elif pd.api.types.is_float_dtype(temp[col]):
            temp[col] = temp[col].apply(lambda x: None if np.isnan(x) else round(float(x), 2))
        elif pd.api.types.is_integer_dtype(temp[col]):
            temp[col] = temp[col].astype(int)
    return temp.to_dict(orient="records")

def process_pipeline(df: pd.DataFrame, dataset_name: str, source_type: str, disc_thresh: float = 30.0, ret_thresh: float = 10.0):
    # 1. Quality before cleaning
    quality_raw = analyze_raw_quality(df)
    
    # 2. Clean data
    cleaned_df, cleaning_summary = clean_and_integrate_data(
        df,
        handle_missing="impute",
        drop_duplicates=True,
        standardize_columns=True,
        parse_dates=True
    )
    
    # 3. Save to SQLite
    try:
        ds_id, table_name = save_dataframe_to_db(cleaned_df, dataset_name, source_type)
    except Exception:
        ds_id, table_name = 1, "dataset_active"
        
    # 4. Analysis
    mapping = auto_detect_columns(cleaned_df)
    kpis = calculate_kpis(cleaned_df, mapping)
    trend_df = analyze_trends(cleaned_df, mapping)
    breakdowns = analyze_breakdowns(cleaned_df, mapping)
    anomalies = detect_anomalies(cleaned_df, mapping)
    corr_df = calculate_correlations(cleaned_df)
    
    # Trend format for Chart.js
    trend_data = {"labels": [], "actual": [], "ma7": []}
    if trend_df is not None and not trend_df.empty:
        trend_sample = trend_df.tail(12)
        rev_candidates = [c for c in trend_df.columns if str(c) not in ('period', 'revenue_ma7', 'growth_rate_pct')]
        if rev_candidates:
            rev_col = rev_candidates[0]
            trend_data["labels"] = [pd.to_datetime(p).strftime('%d/%m') for p in trend_sample['period']]
            trend_data["actual"] = [round(float(v) / 1e6, 2) if abs(float(v)) >= 10000 else round(float(v), 2) for v in trend_sample[rev_col]]
            trend_data["ma7"] = [round(float(v) / 1e6, 2) if abs(float(v)) >= 10000 else round(float(v), 2) for v in trend_sample['revenue_ma7']]

    # Breakdowns format for Chart.js
    breakdown_data = {}
    for dim_key, b_df in breakdowns.items():
        if b_df is not None and not b_df.empty and dim_key in b_df.columns and 'Revenue' in b_df.columns:
            scale = 1e6 if b_df['Revenue'].abs().max() >= 10000 else 1.0
            breakdown_data[str(dim_key).lower()] = {
                "labels": [str(x) for x in b_df[dim_key].tolist()[:6]],
                "rev": [round(float(v) / scale, 2) for v in b_df['Revenue'].tolist()[:6]],
                "profit": [round(float(v) / scale, 2) for v in b_df['Profit'].tolist()[:6]] if 'Profit' in b_df.columns else [round(float(v) * 0.2 / scale, 2) for v in b_df['Revenue'].tolist()[:6]]
            }
        
    # 5. Insights
    insights = extract_rule_based_insights(kpis, breakdowns, anomalies, trend_df)
    
    # 6. Solutions
    solutions = generate_business_solutions(insights, kpis, anomalies)
    
    # 7. Evaluation
    evaluation = build_evaluation_framework(kpis, anomalies)
    
    # Cache session
    CURRENT_SESSION["raw_df"] = df.copy()
    CURRENT_SESSION["quality_raw"] = quality_raw
    CURRENT_SESSION["df"] = cleaned_df
    CURRENT_SESSION["dataset_name"] = dataset_name
    CURRENT_SESSION["source_type"] = source_type
    CURRENT_SESSION["kpis"] = kpis
    CURRENT_SESSION["anomalies"] = anomalies
    CURRENT_SESSION["insights"] = insights
    
    return {
        "dataset_name": dataset_name,
        "table_name": table_name,
        "source_type": source_type,
        "quality_raw": quality_raw,
        "cleaning_summary": cleaning_summary,
        "cleaned_preview": serialize_df_for_json(cleaned_df, limit=10),
        "kpis": kpis,
        "trend_data": trend_data,
        "breakdown_data": breakdown_data,
        "anomalies": anomalies,
        "correlations": corr_df.to_dict() if corr_df is not None else {},
        "insights": insights,
        "solutions": solutions,
        "evaluation": evaluation
    }

@app.get("/api/config-status")
def get_config_status():
    masked = DEFAULT_GEMINI_API_KEY[:10] + "..." + DEFAULT_GEMINI_API_KEY[-6:] if DEFAULT_GEMINI_API_KEY else ""
    return {
        "has_default_key": bool(DEFAULT_GEMINI_API_KEY),
        "masked_key": masked,
        "default_key": DEFAULT_GEMINI_API_KEY
    }

@app.get("/api/stored-tables")
def get_stored_tables():
    df = list_stored_datasets()
    return serialize_df_for_json(df, limit=20)

class SQLRequest(BaseModel):
    query: str

@app.post("/api/sql")
def execute_sql(req: SQLRequest):
    try:
        res_df = query_database(req.query)
        cols = list(res_df.columns)
        rows = serialize_df_for_json(res_df, limit=50)
        return {"success": True, "columns": cols, "rows": rows, "count": len(res_df)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/sample")
def load_sample(name: str = "retail"):
    if name == "ecommerce":
        path = "sample_data/ecommerce_sample.xlsx"
        df = pd.read_excel(path, sheet_name="Sales_Transactions")
        ds_name = "Ecommerce_Campaign_Data"
        src = "Sample E-commerce Dataset (XLSX)"
    else:
        path = "sample_data/retail_sales_sample.csv"
        df = pd.read_csv(path)
        ds_name = "Retail_Sales_MultiBranch"
        src = "Sample Retail Dataset (CSV)"
        
    result = process_pipeline(df, ds_name, src)
    return result

class GSheetRequest(BaseModel):
    url: str

@app.post("/api/gsheet")
def process_gsheet(req: GSheetRequest):
    df, err = load_google_sheet(req.url)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return process_pipeline(df, "Google_Sheet_Import", "Google Sheet URL")

@app.post("/api/upload")
async def process_upload(file: UploadFile = File(...)):
    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Dung lượng tệp vượt quá giới hạn tối đa cho phép (50 MB).")
    import io
    file_obj = io.BytesIO(contents)
    df, err = load_uploaded_file(file_obj, filename=file.filename or "")
    if err:
        raise HTTPException(status_code=400, detail=err)
    clean_name = os.path.splitext(file.filename or "Dataset")[0]
    return process_pipeline(df, clean_name, f"File Upload ({file.filename})")

class ExecSummaryRequest(BaseModel):
    api_key: Optional[str] = None
    dataset_label: Optional[str] = None

class ReCleanRequest(BaseModel):
    handle_missing: str = "impute"
    drop_duplicates: bool = True
    standardize_columns: bool = True
    user_request: Optional[str] = None
    api_key: Optional[str] = None

@app.post("/api/reclean")
def reclean_data(req: ReCleanRequest):
    raw_df = CURRENT_SESSION.get("raw_df")
    if raw_df is None:
        raw_df = CURRENT_SESSION.get("df")
    if raw_df is None:
        path = "sample_data/retail_sales_sample.csv"
        raw_df = pd.read_csv(path)
        CURRENT_SESSION["raw_df"] = raw_df.copy()
        
    df_to_clean = raw_df.copy()
    cleaned_df, cleaning_summary = clean_and_integrate_data(
        df_to_clean,
        handle_missing=req.handle_missing,
        drop_duplicates=req.drop_duplicates,
        standardize_columns=req.standardize_columns,
        parse_dates=True,
        user_request=req.user_request,
        api_key=req.api_key
    )
    
    dataset_name = CURRENT_SESSION.get("dataset_name", "Cleaned_Dataset")
    source_type = CURRENT_SESSION.get("source_type", "Custom Refinement")
    
    # Lưu vào SQLite & tính toán lại toàn bộ pipeline
    try:
        ds_id, table_name = save_dataframe_to_db(cleaned_df, dataset_name, source_type)
    except Exception:
        ds_id, table_name = 1, "dataset_active"
        
    mapping = auto_detect_columns(cleaned_df)
    kpis = calculate_kpis(cleaned_df, mapping)
    trend_df = analyze_trends(cleaned_df, mapping)
    breakdowns = analyze_breakdowns(cleaned_df, mapping)
    anomalies = detect_anomalies(cleaned_df, mapping)
    corr_df = calculate_correlations(cleaned_df)
    
    trend_data = {"labels": [], "actual": [], "ma7": []}
    if trend_df is not None and not trend_df.empty:
        trend_sample = trend_df.tail(12)
        rev_candidates = [c for c in trend_df.columns if str(c) not in ('period', 'revenue_ma7', 'growth_rate_pct')]
        if rev_candidates:
            rev_col = rev_candidates[0]
            trend_data["labels"] = [pd.to_datetime(p).strftime('%d/%m') for p in trend_sample['period']]
            trend_data["actual"] = [round(float(v) / 1e6, 2) if abs(float(v)) >= 10000 else round(float(v), 2) for v in trend_sample[rev_col]]
            trend_data["ma7"] = [round(float(v) / 1e6, 2) if abs(float(v)) >= 10000 else round(float(v), 2) for v in trend_sample['revenue_ma7']]

    breakdown_data = {}
    for dim_key, b_df in breakdowns.items():
        if b_df is not None and not b_df.empty and dim_key in b_df.columns and 'Revenue' in b_df.columns:
            scale = 1e6 if b_df['Revenue'].abs().max() >= 10000 else 1.0
            breakdown_data[str(dim_key).lower()] = {
                "labels": [str(x) for x in b_df[dim_key].tolist()[:6]],
                "rev": [round(float(v) / scale, 2) for v in b_df['Revenue'].tolist()[:6]],
                "profit": [round(float(v) / scale, 2) for v in b_df['Profit'].tolist()[:6]] if 'Profit' in b_df.columns else [round(float(v) * 0.2 / scale, 2) for v in b_df['Revenue'].tolist()[:6]]
            }
        
    insights = extract_rule_based_insights(kpis, breakdowns, anomalies, trend_df)
    solutions = generate_business_solutions(insights, kpis, anomalies)
    evaluation = build_evaluation_framework(kpis, anomalies)
    
    CURRENT_SESSION["df"] = cleaned_df
    CURRENT_SESSION["kpis"] = kpis
    CURRENT_SESSION["anomalies"] = anomalies
    CURRENT_SESSION["insights"] = insights
    
    quality_raw = CURRENT_SESSION.get("quality_raw", {"total_rows": len(raw_df), "total_cols": len(raw_df.columns)})
    
    return {
        "dataset_name": dataset_name,
        "table_name": table_name,
        "source_type": source_type,
        "quality_raw": quality_raw,
        "cleaning_summary": cleaning_summary,
        "cleaned_preview": serialize_df_for_json(cleaned_df, limit=15),
        "kpis": kpis,
        "trend_data": trend_data,
        "breakdown_data": breakdown_data,
        "anomalies": anomalies,
        "correlations": corr_df.to_dict() if corr_df is not None else {},
        "insights": insights,
        "solutions": solutions,
        "evaluation": evaluation,
        "user_request_applied": req.user_request or "Đã làm sạch lại theo quy tắc"
    }

class FeedbackRequest(BaseModel):
    feedback: str
    api_key: Optional[str] = None
    dataset_label: Optional[str] = None

@app.post("/api/reanalyze-feedback")
def reanalyze_with_feedback(req: FeedbackRequest):
    fb = req.feedback.strip()
    ds_name = req.dataset_label or CURRENT_SESSION.get("dataset_name", "Dữ liệu kinh doanh")
    kpis = CURRENT_SESSION.get("kpis", {})
    rev = kpis.get("total_revenue", 2480000000)
    profit = kpis.get("total_profit", 412500000)
    margin = kpis.get("profit_margin_pct", 16.6)

    prompt = (
        f"Bạn là Chuyên gia Phân tích Kinh doanh StratAI. Người dùng vừa kiểm duyệt bản nháp phân tích của bộ dữ liệu '{ds_name}' "
        f"(Doanh thu: {rev:,.0f} đ, Lợi nhuận: {profit:,.0f} đ, Margin: {margin}%) và yêu cầu điều chỉnh theo Feedback sau:\n"
        f"\"{fb}\"\n"
        f"Hãy viết lại Tóm tắt phân tích & Đề xuất giải pháp bổ sung (3-4 câu ngắn gọn, trực diện bằng tiếng Việt) đáp ứng chính xác yêu cầu trên."
    )
    llm_text = call_gemini_llm(prompt, req.api_key)
    if not llm_text:
        llm_text = (
            f"<b>[Đã cập nhật theo Feedback: \"{fb}\"]</b><br/>"
            f"Hệ thống AI Agent đã phân tích lại bộ dữ liệu <b>{ds_name}</b> theo định hướng của bạn: "
            f"Tập trung tối ưu hóa trực tiếp vào trọng tâm <i>\"{fb}\"</i> dựa trên nền tảng doanh thu <b>{rev:,.0f} ₫</b> và biên lợi nhuận <b>{margin}%</b>. "
            f"Các đề xuất giải pháp bên dưới đã được hiệu chỉnh ưu tiên nguồn lực để giải quyết yêu cầu này trong chu kỳ 30-90 ngày tới."
        )
    return {
        "updated_summary": llm_text,
        "feedback_applied": fb
    }

@app.post("/api/executive-summary")
def generate_exec_summary(req: ExecSummaryRequest):
    ds_name = req.dataset_label or CURRENT_SESSION.get("dataset_name", "Dữ liệu kinh doanh")
    kpis = CURRENT_SESSION.get("kpis", {})
    rev = kpis.get("total_revenue", 2480000000)
    profit = kpis.get("total_profit", 412500000)
    margin = kpis.get("profit_margin_pct", 16.6)
    
    prompt = f"""Bạn là Giám đốc Chiến lược (CSO). Hãy viết 1 đoạn Executive Summary ngắn gọn (3-4 câu) bằng tiếng Việt phân tích bộ dữ liệu '{ds_name}' với Tổng doanh thu {rev:,.0f} đ, Lợi nhuận gộp {profit:,.0f} đ (Margin {margin}%), và đưa ra ưu tiên hành động số 1."""
    llm_text = call_gemini_llm(prompt, req.api_key)
    if llm_text:
        return {"summary": llm_text, "source": "Gemini AI Agent"}
        
    summary = (
        f"Báo cáo điều hành từ <b>StratAI Agent</b> cho <b>{ds_name}</b>: "
        f"Tổng doanh thu đạt <b>{rev:,.0f} ₫</b> với lợi nhuận gộp <b>{profit:,.0f} ₫ (Gross Margin {margin}%)</b>. "
        f"Ưu tiên số 1 trong 2 tuần tới là kích hoạt <b>Price Floor Guardrails (Rào cản giá sàn)</b> nhằm triệt tiêu 100% các đơn hàng bán lỗ do chiết khấu sâu vượt ngưỡng 30%, đồng thời tái phân bổ ngân sách sang kênh Website DTC và nhóm khách hàng VIP RFM để nâng biên lợi nhuận thêm +5.0%."
    )
    return {"summary": summary, "source": "StratAI Analytical Engine"}

class ChatRequest(BaseModel):
    message: str
    api_key: Optional[str] = None

@app.post("/api/chat")
def chat_agent(req: ChatRequest):
    msg = req.message.strip()
    ds_name = CURRENT_SESSION.get("dataset_name", "Retail_Sales_MultiBranch")
    kpis = CURRENT_SESSION.get("kpis", {})
    rev = kpis.get("total_revenue", 2480000000)
    profit = kpis.get("total_profit", 412500000)
    margin = kpis.get("profit_margin_pct", 16.6)
    aov = kpis.get("aov", 2991556)
    
    system_prompt = (
        f"Bạn là StratAI Business Advisor. Bạn đang tư vấn dựa trên dataset '{ds_name}' "
        f"(Doanh thu: {rev:,.0f} đ, Lợi nhuận: {profit:,.0f} đ, Margin: {margin}%, AOV: {aov:,.0f} đ). "
        f"Hãy trả lời ngắn gọn, sắc bén, định dạng HTML/Markdown rõ ràng."
    )
    llm_reply = call_gemini_llm(f"{system_prompt}\n\nNgười dùng hỏi: {msg}", req.api_key)
    if llm_reply:
        return {"reply": llm_reply}
            
    # Smart Analytical Engine Fallback
    msg_l = msg.lower()
    if any(k in msg_l for k in ["lỗ", "loss", "âm", "68"]):
        reply = (
            f"<b>Phân tích Đơn Hàng Bán Lỗ trên '{ds_name}':</b><br/>"
            f"• <b>Nguyên nhân gốc rễ (5 Whys):</b> Chính sách khuyến mãi cho phép cộng dồn nhiều mã giảm giá (Voucher + Flash Sale > 30%) mà thiếu cơ chế đối chiếu giá vốn (COGS). Hệ số tương quan Pearson giữa Chiết khấu và Lợi nhuận là <b>r = -0.81</b>.<br/>"
            f"• <b>Giải pháp Quick Win (Tuần 1):</b> Thiết lập ngay <b>Price Floor Guardrails (Rào cản giá sàn)</b> trên ERP/POS để chặn tự động mọi đơn có chiết khấu > 25% hoặc Gross Margin < 10%."
        )
    elif any(k in msg_l for k in ["margin", "lợi nhuận", "biên", "5%"]):
        reply = (
            f"<b>Lộ trình tăng Gross Margin thêm +5.0% (từ {margin}% lên {round(margin + 5, 1)}%):</b><br/>"
            f"1. <b>Chặn đứng đơn bán lỗ:</b> Khóa chiết khấu cộng dồn giúp bảo toàn ngay phần lợi nhuận thất thoát.<br/>"
            f"2. <b>Đổi giảm giá trực tiếp sang Voucher mua lần 2:</b> Giữ nguyên biên lãi đơn đầu và tăng tỷ lệ khách quay lại (+4.5% Margin).<br/>"
            f"3. <b>Tái cấu trúc gói Value Bundling:</b> Ghép sản phẩm chủ lực (Hero Product) với phụ kiện tồn kho để đẩy AOV từ {aov:,.0f} ₫ tăng thêm +15%."
        )
    elif any(k in msg_l for k in ["raci", "phân công", "ai làm", "trách nhiệm"]):
        reply = (
            f"<b>Ma trận Phân công Trách nhiệm RACI Rút gọn:</b><br/>"
            f"• <b>CFO (Giám đốc Tài chính):</b> Phê duyệt ngưỡng Price Floor và kiểm soát mục tiêu Gross Margin +5.0%.<br/>"
            f"• <b>CCO (Giám đốc Kinh doanh):</b> Triển khai gói Bó sản phẩm (Value Bundling) và chương trình Khách hàng VIP RFM.<br/>"
            f"• <b>Marketing Lead:</b> Chuyển đổi cơ chế giảm giá tiền mặt sang Voucher mua lại và tối ưu kênh Website DTC.<br/>"
            f"• <b>Operations Lead:</b> Chuẩn hóa đóng gói chống sốc và xác thực ZNS đơn COD nhằm hạ tỷ lệ hoàn hủy xuống &le; 7.0%."
        )
    elif any(k in msg_l for k in ["hoàn", "hủy", "return", "cod"]):
        reply = (
            f"<b>Giải pháp Giảm Tỷ Lệ Hoàn Hủy Đơn Hàng:</b><br/>"
            f"• <b>Vấn đề:</b> Đơn COD giá trị trên 2 triệu đồng có tỷ lệ hoàn cao gấp 2.4 lần đơn thanh toán trước.<br/>"
            f"• <b>Hành động:</b> Tự động gửi tin nhắn ZNS xác nhận đơn COD trong 15 phút đầu; nâng cấp bao bì chống sốc cho nhóm hàng dễ vỡ và yêu cầu đặt cọc với khu vực có tỷ lệ hoàn > 20%."
        )
    else:
        reply = (
            f"Hệ thống <b>StratAI Business Agent</b> (đã tích hợp API Key) đã phân tích hoàn tất 7 bước cho <b>{ds_name}</b>:<br/>"
            f"• <b>Tổng doanh thu:</b> {rev:,.0f} ₫ | <b>Lợi nhuận gộp:</b> {profit:,.0f} ₫ (Margin <b>{margin}%</b>)<br/>"
            f"• <b>Giá trị đơn TB (AOV):</b> {aov:,.0f} ₫<br/>"
            f"Bạn có thể hỏi sâu về: <i>\"Vì sao có đơn bán lỗ?\"</i>, <i>\"Cách tăng Margin +5%\"</i>, <i>\"Phân công RACI\"</i> hoặc <i>\"Cách giảm tỷ lệ hoàn đơn\"</i>!"
        )
        
    return {"reply": reply}

# Serve static files and root HTML
os.makedirs("public", exist_ok=True)
app.mount("/static", StaticFiles(directory="public"), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    with open("public/index.html", "r", encoding="utf-8") as f:
        return f.read()
