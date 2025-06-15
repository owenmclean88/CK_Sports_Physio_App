import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timedelta

# -----------------------------
# Generate Mock Data
# -----------------------------
months = pd.date_range(start="2024-01-01", periods=12, freq="M").strftime("%b")
membership_overview = pd.DataFrame({
    "Month": months,
    "Total Members": np.linspace(10000, 35000, 12).astype(int),
    "Target Members": np.linspace(11000, 37000, 12).astype(int),
    "Total Revenue": np.linspace(1.2e6, 4.5e6, 12).astype(int),
    "Target Revenue": np.linspace(1.3e6, 4.6e6, 12).astype(int)
})

start_date = datetime(2023, 10, 1)
dates = [start_date + timedelta(days=i) for i in range(330)]
daily_sales = pd.DataFrame({
    "Date": dates,
    "Daily Members": np.random.poisson(120, size=len(dates)),
    "Daily Revenue": np.random.normal(loc=20000, scale=5000, size=len(dates)).astype(int)
})

packages = [
    "Clubhouse", "Gold", "Silver", "Bronze Corner", "Bronze Tryzone",
    "Full Season GA", "Flexis", "Reduced Access", "Outside Melb",
    "Non-access", "Juniors", "Women of Storm"
]
package_data = pd.DataFrame({
    "Package": packages,
    "Members YTD": np.random.randint(150, 20000, size=len(packages)),
    "Target Members": np.random.randint(200, 21000, size=len(packages)),
    "Revenue YTD": np.random.randint(10000, 1500000, size=len(packages)),
    "Target Revenue": np.random.randint(15000, 1600000, size=len(packages))
})

suburbs = ["Richmond", "Melbourne", "Pakenham", "Point Cook", "Werribee",
           "Tarneit", "Craigieburn", "Sunbury", "Berwick", "Hoppers Crossing"]
location_data = pd.DataFrame({
    "Suburb": suburbs,
    "Member Count": np.random.randint(100, 2000, size=len(suburbs))
})

ticketing_data = pd.DataFrame({
    "Game": [f"HG{i}. Opponent" for i in range(1, 11)],
    "Ticket Sales": np.random.randint(8000, 15000, 10),
    "Sales Target": np.random.randint(9000, 14000, 10),
    "Revenue": np.random.randint(300000, 700000, 10),
    "Revenue Target": np.random.randint(320000, 750000, 10),
    "Avg Ticket Price": np.round(np.random.uniform(35.0, 45.0, 10), 2),
    "Target Ticket Price": np.round(np.random.uniform(36.0, 46.0, 10), 2)
})

months_full = pd.date_range(start="2023-11-01", periods=10, freq="M").strftime('%b')
finance_data = pd.DataFrame({
    "Month": months_full,
    "Income": np.random.randint(1_000_000, 5_000_000, 10),
    "Expenses": np.random.randint(1_000_000, 4_500_000, 10)
})
finance_data["Net Profit"] = finance_data["Income"] - finance_data["Expenses"]

# -----------------------------
# Streamlit Config
# -----------------------------
st.set_page_config(page_title="Gemba Unified Insights", layout="wide")
pages = ["🏠 Landing Page", "🎟️ Ticketing", "🙋 Membership", "💰 Finance"]
page = st.sidebar.selectbox("Navigate", pages)

# -----------------------------
# Landing Page
# -----------------------------
if page == "🏠 Landing Page":
    st.title("Unified Data Tool: Showcase Dashboard")
    st.markdown("""
    Welcome to the demonstration tool designed to showcase what's possible when you connect your data sources with Gemba's analytics solutions.

    #### Modules Included:
    - **Descriptive Analytics**: What happened?
    - **Predictive Analytics**: What is likely to happen?
    """)

    st.header("🎟️ Ticket Sales vs Target")
    st.altair_chart(
        alt.Chart(ticketing_data).transform_fold(["Ticket Sales", "Sales Target"]).mark_bar().encode(
            x='Game:N',
            y='value:Q',
            color='key:N'
        ).properties(width=800, title="Ticket Sales by Game"),
        use_container_width=True
    )

    st.header("🙋 Membership Forecast")
    st.altair_chart(
        alt.Chart(membership_overview).mark_line(point=True).encode(
            x='Month',
            y='Total Members',
            color=alt.value("#3F51B5")
        ).properties(title="Monthly Membership Total", width=800),
        use_container_width=True
    )

# -----------------------------
# Ticketing Page
# -----------------------------
elif page == "🎟️ Ticketing":
    st.title("Ticketing Dashboard")
    st.altair_chart(
        alt.Chart(ticketing_data).transform_fold(["Revenue", "Revenue Target"]).mark_line(point=True).encode(
            x='Game:N',
            y='value:Q',
            color='key:N'
        ).properties(title="Game-by-Game Revenue vs Target", width=800),
        use_container_width=True
    )

# -----------------------------
# Membership Page
# -----------------------------
elif page == "🙋 Membership":
    st.title("Membership Dashboard")
    st.subheader("Overview")
    st.altair_chart(
        alt.Chart(membership_overview).transform_fold(["Total Members", "Target Members"]).mark_area(opacity=0.4).encode(
            x='Month',
            y='value:Q',
            color='key:N'
        ).properties(title="Membership Growth vs Target", width=800),
        use_container_width=True
    )

    st.subheader("Package Performance")
    st.dataframe(package_data)

    st.subheader("Top Suburbs by Membership")
    st.bar_chart(location_data.set_index("Suburb"))

# -----------------------------
# Finance Page
# -----------------------------
elif page == "💰 Finance":
    st.title("Finance Dashboard")
    st.altair_chart(
        alt.Chart(finance_data).transform_fold(["Income", "Expenses"]).mark_bar().encode(
            x='Month',
            y='value:Q',
            color='key:N'
        ).properties(title="Monthly Income vs Expenses", width=800),
        use_container_width=True
    )

    st.altair_chart(
        alt.Chart(finance_data).mark_line(point=True).encode(
            x='Month',
            y='Net Profit',
            color=alt.value("#4CAF50")
        ).properties(title="Net Profit Over Time", width=800),
        use_container_width=True
    )
