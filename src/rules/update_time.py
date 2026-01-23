"""Expected update time rule."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from .base_rule import BaseRule


class UpdateTimeRule(BaseRule):
    """Checks whether snapshot timestamp aligns with expected hours."""

    name = "update_time"

    def evaluate(
        self,
        previous_data: Optional[Dict[str, Any]],
        current_data: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        allowed_hours = self.params.get("allowed_hours", [])
        timestamp = (current_data.get("meta") or {}).get("timestamp_utc")
        if not timestamp:
            return "warn", {"message": "Missing timestamp in snapshot."}

        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return "warn", {"message": "Invalid timestamp format."}

        hour = parsed.hour
        status = "pass" if hour in allowed_hours else "warn"
        return (
            status,
            {
                "hour": hour,
                "allowed_hours": allowed_hours,
            },
        )
