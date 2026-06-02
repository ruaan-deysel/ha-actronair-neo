"""Tests for the push delta deep-merge helper."""

from __future__ import annotations

from custom_components.actronair_neo.api.push.merge import (
    apply_event_paths,
    deep_merge,
)


def test_apply_event_paths_nested_dict():
    state = {"UserAirconSettings": {"Mode": "HEAT", "isOn": True}}
    event = {"type": "status-change-broadcast", "UserAirconSettings.Mode": "COOL"}
    out = apply_event_paths(state, event)
    assert out["UserAirconSettings"]["Mode"] == "COOL"
    assert out["UserAirconSettings"]["isOn"] is True  # sibling preserved


def test_apply_event_paths_list_index():
    state = {"RemoteZoneInfo": [{"LiveTemp_oC": 20.0}, {"LiveTemp_oC": 21.0}]}
    out = apply_event_paths(state, {"RemoteZoneInfo[1].LiveTemp_oC": 26.0})
    assert out["RemoteZoneInfo"][1]["LiveTemp_oC"] == 26.0
    assert out["RemoteZoneInfo"][0]["LiveTemp_oC"] == 20.0  # other zone preserved


def test_apply_event_paths_deeply_nested():
    state = {"LiveAircon": {"OutdoorUnit": {"RoomTemp": 25.0}}}
    out = apply_event_paths(state, {"LiveAircon.OutdoorUnit.RoomTemp": 26.9})
    assert out["LiveAircon"]["OutdoorUnit"]["RoomTemp"] == 26.9


def test_apply_event_paths_extends_list_when_index_missing():
    out = apply_event_paths({}, {"RemoteZoneInfo[2].LiveTemp_oC": 22.5})
    assert out["RemoteZoneInfo"][2]["LiveTemp_oC"] == 22.5
    assert len(out["RemoteZoneInfo"]) == 3


def test_apply_event_paths_ignores_type_and_does_not_mutate():
    state = {"UserAirconSettings": {"Mode": "HEAT"}}
    event = {"type": "status-change-broadcast", "UserAirconSettings.Mode": "COOL"}
    apply_event_paths(state, event)
    assert state["UserAirconSettings"]["Mode"] == "HEAT"  # input untouched
    assert "type" not in apply_event_paths(state, event)


def test_nested_merge_preserves_siblings():
    base = {"a": {"x": 1, "y": 2}, "b": 9}
    delta = {"a": {"y": 20, "z": 30}}
    assert deep_merge(base, delta) == {"a": {"x": 1, "y": 20, "z": 30}, "b": 9}


def test_scalar_overwrite_and_new_key():
    assert deep_merge({"a": 1}, {"a": 2, "b": 3}) == {"a": 2, "b": 3}


def test_lists_replaced_wholesale():
    base = {"zones": [True, True, False]}
    delta = {"zones": [False]}
    assert deep_merge(base, delta) == {"zones": [False]}


def test_empty_delta_is_noop():
    base = {"a": {"x": 1}}
    assert deep_merge(base, {}) == {"a": {"x": 1}}


def test_merge_into_empty_base():
    assert deep_merge({}, {"a": {"x": 1}}) == {"a": {"x": 1}}


def test_inputs_not_mutated():
    base = {"a": {"x": 1}}
    delta = {"a": {"y": 2}}
    deep_merge(base, delta)
    assert base == {"a": {"x": 1}}
    assert delta == {"a": {"y": 2}}
