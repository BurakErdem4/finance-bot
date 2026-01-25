import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import config
from sentiment_module import get_sentiment_score
import os
import time
import subscription_module
import pytz

# Import Portfolio Manager for Personal Data
from portfolio_manager import get_portfolio_balance, get_portfolio_history

def get_app_secret(key):
    """
    Retrieves secret from os.environ (GitHub/Headless) or st.secrets (Streamlit).
    """
    value = os.environ.get(key)
    if value:
        return value
    try:
        return st.secrets[key]
    except (FileNotFoundError, KeyError):
        return None

def calculate_changes(history):
    """
    Calculates Daily, Weekly, and Monthly percentage changes.
    """
    if history.empty:
        return None
        
    current_price = history['Close'].iloc[-1]
    
    # helper for pct change
    def get_pct(prev_price):
        return ((current_price - prev_price) / prev_price) * 100

    # Daily (1 day ago)
    daily_change = 0.0
    if len(history) >= 2:
        daily_change = get_pct(history['Close'].iloc[-2])

    # Weekly (approx 5 trading days)
    weekly_change = 0.0
    if len(history) >= 5:
        weekly_change = get_pct(history['Close'].iloc[-5])
        
    # Monthly (approx 21 trading days)
    monthly_change = 0.0
    if len(history) >= 21:
        monthly_change = get_pct(history['Close'].iloc[-21])
        
    return {
        "price": current_price,
        "daily": daily_change,
        "weekly": weekly_change,
        "monthly": monthly_change
    }

def calculate_user_portfolio_performance(user_email):
    """
    Fetches user portfolio and calculates performance metrics.
    Returns dict or None.
    """
    if not user_email: 
        return None
        
    # 1. Get Holdings
    holdings = get_portfolio_balance(user_email)
    if not holdings:
        return None
        
    total_value_tl = sum([h['total_value_tl'] for h in holdings])
    
    # 2. Get History (for trends)
    # We need at least 1 month of history for metrics
    hist_series = get_portfolio_history(holdings, period='2mo')
    
    if hist_series.empty:
        return {
            "total_tl": total_value_tl,
            "daily": 0, "weekly": 0, "monthly": 0
        }
    
    # Calculate Changes on total portfolio value
    # Re-construct as DataFrame with 'Close' column to reuse calculate_changes
    hist_df = pd.DataFrame({'Close': hist_series})
    metrics = calculate_changes(hist_df)
    
    if metrics:
         return {
            "total_tl": total_value_tl,
            "daily": metrics['daily'],
            "weekly": metrics['weekly'],
            "monthly": metrics['monthly']
        }
    return None

def fetch_newsletter_data():
    """
    Fetches data for all assets defined in key config.NEWSLETTER_ASSETS.
    """
    results = {}
    usd_rate = 35.0 # Default fallback
    
    try:
        usd_hist = yf.Ticker("TRY=X").history(period="1mo")
        if not usd_hist.empty:
            usd_rate = usd_hist['Close'].iloc[-1]
    except:
        pass

    for category, assets in config.NEWSLETTER_ASSETS.items():
        results[category] = []
        for asset in assets:
            try:
                # 1. Manual/Representation
                if asset.get("manual"):
                    results[category].append({
                        "name": asset["name"],
                        "price": asset["value"],
                        "daily": 0, "weekly": 0, "monthly": 0,
                        "is_manual": True
                    })
                    continue

                # 2. Calculated Assets (Gram Gold/Silver)
                if asset.get("calc"):
                    if "GOLD" in asset['symbol']: base_sym = "GC=F"
                    else: base_sym = "SI=F"
                        
                    base_hist = yf.Ticker(base_sym).history(period="3mo")
                    if not base_hist.empty:
                        base_metrics = calculate_changes(base_hist)
                        if base_metrics:
                            ons_price = base_metrics['price']
                            gram_price = (ons_price * usd_rate) / 31.10
                            
                            results[category].append({
                                "name": asset["name"],
                                "price": gram_price,
                                "daily": base_metrics['daily'],
                                "weekly": base_metrics['weekly'],
                                "monthly": base_metrics['monthly']
                            })
                    continue

                # 3. Standard Assets
                symbol = asset["symbol"]
                hist = yf.Ticker(symbol).history(period="3mo")
                metrics = calculate_changes(hist)
                
                if metrics:
                    results[category].append({
                        "name": asset["name"],
                        "price": metrics["price"],
                        "daily": metrics["daily"],
                        "weekly": metrics["weekly"],
                        "monthly": metrics["monthly"]
                    })
                else:
                    results[category].append({
                        "name": asset["name"], 
                        "price": 0, "daily": 0, "weekly": 0, "monthly": 0, "error": True
                    })
                    
            except Exception as e:
                # print(f"Error fetching {asset['name']}: {e}")
                results[category].append({
                    "name": asset["name"], 
                    "price": 0, "daily": 0, "weekly": 0, "monthly": 0, "error": True
                })
                
    return results

def get_category_sentiment():
    """
    Fetches one representative news/sentiment for key categories.
    """
    mapping = {
        "Borsa": "XU100.IS",
        "Kripto": "BTC-USD",
        "Emtia": "GC=F"
    }
    
    sentiments = {}
    for cat, sym in mapping.items():
        sentiments[cat] = get_sentiment_score(sym)
        
    return sentiments

def generate_html(data, sentiments, report_type, user_portfolio=None):
    tz = pytz.timezone('Europe/Istanbul')
    report_date = datetime.now(tz).strftime("%d.%m.%Y %H:%M")
    
    # CSS Styles
    style = """
    <style>
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header { background-color: #1a1a1a; color: #ffffff; padding: 20px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; font-weight: 300; }
        .header p { margin: 5px 0 0; font-size: 12px; color: #888; }
        .section { padding: 20px; }
        .section-title { font-size: 16px; font-weight: bold; color: #333; margin-bottom: 10px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px; }
        th { text-align: left; padding: 8px; background-color: #f9f9f9; color: #666; font-size: 12px; }
        td { padding: 8px; border-bottom: 1px solid #eee; }
        .val-pos { color: #2e7d32; font-weight: bold; }
        .val-neg { color: #c62828; font-weight: bold; }
        .val-neu { color: #666; }
        .news-box { background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 4px solid #333; margin-bottom: 15px; }
        .news-title { font-size: 13px; font-weight: bold; color: #333; display: block; margin-bottom: 4px;}
        .news-meta { font-size: 11px; color: #666; }
        .sentiment-badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; color: white; margin-left: 5px; }
        .bg-pos { background-color: #2e7d32; }
        .bg-neg { background-color: #c62828; }
        .bg-neu { background-color: #666; }
        .footer { background-color: #eee; padding: 15px; text-align: center; font-size: 11px; color: #888; }
        .portfolio-box { background-color: #e3f2fd; border-radius: 8px; padding: 15px; margin-bottom: 20px; border: 1px solid #bbdefb; }
    </style>
    """
    
    html = f"""
    <html>
    <head>{style}</head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Finans Bülteni</h1>
                <p>{report_type} • {report_date}</p>
            </div>
            
            <div class="section">
    """
    
    # --- USER PORTFOLIO SECTION ---
    if user_portfolio:
        u = user_portfolio
        
        # Color classes
        d_cls = "val-pos" if u['daily'] > 0 else "val-neg" if u['daily'] < 0 else "val-neu"
        w_cls = "val-pos" if u['weekly'] > 0 else "val-neg" if u['weekly'] < 0 else "val-neu"
        m_cls = "val-pos" if u['monthly'] > 0 else "val-neg" if u['monthly'] < 0 else "val-neu"
        
        html += f"""
        <div class="section-title">💼 Senin Portföyün</div>
        <div class="portfolio-box">
            <table style="margin-bottom:0;">
                <tr>
                    <th width="40%">Toplam Varlık (TL)</th>
                    <th width="20%">Gün</th>
                    <th width="20%">Hafta</th>
                    <th width="20%">Ay</th>
                </tr>
                <tr>
                    <td style="font-size:18px; font-weight:bold;">₺{u['total_tl']:,.2f}</td>
                    <td class="{d_cls}">%{u['daily']:.2f}</td>
                    <td class="{w_cls}">%{u['weekly']:.2f}</td>
                    <td class="{m_cls}">%{u['monthly']:.2f}</td>
                </tr>
            </table>
        </div>
        """
    
    # Loop through categories
    for category, assets in data.items():
        html += f'<div class="section-title">{category}</div>'
        
        # Add Sentiment/News
        if category in sentiments:
            s = sentiments[category]
            s_color = "bg-pos" if s['label'] == "POZİTİF" else "bg-neg" if s['label'] == "NEGATİF" else "bg-neu"
            
            html += f"""
            <div class="news-box" style="border-left-color: {'#2e7d32' if s['label'] == 'POZİTİF' else '#c62828' if s['label'] == 'NEGATİF' else '#666'};">
                <span class="news-title">{s['title']}</span>
                <span class="news-meta">
                    Yapay Zeka Yorumu: <span class="sentiment-badge {s_color}">{s['label']}</span>
                </span>
            </div>
            """
        
        # Table
        html += """
        <table>
            <tr>
                <th width="30%">Varlık</th>
                <th width="25%">Fiyat</th>
                <th width="15%">Gün</th>
                <th width="15%">Hafta</th>
                <th width="15%">Ay</th>
            </tr>
        """
        
        for asset in assets:
            if asset.get('is_manual'):
                html += f"""
                <tr>
                    <td>{asset['name']}</td>
                    <td>%{asset['price']}</td>
                    <td colspan="3" style="text-align:center; color:#999;">Yıllık Getiri</td>
                </tr>
                """
                continue
                
            d_cls = "val-pos" if asset['daily'] > 0 else "val-neg" if asset['daily'] < 0 else "val-neu"
            w_cls = "val-pos" if asset['weekly'] > 0 else "val-neg" if asset['weekly'] < 0 else "val-neu"
            m_cls = "val-pos" if asset['monthly'] > 0 else "val-neg" if asset['monthly'] < 0 else "val-neu"
            
            price_str = f"{asset['price']:,.2f}"
            if "USD" in asset['name'] or "EUR" in asset['name']: price_str += " ₺"
            elif "Altın" in asset['name'] or "Gümüş" in asset['name']: 
                if "Gram" in asset['name']: price_str += " ₺"
                else: price_str = f"${asset['price']:,.2f}"
            elif "Bitcoin" in asset['name'] or "Ethereum" in asset['name']: price_str = f"${asset['price']:,.0f}"
            else: price_str = f"{asset['price']:,.0f}"

            html += f"""
            <tr>
                <td>{asset['name']}</td>
                <td>{price_str}</td>
                <td class="{d_cls}">%{asset['daily']:.2f}</td>
                <td class="{w_cls}">%{asset['weekly']:.2f}</td>
                <td class="{m_cls}">%{asset['monthly']:.2f}</td>
            </tr>
            """
            
        html += "</table>"
        
    html += """
            </div>
            <div class="footer">
                <p>Bu rapor otomatik olarak oluşturulmuştur. Yatırım tavsiyesi değildir.</p>
                <p>Finans Asistanı v2.0</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def send_newsletter(target_email=None, report_type="Günlük"):
    """
    Main function to fetch data, generate HTML and send email.
    Updated to support personalized portfolios.
    """
    try:
        # 1. Fetch Shared Market Data (Assume same for all)
        market_data = fetch_newsletter_data()
        sentiments = get_category_sentiment()
        
        sender_email = get_app_secret("GMAIL_USER")
        password = get_app_secret("GMAIL_PASSWORD")
        
        if not sender_email or not password:
             return False, "E-posta bilgileri (GMAIL_USER/GMAIL_PASSWORD) bulunamadı."
        
        tz = pytz.timezone('Europe/Istanbul')
        report_date = datetime.now(tz).strftime("%d-%m-%Y")
        
        # 5. Determine Recipients
        recipients = []
        
        if target_email:
            recipients = [target_email]
        else:
            all_subs = subscription_module.get_subscribers()
            for s in all_subs:
                email = s.get('email')
                if not email: continue
                
                should_send = False
                if report_type == "Günlük" and s.get('daily', False): should_send = True
                elif report_type == "Haftalık" and s.get('weekly', False): should_send = True
                
                if should_send: recipients.append(email)
            
        if not recipients:
             return False, "Bu rapor tipi için gönderilecek abone bulunamadı."
             
        # 6. Send Loop (Personalized)
        sent_count = 0
        context = ssl.create_default_context()
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            
            for email in recipients:
                try:
                    # Calculate Personal Data
                    user_portfolio = calculate_user_portfolio_performance(email)
                    
                    # Generate Unique HTML
                    html_content = generate_html(market_data, sentiments, report_type, user_portfolio)
                    
                    message = MIMEMultipart("alternative")
                    subj_prefix = "📈 Finans Bülteni"
                    if user_portfolio:
                         subj_prefix = "💼 Kişisel Portföy Raporu & Finans Bülteni"
                         
                    message["Subject"] = f"{subj_prefix} ({report_type}) - {report_date}"
                    message["From"] = sender_email
                    message["To"] = email
                    
                    part = MIMEText(html_content, "html")
                    message.attach(part)
                    
                    server.sendmail(sender_email, email, message.as_string())
                    sent_count += 1
                    
                    time.sleep(1) 
                except Exception as e:
                    print(f"Failed to send to {email}: {e}")
            
        return True, f"Bülten {sent_count} kişiye başarıyla gönderildi!"
        
    except Exception as e:
        return False, f"Hata oluştu: {str(e)}"
