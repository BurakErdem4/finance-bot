import yfinance as yf
import pandas as pd
import streamlit as st
import numpy as np

@st.cache_data(ttl=3600)  # Benchmark data can be cached longer (1 hour)
def get_benchmark_data():
    """
    Fetches 1 year of historical data for USD, Gold, and BIST30.
    Normalizes data to Base 100.
    """
    symbols = {
        "Dolar (USD/TRY)": "USDTRY=X",
        "Altın (Ons)": "GC=F",
        "BIST 30": "XU030.IS"
    }
    
    combined_df = pd.DataFrame()
    
    for label, sym in symbols.items():
        try:
            data = yf.Ticker(sym).history(period="1y")['Close']
            if not data.empty:
                # Basic cleaning and normalization
                data = data.ffill()
                normalized = (data / data.iloc[0]) * 100
                combined_df[label] = normalized
        except Exception as e:
            print(f"Error fetching {label}: {e}")
            
    # Remove NaN values that might arise from different market holidays
    combined_df = combined_df.dropna()
    
    # Add a synthetic "Mevduat / Enflasyon" line (e.g. 3.5% monthly compound)
    if not combined_df.empty:
        # Calculate number of days in the data
        n_days = len(combined_df)
        # 3.5% monthly is roughly (1.035^(1/21)) per trading day assuming 21 days/mo
        daily_rate = 1.035**(1/21)
        inflation_curve = [100 * (daily_rate ** i) for i in range(n_days)]
        combined_df["Mevduat / Enflasyon (%3.5 Aylık)"] = inflation_curve
        
    return combined_df

def get_benchmark_summary(df):
    """Returns a dictionary of total returns in % for each asset."""
    if df.empty:
        return {}
    
    returns = {}
    for col in df.columns:
        total_ret = ((df[col].iloc[-1] / 100) - 1) * 100
        returns[col] = round(total_ret, 2)
    return returns
