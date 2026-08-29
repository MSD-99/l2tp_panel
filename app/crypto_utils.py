from cryptography.fernet import Fernet

from app.config import ENCRYPTION_KEY

_fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


def encrypt_str(plain: str) -> str:
    return _fernet.encrypt(plain.encode()).decode()


def decrypt_str(token: str) -> str:
    return _fernet.decrypt(token.encode()).decode()
