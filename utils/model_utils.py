from datetime import datetime, date, time
import uuid
from enum import Enum
from decimal import Decimal
import re


def serialize_model(instance):
    def parse_array(value):
        """Converts PostgreSQL array string representation to a Python list"""
        if (
            isinstance(value, list)
            and len(value) == 1
            and isinstance(value[0], str)
            and "," in value[0]
        ):
            return [item.strip().strip('"') for item in value[0].split(",")]
        return value

    def convert_value(value):
        """Handles datetime, UUID, Enums, and PostgreSQL arrays correctly"""
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()  # ✅ Convert datetime to ISO format
        elif isinstance(value, uuid.UUID):
            return str(value)  # ✅ Convert UUID to string
        elif isinstance(value, Enum):
            return value.value  # ✅ Convert Enum to string
        elif isinstance(value, Decimal):  # 👈 Add this line
            return float(value)
        return parse_array(value)

    if isinstance(instance, dict):
        # Already a dict, just convert values
        return {
            key: convert_value(value)
            for key, value in instance.items()
            if not key.startswith("_")
        }
    elif hasattr(instance, "__dict__"):
        return {
            key: convert_value(value)
            for key, value in instance.__dict__.items()
            if not key.startswith("_")
        }
    else:
        # Fallback: return as-is
        return instance


# ----------------------------------------------


def slugify(value: str) -> str:
    """
    Converts a string to a slug:
    - Lowercases the string
    - Removes non-alphanumeric characters (excluding spaces and hyphens)
    - Replaces spaces and multiple hyphens with single hyphens
    """
    value = value.lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s-]+", "-", value)
    value = value.strip("-")
    return value


# ----------------------------------------------


def to_safe_for_db(obj):
    """Recursively make any payload object JSON-safe before DB insert."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):  # Pydantic v2
        return {k: to_safe_for_db(v) for k, v in obj.model_dump().items()}
    if hasattr(obj, "dict"):  # Pydantic v1
        return {k: to_safe_for_db(v) for k, v in obj.dict().items()}
    if isinstance(obj, list):
        return [to_safe_for_db(v) for v in obj]
    if isinstance(obj, dict):
        return {k: to_safe_for_db(v) for k, v in obj.items()}
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Decimal):
        return float(obj)
    return obj
