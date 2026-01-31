import streamlit as st
import pandas as pd
import borsapy as bp

# --- TEFAS VERİLERİNİ ÇEKME MODÜLÜ ---

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_tefas_data():
    """
    Yatırım (YAT) ve Emeklilik (EMK) fonlarını çeker, sütunları eşitler ve birleştirir.
    UI elemanı içermez (Cache hatasını önlemek için).
    """
    try:
        # 1. Yatırım Fonlarını Çek
        try:
            df_yat = bp.screen_funds(fund_type="YAT", limit=10000)
            if not df_yat.empty:
                df_yat['Tür'] = 'Yatırım'
        except:
            df_yat = pd.DataFrame()

        # 2. Emeklilik Fonlarını Çek
        try:
            df_emk = bp.screen_funds(fund_type="EMK", limit=10000)
            if not df_emk.empty:
                df_emk['Tür'] = 'Emeklilik'
        except:
            df_emk = pd.DataFrame()

        # 3. Listeler Boş mu Kontrol Et
        if df_yat.empty and df_emk.empty:
            return pd.DataFrame()

        # 4. Sütun İsimlerini Önceden Standartlaştır (Çakışmayı önlemek için)
        # Borsapy bazen İngilizce bazen Türkçe dönebilir, ikisini de map'liyoruz.
        col_map = {
            'fund_code': 'Fon Kodu', 'code': 'Fon Kodu',
            'name': 'Fon Adı', 'title': 'Fon Adı',
            'price': 'Fiyat',
            'return_1m': 'Aylık (%)',
            'return_3m': '3 Aylık (%)',
            'return_6m': '6 Aylık (%)',
            'return_1y': 'Yıllık (%)',
            'return_ytd': 'YTD (%)',
            'fund_type': 'Kategori'
        }
        
        if not df_yat.empty:
            df_yat = df_yat.rename(columns=col_map)
        if not df_emk.empty:
            df_emk = df_emk.rename(columns=col_map)

        # 5. Sadece Ortak Sütunları Seçerek Birleştir (Hata riskini sıfırlar)
        # Önce tüm sütunları birleştirip sonra rename yapmak yerine, rename yapıp birleştiriyoruz.
        df_all = pd.concat([df_yat, df_emk], ignore_index=True)
        
        return df_all

    except Exception as e:
        # Hata olursa boş dön ama UI'a basma (app.py bassın)
        print(f"Veri çekme hatası: {e}") 
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_fund_history(fund_codes):
    """
    Seçilen fonların geçmiş verilerini getirir.
    """
    history_df = pd.DataFrame()
    if not fund_codes:
        return history_df

    for code in fund_codes:
        try:
            fund = bp.Fund(code)
            # Emeklilik fonu olup olmadığını anlamak için try-except bloğu korur
            df = fund.history(period="1y")
            
            # Sütun isimlendirme (price veya close gelebilir)
            col_name = 'price' if 'price' in df.columns else 'close'
            
            if not df.empty and col_name in df.columns:
                history_df[code] = df[col_name]
                 
        except Exception:
            continue
            
    return history_df
