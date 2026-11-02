"""决策模型层。

提供两种决策实现：
1. MockLLM：离线规则式决策模型，默认运行，不依赖外部 API。
2. RealLLM：OpenAI 兼容 Chat Completions 接口实现，通过环境变量配置，
   未配置密钥时自动回退 MockLLM。

决策动作集合：
- document_search  文档检索
- fragment_reader  片段读取
- answer           有据回答（带引用）
- conflict         文档冲突（列引用并请求确认）
- gap              资料外（返回资料缺口）
- block            工具失败等异常阻断
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict


class MockLLM:
    """离线 Mock 决策模型。"""

    def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """根据当前状态返回下一步动作。"""
        # 1. 尚未检索
        if not state["search_done"]:
            return {
                "action": "document_search",
                "params": {
                    "query": state["question"],
                    "context_topic": state["context_topic"],
                },
                "rationale": "先检索与问题相关的文档片段",
                "terminal": False,
            }

        # 2. 检索工具失败
        if state["tool_failed"]:
            return {
                "action": "block",
                "params": {"reason": f"工具失败：{state['tool_failed']}"},
                "rationale": "检索或读取工具失败，如实返回，不编造答案",
                "terminal": True,
            }

        candidates = state["candidates"]

        # 3. 资料外：无候选
        if not candidates:
            return {
                "action": "gap",
                "params": {
                    "reason": "现有文档库未检索到与该问题相关的资料",
                },
                "rationale": "资料覆盖范围外，返回资料缺口而非凭空回答",
                "terminal": True,
            }

        # 4. 逐个读取候选原文（用于引用与冲突查证）
        unread = [
            candidate
            for candidate in candidates
            if candidate["fragment_id"] not in state["read_fragments"]
        ]
        if unread:
            target = unread[0]
            return {
                "action": "fragment_reader",
                "params": {"fragment_id": target["fragment_id"]},
                "rationale": (
                    f"读取 {target['doc_id']} 的原文片段，核对原文是否支持回答"
                ),
                "terminal": False,
            }

        # 5. 全部读取后判断冲突
        if state["conflict_detected"]:
            return {
                "action": "conflict",
                "params": {
                    "topic": state["conflict_topic"],
                    "doc_ids": state["conflict_doc_ids"],
                },
                "rationale": (
                    "不同文档对同一问题给出不一致答案且无适用范围与优先级，"
                    "列出冲突与引用并请求确认适用制度，不凭空选择"
                ),
                "terminal": True,
            }

        # 6. 无冲突：基于原文有据回答
        return {
            "action": "answer",
            "params": {},
            "rationale": "引用原文可支持回答，给出带文档 ID 与原文片段的答案",
            "terminal": True,
        }


class RealLLM:
    """真实大模型决策实现（OpenAI 兼容接口）。

    环境变量：LLM_API_KEY、LLM_BASE_URL、LLM_MODEL。
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.base_url = os.getenv(
            "LLM_BASE_URL", "https://api.openai.com/v1"
        ).rstrip("/")
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """调用真实大模型决策，要求返回 JSON。"""
        prompt = (
            "你是企业知识问答 Agent 的决策模块。"
            "可用动作：document_search, fragment_reader, answer, conflict, gap, block。"
            "请根据当前状态选择下一步，只返回 JSON："
            '{"action": 动作名, "params": {}, "rationale": 依据, "terminal": false}。'
            f"当前状态：{json.dumps(state, ensure_ascii=False)}"
        )
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        decision = json.loads(body["choices"][0]["message"]["content"])
        decision.setdefault("params", {})
        decision.setdefault("terminal", False)
        return decision


def build_llm() -> tuple[Any, str]:
    """构建决策模型：配置 LLM_API_KEY 用 RealLLM，否则用离线 MockLLM。"""
    if os.getenv("LLM_API_KEY"):
        return RealLLM(), "RealLLM"
    return MockLLM(), "MockLLM"
