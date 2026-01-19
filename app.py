import streamlit as st
import pandas as pd
import yfinance as yf
import borsapy as bp
import plotly.express as px
import plotly.graph_objects as go

# Yerel Modüller
from screener_module import find_cheap_industrial_stocks
from fund_module import get_fund_analysis
from info_module import get_market_summary

# Sayfa Ayarları
st.set_page_config(
    page_title="Finansal Takip Botu",
    page_icon="📈",
    layout="wide"
)

# Kenar Çubuğu (Navigasyon)
st.sidebar.title("Finans Botu 🤖")
page = st.sidebar.radio("Menü", ["Piyasa Özeti", "Hisse Tarama", "Fon Analizi", "Bilgi Notu"])

st.sidebar.markdown("---")
st.sidebar.info("Developed with borsapy & streamlit")

# --- 1. PİYASA ÖZETİ ---
if page == "Piyasa Özeti":
    st.title("📊 Piyasa Özeti")
    
    # Üst Bilgi Kartları (Metrics)
    col1, col2, col3, col4 = st.columns(4)
    
    # Dolar ve Euro (Info modülünden)
    market_data = get_market_summary()
    
    with col1:
        st.metric("USD/TRY", f"{market_data['usd'] or '---'} ₺")
    with col2:
        st.metric("EUR/TRY", f"{market_data['eur'] or '---'} ₺")
        
    # BIST30
    with col3:
        try:
            xu030 = bp.Index("XU030")
            val = xu030.info.get('last') if hasattr(xu030, 'info') else "---"
            st.metric("BIST 30", val)
        except:
            st.metric("BIST 30", "Hata")

    # Apple
    with col4:
        try:
            aapl = yf.Ticker("AAPL")
            # Fast fetch for current price
            hist = aapl.history(period="1d")
            if not hist.empty:
                st.metric("Apple (AAPL)", f"{hist['Close'].iloc[-1]:.2f} $")
        except:
             st.metric("Apple", "Hata")

    st.markdown("---")
    
    # Grafikler Yan Yana
    g_col1, g_col2 = st.columns(2)
    
    with g_col1:
        st.subheader("🍏 Apple (Son 1 Ay)")
        try:
            aapl_hist = yf.Ticker("AAPL").history(period="1mo")
            if not aapl_hist.empty:
                fig = px.line(aapl_hist, y="Close", title="AAPL Günlük Kapanış")
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Veri alınamadı: {e}")

    with g_col2:
        st.subheader("🇹🇷 BIST 30 (Son 1 Ay)")
        try:
            xu030_hist = bp.Index("XU030").history(period="1ay")
            if xu030_hist is not None and not xu030_hist.empty:
                # borsapy history index date olabilir
                fig2 = px.line(xu030_hist, y="Close", title="BIST30 Kapanış")
                st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
             st.error(f"Veri alınamadı: {e}")

# --- 2. HİSSE TARAMA ---
elif page == "Hisse Tarama":
    st.title("🔍 Hisse Tarama (Screener)")
    st.markdown("""
    **Kriterler:**
    - Endeks: **BIST SINAİ** (XUSIN)
    - F/K Oranı (P/E) < **10**
    - Son 1 Aylık Getiri > **%0**
    """)
    
    if st.button("Taramayı Başlat"):
        with st.spinner("Hisseler taranıyor..."):
            df = find_cheap_industrial_stocks()
            
        if df is not None and not df.empty:
            st.success(f"{len(df)} adet hisse bulundu.")
            st.dataframe(df, use_container_width=True)
            
            # Basit bir scatter plot
            # criteria sütun isimleri dinamik olabilir, o yüzden sadece listeliyoruz şimdilik
        else:
            st.warning("Kriterlere uygun hisse bulunamadı veya bir hata oluştu.")

# --- 3. FON ANALİZİ ---
elif page == "Fon Analizi":
    st.title("📈 Fon Analizi")
    
    fund_code = st.text_input("Fon Kodu Giriniz (Örn: TCD, AFT, IPV)", "TCD")
    
    if st.button("Analiz Et"):
        with st.spinner(f"{fund_code} verileri çekiliyor..."):
            data = get_fund_analysis(fund_code)
            
        if data["error"]:
            st.error(f"Hata oluştu: {data['error']}")
        else:
            # Üst Bilgiler
            f_col1, f_col2, f_col3 = st.columns(3)
            f_col1.metric("Fon Adı", data['info']['title'])
            f_col2.metric("Fiyat", f"{data['info']['price']} ₺")
            f_col3.metric("Kategori", data['info']['category'])
            
            # Getiriler Tablosu
            st.subheader("Dönemsel Getiriler (%)")
            ret_df = pd.DataFrame([data['returns']])
            st.table(ret_df)
            
            # Varlık Dağılımı (Pasta Grafik)
            st.subheader("Varlık Dağılımı")
            alloc = data['allocation']
            if alloc is not None and not alloc.empty:
                # Sütun isimlerini normalize etme çabası
                name_col = 'name' if 'name' in alloc.columns else 'asset_name'
                val_col = 'value' if 'value' in alloc.columns else 'weight'
                
                if name_col in alloc.columns and val_col in alloc.columns:
                    fig = px.pie(alloc, values=val_col, names=name_col, title=f"{fund_code} Portföy Dağılımı")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.dataframe(alloc)
            else:
                st.info("Varlık dağılım verisi bulunamadı.")

# --- 4. BİLGİ NOTU ---
elif page == "Bilgi Notu":
    st.title("📝 Günlük Bilgi Notu & Takvim")
    
    data = get_market_summary()
    
    # Tahviller
    st.subheader("Tahvil Piyasası")
    b_col1, b_col2 = st.columns(2)
    b_col1.metric("TR 2 Yıllık Tahvil", f"%{data['bond_2y'] or '---'}")
    b_col2.metric("TR 10 Yıllık Tahvil", f"%{data['bond_10y'] or '---'}")
    
    st.info("Mevduat Faizi (Ortalama/Tahmini): %45-50 seviyelerinde")
    
    # Takvim
    st.subheader("📅 Ekonomik Takvim (Bu Hafta - TR Önemli)")
    cal = data['calendar']
    if cal is not None and not cal.empty:
        # Görsellik için bazı kolonları seçelim
        disp_cols = ['Date', 'Time', 'Event', 'Actual', 'Forecast', 'Previous']
        final_cols = [c for c in disp_cols if c in cal.columns]
        st.dataframe(cal[final_cols], use_container_width=True)
    else:
        st.write("Önemli bir veri akışı bulunmuyor.")
