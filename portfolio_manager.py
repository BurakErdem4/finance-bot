import sqlite3
import pandas as pd
import yfinance as yf
import config

DB_PATH = "finance.db"

def add_transaction(date, symbol, trans_type, quantity, price, user_email):
    """Adds a new transaction to the database for a specific user."""
    if not user_email or user_email == "guest":
        return # Block guests or invalid
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (date, user_email, symbol, type, quantity, price)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (date, user_email, symbol.upper(), trans_type, quantity, price))
    conn.commit()
    conn.close()

def get_all_transactions(user_email):
    """Returns all transactions for a specific user as a DataFrame."""
    if not user_email or user_email == "guest":
        return pd.DataFrame()
        
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM transactions WHERE user_email = ? ORDER BY date DESC", conn, params=(user_email,))
    conn.close()
    return df

def get_real_time_price(symbol):
    """
    Fetches real-time price using yfinance.
    Returns: (price_tl, conversion_rate)
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
        candidates = [symbol]
        if "." not in symbol and "-" not in symbol:
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

def get_portfolio_balance(user_email):
    """
    Calculates current holdings for a specific user.
    """
    df = get_all_transactions(user_email)
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

def get_portfolio_by_category(user_email):
    """
    Groups current holdings by category for a specific user.
    """
    holdings = get_portfolio_balance(user_email)
    category_totals = {}
    
    for h in holdings:
        sym = h['symbol']
        category = config.SYMBOL_CATEGORIES.get(sym, "Diğer")
        category_totals[category] = category_totals.get(category, 0) + h['total_value_tl']
        
    return category_totals

def get_benchmark_data(period="1y", custom_ticker=None):
    """
    Fetches historical data for benchmarks: BIST 100, USD/TRY, Gold (Gram/Ons), Bitcoin.
    Also fetches custom_ticker if provided.
    Returns DataFrame with normalized or raw prices.
    """
    benchmarks = {
        "BIST 100": "XU100.IS",
        "Dolar/TL": "TRY=X",
        "Altın (Ons)": "GC=F",
        "Bitcoin": "BTC-USD"
    }
    
    if custom_ticker:
        # Use the ticker itself as the label for simplicity, uppercase for consistency
        benchmarks[f"Rakip: {custom_ticker.upper()}"] = custom_ticker.upper()
    
    df_list = []
    
    for name, sym in benchmarks.items():
        try:
            hist = yf.Ticker(sym).history(period=period)['Close']
            if hist.empty:
                print(f"Benchmark warning: No data for {sym}")
                continue
                
            # Adjust timezone
            if hist.index.tz is not None:
                hist.index = hist.index.tz_localize(None)
            hist.name = name
            df_list.append(hist)
        except Exception as e:
            print(f"Benchmark fetch error {name} ({sym}): {e}")
            
    if df_list:
        combined = pd.concat(df_list, axis=1)
        combined = combined.ffill().dropna()
        return combined
    return pd.DataFrame()

def get_portfolio_history(holdings, period="1y"):
    """
    Approximates portfolio history assuming current holdings were held constant over the period.
    Returns: Series (Total Value in TL over time)
    """
    if not holdings:
        return pd.Series()
        
    total_series = None
    usd_rate_history = None
    
    # Pre-fetch USD history if needed for conversion
    # We'll fetch it once to reuse
    try:
        usd_rate_history = yf.Ticker("TRY=X").history(period=period)['Close']
        if usd_rate_history.index.tz is not None:
            usd_rate_history.index = usd_rate_history.index.tz_localize(None)
    except:
        pass
        
    for h in holdings:
        sym = h['symbol']
        qty = h['quantity']
        
        # Determine ticker
        ticker_sym = sym
        if "." not in sym and "-" not in sym:
             ticker_sym = sym + ".IS" # Fallback/Assumption
        
        try:
            hist = yf.Ticker(ticker_sym).history(period=period)['Close']
            if hist.empty: continue
            
            if hist.index.tz is not None:
                hist.index = hist.index.tz_localize(None)
                
            # Currency Conversion
            # Logic: If name ends with .IS, it is TL. Else USD.
            # This is a simplification.
            is_tl = ticker_sym.endswith(".IS")
            
            if not is_tl and usd_rate_history is not None:
                # Align dates
                aligned_usd = usd_rate_history.reindex(hist.index).ffill()
                val_history = hist * qty * aligned_usd
            else:
                val_history = hist * qty
                
            if total_series is None:
                total_series = val_history
            else:
                total_series = total_series.add(val_history, fill_value=0)
                
        except Exception as e:
            print(f"History error {sym}: {e}")
            
    return total_series.dropna() if total_series is not None else pd.Series()
