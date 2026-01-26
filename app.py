import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime
import pytz 

# Yerel Modüller (Senin dosya yapına uygun)
from screener_module import fetch_bist_data, fetch_us_etf_data
from fund_module import fetch_tefas_data, get_fund_history
from calendar_module import fetch_economic_calendar
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

# --- Session State Başlatma ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'guest_mode' not in st.session_state:
    st.session_state['guest_mode'] = False
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = None
if 'page' not in st.session_state:
    st.session_state['page'] = 'Giriş'

# Veritabanını başlat
init_db()

# --- GİRİŞ EKRANI (LOGIN UI) ---
def login_ui():
    st.set_page_config(page_title="Finans Botu", layout="centered", initial_sidebar_state="collapsed")
    
    st.markdown("<h1 style='text-align: center; color: #4CAF50;'>Finans Botu 🤖</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Kişisel Finans Asistanınız</p>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Giriş Yap", "Kayıt Ol", "Misafir"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("E-posta Adresi")
            password = st.text_input("Şifre", type="password")
            submitted = st.form_submit_button("Giriş Yap")
            
            if submitted:
                from database import verify_user
                user, msg = verify_user(email, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.session_state.guest_mode = False
                    st.session_state.user_email = user['email'] # Email'i state'e kaydet
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
    
    with tab2:
        with st.form("register_form"):
            new_name = st.text_input("Ad Soyad")
            new_email = st.text_input("E-posta Adresi")
            new_pass = st.text_input("Şifre", type="password")
            reg_submitted = st.form_submit_button("Kayıt Ol")
            
            if reg_submitted:
                from database import add_user
                if new_email and new_pass:
                    success, msg = add_user(new_email, new_pass, new_name)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.warning("Lütfen tüm alanları doldurunuz.")

    with tab3:
        st.info("Üye olmadan sadece piyasa verilerini inceleyebilirsiniz. Portföy kaydetme özelliği kapalıdır.")
        if st.button("Misafir Olarak Devam Et"):
            st.session_state['logged_in'] = True
            st.session_state['guest_mode'] = True
            st.session_state['user_info'] = {'name': 'Misafir', 'email': 'guest'}
            st.session_state['user_email'] = 'guest'
            st.rerun()

# --- ERİŞİM KONTROLÜ ---
if not st.session_state['logged_in']:
    login_ui()
    st.stop()

# --- YARDIMCI FONKSİYONLAR ---

# Yfinance Önbellekleme
@st.cache_data(ttl=900)
def get_yfinance_data(symbol, period="1y"):
    try:
        ticker = yf.Ticker(symbol)
        return ticker.history(period=period)
    except:
        return pd.DataFrame()

# Arama Kutusu (Manuel Giriş Destekli)
def create_search_box(label, type="general", key=None):
    if type == "fund":
        options = config.TEFAS_FUNDS
    else:
        options = config.ALL_SYMBOLS
        
    selected = st.selectbox(label, [""] + options, key=f"sel_{key}" if key else None)
    manual_entry = st.checkbox("Listede yok mu? Manuel gir", key=f"chk_{key}" if key else None)
    
    if manual_entry:
        return st.text_input(f"{label} (Manuel)", key=f"txt_{key}" if key else None).upper()
    return selected

# --- UYGULAMA ANA YAPISI ---

st.set_page_config(page_title="Finansal Takip Botu", page_icon="📈", layout="wide")

# --- SIDEBAR (SOL MENÜ) ---
if st.session_state.get('logged_in'):
    user_name = st.session_state.user_info.get('name') or st.session_state.user_info.get('email')
    if st.session_state.get('guest_mode'):
        user_name = "Misafir Kullanıcı"
        
    st.sidebar.caption(f"👤 {user_name}")
    if st.sidebar.button("🚪 Çıkış Yap", key="logout_btn_top"):
        st.session_state['logged_in'] = False
        st.session_state['user_info'] = None
        st.session_state['guest_mode'] = False
        st.session_state['user_email'] = None
        st.rerun()

st.sidebar.title("Finans Botu 🤖")

# Menü Listesi (Bilgi Notu Kaldırıldı, Portföy Birleştirildi)
menu_options = ["Piyasa Özeti", "Hisse Tarama", "Fon Analizi", "Portföyüm", "Portföy Dengeleyici", "Strateji Testi", "Raporlar"]
page = st.sidebar.radio("Menü", menu_options)

st.sidebar.markdown("---")

# 📧 Bülten Aboneliği
st.sidebar.subheader("📩 Bülten Aboneliği")
with st.sidebar.form("sub_form"):
    # Eğer giriş yapmış kullanıcı ise mailini otomatik getir
    default_sub_mail = st.session_state.user_email if not st.session_state.guest_mode else ""
    user_email_sub = st.text_input("E-posta Adresi", value=default_sub_mail, placeholder="ornek@gmail.com")
    c1, c2 = st.columns(2)
    daily_sub = c1.checkbox("Günlük", value=True)
    weekly_sub = c2.checkbox("Haftalık", value=True)
    
    sub_btn = st.form_submit_button("Abone Ol / Güncelle")
    
    if sub_btn:
        if user_email_sub and "@" in user_email_sub:
            with st.spinner("İşlem yapılıyor..."):
                success, msg = subscription_module.add_subscriber(user_email_sub, daily_sub, weekly_sub)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
        else:
            st.warning("Geçerli bir e-posta giriniz.")

st.sidebar.markdown("---")

# 🚀 Hızlı Gönderim (DÜZELTİLMİŞ KOD BLOĞU)
st.sidebar.subheader("🚀 Hızlı Gönderim (Test)")

# Kullanıcı belirleme
current_user = st.session_state.get('user_email')
is_guest = st.session_state.get('guest_mode', False)

# İpucu metni
hint_text = "me@test.com"
if current_user and not is_guest:
    hint_text = f"Boşsa: {current_user}"

test_email = st.sidebar.text_input("Hedef Email", placeholder=hint_text, help="Boş bırakırsanız kayıtlı mailinize gönderilir.")

if st.sidebar.button("Raporu Bana Şimdi Gönder"):
    # 1. Hedef Belirleme
    target = test_email
    if not target and current_user and not is_guest:
        target = current_user
        
    # 2. Kontrol
    if not target:
        st.sidebar.error("Lütfen geçerli bir e-posta adresi girin.")
    else:
        # 3. Gönderim İşlemi
        with st.sidebar.status(f"Rapor hazırlanıyor: {target}...", expanded=True) as status:
            try:
                success, msg = send_newsletter(target, "Günlük")
                if success:
                    status.update(label="Gönderim Başarılı!", state="complete", expanded=False)
                    st.sidebar.success(f"✅ Gönderildi:\n{target}")
                else:
                    status.update(label="Hata Oluştu", state="error")
                    st.sidebar.error(f"Hata: {msg}")
            except Exception as e:
                status.update(label="Sistem Hatası", state="error")
                st.sidebar.error(f"Beklenmedik hata: {str(e)}")

st.sidebar.markdown("---")

# ⏰ Otomatik Zamanlayıcı (Basitleştirilmiş)
# st.sidebar.subheader("⏰ Otomatik Zamanlayıcı") ... (İsteğe bağlı, kod karmaşasını önlemek için kapalı tutulabilir veya eklenebilir. Şimdilik sade tutuyorum)

# --- SAYFA İÇERİKLERİ ---

# --- 1. PİYASA ÖZETİ ---
if page == "Piyasa Özeti":
    st.title("📊 Piyasa Kokpiti")
    
    # A. Ekonomik Takvim (Bilgi Notu Sayfasından Buraya Taşındı)
    with st.expander("📅 Ekonomik Takvim & Beklentiler", expanded=False):
        cal_filter = st.radio("Bölge Seçimi:", ["Türkiye (TR)", "ABD (US)", "Global (All)"], horizontal=True)
        filter_map = {"Türkiye (TR)": "TR", "ABD (US)": "US", "Global (All)": "ALL"}
        
        # Takvim verisini çek
        calendar_data = fetch_economic_calendar(country=filter_map[cal_filter])
        
        if not calendar_data.empty:
            st.dataframe(calendar_data, use_container_width=True, hide_index=True)
        else:
            st.info("Seçilen filtre için bugün önemli bir veri akışı bulunmuyor.")

    st.markdown("---")

    # B. Geniş Pazar Tablosu
    st.subheader("🌍 Küresel Piyasalar ve Varlıklar")
    
    with st.spinner("Piyasa verileri güncelleniyor..."):
        raw_data = fetch_newsletter_data()
        
    table_rows = []
    for cat, assets in raw_data.items():
        for asset in assets:
            price = asset.get('price', 0)
            table_rows.append({
                "Kategori": cat,
                "Varlık İsmi": asset['name'],
                "Son Fiyat": price,
                "Günlük (%)": asset.get('daily', 0),
                "Haftalık (%)": asset.get('weekly', 0),
                "Aylık (%)": asset.get('monthly', 0)
            })
            
    if table_rows:
        df_market = pd.DataFrame(table_rows)
        
        def color_coding(val):
            if isinstance(val, (int, float)):
                color = '#4CAF50' if val > 0 else '#FF5252' if val < 0 else '#FFFFFF'
                return f'color: {color}'
            return ''

        st.dataframe(
            df_market.style.format({
                "Son Fiyat": "{:,.2f}",
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
    
    # C. Haber Akışı
    st.subheader("📢 Piyasa Haberleri ve Beklentiler")
    news_targets = ["XU100.IS", "USDTRY=X", "BTC-USD", "GC=F", "AAPL", "NVDA", "THYAO.IS"]
    
    with st.spinner("Haber akışları taranıyor..."):
        news_items = []
        for sym in news_targets:
            s_data = get_sentiment_score(sym)
            if s_data and s_data.get('timestamp', 0) > 0:
                s_data['symbol'] = sym
                news_items.append(s_data)
        
        news_items.sort(key=lambda x: (x.get('timestamp', 0)), reverse=True)
        
    if news_items:
        for news in news_items:
            lbl = news['label']
            color = "green" if lbl == "POZİTİF" else "red" if lbl == "NEGATİF" else "gray"
            
            with st.expander(f"{news['time_label']} | {news['title']} ({news['symbol']})"):
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.markdown(f":{color}[**{lbl}**]")
                    st.progress((news['score'] + 1) / 2)
                with c2:
                    st.write(f"Etki Puanı: {news['score']}")
                    st.caption(f"Saat: {datetime.fromtimestamp(news.get('timestamp', 0)).strftime('%H:%M')}")
    else:
        st.info("Güncel haber akışı bulunmuyor.")

# --- 2. HİSSE TARAMA ---
elif page == "Hisse Tarama":
    st.title("🔍 Hisse Senedi & ETF Tarama Pro")
    
    tabs1, tabs2 = st.tabs(["🇹🇷 BIST Akıllı Sıralama", "🇺🇸 ABD ETF Fırsatları"])
    
    with tabs1:
        st.header("BIST Değer Analizi")
        st.info("Bankalar PD/DD, Sanayi şirketleri FD/FAVÖK oranına göre sıralanır.")
        
        if st.button("🔄 Sıralamayı Güncelle (BIST)", key="btn_bist_scan"):
            with st.spinner("Analiz yapılıyor..."):
                df_bist = fetch_bist_data()
                
            if not df_bist.empty:
                st.success(f"{len(df_bist)} hisse analiz edildi.")
                st.dataframe(
                    df_bist.style.format({
                        "Fiyat": "{:.2f} ₺",
                        "Günlük (%)": "{:+.2f}%",
                        "PD/DD": "{:.2f}",
                        "FD/FAVÖK": "{:.2f}"
                    }).background_gradient(subset=["PD/DD", "FD/FAVÖK"], cmap="RdYlGn_r"),
                    use_container_width=True,
                    height=600
                )
            else:
                st.warning("Veri çekilemedi.")
                
    with tabs2:
        st.header("ABD ETF Dünyası")
        with st.spinner("ETF verileri güncelleniyor..."):
            df_etf = fetch_us_etf_data()
            
        if not df_etf.empty:
            st.dataframe(
                df_etf.style.format({"YTD Getiri (%)": "{:+.2f}%", "Fiyat ($)": "${:.2f}"}),
                use_container_width=True
            )
        else:
            st.warning("ETF verileri alınamadı.")

# --- 3. FON ANALİZİ ---
elif page == "Fon Analizi":
    st.title("📊 TEFAS Fon Analizi & Karşılaştırma")
    
    if st.button("🔄 Verileri Güncelle"):
        st.cache_data.clear()
        
    with st.spinner("TEFAS verileri hazırlanıyor..."):
        df_funds = fetch_tefas_data()
        
    if not df_funds.empty:
        ftab1, ftab2 = st.tabs(["📋 Fon Tarama", "📈 Karşılaştırma"])
        
        with ftab1:
            search_term = st.text_input("Fon Ara (Ad veya Kod)", "").upper()
            filtered_df = df_funds.copy()
            if search_term:
                filtered_df = filtered_df[
                    filtered_df['Fon Kodu'].str.contains(search_term) | 
                    filtered_df['Fon Adı'].str.upper().str.contains(search_term)
                ]
            
            st.dataframe(
                filtered_df.style.format({
                    "Fiyat": "{:.4f} ₺",
                    "Günlük (%)": "{:+.2f}%",
                    "Yılbaşından Bugüne Getiri": "{:+.2f}%" # Sütun adı TEFAS modülünden ne geliyorsa ona dikkat edin
                }), use_container_width=True, height=600
            )
            
        with ftab2:
            all_codes = df_funds['Fon Kodu'].tolist()
            default_sel = [x for x in ["TCD", "MAC", "AFT"] if x in all_codes]
            selected_funds = st.multiselect("Karşılaştırılacak Fonlar:", all_codes, default=default_sel)
            
            if selected_funds:
                with st.spinner("Geçmiş veriler toplanıyor..."):
                    hist_df = get_fund_history(selected_funds)
                if not hist_df.empty:
                    fig_comp = px.line(hist_df, title="Getiri Karşılaştırması (%) - 1 Yıl")
                    st.plotly_chart(fig_comp, use_container_width=True)
                else:
                    st.warning("Veri bulunamadı.")
    else:
        st.error("TEFAS verileri çekilemedi.")

# --- 4. PORTFÖYÜM ---
elif page == "Portföyüm":
    if st.session_state.guest_mode:
        st.error("Misafir kullanıcılar portföy özelliğini kullanamaz. Lütfen giriş yapın.")
    else:
        st.title("📱 Portföyüm")
        user_email = st.session_state.user_email
    
        with st.spinner("Cüzdan verileri çekiliyor..."):
            holdings = get_portfolio_balance(user_email)
            total_tl = sum([h['total_value_tl'] for h in holdings]) if holdings else 0
            # Basit USD çevrimi
            total_usd = total_tl / 36.5 
            
            # Tarihsel veriyi al (Grafik için)
            from portfolio_manager import get_portfolio_history
            port_history = get_portfolio_history(holdings, period="1y") if holdings else None
            
        # Üst Bilgi Kartları
        c1, c2 = st.columns(2)
        c1.metric("Toplam Varlık (TL)", f"₺{total_tl:,.2f}")
        c2.metric("Toplam Varlık (USD)", f"${total_usd:,.2f}")
        
        st.markdown("---")
        
        # Grafikler
        col_g1, col_g2 = st.columns([2, 1])
        with col_g1:
            if port_history is not None and not port_history.empty:
                fig_l = px.area(port_history, title="Portföy Değerimi (TL)")
                fig_l.update_layout(template="plotly_dark", height=350)
                st.plotly_chart(fig_l, use_container_width=True)
            else:
                st.info("Zaman grafiği için yeterli veri yok.")
        
        with col_g2:
            if holdings:
                df_h = pd.DataFrame(holdings)
                fig_d = px.pie(df_h, values='total_value_tl', names='symbol', title="Varlık Dağılımı", hole=0.4)
                fig_d.update_layout(template="plotly_dark", height=350)
                st.plotly_chart(fig_d, use_container_width=True)
                
        # Varlık Listesi ve İşlemler
        tab_list, tab_trans = st.tabs(["📋 Varlıklarım", "➕ İşlem Ekle"])
        
        with tab_list:
            if holdings:
                df_disp = pd.DataFrame(holdings)
                st.dataframe(
                    df_disp[['symbol', 'quantity', 'avg_cost', 'current_price_tl', 'total_value_tl', 'profit_tl', 'profit_pct']]
                    .style.format({"total_value_tl": "{:,.2f}", "profit_tl": "{:,.2f}", "profit_pct": "{:.2f}%"}),
                    use_container_width=True
                )
            else:
                st.info("Henüz portföyünüzde varlık yok.")
                
        with tab_trans:
            with st.form("add_trans"):
                c_t1, c_t2, c_t3 = st.columns(3)
                t_sym = c_t1.text_input("Sembol (Örn: THYAO.IS)").upper()
                t_type = c_t2.selectbox("İşlem", ["BUY", "SELL"])
                t_date = c_t3.date_input("Tarih")
                
                c_t4, c_t5 = st.columns(2)
                t_qty = c_t4.number_input("Adet", min_value=0.01)
                t_price = c_t5.number_input("Fiyat", min_value=0.01)
                
                if st.form_submit_button("Kaydet"):
                    if t_sym:
                        add_transaction(t_date.strftime("%Y-%m-%d"), t_sym, t_type, t_qty, t_price, user_email)
                        st.success("İşlem eklendi!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Sembol giriniz.")

# --- 5. PORTFÖY DENGELEYİCİ ---
elif page == "Portföy Dengeleyici":
    st.title("⚖️ Portföy Dengeleyici")
    
    # Gerçek portföy verisini çek
    user_email_bal = st.session_state.user_email
    real_portfolio = get_portfolio_by_category(user_email_bal) if not st.session_state.guest_mode else {}
    
    # Eğer portföy boşsa varsayılan
    if not real_portfolio:
        real_portfolio = {k: 0 for k in config.PORTFOLIO_TARGETS.keys()}
        if not st.session_state.guest_mode:
            st.warning("Portföyünüz boş olduğu için hesaplama 0 bakiye üzerinden yapılacak.")

    new_investment = st.number_input("Yatırılacak Yeni Tutar (TL)", value=10000, step=1000)
    
    if st.button("Dağılımı Hesapla"):
        suggestions = calculate_rebalance(new_investment, real_portfolio, config.PORTFOLIO_TARGETS)
        
        s_df = pd.DataFrame(list(suggestions.items()), columns=["Kategori", "Alınacak Tutar"])
        fig = px.bar(s_df, x="Kategori", y="Alınacak Tutar", title="Önerilen Alımlar")
        st.plotly_chart(fig, use_container_width=True)
        st.table(s_df)

# --- 6. STRATEJİ TESTİ ---
elif page == "Strateji Testi":
    st.title("🧪 Strateji Testi (Backtest)")
    
    sym = st.text_input("Sembol (Örn: THYAO.IS)", "THYAO.IS").upper()
    capital = st.number_input("Başlangıç Sermayesi", value=10000)
    strategy = st.selectbox("Strateji", ['RSI Stratejisi (30/70)', 'SMA Cross (50/200)', 'Al ve Tut'])
    
    if st.button("Testi Başlat"):
        with st.spinner("Simülasyon çalışıyor..."):
            df_hist = get_yfinance_data(sym, period="5y")
            if not df_hist.empty:
                results = run_backtest(df_hist, strategy, capital)
                
                if results:
                    metrics = results['metrics']
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Toplam Getiri", f"%{metrics['total_return_pct']:.2f}")
                    c2.metric("Son Bakiye", f"{metrics['final_equity']:,.2f}")
                    
                    st.line_chart(results['equity_curve']['Strategy_Equity'])
                else:
                    st.error("Test hatası.")
            else:
                st.error("Veri bulunamadı.")

# --- 7. RAPORLAR ---
elif page == "Raporlar":
    st.title("📊 Kıyaslamalı Performans Raporu")
    
    with st.spinner("Benchmark verileri hazırlanıyor..."):
        bench_df = get_benchmark_data()
        
    if not bench_df.empty:
        summary = get_benchmark_summary(bench_df)
        st.table(pd.DataFrame(summary).T)
        
        fig = px.line(bench_df, title="Son 1 Yıl Performans (Baz 100)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Veri alınamadı.")