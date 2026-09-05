import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_retail_data():
    os.makedirs("data", exist_ok=True)
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=60)
    
    # 1. Products definition
    products = [
        # Imminent Stock-Out Risks (3 products)
        {"product_id": 101, "product_name": "Wireless Noise-Canceling Headphones", "category": "Electronics", "unit_cost": 80.0, "unit_price": 149.99, "supplier_lead_time_days": 7, "min_reorder_qty": 50},
        {"product_id": 102, "product_name": "Organic Cold-Pressed Almond Milk", "category": "Groceries", "unit_cost": 2.50, "unit_price": 4.99, "supplier_lead_time_days": 5, "min_reorder_qty": 100},
        {"product_id": 103, "product_name": "Ergonomic Mesh Office Chair", "category": "Furniture", "unit_cost": 110.0, "unit_price": 229.99, "supplier_lead_time_days": 10, "min_reorder_qty": 25},
        
        # Deadstock Products (2 products: 0 sales in past 45+ days, positive stock)
        {"product_id": 104, "product_name": "Vintage Cassette Player", "category": "Electronics", "unit_cost": 15.0, "unit_price": 39.99, "supplier_lead_time_days": 14, "min_reorder_qty": 10},
        {"product_id": 105, "product_name": "Neon Green Corduroy Pants", "category": "Apparel", "unit_cost": 12.0, "unit_price": 29.99, "supplier_lead_time_days": 10, "min_reorder_qty": 20},
        
        # Sales Anomaly Products (2 products: 1 spike, 1 drop)
        {"product_id": 106, "product_name": "Smart Fitness Watch Ultra", "category": "Electronics", "unit_cost": 90.0, "unit_price": 199.99, "supplier_lead_time_days": 5, "min_reorder_qty": 30},
        {"product_id": 107, "product_name": "Artisanal Espresso Blend Beans", "category": "Groceries", "unit_cost": 6.0, "unit_price": 14.99, "supplier_lead_time_days": 4, "min_reorder_qty": 50},
        
        # Regular Healthy Products (8 products)
        {"product_id": 108, "product_name": "Ultra HD 4K Gaming Monitor", "category": "Electronics", "unit_cost": 200.0, "unit_price": 349.99, "supplier_lead_time_days": 8, "min_reorder_qty": 15},
        {"product_id": 109, "product_name": "Cotton Graphic T-Shirt", "category": "Apparel", "unit_cost": 5.0, "unit_price": 19.99, "supplier_lead_time_days": 7, "min_reorder_qty": 40},
        {"product_id": 110, "product_name": "Stainless Steel Thermal Bottle", "category": "Home", "unit_cost": 7.50, "unit_price": 24.99, "supplier_lead_time_days": 6, "min_reorder_qty": 30},
        {"product_id": 111, "product_name": "Ceramic Non-Stick Frying Pan", "category": "Home", "unit_cost": 14.0, "unit_price": 34.99, "supplier_lead_time_days": 9, "min_reorder_qty": 25},
        {"product_id": 112, "product_name": "Organic Green Tea Boxes", "category": "Groceries", "unit_cost": 3.0, "unit_price": 7.99, "supplier_lead_time_days": 4, "min_reorder_qty": 60},
        {"product_id": 113, "product_name": "Bluetooth Portable Speaker", "category": "Electronics", "unit_cost": 22.0, "unit_price": 49.99, "supplier_lead_time_days": 6, "min_reorder_qty": 35},
        {"product_id": 114, "product_name": "Running Performance Sneakers", "category": "Apparel", "unit_cost": 35.0, "unit_price": 89.99, "supplier_lead_time_days": 10, "min_reorder_qty": 20},
        {"product_id": 115, "product_name": "Smart LED Desk Lamp", "category": "Home", "unit_cost": 18.0, "unit_price": 39.99, "supplier_lead_time_days": 5, "min_reorder_qty": 25}
    ]
    df_products = pd.DataFrame(products)

    # 2. Inventory definition
    # Store ID: 101
    inventory = [
        # Stock-out risks: stock low compared to 30-day ADS x lead time
        {"store_id": 101, "product_id": 101, "current_stock_units": 10, "last_restock_date": (end_date - timedelta(days=15)).strftime("%Y-%m-%d")}, # ADS ~ 5 => DIR 2.0 days <= 7
        {"store_id": 101, "product_id": 102, "current_stock_units": 12, "last_restock_date": (end_date - timedelta(days=10)).strftime("%Y-%m-%d")}, # ADS ~ 4 => DIR 3.0 days <= 5
        {"store_id": 101, "product_id": 103, "current_stock_units": 5,  "last_restock_date": (end_date - timedelta(days=20)).strftime("%Y-%m-%d")}, # ADS ~ 2 => DIR 2.5 days <= 10
        
        # Deadstock: positive stock, 0 sales past 45+ days
        {"store_id": 101, "product_id": 104, "current_stock_units": 45, "last_restock_date": (end_date - timedelta(days=50)).strftime("%Y-%m-%d")},
        {"store_id": 101, "product_id": 105, "current_stock_units": 30, "last_restock_date": (end_date - timedelta(days=55)).strftime("%Y-%m-%d")},
        
        # Anomalies
        {"store_id": 101, "product_id": 106, "current_stock_units": 120, "last_restock_date": (end_date - timedelta(days=5)).strftime("%Y-%m-%d")},
        {"store_id": 101, "product_id": 107, "current_stock_units": 200, "last_restock_date": (end_date - timedelta(days=3)).strftime("%Y-%m-%d")},
        
        # Regular products
        {"store_id": 101, "product_id": 108, "current_stock_units": 85,  "last_restock_date": (end_date - timedelta(days=7)).strftime("%Y-%m-%d")},
        {"store_id": 101, "product_id": 109, "current_stock_units": 150, "last_restock_date": (end_date - timedelta(days=4)).strftime("%Y-%m-%d")},
        {"store_id": 101, "product_id": 110, "current_stock_units": 90,  "last_restock_date": (end_date - timedelta(days=8)).strftime("%Y-%m-%d")},
        {"store_id": 101, "product_id": 111, "current_stock_units": 70,  "last_restock_date": (end_date - timedelta(days=6)).strftime("%Y-%m-%d")},
        {"store_id": 101, "product_id": 112, "current_stock_units": 180, "last_restock_date": (end_date - timedelta(days=2)).strftime("%Y-%m-%d")},
        {"store_id": 101, "product_id": 113, "current_stock_units": 110, "last_restock_date": (end_date - timedelta(days=5)).strftime("%Y-%m-%d")},
        {"store_id": 101, "product_id": 114, "current_stock_units": 60,  "last_restock_date": (end_date - timedelta(days=9)).strftime("%Y-%m-%d")},
        {"store_id": 101, "product_id": 115, "current_stock_units": 95,  "last_restock_date": (end_date - timedelta(days=4)).strftime("%Y-%m-%d")},
    ]
    df_inventory = pd.DataFrame(inventory)

    # 3. Sales transactions (60 days)
    np.random.seed(42)
    sales = []
    tx_id = 10001
    
    price_map = {p["product_id"]: p["unit_price"] for p in products}

    for day in range(60):
        current_dt = start_date + timedelta(days=day)
        date_str = current_dt.strftime("%Y-%m-%d")

        for p in products:
            pid = p["product_id"]
            price = price_map[pid]
            
            # Deadstock: 0 sales in past 60 days
            if pid in [104, 105]:
                continue
                
            # Imminent stock-outs: Steady daily sales over past 60 days
            if pid == 101: # ADS ~ 5
                units = int(np.random.poisson(5))
            elif pid == 102: # ADS ~ 4
                units = int(np.random.poisson(4))
            elif pid == 103: # ADS ~ 2
                units = int(np.random.poisson(2))
                
            # Sales Anomaly Spike: P106 steady ~10/day, yesterday (day 59) spikes to 45 units
            elif pid == 106:
                if day == 59:
                    units = 45 # Severe spike (>2 std dev + 3x)
                else:
                    units = int(max(1, np.random.normal(10, 2)))
                    
            # Sales Anomaly Drop: P107 steady ~25/day, yesterday (day 59) drops to 2 units
            elif pid == 107:
                if day == 59:
                    units = 2 # Severe drop (< 0.2 * 25)
                else:
                    units = int(max(5, np.random.normal(25, 3)))
                    
            # Regular products
            else:
                units = int(max(1, np.random.poisson(6)))

            if units > 0:
                timestamp_str = f"{date_str} {np.random.randint(9, 21):02d}:{np.random.randint(0, 60):02d}:00"
                sales.append({
                    "transaction_id": tx_id,
                    "store_id": 101,
                    "product_id": pid,
                    "timestamp": timestamp_str,
                    "units_sold": units,
                    "total_revenue": round(units * price, 2)
                })
                tx_id += 1

    df_sales = pd.DataFrame(sales)

    # Save to CSV files in data/
    df_products.to_csv("data/products.csv", index=False)
    df_inventory.to_csv("data/inventory.csv", index=False)
    df_sales.to_csv("data/sales.csv", index=False)

    # Load into SQLite retail_copilot.db (root and data/)
    db_paths = ["retail_copilot.db", "data/retail_copilot.db"]
    for db_path in db_paths:
        conn = sqlite3.connect(db_path)
        df_products.to_sql("products", conn, if_exists="replace", index=False)
        df_inventory.to_sql("inventory", conn, if_exists="replace", index=False)
        df_sales.to_sql("sales", conn, if_exists="replace", index=False)
        conn.close()
        
    print("[SUCCESS] Data generation completed successfully.")

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    generate_retail_data()
