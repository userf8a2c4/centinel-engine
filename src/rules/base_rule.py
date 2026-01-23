"""Base rule class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple


class BaseRule(ABC):
    """Base class for integrity rules."""

    name = "base"

    def __init__(self, params: Dict[str, Any]) -> None:
        self.params = params

    @abstractmethod
    def evaluate(
        self,
        previous_data: Optional[Dict[str, Any]],
        current_data: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        """Evaluate the rule against current/previous data."""
