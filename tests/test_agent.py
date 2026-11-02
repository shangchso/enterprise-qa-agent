"""企业知识问答 Agent 单元测试。

覆盖笔试全部验收点：明确答案、文档冲突、资料外问题、改写相似问题、
上下文追问、工具失败，以及步数上限等补充场景。

运行命令：
    python -m unittest discover -s tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import EnterpriseQaAgent
from src.data_store import DataStore
from src.llm import MockLLM


class EnterpriseQaAgentTest(unittest.TestCase):
    """Agent 检索与冲突处理测试。"""

    def setUp(self) -> None:
        self.store = DataStore(PROJECT_ROOT / "data")
        self.llm = MockLLM()
        self.agent = EnterpriseQaAgent(
            self.store, llm=self.llm, llm_name="MockLLM", max_steps=10
        )

    def _scenario(self, question_id: str) -> dict:
        return self.store.get_question(question_id)

    def test_clear_answer_with_citation(self) -> None:
        """明确答案：基于原文回答并带文档 ID 引用。"""
        scenario = self._scenario("Q1")
        result = self.agent.run(scenario["question"])
        self.assertEqual(result["review_status"], "answered")
        self.assertIn("5 天", result["answer"])
        self.assertEqual(result["citations"][0]["doc_id"], "D03")
        self.assertTrue(result["citations"][0]["original_text"])

    def test_document_conflict_needs_confirmation(self) -> None:
        """文档冲突：列出两个冲突文档，不擅自选答案。"""
        scenario = self._scenario("Q2")
        result = self.agent.run(scenario["question"])
        self.assertEqual(result["review_status"], "needs_confirmation")
        doc_ids = {item["doc_id"] for item in result["conflict_items"]}
        self.assertEqual(doc_ids, {"D01", "D02"})
        self.assertEqual(len(result["citations"]), 0)

    def test_out_of_scope_returns_gap(self) -> None:
        """资料外问题：返回资料缺口，不编造答案。"""
        scenario = self._scenario("Q3")
        result = self.agent.run(scenario["question"])
        self.assertEqual(result["review_status"], "out_of_scope")
        self.assertTrue(result["information_gap"])
        self.assertEqual(result["answer"], "")

    def test_rephrased_question_matches(self) -> None:
        """改写后的相似问题：同义改写仍能检索到正确文档。"""
        scenario = self._scenario("Q4")
        result = self.agent.run(scenario["question"])
        self.assertEqual(result["review_status"], "answered")
        self.assertEqual(result["citations"][0]["doc_id"], "D05")
        self.assertIn("300 元", result["answer"])

    def test_context_follow_up(self) -> None:
        """上下文追问：结合历史解析指代，回答第二个片段。"""
        scenario = self._scenario("Q5")
        first = self.agent.run(scenario["question"])
        self.assertEqual(first["topic"], "密码重置")

        self.store.add_to_history(scenario["question"], first["topic"])
        follow = self.agent.run(
            scenario["follow_up"], context_topic=self.store.last_topic()
        )
        self.assertEqual(follow["review_status"], "answered")
        self.assertIn("无需管理员审批", follow["answer"])
        self.assertEqual(follow["citations"][0]["fragment_id"], "D04-F2")

    def test_tool_failure_blocked(self) -> None:
        """工具失败：检索注入失败后阻断，不编造。"""
        self.store.failed_tool = "document_search"
        scenario = self._scenario("Q6")
        result = self.agent.run(scenario["question"])
        self.assertEqual(result["review_status"], "blocked")
        self.assertIn("工具失败", result["information_gap"])

    def test_step_limit_returns_incomplete(self) -> None:
        """步数上限：极小步数返回明确未完成状态。"""
        agent = EnterpriseQaAgent(
            self.store, llm=self.llm, max_steps=1
        )
        result = agent.run("报销期限是多久？")
        self.assertEqual(result["review_status"], "incomplete")
        self.assertIn("最大步数", result["information_gap"])


if __name__ == "__main__":
    unittest.main()
