"""Agent 核心：ReAct 检索与冲突处理循环。

循环结构：
    模型选择动作 → 执行工具 → 观察结果 → 模型调整下一步或结束

核心能力：
- 检索后读取原文，引用原文支持回答；
- 检测同一话题下的答案冲突，冲突时列引用并请求确认，不凭空选择；
- 资料外问题返回资料缺口；
- 结合对话历史支持上下文追问；
- max_steps 限制步数，超限返回明确未完成状态。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import tools
from .data_store import DataStore
from .llm import MockLLM


class EnterpriseQaAgent:
    """企业知识问答 Agent。"""

    def __init__(
        self,
        store: DataStore,
        llm: Optional[Any] = None,
        llm_name: str = "MockLLM",
        max_steps: int = 10,
    ) -> None:
        self.store = store
        self.llm = llm or MockLLM()
        self.llm_name = llm_name
        self.max_steps = max_steps

    def run(
        self, question: str, context_topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """对单个问题执行完整 ReAct 循环。"""
        state = self._initial_state(question, context_topic)
        trace: List[Dict[str, Any]] = []
        terminal_action: Optional[str] = None
        terminal_reason = ""

        for step in range(1, self.max_steps + 1):
            decision = self.llm.decide(state)
            action = decision["action"]
            params = decision.get("params", {})

            if action in ("answer", "conflict", "gap", "block"):
                terminal_action = action
                terminal_reason = params.get("reason", decision.get("rationale", ""))
                trace.append(
                    {
                        "step": step,
                        "action": action,
                        "tool_arguments": params,
                        "observation_summary": f"终结动作：{decision['rationale']}",
                        "decision_rationale": decision["rationale"],
                    }
                )
                break

            response = self._execute(action, params, state)
            self._update_state(action, response, state)
            trace.append(
                {
                    "step": step,
                    "action": action,
                    "tool_arguments": response.get("arguments", params)
                    if response
                    else params,
                    "observation_summary": self._summarize(action, response),
                    "decision_rationale": decision["rationale"],
                }
            )
        else:
            terminal_action = "step_limit"
            terminal_reason = f"达到最大步数 {self.max_steps}，任务未完成"

        return self._build_result(
            state, trace, terminal_action, terminal_reason
        )

    # ---------- 初始状态 ----------
    def _initial_state(
        self, question: str, context_topic: Optional[str]
    ) -> Dict[str, Any]:
        return {
            "question": question,
            "context_topic": context_topic,
            "search_done": False,
            "candidates": [],
            "read_fragments": {},
            "conflict_detected": False,
            "conflict_topic": None,
            "conflict_doc_ids": [],
            "tool_failed": None,
        }

    # ---------- 动作执行 ----------
    def _execute(
        self, action: str, params: Dict[str, Any], state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if action == "document_search":
            return tools.search_documents(
                self.store,
                params["query"],
                context_topic=params.get("context_topic"),
            )
        if action == "fragment_reader":
            return tools.read_fragment(self.store, params["fragment_id"])
        return None

    # ---------- 状态更新 ----------
    def _update_state(
        self,
        action: str,
        response: Optional[Dict[str, Any]],
        state: Dict[str, Any],
    ) -> None:
        if action == "document_search":
            state["search_done"] = True
            if response["ok"]:
                state["candidates"] = response["result"]["candidates"]
                self._detect_conflict(state)
            else:
                state["tool_failed"] = response["error"]
            return

        if action == "fragment_reader":
            if response["ok"]:
                result = response["result"]
                state["read_fragments"][result["fragment_id"]] = result
            else:
                state["tool_failed"] = response["error"]
            return

    def _detect_conflict(self, state: Dict[str, Any]) -> None:
        """同 topic 下出现不同 answer_value 即判定为冲突。"""
        topics: Dict[str, set] = {}
        topic_docs: Dict[str, set] = {}
        for candidate in state["candidates"]:
            topic = candidate["topic"]
            topics.setdefault(topic, set()).add(candidate["answer_value"])
            topic_docs.setdefault(topic, set()).add(candidate["doc_id"])

        for topic, values in topics.items():
            if len(values) > 1:
                state["conflict_detected"] = True
                state["conflict_topic"] = topic
                state["conflict_doc_ids"] = sorted(topic_docs[topic])

    # ---------- 摘要 ----------
    def _summarize(
        self, action: str, response: Optional[Dict[str, Any]]
    ) -> str:
        if response is None:
            return f"{action} 完成"
        if not response.get("ok", True):
            return f"{action} 返回失败：{response.get('error')}"
        result = response["result"]
        if action == "document_search":
            return (
                f"document_search 命中 {result['candidate_count']} 个候选，"
                f"文档：{result['doc_ids']}"
            )
        if action == "fragment_reader":
            return f"fragment_reader 读取原文：{result['text']}"
        return f"{action} 完成"

    # ---------- 结果组装 ----------
    def _build_result(
        self,
        state: Dict[str, Any],
        trace: List[Dict[str, Any]],
        terminal_action: str,
        terminal_reason: str,
    ) -> Dict[str, Any]:
        status_map = {
            "answer": "answered",
            "conflict": "needs_confirmation",
            "gap": "out_of_scope",
            "block": "blocked",
            "step_limit": "incomplete",
        }
        review_status = status_map.get(terminal_action, "incomplete")

        result: Dict[str, Any] = {
            "question": state["question"],
            "review_status": review_status,
            "topic": None,
            "answer": "",
            "citations": [],
            "conflict_items": [],
            "information_gap": terminal_reason
            if review_status in ("out_of_scope", "blocked", "incomplete")
            else "",
            "steps_used": len(trace),
            "llm_name": self.llm_name,
            "trace": trace,
        }

        read = list(state["read_fragments"].values())

        if terminal_action == "answer":
            result["topic"] = read[0]["topic"]
            citations = [
                {
                    "doc_id": item["doc_id"],
                    "fragment_id": item["fragment_id"],
                    "version_date": item["version_date"],
                    "original_text": item["text"],
                }
                for item in read
            ]
            result["answer"] = read[0]["text"]
            result["citations"] = citations

        if terminal_action == "conflict":
            result["topic"] = state["conflict_topic"]
            fragments_by_id = {item["fragment_id"]: item for item in read}
            result["conflict_items"] = [
                {
                    "doc_id": item["doc_id"],
                    "doc_title": item["doc_title"],
                    "version_date": item["version_date"],
                    "answer_value": item["answer_value"],
                    "original_text": fragments_by_id[item["fragment_id"]]["text"],
                }
                for item in state["candidates"]
                if item["topic"] == state["conflict_topic"]
            ]
            result["answer"] = (
                f"关于「{state['conflict_topic']}」存在制度冲突，"
                "请确认适用制度后再作答"
            )

        return result
