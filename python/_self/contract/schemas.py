# schemas.py

from pydantic import BaseModel
from typing import Literal, Optional

# --- Торговые Схемы (Trade Flow) ---


class TradeInput(BaseModel):
    """Начальные данные для торговой операции."""

    ticker: str
    amount: float  # Сумма в USD для покупки
    max_slippage: float = 0.005  # Максимально допустимое проскальзывание


class PriceOutput(BaseModel):
    """Выходные данные после получения цены."""

    ticker: str
    current_price: float
    volume_24h: float


class ExecutionInput(BaseModel):
    """Входные данные для контракта на исполнение (зависит от цены и начальных данных)."""

    ticker: str
    current_price: float
    amount_usd: float  # Пришло из TradeInput


class ExecutionOutput(BaseModel):
    """Выходные данные после исполнения ордера."""

    order_id: str
    executed_price: float
    quantity_bought: float
    fee_usd: float


class NotificationInput(BaseModel):
    """Входные данные для контракта уведомления."""

    order_id: str
    executed_price: float
    quantity_bought: float


# --- Общие Схемы Задач (Task Flow) ---


class UserFetchInput(BaseModel):
    name: str


class UserFetchOutput(BaseModel):
    user_id: int
    user_name_verified: str


class OrderCreationOutput(BaseModel):
    order_id: str
    status_code: int


class NotifyGenericInput(BaseModel):
    user_id_for_notify: int
    order_id: str
