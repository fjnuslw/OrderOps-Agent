# OrderOps Agent Build Plan

本文档用于约束实际开发顺序。`docs/PROJECT_SPEC.md` 描述完整目标，`docs/CODEX_TASKS.md` 描述任务拆分；本文只回答当前仓库从规格包走向可运行项目时，先做什么、做到什么算完成、哪些事情暂时不做。

## 当前状态

- 已有项目规格、任务拆分、API 契约草稿、政策文档、评测种子、数据库 schema 草稿和架构图。
- 已有最小 FastAPI 后端、测试、Docker Compose、本地配置模块。
- 已导入 Olist 核心订单数据到 PostgreSQL。
- 已生成派生售后工单数据。
- 已完成政策 RAG 第一版，并在本机切换到真实本地模型：`D:\models\bge-m3` embedding 与 `D:\models\bge-reranker-v2-m3` rerank。
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

暂缓：

- 不引入复杂 CI。
- 不提前写部署文档。

### Phase 1: Backend Scaffold

状态：已完成。

目标：建立最小 FastAPI 项目骨架。

验收：

- 有 `apps/api` 后端目录。
- `GET /health` 返回 `{"status": "ok"}`。
- 有最小 pytest 测试。
- 本地测试命令可以跑通。

当前实现：

- FastAPI 应用入口：`apps/api/src/orderops_api/main.py`
- 健康检查路由：`apps/api/src/orderops_api/routers/health.py`
- 健康检查测试：`tests/api/test_health.py`

暂缓：

- 不实现真实业务工具。
- 不接入大模型。
- 不连接真实数据库查询。

### Phase 2: Local Infrastructure

状态：已完成，并通过本地 Docker 验证。PostgreSQL 宿主机端口使用 `15432`，避免和本机已有 `5432` 服务冲突。

目标：建立本地依赖服务，并让应用配置能读取这些地址。

验收：

- `docker-compose.yml` 能启动 PostgreSQL、Redis、Qdrant。
- `.env.example` 记录必要环境变量。
- 后端配置层能读取数据库、Redis、Qdrant 地址。

当前实现：

- 本地容器定义：`docker-compose.yml`
- 环境变量模板：`.env.example`
- 配置读取模块：`apps/api/src/orderops_api/core/config.py`
- 配置测试：`tests/api/test_config.py`
- 本地基础设施说明：`docs/LOCAL_INFRA.md`

暂缓：

- 不做生产级高可用。
- 不做云部署。

### Phase 3: Database and ETL

状态：已完成 schema bootstrap、ETL 导入和本地 smoke check。原始 Olist CSV 保留在 `data/raw/`，不提交到 GitHub。

目标：把 Olist 原始 CSV 导入 PostgreSQL，形成可查询业务数据。

验收：

- `scripts/etl_olist.py` 能读取 `data/raw/` 下的 CSV。
- 核心表至少包含 orders、order_items、payments、reviews、products、sellers、customers。
- 提供 smoke check，能确认导入数量和关键字段。

当前实现：

- Schema 文件：`data/sql/target_schema.sql`
- Schema 初始化脚本：`scripts/db_bootstrap.py`
- Olist ETL 脚本：`scripts/etl_olist.py`
- ETL 文件检查测试：`tests/scripts/test_etl_olist.py`
- ETL 使用说明：`docs/ETL.md`

暂缓：

- 不追求一次覆盖所有字段。
- 不做复杂数据清洗平台。

### Phase 4: Derived Support Tickets

状态：已完成本地生成和 smoke check。当前默认每个 scenario 生成最多 100 条工单，共 400 条。

目标：从订单数据派生售后工单，用于 Agent 场景和评测。

验收：

- 能生成至少 100 条 `support_tickets`。
- 覆盖延迟送达、低分评论、取消订单、高金额订单等 scenario。
- 工单 schema 稳定，可被后续工具读取。

当前实现：

- 工单生成脚本：`scripts/generate_support_tickets.py`
- 工单生成测试：`tests/scripts/test_generate_support_tickets.py`
- 工单说明文档：`docs/SUPPORT_TICKETS.md`
- 本地 smoke check：共 400 条，4 类 scenario 各 100 条。

暂缓：

- 不做人工标注平台。
- 不追求完全真实客服系统字段。

### Phase 5: Policy RAG

状态：已完成，并从测试 fallback 切换到真实本地模型路线。

目标：先做小而稳的政策检索。

验收：

- 能加载 `data/policies/` 文档。
- 能切分、索引、查询政策片段。
- 查询“延迟送达如何补偿”能返回 `delivery_sla_policy_v1#s2` 相关内容。
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
- 本地 smoke check：`延迟送达如何补偿` 首条返回 `delivery_sla_policy_v1#s2`。

说明：

- `HashingEmbeddingProvider` 和 `LexicalReranker` 只用于快速测试和无模型 fallback，不作为本机实际 RAG 路线。
- 如果更换 embedding 模型或维度，必须重新运行 `scripts/index_policies.py`，因为 Qdrant collection 的向量维度需要一致。

暂缓：

- 不一开始做复杂混合召回。
- 不把某个大模型权重提交到仓库。

### Phase 6: Business Tools

状态：下一阶段。

目标：把关键业务动作变成受控工具。

验收：

- 订单查询、政策检索、退款判断、物流赔付、工单草稿使用 Pydantic schema。
- `create_support_ticket` 默认只生成草稿，并标记 `approval_required`。
- SQL 工具只允许 SELECT，并有基础拦截测试。

暂缓：

- 不允许工具直接执行危险写操作。
- 不做全功能客服后台。

### Phase 7: LangGraph Workflow

状态：待开始。

目标：把工具串成可追踪状态机。

验收：

- 延迟送达案例能触发订单查询、政策检索、规则判断和工单草稿。
- Prompt Injection 案例不会调用危险 SQL 工具。
- 每次运行能输出结构化 trace 或 step log。

暂缓：

- 不追求复杂多 Agent 协作。
- 不先做华丽 UI。

### Phase 8: Evaluation

状态：待开始。

目标：用小评测集约束 Agent 行为。

验收：

- `scripts/run_eval.py` 可运行。
- 输出 `eval_report.json` 和 `eval_report.md`。
- 至少包含 Retrieval Recall@5、Tool Selection Accuracy、Task Success Rate、Risk Control Accuracy、p95 latency。

暂缓：

- 不把评测做成完整平台。
- 不把模型表现包装成无法复现的结论。

## 当前下一步

进入 Phase 6：先实现只读业务查询工具和政策检索工具的统一接口，再做退款/赔付判断与工单草稿。每个工具都必须有清晰输入输出 schema、基础测试和人工审批边界。
