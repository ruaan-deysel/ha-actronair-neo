"""Pure helpers for applying realtime status deltas."""

from __future__ import annotations

import copy
import re
from typing import Any, cast

# A single path segment: a key with an optional [index], e.g. "RemoteZoneInfo[0]".
_PATH_SEGMENT = re.compile(r"^([^\[\]]+)(?:\[(\d+)\])?$")


def apply_event_paths(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """
    Apply an Actron ``status-change-broadcast`` event onto a copy of ``state``.

    The broker sends incremental changes as flattened path → value pairs, e.g.::

        {"type": "status-change-broadcast",
         "UserAirconSettings.Mode": "COOL",
         "RemoteZoneInfo[0].LiveTemp_oC": 24.2}

    Each path is split into nested dict keys and ``[index]`` list positions and
    written into a deep copy of ``state`` (so the input is not mutated). The
    ``type`` marker and any unparseable path are ignored. Lists are extended
    with empty dicts when an index is beyond the current length.
    """
    result = copy.deepcopy(state)
    for path, value in event.items():
        if path == "type":
            continue
        _set_path(result, path, value)
    return result


def _set_path(root: dict[str, Any], path: str, value: Any) -> None:
    """Write ``value`` into ``root`` at a flattened ``path`` like ``a.b[2].c``."""
    parts = path.split(".")
    cur: Any = root
    for i, part in enumerate(parts):
        match = _PATH_SEGMENT.match(part)
        if not match or not isinstance(cur, dict):
            return  # unparseable segment or type mismatch — skip safely
        key, raw_index = match.group(1), match.group(2)
        is_last = i == len(parts) - 1

        if raw_index is None:
            if is_last:
                cur[key] = value
                return
            nxt = cur.get(key)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[key] = nxt
            cur = nxt
        else:
            index = int(raw_index)
            lst = cur.get(key)
            if not isinstance(lst, list):
                lst = []
                cur[key] = lst
            while len(lst) <= index:
                lst.append({})
            if is_last:
                lst[index] = value
                return
            if not isinstance(lst[index], dict):
                lst[index] = {}
            cur = lst[index]


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
