import streamlit as st
import pandas as pd
import borsapy as bp
import requests
from datetime import datetime

# TEFAS API Endpoints (Legacy/Backup if needed, but we use borsapy now)
# Keeping imports just in case of simple helpers, but strictly using borsapy for data.

@st.cache_data(ttl=3600)
def fetch_tefas_data():
    """
    Fetches latest data using borsapy and adapts it to the app's expected format.
    """
    try:
        # Fetch data using borsapy
        # fund_type="YAT" covers investment funds (Yatırım Fonları)
        df = bp.screen_funds(fund_type="YAT")
        
        if df.empty:
            st.error("Borsapy servistenden veri alınamadı (Boş Tablo).")
            return pd.DataFrame()

        # Rename columns to match app.py expectations
        # Expected by app: "Fon Kodu", "Fon Adı", "Fiyat", "Günlük (%)", "Aylık (%)", "YTD (%)", "Yıllık (%)", "Sharpe"
        # Borsapy likely English columns: code, title, price, return_1m, etc.
        
        col_map = {
            "code": "Fon Kodu",
            "title": "Fon Adı",
            "price": "Fiyat",
            "return_Daily": "Günlük (%)", # Guessing case
            "return_daily": "Günlük (%)",
            "daily_return": "Günlük (%)",
            "return_1m": "Aylık (%)",
            "return_ytd": "YTD (%)", 
            "return_1y": "Yıllık (%)",
            "sharpe": "Sharpe"
        }
        
        # Normalize columns to lower case for matching if needed, but let's try direct map first
        # To be safe, let's copy and rename available columns
        df = df.rename(columns=col_map)
        
        # Fill missing columns with 0 or NaN if they don't exist in source, to prevent app crash
        expected_cols = ["Fon Kodu", "Fon Adı", "Fiyat", "Günlük (%)", "Aylık (%)", "YTD (%)", "Yıllık (%)", "Sharpe"]
        for col in expected_cols:
            if col not in df.columns:
                # Try to find it loosely
                # If "Günlük (%)" missing, maybe "return_1d" exists?
                pass 
                # We won't error out, just let it be missing or add as None
                # df[col] = 0.0 
        
        # Ensure numeric columns are numeric
        numeric_cols = ["Fiyat", "Günlük (%)", "Aylık (%)", "YTD (%)", "Yıllık (%)", "Sharpe"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        return df

    except Exception as e:
        st.error(f"TEFAS Verisi Çekilemedi (Borsapy Hatası): {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_fund_history(codes, lookback_days=365):
    """
    Returns normalized history for chart using borsapy.Fund(code).history()
    """
    if not codes:
        return pd.DataFrame()
        
    try:
        combined_df = pd.DataFrame()
        
        for code in codes:
            # Fetch history for each fund
            # bp.Fund(code).history(period="1y") usually returns Date index and OHLCV or just Close
            fund = bp.Fund(code)
            hist = fund.history(period="1y")
            
            if hist.empty:
                continue
                
            # Expecting 'price' or 'close' column
            # Let's standardize to 'price'
            tgt_col = None
            if 'price' in hist.columns: tgt_col = 'price'
            elif 'Close' in hist.columns: tgt_col = 'Close'
            elif 'close' in hist.columns: tgt_col = 'close'
            
            if tgt_col:
                # Rename to fund code
                series = hist[[tgt_col]].rename(columns={tgt_col: code})
                # Join
                if combined_df.empty:
                    combined_df = series
                else:
                    combined_df = combined_df.join(series, how='outer')
        
        # Post-process
        if not combined_df.empty:
            combined_df = combined_df.sort_index().ffill().dropna()
            
            # Normalize for chart (Start at 0%)
            # ((Price / Start) - 1) * 100
            normalized = combined_df.apply(lambda x: ((x / x.iloc[0]) - 1) * 100 if len(x) > 0 and x.iloc[0] != 0 else x)
            return normalized
            
        return pd.DataFrame()

    except Exception as e:
        # Don't show error on chart usually, just return empty
        print(f"History Fetch Error: {e}")
        st.warning(f"Geçmiş veri alınırken hata: {e}")
        return pd.DataFrame()

# Helper for portfolio lookup (app.py)
# Keeping this for compatibility as app.py logic might rely on it for non-cached real-time checks
@st.cache_data(ttl=900)
def get_fund_price(code):
    try:
        # Use simple screen or fund detail
        f = bp.Fund(code)
        # Try to get latest price from history or detail
        # Some libs have get_price() or similar
        # Fallback to fetching small history
        hist = f.history(period="1wk") # Shortest
        if not hist.empty:
             # Check columns
            if 'price' in hist.columns: return hist['price'].iloc[-1]
            if 'Close' in hist.columns: return hist['Close'].iloc[-1]
    except:
        pass
    return 0
