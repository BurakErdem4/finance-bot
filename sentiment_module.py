import yfinance as yf
from textblob import TextBlob

def get_sentiment_score(symbol):
    """
    Fetches latest news for a symbol and returns sentiment metrics.
    Returns: { 'score': float, 'label': str, 'count': int }
    """
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news
        
        if not news:
            return {"score": 0, "label": "NÖTR", "count": 0}
            
        polarities = []
        for item in news:
            title = item.get('title', '')
            if title:
                analysis = TextBlob(title)
                polarities.append(analysis.sentiment.polarity)
                
        if not polarities:
            return {"score": 0, "label": "NÖTR", "count": 0}
            
        avg_score = sum(polarities) / len(polarities)
        
        if avg_score > 0.1:
            label = "POZİTİF"
        elif avg_score < -0.1:
            label = "NEGATİF"
        else:
            label = "NÖTR"
            
        return {
            "score": round(avg_score, 2),
            "label": label,
            "count": len(polarities)
        }
    except Exception as e:
        print(f"Sentiment error for {symbol}: {e}")
        return {"score": 0, "label": "HATA", "count": 0}
