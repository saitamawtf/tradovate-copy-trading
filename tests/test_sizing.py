import pytest

from backend.copy.sizing import SizingContext, compute_follower_qty


def test_fixed_mode_returns_value():
    assert compute_follower_qty("fixed", 3, SizingContext(leader_qty=5)) == 3


def test_fixed_mode_zero_when_leader_flat():
    assert compute_follower_qty("fixed", 3, SizingContext(leader_qty=0)) == 0


def test_ratio_mode_multiplies():
    assert compute_follower_qty("ratio", 2.0, SizingContext(leader_qty=3)) == 6


def test_ratio_mode_rounds_up_to_min_one():
    # ratio < 1 but leader has position -> min 1
    assert compute_follower_qty("ratio", 0.2, SizingContext(leader_qty=1)) == 1


def test_equity_scaled_uses_ratio():
    qty = compute_follower_qty(
        "equity_scaled",
        1.0,
        SizingContext(leader_qty=4, leader_equity=50000, follower_equity=25000),
    )
    assert qty == 2


def test_equity_scaled_falls_back_without_equity():
    qty = compute_follower_qty(
        "equity_scaled", 1.0, SizingContext(leader_qty=3)
    )
    assert qty == 3


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        compute_follower_qty("magic", 1.0, SizingContext(leader_qty=1))  # type: ignore[arg-type]
