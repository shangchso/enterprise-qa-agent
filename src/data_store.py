"""内存数据存储层。

加载 data/ 下的合成文档与问题数据，将文档片段展平为可检索单元，
并维护对话历史。提供 failed_tool 注入开关模拟工具失败。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class DataStore:
    """基于 JSON 文件的内存数据仓库。"""

    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self._questions: Dict[str, Dict[str, Any]] = {}
        # 展平后的片段列表，每个片段附带所属文档信息
        self._fragments: List[Dict[str, Any]] = []
        # 对话历史，用于上下文追问
        self._conversation_history: List[Dict[str, str]] = []
        # 失败注入：document_search 或 fragment_reader
        self.failed_tool: Optional[str] = None
        self.load()

    def load(self) -> None:
        """从 JSON 文件加载数据并展平片段。"""
        with (self.data_dir / "questions.json").open("r", encoding="utf-8") as f:
            question_data = json.load(f)
        for question in question_data["questions"]:
            self._questions[question["question_id"]] = question

        with (self.data_dir / "documents.json").open("r", encoding="utf-8") as f:
            document_data = json.load(f)

        for document in document_data["documents"]:
            for fragment in document["fragments"]:
                self._fragments.append(
                    {
                        "fragment_id": fragment["fragment_id"],
                        "doc_id": document["doc_id"],
                        "doc_title": document["title"],
                        "version_date": document["version_date"],
                        "topic": fragment["topic"],
                        "text": fragment["text"],
                        "answer_value": fragment["answer_value"],
                        "keywords": fragment["keywords"],
                    }
                )

    # ---------- 问题 ----------
    def get_question(self, question_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 获取问题场景。"""
        return self._questions.get(question_id)

    # ---------- 片段 ----------
    def all_fragments(self) -> List[Dict[str, Any]]:
        """获取全部展平片段。"""
        return self._fragments

    def get_fragment(self, fragment_id: str) -> Optional[Dict[str, Any]]:
        """按片段 ID 获取单个片段。"""
        for fragment in self._fragments:
            if fragment["fragment_id"] == fragment_id:
                return fragment
        return None

    # ---------- 对话历史 ----------
    def add_to_history(self, question: str, topic: str) -> None:
        """记录一轮问答的主题，供追问时解析指代。"""
        self._conversation_history.append({"question": question, "topic": topic})

    def get_history(self) -> List[Dict[str, str]]:
        """获取对话历史。"""
        return self._conversation_history

    def last_topic(self) -> Optional[str]:
        """获取上一轮话题，没有历史返回 None。"""
        if self._conversation_history:
            return self._conversation_history[-1]["topic"]
        return None

    # ---------- 失败注入 ----------
    def is_tool_failed(self, tool: str) -> bool:
        """判断工具是否被注入失败。"""
        return self.failed_tool == tool

    def reset_runtime(self) -> None:
        """清空对话历史并关闭失败注入。"""
        self._conversation_history.clear()
        self.failed_tool = None
