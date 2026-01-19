import sqlite3
import os

DB_NAME = "finance.db"

def init_db():
    """
    Veritabanını başlatır ve 'prices' tablosunu oluşturur.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Fiyatlar tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            symbol TEXT NOT NULL,
            price REAL NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            symbol TEXT NOT NULL,
            type TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL
        )
    ''')
    
    # Gölge Portföy (Paper Trading) Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            symbol TEXT NOT NULL,
            type TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            commission REAL DEFAULT 0,
            balance_after REAL
        )
    ''')
    
    # Paper Trading Ayarları/Bakiye
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paper_settings (
            key TEXT PRIMARY KEY,
            value REAL
        )
    ''')
    
    # İlk bakiye tanımlama (Eğer yoksa)
    cursor.execute("INSERT OR IGNORE INTO paper_settings (key, value) VALUES ('virtual_balance', 100000.0)")
    
    conn.commit()
    conn.close()
    print(f"Veritabanı hazır: {DB_NAME}")

if __name__ == "__main__":
    init_db()
