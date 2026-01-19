# Proje Yapılandırması

# Takip edilecek semboller
SYMBOLS = {
    "stocks": ["AAPL", "QQQM", "MSFT", "GOOGL"],
    "indices": ["XU030", "XU100", "XUSIN"],
    "funds": ["TCD", "AFT", "IPV"]
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
