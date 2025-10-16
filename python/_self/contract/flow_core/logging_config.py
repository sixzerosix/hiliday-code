# flow_core_project/flow_core/logging_config.py

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_to_console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """
    Настраивает централизованное логирование для Flow Core.

    Args:
        log_level (str): Минимальный уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file (Optional[str]): Путь к файлу для логирования. Если None, логи в файл не записываются.
        log_to_console (bool): Если True, логи также выводятся в консоль.
        max_bytes (int): Максимальный размер файла лога перед ротацией (в байтах).
        backup_count (int): Количество резервных файлов логов для хранения.
    """
    logger = logging.getLogger("flow_core")
    logger.setLevel(log_level.upper())

    if not logger.handlers:  # Предотвращаем дублирование обработчиков
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        if log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            file_handler = RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    logger.info(f"Логирование Flow Core настроено на уровень: {log_level.upper()}")
    if log_file:
        logger.info(f"Логи записываются в файл: {log_file}")
    if log_to_console:
        logger.info("Логи выводятся в консоль.")
