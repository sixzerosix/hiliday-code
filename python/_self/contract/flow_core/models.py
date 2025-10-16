# flow_core_project/flow_core/models.py

from typing import Literal, Set, get_args, Optional
from pydantic import BaseModel

# Базовые, не изменяемые статусы для логики Flow Core
BASE_FLOW_STATUSES = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]


# Функция для создания динамического типа Status
def create_flow_status_type(additional_statuses: Optional[Set[str]] = None):
    """
    Создает тип Literal для статусов Flow Core, включая базовые и дополнительные.
    """
    all_statuses = set(get_args(BASE_FLOW_STATUSES))
    if additional_statuses:
        all_statuses.update(additional_statuses)

    # Сортируем для детерминированного порядка
    sorted_statuses = tuple(sorted(list(all_statuses)))

    # Возвращаем тип Literal
    return Literal[sorted_statuses]


# Класс-заглушка для контрактов без входных/выходных данных
class EmptyData(BaseModel):
    """Модель для контрактов, которые не требуют или не выдают данных."""

    pass


# --- Пример Pydantic моделей для контрактов (для демонстрации) ---
# Эти модели теперь здесь, а не в run_flow.py
class UserInput(BaseModel):
    user_id: str


class UserData(BaseModel):
    user_id: str
    name: str


class ProcessedData(BaseModel):
    processed_id: str
    status: str


class NotificationInput(BaseModel):
    name: str
    message: str


# Модели из schemas.py, которые могут быть использованы в примерах
# Если schemas.py находится в корне проекта, то эти модели будут импортированы оттуда.
# Для простоты, если schemas.py будет в flow_core_project/schemas.py,
# то здесь можно добавить импорты:
# from schemas import (
#     TradeInput, PriceOutput, ExecutionInput, ExecutionOutput, NotificationInput as TradingNotificationInput,
#     NotificationStatusOutput, UserFetchInput, UserFetchOutput, OrderCreationOutput, NotifyGenericInput
# )
