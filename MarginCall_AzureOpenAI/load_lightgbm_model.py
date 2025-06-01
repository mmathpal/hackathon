#load_lightgbm_model.py
import joblib

def load_margin_call_model():
    model = joblib.load("margin_call_lightgbm_model.pkl")
    return model