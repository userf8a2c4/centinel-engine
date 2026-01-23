"""Rule checking large changes between snapshots."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .base_rule import BaseRule


class ChangeThresholdRule(BaseRule):
    """Detects large changes in total votes between snapshots."""

    name = "change_threshold"

    def evaluate(
        self,
        previous_data: Optional[Dict[str, Any]],
        current_data: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        if not previous_data:
            return "pass", {"message": "No previous snapshot to compare."}

        previous_total = (previous_data.get("totals") or {}).get("total_votes", 0)
        current_total = (current_data.get("totals") or {}).get("total_votes", 0)
        if previous_total == 0:
            return "warn", {"message": "Previous total votes are zero."}

        change_pct = abs(current_total - previous_total) / previous_total * 100
        threshold = float(self.params.get("relative_vote_change_pct", 15))
        status = "pass" if change_pct <= threshold else "fail"
        return (
            status,
            {
                "previous_total": previous_total,
                "current_total": current_total,
                "change_pct": round(change_pct, 2),
                "threshold": threshold,
            },
        )
