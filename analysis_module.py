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

def get_technical_signals(df):
    """
    Returns technical signals based on indicators.
    Returns: { 'label': str, 'color': str, 'desc': str, 'rsi': float }
    """
    rsi_series = calculate_rsi(df)
    if rsi_series is None or rsi_series.empty:
        return {"label": "VERİ YOK", "color": "gray", "desc": "Yeterli veri bulunamadı.", "rsi": None}
    
    current_rsi = rsi_series.iloc[-1]
    
    if current_rsi < 30:
        return {
            "label": "GÜÇLÜ AL",
            "color": "green",
            "desc": "RSI Aşırı Satımda (Oversold)",
            "rsi": round(current_rsi, 2)
        }
    elif current_rsi > 70:
        return {
            "label": "SAT",
            "color": "red",
            "desc": "RSI Aşırı Alımda (Overbought)",
            "rsi": round(current_rsi, 2)
        }
    else:
        return {
            "label": "NÖTR",
            "color": "white",
            "desc": "RSI Normal Seviyelerde",
            "rsi": round(current_rsi, 2)
        }
