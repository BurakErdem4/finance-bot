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

def get_app_secret(key):
    """
    Retrieves secret from os.environ (GitHub/Headless) or st.secrets (Streamlit).
    """
    # 1. Try Environment Variable (GitHub Actions / System)
    value = os.environ.get(key)
    if value:
        return value
        
    # 2. Try Streamlit Secrets
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

def fetch_newsletter_data():
    """
    Fetches data for all assets defined in key config.NEWSLETTER_ASSETS.
    """
    results = {}
    usd_rate = 1.0 # Default fallback
    
    # Pre-fetch USD for manual calculations if needed
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
                    # Parse dependencies (e.g., gold_ons * usd / 31.1)
                    # Simplified logic: We know it's Gram Gold or Silver
                    if "GOLD" in asset['symbol']:
                        base_sym = "GC=F"
                    else:
                        base_sym = "SI=F"
                        
                    base_hist = yf.Ticker(base_sym).history(period="3mo")
                    if not base_hist.empty:
                        # Re-calculate history in TRY
                        # Note: This is an approximation using current USD for full history 
                        # or we fetch USD history and multiply.
                        # For simplicity/speed, we fetch base asset changes and apply to calculated price.
                        base_metrics = calculate_changes(base_hist)
                        if base_metrics:
                            # Calculate Gram Price in TL
                            ons_price = base_metrics['price']
                            gram_price = (ons_price * usd_rate) / 31.10
                            
                            results[category].append({
                                "name": asset["name"],
                                "price": gram_price,
                                "daily": base_metrics['daily'], # % change is roughly same as Ons (ignoring USD fluctuation) or we can approximate
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
                print(f"Error fetching {asset['name']}: {e}")
                results[category].append({
                    "name": asset["name"], 
                    "price": 0, "daily": 0, "weekly": 0, "monthly": 0, "error": True
                })
                
    return results

def get_category_sentiment():
    """
    Fetches one representative news/sentiment for key categories.
    """
    # Representative symbols for categories
    mapping = {
        "Borsa": "XU100.IS",
        "Kripto": "BTC-USD",
        "Emtia": "GC=F"
    }
    
    sentiments = {}
    for cat, sym in mapping.items():
        sentiments[cat] = get_sentiment_score(sym)
        
    return sentiments

def generate_html(data, sentiments, report_type):
    report_date = datetime.now().strftime("%d.%m.%Y %H:%M")
    
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
    
    # Loop through categories
    for category, assets in data.items():
        html += f'<div class="section-title">{category}</div>'
        
        # Add Sentiment/News if available for this category
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
                
            # Formatting Colors
            d_cls = "val-pos" if asset['daily'] > 0 else "val-neg" if asset['daily'] < 0 else "val-neu"
            w_cls = "val-pos" if asset['weekly'] > 0 else "val-neg" if asset['weekly'] < 0 else "val-neu"
            m_cls = "val-pos" if asset['monthly'] > 0 else "val-neg" if asset['monthly'] < 0 else "val-neu"
            
            # Format Price
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
    If target_email is None, it sends to ALL subscribers in subscribers.json based on preferences.
    If target_email is provided, it sends only to that email (Manual / Test mode).
    
    report_type values: "Günlük", "Haftalık"
    """
    try:
        # 1. Fetch Market Data
        market_data = fetch_newsletter_data()
        
        # 2. Fetch Sentiments
        sentiments = get_category_sentiment()
        
        # 3. Generate HTML
        html_content = generate_html(market_data, sentiments, report_type)
        
        # 4. Message Construction
        sender_email = get_app_secret("GMAIL_USER")
        password = get_app_secret("GMAIL_PASSWORD")
        
        if not sender_email or not password:
             return False, "E-posta bilgileri (GMAIL_USER/GMAIL_PASSWORD) bulunamadı."
        
        report_date = datetime.now().strftime("%d-%m-%Y")
        
        # 5. Determine Recipients
        recipients = []
        
        if target_email:
            # Single manual Send
            recipients = [target_email]
        else:
            # Broadcast to subscribers
            all_subs = subscription_module.get_subscribers()
            
            # Filter based on Report Type
            # "Günlük" -> check s['daily']
            # "Haftalık" -> check s['weekly']
            
            for s in all_subs:
                email = s.get('email')
                if not email:
                    continue
                    
                should_send = False
                if report_type == "Günlük" and s.get('daily', False):
                    should_send = True
                elif report_type == "Haftalık" and s.get('weekly', False):
                    should_send = True
                # Fallback / manual logic could be added here
                
                if should_send:
                    recipients.append(email)
            
        if not recipients:
             return False, "Bu rapor tipi için gönderilecek abone bulunamadı."
             
        # 6. Send Loop
        sent_count = 0
        context = ssl.create_default_context()
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            
            for email in recipients:
                try:
                    message = MIMEMultipart("alternative")
                    message["Subject"] = f"Finans Bülteni ({report_type}) - {report_date}"
                    message["From"] = sender_email
                    message["To"] = email
                    
                    part = MIMEText(html_content, "html")
                    message.attach(part)
                    
                    server.sendmail(sender_email, email, message.as_string())
                    sent_count += 1
                    
                    # Spam protection delay
                    time.sleep(1) 
                except Exception as e:
                    print(f"Failed to send to {email}: {e}")
            
        return True, f"Bülten {sent_count} kişiye başarıyla gönderildi!"
        
    except Exception as e:
        return False, f"Hata oluştu: {str(e)}"
