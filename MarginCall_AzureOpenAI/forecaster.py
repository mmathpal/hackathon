import os
import re
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import torch
import joblib
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from torch import nn

load_dotenv()

# Initialize LLM
llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_CHAT_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    temperature=0
)

# Embedding model
embedding_model = AzureOpenAIEmbeddings(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION"),
    deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
)

# Load FAISS vectorstore
def load_local_vectorstore():
    return FAISS.load_local(
        "faiss_index",
        embedding_model,
        allow_dangerous_deserialization=True
    )

# Load Models and Encoders
lightgbm_model = joblib.load("margin_call_lightgbm_model.joblib")
client_encoder = joblib.load("client_label_encoder.joblib")

class MarginCallLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers=1):
        super(MarginCallLSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        h0 = torch.zeros(1, x.size(0), 64)
        c0 = torch.zeros(1, x.size(0), 64)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return self.sigmoid(out)

lstm_model = MarginCallLSTM(7, 64)
lstm_model.load_state_dict(torch.load("margin_call_lstm_model.pth"))
lstm_model.eval()

scaler = joblib.load("lstm_scaler.joblib")
historical_df = pd.read_csv("MarginCallData.csv")
historical_df["Client_Encoded"] = client_encoder.transform(historical_df["Client"])

features = ["Client_Encoded", "MTM", "Collateral", "Threshold", "Volatility", "InterestRate", "MTA"]

# ---------- Prediction Functions ----------
def predict_with_lightgbm(input_data):
    client_encoded = client_encoder.transform([input_data["Client"]])[0]
    input_features = [
        client_encoded,
        input_data["MTM"],
        input_data["Collateral"],
        input_data["Threshold"],
        input_data["Volatility"],
        input_data["InterestRate"],
        input_data["MTA"]
    ]
    input_array = np.array([input_features])
    probability = lightgbm_model.predict(input_array)[0]
    return probability

def predict_with_lstm(input_data):
    client_encoded = client_encoder.transform([input_data["Client"]])[0]
    input_features = [
        client_encoded,
        input_data["MTM"],
        input_data["Collateral"],
        input_data["Threshold"],
        input_data["Volatility"],
        input_data["InterestRate"],
        input_data["MTA"]
    ]
    input_array = np.array([input_features])
    input_array_scaled = scaler.transform(input_array.reshape(1, -1))
    input_tensor = torch.tensor(input_array_scaled, dtype=torch.float32).unsqueeze(0)
    probability = lstm_model(input_tensor).detach().numpy()[0][0]
    return probability

def hybrid_predict_margin_call(input_data):
    prob_lgbm = predict_with_lightgbm(input_data)
    prob_lstm = predict_with_lstm(input_data)

    avg_prob = (prob_lgbm + prob_lstm) / 2
    margin_call_required = "Yes" if avg_prob > 0.5 else "No"
    confidence_score = round(avg_prob * 100, 2)
    if margin_call_required == "Yes":
        margin_call_amount = max(round(input_data["MTM"] - input_data["Collateral"] - input_data["Threshold"], 2), 0)
    else:
        margin_call_amount = 0

    return margin_call_required, f"${margin_call_amount:,.2f}", f"{confidence_score:.2f}%"

def clean_comments(text):
    return re.sub(r'\s+', ' ', text).strip()

# ---------- Input Generator ----------
def generate_dynamic_inputs(historical_df, n_days=3, client_name=None):
    if client_name:
        np.random.seed(abs(hash(client_name)) % (2**32))

    inputs = []
    for _ in range(n_days):
        sample = {}
        for feature in ["MTM", "Collateral", "Threshold", "Volatility", "InterestRate", "MTA"]:
            min_val = historical_df[feature].min()
            max_val = historical_df[feature].max()
            sampled_value = np.random.uniform(min_val, max_val)
            if feature in ["MTM", "Collateral", "Threshold"]:
                sampled_value = round(sampled_value)
            else:
                sampled_value = round(sampled_value, 2)
            sample[feature] = sampled_value

        if client_name:
            sample["Client"] = client_name

        inputs.append(sample)

    return inputs

# ---------- What-If Analysis ----------
def hybrid_what_if_one_day(input_data: dict, client_name: str):
    margin_call_required, margin_call_amount, confidence_score = hybrid_predict_margin_call(input_data)

    vector_store = load_local_vectorstore()
    retriever = vector_store.as_retriever(search_kwargs={"k": 10})
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=False
    )

    today = datetime.today().strftime('%Y-%m-%d')

    prompt = f"""
The ML model predicts that a margin call **{'IS' if margin_call_required == 'Yes' else 'is NOT'}** required for client {client_name} today ({today}).
Prediction Details:
- MTM: {input_data['MTM']}
- Collateral: {input_data['Collateral']}
- Threshold: {input_data['Threshold']}
- Volatility: {input_data['Volatility']}
- InterestRate: {input_data['InterestRate']}
- MTA: {input_data['MTA']}
- Margin Call Required: {margin_call_required}
- Margin Call Amount: {margin_call_amount}
- Confidence Score: {confidence_score}

Using historical margin call data, briefly explain the model's prediction in 2-3 lines.
"""

    explanation = qa_chain.run(prompt)

    return {
        "Client": client_name,
        "Date": today,
        "MarginCallRequired": margin_call_required,
        "MarginCallAmount": margin_call_amount,
        "ConfidenceScore": confidence_score,
        "Comments": clean_comments(explanation)
    }

# ---------- Forecast for T+1, T+2, T+3 ----------
def hybrid_forecast_from_history(client_name: str):
    vector_store = load_local_vectorstore()
    retriever = vector_store.as_retriever(search_kwargs={"k": 20})
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=False
    )

    forecast_results = []
    today = datetime.today()

    simulated_inputs = generate_dynamic_inputs(historical_df, n_days=3, client_name=client_name)

    for i, input_data in enumerate(simulated_inputs):
        forecast_date = (today + timedelta(days=i+1)).strftime('%Y-%m-%d')
        margin_call_required, margin_call_amount, confidence_score = hybrid_predict_margin_call(input_data)

        prompt = f"""
The ML model predicts that a margin call **{'IS' if margin_call_required == 'Yes' else 'is NOT'}** required for client {client_name} on {forecast_date}.
Prediction Details:
- MTM: {input_data['MTM']}
- Collateral: {input_data['Collateral']}
- Threshold: {input_data['Threshold']}
- Volatility: {input_data['Volatility']}
- InterestRate: {input_data['InterestRate']}
- MTA: {input_data['MTA']}
- Margin Call Required: {margin_call_required}
- Margin Call Amount: {margin_call_amount}
- Confidence Score: {confidence_score}

Using historical margin call data, briefly explain the model's prediction in 2-3 lines.
"""

        explanation = qa_chain.run(prompt)

        forecast_results.append({
            "Client": client_name,
            "Date": forecast_date,
            "MarginCallRequired": margin_call_required,
            "MarginCallAmount": margin_call_amount,
            "ConfidenceScore": confidence_score,
            "Comments": clean_comments(explanation)
        })

    return forecast_results

# ---------- Ask Anything ----------
def query_llm_ask_anything(query: str):
    vector_store = load_local_vectorstore()
    retriever = vector_store.as_retriever(search_kwargs={"k": 20})
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=False
    )
    return qa_chain.run(query)