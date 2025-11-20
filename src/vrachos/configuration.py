"""Support for configuration operations."""

import json
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, ValidationError

from .logger import logger


class _ConfigurationEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for configuration objects.

    Handles serialization of common types like Path, Decimal, datetime, Enum,
    set, frozenset, bytes, and custom objects with __dict__ attributes.

    Examples:
        >>> json.dumps(
        ...     {"path": Path("/home/user")},
        ...     cls=_ConfigurationEncoder
        ... )
        '{"path": "/home/user"}'
    """

    def default(self, obj: Any) -> Any:
        """
        Encode objects not natively JSON serializable.

        Args:
            obj: Object to encode.

        Returns:
            JSON-serializable representation of obj.
        """
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, (set, frozenset)):
            return list(obj)
        if hasattr(obj, "__dict__"):
            return obj.__dict__

        return super().default(obj)


class Configuration(BaseModel):
    """
    Base configuration class with JSON file persistence and validation.

    Provides load/save functionality with automatic validation, atomic writes,
    and comprehensive error handling. Subclasses must define a FILEPATH
    class variable pointing to a JSON configuration file.

    The class merges defaults with loaded data, ensuring missing nested values
    are preserved. Uses Pydantic for validation and serialization.

    Attributes:
        FILEPATH: Class variable defining the path to the JSON config file.
                 Must be set by subclasses.

    Example:
        >>> class AppConfig(Configuration):
        ...     FILEPATH = Path("config.json")
        ...     debug: bool = False
        ...     timeout: int = 30
        >>>
        >>> config = AppConfig()
        >>> config.load()  # Load from file or create with defaults
        >>> config.debug = True
        >>> config.save()  # Atomically write to file
    """

    FILEPATH: ClassVar[Path]

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        json_encoders = {Path: str}

    def __init__(self, **data: Any) -> None:
        """Initialize configuration and validate FILEPATH setup."""
        super().__init__(**data)
        self._validate_filepath()

    @classmethod
    def _validate_filepath(cls) -> None:
        """Validate that FILEPATH is properly configured."""
        if not hasattr(cls, "FILEPATH"):
            raise ValueError(
                f"{cls.__name__} must define a FILEPATH class variable"
            )
        if not isinstance(cls.FILEPATH, Path):
            raise TypeError(
                f"FILEPATH must be a Path object, got {type(cls.FILEPATH)}"
            )

    def load(self) -> None:
        """Load configuration from JSON file and update self in-place."""
        try:
            if not self.FILEPATH.exists():
                logger.info(
                    f"Config file not found at {self.FILEPATH},"
                    " creating with defaults"
                )
                self.save()
                return

            # Read and parse JSON with error handling
            try:
                raw_data = self.FILEPATH.read_text(encoding="utf-8")
                loaded_data = json.loads(raw_data)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in config file: {e}")
                raise ValueError(
                    f"Config file contains invalid JSON: {e}"
                ) from e
            except UnicodeDecodeError as e:
                logger.error(f"Config file has encoding issues: {e}")
                raise ValueError(f"Config file encoding error: {e}") from e

            if not isinstance(loaded_data, dict):
                raise ValueError(
                    f"Config file must contain a JSON object,"
                    f" got {type(loaded_data).__name__}"
                )

            # Merge defaults with loaded data
            merged = self.model_dump()
            merged.update(loaded_data)

            # Validate and update
            try:
                validated_obj = self.__class__.model_validate(merged)
            except ValidationError as e:
                logger.error(f"Config validation failed: {e}")
                raise ValueError(f"Config validation failed: {e}") from e

            # Update self in-place
            for field_name in self.model_fields:
                setattr(self, field_name, getattr(validated_obj, field_name))

            logger.info(
                f"Configuration loaded successfully from {self.FILEPATH}"
            )

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def save(self) -> None:
        """Save configuration to JSON file with atomic write."""
        try:
            # Validate file format
            if self.FILEPATH.suffix.lower() != ".json":
                raise ValueError(
                    f"Unsupported config format: {self.FILEPATH.suffix}. "
                    f"Only .json files are supported."
                )

            # Create parent directories
            self.FILEPATH.parent.mkdir(parents=True, exist_ok=True)

            # Prepare data with custom encoder
            data = self.model_dump(
                exclude_unset=False,
                exclude_none=False,
            )
            json_str = (
                json.dumps(
                    data,
                    cls=_ConfigurationEncoder,
                    indent=4,
                    ensure_ascii=False,
                )
                + "\n"
            )

            # Atomic write: write to temp file first, then rename
            temp_file = self.FILEPATH.with_suffix(
                self.FILEPATH.suffix + ".tmp"
            )
            temp_file.write_text(json_str, encoding="utf-8")
            temp_file.replace(self.FILEPATH)

            logger.info(f"Configuration saved to {self.FILEPATH}")

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    def to_dict(self) -> dict[str, Any]:
        """Export configuration as a dictionary."""
        return self.model_dump(
            exclude_unset=False,
            exclude_none=False,
        )

    def to_json(self) -> str:
        """Export configuration as a formatted JSON string."""
        data = self.model_dump(
            exclude_unset=False,
            exclude_none=False,
        )
        return json.dumps(
            data,
            cls=_ConfigurationEncoder,
            indent=4,
            ensure_ascii=False,
        )
