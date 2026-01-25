import yfinance as yf
from textblob import TextBlob

from datetime import datetime
import time

def format_time_label(timestamp):
    """Converts unix timestamp to human readable label."""
    now = time.time()
    diff_sec = now - timestamp
    
    if diff_sec < 3600: # < 1 hour
        return f"{int(diff_sec/60)} dakika önce"
    elif diff_sec < 86400: # < 24 hours
        return f"{int(diff_sec/3600)} saat önce"
    elif diff_sec < 172800: # < 48 hours
        return "Dün"
    else:
        return datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y")

def get_sentiment_score(symbol):
    """
    Fetches latest news for a symbol and returns detailed sentiment.
    """
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news
        
        if not news or len(news) == 0:
            return {
                "score": 0, 
                "label": "NÖTR", 
                "title": "Piyasa ile ilgili güncel akış bulunamadı.", 
                "is_fresh": False, 
                "time_label": "---"
            }
            
        # Get the latest news item (usually first in list)
        latest_item = news[0]
        title = latest_item.get('title')
        if not title:
            title = 'Piyasa ile ilgili güncel akış bulunamadı.'
        pub_time = latest_item.get('providerPublishTime', time.time())
        
        # Calculate sentiment for the latest title
        analysis = TextBlob(title)
        score = round(analysis.sentiment.polarity, 2)
        
        # Freshness Check (24 hours = 86400 seconds)
        is_fresh = (time.time() - pub_time) < 86400
        time_label = format_time_label(pub_time)
        
        if score > 0.1: label = "POZİTİF"
        elif score < -0.1: label = "NEGATİF"
        else: label = "NÖTR"
            
        return {
            "score": score,
            "label": label,
            "title": title,
            "is_fresh": is_fresh,
            "time_label": time_label,
            "timestamp": pub_time
        }
    except Exception as e:
        print(f"Sentiment error for {symbol}: {e}")
        return {"score": 0, "label": "HATA", "title": "Hata oluştu", "is_fresh": False, "time_label": "---", "timestamp": 0}
