# OrderOps Agent Build Plan

本文档用于约束实际开发顺序。`PROJECT_SPEC.md` 描述完整目标，`CODEX_TASKS.md` 描述任务拆分；本文件只回答一个问题：当前仓库从规格包走向可运行项目时，先做什么、做到什么算完成、哪些事情暂时不做。

## 当前状态

- 已有项目规格、任务拆分、API 契约草案、政策文档、评测种子、数据库 schema 草案和架构图。
- 尚未有可运行的后端代码、Python 包结构、测试、Docker Compose 服务或真实 Olist 原始数据。
- `data/raw/` 只保留占位文件，真实 CSV 不提交到 GitHub。
- 当前目标不是一次性做完完整 Agent，而是按阶段建立可运行、可测试、可解释的最小系统。

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

目标：让仓库适合持续开发和 GitHub 更新。

验收：
- README 能说明项目用途和目录结构。
- `.gitignore` 避免提交密钥、虚拟环境、原始大数据和生成报告。
- 本文件明确实际开发顺序。

暂缓：
- 不引入复杂 CI。
- 不提前写部署文档。

### Phase 1: Backend Scaffold

目标：建立最小 FastAPI 项目骨架。

验收：
- 有 `apps/api` 或等价后端目录。
- `GET /health` 返回 `{"status": "ok"}`。
- 有最小 pytest 测试。
- 本地测试命令可以跑通。

暂缓：
- 不实现真实业务工具。
- 不接入大模型。
- 不连接真实数据库。

### Phase 2: Local Infrastructure

目标：建立本地依赖服务，但只保证能启动和被应用配置读取。

验收：
- `docker-compose.yml` 能启动 PostgreSQL、Redis、Qdrant。
- `.env.example` 记录必要环境变量。
- 后端配置层能读取数据库、Redis、Qdrant 地址。

暂缓：
- 不做生产级高可用。
- 不做云部署。

### Phase 3: Database and ETL

目标：把 Olist 原始 CSV 导入 PostgreSQL，形成可查询业务数据。

验收：
- `scripts/etl_olist.py` 能读取 `data/raw/` 下的 CSV。
- 核心表至少包含 orders、order_items、payments、reviews、products、sellers、customers。
- 提供 smoke check，能确认导入数量和关键字段。

暂缓：
- 不追求一次覆盖所有字段。
- 不做复杂数据清洗平台。

### Phase 4: Derived Support Tickets

目标：从订单数据派生售后工单，用于 Agent 场景和评测。

验收：
- 能生成至少 100 条 support_tickets。
- 覆盖延迟送达、低分评论、取消订单、高金额订单等 scenario。
- 工单 schema 稳定，可被后续工具读取。

暂缓：
- 不做人工标注平台。
- 不追求完全真实客服系统字段。

### Phase 5: Policy RAG

目标：先做小而稳的政策检索。

验收：
- 能加载 `data/policies/` 文档。
- 能切分、索引、查询政策片段。
- 查询“延迟送达如何补偿”能召回 `delivery_sla_policy_v1` 相关内容。
- 返回 doc_id、section_id、score、text。

暂缓：
- 不一开始做复杂混合召回和 rerank。
- 不依赖线上向量服务作为唯一方案。

### Phase 6: Business Tools

目标：把关键业务动作变成受控工具。

验收：
- 订单查询、政策检索、退款判断、物流赔付、工单创建草稿使用 Pydantic schema。
- `create_support_ticket` 默认只生成草稿，并标记 `approval_required`。
- SQL 工具只允许 SELECT，并有基础拦截测试。

暂缓：
- 不允许工具直接执行危险写操作。
- 不做全功能客服后台。

### Phase 7: LangGraph Workflow

目标：把工具串成可追踪状态机。

验收：
- 延迟送达案例能触发订单查询、政策检索、规则判断和工单草稿。
- Prompt Injection 案例不会调用 SQL 工具。
- 每次运行能输出结构化 trace 或 step log。

暂缓：
- 不追求复杂多 Agent 协作。
- 不先做华丽 UI。

### Phase 8: Evaluation

目标：用小评测集约束 Agent 行为。

验收：
- `scripts/run_eval.py` 可运行。
- 输出 `eval_report.json` 和 `eval_report.md`。
- 至少包含 Retrieval Recall@5、Tool Selection Accuracy、Task Success Rate、Risk Control Accuracy、p95 latency。

暂缓：
- 不把评测做成完整平台。
- 不把模型表现包装成无法复现的结论。

## 当前下一步

从 Phase 1 开始：创建最小 FastAPI 后端骨架、测试和运行说明。只有当 `GET /health` 和 pytest 通过后，再进入 Docker Compose 与数据库服务。
