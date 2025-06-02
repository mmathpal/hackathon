# main.py

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from forecaster import (
    hybrid_what_if_one_day,
    hybrid_forecast_from_history,
    query_llm_ask_anything
)

app = FastAPI()

# Input schema for What-If
class WhatIfInput(BaseModel):
    Client: str
    MTM: float
    Collateral: float
    Threshold: float
    Volatility: float
    InterestRate: float
    MTA: float

# Input schema for Forecast
class ForecastInput(BaseModel):
    Client: str

# Input schema for Ask Anything
class AskInput(BaseModel):
    query: str

# ---------- Endpoint 1: What-If Margin Call Analysis (One Day) ----------
@app.post("/what-if")
def what_if_analysis(input_data: WhatIfInput):
    input_dict = {
        "Client": input_data.Client,  # <--- ADD THIS LINE
        "MTM": input_data.MTM,
        "Collateral": input_data.Collateral,
        "Threshold": input_data.Threshold,
        "Volatility": input_data.Volatility,
        "InterestRate": input_data.InterestRate,
        "MTA": input_data.MTA
    }
    result = hybrid_what_if_one_day(input_dict, client_name=input_data.Client)
    return {"response": result}

# ---------- Endpoint 2: Forecast Using Historical Data ----------
@app.post("/forecast")
def forecast_margin_calls(input_data: ForecastInput):
    result = hybrid_forecast_from_history(client_name=input_data.Client)
    return {"response": result}

# ---------- Endpoint 3: Ask Anything ----------
@app.post("/ask")
def ask_anything(input_data: AskInput):
    result = query_llm_ask_anything(input_data.query)
    return {"response": result}