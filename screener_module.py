import streamlit as st
import yfinance as yf
import pandas as pd
import config

@st.cache_data(ttl=1800) # Cache for 30 mins
def fetch_bist_data():
    """
    Fetches fundamental data for BIST 100 tickers and applies screening logic.
    - Financials/Real Estate: PD/DD < 1.0
    - Industrials/Others: FD/FAVOK (EV/EBITDA) < 5.0
    """
    tickers = config.BIST_100_TICKERS
    data = []
    
    # Progress bar simulation logic on frontend usually, but here we scan
    
    for symbol in tickers:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Key Data Points
            name = info.get('shortName', symbol)
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            
            # Fundamentals
            pb = info.get('priceToBook') # PD/DD
            ev_ebitda = info.get('enterpriseToEbitda') # FD/FAVÖK
            pe = info.get('trailingPE')
            rec_key = info.get('recommendationKey', 'none').lower()
            
            current_price = info.get('currentPrice')
            
            # Screening Logic
            passed = False
            reason = ""
            
            is_finance_re = sector in ['Financial Services', 'Real Estate']
            
            if is_finance_re:
                # Banka/GYO Kriteri: PD/DD < 1.0
                if pb is not None and pb < 1.0:
                    passed = True
                    reason = f"PD/DD: {pb:.2f} < 1.0"
            else:
                # Sanayi Kriteri: FD/FAVOK < 5.0
                if ev_ebitda is not None and ev_ebitda < 5.0 and ev_ebitda > 0:
                     passed = True
                     reason = f"FD/FAVÖK: {ev_ebitda:.2f} < 5.0"
            
            # Optional: Add regardless if 'buy' recommendation?
            # User said: If recommendationKey == 'buy', prioritize.
            # But primarily filter by fundamentals.
            # Let's include everything but mark 'passed' ones, OR only return passed ones.
            # "fetch_bist_data... Sonuçları bir DataFrame olarak döndür." implies screening result.
            
            if passed:
                data.append({
                    "Sembol": symbol,
                    "İsim": name,
                    "Sektör": sector,
                    "Fiyat": current_price,
                    "PD/DD": pb,
                    "FD/FAVÖK": ev_ebitda,
                    "Öneri": rec_key,
                    "Kriter": reason
                })
                
        except Exception as e:
            # print(f"Error fetching {symbol}: {e}")
            continue
            
    return pd.DataFrame(data)

@st.cache_data(ttl=3600)
def fetch_us_etf_data():
    """
    Fetches US ETF data: Returns, Expense Ratio, PE.
    """
    tickers = config.US_ETFS
    data = []
    
    for symbol in tickers:
        try:
            t = yf.Ticker(symbol)
            info = t.info
            
            data.append({
                "Sembol": symbol,
                "İsim": info.get('shortName', symbol),
                "YTD Getiri (%)": info.get('ytdReturn', 0) * 100 if info.get('ytdReturn') else 0,
                "Masraf (%)": info.get('annualReportExpenseRatio', 0) * 100 if info.get('annualReportExpenseRatio') else 0,
                "PE (F/K)": info.get('trailingPE', 0),
                "Fiyat ($)": info.get('currentPrice', 0)
            })
        except:
            continue
            
    return pd.DataFrame(data)
