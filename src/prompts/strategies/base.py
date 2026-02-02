from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """Базовый класс стратегии для генерации промпт-секций."""

    @abstractmethod
    def get_role(self) -> str:
        """Описание роли трейдера."""
        ...

    @abstractmethod
    def get_objective(self) -> str:
        """Цель стратегии."""
        ...

    @abstractmethod
    def get_time_horizon(self) -> str:
        """Горизонт удержания позиции."""
        ...

    @abstractmethod
    def get_strategy_section(self, ctx: dict) -> str:
        """Полная секция стратегии (## 3. СТРАТЕГИЯ)."""
        ...
