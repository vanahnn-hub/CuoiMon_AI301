import os
import pandas as pd
import numpy as np

def generate_samples():
    os.makedirs("sample_data", exist_ok=True)
    np.random.seed(42)
    
    # 1. Retail Sales Dataset (CSV)
    dates = pd.date_range(start="2026-08-01", end="2026-10-31", freq="D")
    categories = ["Điện tử & Phụ kiện", "Thời trang Nam/Nữ", "Gia dụng thông minh", "Mỹ phẩm & Chăm sóc da"]
    branches = ["Chi nhánh Hà Nội", "Chi nhánh TP.HCM", "Chi nhánh Đà Nẵng", "Kênh Online E-commerce"]
    segments = ["Khách hàng VIP", "Khách hàng Thân thiết", "Khách hàng Mới", "Khách hàng Bán sỉ"]
    channels = ["Facebook Ads", "Google Search", "TikTok Shop", "Trực tiếp tại Cửa hàng"]
    
    rows = []
    order_id = 1001
    
    for dt in dates:
        # Số đơn hàng mỗi ngày: 5 - 12 đơn
        daily_orders = np.random.randint(6, 14)
        # Giả lập sụt giảm doanh số vào giữa tháng 9 (từ ngày 12/9 đến 18/9 do gián đoạn kho vận)
        if pd.Timestamp("2026-09-12") <= dt <= pd.Timestamp("2026-09-18"):
            daily_orders = np.random.randint(1, 4)
            
        for _ in range(daily_orders):
            cat = np.random.choice(categories, p=[0.35, 0.25, 0.20, 0.20])
            branch = np.random.choice(branches, p=[0.35, 0.40, 0.10, 0.15])
            seg = np.random.choice(segments, p=[0.15, 0.35, 0.45, 0.05])
            channel = np.random.choice(channels, p=[0.30, 0.25, 0.25, 0.20])
            
            if cat == "Điện tử & Phụ kiện":
                price = np.random.choice([450000, 850000, 1200000, 2500000])
                cogs = price * np.random.uniform(0.60, 0.75)
            elif cat == "Thời trang Nam/Nữ":
                price = np.random.choice([250000, 390000, 590000, 890000])
                cogs = price * np.random.uniform(0.40, 0.55)
            elif cat == "Gia dụng thông minh":
                price = np.random.choice([550000, 1100000, 1850000])
                cogs = price * np.random.uniform(0.55, 0.70)
            else: # Mỹ phẩm
                price = np.random.choice([190000, 320000, 650000])
                cogs = price * np.random.uniform(0.35, 0.50)
                
            qty = np.random.randint(1, 4)
            
            # Giả lập chiết khấu: thường 0-15%, nhưng thỉnh thoảng sale giảm sâu 35-45% gây lỗ vốn!
            if np.random.rand() < 0.08:
                discount_pct = np.random.choice([35.0, 40.0, 50.0]) # Khuyến mãi sâu
            else:
                discount_pct = np.random.choice([0.0, 5.0, 10.0, 15.0])
                
            rev_before_disc = price * qty
            actual_revenue = rev_before_disc * (1 - discount_pct / 100.0)
            total_cogs = cogs * qty
            profit = actual_revenue - total_cogs
            
            # Tỷ lệ hoàn hàng: đặc biệt cao ở TikTok Shop hoặc Mỹ phẩm
            is_return = "Đã hoàn thành"
            if np.random.rand() < (0.18 if channel == "TikTok Shop" else 0.04):
                is_return = "Hoàn trả đơn hàng"
                
            rows.append({
                "Date": dt.strftime("%Y-%m-%d"),
                "Order_ID": f"ORD-{order_id}",
                "Branch": branch,
                "Category": cat,
                "Customer_Segment": seg,
                "Marketing_Channel": channel,
                "Units_Sold": qty,
                "Unit_Price": price,
                "Discount_Percent": discount_pct,
                "Revenue": round(actual_revenue, 0),
                "COGS": round(total_cogs, 0),
                "Gross_Profit": round(profit, 0),
                "Return_Status": is_return
            })
            order_id += 1

    df_retail = pd.DataFrame(rows)
    
    # Tạo một số dòng trùng lặp và dữ liệu thiếu có chủ đích để mô phỏng bước làm sạch dữ liệu
    # Thêm 5 dòng duplicate
    dup_rows = df_retail.iloc[10:15].copy()
    df_retail = pd.concat([df_retail, dup_rows], ignore_index=True)
    
    # Đặt ngẫu nhiên một số ô thành NaN (khuyết thiếu)
    df_retail.loc[np.random.choice(df_retail.index, 8, replace=False), "Customer_Segment"] = np.nan
    df_retail.loc[np.random.choice(df_retail.index, 5, replace=False), "Discount_Percent"] = np.nan
    
    csv_path = "sample_data/retail_sales_sample.csv"
    df_retail.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"Generated {len(df_retail)} rows to {csv_path}")
    
    # 2. Tạo sample XLSX (E-commerce Multi-sheet)
    xlsx_path = "sample_data/ecommerce_sample.xlsx"
    with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
        df_retail.head(300).to_excel(writer, sheet_name='Sales_Transactions', index=False)
        
        # Sheet 2: Marketing Channels
        channels_summary = pd.DataFrame([
            {"Channel": "Facebook Ads", "Ad_Spend": 45000000, "Clicks": 12500, "Conversions": 450, "ROAS": 3.8},
            {"Channel": "Google Search", "Ad_Spend": 38000000, "Clicks": 8900, "Conversions": 520, "ROAS": 4.5},
            {"Channel": "TikTok Shop", "Ad_Spend": 25000000, "Clicks": 28000, "Conversions": 610, "ROAS": 2.9},
            {"Channel": "KOL / Influencer", "Ad_Spend": 20000000, "Clicks": 7500, "Conversions": 230, "ROAS": 2.2}
        ])
        channels_summary.to_excel(writer, sheet_name='Marketing_Performance', index=False)
    print(f"Generated Excel to {xlsx_path}")

if __name__ == "__main__":
    generate_samples()

