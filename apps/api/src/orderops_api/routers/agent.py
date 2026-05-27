from fastapi import APIRouter

from orderops_api.agent.graph import run_agent
from orderops_api.agent.state import AgentRunInput, AgentRunOutput


router = APIRouter(tags=["agent"])


@router.post("/api/agent/run", response_model=AgentRunOutput)
def agent_run(request: AgentRunInput) -> AgentRunOutput:
    return run_agent(request)


@router.post("/api/chat", response_model=AgentRunOutput)
def chat(request: AgentRunInput) -> AgentRunOutput:
    return run_agent(request)
