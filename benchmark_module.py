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

import config

def calculate_sharpe_ratio(df_col_series, risk_free_annual=0.40):
    """
    Calculates Annualized Sharpe Ratio for a given price series.
    Sharpe = (Mean Return - Risk Free) / Std Dev
    """
    if len(df_col_series) < 2:
        return 0
        
    daily_returns = df_col_series.pct_change().dropna()
    avg_daily_ret = daily_returns.mean()
    std_daily_ret = daily_returns.std()
    
    # Annualization (approx 252 trading days)
    annual_ret = avg_daily_ret * 252
    annual_std = std_daily_ret * np.sqrt(252)
    
    if annual_std == 0:
        return 0
        
    sharpe = (annual_ret - risk_free_annual) / annual_std
    return round(sharpe, 2)

def calculate_real_return(nominal_return_pct, inflation_annual=45):
    """
    Calculates inflation-adjusted (Real) return.
    Formula: ((1 + nominal) / (1 + inflation)) - 1
    """
    nom = nominal_return_pct / 100
    inf = inflation_annual / 100
    real_ret = ((1 + nom) / (1 + inf)) - 1
    return round(real_ret * 100, 2)

def get_benchmark_summary(df):
    """
    Returns a dictionary of metrics for each asset.
    Includes Nominal Return, Real Return, and Sharpe Ratio.
    """
    if df.empty:
        return {}
    
    summary = {}
    inf_rate = getattr(config, 'ANNUAL_INFLATION_RATE', 45)
    rf_rate = getattr(config, 'RISK_FREE_RATE', 0.40)

    for col in df.columns:
        # 1. Nominal Return
        nom_ret = ((df[col].iloc[-1] / 100) - 1) * 100
        
        # 2. Real Return
        real_ret = calculate_real_return(nom_ret, inf_rate)
        
        # 3. Sharpe Ratio
        sharpe = calculate_sharpe_ratio(df[col], rf_rate)
        
        summary[col] = {
            "nominal": round(nom_ret, 2),
            "real": real_ret,
            "sharpe": sharpe
        }
    return summary
