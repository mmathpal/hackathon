# predict_margin_call.py

import numpy as np
import joblib
import os

# Load Model
MODEL_PATH = "margin_call_lightgbm_model.pkl"

def load_model():
    return joblib.load(MODEL_PATH)

def predict_margin_call(model, input_data: dict):
    """
    Predicts margin call required, amount, and confidence.
    """
    features = ["MTM", "Collateral", "Threshold", "Volatility", "InterestRate", "MTA"]
    input_array = np.array([[input_data[feature] for feature in features]])

    # ML Model Prediction
    prediction_proba = model.predict(input_array)[0]
    margin_call_required = "Yes" if prediction_proba >= 0.5 else "No"
    confidence_score = round(prediction_proba * 100, 2) if margin_call_required == "Yes" else round((1 - prediction_proba) * 100, 2)

    # Calculate Margin Call Amount
    mtm = input_data["MTM"]
    collateral = input_data["Collateral"]
    threshold = input_data["Threshold"]
    mta = input_data["MTA"]

    margin_call_amount = mtm - collateral - threshold

    # Final Decision: Only issue if > MTA
    if margin_call_amount > mta:
        margin_call_issued = "Yes"
    else:
        margin_call_issued = "No"

    return {
        "MarginCallRequired": margin_call_issued,
        "MarginCallAmount": f"${margin_call_amount:,.2f}",
        "ConfidenceScore": f"{confidence_score}%"
    }