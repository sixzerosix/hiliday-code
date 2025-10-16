# flow_core.py

import uuid
import asyncio
from typing import Any, Dict, List, Optional, Literal, Callable, Type
from pydantic import BaseModel, ValidationError

Status = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]


class Contract:
    """Представляет универсальную задачу с контрактом данных (Input/Output Pydantic)."""

    def __init__(
        self,
        name: str,
        InputModel: Type[BaseModel],
        OutputModel: Type[BaseModel],
        logic: Callable[..., Dict[str, Any]],
    ) -> None:
        self.id = uuid.uuid4()
        self.name = name
        self.InputModel = InputModel
        self.OutputModel = OutputModel
        self.logic = logic
        self.data: Dict[str, Any] = {}
        self.status: Status = "PENDING"
        self.required_inputs: Dict[str, Any] = {}  # Собранные сырые данные

    def is_ready(self) -> bool:
        """Проверяет, собрано ли достаточно данных для попытки валидации входной схемы."""
        # Проверяем, что собрано ключей больше или равно необходимому для InputModel
        return self.status == "PENDING" and len(self.required_inputs) >= len(
            self.InputModel.model_fields
        )

    async def execute(self) -> None:
        """Асинхронно выполняет логику контракта с валидацией Pydantic."""
        if not self.is_ready():
            return

        self.status = "RUNNING"
        print(f"🟡 [CORE] Контракт '{self.name}' запущен (RUNNING)...")

        try:
            # 1. ВАЛИДАЦИЯ ВХОДНЫХ ДАННЫХ Pydantic
            validated_inputs = self.InputModel(**self.required_inputs)
            input_data_for_logic = validated_inputs.model_dump()

            # 2. Выполнение логики
            if asyncio.iscoroutinefunction(self.logic):
                result = await self.logic(**input_data_for_logic)
            else:
                result = await asyncio.to_thread(self.logic, **input_data_for_logic)

            # 3. ВАЛИДАЦИЯ ВЫХОДНЫХ ДАННЫХ Pydantic
            validated_output = self.OutputModel(**result)
            self.data = validated_output.model_dump()

            self.status = "COMPLETED"
            print(f"✅ [CORE] Контракт '{self.name}' завершен. Результат: {self.data}")

        except ValidationError as e:
            self.status = "FAILED"
            print(
                f"❌ [CORE] Контракт '{self.name}' провалился из-за ошибки валидации: {e.errors()}"
            )
            self.data = {}
        except Exception as e:
            self.status = "FAILED"
            print(
                f"❌ [CORE] Контракт '{self.name}' провалился из-за внутренней ошибки: {e}"
            )
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
            for key in contract.InputModel.model_fields.keys():
                if key in initial_data:
                    contract.required_inputs[key] = initial_data[key]
        print("🚀 [CORE] Инициализация Потока завершена.")

    # Фрагмент кода, который нужно изменить в flow_core.py

    def _distribute_data(self, completed_contract: Contract) -> None:
        """Распределяет выходные данные завершенного контракта по зависимым."""
        for dep in self.dependencies:
            if dep.source == completed_contract:
                target = dep.target
                if target.status == "PENDING":

                    # --- НОВАЯ ЛОГИКА АВТОМАТИЧЕСКОГО МЭППИНГА ---
                    if "*" in dep.mapping and dep.mapping["*"] == "*":
                        # Если указан маркер "*: *", автоматически передаем совпадающие ключи
                        target_input_keys = target.InputModel.model_fields.keys()
                        for src_key, src_value in completed_contract.data.items():
                            if src_key in target_input_keys:
                                target.required_inputs[src_key] = src_value
                                print(
                                    f"      [AUTO-MAP] {completed_contract.name}:{src_key} -> {target.name}:{src_key}"
                                )
                        continue  # Пропускаем стандартный маппинг для этой зависимости
                    # -----------------------------------------------

                    # Стандартный маппинг
                    for src_key, target_key in dep.mapping.items():
                        if src_key in completed_contract.data:
                            target.required_inputs[target_key] = (
                                completed_contract.data[src_key]
                            )

    async def run(self, initial_data: Dict[str, Any] | None = None) -> None:
        """Основной цикл планировщика."""

        self._initialize_contracts(initial_data or {})

        while any(c.status in ["PENDING", "RUNNING"] for c in self.contracts):

            ready_contracts = [c for c in self.contracts if c.is_ready()]
            newly_started_count = 0

            for contract in ready_contracts:
                task = asyncio.create_task(contract.execute())
                self.running_tasks.append(task)
                newly_started_count += 1

            if ready_contracts:
                print(
                    f"\n💡 [CORE] Найдено и запущено {newly_started_count} новых контрактов."
                )

            if not self.running_tasks and any(
                c.status == "PENDING" for c in self.contracts
            ):
                print(
                    "\n🛑 [CORE] Тупиковая ситуация: Нет готовых к выполнению контрактов, и нет запущенных задач."
                )
                break

            if self.running_tasks:
                done, pending = await asyncio.wait(
                    self.running_tasks, return_when=asyncio.FIRST_COMPLETED
                )
                self.running_tasks = list(pending)

                for task in done:
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
                            f"--- [CORE] Процесс остановлен из-за ошибки в контракте '{completed_contract.name}' ---"
                        )
                        return

            await asyncio.sleep(0.1)

        print("\n--- [CORE] ПОТОК ЗАВЕРШЕН ---")
