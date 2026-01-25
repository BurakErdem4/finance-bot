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
    "TR": {"start": "10:15", "end": "10:30"},
    "US": {"summer": "16:45", "winter": "17:45"}
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
# Otomatik Tamamlama (Autocomplete) Listeleri
ALL_SYMBOLS = [
    # BIST (Popüler)
    "THYAO.IS", "ASELS.IS", "GARAN.IS", "EREGL.IS", "SASA.IS", "KCHOL.IS", "AKBNK.IS", "TUPRS.IS", "SISE.IS", "BIMAS.IS",
    "FROTO.IS", "ISCTR.IS", "YKBNK.IS", "SAHOL.IS", "HEKTS.IS", "PETKM.IS", "TCELL.IS", "ARCLK.IS", "ENKAI.IS", "TOASO.IS",
    "ASTOR.IS", "GUBRF.IS", "KONTR.IS", "MAVI.IS", "ALARK.IS", "PGSUS.IS", "TTKOM.IS", "SOKM.IS", "ODAS.IS", "TTRAK.IS",
    "DOAS.IS", "VESTL.IS", "KOZAL.IS", "KOZAA.IS", "TKFEN.IS", "ULKER.IS", "EKGYO.IS", "DOHOL.IS", "BRSAN.IS", "OYAKC.IS",
    "XU100.IS", "XU030.IS", "XBANK.IS",
    
    # ABD Borsaları
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "AMD", "INTC", 
    "QCOM", "CSCO", "PYPL", "ADBE", "BA", "DIS", "JPM", "V", "JNJ", "WMT",
    "SPY", "QQQ", "DIA", "VTI", "VOO", "SCHD",
    
    # Kripto
    "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD", "BNB-USD", "DOT-USD", "MATIC-USD",
    
    # Emtia & Döviz
    "GC=F", "SI=F", "CL=F", "NG=F", # Altın, Gümüş, Petrol, Gaz
    "TRY=X", "EURTRY=X", "EURUSD=X", "DX-Y.NYB" # Dolar/TL, Euro/TL, Parite, DXY
]

TEFAS_FUNDS = [
    "TCD", "AFT", "YAS", "MAC", "IPB", "TI2", "AFA", "NNF", "HKH", "IPV", 
    "KUB", "AES", "BIO", "GBC", "KTM", "TTE", "IDH", "OJT", "BUY", "GMR"
]

BIST_100_TICKERS = [
    # Top 30-40 BIST Companies for Screener
    "THYAO.IS", "ASELS.IS", "GARAN.IS", "EREGL.IS", "SASA.IS", "KCHOL.IS", "AKBNK.IS", "TUPRS.IS", "SISE.IS", "BIMAS.IS",
    "FROTO.IS", "ISCTR.IS", "YKBNK.IS", "SAHOL.IS", "HEKTS.IS", "PETKM.IS", "TCELL.IS", "ARCLK.IS", "ENKAI.IS", "TOASO.IS",
    "ASTOR.IS", "GUBRF.IS", "KONTR.IS", "MAVI.IS", "ALARK.IS", "PGSUS.IS", "TTKOM.IS", "SOKM.IS", "ODAS.IS", "TTRAK.IS",
    "DOAS.IS", "VESTL.IS", "KOZAL.IS", "KOZAA.IS", "TKFEN.IS", "ULKER.IS", "EKGYO.IS", "DOHOL.IS", "OYAKC.IS", "AEFES.IS"
]

US_ETFS = [
    # US ETF Opportunities
    "SPY", "QQQ", "VTI", "VOO", # General Market
    "GLD", "SLV", # Commodities
    "ARKK", # Innovation
    "XLF", # Finance
    "XLE", # Energy
    "XLK", # Tech
    "SMH", # Semi
    "SCHD" # Dividend
]
