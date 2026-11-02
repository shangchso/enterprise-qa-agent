"""Agent 可调用的知识检索工具集合。

包含两个工具：
- document_search: 文档检索（按关键词匹配相关片段）
- fragment_reader: 片段读取（读取原文片段用于回答与查证）
"""

from .document_search import search_documents
from .fragment_reader import read_fragment

__all__ = [
    "search_documents",
    "read_fragment",
]
