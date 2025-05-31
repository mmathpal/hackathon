from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from forecaster_llm import (
    query_llm_what_if_one_day,
    query_llm_forecast_from_history,
    query_llm_ask_anything
)

app = FastAPI()

# Request schema for What-If (single day)
class WhatIfInput(BaseModel):
    Client: str
    Volatility: float    
    Interest_Rate: float
    

# Request schema for Forecast (just pass client name)
class ForecastInput(BaseModel):
    Client: str

# Request schema for Ask Anything
class AskInput(BaseModel):
    query: str

# ---------- Endpoint 1: What-If Margin Call Analysis (One Day) ----------
@app.post("/what-if")
def what_if_analysis(input_data: WhatIfInput):
    input_dict = {
        "Client": input_data.Client,
        "Volatility": input_data.Volatility,        
        "Interest Rate": input_data.Interest_Rate        
    }
    result = query_llm_what_if_one_day(input_dict, client_name=input_data.Client)
    return {"response": result}

# ---------- Endpoint 2: Forecast Using Historical Data ----------
@app.post("/forecast")
def forecast_margin_calls(input_data: ForecastInput):
    result = query_llm_forecast_from_history(client_name=input_data.Client)
    return {"response": result}

# ---------- Endpoint 3: Ask Anything ----------
@app.post("/ask")
def ask_anything(input_data: AskInput):
    result = query_llm_ask_anything(input_data.query)
    return {"response": result}
