import streamlit as st
import pandas as pd
import yfinance as yf
import borsapy as bp
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Yerel Modüller
from screener_module import fetch_bist_data, fetch_us_etf_data
from fund_module import get_fund_analysis
from info_module import get_market_summary
import config
from database import init_db
from rebalance_module import calculate_rebalance, get_rebalance_summary
from analysis_module import calculate_sma, calculate_rsi, get_technical_signals
from benchmark_module import get_benchmark_data, get_benchmark_summary
from backtest_module import run_backtest, run_periodic_backtest
from mail_module import send_newsletter, fetch_newsletter_data
from portfolio_manager import add_transaction, get_all_transactions, get_portfolio_balance, get_portfolio_by_category

from sentiment_module import get_sentiment_score
import subscription_module
import paper_trader
import time
from datetime import datetime

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
    <div style="padding:15px; border-radius:12px; background-color:#1E1E1E; border: 2px solid {signal['color']}; color:white; margin-bottom:20px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h2 style="margin:0; color:{signal['color']};">{signal['label']}</h2>
                <p style="margin:5px 0 0 0; color:#AAA;">{signal['desc']}</p>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 24px; font-weight: bold;">{signal['score']}/100</div>
                <div style="font-size: 14px; color:#AAA;">Teknik Puan</div>
            </div>
        </div>
        <hr style="border: 0; border-top: 1px solid #333; margin: 15px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="font-size: 16px;">🎯 Önerilen Giriş: <span style="font-weight:bold; color:cyan;">Portföyün %{signal['kelly']}</span></div>
            <div style="font-size: 14px; color:#AAA;">RSI: {signal['rsi']}</div>
        </div>
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
        return ticker.history(period=period)
    except:
        return pd.DataFrame()

# Helper for price formatting
def format_price(val, currency="₺"):
    if isinstance(val, dict):
        val = val.get('last') or val.get('price', 0)
    try:
        val_str = f"{float(val):,.2f}"
        if currency == "$":
            return f"${val_str}"
        return f"{val_str} {currency}"
    except (ValueError, TypeError):
        return "---"

# Helper for Autocomplete Search Box
def create_search_box(label, type="general", key=None):
    """
    Creates a selectbox with a 'manual entry' fallback.
    """
    if type == "fund":
        options = config.TEFAS_FUNDS
    else:
        options = config.ALL_SYMBOLS
        
    # Use selectbox with empty option
    selected = st.selectbox(label, [""] + options, key=f"sel_{key}" if key else None)
    
    # Toggle for Manual Entry
    manual_entry = st.checkbox("Listede yok mu? Manuel gir", key=f"chk_{key}" if key else None)
    
    if manual_entry:
        return st.text_input(f"{label} (Manuel)", key=f"txt_{key}" if key else None).upper()
    
    return selected

# Kenar Çubuğu (Navigasyon)
st.sidebar.title("Finans Botu 🤖")
page = st.sidebar.radio("Menü", ["Piyasa Özeti", "Hisse Tarama", "Fon Analizi", "Portföy Dengeleyici", "Strateji Testi", "Cüzdanım", "👻 Gölge Portföy", "Raporlar", "Bilgi Notu"])

st.sidebar.markdown("---")

import pytz # Added for Timezone

# 📧 Bülten Aboneliği (Yeni Sistem)
st.sidebar.subheader("📩 Bülten Aboneliği")
with st.sidebar.form("sub_form"):
    user_email = st.text_input("E-posta Adresi", placeholder="ornek@gmail.com")
    c1, c2 = st.columns(2)
    daily_sub = c1.checkbox("Günlük", value=True)
    weekly_sub = c2.checkbox("Haftalık", value=True)
    
    sub_btn = st.form_submit_button("Abone Ol / Güncelle")
    
    if sub_btn:
        if user_email and "@" in user_email:
            with st.spinner("İşlem yapılıyor..."):
                success, msg = subscription_module.add_subscriber(user_email, daily_sub, weekly_sub)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
        else:
            st.warning("Geçerli bir e-posta giriniz.")

st.sidebar.markdown("---")

# 📧 Manuel Raporlama (Test)
st.sidebar.subheader("🚀 Hızlı Gönderim (Test)")
test_email = st.sidebar.text_input("Hedef Email (Boşsa size gelir)", placeholder="me@test.com")
if st.sidebar.button("Raporu Bana Şimdi Gönder"):
    target = test_email if test_email else st.secrets.get("GMAIL_USER") 
    # Or just use the input if current user
    if not target:
        st.sidebar.error("Lütfen bir e-posta girin.")
    else:
        with st.spinner(f"{target} adresine gönderiliyor..."):
            s, m = send_newsletter(target, "Günlük")
            if s: 
                st.sidebar.success(m) 
            else: 
                st.sidebar.error(m)


# ⏰ Otomatik Zamanlayıcı
st.sidebar.markdown("---")
st.sidebar.subheader("⏰ Otomatik Zamanlayıcı")
enable_scheduler = st.sidebar.checkbox("Zamanlayıcıyı Aktif Et")

if enable_scheduler:
    status_placeholder = st.sidebar.empty()
    
    # Basit bir döngü
    # Not: Bu döngü UI'ı bloklayabilir, bot modu gibi düşünülmeli
    if "last_check" not in st.session_state:
        st.session_state.last_check = time.time()
        
    tz = pytz.timezone('Europe/Istanbul')
    now = datetime.now(tz)
    curr_time = now.strftime("%H:%M")
    
    try:
        # Timezone handled by pytz, so standard time is correct local time
        # US Schedule logic might need adjustment if it refers to specific US hours, but normally we just track local trigger times from config
        
        # Taking simplified approach: Config times are considered Local TR Times as per user request
        # If config has distinction, we use it.
        # Assuming config.NEWSLETTER_SCHEDULE has "US" and "TR" keys with local trigger times.
        
        us_time = config.NEWSLETTER_SCHEDULE["US"]["winter"] # Defaulting to single trigger for simplicity or keep existing logic if flexible
        
        # TR Time: start/end aralığı veya tek saat
        tr_conf = config.NEWSLETTER_SCHEDULE["TR"]
        tr_time = tr_conf if isinstance(tr_conf, str) else tr_conf.get("start", "10:15")
        
        status_placeholder.info(f"⏳ Takip: {curr_time} \nTR: {tr_time} | US: {us_time}")
        
        # State check for daily sending
        today_str = now.strftime("%Y-%m-%d")
        if "sent_log" not in st.session_state:
            st.session_state.sent_log = {} # {"TR": "2024-01-01", "US": "2024-01-01"}
            
        # TR Check
        if curr_time == tr_time and st.session_state.sent_log.get("TR") != today_str:
            with st.spinner("TR Raporu gönderiliyor..."):
                send_newsletter(None, "Günlük")
                st.session_state.sent_log["TR"] = today_str
                st.success("TR Raporu gönderildi!")
                
        # US Check
        if curr_time == us_time and st.session_state.sent_log.get("US") != today_str:
            with st.spinner("ABD Raporu gönderiliyor..."):
                send_newsletter(None, "Günlük")
                st.session_state.sent_log["US"] = today_str
                st.success("ABD Raporu gönderildi!")
                
    except Exception as e:
        status_placeholder.warning(f"Zamanlayıcı Hatası: {str(e)}")
        
    # Auto-rerun loop (Sleep 60s)
    time.sleep(30)
    st.rerun()

st.sidebar.markdown("---")

# --- 1. PİYASA ÖZETİ (DASHBOARD) ---
if page == "Piyasa Özeti":
    st.title("📊 Piyasa Kokpiti")
    
    # 1. Geniş Pazar Tablosu
    st.subheader("🌍 Küresel Piyasalar ve Varlıklar")
    
    with st.spinner("Piyasa verileri güncelleniyor (Bülten Modu)..."):
        # Reuse newsletter logic
        raw_data = fetch_newsletter_data()
        
    # Flatten Data for Table
    table_rows = []
    for cat, assets in raw_data.items():
        for asset in assets:
            # Handle manual/error cases gracefully
            price = asset.get('price', 0)
            d_chg = asset.get('daily', 0)
            w_chg = asset.get('weekly', 0)
            m_chg = asset.get('monthly', 0)
            
            # Format Price
            if "USD" in asset['name'] or "EUR" in asset['name']: p_str = f"{price:.4f}"
            elif "Altın" in asset['name'] or "Gümüş" in asset['name']: p_str = f"{price:.2f}"
            else: p_str = f"{price:,.2f}"
                
            table_rows.append({
                "Kategori": cat,
                "Varlık İsmi": asset['name'],
                "Son Fiyat": p_str,
                "Günlük (%)": d_chg,
                "Haftalık (%)": w_chg,
                "Aylık (%)": m_chg
            })
            
    if table_rows:
        df_market = pd.DataFrame(table_rows)
        
        # Color Styling Function
        def color_coding(val):
            if isinstance(val, (int, float)):
                color = '#4CAF50' if val > 0 else '#FF5252' if val < 0 else '#FFFFFF'
                return f'color: {color}'
            return ''

        # Apply styling
        # Note: formatting floats in pandas display
        st.dataframe(
            df_market.style.format({
                "Günlük (%)": "{:+.2f}%",
                "Haftalık (%)": "{:+.2f}%",
                "Aylık (%)": "{:+.2f}%"
            }).map(color_coding, subset=["Günlük (%)", "Haftalık (%)", "Aylık (%)"]),
            use_container_width=True,
            height=500
        )
    else:
        st.warning("Veri alınamadı.")
        
    st.markdown("---")
    
    # 2. Akıllı Haber Akışı
    st.subheader("📢 Piyasa Haberleri ve Beklentiler")
    
    # Define key assets to scan for news
    news_targets = ["XU100.IS", "USDTRY=X", "BTC-USD", "GC=F", "AAPL", "NVDA", "THYAO.IS"]
    
    with st.spinner("Haber akışları taranıyor ve analiz ediliyor..."):
        news_items = []
        for sym in news_targets:
            s_data = get_sentiment_score(sym)
            if s_data and s_data.get('timestamp', 0) > 0 and s_data.get('is_fresh'): # Only fresh news? Or all? User said "En Yeni". Let's include all but prioritizing fresh.
                # Enrich with symbol name roughly
                s_data['symbol'] = sym
                news_items.append(s_data)
        
        # Sort: 1. Timestamp (Desc), 2. Score (Abs Desc - Impact)
        # Actually user said: Prioritize Newest, then Impact.
        # So primary sort key is timestamp.
        news_items.sort(key=lambda x: (x.get('timestamp', 0), abs(x.get('score', 0))), reverse=True)
        
    # Display News
    if news_items:
        for news in news_items:
            # Color badge
            lbl = news['label']
            if lbl == "POZİTİF": color = "green"
            elif lbl == "NEGATİF": color = "red"
            else: color = "gray"
            
            with st.expander(f"{news['time_label']} | {news['title']} ({news['symbol']})", expanded=True):
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.caption("Yapay Zeka Görüşü")
                    st.markdown(f":{color}[{lbl}]")
                    st.progress( (news['score'] + 1) / 2 ) # Map -1..1 to 0..1
                with c2:
                    st.write(f"**Etki Puanı:** {news['score']}")
                    st.info(f"Haber saati: {datetime.fromtimestamp(news.get('timestamp', 0)).strftime('%H:%M')}")
    else:
        st.info("Şu an için taranan varlıklarda güncel haber akışı bulunmuyor.")

# --- 2. HİSSE TARAMA ---
# --- 2. HİSSE TARAMA (YENİLENMİŞ) ---
elif page == "Hisse Tarama":
    st.title("🔍 Hisse Senedi & ETF Tarama Pro")
    
    tabs1, tabs2 = st.tabs(["🇹🇷 BIST Akıllı Sıralama", "🇺🇸 ABD ETF Fırsatları"])
    
    with tabs1:
        st.header("BIST Değer Analizi (Sıralı Liste)")
        st.info("""
        **Sıralama Mantığı (Ucuzdan Pahalıya):**
        - **Bankalar & GYO'lar:** PD/DD puanına göre sıralanır. (Düşük = İyi)
        - **Sanayi & Hizmetler:** FD/FAVÖK puanına göre sıralanır. (Düşük = İyi)
        *Tüm BIST 30+ hisseleri taranır, eleme yapılmaz.*
        """)
        
        if st.button("🔄 Sıralamayı Güncelle (BIST)", key="btn_bist_scan"):
            with st.spinner("Piyasa verileri analiz ediliyor ve puanlanıyor..."):
                df_bist = fetch_bist_data()
                
            if isinstance(df_bist, pd.DataFrame) and not df_bist.empty:
                st.success(f"{len(df_bist)} hisse analiz edildi ve sıralandı.")
                
                # Helper for display
                def fmt_decimal(val):
                    if val == -1 or val is None: return "Veri Yok"
                    return f"{val:.2f}"
                
                df_display = df_bist.copy()
                df_display['PD/DD'] = df_display['PD/DD'].apply(lambda x: x if x != -1 else None)
                df_display['FD/FAVÖK'] = df_display['FD/FAVÖK'].apply(lambda x: x if x != -1 else None)
                
                # Styling
                st.dataframe(
                    df_display.style.format({
                        "Fiyat": "{:.2f} ₺",
                        "Günlük (%)": "{:+.2f}%",
                        "PD/DD": "{:.2f}",
                        "FD/FAVÖK": "{:.2f}"
                    }, na_rep="-")
                    .background_gradient(subset=["PD/DD", "FD/FAVÖK"], cmap="RdYlGn_r", vmin=0, vmax=10)
                    .map(lambda x: f"color: {'green' if x > 0 else 'red'}", subset=["Günlük (%)"]), 
                    use_container_width=True,
                    height=600
                )
            else:
                st.warning("Veri çekilemedi.")
                
    with tabs2:
        st.header("ABD ETF Dünyası (Sabit Takip)")
        st.caption("Veriler ETF.com ve Yahoo Finance hibrit yapısı ile sağlanmaktadır.")
        
        with st.spinner("ETF verileri güncelleniyor..."):
            df_etf = fetch_us_etf_data()
            
        if isinstance(df_etf, pd.DataFrame) and not df_etf.empty:
            # Sort by YTD Return Desc
            df_etf = df_etf.sort_values("YTD Getiri (%)", ascending=False)
            
            st.dataframe(
                df_etf.style.format({
                    "YTD Getiri (%)": "{:+.2f}%",
                    "Masraf (%)": "{:.2f}%",
                    "Fiyat ($)": "${:.2f}"
                }).bar(subset=["YTD Getiri (%)"], align="mid", color=['#d65f5f', '#5fba7d']),
                use_container_width=True
            )
        else:
            st.warning("ETF verileri alınamadı.")

# --- 3. FON ANALİZİ ---
elif page == "Fon Analizi":
    st.title("TEFAS Fon Analizi")
    fund_code = create_search_box("Fon Kodu (Örn: TCD, AFT)", type="fund", key="fund_sym")

    if fund_code:
        # TEFAS'tan veri çekme simülasyonu veya gerçek istek
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
                    fig.update_layout(template="plotly_dark")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.dataframe(alloc)
            else:
                st.info("Varlık dağılım verisi bulunamadı.")

# --- 4. PORTFÖY DENGELEYİCİ ---
elif page == "Portföy Dengeleyici":
    st.title("⚖️ Portföy Dengeleyici (Smart Rebalance)")
    st.markdown("Yeni yatırımlarınızı hedef portföy yüzdelerinize göre otomatik olarak dağıtın.")

    # 1. Mevcut Durumu Göster (GERÇEK VERİLERDEN)
    st.subheader("Mevcut Portföy Dağılımı (Gerçek)")
    real_portfolio = get_portfolio_by_category()

    if not real_portfolio:
        st.warning("Henüz cüzdanınızda varlık bulunmuyor. Lütfen 'Cüzdanım' sayfasından işlem ekleyin veya hedef analizi için örnek verileri kontrol edin.")
        # Fallback to empty context or sample if requested
        real_portfolio = {cat: 0 for cat in config.PORTFOLIO_TARGETS}

    current_df = pd.DataFrame(list(real_portfolio.items()), columns=["Kategori", "Mevcut Değer (TL)"])
    current_df["Hedef (%)"] = current_df["Kategori"].map(config.PORTFOLIO_TARGETS).fillna(0)

    total_val = current_df["Mevcut Değer (TL)"].sum()
    if total_val > 0:
        current_df["Mevcut (%)"] = (current_df["Mevcut Değer (TL)"] / total_val * 100).round(2)
    else:
        current_df["Mevcut (%)"] = 0

    st.table(current_df)
    st.write(f"**Toplam Portföy Değeri:** {total_val:,.2f} ₺")

    st.markdown("---")

    # 2. Yeni Yatırım Girişi
    new_investment = st.number_input("Yatırılacak Tutar (TL)", min_value=0, value=10000, step=1000)

    if st.button("Hesapla"):
        suggestions = calculate_rebalance(
            new_investment,
            real_portfolio,
            config.PORTFOLIO_TARGETS
        )

        st.success("✅ Dağıtım Önerisi Hazır")

        s_df = pd.DataFrame(list(suggestions.items()), columns=["Kategori", "Alınacak Tutar (TL)"])
        fig = px.bar(s_df, x="Kategori", y="Alınacak Tutar (TL)", title="Yeni Yatırım Dağılımı")
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

        st.info(get_rebalance_summary(suggestions))

        st.subheader("İşlem Detayları")
        st.table(s_df.style.format({"Alınacak Tutar (TL)": "{:,.2f}"}))

# --- 5. STRATEJİ TESTİ (BACKTEST) ---
elif page == "Strateji Testi":
    st.title("🧪 Strateji Testi (Backtest)")
    st.markdown("Geçmiş veriler üzerinde stratejilerinizi test edin ve performansını ölçün.")

    st.subheader("B. Geriye Dönük Test (Backtest)")
    backtest_symbol = create_search_box("Test Edilecek Sembol", key="bt_sym")

    if backtest_symbol:
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            initial_cap = st.number_input("Başlangıç Sermayesi ($/TL)", value=1000, step=100)
        with col_b2:
            strategy_choice = st.selectbox("Strateji Seçimi", ['RSI Stratejisi (30/70)', 'SMA Cross (50/200)', 'Al ve Tut', 'Smart DCA', 'Normal DCA'])

        is_periodic = st.toggle("Dönemsel (Yıllık) Test")
    monthly_dca = 0
    if 'DCA' in strategy_choice:
        monthly_dca = st.number_input("Aylık Alım Tutarı", value=100, step=50)
        
    if st.button("Simülasyonu Başlat"):
        with st.spinner(f"{backtest_symbol} için simülasyon çalıştırılıyor..."):
            df_hist = get_yfinance_data(backtest_symbol, period="5y") # Longer period for periodic tests
            
            if not df_hist.empty:
                if is_periodic:
                    periodic_results = run_periodic_backtest(df_hist, strategy_choice, initial_cap)
                    if periodic_results:
                        st.subheader("🗓️ Yıllık Performans Kıyaslaması")
                        summary_data = []
                        for res in periodic_results:
                            m = res['metrics']
                            summary_data.append({
                                "Yıl": m['year'],
                                "Yatırılan": m.get('total_invested', initial_cap),
                                "Son Bakiye": m['final_equity'],
                                "Getiri (%)": f"%{m['total_return_pct']}"
                            })
                        st.table(summary_data)
                        
                        # Multi-year chart (Just show the combined curve or first/last?)
                        # For simplicity, we'll show the combined metrics in a bar chart
                        perf_df = pd.DataFrame(summary_data)
                        perf_df["Getiri Sayısal"] = perf_df["Getiri (%)"].str.replace('%', '').astype(float)
                        fig_p = px.bar(perf_df, x="Yıl", y="Getiri Sayısal", title="Yıllara Göre Getiri (%)")
                        st.plotly_chart(fig_p, use_container_width=True)
                else:
                    results = run_backtest(df_hist, strategy_choice, initial_cap, monthly_dca=monthly_dca)
                    if results:
                        metrics = results['metrics']
                        equity_df = results['equity_curve']
                        
                        m_col1, m_col2, m_col3 = st.columns(3)
                        m_col1.metric("Toplam Getiri", f"%{metrics['total_return_pct']}", delta=f"{metrics['total_return_pct']}%")
                        m_col2.metric("Son Bakiye", f"{metrics['final_equity']:,} {config.SYMBOLS.get('currency', '₺')}")
                        m_col3.metric("Yatırılan Toplam", metrics.get('total_invested', initial_cap))
                        
                        st.markdown("---")
                        
                        st.subheader("Performans Grafiği")
                        fig_bt = px.line(equity_df, y=['Strategy_Equity', 'BuyHold_Equity'], 
                                       labels={"value": "Sermaye Değeri", "index": "Tarih"},
                                       title=f"{backtest_symbol} için {strategy_choice} Performansı")
                        fig_bt.update_layout(template="plotly_dark", height=500)
                        st.plotly_chart(fig_bt, use_container_width=True)
                        
                        if 'DCA' in strategy_choice:
                            st.info("💡 Smart DCA: Fiyat SMA200 altındaysa 1.5x, RSI > 80 ise 0.5x alım yapar.")
                    else:
                        st.error("Simülasyon sırasında hata oluştu.")
            else:
                st.warning(f"{backtest_symbol} için yeterli veri bulunamadı.")

# --- 6. CÜZDANIM (PORTFOLIO) ---
# --- 6. CÜZDANIM (PORTFOLIO PRO) ---
elif page == "Cüzdanım":
    st.title("📱 Portföyüm")
    
    # Fetch Data
    with st.spinner("Portföy verileri hazırlanıyor..."):
        holdings = get_portfolio_balance()
        
        # Calculate Total Values
        total_tl = sum([h['total_value_tl'] for h in holdings]) if holdings else 0
        
        # USD Conversion (Simple)
        usd_rate = 35.0
        try:
            usd_rate = market_data['usd'] # Re-use if fetched, else fetch
        except:
            pass
        total_usd = total_tl / usd_rate
        
        # Historical Data for Chart
        from portfolio_manager import get_benchmark_data, get_portfolio_history
        port_history = get_portfolio_history(holdings, period="1y") if holdings else None
        
    # --- KATMAN 1: Özet ve Görselleştirme ---
    
    # 1. Total Metrics (Big)
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
         st.markdown(f"""
         <div style="text-align: center;">
             <p style="margin:0; color:#888; font-size: 14px;">Toplam Varlık (TL)</p>
             <h1 style="margin:0; font-size: 36px; color: #4CAF50;">₺{total_tl:,.2f}</h1>
         </div>
         """, unsafe_allow_html=True)
         
    with row1_col2:
        st.markdown(f"""
         <div style="text-align: center;">
             <p style="margin:0; color:#888; font-size: 14px;">Toplam Varlık (USD)</p>
             <h1 style="margin:0; font-size: 36px; color: #2196F3;">${total_usd:,.2f}</h1>
         </div>
         """, unsafe_allow_html=True)
    
    st.write("")
    
    # 2. Charts (Line + Donut)
    c_chart1, c_chart2 = st.columns([2, 1])
    
    with c_chart1:
        if port_history is not None and not port_history.empty:
            fig_l = px.area(port_history, title="Portföy Değişim Grafiği (TL)", labels={"value": "Değer", "index": "Tarih"})
            fig_l.update_layout(template="plotly_dark", height=300, showlegend=False, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_l, use_container_width=True)
        else:
            st.info("Grafik için yeterli veri yok.")
            
    with c_chart2:
        if holdings:
            df_h = pd.DataFrame(holdings)
            fig_d = px.pie(df_h, values='total_value_tl', names='symbol', hole=0.4, title="Dağılım")
            fig_d.update_layout(template="plotly_dark", height=300, showlegend=False, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_d, use_container_width=True)

    st.markdown("---")
    
    # --- KATMAN 2: Varlık Listesi (Kart Görünümü) ---
    st.subheader("📋 Varlıklarınız")
    
    if holdings:
        for h in holdings:
            # Color for P/L
            pl_color = "#4CAF50" if h['profit_tl'] >= 0 else "#FF5252"
            
            with st.container():
                # Card-like layout
                cc1, cc2, cc3, cc4, cc5 = st.columns([1, 1, 1, 1, 1])
                
                cc1.markdown(f"**{h['symbol']}**")
                cc2.caption("Fiyat")
                cc2.write(f"{h['current_price_tl']:.2f}")
                
                cc3.caption("Adet")
                cc3.write(f"{h['quantity']}")
                
                cc4.caption("Değer")
                cc4.write(f"{h['total_value_tl']:,.0f}")
                
                cc5.caption("K/Z")
                cc5.markdown(f"<span style='color:{pl_color}; font-weight:bold;'>{h['profit_tl']:,.0f} ({h['profit_pct']:.1f}%)</span>", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin:5px 0; opacity:0.2;'>", unsafe_allow_html=True)
    else:
        st.info("Portföyünüz boş.")

    st.markdown("---")

    # --- KATMAN 3: Sekmeli Analiz ---
    tab1, tab2, tab3 = st.tabs(["📊 Detaylı Analiz", "📈 Kıyaslama", "➕ İşlemler"])
    
    with tab1:
        if holdings:
            st.caption("Detaylı Portföy Tablosu")
            # Create Detailed DF
            detailed_data = []
            for h in holdings:
                weight = (h['total_value_tl'] / total_tl) * 100 if total_tl > 0 else 0
                detailed_data.append({
                    "Varlık": h['symbol'],
                    "Ağırlık (%)": f"%{weight:.1f}",
                    "Ort. Maliyet": f"{h['avg_cost']:.2f}",
                    "Güncel Fiyat": f"{h['current_price_tl']:.2f}",
                    "Toplam Değer": f"{h['total_value_tl']:,.2f}",
                    "Kar/Zarar": f"{h['profit_tl']:,.2f}"
                })
            st.dataframe(pd.DataFrame(detailed_data), use_container_width=True)
    
    with tab2:
        st.subheader("Endekslerle Performans Kıyaslaması (1 Yıl)")
        
        # Custom Competitor Input
        custom_comp = create_search_box("VS Özel Rakip Ekle", key="bench_sym")
        
        if port_history is not None:

            with st.spinner("Benchmark verileri çekiliyor..."):
                bench_df = get_benchmark_data(period="1y", custom_ticker=custom_comp if custom_comp else None)
                
            if not bench_df.empty:
                # Merge Portfolio History
                # Normalize all to start at 0%
                
                merged = bench_df.copy()
                merged["Portföyüm"] = port_history
                
                # Align dates (intersection)
                merged = merged.ffill().dropna()
                
                if not merged.empty:
                    # Normalize: (Price / StartPrice - 1) * 100
                    norm_df = merged.apply(lambda x: ((x / x.iloc[0]) - 1) * 100)
                    
                    fig_bm = px.line(norm_df, title="Getiri Karşılaştırması (%)")
                    fig_bm.update_layout(template="plotly_dark", height=400)
                    st.plotly_chart(fig_bm, use_container_width=True)
                else:
                    st.warning("Tarih eşleşmesi yapılamadı.")
            else:
                st.warning("Benchmark verisi alınamadı.")
    
    with tab3:
        st.subheader("İşlem Ekle / Çıkar")
        with st.form("transaction_form_new", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                t_date = st.date_input("İşlem Tarihi")
                t_symbol = create_search_box("Hisse Sembolü", key="trans_sym")
            with col2:
                t_type = st.selectbox("İşlem Türü", ["BUY", "SELL"])
                t_qty = st.number_input("Adet", min_value=0.01, step=1.0)
            with col3:
                t_price = st.number_input("Fiyat", min_value=0.01, step=0.1)
                submitted = st.form_submit_button("💾 Kaydet")
                
            if submitted:
                 if t_symbol:
                    add_transaction(t_date.strftime("%Y-%m-%d"), t_symbol, t_type, t_qty, t_price)
                    st.success("İşlem kaydedildi! Veriler güncelleniyor...")
                    time.sleep(1)
                    st.rerun()
                 else:
                    st.error("Sembol giriniz.")
        
        # History Table
        st.subheader("Geçmiş İşlemler")
        history = get_all_transactions()
        if not history.empty:
            st.dataframe(history.drop(columns=['id']), use_container_width=True, height=200)

# --- 7. GÖLGE PORTFÖY (PAPER TRADING) ---
elif page == "👻 Gölge Portföy":
    st.title("👻 Gölge Portföy (Paper Trading)")
    st.markdown("Botun kendi kendine yaptığı sanal işlemleri ve performansını takip edin.")
    
    # Metrics
    balance = paper_trader.get_virtual_balance()
    initial_balance = 100000.0
    total_profit = balance - initial_balance
    profit_pct = (total_profit / initial_balance) * 100
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Sanal Bakiye", f"{balance:,.2f} ₺")
    c2.metric("Toplam Kar/Zarar", f"{total_profit:,.2f} ₺", delta=f"{profit_pct:.2f}%")
    c3.info(f"Bot Stratejisi: \n- Teknik Puan > 80: AL \n- Teknik Puan < 40: SAT")
    
    st.markdown("---")
    
    # Bot Control
    st.subheader("🤖 Bot Kontrol Merkezi")
    force_bot = st.toggle("🧪 Test Modu (Sinyal gelmese de ilk hisseyi al/sat)")
    
    if st.button("Botu Çalıştır (Piyasayı Tara & İşlem Yap)"):
        # Sample scanning list (can be expanded)
        scan_list = ["THYAO", "EREGL", "ASELS", "SISE", "AKBNK", "KCHOL", "TUPRS", "SAHOL", "BIMAS"]
        logs = paper_trader.run_paper_bot(scan_list, force_trade=force_bot)
        
        if logs:
            st.success(f"İşlem özeti: {len(logs)} aksiyon alındı.")
        
        # We don't need a rerun here because the bot function already updated the UI 
        # but a rerun helps refreshing the metrics/tables below.
        st.button("Verileri Yenile")

    st.markdown("---")
    
    # Open Positions
    st.subheader("📦 Açık Pozisyonlar")
    open_pos = paper_trader.get_open_paper_positions()
    if open_pos:
        pos_list = []
        for sym, qty in open_pos.items():
            try:
                yf_sym = sym if "." in sym or "-" in sym else sym + ".IS"
                curr_price = yf.Ticker(yf_sym).history(period="1d")['Close'].iloc[-1]
                pos_list.append({"Sembol": sym, "Adet": round(qty, 2), "Güncel Fiyat": round(curr_price, 2)})
            except:
                pos_list.append({"Sembol": sym, "Adet": round(qty, 2), "Güncel Fiyat": "---"})
        st.table(pos_list)
    else:
        st.info("Henüz bot tarafından açılmış bir sanal pozisyon bulunmuyor.")

    # History
    st.subheader("📜 Bot İşlem Geçmişi")
    history = paper_trader.get_paper_history()
    if not history.empty:
        st.dataframe(history.drop(columns=['id']), use_container_width=True)
    else:
        st.write("Henüz bir işlem kaydı yok.")

# --- 8. RAPORLAR (BENCHMARK) ---
elif page == "Raporlar":
    st.title("📊 Kıyaslamalı Performans Raporu")
    st.markdown(f"Varlıkların son 1 yıllık performansı (Enflasyon Beklentisi: %{config.ANNUAL_INFLATION_RATE})")
    
    with st.spinner("Benchmark verileri çekiliyor..."):
        benchmark_df = get_benchmark_data()
        
    if not benchmark_df.empty:
        summary = get_benchmark_summary(benchmark_df)
        
        # Display Metrics in a Table for clarity
        report_table = []
        for asset, stats in summary.items():
            report_table.append({
                "Varlık": asset,
                "Nominal Getiri (%)": stats['nominal'],
                "Reel Getiri (%)": stats['real'],
                "Sharpe Oranı": stats['sharpe']
            })
        
        st.table(pd.DataFrame(report_table))
            
        st.markdown("---")
        
        fig = px.line(benchmark_df, title="Son 1 Yıl Performans Kıyaslaması (Baz 100)",
                     labels={"value": "Endeks Değeri", "index": "Tarih"})
        fig.update_layout(template="plotly_dark", height=600)
        st.plotly_chart(fig, use_container_width=True)
        
        st.info(f"💡 Sharpe Oranı > 1.0 olması risk başına alınan getirinin tatminkar olduğunu gösterir. Reel getiri %{config.ANNUAL_INFLATION_RATE} enflasyon düşüldükten sonra kalan net kazançtır.")
    else:
        st.error("Benchmark verileri alınamadı.")

# --- 8. BİLGİ NOTU ---
elif page == "Bilgi Notu":
    st.title("📝 Günlük Bilgi Notu & Takvim")
    
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
