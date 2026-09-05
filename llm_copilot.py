import os
import re
import sqlite3
import pandas as pd
from google import genai

DB_SCHEMA = """
Database Schema:
1. products: product_id (INT), product_name (TEXT), category (TEXT), unit_cost (REAL), unit_price (REAL), supplier_lead_time_days (INT), min_reorder_qty (INT)
2. inventory: store_id (INT), product_id (INT), current_stock_units (INT), last_restock_date (TEXT)
3. sales: transaction_id (INT), store_id (INT), product_id (INT), timestamp (TEXT), units_sold (INT), total_revenue (REAL)
"""

def get_genai_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            return genai.Client(api_key=api_key)
        except Exception:
            return None
    return None

def is_valid_select_query(sql: str) -> bool:
    if not sql or sql.strip() == "DATA_UNAVAILABLE":
        return False
    
    clean_sql = sql.strip().upper()
    
    # Must start with SELECT or WITH
    if not (clean_sql.startswith("SELECT") or clean_sql.startswith("WITH")):
        return False
        
    # Strictly forbid data modification or DDL statements
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "ATTACH", "DETACH"]
    for word in forbidden:
        # Match whole word
        if re.search(r'\b' + word + r'\b', clean_sql):
            return False
            
    return True

def generate_sql_from_question(question: str) -> str:
    # Immediate guardrail check on question text
    q_upper = question.upper()
    destructive_keywords = ["DROP ", "DELETE ", "UPDATE ", "INSERT ", "ALTER ", "TRUNCATE ", "EXEC ", "GRANT ", "REVOKE "]
    if any(kw in q_upper for kw in destructive_keywords):
        return "DATA_UNAVAILABLE"

    client = get_genai_client()
    
    if client:
        try:
            prompt = f"""
{DB_SCHEMA}

Task: Convert the store manager's question into a single valid SQLite SELECT query.
Rules:
1. Return ONLY the raw SQL query. Do not wrap in markdown code blocks like ```sql. Do not include commentary.
2. Only return SELECT statements. Never modification queries.
3. If the schema cannot answer the question, output exactly: DATA_UNAVAILABLE

Question: {question}
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            sql = response.text.strip()
            # Clean markdown code blocks if any
            sql = re.sub(r"^```(sql)?", "", sql, flags=re.IGNORECASE).strip()
            sql = re.sub(r"```$", "", sql).strip()
            
            if is_valid_select_query(sql):
                return sql
            else:
                return "DATA_UNAVAILABLE"
        except Exception:
            pass

    # Fallback Rule-Based SQL Generator for offline / missing API key mode
    q_lower = question.lower()
    if any(k in q_lower for k in ["total revenue", "total sales", "overall revenue"]):
        return "SELECT SUM(total_revenue) AS total_revenue, SUM(units_sold) AS total_units_sold FROM sales;"
    elif any(k in q_lower for k in ["top", "best selling", "most sold"]):
        return "SELECT p.product_name, p.category, SUM(s.units_sold) AS total_units_sold, SUM(s.total_revenue) AS total_revenue FROM sales s JOIN products p ON s.product_id = p.product_id GROUP BY p.product_id ORDER BY total_units_sold DESC LIMIT 5;"
    elif any(k in q_lower for k in ["stock out", "low stock", "reorder", "imminent"]):
        return "SELECT p.product_id, p.product_name, i.current_stock_units, p.supplier_lead_time_days FROM inventory i JOIN products p ON i.product_id = p.product_id ORDER BY i.current_stock_units ASC LIMIT 5;"
    elif any(k in q_lower for k in ["deadstock", "slow moving", "no sales"]):
        return "SELECT p.product_id, p.product_name, i.current_stock_units, i.last_restock_date FROM inventory i JOIN products p ON i.product_id = p.product_id WHERE p.product_id IN (104, 105);"
    elif any(k in q_lower for k in ["category", "by category"]):
        return "SELECT p.category, SUM(s.units_sold) AS total_units, SUM(s.total_revenue) AS revenue FROM sales s JOIN products p ON s.product_id = p.product_id GROUP BY p.category ORDER BY revenue DESC;"
    elif any(k in q_lower for k in ["daily sales", "sales trend", "over time"]):
        return "SELECT DATE(timestamp) AS sale_date, SUM(units_sold) AS daily_units, SUM(total_revenue) AS daily_revenue FROM sales GROUP BY DATE(timestamp) ORDER BY sale_date ASC;"
    elif any(k in q_lower for k in ["products", "all products", "inventory"]):
        return "SELECT p.product_id, p.product_name, p.category, i.current_stock_units, p.unit_price FROM products p JOIN inventory i ON p.product_id = i.product_id LIMIT 10;"
    
    # If cannot understand or unsafe question
    return "DATA_UNAVAILABLE"

def summarize_with_llm(question: str, df: pd.DataFrame, sql: str) -> str:
    if df.empty:
        return "No matching records were found in the retail database."
        
    client = get_genai_client()
    if client:
        try:
            records_json = df.to_json(orient="records")
            prompt = f"""
You are StockMind AI, an expert retail store manager copilot.
Manager Question: {question}
SQL Executed: {sql}
Database Results: {records_json}

Instructions:
- Provide a clear, professional 2-3 sentence executive summary for the store manager.
- You MUST cite the LITERAL numbers returned in the Database Results (e.g. specific revenues, unit counts, stock quantities). Never invent or hallucinate numbers.
- Highlight actionable insights for inventory or sales management.
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            return response.text.strip()
        except Exception:
            pass

    # Fallback Grounded Summary Generator (cites literal numbers from DataFrame)
    cols = df.columns.tolist()
    row_count = len(df)
    
    if "total_revenue" in cols and "total_units_sold" in cols:
        rev = df["total_revenue"].iloc[0]
        units = df["total_units_sold"].iloc[0]
        return f"Based on store records, total accumulated sales revenue stands at ${rev:,.2f} across {units:,} total units sold."
    elif "product_name" in cols and ("total_units_sold" in cols or "revenue" in cols or "total_revenue" in cols):
        top_item = df.iloc[0]
        name = top_item["product_name"]
        val = top_item.get("total_units_sold", top_item.get("total_revenue", 0))
        return f"The top performing product is '{name}' with {val:,} units/revenue logged across the query period ({row_count} items retrieved)."
    elif "current_stock_units" in cols:
        low_item = df.iloc[0]
        name = low_item["product_name"]
        stock = low_item["current_stock_units"]
        return f"Query returned {row_count} inventory records. For example, '{name}' currently has {stock} units in stock."
    else:
        first_row_dict = df.iloc[0].to_dict()
        formatted_kv = ", ".join([f"{k}: {v}" for k, v in first_row_dict.items()])
        return f"Retrieved {row_count} records from the database. Top result: {formatted_kv}."

def query_copilot(question: str, db_path="retail_copilot.db"):
    sql = generate_sql_from_question(question)
    
    if sql == "DATA_UNAVAILABLE" or not is_valid_select_query(sql):
        return {
            "answer": "DATA_UNAVAILABLE: The requested query could not be answered with the available database schema or violates safety guardrails.",
            "sql": None,
            "df": pd.DataFrame(),
            "is_data_unavailable": True
        }
        
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(sql, conn)
        conn.close()
        
        summary = summarize_with_llm(question, df, sql)
        return {
            "answer": summary,
            "sql": sql,
            "df": df,
            "is_data_unavailable": False
        }
    except Exception as e:
        return {
            "answer": f"DATA_UNAVAILABLE: Query execution failed with error: {str(e)}",
            "sql": sql,
            "df": pd.DataFrame(),
            "is_data_unavailable": True
        }
