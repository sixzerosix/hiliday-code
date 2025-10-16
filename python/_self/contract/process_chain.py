import uuid


# Контракт как обязательство которое должно быть выполнено
class Contract:
    """Represents a contract in the process chain."""

    def __init__(self, dependencies: list["Dependency"] | None = None) -> None:
        self.id = uuid.uuid4()
        self.input = {}  # Input data
        self.output = {}  # Output data

        self.dependencies = dependencies  # Relation to other contracts


# Зависимости ответственны за отношения между контрактами
class Dependency:
    """Represents a dependency between contracts."""

    def __init__(self, contract: Contract) -> None:
        self.contract = contract


# Цепочка ответственна только за выполнение последовательности
class Chain:
    """Represents a chain of contracts in the process."""

    def __init__(self, contracts: list[Contract]) -> None:
        self.contracts = contracts


# Процесс цепочки ответственен за управление всей цепочкой
class ProcessChain:
    """Represents the entire process chain."""

    def __init__(self, chains: list[Chain]) -> None:
        self.chains = chains


class Flow:
    """Represents the flow of data between contracts in the process."""

    def __init__(self, process_chain: ProcessChain) -> None:
        self.process_chain = process_chain
        self.data = {}


contract1 = Contract()
dependency = Dependency(contract1)
contract2 = Contract(dependencies=[dependency])
