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
    Analyzes symbols and executes paper trades based on technical score.
    Now includes live progress updates via st.status.
    """
    logs = []
    trades_made = 0
    open_pos = get_open_paper_positions()
    
    with st.status("🔍 Piyasa Taranıyor...", expanded=True) as status:
        for sym in symbols:
            try:
                st.write(f"⏳ **{sym}** taranıyor...")
                yf_sym = sym if "." in sym or "-" in sym else sym + ".IS"
                hist = yf.Ticker(yf_sym).history(period="1y")
                
                if hist.empty:
                    st.write(f"⚠️ {sym} için veri çekilemedi.")
                    continue
                
                signal = get_technical_signals(hist)
                score = signal['score']
                price = hist['Close'].iloc[-1]
                
                # 1. SELL Logic
                if sym in open_pos:
                    if score < 40 or (force_trade and trades_made == 0):
                        qty = open_pos[sym]
                        success, msg = execute_paper_trade(sym, 'SELL', qty, price)
                        log_msg = f"📉 **{sym} taranıyor...** Puan: {score} (SAT EMRİ!)"
                        st.write(log_msg)
                        logs.append(f"🤖 {log_msg}: {msg}")
                        trades_made += 1
                    else:
                        st.write(f"✅ {sym} taranıyor... Puan: {score} (Pozisyon Korunuyor)")
                        
                # 2. BUY Logic
                elif sym not in open_pos:
                    if score > 80 or (force_trade and trades_made == 0):
                        balance = get_virtual_balance()
                        investment = balance * 0.10
                        qty = investment / price
                        success, msg = execute_paper_trade(sym, 'BUY', qty, price)
                        log_msg = f"🚀 **{sym} taranıyor...** Puan: {score} (AL EMRİ!)"
                        st.write(log_msg)
                        logs.append(f"🤖 {log_msg}: {msg}")
                        trades_made += 1
                    else:
                        st.write(f"💠 {sym} taranıyor... Puan: {score} (Yetersiz - Hedef > 80)")
                        
            except Exception as e:
                st.write(f"❌ {sym} hatası: {str(e)}")
                logs.append(f"❌ {sym} hatası: {str(e)}")
        
        status.update(label="✅ Tarama Tamamlandı", state="complete", expanded=False)

    if trades_made == 0:
        st.info("ℹ️ **Tarama Tamamlandı.** Mevcut piyasa koşullarında 80 üzeri puana sahip hisse bulunamadı.")
            
    return logs

def get_paper_history():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM paper_trades ORDER BY id DESC", conn)
    conn.close()
    return df
