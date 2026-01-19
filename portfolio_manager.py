import sqlite3
import pandas as pd

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

def get_portfolio_balance():
    """
    Calculates current holdings, average costs, and current market values with currency conversion.
    Returns: List of dicts enriched with current prices in TL and P/L metrics.
    """
    import yfinance as yf
    
    df = get_all_transactions()
    if df.empty:
        return []

    # 1. Get USD/TRY rate
    try:
        usdtry = yf.Ticker("TRY=X").history(period="1d")['Close'].iloc[-1]
    except:
        usdtry = 1.0 # Fallback
        
    # Group by symbol
    summary = []
    symbols = df['symbol'].unique()

    for sym in symbols:
        sym_df = df[df['symbol'] == sym].sort_values('date')
        
        net_qty = 0
        total_cost = 0 # This is always stored in whatever currency the price was entered in. 
                       # Assumptions: BIST trades in TL, foreign in USD.
        
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
            
            # 2. Fetch Live Price & Convert to TL
            yf_sym = sym if "-" in sym or "." in sym else sym + ".IS"
            ticker = yf.Ticker(yf_sym)
            try:
                curr_price = ticker.history(period="1d")['Close'].iloc[-1]
            except:
                curr_price = avg_cost # Fallback to cost if fail
            
            # Conversion logic
            is_foreign = not yf_sym.endswith(".IS")
            curr_price_tl = curr_price * usdtry if is_foreign else curr_price
            avg_cost_tl = avg_cost * usdtry if is_foreign else avg_cost
            
            total_val_tl = curr_price_tl * net_qty
            total_invested_tl = avg_cost_tl * net_qty
            
            profit_tl = total_val_tl - total_invested_tl
            profit_pct = (profit_tl / total_invested_tl * 100) if total_invested_tl > 0 else 0

            summary.append({
                "symbol": sym,
                "quantity": round(net_qty, 4),
                "avg_cost": round(avg_cost, 2),
                "avg_cost_tl": round(avg_cost_tl, 2),
                "current_price_tl": round(curr_price_tl, 2),
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
    import yfinance as yf
    import config
    
    holdings = get_portfolio_balance()
    category_totals = {}
    
    for h in holdings:
        sym = h['symbol']
        # Find category
        category = config.SYMBOL_CATEGORIES.get(sym, "Diğer")
        
        # Get current price
        yf_sym = sym if "-" in sym or "." in sym else sym + ".IS"
        try:
            ticker = yf.Ticker(yf_sym)
            curr_price = ticker.history(period="1d")['Close'].iloc[-1]
        except:
            curr_price = h['avg_cost']
            
        curr_total_val = curr_price * h['quantity']
        
        category_totals[category] = category_totals.get(category, 0) + curr_total_val
        
    return category_totals
