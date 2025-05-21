import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import StringIO
from datetime import datetime, timedelta

# Generate next 5 dates
def get_future_dates(n=5):
    return [(datetime.today() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, n+1)]

# Dummy clients and base data
clients = ['Client A', 'Client B', 'Client C']
future_dates = get_future_dates()

# Simulate Forecast data
def generate_forecast_data(client):
    np.random.seed(hash(client) % 1000000)
    margin_calls = np.random.randint(500000, 2000000, size=5)
    margin_call_made = ['Yes' if val > 1000000 else 'No' for val in margin_calls]
    return pd.DataFrame({
        'Date': future_dates,
        'Forecasted Margin Call (USD)': margin_calls,
        'Margin Call Made': margin_call_made
    })

# Simulate What-If scenario results
def simulate_what_if(volatility, fx_rate, interest_rate, threshold, collateral, mtm):
    base = 1_000_000
    noise = np.random.randint(-200_000, 200_000, size=5)
    adjusted = (base + noise).astype(float)

    adjusted += (volatility - 20) * 10000
    adjusted += (fx_rate - 1.0) * 20000
    adjusted += (interest_rate - 5) * 15000
    adjusted -= threshold * 0.2
    adjusted -= collateral * 0.1
    adjusted -= mtm * 0.05

    adjusted = np.maximum(adjusted, 0)
    margin_call_made = ['Yes' if val > 1000000 else 'No' for val in adjusted]

    return pd.DataFrame({
        'Date': get_future_dates(),
        'What-If Margin Call (USD)': adjusted.astype(int),
        'Margin Call Made': margin_call_made
    })

# Streamlit setup
st.set_page_config(layout="wide")
st.title("📊 Margin Call Forecaster")

# Sidebar for client and view selection
with st.sidebar:
    selected_client = st.selectbox("Select Client", clients)
    view_option = st.radio("Select View", ["Forecast", "What-If Scenario"])

# Generate data
if view_option == "Forecast":
    data_df = generate_forecast_data(selected_client)
    file_name = "forecast_margin_calls.csv"
else:
    data_df = simulate_what_if(25, 1.1, 5.0, 500_000, 2_000_000, 3_000_000)
    file_name = "what_if_margin_calls.csv"

# Forecast View
if view_option == "Forecast":
    st.dataframe(data_df.reset_index(drop=True), use_container_width=True)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(data_df['Date'], data_df['Forecasted Margin Call (USD)'], marker='o', color='green')
    ax.set_title("Forecasted Margin Call (USD)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Amount (USD)")
    ax.grid(True)
    st.pyplot(fig)

# What-If Scenario View
else:
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.subheader("🔧 Adjust Parameters")
        volatility = st.slider("Market Volatility (VIX)", 10, 50, 25)
        fx_rate = st.slider("FX Rate (e.g., EUR/USD)", 0.9, 1.5, 1.1)
        interest_rate = st.slider("Interest Rate (%)", 0.0, 10.0, 5.0, step=0.1)
        threshold = st.slider("Threshold (USD)", 0, 2_000_000, 500_000, step=50_000)
        collateral = st.slider("Collateral Posted (USD)", 0, 5_000_000, 2_000_000, step=100_000)
        mtm = st.slider("MTM (USD)", -5_000_000, 5_000_000, 0, step=100_000)

    with right_col:
        updated_df = simulate_what_if(volatility, fx_rate, interest_rate, threshold, collateral, mtm)

        st.subheader("📋 What-If Scenario: Tabular View")
        st.dataframe(updated_df, use_container_width=True)

        st.subheader("📈 What-If Scenario: Chart View")
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(updated_df['Date'], updated_df['What-If Margin Call (USD)'], marker='o', color='red')
        ax.set_title("What-If Margin Call (USD)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Amount (USD)")
        ax.grid(True)
        st.pyplot(fig)