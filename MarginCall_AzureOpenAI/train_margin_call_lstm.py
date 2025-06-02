# train_margin_call_lstm.py

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
import joblib

# 1. Load data
df = pd.read_csv("MarginCallData.csv")

# 2. Label Encoding for Client
client_encoder = LabelEncoder()
df["Client_Encoded"] = client_encoder.fit_transform(df["Client"])

# 3. Features and Target
features = ["Client_Encoded", "MTM", "Collateral", "Threshold", "Volatility", "InterestRate", "MTA"]
target = "MarginCallMade"

# 4. Convert MarginCallMade to binary
df["MarginCallMade"] = df["MarginCallMade"].map({"Yes": 1, "No": 0})

X = df[features]
y = df[target]

# 5. Normalize features
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

# 6. Prepare for LSTM (batch_size, seq_len, input_size)
X_scaled = np.expand_dims(X_scaled, axis=1)

# 7. Split into train and test
split = int(0.8 * len(X))
X_train, X_test = X_scaled[:split], X_scaled[split:]
y_train, y_test = y[:split], y[split:]

# 8. Convert to tensors
X_train_tensor = torch.tensor(X_train, dtype=torch.float32)
y_train_tensor = torch.tensor(y_train.values, dtype=torch.float32)

X_test_tensor = torch.tensor(X_test, dtype=torch.float32)
y_test_tensor = torch.tensor(y_test.values, dtype=torch.float32)

train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)

# 9. Define LSTM Model
class LSTMModel(nn.Module):
    def __init__(self, input_size):
        super(LSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size=64, batch_first=True)
        self.fc = nn.Linear(64, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        out = self.fc(lstm_out[:, -1, :])
        return self.sigmoid(out)

model = LSTMModel(input_size=len(features))

# 10. Loss and Optimizer
criterion = nn.BCELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

# 11. Train the Model
print("Training LSTM Model...")
epochs = 50
for epoch in range(epochs):
    model.train()
    for xb, yb in train_loader:
        optimizer.zero_grad()
        outputs = model(xb).squeeze()
        loss = criterion(outputs, yb)
        loss.backward()
        optimizer.step()

    if (epoch+1) % 10 == 0:
        print(f"Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}")

# 12. Save Model, Scaler, and LabelEncoder
torch.save(model.state_dict(), "margin_call_lstm_model.pth")
joblib.dump(scaler, "lstm_scaler.joblib")
joblib.dump(client_encoder, "client_label_encoder.joblib")

print("✅ LSTM model, scaler, and client label encoder saved!")