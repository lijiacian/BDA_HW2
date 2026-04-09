import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

st.set_page_config(
    page_title="MSTR Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    div[data-testid="stExpander"] { border: none !important; box-shadow: none !important; }
    </style>
    """, unsafe_allow_html=True)

MSTR_HOLDINGS_HISTORY = [
    ("2024-12-30", 446400), ("2025-01-06", 447470), ("2025-01-13", 450000),
    ("2025-01-21", 461000), ("2025-01-27", 471107), ("2025-02-10", 478740),
    ("2025-02-24", 499096), ("2025-03-17", 499226), ("2025-03-24", 506137),
    ("2025-03-31", 528185), ("2025-04-14", 531644), ("2025-04-21", 538200),
    ("2025-04-28", 553555), ("2025-05-05", 555450), ("2025-05-12", 568840),
    ("2025-05-19", 576230), ("2025-05-26", 580250), ("2025-06-02", 580955),
    ("2025-06-09", 582000), ("2025-06-16", 592100), ("2025-06-23", 592345),
    ("2025-06-30", 597325), ("2025-07-14", 601550), ("2025-07-21", 607770),
    ("2025-07-29", 628791), ("2025-08-11", 628946), ("2025-08-18", 629376),
    ("2025-08-25", 632457), ("2025-09-02", 636505), ("2025-09-08", 638460),
    ("2025-09-15", 638985), ("2025-09-22", 639835), ("2025-09-29", 640031),
    ("2025-10-13", 640250), ("2025-10-20", 640418), ("2025-10-27", 640808),
    ("2025-11-03", 641205), ("2025-11-10", 641692), ("2025-11-17", 649870),
    ("2025-12-01", 650000), ("2025-12-08", 660624), ("2025-12-15", 671268),
    ("2025-12-29", 672497), ("2025-12-31", 672500), ("2026-01-05", 673783),
    ("2026-01-12", 687410), ("2026-01-20", 709715), ("2026-01-26", 712647),
    ("2026-02-02", 713502), ("2026-02-09", 714644), ("2026-02-17", 717131),
    ("2026-02-23", 717722), ("2026-03-02", 720737), ("2026-03-09", 738731),
    ("2026-03-16", 761068), ("2026-03-23", 762099), ("2026-04-06", 766970)
]

MSTR_SHARES_HISTORY = [
    ("2023-12-31", 168681000),
    ("2024-12-31", 245778000),
    ("2025-03-31", 266178000),
    ("2025-06-30", 280958000),
    ("2025-09-30", 287108000),
    ("2025-12-31", 312062000),
    ("2026-03-31", 346223000),
    ("2026-04-04", 346819000),
]

@st.cache_data(ttl=21600)
def get_data():
    return load_market_data()
def load_market_data():
    history_df = pd.DataFrame(MSTR_HOLDINGS_HISTORY, columns=["Date", "BTC_Holdings"])
    history_df['Date'] = pd.to_datetime(history_df['Date'])
    
    shares_df = pd.DataFrame(MSTR_SHARES_HISTORY, columns=["Date", "Shares_Outstanding"])
    shares_df['Date'] = pd.to_datetime(shares_df['Date'])
    
    start_date = history_df['Date'].min()
    end_date = datetime.now() + timedelta(days=1)
    
    btc_raw = yf.download("BTC-USD", start=start_date, end=end_date)
    mstr_raw = yf.download("MSTR", start=start_date, end=end_date)

    if isinstance(btc_raw.columns, pd.MultiIndex):
        btc_raw.columns = btc_raw.columns.get_level_values(0)
    if isinstance(mstr_raw.columns, pd.MultiIndex):
        mstr_raw.columns = mstr_raw.columns.get_level_values(0)

    def get_clean_close(df):
        if isinstance(df.columns, pd.MultiIndex):
            return df['Close'].iloc[:, 0]
        return df['Close']

    btc_price = get_clean_close(btc_raw)
    mstr_price = get_clean_close(mstr_raw)

    daily_df = pd.DataFrame(index=btc_price.index)
    daily_df['BTC_Price'] = btc_price
    daily_df['MSTR_Price'] = mstr_price.reindex(daily_df.index).ffill()
    
    history_df.set_index('Date', inplace=True)
    daily_df = daily_df.join(history_df)
    daily_df['BTC_Holdings'] = daily_df['BTC_Holdings'].ffill()
    
    shares_df.set_index('Date', inplace=True)
    daily_df = daily_df.join(shares_df)

    daily_df['Shares_Outstanding'] = (
        daily_df['Shares_Outstanding']
        .ffill()
        .bfill()
    )
    daily_df['MSTR_MarketCap_B'] = (daily_df['MSTR_Price'] * daily_df['Shares_Outstanding']) / 1e9
    daily_df['NAV_Value_Billion'] = (daily_df['BTC_Holdings'] * daily_df['BTC_Price']) / 1e9
    daily_df['Premium_Pct'] = (daily_df['MSTR_MarketCap_B'] / daily_df['NAV_Value_Billion'] - 1) * 100
    
    return daily_df.dropna(subset=['Premium_Pct'])

st.title("MicroStrategy Dashboard")
st.markdown("Dashboard monitoring MSTR Market Cap vs. Bitcoin Net Asset Value (NAV).")

try:
    if "df" not in st.session_state:
        with st.spinner("'Synchronizing with market data..."):
            st.session_state.df = get_data()

    df = st.session_state.df

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("BTC Price (USD)", f"${latest['BTC_Price']:,.2f}", f"{(latest['BTC_Price']-prev['BTC_Price']):,.2f}")
    m2.metric("MSTR Price (USD)", f"${latest['MSTR_Price']:.2f}", f"{(latest['MSTR_Price']-prev['MSTR_Price']):.2f}")
    m3.metric("Premium / Discount", f"{latest['Premium_Pct']:.2f}%", f"{(latest['Premium_Pct']-prev['Premium_Pct']):.2f}%")
    m4.metric("Total BTC Holdings", f"{latest['BTC_Holdings']:,.0f} ₿")

    st.markdown("---")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.08, 
                        row_heights=[0.7, 0.3])

    fig.add_trace(go.Scatter(x=df.index, y=df['MSTR_MarketCap_B'], name="Market Cap",
                             line=dict(color='#00f2ff', width=3)), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df.index, y=df['NAV_Value_Billion'], name="BTC NAV",
                             fill='tonexty', fillcolor='rgba(242, 169, 0, 0.1)',
                             line=dict(color='#f2a900', width=2, shape='hv')), row=1, col=1)

    colors = ['#ff4b4b' if x > 0 else '#00ff00' for x in df['Premium_Pct']]
    fig.add_trace(go.Bar(x=df.index, y=df['Premium_Pct'], name="Premium %",
                         marker_color=colors), row=2, col=1)

    fig.update_layout(
        height=700,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=20, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    fig.update_yaxes(title_text="Value ($ Billion)", row=1, col=1, gridcolor='#30363d')
    fig.update_yaxes(title_text="Premium %", row=2, col=1, gridcolor='#30363d')
    fig.update_xaxes(gridcolor='#30363d')

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Detailed Historical Records"):
        formatted_df = df[['MSTR_Price', 'BTC_Price', 'BTC_Holdings', 'Premium_Pct']].tail(20).copy()
        formatted_df.index = formatted_df.index.strftime('%Y-%m-%d')
        st.table(formatted_df.sort_index(ascending=False))

except Exception as e:
    st.error(f"System Error: {e}")
    st.info("Ensure your internet connection is active and yfinance is reachable.")


import os
from openai import OpenAI

st.sidebar.markdown("---")
st.sidebar.title("🤖 MSTR AI Assistant")

try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=groq_api_key
    )
except Exception as e:
    st.sidebar.error("GROQ_API_KEY not detected.")
    st.stop()

if "messages" not in st.session_state:
    system_prompt = f"""
    You are a professional financial analyst. The current MSTR data is as follows:
    - MSTR Price: ${latest['MSTR_Price']:.2f}
    - BTC Price: ${latest['BTC_Price']:,.2f}
    - Current Premium: {latest['Premium_Pct']:.2f}%
    Please answer based on the data in a professional and concise tone.
    [IMPORTANT] Do not use backticks (`) or code blocks to format numbers or data. 
    Provide the response in plain professional text only.
    """
    st.session_state.messages = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": f"Hello! I am an analysis assistant powered by open-source Llama models. The current premium is {latest['Premium_Pct']:.2f}%. How can I help you today?"}
    ]

chat_container = st.sidebar.container(height=450)
with chat_container:
    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

if prompt := st.sidebar.chat_input("Ask about MSTR analysis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)

    with chat_container:
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                stream=True,
            )
            
            for chunk in completion:
                full_response += (chunk.choices[0].delta.content or "")
                response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})