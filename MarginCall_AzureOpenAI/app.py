import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go

# FastAPI endpoint base URL
API_BASE_URL = "http://localhost:8000"

# Helper function to handle API errors
def handle_api_response(response, error_message="Failed to fetch data"):
    if response.status_code == 200:
        return response.json()["response"]
    else:
        st.error(f"{error_message}: {response.status_code} - {response.text}")
        return None

# Streamlit setup
st.set_page_config(layout="wide")
st.title("📊 Margin Call Forecaster")

# Sidebar for client and view selection
with st.sidebar:
    clients = ['ClientA', 'ClientB', 'ClientC', 'ClientD', 'ClientE', 'ClientF']
    selected_client = st.selectbox("Select Client", clients)
    view_option = st.radio(
        "Select View",
        ["📈 Forecast", "🔧 What-If Scenario", "❓ Ask Anything"]
    )
    
    st.markdown("""---""")
    st.markdown(
        """
        <div style='color: gray; text-align: center; font-size: 14px;'>
        ⚡ Powered by: <b>Agentic AI<b> | <b>LLM</b> | <b>RAG</b> | <b>LSTM</b> | <b>LightGBM</b> | <b>Azure OpenAI</b>
        </div>
        """, unsafe_allow_html=True
    )

# Forecast View
if view_option == "📈 Forecast":
    st.subheader(f"📋 Forecast for {selected_client} (T+1 to T+3)")

    headers = {"Content-Type": "application/json"}
    data = {"Client": selected_client}

    with st.spinner("🔄 Thinking... Generating Forecast..."):
        response = requests.post(f"{API_BASE_URL}/forecast", json=data, headers=headers)
        result = handle_api_response(response, "Failed to fetch forecast")

    if result:
        try:
            df = pd.DataFrame(result)
            df = df[["Date", "MarginCallRequired", "MarginCallAmount", "ConfidenceScore", "Comments"]]

            df = df.rename(columns={
                "Date": "Margin Call Date",
                "MarginCallRequired": "Margin Call Required?",
                "MarginCallAmount": "Margin Call Amount (USD)",
                "ConfidenceScore": "Confidence Score (%)",
                "Comments": "Explanation"
            })

            # Download button on top-right
            csv = df.to_csv(index=False)
            download_col, _ = st.columns([0.8, 0.2])
            with download_col:
                st.download_button(
                    label="⬇️ Download Forecast Data",
                    data=csv,
                    file_name="forecast_margin_calls.csv",
                    mime="text/csv"
                )

            # Display table with better centered header styling
            st.markdown(
                """
                <style>
                table {
                    width: 100%;
                    table-layout: fixed;
                    border-collapse: collapse;
                }
                thead tr th {
                    background-color: #0D6EFD;
                    color: white;
                    text-align: center !important; /* Force center header */
                    padding: 12px 8px;
                    font-size: 16px;
                    border: 1px solid #ddd;
                    vertical-align: middle;
                }
                tbody tr td {
                    text-align: left !important; /* Left align data */
                    padding: 10px 8px;
                    white-space: normal !important;
                    word-wrap: break-word !important;
                    border: 1px solid #ddd;
                    font-size: 14px;
                    vertical-align: top;
                }
                /* Specific Column Widths */
                th:nth-child(1), td:nth-child(1) { width: 120px; }   /* Date */
                th:nth-child(2), td:nth-child(2) { width: 160px; }   /* Margin Call Required */
                th:nth-child(3), td:nth-child(3) { width: 150px; }   /* Margin Call Amount */
                th:nth-child(4), td:nth-child(4) { width: 120px; }   /* Confidence Score */
                th:nth-child(5), td:nth-child(5) { width: 600px; }   /* Explanation - wider */
                
                tr:hover {
                    background-color: #f1f1f1;
                }
                </style>
                """, unsafe_allow_html=True
            )

            # Render the table
            st.markdown(df.to_html(index=False, escape=False), unsafe_allow_html=True)

            # Combined Line Chart
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=pd.to_datetime(df["Margin Call Date"]).dt.strftime('%Y-%m-%d'),
                y=df["Margin Call Amount (USD)"],
                mode="lines+markers",
                name="Margin Call Amount (USD)",
                line=dict(color='royalblue', width=3),
                marker=dict(size=8)
            ))

            fig.add_trace(go.Scatter(
                x=pd.to_datetime(df["Margin Call Date"]).dt.strftime('%Y-%m-%d'),
                y=df["Confidence Score (%)"].str.rstrip('%').astype(float),
                mode="lines+markers",
                name="Confidence Score (%)",
                line=dict(color='seagreen', width=3, dash='dot'),
                marker=dict(size=8),
                yaxis="y2"
            ))

            fig.update_layout(
                title=f"📈 Forecast for {selected_client}",
                xaxis=dict(
                    title="Date",
                    tickformat="%Y-%m-%d",
                    tickmode='linear'
                ),
                yaxis=dict(title="Margin Call Amount (USD)", side="left", rangemode="tozero"),
                yaxis2=dict(title="Confidence Score (%)", overlaying="y", side="right", rangemode="tozero"),
                template="plotly_white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Error parsing forecast response: {str(e)}")
            st.write("⚠️ Please check the LLM response format.")

# What-If Scenario View
elif view_option == "🔧 What-If Scenario":
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.subheader("🔧 Adjust Parameters")
        mtm = st.slider("MTM (USD)", min_value=0, max_value=3_0_000_00, value=400000, step=10_000)
        collateral = st.slider("Collateral (USD)", min_value=0, max_value=5_000_00, value=100000, step=10_000)
        threshold = st.slider("Threshold (USD)", min_value=0, max_value=4_00_000, value=30000, step=10_000)        
        volatility = st.slider("Market Volatility (VIX)", 0, 50, 20)
        interest_rate = st.slider("Interest Rate (%)", 0.0, 10.0, 2.5, step=0.1)

    with right_col:
        st.subheader(f"📋 What-If Scenario: LLM-Based Analysis for {selected_client}")
        input_data = {
            "Client": selected_client,
            "MTM": mtm,
            "Collateral": collateral,
            "Threshold": threshold,
            "Volatility": volatility,
            "InterestRate": interest_rate,
            "MTA": 1000,
            "Currency": "USD"
        }

        headers = {"Content-Type": "application/json"}

        with st.spinner("🔄 Thinking... Performing What-If Analysis..."):
            response = requests.post(f"{API_BASE_URL}/what-if", json=input_data, headers=headers)
            result = handle_api_response(response, "Failed to fetch what-if analysis")

        if result:
            try:
                margin_call_amount = float(str(result.get("MarginCallAmount", 0)).replace(",", "").replace("$", "").replace("%", ""))
                confidence_score = float(str(result.get("ConfidenceScore", "0%")).rstrip('%'))

                df = pd.DataFrame([result])
                df = df[["Date", "MarginCallRequired", "MarginCallAmount", "ConfidenceScore", "Comments"]]

                with st.expander("📋 Margin Call Details", expanded=True):
                    st.write(f"📅 **Date:** {result['Date']}")
                    margin_call_icon = "✅" if result['MarginCallRequired'].lower() == "yes" else "❌"
                    st.write(f"{margin_call_icon} **Margin Call Required?** {result['MarginCallRequired']}")
                    st.write(f"💰 **Margin Call Amount (USD):** {result['MarginCallAmount']}")
                    st.write(f"📈 **Confidence Score:** {result['ConfidenceScore']}")
                    st.write(f"📝 **Details:** {result['Comments']}")

                # Combined Line Chart for What-If
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=["Scenario"],
                    y=[margin_call_amount],
                    mode="lines+markers",
                    name="Margin Call Amount (USD)",
                    line=dict(color='indianred', width=3),
                    marker=dict(size=8)
                ))

                fig.add_trace(go.Scatter(
                    x=["Scenario"],
                    y=[confidence_score],
                    mode="lines+markers",
                    name="Confidence Score (%)",
                    line=dict(color='seagreen', width=3, dash='dot'),
                    marker=dict(size=8),
                    yaxis="y2"
                ))

                fig.update_layout(
                    title=f"📈 What-If Analysis for {selected_client}",
                    xaxis=dict(title=""),
                    yaxis=dict(title="Margin Call Amount (USD)", side="left", rangemode="tozero"),
                    yaxis2=dict(title="Confidence Score (%)", overlaying="y", side="right", rangemode="tozero"),
                    template="plotly_white",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"Error parsing what-if response: {str(e)}")
                st.write("⚠️ Please check the LLM response format.")

# Ask Anything View
else:
    st.subheader("❓ Ask Anything About Margin Calls")
    query = st.text_input("Enter your question:", placeholder="e.g., What factors influence margin calls?")
    if query:
        with st.spinner("🔄 Thinking... Fetching response..."):
            response = requests.post(f"{API_BASE_URL}/ask", json={"query": query})
            result = handle_api_response(response, "Failed to fetch response")
        if result:
            st.write("### 🧠 LLM Response")
            st.success(result)