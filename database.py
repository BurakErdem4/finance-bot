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
    
    # Kullanıcılar Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password_hash BLOB NOT NULL,
            full_name TEXT,
            is_verified BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Veritabanı hazır: {DB_NAME}")

def add_user(email, password, full_name):
    """
    Registers a new user. Returns (success, message).
    """
    from auth_module import hash_password
    
    hashed = hash_password(password)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO users (email, password_hash, full_name, is_verified) VALUES (?, ?, ?, 0)", (email, hashed, full_name))
        conn.commit()
        conn.close()
        return True, "Kayıt başarılı! Giriş yapabilirsiniz."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Bu e-posta adresi zaten kayıtlı."
    except Exception as e:
        conn.close()
        return False, f"Hata: {e}"

def verify_user(email, password):
    """
    Verifies login credentials. Returns (user_obj, message).
    """
    from auth_module import check_password
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT email, password_hash, full_name FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        stored_email, stored_hash, stored_name = user
        if check_password(password, stored_hash):
            return {"email": stored_email, "name": stored_name}, "Giriş Başarılı"
    
    return None, "E-posta veya şifre hatalı."

if __name__ == "__main__":
    init_db()
