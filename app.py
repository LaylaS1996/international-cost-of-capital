
import streamlit as st

# PAGE CONFIGURATION
st.set_page_config(
    page_title="International Cost of Capital",
    page_icon="🌎",
    layout="wide"
)

# TITLE
st.title("🌎 International Cost of Capital Calculator")

st.write(
    "Compare the cost of equity, cost of debt, and "
    "weighted average cost of capital (WACC) "
    "in USD and foreign currencies."
)

st.divider()

# USER INPUTS
st.sidebar.header("Investment Assumptions")

industry = st.sidebar.selectbox(
    "Select Industry",
    [
        "Software (System & Application)",
        "Healthcare",
        "Real Estate",
        "Retail",
        "Manufacturing",
        "Financial Services"
    ]
)

country = st.sidebar.selectbox(
    "Select Country",
    [
        "United States",
        "United Kingdom",
        "Germany",
        "France",
        "Japan",
        "Canada",
        "Australia",
        "India",
        "Brazil"
    ]
)

equity_risk_premium = st.sidebar.number_input(
    "Equity Risk Premium (%)",
    min_value=0.0,
    max_value=30.0,
    value=6.5,
    step=0.1
)

debt_share = st.sidebar.slider(
    "Target Debt Financing (%)",
    min_value=0,
    max_value=100,
    value=30
)

st.sidebar.divider()

st.sidebar.write("Data sources:")
st.sidebar.write("- Aswath Damodaran")
st.sidebar.write("- OECD")
st.sidebar.write("- Trading Economics")

# RESULTS LAYOUT
st.header("Cost of Capital Comparison")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🇺🇸 United States (USD)")
    st.info("USD calculations will appear here.")

with col2:
    st.subheader("🌍 Selected Country")
    st.info("Foreign currency calculations will appear here.")

st.divider()

st.header("Current Assumptions")

st.write(f"**Selected Industry:** {industry}")
st.write(f"**Selected Country:** {country}")
st.write(f"**Equity Risk Premium:** {equity_risk_premium}%")
st.write(f"**Debt Financing:** {debt_share}%")

st.caption(
    "Developed for Northwestern University "
    "Kellogg School of Management."
)
