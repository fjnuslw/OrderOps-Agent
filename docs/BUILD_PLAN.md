# OrderOps Agent Build Plan

本文档用于约束实际开发顺序。`docs/PROJECT_SPEC.md` 描述完整目标，`docs/CODEX_TASKS.md` 描述任务拆分；本文只回答当前仓库从规格包走向可运行项目时，先做什么、做到什么算完成、哪些事情暂时不做。

## 当前状态

- 已有项目规格、任务拆分、API 契约草稿、政策文档、评测种子、数据库 schema 草稿和架构图。
- 已有 FastAPI 后端、测试、Docker Compose、本地配置模块。
- 已导入 Olist 核心订单数据到 PostgreSQL。
- 已生成派生售后工单数据。
- 已完成政策 RAG，并在本机切换到真实本地模型：`D:\models\bge-m3` embedding 与 `D:\models\bge-reranker-v2-m3` rerank。
- 已完成 Phase 6 业务工具层：订单摘要、政策检索、延迟赔付判断、退款资格判断、工单草稿、审批流转、只读 SQL 分析、卖家质量分析、工具调用日志。
- `data/raw/` 只保留占位文件，真实 CSV 不提交到 GitHub。

## 总体目标

构建一个电商售后履约运营 Agent Demo，展示以下能力：

- 通过 FastAPI 暴露服务接口。
- 使用 PostgreSQL 保存订单、工单和派生业务数据。
- 使用政策文档构建可检索知识库。
- 使用受控工具完成订单查询、政策检索、退款/赔付判断、工单草稿和客服回复。
- 使用 LangGraph 编排可追踪的 Agent 工作流。
- 使用评测脚本验证检索、工具选择、任务成功率、风险控制和延迟。

## 阶段顺序

### Phase 0: Repository Baseline

状态：已完成。

目标：让仓库适合持续开发和 GitHub 更新。

验收：

- README 能说明项目用途和目录结构。
- `.gitignore` 避免提交密钥、虚拟环境、原始大数据和生成报告。
- 本文档明确实际开发顺序。

### Phase 1: Backend Scaffold

状态：已完成。

目标：建立最小 FastAPI 项目骨架。

当前实现：

- FastAPI 应用入口：`apps/api/src/orderops_api/main.py`
- 健康检查路由：`apps/api/src/orderops_api/routers/health.py`
- 健康检查测试：`tests/api/test_health.py`

### Phase 2: Local Infrastructure

状态：已完成，并通过本地 Docker 验证。PostgreSQL 宿主机端口使用 `15432`，避免和本机已有 `5432` 服务冲突。

当前实现：

- 本地容器定义：`docker-compose.yml`
- 环境变量模板：`.env.example`
- 配置读取模块：`apps/api/src/orderops_api/core/config.py`
- 配置测试：`tests/api/test_config.py`
- 本地基础设施说明：`docs/LOCAL_INFRA.md`

### Phase 3: Database and ETL

状态：已完成 schema bootstrap、ETL 导入和本地 smoke check。原始 Olist CSV 保留在 `data/raw/`，不提交到 GitHub。

当前实现：

- Schema 文件：`data/sql/target_schema.sql`
- Schema 初始化脚本：`scripts/db_bootstrap.py`
- Olist ETL 脚本：`scripts/etl_olist.py`
- ETL 文件检查测试：`tests/scripts/test_etl_olist.py`
- ETL 使用说明：`docs/ETL.md`

### Phase 4: Derived Support Tickets

状态：已完成本地生成和 smoke check。当前默认每个 scenario 生成最多 100 条工单，共 400 条。

当前实现：

- 工单生成脚本：`scripts/generate_support_tickets.py`
- 工单生成测试：`tests/scripts/test_generate_support_tickets.py`
- 工单说明文档：`docs/SUPPORT_TICKETS.md`
- 本地 smoke check：共 400 条，4 类 scenario 各 100 条。

### Phase 5: Policy RAG

状态：已完成，并从测试 fallback 切换到真实本地模型路线。

验收：

- 能加载 `data/policies/` 文档。
- 能切分、索引、查询政策片段。
- 查询“延迟送达如何补偿”能返回 `delivery_sla_policy_v1` 的延迟送达判断相关内容。
- 返回 doc_id、section_id、score、text。
- 本机实际检索使用 `D:\models\bge-m3` embedding 与 `D:\models\bge-reranker-v2-m3` rerank。

当前实现：

- 政策加载与切分：`apps/api/src/orderops_api/rag/policies.py`
- embedding provider 抽象：`apps/api/src/orderops_api/rag/embedding.py`
- Qdrant HTTP 客户端：`apps/api/src/orderops_api/rag/qdrant.py`
- 检索与 rerank provider 抽象：`apps/api/src/orderops_api/rag/search.py`、`apps/api/src/orderops_api/rag/rerank.py`
- 索引脚本：`scripts/index_policies.py`
- 检索脚本：`scripts/search_policy.py`
- HuggingFace 模型下载脚本：`scripts/download_hf_snapshot.py`
- RAG 说明文档：`docs/POLICY_RAG.md`
- 本地 smoke check：`延迟送达如何补偿` 首条返回 `delivery_sla_policy_v1#s3`。

说明：

- `HashingEmbeddingProvider` 和 `LexicalReranker` 只用于快速测试和无模型 fallback，不作为本机实际 RAG 路线。
- 如果更换 embedding 模型或维度，必须重新运行 `scripts/index_policies.py`，因为 Qdrant collection 的向量维度需要一致。
- 当前 policy 是 Demo 合成政策，并显式区分业务规则和 Olist 数据字段映射。

### Phase 6: Business Tools

状态：已完成当前阶段收束。

目标：把关键业务动作变成受控工具，供后续 LangGraph 编排直接调用。

验收：

- 订单查询、政策检索、退款判断、物流赔付、工单草稿使用 Pydantic schema。
- `create_support_ticket_draft` 只生成草稿，并标记 `approval_required`。
- 审批工具能把 pending approval 流转为 approved/rejected，并更新工单状态。
- SQL 工具只允许 SELECT/WITH，禁止危险写操作和隐私字段，并自动控制 LIMIT。
- 卖家质量分析返回稳定指标、风险等级和建议动作。
- 所有工具写入 `tool_call_logs`。

当前实现：

- 订单摘要工具：`apps/api/src/orderops_api/tools/order_tools.py`
- 政策检索工具包装：`apps/api/src/orderops_api/tools/policy_tools.py`
- 延迟赔付判断工具：`apps/api/src/orderops_api/tools/delivery_tools.py`
- 退款资格判断工具：`apps/api/src/orderops_api/tools/refund_tools.py`
- 工单草稿工具：`apps/api/src/orderops_api/tools/ticket_tools.py`
- 审批流转工具：`apps/api/src/orderops_api/tools/approval_tools.py`
- SQL Guard 基础规则：`apps/api/src/orderops_api/tools/sql_guard.py`
- 只读 SQL 分析工具：`apps/api/src/orderops_api/tools/sql_tools.py`
- 卖家质量分析工具：`apps/api/src/orderops_api/tools/analysis_tools.py`
- 工具调用日志：`apps/api/src/orderops_api/tools/logging.py`
- 工具 API 路由：`apps/api/src/orderops_api/routers/tools.py`
- 工具说明文档：`docs/BUSINESS_TOOLS.md`

本地 smoke check：

- 订单 `1b3190b2dfa9d789e1f14c05b647a14a` 返回 `eligible_with_manual_approval`。
- 工单草稿 `DRAFT-60D7D181E78F` 可由 approval `APR-A2C5C1365168` 审批为 `approved`，工单状态变为 `open`。
- 退款判断返回 `eligible_with_manual_approval` 并引用 `refund_policy_v1`。
- SQL 分析能执行订单状态统计，并拦截 `customer_unique_id` 隐私字段。
- 卖家 `7a67c85e85bb2ce8582c35f2203ad736` 可返回质量指标、风险等级和建议动作。

暂缓：

- 不执行真实资金动作。
- 不做全功能客服后台。
- 不把 SQL 工具开放为任意写操作。

### Phase 7: LangGraph Workflow

状态：已完成当前阶段收束。

目标：把 Phase 6 工具串成可追踪状态机。

验收：

- 延迟送达案例能触发订单查询、政策检索、规则判断、工单草稿和审批等待。
- 退款案例能触发订单查询、退款政策检索、退款资格判断和审批等待。
- Prompt Injection 案例不会调用危险 SQL 工具。
- 每次运行能输出结构化 trace 或 step log。

当前实现：

- LangGraph 状态机入口：`apps/api/src/orderops_api/agent/graph.py`
- 状态、计划、引用和 step trace schema：`apps/api/src/orderops_api/agent/state.py`
- 输入安全和意图路由规则：`apps/api/src/orderops_api/agent/guard.py`
- LLM 路由和最终回复 schema：`apps/api/src/orderops_api/agent/llm_planner.py`
- DeepSeek/OpenAI-compatible LLM client：`apps/api/src/orderops_api/llm/client.py`
- API 路由：`POST /api/agent/run`、`POST /api/chat`
- CLI：`scripts/run_agent_case.py`
- 文档：`docs/AGENT_WORKFLOW.md`

### Phase 8: Evaluation

状态：当前种子回归套件已完成。

当前实现：

- `data/eval/eval_cases_seed.csv` 定义 8 个固定评测 case。
- `apps/api/src/orderops_api/evaluation/` 负责加载 case、记录工具调用、计算指标和渲染报告。
- `scripts/run_eval.py` 提供命令行评测入口。
- `POST /api/evals/run` 提供 FastAPI 评测入口。
- `scripts/phase_smoke_check.py` 包含一个不调用真实 LLM、不写业务数据的 Phase 8 smoke case。
- `docs/EVALUATION.md` 记录指标、命令和安全默认值。

目标：用小评测集约束 Agent 行为。

验收：

- `scripts/run_eval.py` 可运行。
- 输出 `eval_report.json` 和 `eval_report.md`。
- 至少包含 Retrieval Recall@5、Tool Selection Accuracy、Task Success Rate、Risk Control Accuracy、p95 latency。

## 当前下一步

Phase 8 已经收束。下一步更适合在 trace 持久化、多轮记忆、或小型运营 UI 之间选择一个方向继续推进。
