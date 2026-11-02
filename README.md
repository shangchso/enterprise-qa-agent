# 企业知识问答 Agent（Enterprise QA Agent）

小影科技 2027 校招 AI Agent 笔试题第 3 题：帮助员工找到制度或产品问题的
**可靠答案**。基于 Python 标准库原生实现，默认离线运行，无需第三方依赖。

## 1. 项目简介

Agent 通过 ReAct 循环完成检索式问答：

```
模型选择动作 → 执行工具 → 观察结果 → 模型调整下一步或结束
```

- 答案必须由**引用原文**支持，带文档 ID 与原文片段；
- 文档冲突时列出冲突与引用并请求确认，**不凭空选答案**；
- 资料外问题返回资料缺口，不编造；
- 支持同义改写检索与上下文追问。

## 2. 环境要求

- Python 3.9+（开发环境 Python 3.13）
- 默认离线运行，无需安装依赖、无需 API Key。

## 3. 安装与运行

```bash
cd enterprise-qa-agent

python run.py --list                 # 查看全部问题

python run.py --question-id Q1       # 明确答案
python run.py --question-id Q2       # 文档冲突
python run.py --question-id Q3       # 资料外问题
python run.py --question-id Q4       # 改写后的相似问题
python run.py --question-id Q5       # 上下文追问（自动两轮）
python run.py --question-id Q6 --fail-tool document_search  # 工具失败
```

## 4. 运行测试

```bash
python -m unittest discover -s tests
```

预期：7 个测试全部通过。

## 5. 目录结构

```
enterprise-qa-agent/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── run.py                  # CLI 入口
├── src/
│   ├── agent.py            # ReAct 检索与冲突处理循环
│   ├── llm.py              # MockLLM / RealLLM
│   ├── data_store.py       # 数据加载、片段展平、对话历史
│   └── tools/              # 文档检索、片段读取
├── data/                   # 合成文档与问题
├── tests/                  # 单元测试
├── examples/traces/        # 7 份场景 Trace
└── docs/                   # 01~05 五份文档
```

## 6. 评审入口

- 需求与验收点：`docs/01-requirements.md`
- 方案与冲突处理：`docs/02-solution.md`
- 测试结果：`docs/03-evaluation.md`
- 场景 Trace：`examples/traces/`

## 7. 真实模型接入（可选）

配置环境变量后自动启用 RealLLM（OpenAI 兼容接口，基于 `urllib`）：

```bash
cp .env.example .env   # 填写 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL
```

未配置 `LLM_API_KEY` 时始终使用离线 MockLLM。Mock 仅验证流程，不代表真实
模型决策效果。
