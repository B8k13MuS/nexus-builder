import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict
from core.tools.base import BaseTool

_ALLOWED = {"pip", "pip3", "python", "python3", "npm", "node", "ls", "cat", "echo"}


class ShellExecutorTool(BaseTool):
    """Выполняет shell-команды для настройки и запуска проектов."""

    @property
    def name(self) -> str:
        return "shell_executor"

    @property
    def description(self) -> str:
        return (
            "Выполняет shell-команды: pip install, запуск Python-скриптов, проверка файлов. "
            "Используется для настройки созданных проектов."
        )

    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Args:
            command: команда для выполнения
            working_dir: имя проекта в output/projects/ (опционально)
        """
        command = kwargs.get("command", "").strip()
        working_dir = kwargs.get("working_dir", "")

        if not command:
            return {"success": False, "error": "Не указана команда", "result": None}

        try:
            parts = shlex.split(command)
        except ValueError as e:
            return {"success": False, "error": f"Ошибка разбора команды: {e}", "result": None}

        base_cmd = os.path.basename(parts[0]) if parts else ""
        if base_cmd not in _ALLOWED:
            return {
                "success": False,
                "error": f"'{base_cmd}' не разрешена. Разрешены: {', '.join(sorted(_ALLOWED))}",
                "result": None,
            }

        project_root = Path(__file__).resolve().parents[2]
        venv_bin = project_root / "venv" / "bin"

        # Используем pip/python из venv
        if base_cmd in ("pip", "pip3"):
            parts[0] = str(venv_bin / "pip") if (venv_bin / "pip").exists() else "pip3"
        elif base_cmd in ("python", "python3"):
            parts[0] = str(venv_bin / "python") if (venv_bin / "python").exists() else "python3"

        if working_dir:
            cwd = (project_root / "output" / "projects" / working_dir).resolve()
            if not str(cwd).startswith(str((project_root / "output").resolve())):
                return {"success": False, "error": "Недопустимый рабочий каталог", "result": None}
            if not cwd.exists():
                cwd = project_root
        else:
            cwd = project_root

        try:
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(cwd),
                encoding="utf-8",
            )
            output = (result.stdout + result.stderr).strip()
            if result.returncode == 0:
                return {"success": True, "result": output or "Команда выполнена успешно.", "error": None}
            else:
                return {"success": False, "error": output or f"Код завершения: {result.returncode}", "result": None}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Таймаут (60 сек)", "result": None}
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}
