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
import config
from database import init_db
from rebalance_module import calculate_rebalance, get_rebalance_summary

# Veritabanını başlat
init_db()

# Sayfa Ayarları
st.set_page_config(
    page_title="Finansal Takip Botu",
    page_icon="📈",
    layout="wide"
)

# Caching for yfinance to prevent frequent API calls
@st.cache_data(ttl=900)
def get_yfinance_data(symbol, period="1mo"):
    try:
        ticker = yf.Ticker(symbol)
        return ticker.history(period=period)
    except:
        return pd.DataFrame()

# Helper for price formatting
def format_price(val, currency="₺"):
    if isinstance(val, dict):
        val = val.get('last') or val.get('price', 0)
    try:
        return f"{float(val):.2f} {currency}"
    except (ValueError, TypeError):
        return "---"

# Kenar Çubuğu (Navigasyon)
st.sidebar.title("Finans Botu 🤖")
page = st.sidebar.radio("Menü", ["Piyasa Özeti", "Hisse Tarama", "Fon Analizi", "Portföy Dengeleyici", "Bilgi Notu"])

st.sidebar.markdown("---")

# --- 1. PİYASA ÖZETİ ---
if page == "Piyasa Özeti":
    st.title("📊 Piyasa Özeti")
    
    # Global Sembol Seçimi
    symbol_to_track = st.text_input("Takip Edilecek Sembol (Yfinance)", "AAPL").upper()
    
    # Üst Bilgi Kartları (Metrics)
    col1, col2, col3, col4 = st.columns(4)
    
    # Dolar ve Euro (Info modülünden)
    market_data = get_market_summary()
    
    with col1:
        st.metric("USD/TRY", format_price(market_data['usd']))
    with col2:
        st.metric("EUR/TRY", format_price(market_data['eur']))
        
    # BIST30
    with col3:
        try:
            xu030 = bp.Index("XU030")
            val = xu030.info.get('last') if hasattr(xu030, 'info') else "---"
            st.metric("BIST 30", format_price(val))
        except:
            st.metric("BIST 30", "Hata")

    # Dinamik Sembol
    with col4:
        try:
            hist_current = get_yfinance_data(symbol_to_track, period="1d")
            if not hist_current.empty:
                st.metric(f"Sembol ({symbol_to_track})", format_price(hist_current['Close'].iloc[-1], "$"))
            else:
                st.metric(f"Sembol ({symbol_to_track})", "Yüklenemedi")
        except:
             st.metric(f"Sembol ({symbol_to_track})", "Hata")

    st.markdown("---")
    
    # Grafikler Yan Yana
    g_col1, g_col2 = st.columns(2)
    
    with g_col1:
        st.subheader(f"📈 {symbol_to_track} (Son 1 Ay)")
        try:
            symbol_hist = get_yfinance_data(symbol_to_track, period="1mo")
            if not symbol_hist.empty:
                fig = px.line(symbol_hist, y="Close", title=f"{symbol_to_track} Günlük Kapanış")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"{symbol_to_track} için grafik verisi bulunamadı.")
        except Exception as e:
            st.error(f"Veri alınamadı: {e}")

    with g_col2:
        st.subheader("🇹🇷 BIST 30 (Son 1 Ay)")
        try:
            xu030_hist = bp.Index("XU030").history(period="1ay")
            if xu030_hist is not None and not xu030_hist.empty:
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
        else:
            st.warning("Kriterlere uygun hisse bulunamadı veya bir hata oluştu.")

# --- 3. FON ANALİZİ ---
elif page == "Fon Analizi":
    st.title("📈 Fon Analizi")
    
    default_fund = config.SYMBOLS["funds"][0] if config.SYMBOLS["funds"] else "TCD"
    fund_code = st.text_input("Fon Kodu Giriniz (Örn: TCD, AFT, IPV)", default_fund)
    
    if st.button("Analiz Et"):
        with st.spinner(f"{fund_code} verileri çekiliyor..."):
            data = get_fund_analysis(fund_code)
            
        if data["error"]:
            st.error(f"Hata oluştu: {data['error']}")
        else:
            f_col1, f_col2, f_col3 = st.columns(3)
            f_col1.metric("Fon Adı", data['info']['title'])
            f_col2.metric("Fiyat", format_price(data['info']['price']))
            f_col3.metric("Kategori", data['info']['category'])
            
            st.subheader("Dönemsel Getiriler (%)")
            ret_df = pd.DataFrame([data['returns']])
            st.table(ret_df)
            
            st.subheader("Varlık Dağılımı")
            alloc = data['allocation']
            if alloc is not None and not alloc.empty:
                name_col = 'name' if 'name' in alloc.columns else 'asset_name'
                val_col = 'value' if 'value' in alloc.columns else 'weight'
                
                if name_col in alloc.columns and val_col in alloc.columns:
                    fig = px.pie(alloc, values=val_col, names=name_col, title=f"{fund_code} Portföy Dağılımı")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.dataframe(alloc)
            else:
                st.info("Varlık dağılım verisi bulunamadı.")

# --- 4. PORTFÖY DENGELEYİCİ ---
elif page == "Portföy Dengeleyici":
    st.title("⚖️ Portföy Dengeleyici (Smart Rebalance)")
    st.markdown("Yeni yatırımlarınızı hedef portföy yüzdelerinize göre otomatik olarak dağıtın.")
    
    # 1. Mevcut Durumu Göster
    st.subheader("Mevcut Portföy Dağılımı")
    current_df = pd.DataFrame(list(config.CURRENT_PORTFOLIO.items()), columns=["Kategori", "Mevcut Değer (TL)"])
    current_df["Hedef (%)"] = current_df["Kategori"].map(config.PORTFOLIO_TARGETS)
    
    total_val = current_df["Mevcut Değer (TL)"].sum()
    current_df["Mevcut (%)"] = (current_df["Mevcut Değer (TL)"] / total_val * 100).round(2)
    
    st.table(current_df)
    st.write(f"**Toplam Portföy Değeri:** {total_val:,.2f} TL")
    
    st.markdown("---")
    
    # 2. Yeni Yatırım Girişi
    new_investment = st.number_input("Yatırılacak Tutar (TL)", min_value=0, value=10000, step=1000)
    
    if st.button("Hesapla"):
        suggestions = calculate_rebalance(
            new_investment, 
            config.CURRENT_PORTFOLIO, 
            config.PORTFOLIO_TARGETS
        )
        
        st.success("✅ Dağıtım Önerisi Hazır")
        
        # Grafik ile gösterim
        s_df = pd.DataFrame(list(suggestions.items()), columns=["Kategori", "Alınacak Tutar (TL)"])
        fig = px.bar(s_df, x="Kategori", y="Alınacak Tutar (TL)", title="Yeni Yatırım Dağılımı")
        st.plotly_chart(fig, use_container_width=True)
        
        # Öneri Metni
        st.info(get_rebalance_summary(suggestions))
        
        # Detaylı Tablo
        st.subheader("İşlem Detayları")
        st.table(s_df.style.format({"Alınacak Tutar (TL)": "{:,.2f}"}))

# --- 5. BİLGİ NOTU ---
elif page == "Bilgi Notu":
    st.title("📝 Günlük Bilgi Notu & Takvim")
    
    # Ekonomik Takvim Filtresi
    cal_filter = st.selectbox("Takvim Filtresi", ["Türkiye (TR)", "ABD (US)", "Global (All)"])
    filter_map = {"Türkiye (TR)": "TR", "ABD (US)": "US", "Global (All)": "ALL"}
    
    data = get_market_summary(calendar_country=filter_map[cal_filter])
    
    st.subheader("Tahvil Piyasası")
    b_col1, b_col2 = st.columns(2)
    b_col1.metric("TR 2 Yıllık Tahvil", f"%{data['bond_2y'] or '---'}")
    b_col2.metric("TR 10 Yıllık Tahvil", f"%{data['bond_10y'] or '---'}")
    
    st.sidebar.markdown("### Hedef Portföy")
    for category, percentage in config.PORTFOLIO_TARGETS.items():
        st.sidebar.write(f"- {category}: %{percentage}")

    st.info("Mevduat Faizi (Ortalama/Tahmini): %45-50 seviyelerinde")
    
    st.subheader(f"📅 Ekonomik Takvim ({cal_filter})")
    cal = data['calendar']
    if cal is not None and not cal.empty:
        disp_cols = ['Date', 'Time', 'Event', 'Actual', 'Forecast', 'Previous']
        final_cols = [c for c in disp_cols if c in cal.columns]
        st.dataframe(cal[final_cols], use_container_width=True)
    else:
        st.write("Seçilen filtre için önemli bir veri akışı bulunmuyor.")
