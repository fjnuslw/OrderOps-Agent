# Codex Tasks

本文档把阶段路线拆成可执行任务。当前项目已经完成 Task 0 到 Task 5，下一步进入 Task 6。

## Task 0: Repository And API Scaffold

状态：已完成。

目标：创建可持续开发的 FastAPI 项目骨架。

验收：

- `GET /health` 返回 OK。
- `pytest` 可以通过。
- README、`.gitignore`、环境变量模板和基础文档齐全。
- Docker Compose 能启动 Postgres、Redis、Qdrant。

## Task 1: Olist ETL

状态：已完成。

目标：把 Olist CSV 导入 PostgreSQL。

验收：

- `orders`、`order_items`、`payments`、`reviews`、`products`、`sellers`、`customers` 表有数据。
- 时间字段能正确解析。
- 提供导入脚本和 smoke check。

主要文件：

- `scripts/db_bootstrap.py`
- `scripts/etl_olist.py`
- `docs/ETL.md`

## Task 2: Derived Support Tickets

状态：已完成。

目标：从订单延迟、低分评论、取消订单、高金额订单派生 `support_tickets`。

验收：

- 覆盖 `delivery_delay`、`low_review`、`canceled_order`、`high_value_order`。
- 每类 scenario 有稳定生成逻辑。
- 工单数据进入 PostgreSQL，可被后续工具读取。

主要文件：

- `scripts/generate_support_tickets.py`
- `docs/SUPPORT_TICKETS.md`

## Task 3: Policy RAG

状态：已完成。

目标：实现政策文档加载、切分、索引、检索和 rerank。

验收：

- `data/policies/*.md` 可加载。
- Qdrant collection 使用当前 embedding 维度。
- 查询“延迟送达如何补偿”能召回 `delivery_sla_policy_v1` 相关章节。
- 本机实际运行使用 `D:\models\bge-m3` 和 `D:\models\bge-reranker-v2-m3`。

主要文件：

- `apps/api/src/orderops_api/rag/`
- `scripts/index_policies.py`
- `scripts/search_policy.py`
- `docs/POLICY_RAG.md`

## Task 4: Business Tools

状态：已完成。

目标：实现 Agent 可调用的受控业务工具。

验收：

- 所有工具使用 Pydantic schema。
- 工具调用写入 `tool_call_logs`。
- 工单创建只生成草稿和 pending approval。
- 审批工具可以 approve/reject。
- SQL 工具只允许 SELECT/WITH，拦截危险操作和隐私字段。
- 卖家质量分析返回指标、风险等级和建议动作。

主要工具：

- `get_order_summary`
- `search_policy_tool`
- `check_delivery_compensation`
- `check_refund_eligibility`
- `create_support_ticket_draft`
- `decide_approval`
- `run_sql_analysis`
- `analyze_seller_quality`

主要文件：

- `apps/api/src/orderops_api/tools/`
- `apps/api/src/orderops_api/routers/tools.py`
- `docs/BUSINESS_TOOLS.md`

## Task 5: LangGraph Workflow

状态：已完成。

目标：把 Phase 6 工具串成可追踪状态机。

验收：

- 延迟送达案例能触发订单查询、政策检索、赔付判断、工单草稿和审批等待。
- 退款复核案例能触发订单查询、政策检索、退款资格判断、工单草稿和审批等待。
- Prompt Injection 案例不会调用危险 SQL。
- 每次运行输出结构化 trace 或 step log。
- 不暴露模型原始 chain-of-thought，只输出可审计步骤摘要。

建议实现：

- `apps/api/src/orderops_api/agent/state.py`
- `apps/api/src/orderops_api/agent/graph.py`
- `scripts/run_agent_case.py`

当前实现补充：

- `apps/api/src/orderops_api/agent/guard.py`
- `apps/api/src/orderops_api/routers/agent.py`
- `docs/AGENT_WORKFLOW.md`
- `tests/agent/test_graph.py`
- `tests/agent/test_guard.py`

## Task 6: Evaluation

状态：待开始。

目标：实现 `scripts/run_eval.py` 和指标计算。

验收：

- 输出 `eval_report.json` 和 `eval_report.md`。
- 包含 Retrieval Recall@5、Tool Selection Accuracy、Task Success Rate、Risk Control Accuracy、p95 latency。
- 使用固定 eval cases，失败案例可追溯。
