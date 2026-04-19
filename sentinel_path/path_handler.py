"""
Module for handling and validating file paths.
This acts as a pre-processing filter to ensure paths are clean and accessible
before any heavy analysis begins.
"""

import os
from pathlib import Path
from typing import Union


def clean_path(raw_path: Union[str, Path]) -> Path:
    """
    Normalizes the path string to handle cross-platform differences.
    
    Why: Different operating systems use different path separators (e.g., / vs \\).
    By converting to a Path object and using resolve(), we ensure the path is
    interpreted correctly regardless of where the config originated.
    
    Business result: Prevents 'File Not Found' errors when moving projects between Windows and Linux.
    """
    if isinstance(raw_path, str):
        # We replace backslashes to handle Windows-style paths on Unix-like systems
        # if they were hardcoded in a configuration file.
        raw_path = raw_path.replace("\\", "/")
    
    return Path(raw_path).expanduser().resolve()


def validate_access(path: Path, mode: int = os.R_OK) -> bool:
    """
    Checks if the current user has the required permissions for the given path.
    
    Why: Using os.access allows us to fail fast if the input files are not readable
    or the output directory is not writable, instead of crashing deep in the logic.
    
    Note: Currently does not support UNC paths (network shares). This is a known
    limitation for future refactoring.
    
    Business result: Provides clear, early warnings about permission issues,
    saving execution time and improving user experience.
    """
    if not path.exists():
        return False
    
    return os.access(path, mode)
