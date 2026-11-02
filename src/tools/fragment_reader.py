"""工具二：片段读取。

按片段 ID 读取完整原文片段，用于回答与冲突查证。支持失败注入。
"""

from __future__ import annotations

from typing import Any, Dict

from ..data_store import DataStore


def read_fragment(store: DataStore, fragment_id: str) -> Dict[str, Any]:
    """读取原文片段。

    Args:
        store: 数据仓库。
        fragment_id: 片段 ID。

    Returns:
        统一结构的工具返回结果。
    """
    tool = "fragment_reader"
    arguments = {"fragment_id": fragment_id}

    if store.is_tool_failed(tool):
        return {
            "ok": False,
            "tool": tool,
            "arguments": arguments,
            "error": "片段读取工具执行失败",
        }

    fragment = store.get_fragment(fragment_id)
    if fragment is None:
        return {
            "ok": False,
            "tool": tool,
            "arguments": arguments,
            "error": f"未找到片段 {fragment_id}",
        }

    return {
        "ok": True,
        "tool": tool,
        "arguments": arguments,
        "result": {
            "fragment_id": fragment["fragment_id"],
            "doc_id": fragment["doc_id"],
            "doc_title": fragment["doc_title"],
            "version_date": fragment["version_date"],
            "topic": fragment["topic"],
            "text": fragment["text"],
        },
    }
