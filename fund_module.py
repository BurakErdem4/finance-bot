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
    Fetches latest data using borsapy for both Investment (YAT) and Pension (EMK) funds,
    combines them, and adapts it to the app's expected format.
    """
    try:
        # 1. Fetch Investment Funds
        try:
            df_yat = bp.screen_funds(fund_type="YAT")
            if not df_yat.empty:
                df_yat["Tür"] = "Yatırım"
        except Exception as e:
            print(f"Yatırım fonları çekilemedi: {e}")
            df_yat = pd.DataFrame()

        # 2. Fetch Pension Funds
        try:
            df_emk = bp.screen_funds(fund_type="EMK")
            if not df_emk.empty:
                df_emk["Tür"] = "Emeklilik"
        except Exception as e:
            print(f"Emeklilik fonları çekilemedi: {e}")
            df_emk = pd.DataFrame()

        # 3. Combine DataFrames
        if df_yat.empty and df_emk.empty:
            st.error("Borsapy servisinden veri alınamadı (Yatırım ve Emeklilik fonları boş).")
            return pd.DataFrame()
        
        df = pd.concat([df_yat, df_emk], ignore_index=True)

        # 4. Rename columns to match app.py expectations
        # Expected by app: "Fon Kodu", "Fon Adı", "Fiyat", "Günlük (%)", "Aylık (%)", "YTD (%)", "Yıllık (%)", "Sharpe"
        column_mapping = {
            'fund_code': 'Fon Kodu',
            'name': 'Fon Adı',
            'price': 'Fiyat',
            'return_1m': 'Aylık (%)',
            'return_3m': '3 Aylık (%)',
            'return_6m': '6 Aylık (%)',
            'return_1y': 'Yıllık (%)',
            'return_ytd': 'YTD (%)'
        }
        
        # Apply renaming
        df = df.rename(columns=column_mapping)
        
        # Ensure 'Sharpe' column exists if possible
        if 'sharpe' in df.columns:
            df = df.rename(columns={'sharpe': 'Sharpe'})
        elif 'sharpe_ratio' in df.columns:
            df = df.rename(columns={'sharpe_ratio': 'Sharpe'})
            
        # 5. Clean up and Fill missing numeric columns
        expected_numeric = ["Fiyat", "Günlük (%)", "Aylık (%)", "YTD (%)", "Yıllık (%)", "Sharpe"]
        for col in expected_numeric:
            if col not in df.columns:
                 # Initialize with 0 if missing
                 df[col] = 0.0
            else:
                 df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Keep only relevant columns if possible, but keeping all is safer for now.
        # Ensure 'Tür' is present (it should be)
        if 'Tür' not in df.columns:
            df['Tür'] = 'Belirsiz'

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
