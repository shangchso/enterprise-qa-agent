"""工具一：文档检索。

按问题中的关键词（含同义改写）匹配相关文档片段。追问时结合上下文话题
一起匹配。支持失败注入。

检索只返回候选片段的元信息与答案值，完整原文由 fragment_reader 读取，
体现两个工具的分工。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..data_store import DataStore


def _match(fragment: Dict[str, Any], text: str) -> bool:
    """判断片段的任一关键词是否出现在文本中。"""
    return any(keyword in text for keyword in fragment["keywords"])


def search_documents(
    store: DataStore,
    query: str,
    context_topic: Optional[str] = None,
) -> Dict[str, Any]:
    """检索相关文档片段。

    Args:
        store: 数据仓库。
        query: 用户问题。
        context_topic: 上一轮话题（追问时用于解析指代）。

    Returns:
        统一结构的工具返回结果。
    """
    tool = "document_search"
    arguments = {"query": query, "context_topic": context_topic}

    if store.is_tool_failed(tool):
        return {
            "ok": False,
            "tool": tool,
            "arguments": arguments,
            "error": "文档检索服务执行失败",
        }

    # 先按问题文本做关键词匹配
    text_hits = [
        fragment for fragment in store.all_fragments() if _match(fragment, query)
    ]

    # 文本未命中任何片段时，才用上下文话题兜底（解析指代）
    if not text_hits and context_topic:
        text_hits = [
            fragment
            for fragment in store.all_fragments()
            if fragment["topic"] == context_topic
        ]

    matched = [
        {
            "fragment_id": fragment["fragment_id"],
            "doc_id": fragment["doc_id"],
            "doc_title": fragment["doc_title"],
            "version_date": fragment["version_date"],
            "topic": fragment["topic"],
            "answer_value": fragment["answer_value"],
        }
        for fragment in text_hits
    ]

    return {
        "ok": True,
        "tool": tool,
        "arguments": arguments,
        "result": {
            "candidates": matched,
            "candidate_count": len(matched),
            "doc_ids": sorted({item["doc_id"] for item in matched}),
        },
    }
