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
from benchmark_module import get_benchmark_data, get_benchmark_summary
from backtest_module import run_backtest, run_periodic_backtest
from mail_module import send_daily_report
from portfolio_manager import add_transaction, get_all_transactions, get_portfolio_balance, get_portfolio_by_category
from sentiment_module import get_sentiment_score
import paper_trader

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
        return f"{float(val):.2f} {currency}"
    except (ValueError, TypeError):
        return "---"

# Kenar Çubuğu (Navigasyon)
st.sidebar.title("Finans Botu 🤖")
page = st.sidebar.radio("Menü", ["Piyasa Özeti", "Hisse Tarama", "Fon Analizi", "Portföy Dengeleyici", "Strateji Testi", "Cüzdanım", "👻 Gölge Portföy", "Raporlar", "Bilgi Notu"])

st.sidebar.markdown("---")

# 📧 Mail Raporlama
st.sidebar.subheader("📧 Rapor Gönder")
target_email = st.sidebar.text_input("Alıcı Maili", st.secrets.get("GMAIL_USER", ""))
report_type = st.sidebar.selectbox("Rapor Tipi", ["Günlük", "Haftalık"])

if st.sidebar.button("Gönder"):
    with st.spinner("Rapor gönderiliyor..."):
        success, message = send_daily_report(target_email, report_type)
        if success:
            st.sidebar.success(message)
        else:
            st.sidebar.error(message)

st.sidebar.markdown("---")

# --- 1. PİYASA ÖZETİ ---
if page == "Piyasa Özeti":
    st.title("📊 Piyasa Özeti")
    
    # A. Gerçek Portföy Özeti (En Üstte)
    with st.spinner("Cüzdan özeti hazırlanıyor..."):
        holdings = get_portfolio_balance()
    
    if holdings:
        total_portfolio_val = sum([h['total_value_tl'] for h in holdings])
        st.metric("💰 Toplam Portföy Değeri", f"{total_portfolio_val:,.2f} ₺")
        
        # Pasta Grafik
        pie_data = [{"Sembol": h['symbol'], "Değer": h['total_value_tl']} for h in holdings]
        pie_df = pd.DataFrame(pie_data)
        fig_pie = px.pie(pie_df, values="Değer", names="Sembol", title="Cüzdan Dağılımı (Gerçek)")
        fig_pie.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown("---")

    # B. Global Sembol Seçimi
    symbol_to_track = st.text_input("Takip Edilecek Sembol (Yfinance)", "AAPL").upper()
    
    # Veri Çekme
    with st.spinner(f"{symbol_to_track} verileri analiz ediliyor..."):
        symbol_hist_full = get_yfinance_data(symbol_to_track, period="1y")
    
    # Üst Bilgi Kartları (Metrics)
    col1, col2, col3, col4, col5 = st.columns(5)
    market_data = get_market_summary()
    
    with col1:
        st.metric("USD/TRY", format_price(market_data['usd']))
    with col2:
        st.metric("EUR/TRY", format_price(market_data['eur']))
        
    with col3:
        try:
            xu030 = bp.Index("XU030")
            val = xu030.info.get('last') if hasattr(xu030, 'info') else "---"
            st.metric("BIST 30", format_price(val))
        except:
            st.metric("BIST 30", "Hata")

    with col4:
        if not symbol_hist_full.empty:
            st.metric(f"Sembol ({symbol_to_track})", format_price(symbol_hist_full['Close'].iloc[-1], "$"))
        else:
            st.metric(f"Sembol ({symbol_to_track})", "Yüklenemedi")

    with col5:
        with st.spinner("Sentiment analiz ediliyor..."):
            sentiment = get_sentiment_score(symbol_to_track)
            st.metric("Haber Algısı", sentiment['label'], delta=f"Skor: {sentiment['score']}")

    st.markdown("---")
    
    if not symbol_hist_full.empty:
        display_technical_analysis(symbol_hist_full, symbol_to_track)
    else:
        st.warning(f"{symbol_to_track} için analiz verisi bulunamadı.")

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
    
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    
    with b_col1:
        backtest_symbol = st.text_input("Hisse/Fon Sembolü", "BTC-USD").upper()
    with b_col2:
        initial_cap = st.number_input("Başlangıç Sermayesi ($/TL)", value=1000, step=100)
    with b_col3:
        strategy_choice = st.selectbox("Strateji Seçimi", ['RSI Stratejisi (30/70)', 'SMA Cross (50/200)', 'Al ve Tut', 'Smart DCA', 'Normal DCA'])
    with b_col4:
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
elif page == "Cüzdanım":
    st.title("💰 Cüzdanım (Portföy Takibi)")
    
    st.subheader("➕ Yeni İşlem Ekle")
    with st.form("transaction_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            t_date = st.date_input("İşlem Tarihi")
            t_symbol = st.text_input("Hisse Sembolü (Örn: THYAO, AAPL)").upper()
        with col2:
            t_type = st.selectbox("İşlem Türü", ["BUY", "SELL"])
            t_qty = st.number_input("Adet", min_value=0.01, step=0.1)
        with col3:
            t_price = st.number_input("Birim Fiyat (Döviz/TL)", min_value=0.01, step=0.01)
            submitted = st.form_submit_button("İşlemi Kaydet")
            
        if submitted:
            if t_symbol:
                add_transaction(t_date.strftime("%Y-%m-%d"), t_symbol, t_type, t_qty, t_price)
                st.success(f"{t_symbol} {t_type} işlemi başarıyla kaydedildi!")
                st.rerun()
            else:
                st.error("Lütfen bir sembol giriniz.")

    st.markdown("---")
    
    st.subheader("📂 Mevcut Varlıklarım")
    with st.spinner("Bakiyeler ve güncel fiyatlar hesaplanıyor..."):
        holdings = get_portfolio_balance()
    
    if holdings:
        # Build UI table using enriched data
        current_vals = []
        for h in holdings:
            current_vals.append({
                "Sembol": h['symbol'],
                "Adet": h['quantity'],
                "Maliyet (Döviz/TL)": h['avg_cost'],
                "Güncel Fiyat (TL)": h['current_price_tl'],
                "Güncel Değer (TL)": h['total_value_tl'],
                "Kar/Zarar (TL)": h['profit_tl'],
                "Kar/Zarar (%)": h['profit_pct']
            })
        
        res_df = pd.DataFrame(current_vals)
        st.table(res_df.style.format({
            "Maliyet (Döviz/TL)": "{:.2f}",
            "Güncel Fiyat (TL)": "{:.2f} ₺",
            "Güncel Değer (TL)": "{:,.2f} ₺",
            "Kar/Zarar (TL)": "{:,.2f} ₺",
            "Kar/Zarar (%)": "%{:.2f}"
        }))
        
        total_curr = res_df["Güncel Değer (TL)"].sum()
        total_cost = sum([h['total_invested_tl'] for h in holdings])
        total_profit = total_curr - total_cost
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Portföy Değeri", f"{total_curr:,.2f} ₺")
        m2.metric("Toplam Maliyet (TL)", f"{total_cost:,.2f} ₺")
        m3.metric("Toplam Kar/Zarar", f"{total_profit:,.2f} ₺", delta=f"{total_profit:,.2f} ₺")
    else:
        st.info("Henüz bir işleminiz bulunmuyor.")

    st.markdown("---")
    
    st.subheader("📜 İşlem Geçmişi")
    history = get_all_transactions()
    if not history.empty:
        st.dataframe(history.drop(columns=['id']), use_container_width=True)
    else:
        st.write("İşlem geçmişi bulunamadı.")

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
