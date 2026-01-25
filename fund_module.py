import streamlit as st
import pandas as pd
from tefas import Crawler
from datetime import datetime, timedelta
import numpy as np
import config

# Initialize Crawler
crawler = Crawler()

@st.cache_data(ttl=3600)
def fetch_tefas_data():
    """
    Fetches the latest fund data from TEFAS.
    Returns a DataFrame with columns: Code, Title, Price, Returns, Sharpe (calculated if possible).
    """
    try:
        # Fetch data for today (or recent past if weekend)
        # TEFAS Crawler by default fetches recent data if date not specified or we specify range
        # Usually fetching for 'yesterday' ensures data availability
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3) # Look back a few days to ensure we hit a trading day
        
        # The crawler.fetch returns a DataFrame of history. 
        # To get the "table" of all funds, we usually fetch for a single specific date.
        # However, obtaining the "latest list" might require fetching a small range and taking the last entry per fund.
        
        df = crawler.fetch(start=start_date.strftime("%Y-%m-%d"), 
                           end=end_date.strftime("%Y-%m-%d"),
                           columns=["code", "date", "price", "title"])
        
        if df.empty:
            return pd.DataFrame()
            
        # Get latest data per fund
        df['date'] = pd.to_datetime(df['date'])
        latest_df = df.sort_values('date').groupby('code').last().reset_index()
        
        # We need returns (Day, Month, YTD, Year). 
        # tefas-crawler fetch might not return percentages directly in the basic call depending on columns.
        # Standard columns often include price. We might need to calculating changes or fetch broader columns if supported.
        # Actually, tefas-crawler mostly fetches historical price data.
        # To get the "Table" with returns, we might need to fetch a longer period for all funds and calculate.
        # Optimizing: Fetch 1 Year of data for ALL funds is heavy (millions of rows).
        # Better Strategy: 
        # 1. Fetch latest list.
        # 2. To get returns, we need history points: 1 month ago, 1 year ago, YTD start.
        # This is heavy. Alternatively, does TEFAS have a snapshot endpoint? The crawler mostly traverses history.
        
        # Let's try to simulate the "Table" by fetching distinct points or using what we have.
        # If we cannot easily fetch pre-calculated returns from this library, we might have to rely on
        # checking specific dates.
        
        # Alternative: The user wants a "Professional Analysis Screen".
        # Let's fetch 1 year history for ALL funds? That's too much RAM.
        # Let's fetch last 1 month for lighter load?
        # Or maybe just fetch "Today" and assume the crawler helps?
        # Actually, standard usage often pulls a range.
        
        # Let's refine. We will fetch 1 year data but ONLY for specific columns to save memory, 
        # OR we accept the load. There are ~500 funds. 500 * 250 rows = 125,000 rows. This is handleable in pandas.
        
        lookback = 370 # ~1 Year + buffer
        start_hist = end_date - timedelta(days=lookback)
        
        # Fetching 1 year history for ALL funds
        full_df = crawler.fetch(start=start_hist.strftime("%Y-%m-%d"), 
                                end=end_date.strftime("%Y-%m-%d"),
                                columns=["code", "date", "price", "title"])
                                
        if full_df.empty:
            return pd.DataFrame()
            
        full_df['date'] = pd.to_datetime(full_df['date'])
        full_df = full_df.sort_values(['code', 'date'])
        
        # Pivot or Group to calculate metrics
        # We need: Price, Daily%, Monthly%, YTD%, Annual%, Sharpe
        
        summary_data = []
        risk_free_daily = (getattr(config, 'RISK_FREE_RATE', 0.40) / 252)
        
        # Group processing
        for code, group in full_df.groupby('code'):
            if group.empty: continue
            
            curr_row = group.iloc[-1]
            price = curr_row['price']
            title = curr_row['title']
            
            # Helper to find price N days ago
            def get_pct_change(days_ago_rows):
                if days_ago_rows.empty: return 0
                old_price = days_ago_rows.iloc[0]['price']
                if old_price == 0: return 0
                return ((price - old_price) / old_price) * 100

            # Daily
            # prev_day = group.iloc[-2] if len(group) >= 2 else None
            # pct_day = ...
            pct_day = group['price'].pct_change().iloc[-1] * 100 if len(group) > 1 else 0
            
            # Monthly (approx 22 trading days or 30 calendar days)
            # Find row closest to 30 days ago
            date_30d = curr_row['date'] - timedelta(days=30)
            # Filter distinct dates <= date_30d
            # Optimization: Just take index -22? No, trading days vary.
            # Let's search by date.
            
            # Vectorized or approximate is faster?
            # Let's use simple logic:
            
            # Monthly
            mask_30 = group['date'] <= date_30d
            row_30 = group[mask_30].iloc[-1] if mask_30.any() else group.iloc[0]
            pct_month = ((price - row_30['price']) / row_30['price']) * 100
            
            # Annual
            date_1y = curr_row['date'] - timedelta(days=365)
            mask_1y = group['date'] <= date_1y
            row_1y = group[mask_1y].iloc[-1] if mask_1y.any() else group.iloc[0]
            pct_year = ((price - row_1y['price']) / row_1y['price']) * 100
            
            # YTD
            curr_year = curr_row['date'].year
            date_ytd = datetime(curr_year, 1, 1)
            mask_ytd = group['date'] <= date_ytd
            row_ytd = group[mask_ytd].iloc[-1] if mask_ytd.any() else group.iloc[0] # First data of year or closer
            # Actually YTD base is last year close (Dec 31)
            # Simplification:
            pct_ytd = ((price - row_ytd['price']) / row_ytd['price']) * 100
            
            # Sharpe Ratio (Annualized)
            # Calculate daily returns for last year
            last_year_data = group[group['date'] > date_1y].copy()
            if len(last_year_data) > 10:
                daily_rets = last_year_data['price'].pct_change().dropna()
                mean_ret = daily_rets.mean()
                std_ret = daily_rets.std()
                
                if std_ret > 0:
                    sharpe = (mean_ret - risk_free_daily) / std_ret * np.sqrt(252)
                else:
                    sharpe = 0
            else:
                sharpe = 0
                
            summary_data.append({
                "Fon Kodu": code,
                "Fon Adı": title,
                "Fiyat": price,
                "Günlük (%)": pct_day,
                "Aylık (%)": pct_month,
                "YTD (%)": pct_ytd,
                "Yıllık (%)": pct_year,
                "Sharpe": sharpe
            })
            
        return pd.DataFrame(summary_data)

    except Exception as e:
        print(f"TEFAS Fetch Error: {e}")
        return pd.DataFrame()

def get_fund_history(codes, lookback_days=365):
    """
    Fetches historical data for specific funds for comparison chart.
    Returns normalized DataFrame (starts at 0).
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    try:
        # Fetch only for selected codes? Crawler might not support list filtering in fetch directly efficiently
        # But we can assume we fetch a wider range or filter after.
        # Actually tefas-crawler creates post requests. 
        # If we loop, it is slow. The library documentation suggests fetching all or by column.
        # Let's try fetching all and filtering.
        
        all_hist = crawler.fetch(start=start_date.strftime("%Y-%m-%d"), 
                                 end=end_date.strftime("%Y-%m-%d"),
                                 columns=["code", "date", "price"])
                                 
        if all_hist.empty: return pd.DataFrame()
        
        all_hist['date'] = pd.to_datetime(all_hist['date'])
        
        # Filter codes
        df = all_hist[all_hist['code'].isin(codes)]
        
        # Pivot
        pivot_df = df.pivot(index='date', columns='code', values='price')
        pivot_df = pivot_df.ffill().dropna()
        
        # Normalize
        if not pivot_df.empty:
            normalized = pivot_df.apply(lambda x: ((x / x.iloc[0]) - 1) * 100)
            return normalized
            
        return pd.DataFrame()
        
    except Exception as e:
        print(f"History Error: {e}")
        return pd.DataFrame()

# Old wrapper for compatibility if needed, but not used in new design
def get_fund_analysis(code):
    return {} # Placeholder to prevent import errors if legacy code exists
