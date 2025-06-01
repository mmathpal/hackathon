# lstm_data_prep.py

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
import joblib

# Load your data
df = pd.read_csv("MarginCallData.csv")
df['Date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y')

# Encode MarginCallMade
df['MarginCallMade'] = df['MarginCallMade'].map({'Yes': 1, 'No': 0})

# Encode Clients
client_encoder = LabelEncoder()
df['Client_ID'] = client_encoder.fit_transform(df['Client'])
joblib.dump(client_encoder, "client_label_encoder.joblib")

# Remove Currency if not needed
df.drop(columns=['Currency'], inplace=True)

# Sort Data
df = df.sort_values(by=['Client', 'Date']).reset_index(drop=True)

# Select Features
features = ["MTM", "Collateral", "Threshold", "Volatility", "InterestRate", "MTA"]

scaler = MinMaxScaler()
df[features] = scaler.fit_transform(df[features])

# Save Scaler
joblib.dump(scaler, "lstm_scaler.joblib")

print("✅ Data Prepared for LSTM")