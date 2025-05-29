import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pandas as pd

# FastAPI endpoint base URL
API_BASE_URL = "http://localhost:8000"

# Generate next 5 dates for fallback or display
def get_future_dates(n=5):
    return [(datetime.today() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, n+1)]

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
    clients = ['Client A', 'Client B', 'Client C']
    selected_client = st.selectbox("Select Client", clients)
    view_option = st.radio("Select View", ["Forecast", "What-If Scenario", "Ask Anything"])

# Forecast View
if view_option == "Forecast":
    st.subheader(f"📋 LLM-Based Forecast for {selected_client} (T+1 to T+3)")
    
    # Call FastAPI /forecast endpoint

    headers = {
        "Content-Type": "application/json"
        #"Authorization": "Bearer YOUR_API_KEY"  # If required
    }
    data = {
        "Client": selected_client,
    }

    response = requests.post(f"{API_BASE_URL}/forecast", json=data, headers=headers)
    # st.write(response.status_code, response.json())
    result = handle_api_response(response, "Failed to fetch forecast")
        
    if result:
        st.write("### Raw Forecast Response")  # Debugging
        st.write(result) ## comment later

        data = response.json()
        #first_item = data["response"][0]  # Ensure the index refers to the correct element
        #string_value = first_item.get("Comments", "")  # Access the field containing a string

        try:
            df = pd.DataFrame(data["response"])
            df = df[["Date", "MarginCallRequired", "MarginCallAmount","Comments"]]
            # Rename columns
            df = df.rename(columns={
                "Date": "Margin Call Date",
                "MarginCallRequired": "Margin Call Required?",
                "MarginCallAmount": "Margin Call Amount (USD)"
            })
            st.dataframe(df, use_container_width=True)
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download Forecast Data as CSV",
                data=csv,
                file_name="forecast_margin_calls.csv",
                mime="text/csv"
            )
            
            # Chart.js visualization
            st.write("### Forecast Chart")
            chart_data = {
                "type": "line",
                "data": {
                    "labels": df["Margin Call Date"].tolist(),
                    "datasets": [{
                        "label": "Forecasted Margin Call (USD)",
                        "data": df["Margin Call Amount (USD)"].tolist(),
                        "borderColor": "#3498db",
                        "backgroundColor": "rgba(52, 152, 219, 0.2)",
                        "fill": True,
                        "tension": 0.4
                    }]
                },
                "options": {
                    "scales": {
                        "x": {"title": {"display": True, "text": "Date"}},
                        "y": {"title": {"display": True, "text": "Margin Call Amount (USD)"}, "beginAtZero": False}
                    },
                    "plugins": {
                        "title": {"display": True, "text": f"Margin Call Forecast for {selected_client} (T+1 to T+3)"}
                    }
                }
            }
            st.components.v1.html(f"""
                <canvas id="forecastChart"></canvas>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <script>
                    new Chart(document.getElementById('forecastChart'), {json.dumps(chart_data)});
                </script>
            """, height=400)
            
        except Exception as e:
            st.error(f"Error parsing forecast response: {str(e)}")
            st.write("Please check the LLM response format.")

# What-If Scenario View
elif view_option == "What-If Scenario":
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
        st.subheader("📋 What-If Scenario: LLM-Based Analysis")
        input_data = {
            "MTM": mtm,
            "Collateral": collateral,
            "Threshold": threshold,
            "Volatility": volatility,
            "FX_Rate": fx_rate,
            "Interest_Rate": interest_rate,
            "MTA": 100000,  # Fixed MTA for simplicity
            "Currency": "USD"
        }
        
        # Call FastAPI /what-if endpoint
        response = requests.post(f"{API_BASE_URL}/what-if", json=input_data)
        result = handle_api_response(response, "Failed to fetch what-if analysis")
        
        if result:
            st.write("### Raw What-If Response")  # Debugging
            st.write(result)
            try:
                lines = [line.strip() for line in result.split("\n") if line.strip()]
                required = lines[0].split(":", 1)[1].strip() if ":" in lines[0] else "Unknown"
                amount_str = lines[1].split(":", 1)[1].strip() if len(lines) > 1 and ":" in lines[1] else "0"
                amount = float(amount_str.replace("$", "").replace(",", "")) if amount_str.replace("$", "").replace(",", "").replace(".", "").isdigit() else 0.0
                explanation = lines[2].split(":", 1)[1].strip() if len(lines) > 2 and ":" in lines[2] else "No explanation"
                
                # Display DataFrame
                df = pd.DataFrame([{
                    "Date": datetime.today().strftime('%Y-%m-%d'),
                    "Margin Call Required": required,
                    "Margin Call Amount (USD)": amount,
                    "Explanation": explanation
                }])
                st.dataframe(df, use_container_width=True)
                
                # Download button
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download What-If Data as CSV",
                    data=csv,
                    file_name="what_if_margin_calls.csv",
                    mime="text/csv"
                )
                
                # Chart.js visualization (single point)
                st.write("### What-If Chart")
                chart_data = {
                    "type": "bar",
                    "data": {
                        "labels": [datetime.today().strftime('%Y-%m-%d')],
                        "datasets": [{
                            "label": "What-If Margin Call (USD)",
                            "data": [amount],
                            "backgroundColor": "rgba(231, 76, 60, 0.5)",
                            "borderColor": "#e74c3c",
                            "borderWidth": 1
                        }]
                    },
                    "options": {
                        "scales": {
                            "x": {"title": {"display": True, "text": "Date"}},
                            "y": {"title": {"display": True, "text": "Margin Call Amount (USD)"}, "beginAtZero": False}
                        },
                        "plugins": {
                            "title": {"display": True, "text": f"What-If Margin Call for {selected_client}"}
                        }
                    }
                }
                st.components.v1.html(f"""
                    <canvas id="whatIfChart"></canvas>
                    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                    <script>
                        new Chart(document.getElementById('whatIfChart'), {json.dumps(chart_data)});
                    </script>
                """, height=400)
                
            except Exception as e:
                st.error(f"Error parsing what-if response: {str(e)}")
                st.write("Please check the LLM response format.")

# Ask Anything View
else:
    st.subheader("❓ Ask Anything About Margin Calls")
    query = st.text_input("Enter your question:", placeholder="e.g., What factors influence margin calls?")
    if query:
        # Call FastAPI /ask endpoint
        response = requests.post(f"{API_BASE_URL}/ask", json={"query": query})
        result = handle_api_response(response, "Failed to fetch response")
        if result:
            st.write("### Response")
            st.write(result)