import yfinance as yf
import borsapy as bp
import pandas as pd
from screener_module import find_cheap_industrial_stocks
from fund_module import analyze_specific_fund
from info_module import get_daily_info_note

def main():
    print("--- Finansal Takip Botu Başlatılıyor ---\n")

    # 1. Apple (AAPL) Verisi - yfinance ile
    print(">>> Apple (AAPL) verisi çekiliyor (yfinance)...")
    try:
        aapl = yf.Ticker("AAPL")
        # Son 1 aylık veriyi al
        aapl_hist = aapl.history(period="1mo")
        
        print(f"AAPL Son Fiyat: {aapl_hist['Close'].iloc[-1]:.2f} USD")
        print("\nAAPL Son 5 Günlük Veri:")
        print(aapl_hist.tail())
    except Exception as e:
        print(f"Hata (AAPL): {e}")

    print("-" * 50 + "\n")

    # 2. BIST30 Verisi - borsapy ile
    print(">>> BIST30 Endeks verisi çekiliyor (borsapy)...")
    try:
        # BIST30 Endeksi için borsapy kullanımı
        xu030 = bp.Index("XU030")
        
        # Endeks bilgileri (cache'den hızlı erişim)
        if hasattr(xu030, 'info') and xu030.info:
             print(f"BIST30 Güncel Değer: {xu030.info.get('last')}")
        
        # Son 1 aylık geçmiş veri
        xu030_hist = xu030.history(period="1ay")
        
        print("\nBIST30 Son 5 Günlük Veri:")
        print(xu030_hist.tail())
        
        # İsterseniz bileşenleri de görebilirsiniz
        # print(f"\nBIST30 Bileşen Sayısı: {len(xu030.components)}")
        
    except Exception as e:
        print(f"Hata (BIST30): {e}")

    print("-" * 50 + "\n")

    # 3. Hisse Tarama
    find_cheap_industrial_stocks()

    print("-" * 50 + "\n")

    # 4. Fon Analizi
    analyze_specific_fund("TCD")  # Örnek: Tacirler Değişken Fon

    print("-" * 50 + "\n")

    # 5. Günlük Bilgi Notu
    get_daily_info_note()

if __name__ == "__main__":
    main()
