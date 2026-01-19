import pandas as pd
import numpy as np
from analysis_module import calculate_sma, calculate_rsi

def run_backtest(df, strategy_name, initial_capital=1000):
    """
    Simulates a trading strategy on historical data.
    
    Args:
        df (DataFrame): Historical data with 'Close' column.
        strategy_name (str): 'RSI Stratejisi (30/70)', 'SMA Cross (50/200)', or 'Al ve Tut'.
        initial_capital (float): Starting cash.
        
    Returns:
        dict: { 'metrics': dict, 'equity_curve': DataFrame }
    """
    if df is None or df.empty:
        return None
    
    data = df.copy()
    commission_rate = 0.002 # %0.2
    
    # Calculate Indicators
    data['SMA50'] = calculate_sma(data, 50)
    data['SMA200'] = calculate_sma(data, 200)
    data['RSI'] = calculate_rsi(data)
    
    # Simulation variables
    cash = initial_capital
    position = 0 # Units held
    equity_curve = []
    trade_count = 0
    
    for i in range(len(data)):
        price = data['Close'].iloc[i]
        date = data.index[i]
        
        # Strategy Logic
        if strategy_name == 'RSI Stratejisi (30/70)':
            rsi_val = data['RSI'].iloc[i]
            if rsi_val < 30 and position == 0 and not np.isnan(rsi_val):
                # BUY
                units_to_buy = cash / (price * (1 + commission_rate))
                position = units_to_buy
                cash = 0
                trade_count += 1
            elif rsi_val > 70 and position > 0 and not np.isnan(rsi_val):
                # SELL
                cash = position * price * (1 - commission_rate)
                position = 0
                trade_count += 1
                
        elif strategy_name == 'SMA Cross (50/200)':
            sma50 = data['SMA50'].iloc[i]
            sma200 = data['SMA200'].iloc[i]
            if not np.isnan(sma50) and not np.isnan(sma200):
                if sma50 > sma200 and position == 0:
                    # BUY
                    units_to_buy = cash / (price * (1 + commission_rate))
                    position = units_to_buy
                    cash = 0
                    trade_count += 1
                elif sma50 < sma200 and position > 0:
                    # SELL
                    cash = position * price * (1 - commission_rate)
                    position = 0
                    trade_count += 1
                    
        elif strategy_name == 'Al ve Tut':
            if i == 0:
                # BUY once at the start
                units_to_buy = cash / (price * (1 + commission_rate))
                position = units_to_buy
                cash = 0
                trade_count = 1
        
        # Track total equity value
        current_equity = cash + (position * price)
        equity_curve.append(current_equity)
    
    # Final cleanup
    final_equity = equity_curve[-1]
    total_return_pct = ((final_equity / initial_capital) - 1) * 100
    
    # Benchmark: Al ve Tut Comparison (if current strategy isn't already Buy & Hold)
    # We'll just provide the curve and metrics for the selected strategy.
    # The UI can handle the comparison chart if needed.
    
    result_df = pd.DataFrame(index=data.index)
    result_df['Strategy_Equity'] = equity_curve
    result_df['Price'] = data['Close']
    # Normalized price for Buy & Hold comparison (starting at initial capital)
    first_price = data['Close'].iloc[0]
    result_df['BuyHold_Equity'] = (data['Close'] / first_price) * initial_capital * (1 - commission_rate)

    metrics = {
        "initial_capital": initial_capital,
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return_pct, 2),
        "trade_count": trade_count,
        "strategy_name": strategy_name
    }
    
    return {
        "metrics": metrics,
        "equity_curve": result_df
    }
