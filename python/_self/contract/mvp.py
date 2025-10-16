import uuid
import asyncio
from typing import Any, Dict, List, Optional, Literal, Callable, Type
from pydantic import BaseModel, ValidationError

# --- НОВОЕ: Определение Pydantic Схем для Контрактов ---


class FetchUserInput(BaseModel):
    """Входная схема для контракта FetchUser."""

    name: str


class FetchUserOutput(BaseModel):
    """Выходная схема для контракта FetchUser."""

    user_id: int
    user_name_verified: str


class CreateOrderInput(BaseModel):
    """Входная схема для контракта CreateOrder."""

    user_id: int
    product: str


class CreateOrderOutput(BaseModel):
    """Выходная схема для контракта CreateOrder."""

    order_id: str
    status_code: int


class NotifyUserInput(BaseModel):
    """Входная схема для контракта NotifyUser."""

    user_id_for_notify: int
    order_id: str


class NotifyUserOutput(BaseModel):
    """Выходная схема для контракта NotifyUser."""

    notification_sent: bool


# -------------------------------------------------------------------

# --- 1. Определение Структур Данных ---

Status = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]


class Contract:
    """Представляет задачу с требованиями и результатом, теперь использующую Pydantic."""

    def __init__(
        self,
        name: str,
        # ИСПОЛЬЗУЕМ Pydantic классы вместо List[str]
        InputModel: Type[BaseModel],
        OutputModel: Type[BaseModel],
        logic: Callable[..., Dict[str, Any]],  # Асинхронная или синхронная функция
    ) -> None:
        self.id = uuid.uuid4()
        self.name = name
        # Ссылки на Pydantic схемы
        self.InputModel = InputModel
        self.OutputModel = OutputModel
        self.logic = logic
        self.data: Dict[str, Any] = {}
        self.status: Status = "PENDING"
        self.required_inputs: Dict[str, Any] = {}  # Собранные сырые данные

    def is_ready(self) -> bool:
        """Проверяет, собрано ли достаточно данных для попытки валидации."""
        # Проверяем, что собрано СТОЛЬКО ЖЕ или больше ключей, чем нужно в InputModel
        return self.status == "PENDING" and len(self.required_inputs) >= len(
            self.InputModel.model_fields
        )

    async def execute(self) -> None:
        """Асинхронно выполняет логику контракта с валидацией Pydantic."""
        if not self.is_ready():
            print(f"⚠️ {self.name} не готов к запуску или уже в работе.")
            return

        self.status = "RUNNING"
        print(f"🟡 Контракт '{self.name}' запущен (RUNNING)...")

        try:
            # 1. ВАЛИДАЦИЯ ВХОДНЫХ ДАННЫХ Pydantic
            validated_inputs = self.InputModel(**self.required_inputs)

            # Данные для логики берем из валидированной модели
            input_data_for_logic = validated_inputs.model_dump()

            # 2. Выполнение логики
            if asyncio.iscoroutinefunction(self.logic):
                result = await self.logic(**input_data_for_logic)
            else:
                result = await asyncio.to_thread(self.logic, **input_data_for_logic)

            # 3. ВАЛИДАЦИЯ ВЫХОДНЫХ ДАННЫХ Pydantic
            validated_output = self.OutputModel(**result)
            self.data = validated_output.model_dump()  # Сохраняем проверенные данные

            self.status = "COMPLETED"
            print(f"✅ Контракт '{self.name}' завершен. Результат: {self.data}")

        except ValidationError as e:
            self.status = "FAILED"
            print(
                f"❌ Контракт '{self.name}' провалился из-за ошибки валидации: {e.errors()}"
            )
            self.data = {}
        except Exception as e:
            self.status = "FAILED"
            print(f"❌ Контракт '{self.name}' провалился: {e}")
            self.data = {}


class Dependency:
    """Определяет связь и правила маппинга данных между контрактами."""

    def __init__(
        self,
        source_contract: Contract,
        target_contract: Contract,
        mapping: Dict[str, str],  # {ключ_источника: ключ_цели}
    ) -> None:
        self.source = source_contract
        self.target = target_contract
        self.mapping = mapping


# --- 2. Класс-Исполнитель (Flow/Scheduler Core) ---


class AsyncFlow:
    """Управляет асинхронным порядком выполнения и потоком данных."""

    def __init__(
        self, contracts: List[Contract], dependencies: List[Dependency]
    ) -> None:
        self.contracts = contracts
        self.dependencies = dependencies
        self.running_tasks: List[asyncio.Task] = []

    def _initialize_contracts(self, initial_data: Dict[str, Any]) -> None:
        """Инициализирует контракты начальными данными."""
        for contract in self.contracts:
            # Итерируемся по полям InputModel (ключи)
            for key in contract.InputModel.model_fields.keys():
                if key in initial_data:
                    contract.required_inputs[key] = initial_data[key]
        print("🚀 Инициализация Потока завершена.")

    def _distribute_data(self, completed_contract: Contract) -> None:
        """Распределяет выходные данные завершенного контракта по зависимым."""
        for dep in self.dependencies:
            if dep.source == completed_contract:
                target = dep.target
                if target.status == "PENDING":
                    for src_key, target_key in dep.mapping.items():
                        # Данные берутся из проверенного self.data
                        if src_key in completed_contract.data:
                            target.required_inputs[target_key] = (
                                completed_contract.data[src_key]
                            )

    async def run(self, initial_data: Dict[str, Any] = None) -> None:
        """Основной цикл планировщика."""

        self._initialize_contracts(initial_data or {})

        while any(c.status in ["PENDING", "RUNNING"] for c in self.contracts):

            # 1. Запуск готовых контрактов
            ready_contracts = [c for c in self.contracts if c.is_ready()]
            newly_started_count = 0

            for contract in ready_contracts:
                task = asyncio.create_task(contract.execute())
                self.running_tasks.append(task)
                newly_started_count += 1

            if ready_contracts:
                print(
                    f"\n💡 Найдено и запущено {newly_started_count} новых контрактов."
                )

            # 2. Ожидание завершения любой из запущенных задач
            if not self.running_tasks and any(
                c.status == "PENDING" for c in self.contracts
            ):
                print(
                    "\n🛑 Тупиковая ситуация: Нет готовых к выполнению контрактов, и нет запущенных задач."
                )
                break

            if self.running_tasks:
                done, pending = await asyncio.wait(
                    self.running_tasks, return_when=asyncio.FIRST_COMPLETED
                )
                self.running_tasks = list(pending)

                # 3. Обработка завершенных контрактов
                for task in done:
                    # Находим, какой контракт завершился
                    # NOTE: Более надежный поиск: хранить ссылку на контракт в самой Task или использовать словарь ID.
                    completed_contract = next(
                        (
                            c
                            for c in self.contracts
                            if c.status in ["COMPLETED", "FAILED"]
                        ),
                        None,
                    )

                    if completed_contract and completed_contract.status == "COMPLETED":
                        self._distribute_data(completed_contract)
                    elif completed_contract and completed_contract.status == "FAILED":
                        print(
                            f"--- Процесс остановлен из-за ошибки в контракте '{completed_contract.name}' ---"
                        )
                        return

            await asyncio.sleep(0.1)

        print("\n--- ПОТОК ЗАВЕРШЕН ---")


# --- 3. Определяем Логику Контрактов (Асинхронные Функции) ---

# Логика теперь ожидает аргументы, соответствующие Pydantic схемам


async def task_fetch_user_id(name: str) -> Dict[str, Any]:
    print(f"   [LOGIC: FetchUser] Ищем ID для {name}...")
    await asyncio.sleep(1.5)
    # Возвращаемые данные должны соответствовать FetchUserOutput
    return {"user_id": 12345, "user_name_verified": name}


def task_create_order(user_id: int, product: str) -> Dict[str, Any]:
    print(
        f"   [LOGIC: CreateOrder] Создаем заказ для ID: {user_id} на продукт: {product}..."
    )
    import time

    time.sleep(0.5)
    # Возвращаемые данные должны соответствовать CreateOrderOutput
    return {"order_id": f"ORD-{user_id}-001", "status_code": 200}


async def task_send_notification(
    user_id_for_notify: int, order_id: str
) -> Dict[str, Any]:
    print(
        f"   [LOGIC: NotifyUser] Отправляем уведомление по заказу {order_id} для {user_id_for_notify}..."
    )
    await asyncio.sleep(0.1)
    # Возвращаемые данные должны соответствовать NotifyUserOutput
    return {"notification_sent": True}


# --- 4. Создание и Запуск Потока ---

# 4.1. Создание Контрактов с Pydantic Схемами
c1 = Contract(
    name="FetchUser",
    InputModel=FetchUserInput,  # Схема входа
    OutputModel=FetchUserOutput,  # Схема выхода
    logic=task_fetch_user_id,
)
c2 = Contract(
    name="CreateOrder",
    InputModel=CreateOrderInput,
    OutputModel=CreateOrderOutput,
    logic=task_create_order,
)
c3 = Contract(
    name="NotifyUser",
    InputModel=NotifyUserInput,
    OutputModel=NotifyUserOutput,
    logic=task_send_notification,
)

# 4.2. Создание Зависимостей (Маппинг остается прежним, но теперь более строгим)
# C1 -> C2
dep1_2 = Dependency(
    source_contract=c1, target_contract=c2, mapping={"user_id": "user_id"}
)

# C2 -> C3
dep2_3 = Dependency(
    source_contract=c2, target_contract=c3, mapping={"order_id": "order_id"}
)

# C1 -> C3 (C3 нужен user_id, который дает C1)
dep1_3 = Dependency(
    source_contract=c1, target_contract=c3, mapping={"user_id": "user_id_for_notify"}
)

# 4.3. Запуск
flow = AsyncFlow(contracts=[c1, c2, c3], dependencies=[dep1_2, dep2_3, dep1_3])

initial_process_data = {
    "name": "Alex",  # Для FetchUserInput
    "product": "Laptop X1",  # Для CreateOrderInput
}

print("--- АСИНХРОННЫЙ ЗАПУСК ЯДРА С ВАЛИДАЦИЕЙ PYDANTIC ---")
asyncio.run(flow.run(initial_process_data))
