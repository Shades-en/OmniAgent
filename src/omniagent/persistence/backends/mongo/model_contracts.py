"""Mongo-specific validation helpers for document model contracts."""

from __future__ import annotations

import inspect
from typing import Any, Iterable

from omniagent.db.mongo import DocumentModels
from omniagent.domain_protocols import MessageProtocol, SessionProtocol, SummaryProtocol, UserProtocol


def _has_model_field(model: type[Any], field_name: str) -> bool:
    model_fields = getattr(model, "model_fields", None)
    if isinstance(model_fields, dict) and field_name in model_fields:
        return True
    return hasattr(model, field_name)


def _validate_model_protocol_contract(model: type[Any], protocol: type[Any], model_name: str) -> None:
    missing_fields = [
        field_name
        for field_name in getattr(protocol, "__annotations__", {})
        if not _has_model_field(model, field_name)
    ]
    missing_methods = [
        method_name
        for method_name, method in protocol.__dict__.items()
        if callable(method) and not method_name.startswith("_") and not callable(getattr(model, method_name, None))
    ]
    if missing_fields or missing_methods:
        missing_parts: list[str] = []
        if missing_fields:
            missing_parts.append(f"fields={missing_fields}")
        if missing_methods:
            missing_parts.append(f"methods={missing_methods}")
        missing_text = ", ".join(missing_parts)
        raise TypeError(
            f"{model_name} does not satisfy {protocol.__name__} contract: {missing_text}"
        )


def validate_document_models(models: DocumentModels) -> None:
    """Validate Mongo document models against domain protocols."""
    _validate_model_protocol_contract(models.user, UserProtocol, "User model")
    _validate_model_protocol_contract(models.session, SessionProtocol, "Session model")
    _validate_model_protocol_contract(models.message, MessageProtocol, "Message model")
    _validate_model_protocol_contract(models.summary, SummaryProtocol, "Summary model")


_REPOSITORY_MODEL_METHOD_CONTRACTS: dict[str, dict[str, dict[str, Any]]] = {
    "User model": {
        "get_by_client_id": {"required_params": ("client_id",)},
        "delete_by_client_id": {"required_params": ("client_id",)},
    },
    "Session model": {
        "get_by_id_and_client_id": {"required_params": ("session_id", "client_id")},
        "get_paginated_by_user_client_id": {"required_params": ("client_id", "page", "page_size")},
        "count_by_user_client_id": {"required_params": ("client_id",)},
        "get_all_by_user_client_id": {"required_params": ("client_id",)},
        "update_name_by_client_id": {"required_params": ("session_id", "name", "client_id")},
        "delete_with_related_by_client_id": {"required_params": ("session_id", "client_id")},
        "delete_all_by_user_client_id": {"required_params": ("client_id",)},
        "to_public_dicts": {"min_params": 1},
    },
    "Message model": {
        "get_paginated_by_session": {"required_params": ("session_id", "page", "page_size")},
        "count_by_session": {"required_params": ("session_id",)},
        "get_all_by_session": {"required_params": ("session_id",)},
        "delete_by_client_message_id_and_client_id": {"required_params": ("client_message_id", "client_id")},
        "to_public_dicts": {"min_params": 1},
    },
    "Summary model": {
        "get_latest_by_session": {"required_params": ("session_id",)},
        "create_with_session": {"required_params": ("session", "summary")},
    },
}


def _validate_method_contract(
    model: type[Any],
    *,
    model_name: str,
    method_name: str,
    required_params: Iterable[str] | None = None,
    min_params: int | None = None,
) -> None:
    method = getattr(model, method_name, None)
    if not callable(method):
        raise TypeError(f"{model_name} repository contract failed: missing method '{method_name}'")

    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            f"{model_name} repository contract failed: could not inspect method '{method_name}': {exc}"
        ) from exc

    params = signature.parameters
    required = tuple(required_params or ())
    missing = [param for param in required if param not in params]
    if missing:
        raise TypeError(
            f"{model_name} repository contract failed: method '{method_name}' missing required params {missing}"
        )

    if min_params is not None:
        explicit_params = [
            parameter
            for parameter in params.values()
            if parameter.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        if len(explicit_params) < min_params:
            raise TypeError(
                f"{model_name} repository contract failed: method '{method_name}' expects at least {min_params} parameter(s)"
            )


def validate_repository_models(models: DocumentModels) -> None:
    """Validate repository-required methods on configured Mongo model classes."""
    model_map = {
        "User model": models.user,
        "Session model": models.session,
        "Message model": models.message,
        "Summary model": models.summary,
    }
    for model_name, method_contracts in _REPOSITORY_MODEL_METHOD_CONTRACTS.items():
        model = model_map[model_name]
        for method_name, contract in method_contracts.items():
            _validate_method_contract(
                model,
                model_name=model_name,
                method_name=method_name,
                required_params=contract.get("required_params"),
                min_params=contract.get("min_params"),
            )

