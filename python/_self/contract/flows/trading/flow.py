# trading_flow.py

import uuid
import asyncio
import logging
from typing import Dict, Any, Set

from flow_core.core import Contract, Dependency, AsyncFlow
from flow_core.models import EmptyData
from .schemas import (
    TradeInput,
    PriceOutput,
    ExecutionInput,
    ExecutionOutput,
    NotificationInput,
    NotificationStatusOutput,
    # НОВЫЕ ИМПОРТЫ СХЕМ
    VolumeCheckInput,
    VolumeCheckOutput,
    PriceAlertInput,
    PriceAlertOutput,
)
from flow_core.logging_config import setup_logging

logger = logging.getLogger("flow_core.trading_flow")

# --- 1. Логика Контрактов (Торговая Операция) ---


async def get_market_price(
    ticker: str, amount_usd: float, max_slippage: float = 0.005, **kwargs
) -> Dict[str, Any]:
    """Контракт 1: Получение рыночной цены."""
    logger.info(
        f"Запрос цены для {ticker} с макс. проскальзыванием {max_slippage} для {amount_usd}$..."
    )
    await asyncio.sleep(0.8)
    # C1_Price.data будет содержать все эти поля:
    return {"ticker": ticker, "current_price": 150.50, "volume_24h": 500000.0}


async def check_risk_and_execute(
    ticker: str, current_price: float, amount_usd: float
) -> Dict[str, Any]:
    """Контракт 2: Проверка рисков и исполнение ордера."""
    if amount_usd / current_price > 1000:
        logger.error("Риск-менеджмент: Слишком большой объем для исполнения!")
        raise Exception("Риск-менеджмент: Слишком большой объем для исполнения!")

    logger.info(f"Исполнение ордера на {amount_usd}$ по цене {current_price}...")

    await asyncio.sleep(1.2)
    quantity = amount_usd / current_price

    return {
        "order_id": f"EX-{ticker}-{uuid.uuid4().hex[:4]}",
        "executed_price": current_price,
        "quantity_bought": quantity,
        "fee_usd": amount_usd * 0.001,
    }


async def send_execution_notification(
    order_id: str, executed_price: float, quantity_bought: float
) -> Dict[str, Any]:
    """Контракт 3: Уведомление об исполнении ордера."""
    logger.info(
        f"Уведомление: Ордер {order_id} исполнен. Куплено: {quantity_bought:.2f} по {executed_price}!"
    )
    return {"notification_status": "SENT"}


# --- НОВАЯ ЛОГИКА КОНТРАКТОВ ---


async def check_trading_volume(ticker: str, volume_24h: float) -> Dict[str, Any]:
    """Контракт 4: Проверка объема торгов."""
    logger.info(f"Проверка объема торгов для {ticker}. Объем за 24ч: {volume_24h}")
    is_high = volume_24h > 400000.0  # Пример условия
    await asyncio.sleep(0.3)
    return {"ticker": ticker, "is_high_volume": is_high}


async def send_price_alert(ticker: str, current_price: float) -> Dict[str, Any]:
    """Контракт 5: Отправка ценового уведомления."""
    logger.info(
        f"Отправка ценового уведомления для {ticker} по цене {current_price}..."
    )
    # Имитация отправки уведомления
    await asyncio.sleep(0.2)
    return {"ticker": ticker, "alert_sent": True}


# --- 2. Создание Flow ---

# Контракты
C1_Price = Contract(
    name="GetMarketPrice",
    InputModel=TradeInput,
    OutputModel=PriceOutput,
    logic=get_market_price,
)

C2_Execute = Contract(
    name="ExecuteOrder",
    InputModel=ExecutionInput,
    OutputModel=ExecutionOutput,
    logic=check_risk_and_execute,
)

C3_Notify = Contract(
    name="NotifyExecution",
    InputModel=NotificationInput,
    OutputModel=NotificationStatusOutput,
    logic=send_execution_notification,
)

# НОВЫЕ КОНТРАКТЫ
C4_VolumeCheck = Contract(
    name="CheckVolume",
    InputModel=VolumeCheckInput,
    OutputModel=VolumeCheckOutput,
    logic=check_trading_volume,
)

C5_PriceAlert = Contract(
    name="PriceAlert",
    InputModel=PriceAlertInput,
    OutputModel=PriceAlertOutput,
    logic=send_price_alert,
)


# Зависимости (Связывание данных)
# C1 (Цена) -> C2 (Исполнение) - берет ticker, current_price
DEP_P_E = Dependency(
    source_contract=C1_Price,
    target_contract=C2_Execute,
    mapping={"current_price": "current_price", "ticker": "ticker"},
)

# C1 (Цена) -> C4 (Проверка объема) - берет ticker, volume_24h
DEP_P_VC = Dependency(
    source_contract=C1_Price,
    target_contract=C4_VolumeCheck,
    mapping={"ticker": "ticker", "volume_24h": "volume_24h"},
)

# C1 (Цена) -> C5 (Ценовое уведомление) - берет ticker, current_price
DEP_P_PA = Dependency(
    source_contract=C1_Price,
    target_contract=C5_PriceAlert,
    mapping={"ticker": "ticker", "current_price": "current_price"},
)


# C2 (Исполнение) -> C3 (Уведомление)
DEP_E_N = Dependency(
    source_contract=C2_Execute,
    target_contract=C3_Notify,
    mapping={
        "order_id": "order_id",
        "executed_price": "executed_price",
        "quantity_bought": "quantity_bought",
    },
)

# --- 3. Запуск ---

# if __name__ == "__main__":
setup_logging(
    log_level="DEBUG", log_to_console=True, log_file="trading_flow.log"
)  # Установим DEBUG для более детального вывода
logger.info("--- ЗАПУСК ПОТОКА ТОРГОВЫХ ОПЕРАЦИЙ ---")

custom_trading_statuses: Set[str] = {"PRE_CHECK_FAILED", "PENDING_APPROVAL"}

trade_flow = AsyncFlow(
    contracts=[
        C1_Price,
        C2_Execute,
        C3_Notify,
        C4_VolumeCheck,
        C5_PriceAlert,
    ],  # Включаем все контракты
    dependencies=[DEP_P_E, DEP_P_VC, DEP_P_PA, DEP_E_N],  # Включаем все зависимости
    additional_flow_statuses=custom_trading_statuses,
)

initial_trade_data = {
    "ticker": "ETHUSD",
    "amount_usd": 1000.00,
    "max_slippage": 0.001,
}

asyncio.run(trade_flow.run(initial_trade_data))
logger.info("--- ПОТОК ТОРГОВЫХ ОПЕРАЦИЙ ЗАВЕРШЕН ---")
