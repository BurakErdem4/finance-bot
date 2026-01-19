import pandas as pd
import numpy as np
from analysis_module import calculate_sma, calculate_rsi

from strategies import get_smart_dca_multiplier

def run_backtest(df, strategy_name, initial_capital=1000, monthly_dca=0):
    """
    Simulates a trading strategy on historical data.
    Supports Lump Sum or DCA.
    """
    if df is None or df.empty:
        return None
    
    data = df.copy()
    commission_rate = 0.002 # %0.2
    
    # Calculate Indicators
    data['SMA200'] = calculate_sma(data, 200)
    data['RSI'] = calculate_rsi(data)
    
    # Simulation variables
    cash = initial_capital
    position = 0 # Units held
    equity_curve = []
    trade_count = 0
    total_invested = initial_capital
    
    last_month = -1
    
    for i in range(len(data)):
        price = data['Close'].iloc[i]
        date = data.index[i]
        
        # DCA Logic (First trading day of month)
        if monthly_dca > 0 and date.month != last_month:
            multiplier = 1.0
            if strategy_name == 'Smart DCA':
                multiplier = get_smart_dca_multiplier(data.iloc[i])
            
            added_cash = monthly_dca * multiplier
            cash += added_cash
            total_invested += added_cash
            last_month = date.month
            
            # Auto-buy for DCA (Monthly Buy)
            units_to_buy = cash / (price * (1 + commission_rate))
            position += units_to_buy
            cash = 0
            trade_count += 1

        # Logic for Lump Sum Strategies
        if monthly_dca == 0:
            if strategy_name == 'RSI Stratejisi (30/70)':
                rsi_val = data['RSI'].iloc[i]
                if rsi_val < 30 and position == 0 and not np.isnan(rsi_val):
                    units_to_buy = cash / (price * (1 + commission_rate))
                    position = units_to_buy
                    cash = 0
                    trade_count += 1
                elif rsi_val > 70 and position > 0 and not np.isnan(rsi_val):
                    cash = position * price * (1 - commission_rate)
                    position = 0
                    trade_count += 1
            elif strategy_name == 'Al ve Tut' and i == 0:
                units_to_buy = cash / (price * (1 + commission_rate))
                position = units_to_buy
                cash = 0
                trade_count = 1
        
        # Track total equity value
        current_equity = cash + (position * price)
        equity_curve.append(current_equity)
    
    final_equity = equity_curve[-1]
    total_return_pct = ((final_equity / total_invested) - 1) * 100
    
    result_df = pd.DataFrame(index=data.index)
    result_df['Strategy_Equity'] = equity_curve
    result_df['Price'] = data['Close']
    
    # Benchmark Comparison (Always vs Lump Sum Buy & Hold for simplicity)
    first_price = data['Close'].iloc[0]
    result_df['BuyHold_Equity'] = (data['Close'] / first_price) * initial_capital * (1 - commission_rate)

    metrics = {
        "initial_capital": initial_capital,
        "total_invested": round(total_invested, 2),
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return_pct, 2),
        "trade_count": trade_count,
        "strategy_name": strategy_name
    }
    
    return {
        "metrics": metrics,
        "equity_curve": result_df
    }

def run_periodic_backtest(df, strategy_name, initial_capital):
    """
    Splits data by year and runs backtest for each segment.
    """
    if df is None or df.empty:
        return []
        
    years = df.index.year.unique()
    results = []
    
    for year in years:
        year_data = df[df.index.year == year]
        if len(year_data) < 20: continue # Skip if very few days
        
        res = run_backtest(year_data, strategy_name, initial_capital)
        if res:
            res['metrics']['year'] = year
            results.append(res)
            
    return results
