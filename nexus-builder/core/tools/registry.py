from typing import Dict
from core.tools.base import BaseTool
from core.tools.file_writer import FileWriterTool
from core.tools.web_search import WebSearchTool
from core.tools.code_executor import CodeExecutorTool
from core.tools.project_builder import ProjectBuilderTool
from core.tools.shell_executor import ShellExecutorTool


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        for tool in [
            FileWriterTool(),
            WebSearchTool(),
            CodeExecutorTool(),
            ProjectBuilderTool(),
            ShellExecutorTool(),
        ]:
            self.register(tool)

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        return self._tools.get(name)

    def get_all_descriptions(self) -> str:
        return "\n".join(f"- {t.name}: {t.description}" for t in self._tools.values())

    def execute(self, name: str, **kwargs):
        tool = self.get(name)
        if not tool:
            return {"success": False, "error": f"Инструмент '{name}' не найден", "result": None}
        return tool.execute(**kwargs)


tool_registry = ToolRegistry()
