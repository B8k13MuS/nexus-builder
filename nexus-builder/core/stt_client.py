import subprocess
import json
import logging
import os
import uuid
from config import GROQ_API_KEY, GROQ_STT_URL

logger = logging.getLogger(__name__)


def transcribe_audio(file_path: str) -> str:
    """Отправляет локальный аудиофайл в Groq Whisper API."""
    if not os.path.exists(file_path):
        logger.error(f"Файл не найден: {file_path}")
        return "Ошибка: аудиофайл не найден."

    command = [
        "curl", "-k", "-s", "-X", "POST", GROQ_STT_URL,
        "-H", f"Authorization: Bearer {GROQ_API_KEY}",
        "-F", f"file=@{file_path}",
        "-F", "model=whisper-large-v3",
        "-F", "response_format=json",
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding="utf-8")
        response_data = json.loads(result.stdout)
        text = response_data.get("text", "").strip()
        if not text:
            logger.warning(f"Groq вернул пустой текст. Ответ: {response_data}")
            return "Я не смог разобрать, что вы сказали."
        logger.info(f"Распознанный текст: {text}")
        return text
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при вызове Groq API: {e.stderr}")
        return "Ошибка при распознавании речи."
    except json.JSONDecodeError:
        logger.error(f"Не удалось распарсить ответ от Groq: {result.stdout}")
        return "Ошибка обработки ответа распознавания."


class STTClient:
    """Класс-обертка для распознавания речи."""

    def transcribe(self, url_or_path: str) -> str:
        """
        Распознает речь из URL или локального файла.
        Если передан URL, скачивает файл во временную папку.
        """
        if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_audio")
            os.makedirs(temp_dir, exist_ok=True)
            # Уникальное имя файла во избежание гонки при параллельных запросах
            temp_file = os.path.join(temp_dir, f"voice_{uuid.uuid4().hex}.ogg")

            logger.info(f"Скачивание аудио из URL: {url_or_path[:50]}...")
            download_cmd = ["curl", "-k", "-s", "-L", "-o", temp_file, url_or_path]
            try:
                subprocess.run(download_cmd, check=True, capture_output=True)
                return transcribe_audio(temp_file)
            except subprocess.CalledProcessError as e:
                logger.error(f"Ошибка скачивания аудио: {e.stderr}")
                return "Ошибка скачивания аудиофайла."
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        else:
            return transcribe_audio(url_or_path)
