import yfinance as yf
import pandas as pd
import streamlit as st
import numpy as np

@st.cache_data(ttl=3600)
def get_benchmark_data():
    """
    Fetches 1 year of historical data for USD, Gold, and BIST30.
    Normalizes data to Base 100.
    """
    symbols = {
        "Dolar (USD/TRY)": "TRY=X",
        "Altın (Ons)": "GC=F",
        "BIST 30": "XU030.IS"
    }
    
    combined_df = pd.DataFrame()
    
    for label, sym in symbols.items():
        try:
            # Fetch data with yfinance
            ticker = yf.Ticker(sym)
            data = ticker.history(period="1y")['Close']
            
            if not data.empty:
                # Basic cleaning: forward fill gaps (holidays, weekends)
                data = data.ffill()
                # Normalize: Base 100
                normalized = (data / data.iloc[0]) * 100
                combined_df[label] = normalized
            else:
                st.error(f"{label} ({sym}) verisi Yahoo Finance'dan çekilemedi (Empty).")
                print(f"Hata: {label} ({sym}) çekilemedi.")
                
        except Exception as e:
            st.error(f"{label} ({sym}) çekilirken hata oluştu: {e}")
            print(f"Hata ({label}): {e}")
            
    # Final data cleaning for combined dataframe
    if not combined_df.empty:
        # Fill any remaining NaNs across the whole dataframe (if symbols have different start dates)
        combined_df = combined_df.ffill().dropna()
    
    # Add a synthetic "Mevduat / Enflasyon" line (e.g. 3.5% monthly compound)
    if not combined_df.empty:
        n_days = len(combined_df)
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
