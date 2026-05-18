# OrderOps Agent Codex Starter Pack

本包用于把 OrderOps Agent Demo 交给 Codex 分阶段实现。

建议顺序：

1. 阅读 `docs/PROJECT_SPEC.md`
2. 使用 `docs/CODEX_TASKS.md` 中的任务拆分生成项目骨架
3. 把 Olist CSV 放入 `data/raw/`
4. 执行 ETL、构建政策索引、实现工具、接入 LangGraph
5. 使用 `data/eval/eval_cases_seed.csv` 做最小评测

本包不包含 Olist 原始数据。请通过 Kaggle 或其他公开镜像下载，并在 README 中注明数据来源。
