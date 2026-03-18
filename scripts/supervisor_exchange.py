#!/usr/bin/env python
"""Utility for inspecting and answering ResearchClaw supervisor requests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _request_dirs(exchange_dir: Path) -> tuple[Path, Path]:
    requests_dir = exchange_dir / "requests"
    responses_dir = exchange_dir / "responses"
    requests_dir.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)
    return requests_dir, responses_dir


def _iter_pending(exchange_dir: Path) -> list[Path]:
    requests_dir, responses_dir = _request_dirs(exchange_dir)
    pending: list[Path] = []
    for request_path in sorted(requests_dir.glob("*.json")):
        response_path = responses_dir / request_path.name
        try:
            request = _load_json(request_path)
        except json.JSONDecodeError:
            continue
        if request.get("status") == "completed":
            continue
        if response_path.exists():
            continue
        pending.append(request_path)
    return pending


def cmd_pending(args: argparse.Namespace) -> int:
    pending = _iter_pending(Path(args.exchange_dir))
    if not pending:
        print("No pending supervisor requests.")
        return 0

    for path in pending:
        request = _load_json(path)
        print(
            json.dumps(
                {
                    "id": request.get("id"),
                    "created_at": request.get("created_at"),
                    "model": request.get("model"),
                    "json_mode": request.get("json_mode"),
                    "message_count": len(request.get("messages", [])),
                    "path": str(path),
                },
                ensure_ascii=False,
            )
        )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    exchange_dir = Path(args.exchange_dir)
    request_path = exchange_dir / "requests" / f"{args.request_id}.json"
    request = _load_json(request_path)
    print(json.dumps(request, indent=2, ensure_ascii=False))
    return 0


def _response_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.json_file:
        return _load_json(Path(args.json_file))

    if args.content_file:
        content = Path(args.content_file).read_text(encoding="utf-8")
    elif args.stdin:
        import sys

        content = sys.stdin.read()
    else:
        content = args.content or ""

    payload: dict[str, Any] = {
        "content": content,
        "model": args.model,
        "finish_reason": args.finish_reason,
    }
    return payload


def cmd_respond(args: argparse.Namespace) -> int:
    exchange_dir = Path(args.exchange_dir)
    _, responses_dir = _request_dirs(exchange_dir)
    response_path = responses_dir / f"{args.request_id}.json"
    payload = _response_payload(args)
    response_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(response_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect and answer AutoResearchClaw supervisor requests."
    )
    parser.add_argument(
        "--exchange-dir",
        default=".researchclaw-supervisor",
        help="Supervisor exchange directory",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    pending_p = sub.add_parser("pending", help="List pending requests")
    pending_p.set_defaults(func=cmd_pending)

    show_p = sub.add_parser("show", help="Print a request payload")
    show_p.add_argument("request_id", help="Request ID without .json")
    show_p.set_defaults(func=cmd_show)

    respond_p = sub.add_parser("respond", help="Write a response payload")
    respond_p.add_argument("request_id", help="Request ID without .json")
    respond_p.add_argument("--content", help="Response content text")
    respond_p.add_argument("--content-file", help="Read response content from file")
    respond_p.add_argument("--json-file", help="Use a full response JSON file")
    respond_p.add_argument(
        "--stdin", action="store_true", help="Read response content from stdin"
    )
    respond_p.add_argument("--model", default="codex-supervisor")
    respond_p.add_argument("--finish-reason", default="stop")
    respond_p.set_defaults(func=cmd_respond)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
