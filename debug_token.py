import os
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Проверяем разные варианты названий переменных
bot_token = os.getenv("BOT_TOKEN")
telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

print("=== ПРОВЕРКА ТОКЕНА ===")
print(f"BOT_TOKEN: {'SET' if bot_token else 'NOT SET'} - {bot_token[:15] if bot_token else 'None'}...")
print(f"TELEGRAM_BOT_TOKEN: {'SET' if telegram_bot_token else 'NOT SET'} - {telegram_bot_token[:15] if telegram_bot_token else 'None'}...")
print(f"\nВсе переменные окружения:")
for key, value in os.environ.items():
    if 'TOKEN' in key:
        print(f"  {key}: {value[:15]}..." if value else f"  {key}: {value}")
