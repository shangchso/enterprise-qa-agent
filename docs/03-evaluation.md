# 03 测试与评估

## 1. 测试方式

- 单元测试：`tests/test_agent.py`，基于标准库 `unittest`。
- 场景验证：`run.py` 生成的 Trace 存于 `examples/traces/`。

运行命令：

```bash
python -m unittest discover -s tests
```

## 2. 测试预期与实际结果

| 测试方法 | 预期 | 实际 |
| --- | --- | --- |
| test_clear_answer_with_citation | 带 D03 引用回答年假 5 天 | 通过 |
| test_document_conflict_needs_confirmation | 列 D01/D02 冲突，不擅自选 | 通过 |
| test_out_of_scope_returns_gap | 资料外返回缺口 | 通过 |
| test_rephrased_question_matches | 改写命中 D05，回答 300 元 | 通过 |
| test_context_follow_up | 追问命中 D04-F2，回答无需审批 | 通过 |
| test_tool_failure_blocked | 检索失败阻断 | 通过 |
| test_step_limit_returns_incomplete | 步数上限返回 incomplete | 通过 |

实际运行：**7 个测试全部通过**。

## 3. 场景 Trace 核对

| 场景 | 最终状态 | 关键核对项 |
| --- | --- | --- |
| Q1 | answered | 引用 D03 原文，答案 5 天 |
| Q2 | needs_confirmation | 冲突项含 D01(30天)/D02(15天) 原文 |
| Q3 | out_of_scope | 无候选，返回资料缺口 |
| Q4 | answered | 改写命中 D05，答案 300 元 |
| Q5 / Q5_followup | answered | 追问答案为无需管理员审批 |
| Q6 | blocked | 检索工具失败，不编造 |

## 4. 已知限制

1. MockLLM 为规则式决策，只验证流程与冲突处理，不代表真实模型效果。
2. 检索基于关键词包含匹配，未做向量语义检索，复杂语义可能漏召回。
3. 文档为内存态，进程结束后不持久化（Trace 文件除外）。
4. 冲突处理停在"请求确认"，未实现确认后的自动续答。
