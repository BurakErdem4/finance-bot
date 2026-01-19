from analysis_module import calculate_sma, calculate_rsi

def get_smart_dca_multiplier(df_row):
    """
    Returns a DCA multiplier based on technical conditions.
    Logic: 
    - Price < SMA200 -> 1.5x (Buy the dip)
    - RSI > 80 -> 0.5x (Overbought, avoid heavy buying)
    - Default -> 1.0x
    """
    price = df_row['Close']
    sma200 = df_row.get('SMA200')
    rsi = df_row.get('RSI')
    
    if sma200 and price < sma200:
        return 1.5
    if rsi and rsi > 80:
        return 0.5
    return 1.0
