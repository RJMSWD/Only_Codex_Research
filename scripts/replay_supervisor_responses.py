#!/usr/bin/env python
"""Replay matching supervisor responses for repeated pipeline runs."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _last_user_content(payload: dict[str, Any]) -> str:
    messages = payload.get("messages", [])
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def _response_exists(responses_dir: Path, request_id: str) -> bool:
    return (responses_dir / f"{request_id}.json").exists()


def _copy_response(
    responses_dir: Path,
    *,
    source_id: str,
    target_id: str,
) -> Path:
    source_path = responses_dir / f"{source_id}.json"
    target_path = responses_dir / f"{target_id}.json"
    payload = _load_json(source_path)
    payload["request_id"] = target_id
    target_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return target_path


def _replay_pending_once(exchange_dir: Path) -> list[tuple[str, str]]:
    requests_dir = exchange_dir / "requests"
    responses_dir = exchange_dir / "responses"
    requests_dir.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)

    request_paths = sorted(requests_dir.glob("*.json"))
    request_payloads = {path.stem: _load_json(path) for path in request_paths}
    replayed: list[tuple[str, str]] = []

    for request_path in request_paths:
        request_id = request_path.stem
        if _response_exists(responses_dir, request_id):
            continue

        current_payload = request_payloads[request_id]
        current_content = _last_user_content(current_payload)
        if not current_content:
            continue

        matched_id = None
        for old_id, old_payload in request_payloads.items():
            if old_id == request_id:
                continue
            if old_id >= request_id:
                continue
            if not _response_exists(responses_dir, old_id):
                continue
            if _last_user_content(old_payload) == current_content:
                matched_id = old_id
                break

        if matched_id is None:
            continue

        _copy_response(responses_dir, source_id=matched_id, target_id=request_id)
        replayed.append((request_id, matched_id))

    return replayed


def _watch(exchange_dir: Path, poll_seconds: float) -> int:
    print(f"Watching {exchange_dir} for replayable supervisor requests...")
    while True:
        replayed = _replay_pending_once(exchange_dir)
        for new_id, old_id in replayed:
            print(f"{new_id} <- {old_id}")
        time.sleep(max(poll_seconds, 0.2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay exact-match supervisor responses from earlier runs."
    )
    parser.add_argument(
        "--exchange-dir",
        default=".researchclaw-supervisor",
        help="Supervisor exchange directory",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously watch and replay matching pending requests",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=1.0,
        help="Polling interval used with --watch",
    )
    args = parser.parse_args()

    exchange_dir = Path(args.exchange_dir)
    if args.watch:
        return _watch(exchange_dir, args.poll_seconds)

    replayed = _replay_pending_once(exchange_dir)
    if not replayed:
        print("No replayable pending requests found.")
        return 0

    for new_id, old_id in replayed:
        print(f"{new_id} <- {old_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
