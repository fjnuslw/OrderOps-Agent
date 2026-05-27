from __future__ import annotations

from argparse import ArgumentParser
import json

from orderops_api.agent.graph import run_agent
from orderops_api.agent.state import AgentRunInput


def main() -> None:
    parser = ArgumentParser(description="Run one local OrderOps Agent workflow case.")
    parser.add_argument("message", help="User message to send to the agent.")
    parser.add_argument("--session-id", default="local-cli-session")
    parser.add_argument("--user-role", choices=["customer", "agent", "ops_admin"], default="agent")
    parser.add_argument("--order-id")
    parser.add_argument("--seller-id")
    parser.add_argument("--request-at", help="Optional ISO datetime for refund review, for example 2018-05-10T00:00:00.")
    parser.add_argument("--trace-id")
    parser.add_argument("--no-ticket", action="store_true", help="Do not create draft support tickets.")
    args = parser.parse_args()

    request = AgentRunInput(
        session_id=args.session_id,
        user_role=args.user_role,
        message=args.message,
        order_id=args.order_id,
        seller_id=args.seller_id,
        request_at=args.request_at,
        trace_id=args.trace_id,
        auto_create_ticket=not args.no_ticket,
    )
    result = run_agent(request)
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
