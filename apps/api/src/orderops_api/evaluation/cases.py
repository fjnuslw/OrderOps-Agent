from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    case_id: str = Field(min_length=1)
    scenario: str = Field(min_length=1)
    user_role: Literal["customer", "agent", "ops_admin"] = "agent"
    message: str = Field(min_length=1)
    order_id: str | None = None
    seller_id: str | None = None
    request_at: datetime | None = None
    auto_create_ticket: bool = False
    expected_intent: str = ""
    expected_tools: list[str] = Field(default_factory=list)
    expected_decision: str | None = None
    expected_approval_required: bool | None = None
    expected_risk_level: str | None = None
    expected_citations: list[str] = Field(default_factory=list)
    expected_blocked: bool | None = None
    metric_tags: list[str] = Field(default_factory=list)


def load_eval_cases(path: Path) -> list[EvalCase]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return [parse_eval_case(row) for row in reader]


def parse_eval_case(row: dict[str, str]) -> EvalCase:
    return EvalCase(
        case_id=required(row, "case_id"),
        scenario=required(row, "scenario"),
        user_role=(row.get("user_role") or "agent").strip() or "agent",
        message=required(row, "message"),
        order_id=optional_text(row.get("order_id")),
        seller_id=optional_text(row.get("seller_id")),
        request_at=parse_datetime(row.get("request_at")),
        auto_create_ticket=parse_bool(row.get("auto_create_ticket"), default=False),
        expected_intent=(row.get("expected_intent") or "").strip(),
        expected_tools=parse_list(row.get("expected_tools")),
        expected_decision=optional_text(row.get("expected_decision")),
        expected_approval_required=parse_optional_bool(row.get("expected_approval_required")),
        expected_risk_level=optional_text(row.get("expected_risk_level")),
        expected_citations=parse_list(row.get("expected_citations")),
        expected_blocked=parse_optional_bool(row.get("expected_blocked")),
        metric_tags=parse_csv_tags(row.get("metric_tags")),
    )


def required(row: dict[str, str], key: str) -> str:
    value = optional_text(row.get(key))
    if value is None:
        raise ValueError(f"Eval case is missing required field: {key}")
    return value


def optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def parse_bool(value: str | None, default: bool) -> bool:
    parsed = parse_optional_bool(value)
    return default if parsed is None else parsed


def parse_optional_bool(value: str | None) -> bool | None:
    text = (value or "").strip().lower()
    if not text:
        return None
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def parse_datetime(value: str | None) -> datetime | None:
    text = optional_text(value)
    if text is None:
        return None
    return datetime.fromisoformat(text)


def parse_list(value: str | None) -> list[str]:
    text = optional_text(value)
    if text is None:
        return []
    return [item.strip() for item in text.split("|") if item.strip()]


def parse_csv_tags(value: str | None) -> list[str]:
    text = optional_text(value)
    if text is None:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]
