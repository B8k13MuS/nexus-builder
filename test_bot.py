import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Проверяем оба возможных названия
token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

if not token:
    print("❌ Токен не найден! Проверьте .env файл")
    print("Должно быть: BOT_TOKEN=ваш_токен")
    exit(1)

print(f"Токен найден (длина: {len(token)} символов)")
print(f"Первые 10 символов: {token[:10]}...")
print(f"Последние 5 символов: ...{token[-5:]}")
print(f"Формат: {'цифры:буквы' if ':' in token else 'НЕПРАВИЛЬНЫЙ ФОРМАТ (должен содержать :)'}")

# Пробуем подключиться
url = f"https://api.telegram.org/bot{token}/getMe"
try:
    response = requests.get(url, timeout=10)
    result = response.json()
    
    if result.get('ok'):
        print("\n✅ ТОКЕН РАБОТАЕТ!")
        print(f"Бот: @{result['result']['username']}")
        print(f"ID: {result['result']['id']}")
    else:
        print(f"\n❌ ТОКЕН НЕ РАБОТАЕТ!")
        print(f"Ошибка: {result.get('description')}")
        print("\nВозможные причины:")
        print("1. Неправильно скопирован токен")
        print("2. Токен отозван в BotFather")
        print("3. В токене есть лишние символы (пробелы, кавычки)")
except Exception as e:
    print(f"\n❌ Ошибка подключения: {e}")
