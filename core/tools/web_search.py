import subprocess
import json
from typing import Any, Dict
from core.tools.base import BaseTool

class WebSearchTool(BaseTool):
    """Инструмент для поиска информации в интернете через DuckDuckGo."""
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "Ищет информацию в интернете по запросу. Возвращает краткие результаты поиска."
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Выполняет поиск в интернете.
        
        Args:
            query: поисковый запрос
        """
        query = kwargs.get("query")
        
        if not query:
            return {"success": False, "error": "Не указан query", "result": None}
        
        # Проверяем, есть ли кириллица в запросе
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in query)
        
        if has_cyrillic:
            # Если есть кириллица, используем LLM для перевода на английский
            try:
                from core.llm_client import LLMClient
                llm = LLMClient()
                translate_prompt = f"Translate the following Russian text to English for a web search query. Return ONLY the English translation, nothing else: {query}"
                english_query = llm.ask(translate_prompt).strip()
                query = english_query
            except Exception as e:
                # Если перевод не удался, используем оригинальный запрос
                pass
        
        # Используем DuckDuckGo Instant Answer API (бесплатный, без ключа)
        encoded_query = query.replace(" ", "+")
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
        
        try:
            # Используем curl для запроса
            command = ["curl", "-k", "-s", "-L", url]
            result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', timeout=10)
            
            data = json.loads(result.stdout)
            
            # Извлекаем релевантную информацию
            abstract = data.get("AbstractText", "")
            if not abstract:
                # Если нет абстракта, берем первые связанные темы
                related = data.get("RelatedTopics", [])
                if related:
                    abstract = related[0].get("Text", "Результаты не найдены")
                else:
                    abstract = "Результаты не найдены"
            
            return {
                "success": True,
                "result": abstract[:500],  # Ограничиваем длину
                "error": None
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Таймаут поиска", "result": None}
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}
