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
    conn.commit()
    conn.close()
    print(f"Veritabanı hazır: {DB_NAME}")

if __name__ == "__main__":
    init_db()
