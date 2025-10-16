# flow_core_project/flow_core/core.py

import uuid
import asyncio
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Literal,
    Callable,
    Type,
    Awaitable,
    Union,
    Set,
    get_args,
)

from pydantic import BaseModel, ValidationError

# Импортируем функцию для создания статусов и базовые статусы
from flow_core.models import create_flow_status_type, BASE_FLOW_STATUSES

logger = logging.getLogger("flow_core.core")

Status = BASE_FLOW_STATUSES


class Contract:
    """Представляет универсальную задачу с контрактом данных (Input/Output Pydantic)."""

    def __init__(
        self,
        name: str,
        InputModel: Type[BaseModel],
        OutputModel: Type[BaseModel],
        logic: Callable[..., Union[Dict[str, Any], Awaitable[Dict[str, Any]]]],
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
        return self.status == "PENDING" and len(self.required_inputs) >= len(
            self.InputModel.model_fields
        )

    async def execute(self) -> None:
        """Асинхронно выполняет логику контракта с валидацией Pydantic."""
        if self.status != "PENDING":
            return

        self.status = "RUNNING"
        logger.info(f"Контракт '{self.name}' запущен (RUNNING)...")

        try:
            validated_inputs = self.InputModel(**self.required_inputs)
            input_data_for_logic = validated_inputs.model_dump()

            if asyncio.iscoroutinefunction(self.logic):
                result = await self.logic(**input_data_for_logic)
            else:
                result = await asyncio.to_thread(self.logic, **input_data_for_logic)

            validated_output = self.OutputModel(**result)
            self.data = validated_output.model_dump()

            self.status = "COMPLETED"
            logger.info(f"Контракт '{self.name}' завершен. Результат: {self.data}")

        except ValidationError as e:
            self.status = "FAILED"
            logger.error(
                f"Контракт '{self.name}' провалился из-за ошибки валидации: {e.errors()}"
            )
            self.data = {}
        except Exception as e:
            self.status = "FAILED"
            logger.exception(
                f"Контракт '{self.name}' провалился из-за внутренней ошибки."
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
        self,
        contracts: List[Contract],
        dependencies: List[Dependency],
        additional_flow_statuses: Optional[Set[str]] = None,
    ) -> None:
        self.contracts = contracts
        self.dependencies = dependencies
        self.running_tasks: List[asyncio.Task] = []
        self.task_contract_map: Dict[asyncio.Task, Contract] = {}

        self.FlowStatus = create_flow_status_type(additional_flow_statuses)
        self._all_valid_statuses = set(get_args(self.FlowStatus))
        self._base_flow_statuses = set(get_args(BASE_FLOW_STATUSES))

    def _initialize_contracts(self, initial_data: Dict[str, Any]) -> None:
        """Инициализирует контракты начальными данными."""
        for contract in self.contracts:
            for key in contract.InputModel.model_fields.keys():
                if key in initial_data:
                    contract.required_inputs[key] = initial_data[key]
        logger.info("Инициализация Потока завершена.")

    def _distribute_data(self, completed_contract: Contract) -> None:
        """Распределяет выходные данные завершенного контракта по зависимым."""
        for dep in self.dependencies:
            if dep.source == completed_contract:
                target = dep.target
                # Разрешаем передачу данных, если целевой контракт находится в PENDING
                # или в одном из дополнительных статусов, но не RUNNING/COMPLETED/FAILED
                if target.status == "PENDING" or (
                    target.status not in self._base_flow_statuses
                    and target.status != "RUNNING"
                    and target.status != "COMPLETED"
                    and target.status != "FAILED"
                ):

                    if "*" in dep.mapping and dep.mapping["*"] == "*":
                        target_input_keys = target.InputModel.model_fields.keys()
                        for src_key, src_value in completed_contract.data.items():
                            if src_key in target_input_keys:
                                target.required_inputs[src_key] = src_value
                                logger.debug(
                                    f"[AUTO-MAP] {completed_contract.name}:{src_key} -> {target.name}:{src_key}"
                                )
                        continue

                    for src_key, target_key in dep.mapping.items():
                        if src_key in completed_contract.data:
                            target.required_inputs[target_key] = (
                                completed_contract.data[src_key]
                            )

    async def run(self, initial_data: Dict[str, Any] | None = None) -> None:
        """Основной цикл планировщика."""

        self._initialize_contracts(initial_data or {})

        # ИСПРАВЛЕНО: Условие цикла. Продолжаем, пока есть хотя бы один незавершенный контракт.
        while any(c.status not in ["COMPLETED", "FAILED"] for c in self.contracts):

            ready_contracts = [c for c in self.contracts if c.is_ready()]
            newly_started_count = 0

            for contract in ready_contracts:
                task = asyncio.create_task(contract.execute())
                self.running_tasks.append(task)
                self.task_contract_map[task] = contract
                newly_started_count += 1

            if newly_started_count > 0:
                logger.info(
                    f"Найдено и запущено {newly_started_count} новых контрактов."
                )

            # ИСПРАВЛЕНО: Детектор тупиковой ситуации
            # Тупик, если нет активных задач И нет контрактов в PENDING,
            # но при этом есть контракты, которые еще не COMPLETED/FAILED.
            if not self.running_tasks and not any(
                c.status == "PENDING" for c in self.contracts
            ):
                if any(c.status not in ["COMPLETED", "FAILED"] for c in self.contracts):
                    logger.warning(
                        "Тупиковая ситуация: Нет запущенных контрактов, нет готовых к выполнению (PENDING), "
                        "но есть незавершенные контракты. Поток остановлен."
                    )
                    break

            if self.running_tasks:
                done, pending = await asyncio.wait(
                    self.running_tasks, return_when=asyncio.FIRST_COMPLETED
                )
                self.running_tasks = list(pending)

                for task in done:
                    completed_contract = self.task_contract_map.pop(task)

                    if completed_contract.status == "COMPLETED":
                        self._distribute_data(completed_contract)
                    elif completed_contract.status == "FAILED":
                        logger.error(
                            f"Процесс остановлен из-за ошибки в контракте '{completed_contract.name}'."
                        )
                        return

            await asyncio.sleep(0.1)

        logger.info("ПОТОК ЗАВЕРШЕН.")
