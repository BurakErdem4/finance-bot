import sqlite3
import pandas as pd
import yfinance as yf
import config

DB_PATH = "finance.db"

def add_transaction(date, symbol, trans_type, quantity, price):
    """Adds a new transaction to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (date, symbol, type, quantity, price)
        VALUES (?, ?, ?, ?, ?)
    ''', (date, symbol.upper(), trans_type, quantity, price))
    conn.commit()
    conn.close()

def get_all_transactions():
    """Returns all transactions as a DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC", conn)
    conn.close()
    return df

def get_real_time_price(symbol):
    """
    Fetches real-time price using yfinance.
    Returns: (price_tl, conversion_rate)
    
    Logic:
    1. Get USD/TRY rate.
    2. Try fetching symbol (if plain, try adding .IS regarding smart logic).
    3. If ends with .IS -> Price is TL (rate=1).
    4. If Foreign -> Price is USD (rate=USDTRY).
    """
    try:
        # 1. Get USD/TRY Rate
        try:
            usd_curr = yf.Ticker("TRY=X").history(period="1d")
            if not usd_curr.empty:
                usd_try = usd_curr['Close'].iloc[-1]
            else:
                usd_try = 35.0 # Fallback
        except:
            usd_try = 35.0

        # 2. Smart Fetch Logic
        # Try as is first
        candidates = [symbol]
        if "." not in symbol and "-" not in symbol:
             # Common input error: User types "THYAO" for BIST
             # But checks checking pure "THYAO" might return nothing or wrong ticker
             # We prioritize .IS for pure strings if they look like BIST? 
             # Or just try .IS as secondary.
             candidates.append(symbol + ".IS")
             
        ticker = None
        data = None
        final_symbol = symbol
        
        for cand in candidates:
            try:
                t = yf.Ticker(cand)
                h = t.history(period="1d")
                if not h.empty:
                    data = h['Close'].iloc[-1]
                    final_symbol = cand
                    break
            except:
                continue
        
        if data is None:
            return None, 1.0

        # 3. Currency Logic
        if final_symbol.endswith(".IS"):
            return data, 1.0
        else:
            # Assume Foreign (Default USD)
            return data * usd_try, usd_try
            
    except Exception as e:
        print(f"Price fetch error for {symbol}: {e}")
        return None, 1.0

def get_portfolio_balance():
    """
    Calculates current holdings, average costs, and current market values with currency conversion.
    Returns: List of dicts enriched with current prices in TL and P/L metrics.
    """
    df = get_all_transactions()
    if df.empty:
        return []

    summary = []
    symbols = df['symbol'].unique()

    for sym in symbols:
        sym_df = df[df['symbol'] == sym].sort_values('date')
        
        net_qty = 0
        total_cost = 0
        
        for index, row in sym_df.iterrows():
            if row['type'] == 'BUY':
                new_total_cost = (net_qty * (total_cost / net_qty if net_qty > 0 else 0)) + (row['quantity'] * row['price'])
                net_qty += row['quantity']
                total_cost = new_total_cost
            elif row['type'] == 'SELL':
                if net_qty >= row['quantity']:
                    avg_cost = total_cost / net_qty
                    net_qty -= row['quantity']
                    total_cost = net_qty * avg_cost if net_qty > 0 else 0
                else:
                    net_qty = 0
                    total_cost = 0

        if net_qty > 0:
            avg_cost = total_cost / net_qty
            
            # Fetch Real Time Price & Rate
            current_price_tl, rate = get_real_time_price(sym)
            
            # Fallback
            if current_price_tl is None:
                current_price_tl = avg_cost # Use cost if live fetch fails
                rate = 1.0 # Assume no conversion if fail
            
            # Calculate metrics
            avg_cost_tl = avg_cost * rate # Convert cost to TL using same rate assumption
            
            total_val_tl = current_price_tl * net_qty
            total_invested_tl = avg_cost_tl * net_qty
            
            profit_tl = total_val_tl - total_invested_tl
            profit_pct = (profit_tl / total_invested_tl * 100) if total_invested_tl > 0 else 0

            summary.append({
                "symbol": sym,
                "quantity": round(net_qty, 4),
                "avg_cost": round(avg_cost, 2), # Original entered cost
                "avg_cost_tl": round(avg_cost_tl, 2), # Converted Cost
                "current_price_tl": round(current_price_tl, 2),
                "total_invested_tl": round(total_invested_tl, 2),
                "total_value_tl": round(total_val_tl, 2),
                "profit_tl": round(profit_tl, 2),
                "profit_pct": round(profit_pct, 2)
            })

    return summary

def get_portfolio_by_category():
    """
    Groups current holdings by category defined in config.SYMBOL_CATEGORIES.
    Returns: Dict {'Category': current_market_value}
    """
    holdings = get_portfolio_balance()
    category_totals = {}
    
    for h in holdings:
        sym = h['symbol']
        category = config.SYMBOL_CATEGORIES.get(sym, "Diğer")
        category_totals[category] = category_totals.get(category, 0) + h['total_value_tl']
        
    return category_totals
