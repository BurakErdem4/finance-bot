import yfinance as yf
import pandas as pd
import streamlit as st
import numpy as np

@st.cache_data(ttl=3600)
def get_benchmark_data():
    """
    Fetches 1 year of historical data for USD, Gold, and BIST30.
    Uses a master timeline to align different markets.
    """
    symbols = {
        "Dolar (USD/TRY)": "TRY=X",
        "Altın (Ons)": "GC=F",
        "BIST 30": "XU030.IS"
    }
    
    # Create Master Timeline: All days in the last year
    end_date = pd.Timestamp.now()
    start_date = end_date - pd.DateOffset(years=1)
    master_index = pd.date_range(start=start_date, end=end_date, freq='D')
    combined_df = pd.DataFrame(index=master_index)
    
    found_any = False
    for label, sym in symbols.items():
        try:
            ticker = yf.Ticker(sym)
            data = ticker.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))['Close']
            
            if not data.empty:
                # Remove timezone if exists for joining
                if data.index.tz is not None:
                    data.index = data.index.tz_localize(None)
                
                # Join with master timeline
                combined_df[label] = data
                found_any = True
            else:
                st.warning(f"⚠️ {label} verisi çekilemedi, grafikten çıkarıldı.")
        except Exception as e:
            st.warning(f"⚠️ {label} hatası: {e}")
            
    if not found_any:
        return pd.DataFrame()
        
    # Data Cleaning: Forward fill (holidays/weekends) and normalize
    # We drop columns that are entirely NaN
    combined_df = combined_df.dropna(axis=1, how='all')
    
    # Forward fill gaps
    combined_df = combined_df.ffill()
    
    # Backfill if the start of the year is empty (rare but possible)
    combined_df = combined_df.bfill()
    
    # Normalize: Base 100 based on the first available valid price
    for col in combined_df.columns:
        first_valid = combined_df[col].iloc[0]
        if first_valid != 0:
            combined_df[col] = (combined_df[col] / first_valid) * 100
            
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
