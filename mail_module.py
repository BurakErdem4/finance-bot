import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
import yfinance as yf
import borsapy as bp
import pandas as pd
from datetime import datetime

def send_daily_report(target_email, report_type="Günlük"):
    """
    Sends a financial summary report via email using Gmail SMTP.
    Credentials must be in st.secrets['GMAIL_USER'] and st.secrets['GMAIL_PASSWORD'].
    """
    try:
        # 1. Fetch Data
        usd = yf.Ticker("TRY=X").history(period="1d")['Close'].iloc[-1]
        gold = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        
        try:
            xu030 = bp.Index("XU030")
            bist30 = xu030.info.get('last', "---")
        except:
            bist30 = "Veri alınamadı"
            
        report_date = datetime.now().strftime("%d-%m-%Y %H:%M")
        
        # 2. Get Credentials
        sender_email = st.secrets["GMAIL_USER"]
        password = st.secrets["GMAIL_PASSWORD"]
        
        # 3. Create HTML Template
        subject = "Haftalık Finans Özeti" if report_type == "Haftalık" else "Günlük Finans Raporu"
        title = "📅 Haftalık Finans Özeti" if report_type == "Haftalık" else "📉 Günlük Finans Raporu"
        
        message = MIMEMultipart("alternative")
        message["Subject"] = f"{subject} - {report_date}"
        message["From"] = sender_email
        message["To"] = target_email
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
            <div style="background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
                <h1 style="color: #333;">{title}</h1>
                <p style="color: #666;">Tarih: {report_date}</p>
                <hr style="border: 0; border-top: 1px solid #eee;">
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                    <tr style="background-color: #f8f8f8;">
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Varlık</th>
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Fiyat</th>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">USD/TRY</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{usd:.2f} ₺</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">Altın (Ons)</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{gold:.2f} $</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">BIST 30</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{bist30}</td>
                    </tr>
                </table>
                <p style="margin-top: 30px; font-size: 12px; color: #999;">Bu {report_type.lower()} rapor Finans Botu tarafından otomatik olarak oluşturulmuştur.</p>
            </div>
        </body>
        </html>
        """
        
        part = MIMEText(html, "html")
        message.attach(part)
        
        # 4. Send Email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, target_email, message.as_string())
            
        return True, "Rapor başarıyla gönderildi!"
        
    except Exception as e:
        return False, f"Hata oluştu: {str(e)}"
