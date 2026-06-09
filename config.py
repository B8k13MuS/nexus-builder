"""Конфигурация Nexus-Builder"""
import os

# ==========================================
# Настройки для Polza.ai (LLM)
# ==========================================
POLZA_API_URL = os.getenv("POLZA_API_URL", "https://api.polza.ai/v1/chat/completions")
POLZA_API_KEY = os.getenv("POLZA_API_KEY", "ТВОЙ_POLZA_API_KEY")
POLZA_MODEL = os.getenv("POLZA_MODEL", "openai/gpt-4.1-nano")

# ==========================================
# Настройки для Groq Whisper (STT - распознавание речи)
# ==========================================
# Получи бесплатный ключ здесь: https://console.groq.com/keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "ТВОЙ_GROQ_API_KEY")
GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# ==========================================
# Настройки для Telegram
# ==========================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "ТВОЙ_TELEGRAM_TOKEN")
# Дополнительные настройки для LLM (требуются llm_client.py)
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1000"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
TIMEOUT = int(os.getenv("TIMEOUT", "30"))
