#!/usr/bin/env python3
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import check_config, OUTPUT_DIR
from core.llm_client import LLMClient

def generate_bot_code(description: str) -> str:
    prompt = """Ты эксперт по aiogram 3.x. Используй ТОЛЬКО aiogram 3.x синтаксис (Router, @router.message, @router.callback_query). Не используй callback_query_handler.
    Пример структуры:
    import asyncio
    from aiogram import Bot, Dispatcher, Router, F
    from aiogram.filters import Command
    from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    router = Router()

    @router.message(Command("start"))
    async def cmd_start(message: Message):
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Каталог", callback_data="catalog")]])
        await message.answer("Привет! Я бот для курсов психологии.", reply_markup=kb)

    @router.callback_query(F.data == "catalog")
    async def proc_cat(callback: CallbackQuery):
        await callback.message.edit_text("Наш каталог курсов...")

    async def main():
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()
        dp.include_router(router)
        print("Бот запущен!")
        await dp.start_polling(bot)

    if __name__ == "__main__":
        asyncio.run(main())
    Выводи ТОЛЬКО код Python, без лишних слов."""

    client = LLMClient()
    result = client.ask(f"Создай бота: {description}", system_prompt=prompt)
    
    # Распаковываем кортеж (content, cost)
    if isinstance(result, tuple):
        resp, cost = result
    else:
        resp = result
    
    # Проверяем, нет ли ошибки
    if resp.startswith("Error:"):
        print(f"❌ Ошибка LLM: {resp}")
        return None
    
    # Очищаем код от markdown-обёртки
    resp = re.sub(r'^```python\s*', '', resp, flags=re.MULTILINE)
    resp = re.sub(r'\s*```$', '', resp, flags=re.MULTILINE)
    return resp.strip()

def save_code(filename: str, code: str):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(code)
    print(f"💾 Сохранено в: {path}")

def main():
    print("🚀 Запуск Nexus-Builder...")
    check_config()
    desc = """Бот для продажи курсов по психологии.
    1. /start с приветствием и кнопками.
    2. Кнопка "Каталог курсов" (заглушка).
    3. Кнопка "Связаться с менеджером".
    Используй InlineKeyboardMarkup."""
    print(f"📝 Задача:\n{desc}\n" + "-"*40)
    code = generate_bot_code(desc)
    if code and not code.startswith("Error"):
        save_code("psychology_bot.py", code)
        print("\n✅ Готово! Бот сгенерирован.")
    else:
        print(f"\n❌ Ошибка: {code}")

if __name__ == "__main__":
    main()
