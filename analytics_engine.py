import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def compute_analytics(db_path="retail_copilot.db"):
    conn = sqlite3.connect(db_path)
    
    # Load tables
    df_products = pd.read_sql("SELECT * FROM products", conn)
    df_inventory = pd.read_sql("SELECT * FROM inventory", conn)
    df_sales = pd.read_sql("SELECT * FROM sales", conn)
    conn.close()

    if df_sales.empty:
        return {"stock_outs": [], "deadstock": [], "anomalies": []}

    # Convert timestamp
    df_sales["timestamp"] = pd.to_datetime(df_sales["timestamp"])
    max_date = df_sales["timestamp"].max().normalize()
    cutoff_30d = max_date - timedelta(days=30)
    yesterday_date = max_date.strftime("%Y-%m-%d")

    # Filter 30-day sales
    df_30d = df_sales[df_sales["timestamp"] >= cutoff_30d].copy()
    
    # Group by product_id for 30d metrics
    sales_30d_summary = df_30d.groupby("product_id").agg(
        total_30d_units=("units_sold", "sum"),
        total_30d_revenue=("total_revenue", "sum")
    ).reset_index()

    # Daily sales per product over last 30 days
    df_30d["date"] = df_30d["timestamp"].dt.strftime("%Y-%m-%d")
    daily_sales = df_30d.groupby(["product_id", "date"])["units_sold"].sum().reset_index()

    # Merge products with inventory
    merged = pd.merge(df_inventory, df_products, on="product_id", how="inner")
    merged = pd.merge(merged, sales_30d_summary, on="product_id", how="left")
    merged["total_30d_units"] = merged["total_30d_units"].fillna(0)
    merged["total_30d_revenue"] = merged["total_30d_revenue"].fillna(0)

    # 1. ADS (Average Daily Sales over 30 days)
    merged["ads"] = merged["total_30d_units"] / 30.0

    # 2. Days of Inventory Remaining (DIR)
    merged["dir"] = np.where(merged["ads"] > 0, merged["current_stock_units"] / merged["ads"], 999.0)

    stock_out_alerts = []
    deadstock_alerts = []
    anomaly_alerts = []

    for _, row in merged.iterrows():
        pid = row["product_id"]
        pname = row["product_name"]
        cat = row["category"]
        stock = int(row["current_stock_units"])
        lead_time = int(row["supplier_lead_time_days"])
        min_reorder = int(row["min_reorder_qty"])
        ads = float(row["ads"])
        dir_days = float(row["dir"])
        units_30d = int(row["total_30d_units"])
        unit_cost = float(row["unit_cost"])

        # Category A: Imminent Stock-Out Risk (DIR <= supplier_lead_time_days and ads > 0)
        if ads > 0 and dir_days <= lead_time:
            lead_time_demand = ads * lead_time
            deficit = lead_time_demand - stock
            suggested_reorder = int(max(min_reorder, np.ceil(deficit + (ads * 3)))) # Add 3 days buffer
            
            rec = f"Reorder {suggested_reorder} units today from supplier."
            math_info = f"Current stock: {stock} units | ADS: {ads:.1f}/day | Lead time: {lead_time} days | Projected lead time demand: {lead_time_demand:.1f} units | Days of inventory left: {dir_days:.1f} days"
            
            stock_out_alerts.append({
                "product_id": pid,
                "product_name": pname,
                "category": cat,
                "severity": "CRITICAL" if dir_days <= 3 else "HIGH",
                "alert_type": "Stock-Out Risk",
                "recommendation": rec,
                "math_formula": math_info,
                "dir": round(dir_days, 1),
                "stock": stock,
                "lead_time": lead_time,
                "ads": round(ads, 2)
            })

        # Category B: Deadstock / Tied-Up Capital (30-day total sales == 0 and stock > 0)
        if units_30d == 0 and stock > 0:
            tied_up_capital = round(stock * unit_cost, 2)
            rec = f"Apply 25% discount clearance or bundle with high-volume items to liquidate {stock} units."
            math_info = f"30-day sales: 0 units | Current stock: {stock} units | Unit cost: ${unit_cost:.2f} | Tied-up capital: ${tied_up_capital:,.2f}"
            
            deadstock_alerts.append({
                "product_id": pid,
                "product_name": pname,
                "category": cat,
                "severity": "MEDIUM",
                "alert_type": "Deadstock",
                "recommendation": rec,
                "math_formula": math_info,
                "stock": stock,
                "capital": tied_up_capital
            })

        # Category C: Sales Anomalies (Spikes & Drops on yesterday's sales)
        p_daily = daily_sales[daily_sales["product_id"] == pid]
        if not p_daily.empty:
            yest_row = p_daily[p_daily["date"] == yesterday_date]
            yest_sales = int(yest_row["units_sold"].values[0]) if not yest_row.empty else 0
            
            mean_daily = p_daily["units_sold"].mean()
            std_daily = p_daily["units_sold"].std() if len(p_daily) > 1 else 0.0
            
            # Anomaly Spike: > mean + 2*std or > 3*mean
            if (std_daily > 0 and yest_sales > (mean_daily + 2 * std_daily)) or (mean_daily > 0 and yest_sales >= 3 * mean_daily):
                rec = f"Verify promotional campaign or bulk order surge. Increase safety stock buffer."
                math_info = f"Yesterday's sales: {yest_sales} units | 30-day daily avg: {mean_daily:.1f} units | Std dev: {std_daily:.1f} | Spike ratio: {yest_sales/max(1, mean_daily):.1f}x"
                
                anomaly_alerts.append({
                    "product_id": pid,
                    "product_name": pname,
                    "category": cat,
                    "severity": "HIGH",
                    "alert_type": "Sales Spike Anomaly",
                    "recommendation": rec,
                    "math_formula": math_info,
                    "yesterday_sales": yest_sales,
                    "avg_sales": round(mean_daily, 1)
                })
            # Anomaly Drop: < 0.2 * 30-day average (and mean > 3 units/day)
            elif mean_daily > 3.0 and yest_sales < (0.2 * mean_daily):
                rec = f"Investigate potential out-of-stock shelf display issue, pricing error, or competitive disruption."
                math_info = f"Yesterday's sales: {yest_sales} units | 30-day daily avg: {mean_daily:.1f} units | Drop: {((mean_daily - yest_sales)/mean_daily)*100:.1f}% below average"
                
                anomaly_alerts.append({
                    "product_id": pid,
                    "product_name": pname,
                    "category": cat,
                    "severity": "HIGH",
                    "alert_type": "Sales Drop Anomaly",
                    "recommendation": rec,
                    "math_formula": math_info,
                    "yesterday_sales": yest_sales,
                    "avg_sales": round(mean_daily, 1)
                })

    return {
        "stock_outs": stock_out_alerts,
        "deadstock": deadstock_alerts,
        "anomalies": anomaly_alerts
    }

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    alerts = compute_analytics()
    print("=== STOCK-OUT ALERTS ===")
    for a in alerts["stock_outs"]:
        print(f"[{a['severity']}] {a['product_name']} (ID: {a['product_id']})")
        print(f"  Rec:  {a['recommendation']}")
        print(f"  Math: {a['math_formula']}\n")

    print("=== DEADSTOCK ALERTS ===")
    for a in alerts["deadstock"]:
        print(f"[{a['severity']}] {a['product_name']} (ID: {a['product_id']})")
        print(f"  Rec:  {a['recommendation']}")
        print(f"  Math: {a['math_formula']}\n")

    print("=== SALES ANOMALY ALERTS ===")
    for a in alerts["anomalies"]:
        print(f"[{a['severity']}] {a['product_name']} (ID: {a['product_id']})")
        print(f"  Rec:  {a['recommendation']}")
        print(f"  Math: {a['math_formula']}\n")
