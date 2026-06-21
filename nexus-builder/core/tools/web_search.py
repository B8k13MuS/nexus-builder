import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Dict
from core.tools.base import BaseTool

# Импортируем ssl чтобы пропустить верификацию (WSL2 workaround)
import ssl
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


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
        Args:
            query: поисковый запрос
        """
        query = kwargs.get("query", "").strip()
        if not query:
            return {"success": False, "error": "Не указан query", "result": None}

        # Если есть кириллица — переводим через LLM
        if any("Ѐ" <= c <= "ӿ" for c in query):
            try:
                from core.llm_client import LLMClient
                llm = LLMClient()
                translated, _ = llm.ask(
                    f"Translate the following Russian text to English for a web search query. "
                    f"Return ONLY the English translation, nothing else: {query}"
                )
                if translated and not translated.startswith("Error:"):
                    query = translated.strip().strip('"').strip("'")
            except Exception:
                pass  # Используем оригинальный запрос если перевод не удался

        params = urllib.parse.urlencode({
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        })
        url = f"https://api.duckduckgo.com/?{params}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NexusAgent/1.0"})
            with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)

            abstract = data.get("AbstractText", "")
            if not abstract:
                related = data.get("RelatedTopics", [])
                abstract = related[0].get("Text", "") if related else ""
            if not abstract:
                abstract = "Результаты не найдены"

            return {"success": True, "result": abstract[:500], "error": None}

        except urllib.error.URLError as e:
            return {"success": False, "error": f"Сетевая ошибка: {e.reason}", "result": None}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Ошибка разбора ответа: {e}", "result": None}
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}
