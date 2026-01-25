import bcrypt

def hash_password(password):
    """
    Hashes a plain text password using bcrypt.
    Returns the hashed password as bytes.
    """
    if isinstance(password, str):
        password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password, salt)

def check_password(plain_password, hashed_password):
    """
    Checks if a plain text password matches the hashed password.
    Returns True if valid, False otherwise.
    """
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')
    if isinstance(hashed_password, str):
        # Depending on how it's stored in DB (text/blob), might need encoding
        hashed_password = hashed_password.encode('utf-8')
        
    return bcrypt.checkpw(plain_password, hashed_password)
