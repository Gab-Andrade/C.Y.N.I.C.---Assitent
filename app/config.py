from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"

CREDENTIALS_DIR = APP_DIR / "credentials"
TOKENS_DIR = APP_DIR / "tokens"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"
TOKEN_FILE = TOKENS_DIR / "token.json"
STORAGE_DIR = APP_DIR / "storage"
MEMORIA_DIR = STORAGE_DIR / "memoria_cynic"
AUDIOS_DIR = STORAGE_DIR / "audios"
LOGS_DIR = STORAGE_DIR / "logs"
STATIC_DIR = APP_DIR / "static"
