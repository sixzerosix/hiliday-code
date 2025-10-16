# task_flow.py

import asyncio
from typing import Dict, Any
from flow_core import Contract, Dependency, AsyncFlow
from schemas import (
    UserFetchInput,
    UserFetchOutput,
    OrderCreationOutput,
    NotifyGenericInput,
)

# --- 1. Логика Контрактов (Общие Задачи) ---


async def task_fetch_user_id(name: str) -> Dict[str, Any]:
    """Задача 1: Получение ID пользователя."""
    print(f"   [TASK LOGIC] Ищем ID для имени: {name}...")
    await asyncio.sleep(1.0)
    return {"user_id": 9876, "user_name_verified": name}


def task_process_order(user_id: int) -> Dict[str, Any]:
    """Задача 2: Обработка заказа."""
    print(f"   [TASK LOGIC] Обрабатываем заказ для ID: {user_id}...")
    import time

    time.sleep(0.3)
    return {"order_id": f"TASK-ORD-{user_id}-002", "status_code": 200}


async def task_send_generic_notification(
    user_id_for_notify: int, order_id: str
) -> Dict[str, Any]:
    """Задача 3: Отправка уведомления."""
    print(
        f"   [TASK LOGIC] Отправляем уведомление по заказу {order_id} для {user_id_for_notify}..."
    )
    await asyncio.sleep(0.1)
    return {"notification_sent": True}


# --- 2. Создание Flow ---

# Контракты
T1_User = Contract(
    name="FetchUser",
    InputModel=UserFetchInput,
    OutputModel=UserFetchOutput,
    logic=task_fetch_user_id,
)

T2_Order = Contract(
    name="ProcessOrder",
    InputModel=UserFetchOutput,  # T2 ожидает user_id из T1
    OutputModel=OrderCreationOutput,
    logic=task_process_order,
)

T3_Notify = Contract(
    name="NotifyUser",
    InputModel=NotifyGenericInput,
    OutputModel=NotifyGenericInput,
    logic=task_send_generic_notification,
)

# Зависимости
# T1 -> T2
DEP_U_O = Dependency(
    source_contract=T1_User, target_contract=T2_Order, mapping={"user_id": "user_id"}
)

# T2 -> T3
DEP_O_N = Dependency(
    source_contract=T2_Order,
    target_contract=T3_Notify,
    mapping={"order_id": "order_id"},
)

# T1 -> T3 (T3 нужен user_id)
DEP_U_N = Dependency(
    source_contract=T1_User,
    target_contract=T3_Notify,
    mapping={"user_id": "user_id_for_notify"},
)

# --- 3. Запуск ---

if __name__ == "__main__":
    task_flow = AsyncFlow(
        contracts=[T1_User, T2_Order, T3_Notify],
        dependencies=[DEP_U_O, DEP_O_N, DEP_U_N],
    )

    initial_task_data = {"name": "Jane", "some_extra_data": "ignored"}

    print("\n--- ЗАПУСК ПОТОКА ОБЩИХ ЗАДАЧ ---")
    asyncio.run(task_flow.run(initial_task_data))
