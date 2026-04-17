from dataclasses import dataclass
from typing import Literal

SizeMode = Literal["fixed", "ratio", "equity_scaled"]


@dataclass
class SizingContext:
    leader_qty: int
    leader_equity: float | None = None
    follower_equity: float | None = None


def compute_follower_qty(
    mode: SizeMode,
    value: float,
    ctx: SizingContext,
) -> int:
    """Compute the quantity the follower should use.

    - fixed: always ``value`` contracts.
    - ratio: ``leader_qty * value`` (rounded, min 1 if leader has a position).
    - equity_scaled: ``leader_qty * (follower_equity / leader_equity) * value``.
    """
    if ctx.leader_qty <= 0:
        return 0
    if mode == "fixed":
        return max(0, int(round(value)))
    if mode == "ratio":
        out = ctx.leader_qty * value
        return max(1, int(round(out))) if out > 0 else 0
    if mode == "equity_scaled":
        if not ctx.leader_equity or ctx.leader_equity <= 0:
            return max(1, int(round(ctx.leader_qty * value)))
        fe = ctx.follower_equity or ctx.leader_equity
        scale = fe / ctx.leader_equity
        out = ctx.leader_qty * scale * value
        return max(1, int(round(out))) if out > 0 else 0
    raise ValueError(f"unknown size mode: {mode}")
