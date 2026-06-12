"""Configuration error type for fail-fast validation."""


class ConfigError(ValueError):
    """Raised when the assembled configuration is invalid."""
