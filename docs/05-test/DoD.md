# Definition of Done

> DoD 用于判断一个需求、模块或文档任务是否真正完成。  
> 当前范围：API 自动化测试平台 MVP。

---

## 1. 通用完成标准

任何任务完成前必须确认：

- [ ] 目标与 API 自动化测试平台 MVP 范围一致。
- [ ] 没有引入未经确认的复杂能力。
- [ ] 实现或文档与现有结构保持一致。
- [ ] 无明显重复逻辑。
- [ ] 无敏感信息泄露。
- [ ] 无未说明的 TODO/FIXME。

---

## 2. 代码任务 DoD

- [ ] 功能按需求完成。
- [ ] Router、Service、Repository 分层清晰。
- [ ] 请求和响应 Schema 明确。
- [ ] 异常处理完整。
- [ ] 权限校验完整。
- [ ] 日志不记录 Token、Password、Cookie。
- [ ] 涉及数据库变更时已提供 Alembic Migration。
- [ ] OpenAPI 文档可生成。
- [ ] 新增逻辑有单元测试或 API 测试。
- [ ] 相关测试通过。

---

## 3. API 测试模块 DoD

- [ ] 项目、环境、集合、用例数据关系正确。
- [ ] 变量替换有测试覆盖。
- [ ] 请求构造有测试覆盖。
- [ ] 断言引擎有测试覆盖。
- [ ] 执行器设置超时。
- [ ] TestRun 状态流转正确。
- [ ] TestResult 保存请求、响应、断言和错误信息。
- [ ] 报告统计准确。

---

## 4. 文档任务 DoD

- [ ] 文档放在正确目录。
- [ ] 文档命名符合目录规范。
- [ ] 文档内容与当前 MVP 范围一致。
- [ ] 涉及接口时同步更新 `03-api/OPENAPI.yaml`。
- [ ] 涉及错误码时同步更新 `03-api/ERROR_CODE.md`。
- [ ] 涉及架构决策时同步更新 `04-rules/ADR.md`。
- [ ] Markdown 代码块闭合。
- [ ] 无过期目录或旧文档引用。

---

## 5. 发布前检查

建议执行：

```bash
pytest src/tests
```

如涉及前端：

```bash
cd frontend
npm run build
```

如涉及文档结构：

```bash
find docs -maxdepth 2 -type f | sort
```
