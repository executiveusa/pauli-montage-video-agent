"""Cross-transport problem contracts for YAPPY-CLIPZ actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ActionProblem(Exception):
    code: str
    message: str
    status: int = 400
    retryable: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message

    def document(self, *, request_id: str, correlation_id: str) -> dict[str, Any]:
        return {
            "contractVersion": "1.0.0",
            "requestId": request_id,
            "correlationId": correlation_id,
            "error": {
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
                "status": self.status,
                "details": self.details,
            },
        }
