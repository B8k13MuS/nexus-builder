import ast
import subprocess
import tempfile
import os
from typing import Any, Dict
from core.tools.base import BaseTool

# ──────────────────────────────────────────────
# AST-песочница
#
# Код генерируется LLM по голосовой команде пользователя, поэтому
# выполняется в максимально урезанном окружении: только вычисления
# и работа с данными, без файловой системы, сети, процессов и без
# обходов через dunder-атрибуты (__class__, __globals__, __subclasses__ и т.д.)
# ──────────────────────────────────────────────

_ALLOWED_IMPORTS = {
    "math", "random", "datetime", "json", "re", "statistics",
    "itertools", "collections", "decimal", "fractions", "string",
    "textwrap", "time",
}

_FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "open", "input", "__import__",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "exit", "quit", "breakpoint", "memoryview",
}

_FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "socket", "shutil", "pathlib",
    "importlib", "ctypes", "multiprocessing", "threading",
    "asyncio", "pickle", "marshal", "shelve", "tempfile",
    "requests", "urllib", "http", "ftplib", "telnetlib",
}


class SandboxViolation(Exception):
    pass


class _SandboxValidator(ast.NodeVisitor):
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            root = alias.name.split(".")[0]
            if root in _FORBIDDEN_MODULES or root not in _ALLOWED_IMPORTS:
                raise SandboxViolation(f"Импорт модуля запрещён: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        root = (node.module or "").split(".")[0]
        if root in _FORBIDDEN_MODULES or root not in _ALLOWED_IMPORTS:
            raise SandboxViolation(f"Импорт модуля запрещён: {node.module}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr.startswith("__") and node.attr.endswith("__"):
            raise SandboxViolation(f"Доступ к dunder-атрибуту запрещён: {node.attr}")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if node.id in _FORBIDDEN_NAMES:
            raise SandboxViolation(f"Использование запрещено: {node.id}")
        if node.id.startswith("__") and node.id.endswith("__"):
            raise SandboxViolation(f"Использование запрещено: {node.id}")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, str) and "__" in node.value:
            raise SandboxViolation("Строковый литерал содержит запрещённую последовательность '__'")
        self.generic_visit(node)


def _validate(code: str) -> None:
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as e:
        raise SandboxViolation(f"Синтаксическая ошибка: {e}")
    _SandboxValidator().visit(tree)


class CodeExecutorTool(BaseTool):
    """Инструмент для выполнения фрагментов кода Python в песочнице."""

    @property
    def name(self) -> str:
        return "code_executor"

    @property
    def description(self) -> str:
        return (
            "Выполняет предоставленный код на Python в ограниченной песочнице "
            "(только вычисления и обработка данных, без файловой системы и сети) "
            "и возвращает результат (stdout) или ошибку (stderr)."
        )

    def execute(self, **kwargs) -> Dict[str, Any]:
        code = kwargs.get("code")
        if not code:
            return {"success": False, "error": "Не указан параметр 'code'", "result": None}

        try:
            _validate(code)
        except SandboxViolation as e:
            return {"success": False, "result": None, "error": f"Заблокировано песочницей: {e}"}

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_path = f.name

            result = subprocess.run(
                ['python3', '-I', temp_path],
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8',
                env={"PATH": os.environ.get("PATH", "")},
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                return {
                    "success": True,
                    "result": output if output else "Код выполнен успешно, вывод пуст.",
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "result": None,
                    "error": result.stderr.strip()[:1000]
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Превышено время выполнения кода (10 сек)", "result": None}
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
