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
        ⚡ Powered by: <b>LLM</b> | <b>RAG</b> | <b>VectorDB</b> | <b>Azure OpenAI</b>
        </div>
        """, unsafe_allow_html=True
    )

# Forecast View
if view_option == "📈 Forecast":
    st.subheader(f"📋 LLM-Based Forecast for {selected_client} (T+1 to T+3)")

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

            # Display table with styling
            st.markdown(
                """
                <style>
                table {
                    width: 100%;
                    table-layout: fixed;
                }
                th {
                    background-color: #0D6EFD;
                    color: white;
                    text-align: center;
                    padding: 10px;
                }
                td {
                    text-align: left;
                    padding: 8px;
                    white-space: normal !important;
                    word-wrap: break-word !important;
                    max-width: 250px;
                }
                </style>
                """, unsafe_allow_html=True
            )
            st.markdown(df.to_html(index=False, escape=False), unsafe_allow_html=True)

            # Plotly Combined Line Chart
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
        volatility = st.slider("Market Volatility (VIX)", 0, 50, 20)
        interest_rate = st.slider("Interest Rate (%)", 0.0, 10.0, 2.5, step=0.1)

    with right_col:
        st.subheader(f"📋 What-If Scenario: LLM-Based Analysis for {selected_client}")
        input_data = {
            "Client": selected_client,
            "Volatility": volatility,
            "Interest_Rate": interest_rate
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
                    st.write(f"✅ **Margin Call Required?** {result['MarginCallRequired']}")
                    st.write(f"💰 **Margin Call Amount (USD):** {result['MarginCallAmount']}")
                    st.write(f"📈 **Confidence Score:** {result['ConfidenceScore']}")
                    st.write(f"📝 **Details:** {result['Comments']}")

                # Combined Line Chart for What-If
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=["Scenario"],  # Single label
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
                    xaxis=dict(title=""),  # No time/date
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