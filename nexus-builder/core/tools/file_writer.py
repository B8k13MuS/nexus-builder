import os
from pathlib import Path
from typing import Any, Dict
from core.tools.base import BaseTool


class FileWriterTool(BaseTool):
    """Инструмент для записи текста в файл."""

    @property
    def name(self) -> str:
        return "file_writer"

    @property
    def description(self) -> str:
        return "Записывает текст в указанный файл. Используется для сохранения заметок, планов, результатов."

    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Args:
            file_path: имя файла (только имя, без пути) — сохраняется в output/
            content: текст для записи
            mode: 'w' — перезапись, 'a' — добавление (по умолчанию 'w')
        """
        file_path = kwargs.get("file_path")
        content = kwargs.get("content")
        mode = kwargs.get("mode", "w")

        if not file_path:
            return {"success": False, "error": "Не указан file_path", "result": None}
        if content is None:
            return {"success": False, "error": "Не указан content", "result": None}
        if mode not in ("w", "a"):
            return {"success": False, "error": f"Недопустимый режим: {mode}", "result": None}

        base_dir = Path(__file__).resolve().parents[2] / "output"
        base_dir.mkdir(exist_ok=True)

        # Защита от path traversal: берём только basename, резолвим и проверяем префикс
        safe_name = Path(file_path).name
        full_path = (base_dir / safe_name).resolve()
        if not str(full_path).startswith(str(base_dir.resolve())):
            return {"success": False, "error": "Недопустимый путь к файлу", "result": None}

        try:
            with open(full_path, mode, encoding="utf-8") as f:
                f.write(content)
            return {
                "success": True,
                "result": f"Файл сохранен: {full_path} ({len(content)} символов)",
                "error": None,
            }
        except OSError as e:
            return {"success": False, "error": str(e), "result": None}
