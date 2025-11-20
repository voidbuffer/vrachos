"""Utilities useful for working with time and date."""

from datetime import UTC, datetime


def utc_2_iso(timestamp: datetime | None = None) -> str:
    """
    Convert a datetime to ISO 8601 format with microseconds and Z suffix (UTC).

    If no timestamp is provided, use current UTC time.
    """
    if timestamp is None:
        timestamp = datetime.now(UTC)
    elif timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    else:
        timestamp = timestamp.astimezone(UTC)
    return timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z")


def iso_2_utc(iso_str: str | None = None) -> datetime:
    """
    Convert an ISO 8601 string with Z suffix to UTC datetime.

    If no string is provided, return current UTC datetime.
    """
    if iso_str is None:
        return datetime.now(UTC)

    # Remove 'Z' suffix if present
    dt = datetime.fromisoformat(iso_str.rstrip("Z"))

    # Ensure UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)

    return dt
