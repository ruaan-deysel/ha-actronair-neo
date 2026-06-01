"""Pure deep-merge helper for applying realtime status deltas."""

from __future__ import annotations

from typing import Any, cast


def deep_merge(base: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    """
    Return a new dict with ``delta`` deep-merged onto ``base``.

    Nested dicts merge recursively; any non-dict value (including lists) in
    ``delta`` replaces the corresponding value in ``base`` wholesale. Inputs
    are not mutated.
    """
    result: dict[str, Any] = dict(base)
    for key, delta_value in delta.items():
        base_value = result.get(key)
        if isinstance(base_value, dict) and isinstance(delta_value, dict):
            result[key] = deep_merge(
                cast("dict[str, Any]", base_value),
                cast("dict[str, Any]", delta_value),
            )
        else:
            result[key] = delta_value
    return result
