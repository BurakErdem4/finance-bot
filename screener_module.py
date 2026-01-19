import streamlit as st
import borsapy as bp
import pandas as pd

@st.cache_data(ttl=900)
def find_cheap_industrial_stocks():
    """
    Finds industrial stocks with low P/E ratio and positive monthly return.
    Criteria:
    - Index: BIST Sınai (XUSIN)
    - P/E (pe) < 10
    - Monthly Return (return_1m) > 0
    """
    print(">>> Hisse Tarama Başlatılıyor (Kriter: Sınai [XUSIN], F/K < 10, Aylık Getiri > %0)...")
    
    try:
        # 1. Endeks Bileşenlerini Al (Client-side filtreleme için)
        # API filtrelemesi bazen sorun çıkarabildiği için (SSL/Character issues),
        # önce geniş tarama yapıp sonra biz filtreliyoruz.
        try:
            ind_index = bp.Index("XUSIN")
            industrial_symbols = set(ind_index.component_symbols)
            # print(f"Sınai Endeksi (XUSIN) içinde {len(industrial_symbols)} hisse var.")
        except Exception as e:
            print(f"Endeks bileşenleri alınamadı: {e}")
            return None

        # 2. Genel Tarama Yap (Sektör/Endeks filtresi olmadan)
        screener = bp.Screener()
        screener.add_filter("pe", max=10)
        screener.add_filter("return_1m", min=0)
        
        # Diğer potansiyel kriterler eklenebilir
        # screener.add_filter("market_cap", min=1000) # Min 1 milyar TL gibi
        
        results = screener.run()
        
        if results is None or results.empty:
            print("Kriterlere uygun hisse bulunamadı.")
            return None

        # 3. Sonuçları Endekse Göre Filtrele
        # results dataframe'inde 'symbol' kolonu hisse kodlarını içerir.
        final_results = results[results['symbol'].isin(industrial_symbols)]
        
        if final_results.empty:
             print("Sınai endeksinde bu kriterlere uyan hisse bulunamadı.")
             return None
            
        # Sonuçları F/K'ya (criteria_23 = P/E usually, but let's assume 'pe' or mapped)
        # borsapy sonuçları bazen criteria_ID şeklinde döner. 
        # Ancak debug çıktısında gördük ki 'symbol' ve 'name' var.
        # F/K sütununu bulup ona göre sıralamak daha şık olurdu ama şimdilik varsayılan sıralama kalsın.
        
        print(f"\nBulunan Hisse Sayısı: {len(final_results)}")
        print(final_results.head(10)) 
        
        return final_results

    except Exception as e:
        print(f"Hata (Screener): {e}")
        return None
