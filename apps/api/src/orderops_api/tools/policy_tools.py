from __future__ import annotations

from time import perf_counter
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from orderops_api.core.config import get_settings
from orderops_api.rag.search import PolicySearchResult, search_policy
from orderops_api.tools.logging import ToolError, elapsed_ms, try_insert_tool_call_log


ToolStatus = Literal["success", "error"]


class PolicySearchInput(BaseModel):
    query: str = Field(min_length=1)
    doc_types: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)
    rerank: bool = True
    trace_id: str | None = None


class PolicyCitation(BaseModel):
    doc_id: str
    section_id: str
    score: float
    title: str
    text: str
    source_path: str
    risk_level: str

    @computed_field
    @property
    def ref(self) -> str:
        if self.section_id.startswith(f"{self.doc_id}#"):
            return self.section_id
        return f"{self.doc_id}#{self.section_id}"


class PolicySearchOutput(BaseModel):
    status: ToolStatus
    query: str
    results: list[PolicyCitation] = Field(default_factory=list)
    error: ToolError | None = None


def policy_result_to_citation(result: PolicySearchResult) -> PolicyCitation:
    return PolicyCitation(
        doc_id=result.doc_id,
        section_id=result.section_id,
        score=result.score,
        title=result.title,
        text=result.text,
        source_path=result.source_path,
        risk_level=result.risk_level,
    )


def matches_doc_types(result: PolicySearchResult, doc_types: list[str]) -> bool:
    if not doc_types:
        return True
    return any(result.doc_id == doc_type or result.doc_id.startswith(f"{doc_type}_") for doc_type in doc_types)


def search_policy_tool(request: PolicySearchInput) -> PolicySearchOutput:
    settings = get_settings()
    started_at = perf_counter()
    try:
        retrieval_k = request.top_k * 4 if request.doc_types else request.top_k
        raw_results = search_policy(
            request.query,
            top_k=retrieval_k,
            rerank=request.rerank,
        )
        citations = [
            policy_result_to_citation(result)
            for result in raw_results
            if matches_doc_types(result, request.doc_types)
        ][: request.top_k]
        result = PolicySearchOutput(
            status="success",
            query=request.query,
            results=citations,
        )
        try_insert_tool_call_log(
            settings.database_url,
            trace_id=request.trace_id,
            tool_name="search_policy",
            args=request,
            result=result,
            status=result.status,
            latency_ms=elapsed_ms(started_at),
        )
        return result
    except Exception as exc:
        result = PolicySearchOutput(
            status="error",
            query=request.query,
            error=ToolError(code=exc.__class__.__name__, message=str(exc)),
        )
        try_insert_tool_call_log(
            settings.database_url,
            trace_id=request.trace_id,
            tool_name="search_policy",
            args=request,
            result=result,
            status=result.status,
            latency_ms=elapsed_ms(started_at),
            error_type=exc.__class__.__name__,
        )
        return result
