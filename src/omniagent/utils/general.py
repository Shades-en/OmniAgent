from uuid import uuid4
import json
import os
import secrets
from datetime import datetime
from typing import Any
import tiktoken
from bson import ObjectId

# Cached encoder instance
_tiktoken_encoder: tiktoken.Encoding | None = None

# URL-safe alphabet for nanoid (same as AI SDK)
_NANOID_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"

def _generate_nanoid(length: int = 21) -> str:
    """
    Generate a nanoid-style ID using cryptographically secure random generation.
    Uses the same URL-safe alphabet as Vercel AI SDK: A-Za-z0-9_-
    
    Args:
        length: Length of the ID (default 21, matching nanoid default)
    
    Returns:
        A URL-safe random string ID
    
    Example:
        >>> _generate_nanoid(16)
        'kAANsGIQ6xRJp4Zc'
    """
    return ''.join(secrets.choice(_NANOID_ALPHABET) for _ in range(length))

def generate_id(length: int = 8, id_type: str = "uuid") -> str:
    """
    Generate a unique ID with specified length and type.
    
    Args:
        length: Length of the ID
        id_type: Type of ID to generate:
            - "mongodb": MongoDB-compatible ObjectId (24 chars, ignores length param)
            - "nanoid": AI SDK-style nanoid using URL-safe chars (A-Za-z0-9_-)
            - "uuid": UUID hex string truncated to specified length (default)
    
    Returns:
        Generated ID string
    
    Examples:
        >>> generate_id(24, "mongodb")  # MongoDB ObjectId
        '507f1f77bcf86cd799439011'
        >>> generate_id(16, "nanoid")   # AI SDK style
        'kAANsGIQ6xRJp4Zc'
        >>> generate_id(8, "uuid")      # Regular UUID
        'a3f5c8d1'
    """
    if id_type == "mongodb":
        return str(ObjectId())
    elif id_type == "nanoid":
        return _generate_nanoid(length)
    else:  # uuid (default)
        return uuid4().hex[:length]

def get_env_int(name: str, default: int | None = None) -> int | None:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    try:
        return int(v)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {v!r}")

def _env_flag(name: str, default: bool = False) -> bool:
    """Parse boolean-like environment flags.

    Accepts true values: '1', 'true', 'yes', 'on' (case-insensitive). False for others or unset.
    """
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _load_json_string_map(env_key: str, default: dict[str, str]) -> dict[str, str]:
    """Load a JSON object from env and validate it as str->str mapping."""
    raw_value = os.getenv(env_key)
    if not raw_value:
        return dict(default)

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{env_key} must be valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"{env_key} must be a JSON object mapping strings to strings")

    normalized: dict[str, str] = {}
    for key, value in parsed.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError(f"{env_key} keys and values must be strings")
        normalized[key] = value
    return normalized


def _load_json_dict(env_key: str) -> dict[str, object]:
    """Load a JSON object from env and validate it as dict."""
    raw_value = os.getenv(env_key, "")
    if not raw_value:
        return {}

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{env_key} must be valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"{env_key} must be a JSON object")
    return parsed

def get_token_count(text: str) -> int:
    """Count tokens in text using tiktoken encoder for BASE_MODEL."""
    from omniagent.config import BASE_MODEL
    
    global _tiktoken_encoder
    if _tiktoken_encoder is None:
        _tiktoken_encoder = tiktoken.encoding_for_model(BASE_MODEL)
    return len(_tiktoken_encoder.encode(text))


def iso_or_empty(value: Any) -> str:
    """Return ISO-8601 string for datetime values, otherwise empty string."""
    if isinstance(value, datetime):
        return value.isoformat()
    return ""

__all__ = [
    "generate_id", 
    "get_env_int", 
    "_env_flag",
    "_load_json_string_map",
    "_load_json_dict",
    "get_token_count",
    "iso_or_empty",
]
