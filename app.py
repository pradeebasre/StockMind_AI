import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from analytics_engine import compute_analytics
from llm_copilot import query_copilot, get_genai_client

# Page Config
st.set_page_config(
    page_title="StockMind AI | Retail Copilot",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern, Premium Dark Aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        color: #f8fafc;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(12px);
    }
    
    /* Header Container */
    .header-box {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.15));
        border: 1px solid rgba(168, 85, 247, 0.3);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    
    .header-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #818cf8, #c084fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    
    .header-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-top: 6px;
    }
    
    /* Alert Card Styling */
    .alert-card {
        background: rgba(30, 41, 59, 0.7);
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 14px;
        border-left: 4px solid #ef4444;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transition: transform 0.2s ease;
    }
    
    .alert-card-stockout {
        border-left-color: #f43f5e;
        background: rgba(244, 63, 94, 0.08);
        border: 1px solid rgba(244, 63, 94, 0.2);
        border-left: 4px solid #f43f5e;
    }
    
    .alert-card-deadstock {
        border-left-color: #f59e0b;
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.2);
        border-left: 4px solid #f59e0b;
    }
    
    .alert-card-anomaly {
        border-left-color: #3b82f6;
        background: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-left: 4px solid #3b82f6;
    }
    
    .alert-title {
        font-weight: 600;
        font-size: 1rem;
        color: #f8fafc;
        margin-bottom: 4px;
    }
    
    .alert-rec {
        color: #e2e8f0;
        font-size: 0.88rem;
        margin-bottom: 6px;
        font-weight: 500;
    }
    
    .alert-math {
        color: #94a3b8;
        font-size: 0.8rem;
        background: rgba(15, 23, 42, 0.6);
        padding: 6px 8px;
        border-radius: 6px;
        font-family: monospace;
    }

    /* Metric Cards */
    .metric-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .badge-critical { background: #9f1239; color: #ffe4e6; }
    .badge-high { background: #92400e; color: #fef3c7; }
    .badge-medium { background: #1e3a8a; color: #dbeafe; }

</style>
""", unsafe_allow_html=True)

# Fetch Analytics Alerts
@st.cache_data(ttl=60)
def load_alerts():
    return compute_analytics()

alerts = load_alerts()

# SIDEBAR: Needs Attention Today
with st.sidebar:
    st.markdown("## 🚨 Needs Attention Today")
    st.caption("Deterministic Real-Time Risk & Recommendation Engine")
    
    # Subsection 1: Imminent Stock-Outs
    st.markdown("### ⚠️ Imminent Stock-Outs")
    if alerts["stock_outs"]:
        for a in alerts["stock_outs"]:
            st.markdown(f"""
            <div class="alert-card alert-card-stockout">
                <span class="metric-badge badge-critical">{a['severity']}</span>
                <div class="alert-title">{a['product_name']}</div>
                <div class="alert-rec">💡 <b>Rec:</b> {a['recommendation']}</div>
                <div class="alert-math">📐 <b>Math:</b> {a['math_formula']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No stock-out risks detected.")
        
    st.markdown("---")

    # Subsection 2: Deadstock
    st.markdown("### 📦 Deadstock / Tied-Up Capital")
    if alerts["deadstock"]:
        for a in alerts["deadstock"]:
            st.markdown(f"""
            <div class="alert-card alert-card-deadstock">
                <span class="metric-badge badge-high">{a['severity']}</span>
                <div class="alert-title">{a['product_name']}</div>
                <div class="alert-rec">💡 <b>Rec:</b> {a['recommendation']}</div>
                <div class="alert-math">📐 <b>Math:</b> {a['math_formula']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No deadstock detected.")

    st.markdown("---")

    # Subsection 3: Sales Anomalies
    st.markdown("### 📈 Sales Anomalies")
    if alerts["anomalies"]:
        for a in alerts["anomalies"]:
            st.markdown(f"""
            <div class="alert-card alert-card-anomaly">
                <span class="metric-badge badge-medium">{a['alert_type']}</span>
                <div class="alert-title">{a['product_name']}</div>
                <div class="alert-rec">💡 <b>Rec:</b> {a['recommendation']}</div>
                <div class="alert-math">📐 <b>Math:</b> {a['math_formula']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No sales anomalies detected.")

# MAIN PANEL: Store Manager Copilot
st.markdown("""
<div class="header-box">
    <h1 class="header-title">StockMind AI — Retail Store Manager Copilot</h1>
    <div class="header-subtitle">AI-powered conversational SQL insights, inventory risk alerts, and visual analytics</div>
</div>
""", unsafe_allow_html=True)

# Overview Quick Metric Row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Stock-Out Risks", len(alerts["stock_outs"]), delta="Requires Reorder", delta_color="inverse")
col2.metric("Deadstock Items", len(alerts["deadstock"]), delta="Tied-Up Capital", delta_color="inverse")
col3.metric("Sales Anomalies", len(alerts["anomalies"]), delta="Spikes / Drops")
col4.metric("Engine Status", "Active", delta="SQLite Grounded")

st.markdown("---")

# Quick Prompt Suggestions
st.markdown("#### 💬 Ask Store Manager Copilot")
prompt_cols = st.columns(3)
selected_prompt = None
if prompt_cols[0].button("📊 Show top selling products by revenue"):
    selected_prompt = "Show top selling products by revenue"
if prompt_cols[1].button("⚠️ Which products have low inventory stock?"):
    selected_prompt = "Which products have low inventory stock?"
if prompt_cols[2].button("📈 What is the daily sales revenue trend over time?"):
    selected_prompt = "What is the daily sales revenue trend over time?"

# Initialize Chat Session State
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I am StockMind AI Copilot. Ask me any question about your store's inventory, revenue, sales performance, or product health.",
            "sql": None,
            "df": None
        }
    ]

# Display Existing Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sql"):
            with st.expander("🔍 Executed SQL Query"):
                st.code(msg["sql"], language="sql")
        if msg.get("df") is not None and not msg["df"].empty:
            st.markdown("##### 📋 Query Results")
            st.dataframe(msg["df"], use_container_width=True)

# User Chat Input
user_input = st.chat_input("Ask a question about store sales or inventory...")
if selected_prompt:
    user_input = selected_prompt

if user_input:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Process via Copilot Layer
    with st.chat_message("assistant"):
        with st.spinner("Analyzing database and generating grounded answer..."):
            res = query_copilot(user_input)
            
            st.markdown(res["answer"])
            
            if res["sql"]:
                with st.expander("🔍 Executed SQL Query"):
                    st.code(res["sql"], language="sql")
                    
            df = res["df"]
            if df is not None and not df.empty:
                st.markdown("##### 📋 Grounded Data")
                st.dataframe(df, use_container_width=True)
                
                # Render Plotly Chart if data is numeric/time-series/categorical
                cols = df.columns.tolist()
                num_cols = df.select_dtypes(include=['number']).columns.tolist()
                
                if len(cols) >= 2 and len(num_cols) >= 1:
                    st.markdown("##### 📊 Visual Analytics")
                    chart_rendered = False
                    
                    # 1. Date/Time Series Chart
                    date_cols = [c for c in cols if any(k in c.lower() for k in ["date", "time", "day", "stamp"])]
                    if date_cols:
                        d_col = date_cols[0]
                        v_col = num_cols[0]
                        fig = px.line(
                            df, x=d_col, y=v_col, 
                            title=f"{v_col.replace('_', ' ').title()} Over Time",
                            template="plotly_dark",
                            markers=True
                        )
                        fig.update_traces(line_color="#818cf8", line_width=3)
                        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.8)")
                        st.plotly_chart(fig, use_container_width=True)
                        chart_rendered = True
                        
                    # 2. Categorical Bar Chart
                    if not chart_rendered:
                        cat_cols = [c for c in cols if c not in num_cols]
                        if cat_cols:
                            c_col = cat_cols[0]
                            v_col = num_cols[0]
                            fig = px.bar(
                                df.head(10), x=c_col, y=v_col,
                                title=f"Top Items by {v_col.replace('_', ' ').title()}",
                                template="plotly_dark",
                                color=v_col,
                                color_continuous_scale="Purples"
                            )
                            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.8)")
                            st.plotly_chart(fig, use_container_width=True)

            st.session_state.messages.append({
                "role": "assistant",
                "content": res["answer"],
                "sql": res["sql"],
                "df": df
            })
