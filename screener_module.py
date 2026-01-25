import streamlit as st
import yfinance as yf
import pandas as pd
import config
import requests
from bs4 import BeautifulSoup
import time

def fetch_etf_details_from_web(ticker):
    """
    Scrapes ETF.com for Expense Ratio, Segment, and Issuer.
    Returns dict or None.
    """
    url = f"https://www.etf.com/{ticker}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        details = {}
        
        # Scrape Strategy: Find text labels and look for values nearby
        # This is generic and robust to some layout changes
        
        # 1. Expense Ratio
        # Usually "Expense Ratio" followed by value in a list or table
        # We try to find the label and get the text of the next element or parent
        try:
            er_elem = soup.find(string="Expense Ratio")
            if er_elem:
                # Layout dependent: usually parent -> sibling or similar.
                # ETF.com typical layout: <div><span>Title</span><span>Value</span></div>
                er_val_elem = er_elem.find_next("span", class_="field-content") 
                if not er_val_elem: # Try parent's sibling
                     er_val_elem = er_elem.parent.find_next_sibling()
                
                if er_val_elem:
                    details['expense_ratio'] = er_val_elem.get_text(strip=True).replace('%','')
        except:
            pass
            
        # 2. Segment
        try:
            seg_elem = soup.find(string="Segment")
            if seg_elem:
                seg_val_elem = seg_elem.find_next("span", class_="field-content")
                if not seg_val_elem:
                     seg_val_elem = seg_elem.parent.find_next_sibling()
                if seg_val_elem:
                    details['segment'] = seg_val_elem.get_text(strip=True)
        except:
            pass

        # 3. Issuer
        try:
            iss_elem = soup.find(string="Issuer")
            if iss_elem:
                iss_val = iss_elem.find_next("span", class_="field-content")
                if not iss_val:
                     iss_val = iss_elem.parent.find_next_sibling()
                if iss_val:
                    details['issuer'] = iss_val.get_text(strip=True)
        except:
            pass
            
        return details if details else None
        
    except Exception as e:
        # print(f"Scraping error for {ticker}: {e}")
        return None

@st.cache_data(ttl=1800) 
@st.cache_data(ttl=1800) 
def fetch_bist_data():
    """
    Fetches data for BIST 100 tickers using a robust method:
    1. Prices from History (Guaranteed even if market closed)
    2. Fundamentals from Info (If missing, keep ticker)
    3. Sorts by Valuation Score (primary) and Daily Change (secondary)
    """
    tickers = config.BIST_100_TICKERS
    data = []
    
    for symbol in tickers:
        try:
            ticker = yf.Ticker(symbol)
            
            # A. Robust Price Fetch (History)
            # Fetch last 5 days to ensure we get a valid close even after weekends/holidays
            hist = ticker.history(period="5d")
            
            if hist.empty:
                # If history fails, completely skip (dead ticker?)
                continue
                
            current_price = hist['Close'].iloc[-1]
            
            # Calculate Daily Change (%)
            pct_change = 0
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                pct_change = ((current_price - prev_close) / prev_close) * 100
            
            # B. Fundamentals (Info) - Tolerant
            info = ticker.info
            name = info.get('shortName', symbol)
            sector = info.get('sector', 'Unknown')
            
            pb = info.get('priceToBook') # PD/DD
            ev_ebitda = info.get('enterpriseToEbitda') # FD/FAVÖK
            
            # C. Scoring Logic
            # Goal: Rank by cheapness if possible. If not, fallback to neutral.
            score = 100 # Default neutral/high score
            note = ""
            
            is_finance_re = sector in ['Financial Services', 'Real Estate']
            
            has_fundamental_data = False
            
            if is_finance_re:
                # Banka/GYO Rule: PD/DD
                if pb is not None:
                    score = pb
                    has_fundamental_data = True
                    if pb < 1.0:
                        note = "🔥 sudan ucuz (PD/DD)"
                    else:
                        note = "Sektör: Finans"
            else:
                # Industry Rule: FD/FAVÖK
                if ev_ebitda is not None:
                     score = ev_ebitda
                     has_fundamental_data = True
                     if ev_ebitda < 5.0 and ev_ebitda > 0:
                         note = "💎 Potansiyel (FD/FAVÖK)"
                     else:
                        note = "Sektör: Sanayi/Hizmet"
            
            # If no fundamental data, set score high so they appear at bottom (or sorted by return)
            if not has_fundamental_data:
                score = 999
                note = "Veri Yok"

            data.append({
                "Sembol": symbol,
                "İsim": name,
                "Sektör": sector,
                "Fiyat": current_price,
                "Günlük (%)": pct_change,
                "PD/DD": pb if pb is not None else -1,
                "FD/FAVÖK": ev_ebitda if ev_ebitda is not None else -1,
                "Skor": score,
                "Analiz Notu": note
            })
                
        except Exception as e:
            # print(f"Error {symbol}: {e}")
            continue

    # Create DF
    df = pd.DataFrame(data)
    
    if not df.empty:
        # Sort Logic:
        # 1. By Score Ascending (Cheaper is better)
        # 2. If Scores are high (999), Sort by Daily Return Descending (Show gainers)
        df = df.sort_values(by=["Skor", "Günlük (%)"], ascending=[True, False])
        
    return df

@st.cache_data(ttl=3600)
def fetch_us_etf_data():
    """
    Fetches US ETF data using a Hybrid Approach:
    - Static Data (Name, Segment, Expense): Hardcoded DB (Guaranteed)
    - Dynamic Data (Price, Change): yfinance
    """
    
    # Static Database (Guaranteed Data)
    ETF_DB = {
        'QQQ': {'name': 'Invesco QQQ (Nasdaq 100)', 'segment': 'Teknoloji', 'expense': 0.20},
        'SPY': {'name': 'SPDR S&P 500', 'segment': 'Genel Pazar', 'expense': 0.09},
        'VTI': {'name': 'Vanguard Total Stock', 'segment': 'Genel Pazar', 'expense': 0.03},
        'VOO': {'name': 'Vanguard S&P 500', 'segment': 'Genel Pazar', 'expense': 0.03},
        'GLD': {'name': 'SPDR Gold Shares', 'segment': 'Emtia (Altın)', 'expense': 0.40},
        'SLV': {'name': 'iShares Silver Trust', 'segment': 'Emtia (Gümüş)', 'expense': 0.50},
        'ARKK': {'name': 'ARK Innovation', 'segment': 'İnovasyon', 'expense': 0.75},
        'XLF': {'name': 'Financial Select Sector', 'segment': 'Finans', 'expense': 0.10},
        'XLE': {'name': 'Energy Select Sector', 'segment': 'Enerji', 'expense': 0.10},
        'XLK': {'name': 'Technology Select Sector', 'segment': 'Teknoloji', 'expense': 0.10},
        'SMH': {'name': 'VanEck Semiconductor', 'segment': 'Yarı İletken', 'expense': 0.35},
        'SCHD': {'name': 'Schwab US Dividend', 'segment': 'Temettü', 'expense': 0.06}
    }
    
    data = []
    
    for symbol, static_info in ETF_DB.items():
        try:
            # Dynamic Fetch
            t = yf.Ticker(symbol)
            hist = t.history(period="5d") # Fetch slightly more to ensure % change calc
            
            price = 0
            ytd_ret = 0
            
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                # Calculate simple return (approx YTD or just recent move?)
                # Requested "YTD Return" in previous prompts. yfinance info has 'ytdReturn'.
                # Let's try info, if fails, use 0
                pass
            
            # Fetch Info for YTD Return
            info = t.info
            ytd_ret = info.get('ytdReturn', 0) * 100 if info.get('ytdReturn') else 0
            if price == 0: price = info.get('currentPrice', 0)

            data.append({
                "Sembol": symbol,
                "İsim": static_info['name'],
                "Kategori": static_info['segment'],
                "Fiyat ($)": price,
                "YTD Getiri (%)": ytd_ret,
                "Masraf (%)": static_info['expense']
            })
            
        except:
            # Fallback even if dynamic fail: Show Static + 0 Price
            data.append({
                "Sembol": symbol,
                "İsim": static_info['name'],
                "Kategori": static_info['segment'],
                "Fiyat ($)": 0,
                "YTD Getiri (%)": 0,
                "Masraf (%)": static_info['expense']
            })
            continue
            
    return pd.DataFrame(data)
