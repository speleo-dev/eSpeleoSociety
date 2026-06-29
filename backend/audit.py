from dataclasses import dataclass


@dataclass(frozen=True)
class AuditEvent:
    request_id: str
    method: str
    route: str
    status_code: int
    subject: str
    roles: tuple[str, ...]
    outcome: str
    error_code: str | None = None
