import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import numpy as np
import config

# TEFAS API Endpoints
TEFAS_URL = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"

@st.cache_data(ttl=3600)
def _fetch_raw_tefas_data(lookback_days=370):
    """
    Internal helper to fetch raw history from TEFAS for ALL funds.
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        # TEFAS usually expects this format or similar
        # Payload: fontip="YAT", bastarih="2023-01-01", bittarih="2023-01-30"
        # Check date format: TEFAS often uses ISO or dd.mm.yyyy?
        # Based on common usage, it accepts YYYY-MM-DD or similar in API.
        # Let's use generic formatting likely to work or standard form-data.
        
        payload = {
            "fontip": "YAT",
            "bastarih": start_date.strftime("%d.%m.%Y"),
            "bittarih": end_date.strftime("%d.%m.%Y"),
            "fonkod": "" # All funds
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://www.tefas.gov.tr",
            "Referer": "https://www.tefas.gov.tr/TarihselVeriler.aspx"
        }
        
        # TEFAS API usually accepts Form Data
        response = requests.post(TEFAS_URL, data=payload, headers=headers, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            # API returns a dict with 'data' key usually, or list
            # Structure: { "data": [ ... ] } or [ ... ]
            
            # Handling potential wrapper
            if isinstance(data, dict) and 'data' in data:
                rows = data['data']
            elif isinstance(data, list):
                rows = data
            else:
                return pd.DataFrame()
                
            if not rows:
                return pd.DataFrame()
                
            df = pd.DataFrame(rows)
            # Expected Columns: FONKODU, FONUNADI, TARIH, FIYAT, ...
            
            # Normalize columns
            col_map = {
                "FONKODU": "code",
                "FONUNADI": "title",
                "TARIH": "date",
                "FIYAT": "price"
            }
            df = df.rename(columns=col_map)
            
            # Convert types
            # TARIH comes as milliseconds timestamp usually from TEFAS API JSON? 
            # Or string? If string "1706130000000", need to convert.
            # If standard string, parse.
            
            # Observation: TEFAS API dates often tricky.
            # If it comes as '/Date(1641022800000)/', we need parse.
            # If numeric, easy.
            
            # Safe parsing
            if not df.empty and 'date' in df.columns:
                # Check sample format
                sample = df['date'].iloc[0]
                if isinstance(sample, str) and "/Date(" in sample:
                    # Extract timestamp
                    df['date'] = df['date'].apply(lambda x: datetime.fromtimestamp(int(x.replace("/Date(","").replace(")/",""))/1000) if isinstance(x, str) else x)
                else:
                    df['date'] = pd.to_datetime(df['date']) # Generic parser
                    
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            
            return df
            
        else:
            print(f"TEFAS HTTP Error: {response.status_code}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"TEFAS Helper Error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_tefas_data():
    """
    Fetches latest data and calculates summary metrics (Returns, Sharpe).
    """
    # Lookback 1 year + buffer for annual calc
    raw_df = _fetch_raw_tefas_data(lookback_days=380)
    
    if raw_df.empty:
        return pd.DataFrame()
        
    # Sort
    raw_df = raw_df.sort_values(['code', 'date'])
    
    summary_data = []
    risk_free_daily = (getattr(config, 'RISK_FREE_RATE', 0.40) / 252)
    end_date = raw_df['date'].max()
    
    # Process each fund
    # Optimization: processing 500 funds * 250 rows in pure python loop is slow.
    # Vectorized approach is hard due to varying dates.
    # GroupBy apply is clean.
    
    for code, group in raw_df.groupby('code'):
        if len(group) < 2: continue
        
        curr = group.iloc[-1]
        price = curr['price']
        
        # Check recency (if data is too old, skip?)
        if (end_date - curr['date']).days > 10:
            continue # Dead fund
            
        # Helper for % change
        def get_pct(target_date):
            # Find closest date <= target_date
            # subset = group[group['date'] <= target_date]
            # This is slow inside loop.
            # Faster: use searchsorted logic or just timedelta approx index?
            # group is sorted.
            
            mask = group['date'] <= target_date
            if not mask.any(): 
                return group.iloc[0]['price'] # oldest available
            return group.loc[mask.idxmax()]['price'] # closest on or before

        # Dates
        d_1d = curr['date'] - timedelta(days=1) # Or simple prev row
        d_1m = curr['date'] - timedelta(days=30)
        d_ytd = datetime(curr['date'].year, 1, 1)
        d_1y = curr['date'] - timedelta(days=365)
        
        # Prices
        p_1d = group.iloc[-2]['price'] # Prev row guaranteed by len check
        p_1m = get_pct(d_1m)
        p_ytd = get_pct(d_ytd)
        p_1y = get_pct(d_1y)
        
        # Returns
        r_day = ((price - p_1d) / p_1d) * 100 if p_1d else 0
        r_mon = ((price - p_1m) / p_1m) * 100 if p_1m else 0
        r_ytd = ((price - p_ytd) / p_ytd) * 100 if p_ytd else 0
        r_yar = ((price - p_1y) / p_1y) * 100 if p_1y else 0
        
        # Sharpe
        # Data in last 1 year
        last_year_mask = group['date'] > d_1y
        group_1y = group[last_year_mask]
        
        sharpe = 0
        if len(group_1y) > 30:
            daily_series = group_1y['price'].pct_change().dropna()
            std = daily_series.std()
            mean = daily_series.mean()
            if std > 0:
                sharpe = (mean - risk_free_daily) / std * np.sqrt(252)
                
        summary_data.append({
            "Fon Kodu": code,
            "Fon Adı": curr['title'],
            "Fiyat": price,
            "Günlük (%)": r_day,
            "Aylık (%)": r_mon,
            "YTD (%)": r_ytd,
            "Yıllık (%)": r_yar,
            "Sharpe": sharpe
        })
        
    return pd.DataFrame(summary_data)

def get_fund_history(codes, lookback_days=365):
    """
    Returns normalized history for chart.
    Uses generic fetch but filters for codes.
    """
    if not codes: return pd.DataFrame()
    
    # We could reuse the internal helper. 
    # For efficiency, if users select few funds, we might want to fetch only those if API supports?
    # TEFAS API allows `fonkod` (comma separated?). 
    # If not, we fetch all. Fetching all is cached so it's fine.
    
    raw_df = _fetch_raw_tefas_data(lookback_days=lookback_days)
    if raw_df.empty: return pd.DataFrame()
    
    # Filter
    df = raw_df[raw_df['code'].isin(codes)].copy()
    
    # Pivot
    pivot = df.pivot(index='date', columns='code', values='price')
    pivot = pivot.ffill().dropna()
    
    # Normalize
    if not pivot.empty:
        normalized = pivot.apply(lambda x: ((x / x.iloc[0]) - 1) * 100)
        return normalized
        
    return pd.DataFrame()

# Helper for portfolio lookup (app.py) if needed
@st.cache_data(ttl=900)
def get_fund_price(code):
    try:
        # Fetch small history
        # Create a payload just for this fund?
        payload = {
            "fontip": "YAT",
            "bastarih": (datetime.now() - timedelta(days=5)).strftime("%d.%m.%Y"),
            "bittarih": datetime.now().strftime("%d.%m.%Y"),
            "fonkod": code
        }
        headers = {
             "User-Agent": "Mozilla/5.0",
             "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
              "Origin": "https://www.tefas.gov.tr",
            "Referer": "https://www.tefas.gov.tr/TarihselVeriler.aspx"
        }
        r = requests.post(TEFAS_URL, data=payload, headers=headers)
        if r.status_code == 200:
             d = r.json().get('data', [])
             if d: return d[-1]['FIYAT']
    except:
        pass
    return 0
