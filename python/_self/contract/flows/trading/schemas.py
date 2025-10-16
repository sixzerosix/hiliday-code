# schemas.py

from pydantic import BaseModel
from typing import Literal, Optional

# --- Торговые Схемы (Trade Flow) ---


class TradeInput(BaseModel):
    """Начальные данные для торговой операции."""

    ticker: str
    amount_usd: float  # Сумма в USD для покупки
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
    """Входные данные для контракта уведомления об исполнении."""

    order_id: str
    executed_price: float
    quantity_bought: float


class NotificationStatusOutput(BaseModel):
    """Выходные данные после отправки уведомления об исполнении."""

    notification_status: str


# --- НОВЫЕ СХЕМЫ ДЛЯ ДЕМОНСТРАЦИИ ---


class VolumeCheckInput(BaseModel):
    """Входные данные для контракта проверки объема."""

    ticker: str  # Добавим ticker для контекста в логах
    volume_24h: float


class VolumeCheckOutput(BaseModel):
    """Выходные данные после проверки объема."""

    ticker: str
    is_high_volume: bool


class PriceAlertInput(BaseModel):
    """Входные данные для контракта ценового уведомления."""

    ticker: str
    current_price: float


class PriceAlertOutput(BaseModel):
    """Выходные данные после отправки ценового уведомления."""

    ticker: str
    alert_sent: bool


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
