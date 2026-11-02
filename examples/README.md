# 示例与 Trace 说明

本目录存放各场景的实际输出与运行 Trace。每个 Trace 记录完整 ReAct 过程：
每一步的动作、工具入参、观察摘要、决策依据，以及最终回答与引用。

## Trace 与验收点对应关系

| Trace 文件 | 覆盖验收点 | 最终状态 |
| --- | --- | --- |
| `traces/trace_Q1.json` | 明确答案 | answered |
| `traces/trace_Q2.json` | 文档冲突 | needs_confirmation |
| `traces/trace_Q3.json` | 资料外问题 | out_of_scope |
| `traces/trace_Q4.json` | 改写后的相似问题 | answered |
| `traces/trace_Q5.json` | 上下文追问（第一轮） | answered |
| `traces/trace_Q5_followup.json` | 上下文追问（第二轮） | answered |
| `traces/trace_Q6.json` | 工具失败 | blocked |

## 重新生成 Trace

```bash
python run.py --question-id Q1
python run.py --question-id Q2
python run.py --question-id Q5   # 自动生成追问 Trace
python run.py --question-id Q6 --fail-tool document_search
```

每个回答的 `citations` 字段给出文档 ID、片段 ID、版本日期与原文片段；
冲突场景的 `conflict_items` 列出全部冲突文档，可直接用于评审。
