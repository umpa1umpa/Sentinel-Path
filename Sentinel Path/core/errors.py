"""Custom exceptions for Sentinel Path."""


class GraphTopologyError(Exception):
    """Raised when graph topology is invalid."""


class CycleError(GraphTopologyError):
    """Raised when cyclic dependencies are found."""


class ValidationWarning(Exception):
    """Raised for validation warnings in strict mode workflows."""
