import json
from pathlib import Path
from typing import Any, Dict
from core.tools.base import BaseTool


class ProjectBuilderTool(BaseTool):
    """Создаёт файловую структуру проекта из сгенерированных файлов."""

    @property
    def name(self) -> str:
        return "project_builder"

    @property
    def description(self) -> str:
        return (
            "Создаёт проект (Telegram-бот, сайт, сервис, скрипт) — записывает файлы "
            "в output/projects/<project_name>/. Принимает JSON со структурой файлов."
        )

    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Args:
            project_name: имя папки проекта (snake_case)
            files: dict {relative_path: content}
        """
        project_name = kwargs.get("project_name", "").strip()
        files = kwargs.get("files", {})

        if not project_name:
            return {"success": False, "error": "Не указан project_name", "result": None}
        if not files or not isinstance(files, dict):
            return {"success": False, "error": "files не указаны или неверный формат", "result": None}

        safe_name = "".join(c for c in project_name if c.isalnum() or c in "_-").lower() or "project"
        project_root = Path(__file__).resolve().parents[2]
        base_dir = (project_root / "output" / "projects" / safe_name).resolve()
        base_dir.mkdir(parents=True, exist_ok=True)

        created = []
        for rel_path, content in files.items():
            safe_rel = Path(rel_path)
            if safe_rel.is_absolute() or ".." in safe_rel.parts:
                continue
            full_path = (base_dir / safe_rel).resolve()
            if not str(full_path).startswith(str(base_dir)):
                continue
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(str(content), encoding="utf-8")
            created.append(str(safe_rel))

        if not created:
            return {"success": False, "error": "Ни один файл не создан", "result": None}

        return {
            "success": True,
            "result": (
                f"Проект '{safe_name}' создан в output/projects/{safe_name}/\n"
                f"Файлы: {', '.join(created)}"
            ),
            "error": None,
        }
