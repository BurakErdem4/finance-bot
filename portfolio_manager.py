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
    Calculates current holdings and average costs from transactions.
    Returns: List of dicts [{'symbol': 'AAPL', 'quantity': 10, 'avg_cost': 150, 'total_val': 1500}]
    """
    df = get_all_transactions()
    if df.empty:
        return []

    # Group by symbol
    summary = []
    symbols = df['symbol'].unique()

    for sym in symbols:
        sym_df = df[df['symbol'] == sym].sort_values('date')
        
        net_qty = 0
        total_cost = 0
        
        for index, row in sym_df.iterrows():
            if row['type'] == 'BUY':
                # Weighted average cost calculation
                # formula: (old_qty * old_avg + new_qty * new_price) / (old_qty + new_qty)
                new_total_cost = (net_qty * (total_cost / net_qty if net_qty > 0 else 0)) + (row['quantity'] * row['price'])
                net_qty += row['quantity']
                total_cost = new_total_cost
            elif row['type'] == 'SELL':
                # Selling doesn't change average cost of remaining shares, just reduces quantity
                if net_qty >= row['quantity']:
                    avg_cost = total_cost / net_qty
                    net_qty -= row['quantity']
                    total_cost = net_qty * avg_cost if net_qty > 0 else 0
                else:
                    # Over-selling (should handle as 0 or error)
                    net_qty = 0
                    total_cost = 0

        if net_qty > 0:
            avg_cost = total_cost / net_qty
            summary.append({
                "symbol": sym,
                "quantity": round(net_qty, 4),
                "avg_cost": round(avg_cost, 2),
                "total_invested": round(total_cost, 2)
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
