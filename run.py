"""命令行入口（CLI 运行方式）。

可复制的运行命令示例：
    python run.py --list
    python run.py --question-id Q1          # 明确答案
    python run.py --question-id Q2          # 文档冲突
    python run.py --question-id Q3          # 资料外问题
    python run.py --question-id Q4          # 改写后的相似问题
    python run.py --question-id Q5          # 上下文追问（自动两轮）
    python run.py --question-id Q6 --fail-tool document_search  # 工具失败
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from src.agent import EnterpriseQaAgent
from src.data_store import DataStore
from src.llm import build_llm


def print_json(obj: Dict[str, Any]) -> None:
    """以可读 JSON 输出。"""
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def list_questions(store: DataStore) -> None:
    """列出全部问题场景。"""
    questions_path = Path(store.data_dir) / "questions.json"
    with questions_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    print("可用问题列表：")
    for item in data["questions"]:
        print(
            f"  - {item['question_id']} [{item['scenario']}]: {item['question']}"
        )


def save_trace(
    payload: Dict[str, Any], trace_dir: Path, name: str
) -> Path:
    """把结果落盘到 examples/traces/。"""
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / f"trace_{name}.json"
    with trace_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return trace_path


def parse_args(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="企业知识问答 Agent（CLI）")
    parser.add_argument("--question-id", "-q", help="问题场景 ID，如 Q1")
    parser.add_argument("--data-dir", default="data", help="数据目录，默认 data")
    parser.add_argument(
        "--fail-tool",
        choices=["document_search", "fragment_reader"],
        help="向指定工具注入失败",
    )
    parser.add_argument("--max-steps", type=int, default=10, help="最大步数")
    parser.add_argument("--tag", default=None, help="Trace 文件名后缀")
    parser.add_argument(
        "--trace-dir", default="examples/traces", help="Trace 目录"
    )
    parser.add_argument("--list", action="store_true", help="列出问题后退出")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    """主流程。"""
    args = parse_args(argv if argv is not None else sys.argv[1:])
    store = DataStore(args.data_dir)

    if args.list:
        list_questions(store)
        return 0

    if not args.question_id:
        print(
            "错误：请通过 --question-id 指定问题，或使用 --list 查看",
            file=sys.stderr,
        )
        return 2

    scenario = store.get_question(args.question_id)
    if scenario is None:
        print(f"错误：未找到问题场景 {args.question_id}", file=sys.stderr)
        return 2

    if args.fail_tool:
        store.failed_tool = args.fail_tool

    llm, llm_name = build_llm()
    agent = EnterpriseQaAgent(
        store, llm=llm, llm_name=llm_name, max_steps=args.max_steps
    )

    # 第一轮
    first = agent.run(scenario["question"])
    tag = args.tag or args.question_id
    first_path = save_trace(first, Path(args.trace_dir), tag)
    print(f"===== 第一轮结果（Trace：{first_path}）=====")
    print_json(first)

    # 上下文追问：第二轮（复用对话历史）
    if scenario.get("follow_up"):
        if first.get("topic"):
            store.add_to_history(scenario["question"], first["topic"])
        follow = agent.run(
            scenario["follow_up"], context_topic=store.last_topic()
        )
        follow_tag = f"{tag}_followup"
        follow_path = save_trace(follow, Path(args.trace_dir), follow_tag)
        print(f"===== 追问结果（Trace：{follow_path}）=====")
        print_json(follow)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
