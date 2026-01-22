# Proje Yapılandırması

# Takip edilecek semboller
SYMBOLS = {
    "stocks": ["AAPL", "QQQM", "MSFT", "GOOGL"],
    "indices": ["XU030", "XU100", "XUSIN"],
    "funds": ["TCD", "AFT", "IPV"]
}

# Bülten Varlıkları
NEWSLETTER_ASSETS = {
    "Borsa": [
        {"name": "BIST 100", "symbol": "XU100.IS"},
        {"name": "BIST 30", "symbol": "XU030.IS"},
        {"name": "NASDAQ 100", "symbol": "^IXIC"},
        {"name": "S&P 500", "symbol": "^GSPC"}
    ],
    "Döviz": [
        {"name": "USD/TRY", "symbol": "TRY=X"},
        {"name": "EUR/TRY", "symbol": "EURTRY=X"}
    ],
    "Emtia": [
        {"name": "Ons Altın", "symbol": "GC=F"},
        {"name": "Ons Gümüş", "symbol": "SI=F"},
        {"name": "Gram Altın", "symbol": "GRAM_GOLD", "calc": "gold_ons * usd / 31.1"},
        {"name": "Gram Gümüş", "symbol": "GRAM_SILVER", "calc": "silver_ons * usd / 31.1"}
    ],
    "Kripto": [
        {"name": "Bitcoin", "symbol": "BTC-USD"},
        {"name": "Ethereum", "symbol": "ETH-USD"},
        {"name": "XRP", "symbol": "XRP-USD"}
    ],
    "Faiz/Diğer": [
        {"name": "ABD 10Y Tahvil", "symbol": "^TNX"},
        {"name": "Para Piyasası Fonu", "symbol": "PPF", "manual": True, "value": 45.0} # Yıllık brüt getiri tahmini
    ]
}

# Bülten Zamanlaması
NEWSLETTER_SCHEDULE = {
    "TR": "10:15",
    "US": {"winter": "17:45", "summer": "16:45"} # Yaz/Kış saati farkı
}

# Portföy Hedef Yüzdeleri
PORTFOLIO_TARGETS = {
    "Teknoloji": 45,
    "Yerli Hisse": 30,
    "Eurobond": 15,
    "Sasa": "SASA.IS"
}

ANNUAL_INFLATION_RATE = 45 # %45
RISK_FREE_RATE = 0.40 # %40 (Mevduat/Tahvil tahmini)

# Sembol - Kategori Eşleşmesi (Dengeleyici için)
SYMBOL_CATEGORIES = {
    "AAPL": "Teknoloji",
    "MSFT": "Teknoloji",
    "GOOGL": "Teknoloji",
    "QQQM": "Teknoloji",
    "THYAO": "Yerli Hisse",
    "SISE": "Yerli Hisse",
    "EREGL": "Yerli Hisse",
    "IPV": "Eurobond",
    "TCD": "Yerli Hisse",
    "XU030": "Yerli Hisse",
    "GC=F": "Emtia",
    "TRY=X": "Nakit" # Örnek
}

# Mevcut Portföy Durumu (Örnek Veri)
CURRENT_PORTFOLIO = {
    "Teknoloji": 15000,
    "Yerli Hisse": 12000,
    "Eurobond": 3000,
    "Emtia": 2000
}
