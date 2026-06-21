"""Конфигурация Nexus-Builder"""
import os
from pathlib import Path

# Загружаем переменные из .env файла
from dotenv import load_dotenv
load_dotenv()

# ==========================================
# Настройки для Polza.ai (LLM)
# ==========================================
POLZA_API_URL = os.getenv("POLZA_API_URL", "https://api.polza.ai/v1/chat/completions")
POLZA_API_KEY = os.getenv("POLZA_API_KEY", "")
POLZA_MODEL = os.getenv("POLZA_MODEL", "openai/gpt-4.1-nano")

# ==========================================
# Настройки для Groq Whisper (STT - распознавание речи)
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# ==========================================
# Настройки для Telegram
# ==========================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# ==========================================
# Дополнительные настройки для LLM
# ==========================================
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1000"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
TIMEOUT = int(os.getenv("TIMEOUT", "30"))

# ==========================================
# Пути и директории
# ==========================================
OUTPUT_DIR = "output"

# ==========================================
# Безопасность
# ==========================================
_allowed_raw = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS: set[int] = {int(x) for x in _allowed_raw.split(",") if x.strip().isdigit()}
OWNER_USER_ID: int = int(os.getenv("OWNER_USER_ID", "0"))
RATE_LIMIT_MAX: int = int(os.getenv("RATE_LIMIT_MAX", "10"))
RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "300"))


def check_config():
    """Проверяет наличие всех необходимых переменных окружения."""
    missing = []
    if not TELEGRAM_TOKEN:
        missing.append("TELEGRAM_TOKEN")
    if not POLZA_API_KEY:
        missing.append("POLZA_API_KEY")
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")

    if missing:
        raise ValueError(
            f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}\n"
            f"Проверьте файл .env"
        )

    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    Path("skills").mkdir(exist_ok=True)

    if not OWNER_USER_ID:
        print("⚠️  OWNER_USER_ID не задан — уведомления об атаках отключены")
    if not ALLOWED_USER_IDS:
        print("⚠️  ALLOWED_USER_IDS не задан — бот доступен всем")

    print("✅ Конфигурация проверена успешно")
    return True
