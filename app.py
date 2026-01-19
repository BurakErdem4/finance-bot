import streamlit as st
import pandas as pd
import yfinance as yf
import borsapy as bp
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Yerel Modüller
from screener_module import find_cheap_industrial_stocks
from fund_module import get_fund_analysis
from info_module import get_market_summary
import config
from database import init_db
from rebalance_module import calculate_rebalance, get_rebalance_summary
from analysis_module import calculate_sma, calculate_rsi, get_technical_signals

# Veritabanını başlat
init_db()

# Reusable component for Technical Analysis
def display_technical_analysis(df, symbol):
    if df.empty:
        st.warning(f"{symbol} için veri bulunamadı.")
        return

    # Signal Box
    signal = get_technical_signals(df)
    st.markdown(f"""
    <div style="padding:10px; border-radius:10px; background-color:{signal['color']}; color:white; text-align:center; margin-bottom:20px;">
        <h3 style="margin:0;">{symbol} Sinyal Durumu: {signal['label']}</h3>
        <p style="margin:0;">{signal['desc']} (RSI: {signal['rsi']})</p>
    </div>
    """, unsafe_allow_html=True)

    # SMA Hesaplamaları
    sma50 = calculate_sma(df, 50)
    sma200 = calculate_sma(df, 200)
    rsi = calculate_rsi(df)
    
    # Subplots
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                       vertical_spacing=0.1, subplot_titles=(f'Fiyat ve SMA', 'RSI (14)'),
                       row_heights=[0.7, 0.3])
    
    # Fiyat Grafiği
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Fiyat', line=dict(color='white')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sma50, name='SMA 50', line=dict(color='cyan', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sma200, name='SMA 200', line=dict(color='red', width=1.5)), row=1, col=1)
    
    # RSI Grafiği
    fig.add_trace(go.Scatter(x=df.index, y=rsi, name='RSI', line=dict(color='purple')), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    
    fig.update_layout(height=500, template="plotly_dark", showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

# Sayfa Ayarları
st.set_page_config(
    page_title="Finansal Takip Botu",
    page_icon="📈",
    layout="wide"
)

# Caching for yfinance to prevent frequent API calls
@st.cache_data(ttl=900)
def get_yfinance_data(symbol, period="1y"):
    try:
        ticker = yf.Ticker(symbol)
        # We use 1y to have enough data for SMA 200
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
    
    # Veri Çekme (Analiz için 1 yıllık veri alıyoruz)
    with st.spinner(f"{symbol_to_track} verileri analiz ediliyor..."):
        symbol_hist_full = get_yfinance_data(symbol_to_track, period="1y")
    
    # Detaylı Teknik Analiz (Market Summary version)
    if not symbol_hist_full.empty:
        display_technical_analysis(symbol_hist_full, symbol_to_track)
    else:
        st.warning(f"{symbol_to_track} için analiz verisi bulunamadı.")
        
    else:
        st.warning(f"{symbol_to_track} için analiz verisi bulunamadı.")

    st.markdown("---")
    
    # BIST 30 Grafiği (Alt Kısım)
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
            
            st.markdown("---")
            st.subheader("Hızlı Teknik Analiz")
            selected_stock = st.selectbox("Analiz edilecek hisseyi seçin:", df['symbol'].tolist())
            
            if st.button("Teknik Analizi Göster"):
                # Borsa İstanbul hisseleri için .IS son eki gerekebilir yfinance'da
                yf_symbol = selected_stock + ".IS"
                with st.spinner(f"{yf_symbol} analiz ediliyor..."):
                    stock_hist = get_yfinance_data(yf_symbol, period="1y")
                    display_technical_analysis(stock_hist, yf_symbol)
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
