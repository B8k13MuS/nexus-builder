from typing import Dict
from core.tools.base import BaseTool
from core.tools.file_writer import FileWriterTool
from core.tools.web_search import WebSearchTool
from core.tools.code_executor import CodeExecutorTool

class ToolRegistry:
    """Реестр доступных инструментов."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Регистрирует стандартные инструменты."""
        tools_to_register = [
            FileWriterTool(),
            WebSearchTool(),
            CodeExecutorTool(),
        ]
        for tool in tools_to_register:
            self.register(tool)
    
    def register(self, tool: BaseTool):
        """Регистрирует новый инструмент."""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> BaseTool:
        """Возвращает инструмент по имени."""
        return self._tools.get(name)
    
    def get_all_descriptions(self) -> str:
        """Возвращает строку с описанием всех доступных инструментов для промпта LLM."""
        descriptions = []
        for tool in self._tools.values():
            descriptions.append(f"- {tool.name}: {tool.description}")
        return "\n".join(descriptions)
    
    def execute(self, name: str, **kwargs):
        """Выполняет инструмент по имени с переданными аргументами."""
        tool = self.get(name)
        if not tool:
            return {"success": False, "error": f"Инструмент '{name}' не найден", "result": None}
        return tool.execute(**kwargs)

# Глобальный экземпляр реестра
tool_registry = ToolRegistry()
