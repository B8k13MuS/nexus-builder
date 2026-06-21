import subprocess
import tempfile
import os
from typing import Any, Dict
from core.tools.base import BaseTool

class CodeExecutorTool(BaseTool):
    """Инструмент для выполнения фрагментов кода Python."""
    
    @property
    def name(self) -> str:
        return "code_executor"
    
    @property
    def description(self) -> str:
        return "Выполняет предоставленный код на Python и возвращает результат (stdout) или ошибку (stderr). Используйте для вычислений, обработки данных или генерации сложного текста."
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        code = kwargs.get("code")
        if not code:
            return {"success": False, "error": "Не указан параметр 'code'", "result": None}
        
        try:
            # Создаем временный файл для выполнения
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_path = f.name
            
            # Выполняем код с ограничением времени 10 секунд
            result = subprocess.run(
                ['python3', temp_path],
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8'
            )
            
            # Удаляем временный файл
            os.remove(temp_path)
            
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
                    "error": result.stderr.strip()
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Превышено время выполнения кода (10 сек)", "result": None}
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}
