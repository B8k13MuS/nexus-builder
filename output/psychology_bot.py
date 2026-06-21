import asyncio
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Каталог курсов", callback_data="catalog")],
            [InlineKeyboardButton(text="Связаться с менеджером", callback_data="contact")],
        ]
    )
    await message.answer("Здравствуйте! Я бот для продажи курсов по психологии.", reply_markup=kb)

@router.callback_query(F.data == "catalog")
async def proc_catalog(callback: CallbackQuery):
    await callback.message.edit_text("Заглушка для каталога курсов.")

@router.callback_query(F.data == "contact")
async def proc_contact(callback: CallbackQuery):
    await callback.message.edit_text("Для связи с менеджером напишите: example@domain.com.")

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())