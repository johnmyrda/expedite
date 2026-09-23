"""Tests for reusable classic-interface behavior."""

from expedite.pages.classic_ui import adjacent_list_value


def test_adjacent_list_value_starts_at_the_requested_end() -> None:
    values = [10, 20, 30]

    assert adjacent_list_value(values, None, 1) == 10
    assert adjacent_list_value(values, None, -1) == 30


def test_adjacent_list_value_moves_and_clamps() -> None:
    values = [10, 20, 30]

    assert adjacent_list_value(values, 20, 1) == 30
    assert adjacent_list_value(values, 20, -1) == 10
    assert adjacent_list_value(values, 30, 1) == 30
    assert adjacent_list_value(values, 10, -1) == 10


def test_adjacent_list_value_handles_missing_and_empty_selections() -> None:
    assert adjacent_list_value([10, 20, 30], 99, 1) == 10
    assert adjacent_list_value([10, 20, 30], 99, -1) == 30
    assert adjacent_list_value([], None, 1) is None
