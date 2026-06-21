from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """Базовый класс для всех инструментов агента."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Уникальное имя инструмента."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Описание того, что делает инструмент."""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Выполняет действие инструмента.
        
        Args:
            **kwargs: Параметры для инструмента
            
        Returns:
            Dict с результатами выполнения:
            - success: bool
            - result: Any (результат выполнения)
            - error: str (если success=False)
        """
        pass
