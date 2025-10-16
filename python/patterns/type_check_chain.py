"""
Паттерн "Цепочка ответственности":

        Основная функция execute_check_type берет список обработчиков
        (handlers = [is_int, is_float, is_string]) и передает им одни и те же данные ("One").
        Обработка происходит последовательно. Как только один обработчик (is_int или is_float)
        возвращает "успех" (т.е. ненулевое значение), цикл прерывается (break).
        Это позволяет системе попробовать различные способы обработки данных
        (в данном случае, попытки преобразования) до тех пор, пока один из них не сработает.
"""


def is_int(value: str) -> int | None:
    """Проверяет, является ли строка числом."""
    try:
        return int(value)
    except ValueError:
        return None


def is_string(value: str) -> str | None:
    """Проверяет, является ли строка строкой."""
    return value if isinstance(value, str) else None


def is_float(value: str) -> float | None:
    """Проверяет, является ли строка числом с плавающей запятой."""
    try:
        return float(value)
    except ValueError:
        return None


def execute_check_type(handlers: list[callable], *args, **kwargs) -> None:

    if not handlers:
        print("Handlers list is empty")
        return

    try:
        for handler in handlers:
            if handler(*args, **kwargs):
                break
    except ValueError as ve:
        print(f"Type is not available: {ve}")


handlers = [is_int, is_float, is_string]

execute_check_type(handlers, "One")
