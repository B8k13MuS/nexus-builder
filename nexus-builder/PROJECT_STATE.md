# Nexus-Builder: Состояние проекта

## ✅ Что уже сделано

### Базовая инфраструктура
- Ubuntu WSL2 установлена и работает.
- Polza.ai API подключен и протестирован (модель: openai/gpt-4.1-nano).
- Написан рабочий клиент LLMClient (core/llm_client.py), который использует subprocess + curl с флагом -k для обхода проблемы SSL в WSL2.
- Установлен и протестирован aiogram 3.28.2.
- Успешно сгенерирован и запущен первый Telegram-бот (output/psychology_bot.py).
- FFmpeg установлен для работы с аудио.

### 🎤 Голосовой бот (Шаг 1 завершен)
- Создан core/stt_client.py - клиент для распознавания речи через Groq Whisper API.
- Создан output/voice_bot.py - голосовой бот, который принимает голосовые сообщения, транскрибирует их и передает текст в LLM.
- Все API ключи сохранены в ~/.bashrc (POLZA_API_KEY, GROQ_API_KEY, TELEGRAM_TOKEN).

### ⚙️ State Machine (Шаг 2 завершен)
- Создан core/state_machine.py - ядро "Orchestrator State Machine".
- Реализован циклический граф состояний (React Loop): Анализ → Маршрутизация → Выполнение → Критика → Завершение.
- Используется типизированный словарь состояния (AgentState) для управления контекстом.
- Реализована защита от бесконечного цикла (max_iterations=3).
- output/voice_bot.py успешно интегрирован с Orchestrator State Machine.

### 🔧 Система инструментов (Шаг 3 завершен)
- Создан базовый интерфейс для инструментов (core/tools/base.py).
- Реализован первый инструмент FileWriterTool (core/tools/file_writer.py) для записи текста в файлы.
- Создан реестр инструментов (core/tools/registry.py) для управления и вызова инструментов.
- Обновлен core/state_machine.py для поддержки инструментов.

### 🌐 Расширенные инструменты (Шаг 4 завершен)
- Создан инструмент WebSearchTool (core/tools/web_search.py) для поиска в интернете через DuckDuckGo API.
- Создан инструмент CodeExecutorTool (core/tools/code_executor.py) для выполнения Python-кода.
- Обновлен core/tools/registry.py для регистрации всех трёх инструментов.
- Обновлен core/state_machine.py:
  - Метод _route определяет маршрут по ключевым словам (порядок важен):
    - web_search: "найди", "поиск", "интернет", "кто такой", "что такое"
    - file_writer: "сохрани", "файл", "запиши"
    - code_executor: "выполни", "код", "посчитай"
  - Метод _execute динамически формирует аргументы для выбранного инструмента через LLM:
    - web_search: формирует точный поисковый запрос на английском (2-4 слова)
    - code_executor: генерирует Python-код и убирает markdown обёртку
    - file_writer: генерирует контент для сохранения
- Протестировано:
  - file_writer: бот сохраняет файлы по голосовой команде
  - code_executor: бот выполняет Python-код и возвращает результат
  - web_search: бот ищет информацию в интернете

## 📁 Структура проекта
~/nexus-builder/
├── config.py              # API URL, ключи, модель, настройки LLM
├── core/
│   ├── __init__.py
│   ├── llm_client.py      # Клиент для Polza.ai (через curl)
│   ├── stt_client.py      # Клиент для Groq Whisper STT (через curl)
│   ├── state_machine.py   # Ядро Orchestrator State Machine (React Loop)
│   └── tools/
│       ├── __init__.py
│       ├── base.py        # Базовый интерфейс инструментов
│       ├── file_writer.py # Инструмент записи в файл
│       ├── web_search.py  # Инструмент поиска в интернете
│       ├── code_executor.py # Инструмент выполнения Python-кода
│       └── registry.py    # Реестр инструментов
├── nexus_agent.py         # Скрипт-генератор ботов
├── output/
│   ├── psychology_bot.py  # Первый сгенерированный бот (текст)
│   ├── voice_bot.py       # Голосовой бот с интегрированным Orchestrator
│   └── agent_result.txt   # Файл, созданный агентом
├── agents/                # (будет использоваться для суб-агентов)
├── temp_audio/            # Временная папка для аудиофайлов
└── logs/                  # для логов

## 🎯 Главная цель
Создать голосового Telegram-агента с ядром "Orchestrator State Machine", который самостоятельно выполняет действия по созданию сервисов/инструментов по инструкции и отвечает кратко текстом, только по сути.

### 🏗️ Новые инструменты и главный бот (Шаг 5 завершен)
- Создан ProjectBuilderTool (core/tools/project_builder.py) — генерирует проект целиком в output/projects/<name>/
- Создан ShellExecutorTool (core/tools/shell_executor.py) — выполняет pip install и другие shell-команды (whitelist)
- Исправлен баг в FileWriterTool: parents[3] → parents[2] (файлы писались в /home/user/ вместо проекта)
- LLMClient.ask() поддерживает max_tokens override (для генерации проектов нужно 3000 токенов)
- state_machine.py полностью переписан: routing для всех 5 инструментов, автоустановка зависимостей после project_builder
- Создан bot.py — главный Telegram-бот с поддержкой голоса И текстовых сообщений

## 📁 Структура проекта (актуальная)
~/nexus-builder/
├── bot.py                 # Главный Telegram-бот (голос + текст → state_machine)
├── nexus_agent.py         # Скрипт-генератор ботов (устаревший, оставлен)
├── config.py
├── core/
│   ├── llm_client.py      # max_tokens override добавлен
│   ├── stt_client.py
│   ├── state_machine.py   # 5 инструментов + _is_build_request routing
│   ├── logger.py
│   └── tools/
│       ├── base.py
│       ├── file_writer.py  # BUG FIXED: parents[2]
│       ├── web_search.py
│       ├── code_executor.py
│       ├── project_builder.py  # NEW
│       ├── shell_executor.py   # NEW
│       └── registry.py
├── output/
│   └── projects/          # Сгенерированные проекты
└── logs/

## 🚀 Следующий шаг (Шаг 6)
- Запустить bot.py и протестировать создание бота голосовой командой
- Возможно улучшить модель: gpt-4.1-nano может не осилить JSON с кодом за 3000 токенов
- Добавить /status команду в бот (показывает статистику из БД)
