# train_margin_call_lightgbm.py

import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.preprocessing import LabelEncoder
import joblib

# 1. Load the data
df = pd.read_csv("MarginCallData.csv")

# 2. Label Encode 'Client'
client_encoder = LabelEncoder()
df["Client_Encoded"] = client_encoder.fit_transform(df["Client"])

# 3. Convert 'MarginCallMade' to numeric
df["MarginCallMade"] = df["MarginCallMade"].map({"Yes": 1, "No": 0})

# 4. Define features and target (with Client_Encoded)
features = ["Client_Encoded", "MTM", "Collateral", "Threshold", "Volatility", "InterestRate", "MTA"]
target = "MarginCallMade"

X = df[features]
y = df[target]

# 5. Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 6. LightGBM datasets
train_data = lgb.Dataset(X_train, label=y_train)
valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

# 7. Define parameters
params = {
    "objective": "binary",
    "boosting_type": "gbdt",
    "metric": "binary_logloss",
    "verbosity": -1,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "max_depth": -1,
    "random_state": 42,
    "n_jobs": -1
}

# 8. Train the model
print("Training LightGBM Model...")

model = lgb.train(
    params,
    train_data,
    valid_sets=[train_data, valid_data],
    valid_names=["train", "valid"],
    num_boost_round=1000,
    callbacks=[
        lgb.early_stopping(stopping_rounds=50),
        lgb.log_evaluation(period=100)
    ]
)

# 9. Make predictions
y_pred = model.predict(X_test, num_iteration=model.best_iteration)
y_pred_binary = [1 if pred > 0.5 else 0 for pred in y_pred]

# 10. Evaluate
accuracy = accuracy_score(y_test, y_pred_binary)
roc_auc = roc_auc_score(y_test, y_pred)

print(f"Accuracy: {accuracy:.4f}")
print(f"ROC AUC Score: {roc_auc:.4f}")

# 11. Save Model and Client Encoder
joblib.dump(model, "margin_call_lightgbm_model.joblib")
joblib.dump(client_encoder, "client_label_encoder.joblib")

print("✅ LightGBM model and client label encoder saved!")