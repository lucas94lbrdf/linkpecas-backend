import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv, set_key

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

# Obtém a chave de criptografia do .env. Se não existir, cria e salva no .env.
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    if os.path.exists(env_path):
        set_key(env_path, "ENCRYPTION_KEY", ENCRYPTION_KEY)
    else:
        # Fallback se não encontrar o .env (durante build por exemplo)
        os.environ["ENCRYPTION_KEY"] = ENCRYPTION_KEY

cipher = Fernet(ENCRYPTION_KEY.encode())

def encrypt(text: str) -> str:
    if not text:
        return text
    return cipher.encrypt(text.encode()).decode()

def decrypt(encrypted_text: str) -> str:
    if not encrypted_text:
        return encrypted_text
    try:
        return cipher.decrypt(encrypted_text.encode()).decode()
    except Exception:
        # Em caso de falha (ex: já estava decriptado ou mudou a chave)
        return encrypted_text
