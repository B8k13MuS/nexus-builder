import os
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
        Записывает текст в файл.
        
        Args:
            file_path: путь к файлу (относительно ~/nexus-builder/output/)
            content: текст для записи
            mode: режим записи ('w' - перезапись, 'a' - добавление). По умолчанию 'w'.
        """
        file_path = kwargs.get("file_path")
        content = kwargs.get("content")
        mode = kwargs.get("mode", "w")
        
        if not file_path:
            return {"success": False, "error": "Не указан file_path", "result": None}
        if content is None:
            return {"success": False, "error": "Не указан content", "result": None}
        
        # Базовая папка проекта
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        full_path = os.path.join(base_dir, "output", file_path)
        
        # Создаем папку, если её нет
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        try:
            with open(full_path, mode, encoding="utf-8") as f:
                f.write(content)
            return {
                "success": True,
                "result": f"Файл сохранен: {full_path} ({len(content)} символов)",
                "error": None
            }
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}
