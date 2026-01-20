import yfinance as yf
import pandas as pd
import streamlit as st
import numpy as np

@st.cache_data(ttl=3600)
def get_benchmark_data():
    """
    Fetches 1 year of historical data for USD, Gold, and BIST30.
    Implementation follows the 'Zırhlı Yapı' (Armored Structure) requirements.
    """
    symbols = {
        "Dolar (USD/TRY)": "TRY=X",
        "Altın (Ons)": "GC=F",
        "BIST 30": "XU030.IS"
    }
    
    # Adım 1 (Zaman Omurgası): 365 günlük boş Master DataFrame
    # Saat farkı yüzünden eşleşmeme sorununu çözmek için .normalize() kullanıyoruz (Gece 00:00 yapar)
    end_date = pd.Timestamp.now().normalize()
    start_date = end_date - pd.DateOffset(years=1)
    master_index = pd.date_range(start=start_date, end=end_date, freq='D')
    master_df = pd.DataFrame(index=master_index)
    
    found_any = False
    
    # Adım 2 (Bağımsız İndirme)
    for label, sym in symbols.items():
        try:
            ticker = yf.Ticker(sym)
            # Fetch data (ensure we get enough history)
            data = ticker.history(period="1y")['Close']
            
            if not data.empty:
                # Adım 3 (Akıllı Birleştirme)
                # Remove timezone if exists
                if data.index.tz is not None:
                    data.index = data.index.tz_localize(None)
                
                # Normalize data index to midnight to match master_index
                data.index = data.index.normalize()
                
                # Duplicate index protection (rare but possible after normalize)
                data = data.groupby(data.index).last()
                
                # Reindex data to the master timeline (this performs the join)
                aligned_data = data.reindex(master_index)
                master_df[label] = aligned_data
                found_any = True
            else:
                st.warning(f"⚠️ {label} verisi çekilemedi (Yahoo Finance boş döndü).")
        except Exception as e:
            # Adım 5 (Hata Toleransı): Kod çökmez, sadece uyarı verir.
            print(f"Benchmark Warning ({label}): {e}")
            st.warning(f"⚠️ {label} güncel verisi alınamadı.")
            
    if not found_any:
        st.error("Hiçbir benchmark verisi alınamadı. İnternet bağlantınızı kontrol edin.")
        return pd.DataFrame()
        
    # Adım 4 (Boşluk Doldurma): Forward Fill (Cuma -> Haftasonu)
    # Simülasyon (random) KESİNLİKLE YOK.
    master_df = master_df.ffill()
    
    # Baştaki olası boşlukları doldur
    master_df = master_df.bfill()
    
    # Sütunları temizle (Tamamen boş olanları at)
    master_df = master_df.dropna(axis=1, how='all')
    
    # Normalize: Base 100
    for col in master_df.columns:
        first_valid = master_df[col].iloc[0]
        if first_valid and first_valid != 0:
            master_df[col] = (master_df[col] / first_valid) * 100
            
    return master_df

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
