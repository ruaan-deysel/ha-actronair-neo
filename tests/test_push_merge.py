"""Tests for the push delta deep-merge helper."""

from __future__ import annotations

from custom_components.actronair_neo.api.push.merge import deep_merge


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
