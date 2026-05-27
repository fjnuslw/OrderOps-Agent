from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from orderops_api.evaluation.metrics import EvalRunReport
from orderops_api.evaluation.runner import run_eval


class EvalRunRequest(BaseModel):
    cases_path: str = "data/eval/eval_cases_seed.csv"
    reports_dir: str = "reports/eval"
    case_ids: list[str] = Field(default_factory=list)
    case_limit: int | None = Field(default=None, ge=1)
    live_llm: bool = False
    allow_writes: bool = False
    write_reports: bool = False


router = APIRouter(prefix="/api/evals", tags=["evals"])


@router.post("/run", response_model=EvalRunReport)
def run_evals(request: EvalRunRequest) -> EvalRunReport:
    try:
        return run_eval(
            cases_path=Path(request.cases_path),
            reports_dir=Path(request.reports_dir),
            live_llm=request.live_llm,
            allow_writes=request.allow_writes,
            case_ids=set(request.case_ids),
            case_limit=request.case_limit,
            write_reports=request.write_reports,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
