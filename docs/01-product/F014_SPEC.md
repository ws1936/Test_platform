# F014 有限并发执行 — 规格说明

> 状态：Done（核心实现 + Router/Service 透传 + 文档同步）  
> 范围：MVP 增强能力；不引入 Celery / Redis / MQ / 分布式执行。  
> 设计稿：本文档。配套 ADR 见 `docs/04-rules/ADR.md` ADR-006。

---

## 1. 目标

让单次 `TestRun` 内的多条 `TestCase` 在**进程内**以受控并发度并行执行，
显著缩短回归耗时。仍保持 F010 同步执行契约：客户端发请求 → 服务端完成
全部 case → 一次性返回完整结果。

不做分布式、不做多进程 worker、不做跨 Run 调度。

## 2. 非目标

- Celery / Redis / MQ 队列
- 多 worker / 横向扩容
- 跨 Run 并发调度
- Case 内 step 并发
- "上一步响应作为下一步变量"的链式变量
- 重试机制
- Run 级总超时
- 前端 UI 改动（F016 范围）

## 3. 用户故事

| 场景 | 行为 |
|------|------|
| 触发项目级 Run（默认） | 后端按 `settings.TEST_RUN_MAX_CONCURRENCY`（默认 4）并发执行 |
| 用户想强制串行 | `?concurrency=1` |
| 用户想提高并发 | `?concurrency=8`（上限 64） |
| 客户端传非法值 | Router 422，runner 不被调用 |
| 客户端不传 | Service 透传 `None`，runner 走 settings 默认 |

## 4. 接口契约

### 4.1 `POST /api/v1/projects/{project_id}/runs`

新增可选 query 参数：

| 字段 | 类型 | 必填 | 取值范围 | 默认 | 说明 |
|------|------|------|----------|------|------|
| `concurrency` | int | 否 | `1 ≤ N ≤ 64` | settings.TEST_RUN_MAX_CONCURRENCY (4) | 单 Run 内同时在飞的 case 数 |

- **不传** → Service 透传 `None` → Runner 读 `settings.TEST_RUN_MAX_CONCURRENCY`。
- **传 0 / 负数 / > 64** → FastAPI 422。
- **向后兼容**：未升级的客户端不会受影响。

### 4.2 `POST /api/v1/test-cases/{case_id}/run`

同样新增可选 `concurrency`（1 ≤ N ≤ 64）。因单 case 无并行语义，
参数被透传到 Runner 但不影响墙钟时间——仅用于多 case 入口对称。

## 5. 配置

`src/app/config.py::Settings`:

```python
TEST_RUN_MAX_CONCURRENCY: int = 4   # F014 有限并发
```

`.env.example` 已同步提供 `TEST_RUN_MAX_CONCURRENCY=4`。

## 6. 实现要点

### 6.1 并发模型

`TestRunner.execute_run` 使用 **`asyncio.Semaphore(N)` + `asyncio.gather(...)`**：
- HTTP 请求（`httpx.AsyncClient`）在 semaphore 内并发；
- SQLAlchemy `AsyncSession` 操作（get/flush/commit）由 `asyncio.Lock`
  串行化（`self._db_lock`），保证 ORM 写入安全；
- HTTP 请求本身在锁外，并行度不受 DB 串行影响；
- `_execute_single` 内已捕获所有已知异常；
- 每个 task 外层 `except Exception` 是 defensive net，即使引擎层抛
  未预期异常也不影响其他 case（test_runner_concurrency::test_unexpected_exception_in_execute_single_does_not_abort_run）。

### 6.2 非法值回落

`TestRunner.__init__`：

```python
raw = max_concurrency if max_concurrency is not None else settings.TEST_RUN_MAX_CONCURRENCY
self._max_concurrency = max(1, int(raw))
```

`< 1` 全部回落为 1，**永不抛异常**。语义：用户传 `0` 会被 Router 422
挡掉；但通过 Service 直调（非 HTTP 入口）传 0 时静默降级为串行，
保证引擎鲁棒性。

### 6.3 顺序与可追溯

- 串行下 result 顺序 = case_ids 顺序；
- 并发下完成顺序随机，但 report 按 `sequence_no` / 入参顺序排序；
- TestRun 状态机：`pending → running → finished`；
- 并发期间允许 `running` + 部分 result 已落库（流式可读）。

### 6.4 变量 / 断言

- F008 内置变量 `${timestamp}` / `${random_int}` 每次调用重新生成，
  并发下天然 case-level 隔离。
- F009 断言引擎无状态，并发安全。
- 不引入"上一步响应作为下一步变量"（PRD 未要求）。

## 7. 可观测性

Run 启动日志：

```text
TestRunner: run <uuid> started, concurrency=<N>
```

Case 完成日志：单行摘要（status / elapsed_ms），**不含 response body / 敏感 header**。

Run 摘要日志：

```text
TestRunner: run <uuid> finished — total=N passed=... failed=... error=... skipped=...
```

## 8. 测试覆盖

### 8.1 核心引擎（已存在）

`src/tests/test_runner_concurrency.py`（8 个用例，全部转绿）：
- T1: 默认从 settings 读
- T2: `max_concurrency=1` 退化为串行
- T3: `max_concurrency=N` 限制峰值并发
- T4: 非法值（0/-1/-100）回落为 1
- T5: 并发下计数器一致
- T6: `_execute_single` 抛未预期异常不中断
- T7-T8: parametrize 衍生用例

### 8.2 Router/Service 透传（新增）

`src/tests/test_test_run_concurrency_param.py`（9 个用例，全部转绿）：
- 默认值透传：`?concurrency=` 不传 → runner 收到 `None`
- 显式值透传：`?concurrency=1|2|4|8|64` → runner 收到对应 N
- 422 校验：`?concurrency=0` / `?concurrency=200`
- 单 case 入口对称

### 8.3 DoD

- [x] `test_runner_concurrency.py` 8/8 通过
- [x] `test_test_run_concurrency_param.py` 9/9 通过
- [x] 全量 `pytest src/tests/` 420/420 通过（411 旧 + 9 新），0 回归
- [x] 零 DB Migration、零新依赖
- [x] 敏感 header / body 不进日志
- [x] BACKLOG 状态 Todo → Doing → Done
- [x] ARCHITECTURE.md 标注 F014
- [x] OPENAPI.yaml 同步 `?concurrency=` 参数
- [x] .env.example 同步 `TEST_RUN_MAX_CONCURRENCY`

## 9. 风险与权衡

- **DB session 共享**：当前实现用一把 `asyncio.Lock` 串行化 ORM 操作；
  在 case 数 ≫ N 时 DB 写入仍是瓶颈。如未来要消除，可在 per-task 启
  sub-session，但需要更细的事务边界，**不在 F014 范围**。
- **目标 API 端限流**：高并发可能触发被测服务限流，建议 UI 在 SPEC
  选择器旁标注"高并发可能触发被测服务限流"。
- **httpx 握手开销**：当前 `ApiExecutor.execute()` 每次新建
  `AsyncClient`（F010 设计）；F014 沿用，HTTPS 握手不会被摊薄。
  这是 F010 范围内的已知设计选择，F014 不重构它。

## 10. 后续演进（不在本任务）

- F015 报告导出：并发 Run 的结果排序已在 F011 内保证。
- 跨 Run 并发调度：F017（定时任务）评估时再讨论。
- per-case 超时（区别于全局 httpx timeout）：可作为 F014 的小迭代，
  当前不做。

## 11. 关联文档

- `docs/01-product/BACKLOG.md` §3 F014
- `docs/04-rules/ADR.md` ADR-006（F014 决策）
- `docs/02-design/ARCHITECTURE.md` §5 执行流程（F014 标注）
- `docs/03-api/OPENAPI.yaml` `/projects/{project_id}/runs`（concurrency 参数）
- `docs/05-test/ACCEPTANCE.md` §4.5（F014 验收条目）
- `src/tests/test_runner_concurrency.py`
- `src/tests/test_test_run_concurrency_param.py`
