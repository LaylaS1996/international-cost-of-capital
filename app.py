
import streamlit as st

st.set_page_config(
    page_title="International Cost of Capital",
    page_icon="🌎",
    layout="wide"
)

st.title("🌎 International Cost of Capital Calculator")

st.write(
    "Compare the cost of equity, cost of debt, and "
    "WACC in USD and foreign currencies."
)

st.warning(
    "Current inputs are illustrative values from the "
    "course example, not live market data."
)

# COUNTRY INPUTS
countries = {
    "United States": None,
    "Colombia": 12.0,
    "United Kingdom": None,
    "Germany": None,
    "France": None,
    "Japan": None,
    "Canada": None,
    "Australia": None,
    "India": None,
    "Brazil": None
}

# SIDEBAR
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
    list(countries.keys())
)

erp = st.sidebar.number_input(
    "Equity Risk Premium (%)",
    value=6.5,
    step=0.1
) / 100

debt_share = st.sidebar.slider(
    "Target Debt Financing (%)",
    0, 100, 30
) / 100

st.sidebar.subheader("Financial Inputs")

unlevered_beta = st.sidebar.number_input(
    "Unlevered Beta",
    min_value=0.0,
    value=0.80,
    step=0.05
)

tax_rate = st.sidebar.number_input(
    "Corporate Tax Rate (%)",
    min_value=0.0,
    max_value=100.0,
    value=35.0,
    step=0.5
) / 100

us_yield = st.sidebar.number_input(
    "U.S. 10-Year Government Yield (%)",
    value=4.0,
    step=0.1
) / 100

foreign_default = countries[country]

if foreign_default is None:
    foreign_default = 4.0

foreign_yield = st.sidebar.number_input(
    "Selected Country 10-Year Yield (%)",
    value=float(foreign_default),
    step=0.1,
    key=country
) / 100

usd_spread = st.sidebar.number_input(
    "USD BBB Borrowing Spread (%)",
    min_value=0.0,
    value=1.5,
    step=0.1
) / 100

use_foreign_spread_override = st.sidebar.checkbox(
    "Override Foreign Borrowing Spread"
)

# FINANCIAL CALCULATIONS

# 1. Relever beta
if debt_share < 1:
    debt_to_equity = debt_share / (1 - debt_share)

    levered_beta = unlevered_beta * (
        1 + (1 - tax_rate) * debt_to_equity
    )
else:
    levered_beta = None

if levered_beta is None:
    st.error(
        "Debt financing must be below 100% "
        "to calculate levered equity beta."
    )
    st.stop()

# 2. USD cost of equity
us_equity_cost = us_yield + levered_beta * erp

# 3. USD cost of debt
us_debt_cost = us_yield + usd_spread

# 4. USD WACC
us_wacc = (
    (1 - debt_share) * us_equity_cost
    + debt_share * us_debt_cost * (1 - tax_rate)
)

# 5. Foreign currency adjustment
currency_factor = (
    (1 + foreign_yield) / (1 + us_yield)
)

# 6. Foreign cost of equity
foreign_equity_cost = (
    (1 + us_equity_cost) * currency_factor - 1
)

# 7. Foreign borrowing spread
auto_foreign_spread = usd_spread * currency_factor

if use_foreign_spread_override:
    foreign_spread = st.sidebar.number_input(
        "Foreign Borrowing Spread (%)",
        min_value=0.0,
        value=auto_foreign_spread * 100,
        step=0.1
    ) / 100
else:
    foreign_spread = auto_foreign_spread

# 8. Foreign cost of debt
foreign_debt_cost = foreign_yield + foreign_spread

# 9. Foreign WACC
foreign_wacc = (
    (1 - debt_share) * foreign_equity_cost
    + debt_share * foreign_debt_cost * (1 - tax_rate)
)

# DISPLAY RESULTS
st.header("Cost of Capital Comparison")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🇺🇸 United States (USD)")
    st.metric("Cost of Equity", f"{us_equity_cost:.4%}")
    st.metric("Cost of Debt", f"{us_debt_cost:.4%}")
    st.metric("WACC", f"{us_wacc:.4%}")

with col2:
    st.subheader(f"🌍 {country}")
    st.metric(
        "Cost of Equity",
        f"{foreign_equity_cost:.4%}"
    )
    st.metric(
        "Cost of Debt",
        f"{foreign_debt_cost:.4%}"
    )
    st.metric("WACC", f"{foreign_wacc:.4%}")

st.divider()

st.header("Calculation Details")

st.write(f"**Selected Industry:** {industry}")
st.write(f"**Selected Country:** {country}")
st.write(f"**Unlevered Beta:** {unlevered_beta:.4f}")
st.write(f"**Levered Beta:** {levered_beta:.4f}")
st.write(f"**Equity Risk Premium:** {erp:.2%}")
st.write(f"**Debt Financing:** {debt_share:.0%}")
st.write(f"**Corporate Tax Rate:** {tax_rate:.2%}")

st.caption(
    "Methodology: Professor Sergio Rebelo, "
    "Northwestern University Kellogg School of Management."
)
