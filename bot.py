import asyncio
import logging
from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware, Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

from config import (
    TELEGRAM_TOKEN, OWNER_USER_ID, ALLOWED_USER_IDS,
    RATE_LIMIT_MAX, RATE_LIMIT_WINDOW, check_config,
)
from core.llm_client import LLMClient
from core.stt_client import STTClient
from core.state_machine import OrchestratorStateMachine
from core.security import SecurityGuard
from core.skill_manager import skill_manager
from core.logger import logger as db_logger

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

check_config()

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=None))
dp = Dispatcher()
llm = LLMClient()
stt = STTClient()
agent = OrchestratorStateMachine(llm)
guard = SecurityGuard(
    allowed_ids=ALLOWED_USER_IDS,
    owner_id=OWNER_USER_ID,
    max_requests=RATE_LIMIT_MAX,
    window_seconds=RATE_LIMIT_WINDOW,
)

# ──────────────────────────────────────────────
# Middleware безопасности
# ──────────────────────────────────────────────

class SecurityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.Message, dict], Awaitable[Any]],
        event: types.Message,
        data: dict,
    ) -> Any:
        user = event.from_user
        text = event.text or event.caption or ""
        allowed, reason = guard.check(user.id, user.username or "", text)

        if not allowed:
            if reason == "unauthorized":
                await event.answer("⛔ Нет доступа.")
                if OWNER_USER_ID:
                    await bot.send_message(
                        OWNER_USER_ID,
                        f"⚠️ Попытка доступа:\n"
                        f"Пользователь: @{user.username} (id={user.id})\n"
                        f"Текст: {text[:200] or '[голосовое]'}"
                    )
            elif reason == "rate_limit":
                await event.answer("⏳ Слишком много запросов. Подожди немного.")
            elif reason == "too_long":
                await event.answer("✂️ Слишком длинное сообщение (максимум 4000 символов).")
            elif reason == "injection":
                await event.answer("🚫 Запрос заблокирован системой безопасности.")
                if OWNER_USER_ID:
                    await bot.send_message(
                        OWNER_USER_ID,
                        f"🛡️ Заблокирована атака от @{user.username} (id={user.id}):\n{text[:200]}"
                    )
            return

        return await handler(event, data)


dp.message.middleware(SecurityMiddleware())

# ──────────────────────────────────────────────
# Команды
# ──────────────────────────────────────────────

_HELP = (
    "Nexus-Builder — ИИ-агент для создания сервисов.\n\n"
    "Примеры (голосом или текстом):\n"
    "• Создай телеграм-бота для напоминаний\n"
    "• Сделай сайт-визитку на Flask\n"
    "• Напиши скрипт для парсинга цен\n"
    "• Найди информацию о Python asyncio\n"
    "• Посчитай 2**32\n"
    "• Сохрани заметку: завтра встреча в 10\n\n"
    "Команды:\n"
    "/skills — навыки агента\n"
    "/status — статистика\n"
    "/security — безопасность (только владелец)"
)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(_HELP)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(_HELP)


@dp.message(Command("skills"))
async def cmd_skills(message: types.Message):
    await message.answer(f"Навыки агента:\n\n{skill_manager.list_skills()}")


@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    stats = db_logger.get_stats()
    if stats:
        total, avg_iter, avg_dur, total_cost = stats
        text = (
            f"Статистика:\n"
            f"Запросов: {total}\n"
            f"Среднее итераций: {avg_iter:.1f}\n"
            f"Среднее время: {avg_dur:.1f}с\n"
            f"Потрачено: {total_cost:.4f}₽\n"
            f"Навыков: {len(skill_manager.skills)}"
        )
    else:
        text = "Данных пока нет."
    await message.answer(text)


@dp.message(Command("security"))
async def cmd_security(message: types.Message):
    if not guard.is_owner(message.from_user.id):
        await message.answer("⛔ Только для владельца.")
        return
    stats = guard.get_stats()
    recent = guard.recent_blocked(5)
    lines = [
        f"🛡️ Безопасность:",
        f"Заблокировано попыток: {stats['total_blocked']}",
        f"Выученных паттернов: {stats['learned_patterns']}",
        f"Разрешённых ID: {stats['allowed_ids_count']}",
    ]
    if recent:
        lines.append("\nПоследние блокировки:")
        for e in recent:
            lines.append(f"  uid={e['user_id']} @{e['username']}: {e['reason']}")
    await message.answer("\n".join(lines))


# ──────────────────────────────────────────────
# Обработчики сообщений
# ──────────────────────────────────────────────

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    await bot.send_chat_action(message.chat.id, "typing")
    file = await bot.get_file(message.voice.file_id)
    file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file.file_path}"

    text = await asyncio.to_thread(stt.transcribe, file_url)
    if "ошибка" in text.lower():
        await message.answer(text)
        return

    await message.answer(f"Понял: {text}")
    await bot.send_chat_action(message.chat.id, "typing")
    await _process_and_reply(message, text)


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: types.Message):
    await bot.send_chat_action(message.chat.id, "typing")
    await _process_and_reply(message, message.text)


async def _process_and_reply(message: types.Message, text: str):
    try:
        response = await asyncio.to_thread(agent.run, text)
    except Exception as e:
        logging.error(f"Agent error: {e}")
        response = f"Ошибка агента: {e}"

    for i in range(0, max(len(response), 1), 4096):
        await message.answer(response[i:i + 4096])


async def main():
    logging.info("Nexus-Builder запущен.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
