
import streamlit as st
import pandas as pd
import requests
from io import StringIO

# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="International Cost of Capital",
    page_icon="🌎",
    layout="wide"
)

st.title("🌎 International Cost of Capital Calculator")

st.write(
    "Compare the cost of equity, cost of debt, and "
    "weighted average cost of capital (WACC) "
    "in USD and foreign currencies."
)

# =====================================================
# DAMODARAN INDUSTRY BETA DATA
# =====================================================

BETA_SOURCE = (
    "https://pages.stern.nyu.edu/adamodar/"
    "New_Home_Page/datafile/Betas.html"
)

@st.cache_data(ttl=86400)
def get_industry_betas():

    response = requests.get(
        BETA_SOURCE,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20
    )

    response.raise_for_status()

    tables = pd.read_html(
        StringIO(response.text)
    )

    for table in tables:

        # Flatten column names if necessary
        table.columns = [
            " ".join(str(x) for x in col)
            if isinstance(col, tuple)
            else str(col)
            for col in table.columns
        ]

        industry_col = next(
            (
                col for col in table.columns
                if "industry name" in col.lower()
            ),
            None
        )

        beta_col = next(
            (
                col for col in table.columns
                if "unlevered beta" in col.lower()
                and "corrected" not in col.lower()
            ),
            None
        )

        if industry_col and beta_col:

            result = table[
                [industry_col, beta_col]
            ].copy()

            result.columns = [
                "Industry",
                "Beta"
            ]

            result["Beta"] = pd.to_numeric(
                result["Beta"],
                errors="coerce"
            )

            result = result.dropna()

            result = result[
                result["Beta"] >= 0
            ]

            return result

    raise ValueError(
        "Damodaran industry beta table not found."
    )


# =====================================================
# COUNTRY DATA
# =====================================================

# These are illustrative course-example inputs.
# Live government yields will be added later.

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

# =====================================================
# SIDEBAR - INVESTMENT ASSUMPTIONS
# =====================================================

st.sidebar.header("Investment Assumptions")

# Retrieve industry betas
try:

    beta_data = get_industry_betas()

    industries = beta_data[
        "Industry"
    ].tolist()

    default_index = next(
        (
            i for i, name in enumerate(industries)
            if "Software (System & Application)"
            in name
        ),
        0
    )

    industry = st.sidebar.selectbox(
        "Select Industry",
        industries,
        index=default_index
    )

    fetched_beta = float(
        beta_data.loc[
            beta_data["Industry"] == industry,
            "Beta"
        ].iloc[0]
    )

    beta_status = "Damodaran"

except Exception:

    st.sidebar.warning(
        "Unable to retrieve industry beta data. "
        "Manual beta input is available."
    )

    industry = st.sidebar.selectbox(
        "Select Industry",
        ["Software (System & Application)"],
    )

    fetched_beta = 0.80

    beta_status = "Manual"


# Country selection
country = st.sidebar.selectbox(
    "Select Country",
    list(countries.keys())
)

# Equity risk premium
erp = st.sidebar.number_input(
    "Equity Risk Premium (%)",
    min_value=0.0,
    max_value=30.0,
    value=6.5,
    step=0.1
) / 100

# Debt financing
debt_share = st.sidebar.slider(
    "Target Debt Financing (%)",
    min_value=0,
    max_value=99,
    value=30
) / 100


# =====================================================
# FINANCIAL INPUTS
# =====================================================

st.sidebar.subheader("Financial Inputs")

# Unlevered beta
unlevered_beta = st.sidebar.number_input(
    "Unlevered Beta (Manual Override)",
    min_value=0.0,
    value=fetched_beta,
    step=0.01,
    key=f"beta_{industry}"
)

st.sidebar.caption(
    f"Beta source: {beta_status}"
)

# Corporate tax rate
tax_rate = st.sidebar.number_input(
    "Corporate Tax Rate (%)",
    min_value=0.0,
    max_value=100.0,
    value=35.0,
    step=0.5
) / 100

# U.S. risk-free rate
us_yield = st.sidebar.number_input(
    "U.S. 10-Year Government Yield (%)",
    min_value=0.0,
    value=4.0,
    step=0.1
) / 100

# Foreign risk-free rate
foreign_default = countries[country]

if foreign_default is None:
    foreign_default = 4.0

foreign_yield = st.sidebar.number_input(
    "Selected Country 10-Year Yield (%)",
    min_value=0.0,
    value=float(foreign_default),
    step=0.1,
    key=f"yield_{country}"
) / 100

# BBB borrowing spread
usd_spread = st.sidebar.number_input(
    "USD BBB Borrowing Spread (%)",
    min_value=0.0,
    value=1.5,
    step=0.1
) / 100

# Foreign spread override
use_foreign_spread_override = st.sidebar.checkbox(
    "Override Foreign Borrowing Spread"
)


# =====================================================
# FINANCIAL CALCULATIONS
# =====================================================

# STEP 1 - Debt-to-equity ratio
debt_to_equity = (
    debt_share / (1 - debt_share)
)

# STEP 2 - Levered equity beta
levered_beta = unlevered_beta * (
    1 + (1 - tax_rate) * debt_to_equity
)

# STEP 3 - USD cost of equity (CAPM)
us_equity_cost = (
    us_yield + levered_beta * erp
)

# STEP 4 - USD cost of debt
us_debt_cost = (
    us_yield + usd_spread
)

# STEP 5 - USD WACC
us_wacc = (
    (1 - debt_share) * us_equity_cost
    + debt_share * us_debt_cost * (1 - tax_rate)
)

# STEP 6 - Foreign currency adjustment
currency_factor = (
    (1 + foreign_yield) / (1 + us_yield)
)

# STEP 7 - Foreign cost of equity
foreign_equity_cost = (
    (1 + us_equity_cost) * currency_factor - 1
)

# STEP 8 - Foreign borrowing spread
auto_foreign_spread = (
    usd_spread * currency_factor
)

if use_foreign_spread_override:

    foreign_spread = st.sidebar.number_input(
        "Foreign Borrowing Spread (%)",
        min_value=0.0,
        value=float(auto_foreign_spread * 100),
        step=0.1
    ) / 100

else:
    foreign_spread = auto_foreign_spread

# STEP 9 - Foreign cost of debt
foreign_debt_cost = (
    foreign_yield + foreign_spread
)

# STEP 10 - Foreign WACC
foreign_wacc = (
    (1 - debt_share) * foreign_equity_cost
    + debt_share * foreign_debt_cost * (1 - tax_rate)
)


# =====================================================
# RESULTS - SIDE-BY-SIDE COMPARISON
# =====================================================

st.divider()

st.header("Cost of Capital Comparison")

col1, col2 = st.columns(2)

with col1:

    st.subheader("🇺🇸 United States (USD)")

    st.metric(
        "Cost of Equity",
        f"{us_equity_cost:.4%}"
    )

    st.metric(
        "Cost of Debt",
        f"{us_debt_cost:.4%}"
    )

    st.metric(
        "WACC",
        f"{us_wacc:.4%}"
    )

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

    st.metric(
        "WACC",
        f"{foreign_wacc:.4%}"
    )


# =====================================================
# CALCULATION DETAILS
# =====================================================

st.divider()

st.header("Calculation Details")

st.write(
    f"**Selected Industry:** {industry}"
)

st.write(
    f"**Selected Country:** {country}"
)

st.write(
    f"**Unlevered Beta:** {unlevered_beta:.4f}"
)

st.write(
    f"**Levered Beta:** {levered_beta:.4f}"
)

st.write(
    f"**Equity Risk Premium:** {erp:.2%}"
)

st.write(
    f"**Debt Financing:** {debt_share:.0%}"
)

st.write(
    f"**Corporate Tax Rate:** {tax_rate:.2%}"
)

st.write(
    f"**U.S. Government Yield:** {us_yield:.2%}"
)

st.write(
    f"**Foreign Government Yield:** {foreign_yield:.2%}"
)

st.write(
    f"**USD BBB Borrowing Spread:** {usd_spread:.2%}"
)

st.write(
    f"**Foreign Borrowing Spread:** {foreign_spread:.4%}"
)


# =====================================================
# DATA SOURCES & METHODOLOGY
# =====================================================

st.divider()

st.header("Data Sources & Methodology")

st.markdown(
    f"""
    **Industry Betas:** [Aswath Damodaran]({BETA_SOURCE})
    - U.S. industry dataset
    - Published data: January 2026
    - Beta input can be manually overridden

    **Corporate Tax Rates:** OECD
    - Currently entered manually

    **10-Year Government Bond Yields:** Trading Economics
    - Currently entered manually

    **BBB Borrowing Spread:** Aswath Damodaran
    - Currently entered manually

    **Financial Methodology:** Professor Sergio Rebelo,
    Northwestern University Kellogg School of Management.
    """
)

st.info(
    "Industry beta retrieval is automated when the "
    "source is available. Tax rates, borrowing spreads, "
    "and government yields are currently manual inputs. "
    "The initial values are illustrative, not live quotes."
)
