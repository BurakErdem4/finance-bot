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
def fetch_bist_data():
    """
    Fetches fundamental data for BIST 100 tickers and applies screening logic.
    - Financials/Real Estate: PD/DD < 1.0 (or None)
    - Industrials/Others: FD/FAVOK (EV/EBITDA) < 5.0 (or None)
    """
    tickers = config.BIST_100_TICKERS
    data = []
    
    for symbol in tickers:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Key Data Points
            name = info.get('shortName', symbol)
            sector = info.get('sector', 'Unknown')
            # industry = info.get('industry', 'Unknown')
            
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
                if pb is None:
                    passed = True
                    reason = "PD/DD: Veri Eksik"
                elif pb < 1.0:
                    passed = True
                    reason = f"PD/DD: {pb:.2f} < 1.0"
            else:
                # Sanayi Kriteri: FD/FAVOK < 5.0
                if ev_ebitda is None:
                    passed = True
                    reason = "FD/FAVÖK: Veri Eksik"
                elif ev_ebitda < 5.0 and ev_ebitda > 0:
                     passed = True
                     reason = f"FD/FAVÖK: {ev_ebitda:.2f} < 5.0"
            
            if passed:
                data.append({
                    "Sembol": symbol,
                    "İsim": name,
                    "Sektör": sector,
                    "Fiyat": current_price,
                    "PD/DD": pb if pb is not None else -1, # Handle None for sorting
                    "FD/FAVÖK": ev_ebitda if ev_ebitda is not None else -1,
                    "Öneri": rec_key,
                    "Kriter": reason
                })
                
        except Exception as e:
            continue
            
    return pd.DataFrame(data)

@st.cache_data(ttl=3600)
def fetch_us_etf_data():
    """
    Fetches US ETF data: Returns, Expense Ratio, PE.
    Uses hybrid approach: yfinance + ETF.com scraping fallback/augmentation.
    """
    tickers = config.US_ETFS
    data = []
    
    for symbol in tickers:
        try:
            # 1. Yfinance Base Data
            t = yf.Ticker(symbol)
            info = t.info
            
            # 2. Scrape ETF.com (Augmentation)
            etf_details = fetch_etf_details_from_web(symbol)
            
            # Merge Data
            # Expense Ratio Priority: ETF.com > yfinance
            exp_ratio = 0
            
            if etf_details and etf_details.get('expense_ratio'):
                try:
                    exp_ratio = float(etf_details['expense_ratio'])
                except:
                    # Fallback to yfinance if scrape parse fails
                    y_exp = info.get('annualReportExpenseRatio')
                    exp_ratio = y_exp * 100 if y_exp else 0
            else:
                # Fallback to yfinance completely
                y_exp = info.get('annualReportExpenseRatio')
                exp_ratio = y_exp * 100 if y_exp else 0
            
            # Segment/Category
            category = info.get('category', 'Genel')
            if etf_details and etf_details.get('segment'):
                category = etf_details['segment']
                
            data.append({
                "Sembol": symbol,
                "İsim": info.get('shortName', symbol),
                "YTD Getiri (%)": info.get('ytdReturn', 0) * 100 if info.get('ytdReturn') else 0,
                "Masraf (%)": exp_ratio,
                "PE (F/K)": info.get('trailingPE', 0),
                "Fiyat ($)": info.get('currentPrice', 0),
                "Kategori": category,
                "Issuer": etf_details.get('issuer', info.get('fundFamily', '-')) if etf_details else info.get('fundFamily', '-')
            })
        except:
            continue
            
    return pd.DataFrame(data)
