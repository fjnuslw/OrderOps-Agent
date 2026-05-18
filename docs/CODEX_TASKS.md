# Codex 任务拆分

## Task 0: Scaffold

根据 `docs/PROJECT_SPEC.md` 创建 FastAPI + LangGraph 项目骨架。只生成框架，不实现业务逻辑。

验收：
- `GET /health` 返回 OK
- `pytest` 通过
- `docker compose up -d` 能启动 postgres、redis、qdrant

## Task 1: ETL

实现 `scripts/etl_olist.py`，把 Olist CSV 导入 PostgreSQL。

验收：
- orders、order_items、payments、reviews、products、sellers、customers 表有数据
- 时间字段能正确解析
- 提供 smoke check

## Task 2: Derived Tickets

实现 `scripts/generate_support_tickets.py`，从订单延迟、低分评论、取消订单、高金额订单派生 support_tickets。

验收：
- 能生成至少 100 条工单
- 工单 scenario 分布合理

## Task 3: RAG

实现政策文档加载、切分、索引和 `search_policy` 工具。

验收：
- 查询“延迟送达如何补偿”能召回 delivery_sla_policy_v1 的相关章节
- 返回 doc_id、section_id、score、text

## Task 4: Business Tools

实现订单查询、退款判断、物流赔付、工单创建、卖家质量分析和 SQL Guard。

验收：
- 所有工具使用 Pydantic Schema
- create_support_ticket 需要 approval_required
- SQL 工具只允许 SELECT

## Task 5: LangGraph

实现完整状态机。

验收：
- 延迟送达案例能触发订单查询、政策检索、规则判断和工单草稿
- Prompt Injection 案例不调用 SQL 工具

## Task 6: Evaluation

实现 `scripts/run_eval.py` 和指标计算。

验收：
- 输出 eval_report.json 和 eval_report.md
- 包含 Retrieval Recall@5、Tool Selection Accuracy、Task Success Rate、Risk Control Accuracy、p95 latency
