# trading_flow.py

import asyncio
from typing import Dict, Any
from flow_core import Contract, Dependency, AsyncFlow
from schemas import (
    TradeInput,
    PriceOutput,
    ExecutionInput,
    ExecutionOutput,
    NotificationInput,
)

# --- 1. Логика Контрактов (Торговая Операция) ---


async def get_market_price(ticker: str, max_slippage: float) -> Dict[str, Any]:
    """Контракт 1: Получение рыночной цены."""
    print(
        f"   [TRADE LOGIC] Запрос цены для {ticker} с макс. проскальзыванием {max_slippage}..."
    )
    await asyncio.sleep(0.8)
    return {"ticker": ticker, "current_price": 150.50, "volume_24h": 500000.0}


async def check_risk_and_execute(
    ticker: str, current_price: float, amount_usd: float
) -> Dict[str, Any]:
    """Контракт 2: Проверка рисков и исполнение ордера."""
    if amount_usd / current_price > 1000:
        raise Exception("Риск-менеджмент: Слишком большой объем для исполнения!")

    print(
        f"   [TRADE LOGIC] Исполнение ордера на {amount_usd}$ по цене {current_price}..."
    )
    await asyncio.sleep(1.2)
    quantity = amount_usd / current_price

    return {
        "order_id": f"EX-{ticker}-{uuid.uuid4().hex[:4]}",
        "executed_price": current_price,
        "quantity_bought": quantity,
        "fee_usd": amount_usd * 0.001,
    }


def send_execution_notification(
    order_id: str, executed_price: float, quantity_bought: float
) -> Dict[str, Any]:
    """Контракт 3: Уведомление об исполнении ордера (синхронная задача)."""
    print(
        f"   [TRADE LOGIC] Уведомление: Ордер {order_id} исполнен. Куплено: {quantity_bought:.2f} по {executed_price}!"
    )
    return {"notification_status": "SENT"}


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
    OutputModel=NotificationInput,  # Здесь OutputModel может быть простым статусом
    logic=send_execution_notification,
)

# Зависимости (Связывание данных)
# C1 (Цена) -> C2 (Исполнение)
DEP_P_E = Dependency(
    source_contract=C1_Price,
    target_contract=C2_Execute,
    mapping={"current_price": "current_price", "ticker": "ticker"},
)

# TradeInput -> C2 (Исполнение): C2 также нужен 'amount' из начальных данных
# NOTE: В Flow Core при инициализации "amount" попадет в C2. Но для явного маппинга от C1 его не нужно.
# Тут мы маппируем данные, которые прошли через C1 (хотя C1 их не генерировал, он их получил)
# Более чистый способ: C2 зависит от C1 (по цене) И от входных данных (по amount).
# Мы должны убедиться, что 'amount' попал в required_inputs C2.
# В нашем текущем ядре это произойдет через _initialize_contracts.

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

if __name__ == "__main__":
    trade_flow = AsyncFlow(
        contracts=[C1_Price, C2_Execute, C3_Notify], dependencies=[DEP_P_E, DEP_E_N]
    )

    initial_trade_data = {
        "ticker": "ETHUSD",  # Для C1 и C2 (через инициализацию)
        "amount": 1000.00,  # Для C2 (через инициализацию)
        "max_slippage": 0.001,  # Для C1
    }

    print("--- ЗАПУСК ПОТОКА ТОРГОВЫХ ОПЕРАЦИЙ ---")
    asyncio.run(trade_flow.run(initial_trade_data))
