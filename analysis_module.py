import pandas as pd

def calculate_sma(df, window):
    """Calculates Simple Moving Average."""
    if df is None or df.empty or 'Close' not in df.columns:
        return None
    return df['Close'].rolling(window=window).mean()

def calculate_rsi(df, window=14):
    """Calculates Relative Strength Index."""
    if df is None or df.empty or 'Close' not in df.columns:
        return None
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_technical_score(df):
    """
    Calculates a technical score from 0-100 based on RSI, Trend, and Volume.
    """
    if df is None or df.empty or len(df) < 50:
        return 50

    # 1. RSI Score (30%)
    rsi_series = calculate_rsi(df)
    current_rsi = rsi_series.iloc[-1]
    if current_rsi < 30: rsi_score = 90
    elif current_rsi > 70: rsi_score = 10
    else: rsi_score = 100 - abs(current_rsi - 50) * 2 # Peak score at RSI 50 for neutral, or adjust for trend?
    # Let's adjust: Bullish if RSI is rising from 50
    rsi_score = max(0, min(100, (100 - current_rsi) if current_rsi > 50 else (current_rsi + 50)))

    # 2. Trend Score (40%) - SMA 50 vs 200 and Price
    sma50 = calculate_sma(df, 50).iloc[-1]
    sma200 = calculate_sma(df, 200).iloc[-1] if len(df) >= 200 else sma50
    price = df['Close'].iloc[-1]
    
    trend_score = 0
    if price > sma50: trend_score += 30
    if sma50 > sma200: trend_score += 40
    if price > sma200: trend_score += 30
    
    # 3. Volume Score (30%)
    avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
    curr_vol = df['Volume'].iloc[-1]
    vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1
    vol_score = min(100, vol_ratio * 50) # 2x volume = 100 points

    final_score = (rsi_score * 0.3) + (trend_score * 0.4) + (vol_score * 0.3)
    return round(final_score, 2)

def calculate_kelly_position(score):
    """
    Calculates recommended position size using simplified Kelly Criterion.
    f = (p * (b + 1) - 1) / b
    Where p = win probability (derived from score), b = odds (estimated at 1.5)
    """
    p = score / 100.0
    b = 1.5 # Reward/Risk ratio estimate
    kelly_f = (p * (b + 1) - 1) / b
    
    # Prudence: Half-Kelly and cap at 25%
    recommended = max(0, (kelly_f / 2))
    return round(min(recommended, 0.25) * 100, 2)

def get_technical_signals(df):
    """
    Returns technical signals based on score and indicators.
    Returns: { 'label': str, 'color': str, 'desc': str, 'rsi': float, 'score': float, 'kelly': float }
    """
    score = calculate_technical_score(df)
    rsi_series = calculate_rsi(df)
    current_rsi = rsi_series.iloc[-1] if rsi_series is not None and not rsi_series.empty else 0
    kelly = calculate_kelly_position(score)
    
    if score >= 80:
        label, color, desc = "GÜÇLÜ AL", "#00C853", "Tüm faktörler yükselişi destekliyor."
    elif score >= 60:
        label, color, desc = "AL", "#64DD17", "Pozitif trend ve teknik görünüm."
    elif score >= 40:
        label, color, desc = "NÖTR", "#FFD600", "Belirgin bir trend yönü yok."
    elif score >= 20:
        label, color, desc = "SAT", "#FF6D00", "Negatif teknik baskı."
    else:
        label, color, desc = "GÜÇLÜ SAT", "#D50000", "Ağır teknik bozulma."
        
    return {
        "label": label,
        "color": color,
        "desc": desc,
        "rsi": round(current_rsi, 2),
        "score": score,
        "kelly": kelly
    }
