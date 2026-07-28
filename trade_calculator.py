"""Trade-planning math for the Trade Studio workspace.

Pure functions only — no UI, no network calls — mirroring the separation
already used by scoring.py. There is no automatic technical analysis here
(no support/resistance detection, no entry timing): direction, entry, stop,
and target are all supplied by the user in the UI, and this module only does
the downstream arithmetic (risk/reward, position sizing) plus internal-
consistency validation.
"""

from dataclasses import dataclass, field


@dataclass
class TradePlan:
    direction: str                     # "Long" or "Short" — chosen by the user, not inferred
    risk_per_unit: float                # distance to stop
    reward_per_unit: float              # distance to target
    risk_reward_ratio: float | None
    risk_amount: float
    position_size: float | None        # units/shares
    position_value: float | None
    potential_profit: float | None
    warnings: list = field(default_factory=list)


def plan_trade(
    direction: str, entry: float, stop_loss: float, target: float, account_size: float, risk_pct: float
) -> TradePlan:
    """Compute a full trade plan from user-supplied direction and price levels.

    Direction is an explicit user choice ("Long" or "Short"), not inferred
    from entry vs. target — that is what makes it possible to flag all four
    inconsistent-input cases independently: a Long with its stop on the
    wrong side, a Long with its target on the wrong side, and the mirrored
    two cases for a Short.
    """
    warnings = []

    risk_per_unit = abs(entry - stop_loss)
    reward_per_unit = abs(target - entry)

    if direction == "Long":
        if stop_loss >= entry:
            warnings.append("Long trade: Stop Loss should be below Entry.")
        if target <= entry:
            warnings.append("Long trade: Target should be above Entry.")
    else:
        if stop_loss <= entry:
            warnings.append("Short trade: Stop Loss should be above Entry.")
        if target >= entry:
            warnings.append("Short trade: Target should be below Entry.")

    if risk_per_unit == 0:
        warnings.append("Entry and Stop Loss cannot be equal — risk per unit is zero.")

    risk_reward_ratio = (reward_per_unit / risk_per_unit) if risk_per_unit else None
    risk_amount = account_size * (risk_pct / 100)
    position_size = (risk_amount / risk_per_unit) if risk_per_unit else None
    position_value = (position_size * entry) if position_size is not None else None
    potential_profit = (position_size * reward_per_unit) if position_size is not None else None

    return TradePlan(
        direction=direction,
        risk_per_unit=risk_per_unit,
        reward_per_unit=reward_per_unit,
        risk_reward_ratio=risk_reward_ratio,
        risk_amount=risk_amount,
        position_size=position_size,
        position_value=position_value,
        potential_profit=potential_profit,
        warnings=warnings,
    )
