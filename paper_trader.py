import sqlite3
import pandas as pd
from datetime import datetime
import yfinance as yf
from analysis_module import get_technical_signals
import config

DB_PATH = "finance.db"

def get_virtual_balance():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM paper_settings WHERE key = 'virtual_balance'")
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 100000.0

def update_virtual_balance(new_balance):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE paper_settings SET value = ? WHERE key = 'virtual_balance'", (new_balance,))
    conn.commit()
    conn.close()

def get_open_paper_positions():
    """Returns a list of symbols and their net quantity in paper trading."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT symbol, type, quantity FROM paper_trades", conn)
    conn.close()
    
    if df.empty:
        return {}
        
    summary = {}
    for _, row in df.iterrows():
        sym = row['symbol']
        qty = row['quantity']
        if row['type'] == 'BUY':
            summary[sym] = summary.get(sym, 0) + qty
        else:
            summary[sym] = summary.get(sym, 0) - qty
            
    return {k: v for k, v in summary.items() if v > 0.0001}

def execute_paper_trade(symbol, trade_type, quantity, price):
    balance = get_virtual_balance()
    commission = price * quantity * 0.002 # %0.2 commission
    
    if trade_type == 'BUY':
        cost = (price * quantity) + commission
        if cost > balance:
            return False, "Yetersiz sanal bakiye."
        new_balance = balance - cost
    else: # SELL
        earnings = (price * quantity) - commission
        new_balance = balance + earnings
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO paper_trades (date, symbol, type, quantity, price, commission, balance_after)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (datetime.now().strftime("%Y-%m-%d %H:%M"), symbol, trade_type, quantity, price, commission, new_balance))
    conn.commit()
    conn.close()
    
    update_virtual_balance(new_balance)
    return True, "İşlem başarılı."

import streamlit as st

def run_paper_bot(symbols, force_trade=False):
    """
    Analyzes all symbols first, ranks them by score, and picks the BEST one.
    Scan & Sort Strategy.
    """
    logs = []
    scanned_results = []
    open_pos = get_open_paper_positions()
    
    with st.status("🔍 Piyasa Taranıyor (Best-Pick Modu)...", expanded=True) as status:
        for sym in symbols:
            try:
                st.write(f"⏳ **{sym}** analiz ediliyor...")
                yf_sym = sym if "." in sym or "-" in sym else sym + ".IS"
                hist = yf.Ticker(yf_sym).history(period="1y")
                
                if hist.empty:
                    st.write(f"⚠️ {sym} verisi çekilemedi.")
                    continue
                
                signal = get_technical_signals(hist)
                score = signal['score']
                price = hist['Close'].iloc[-1]
                
                scanned_results.append({
                    "symbol": sym,
                    "score": score,
                    "price": price
                })
                st.write(f"📊 {sym}: Puan **{score}**")
                        
            except Exception as e:
                st.write(f"❌ {sym} hatası: {str(e)}")
        
        # Sort by score descending
        scanned_results = sorted(scanned_results, key=lambda x: x['score'], reverse=True)
        
        status.update(label="✅ Tarama Tamamlandı. Karar Aşaması...", state="complete", expanded=False)

    if not scanned_results:
        st.warning("Hiçbir hisse senedi verisi analiz edilemedi.")
        return []

    # Karar Mekanizması
    best_pick = scanned_results[0]
    best_sym = best_pick['symbol']
    best_score = best_pick['score']
    best_price = best_pick['price']

    # 1. SELL Check (Existing positions)
    # We still check for sales normally or we can keep it as is.
    # User's request focused on BUYING logic, but let's maintain sanity for SELLING too.
    for sym in open_pos:
        # If open position score is bad, sell.
        # Finding the current score for the open position from our scan
        match = next((item for item in scanned_results if item["symbol"] == sym), None)
        if match and match['score'] < 40:
            qty = open_pos[sym]
            success, msg = execute_paper_trade(sym, 'SELL', qty, match['price'])
            logs.append(f"🤖 **{sym}** SATILDI (Düşük Puan: {match['score']}): {msg}")

    # 2. BUY Logic (Best-Pick)
    if best_sym not in open_pos:
        if best_score > 80 or force_trade:
            reason = "Güçlü Sinyal (>80)" if best_score > 80 else f"Test Modu (En yüksek puan: {best_score})"
            st.success(f"🏆 **Kazanan Hisse: {best_sym} ({best_score} Puan)**")
            st.info(f"💡 Neden: {reason}. Alım emri giriliyor...")
            
            balance = get_virtual_balance()
            investment = balance * 0.10
            qty = investment / best_price
            success, msg = execute_paper_trade(best_sym, 'BUY', qty, best_price)
            logs.append(f"🤖 **{best_sym}** ALINDI ({best_score} Puan): {msg}")
        else:
            st.info(f"ℹ️ **En iyi tercih {best_sym} ({best_score} Puan)** ancak hedef 80+ puan bulunamadı.")
    else:
        st.info(f"ℹ️ En yüksek puanlı hisse {best_sym} zaten portföyünüzde bulunuyor.")
            
    return logs

def get_paper_history():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM paper_trades ORDER BY id DESC", conn)
    conn.close()
    return df
