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
    Fetches data for Investment (YAT) and Pension (EMK) funds separately,
    standardizes their columns individually to prevent merge issues,
    and returns a combined DataFrame.
    """
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
    
    # Target columns to keep after renaming
    target_columns = list(column_mapping.values()) + ['Sharpe']
    
    def process_dataframe(df_in):
        if df_in.empty:
            return pd.DataFrame(columns=target_columns)
        
        # 1. Provide Sharpe standardization first
        if 'sharpe_ratio' in df_in.columns:
            df_in = df_in.rename(columns={'sharpe_ratio': 'Sharpe'})
        elif 'sharpe' in df_in.columns:
            df_in = df_in.rename(columns={'sharpe': 'Sharpe'})
        else:
            df_in['Sharpe'] = 0.0

        # 2. Rename main columns
        df_in = df_in.rename(columns=column_mapping)
        
        # 3. Add missing columns with default values 0.0 or ""
        for col in target_columns:
            if col not in df_in.columns:
                # If it's a string column like Title/Code but missing (unlikely), empty string
                if col in ['Fon Kodu', 'Fon Adı']:
                    df_in[col] = "Bilinmiyor"
                else:
                    df_in[col] = 0.0
                    
        # 4. Filter and reorder to strictly match target_columns
        return df_in[target_columns]

    try:
        # A. Fetch Investment Funds
        try:
            raw_yat = bp.screen_funds(fund_type="YAT")
            df_yat = process_dataframe(raw_yat)
            len_yat = len(df_yat)
        except Exception as e:
            print(f"Yatırım fonları çekilemedi: {e}")
            df_yat = pd.DataFrame(columns=target_columns)
            len_yat = 0

        # B. Fetch Pension Funds
        try:
            raw_emk = bp.screen_funds(fund_type="EMK")
            df_emk = process_dataframe(raw_emk)
            len_emk = len(df_emk)
        except Exception as e:
            print(f"Emeklilik fonları çekilemedi: {e}")
            df_emk = pd.DataFrame(columns=target_columns)
            len_emk = 0
            
        # Debug Toast
        st.toast(f"Veri Alındı: {len_yat} Yatırım, {len_emk} Emeklilik Fonu")

        # C. Combine
        df = pd.concat([df_yat, df_emk], ignore_index=True)
        
        if df.empty:
            st.error("Hiçbir fon verisi alınamadı (API yanıt vermiyor olabilir).")
            return pd.DataFrame()
            
        # D. Final Clean-up (Numeric conversions)
        numeric_cols = ["Fiyat", "Günlük (%)", "Aylık (%)", "YTD (%)", "Yıllık (%)", "Sharpe"]
        for col in numeric_cols:
             if col in df.columns:
                 df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Drop duplicates if any overlap
        df = df.drop_duplicates(subset=['Fon Kodu'])

        return df

    except Exception as e:
        st.error(f"Kritik Hata (fetch_tefas_data): {str(e)}")
        return pd.DataFrame()

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
