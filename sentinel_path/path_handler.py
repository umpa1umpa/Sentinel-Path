"""Утилиты для нормализации и проверки пользовательских путей."""

import os
from pathlib import Path
from typing import Union


def clean_path(raw_path: Union[str, Path]) -> Path:
    """Приводит путь к каноничному виду перед чтением/записью файлов."""
    if isinstance(raw_path, str):
        # Частый edge case: путь копируют из Windows-конфига и запускают в другой ОС.
        # Нормализация слешей снижает риск ложного "file not found".
        raw_path = raw_path.replace("\\", "/")

    # Важно учитывать: пустая строка после resolve() укажет на текущую директорию.
    # Это удобно для CLI-скриптов, но вызывающий код должен явно решать,
    # считать ли такое поведение допустимым.
    return Path(raw_path).expanduser().resolve()


def validate_access(path: Path, mode: int = os.R_OK) -> bool:
    """Проверяет доступ к пути до запуска тяжелых вычислений."""
    if not path.exists():
        return False

    # Проверяем доступ заранее: это решает проблему поздних ошибок в середине пайплайна,
    # когда пользователь уже подождал расчет и только потом получил отказ ОС.
    return os.access(path, mode)
