import streamlit as st
import borsapy as bp
import pandas as pd
from datetime import datetime

@st.cache_data(ttl=900)
def get_market_summary():
    """
    Fetches daily market info.
    Returns a dictionary with:
    - usd: Current USD/TRY rate
    - eur: Current EUR/TRY rate
    - bond_2y: 2Y Bond yield
    - bond_10y: 10Y Bond yield
    - calendar: DataFrame of upcoming events
    """
    data = {"usd": None, "eur": None, "bond_2y": None, "bond_10y": None, "calendar": None}
    
    # 1. Döviz
    try:
        data["usd"] = bp.FX("USD").current
        data["eur"] = bp.FX("EUR").current
    except: pass
    
    # 2. Tahvil
    try:
        data["bond_2y"] = bp.Bond("2Y").yield_rate
        data["bond_10y"] = bp.Bond("10Y").yield_rate
    except: pass
    
    # 3. Takvim
    try:
        cal = bp.EconomicCalendar()
        events = cal.events(period="1w", country="TR", importance="high")
        if events is not None and not events.empty:
            if 'Date' in events.columns:
                events = events.sort_values(by='Date')
            data["calendar"] = events
    except: pass
    
    return data

def get_daily_info_note():
    # Wrapper for console printing
    print(f"\n>>> Günlük Bilgi Notu Hazırlanıyor ({datetime.now().strftime('%Y-%m-%d')})...")
    data = get_market_summary()
    
    print(f"\n[ Piyasa Özeti ]")
    print(f"USD/TRY: {data['usd']}")
    print(f"EUR/TRY: {data['eur']}")
    print(f"TR 2Y Tahvil: %{data['bond_2y']}")
    print(f"TR 10Y Tahvil: %{data['bond_10y']}")
    
    print(f"\n[ Ekonomik Takvim ]")
    if data['calendar'] is not None:
         cols = ['Date', 'Time', 'Event', 'Actual', 'Forecast', 'Previous']
         display_cols = [c for c in cols if c in data['calendar'].columns]
         print(data['calendar'][display_cols].to_string(index=False))
    else:
        print("Veri yok.")

if __name__ == "__main__":
    get_daily_info_note()
