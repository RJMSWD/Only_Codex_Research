from __future__ import annotations

import json
from pathlib import Path

import pytest

from researchclaw.config import RCConfig
from researchclaw.llm import create_llm_client
from researchclaw.llm.supervisor_client import SupervisorClient


def _supervisor_config_data(tmp_path: Path) -> dict[str, object]:
    return {
        "project": {"name": "rc-supervisor-test", "mode": "docs-first"},
        "research": {"topic": "filesystem supervisor"},
        "runtime": {"timezone": "UTC"},
        "notifications": {"channel": "local"},
        "knowledge_base": {"backend": "markdown", "root": str(tmp_path / "kb")},
        "openclaw_bridge": {},
        "llm": {
            "provider": "supervisor",
            "primary_model": "codex-supervisor",
            "fallback_models": ["codex-fallback"],
            "supervisor": {
                "exchange_dir": str(tmp_path / "exchange"),
                "timeout_sec": 1,
                "poll_interval_sec": 0.01,
            },
        },
        "experiment": {"mode": "sandbox"},
    }


@pytest.fixture()
def rc_config(tmp_path: Path) -> RCConfig:
    return RCConfig.from_dict(
        _supervisor_config_data(tmp_path),
        project_root=tmp_path,
        check_paths=False,
    )


def test_create_llm_client_returns_supervisor_client(rc_config: RCConfig) -> None:
    client = create_llm_client(rc_config)

    assert isinstance(client, SupervisorClient)


def test_supervisor_client_preflight_creates_exchange_dir(rc_config: RCConfig) -> None:
    client = SupervisorClient.from_rc_config(rc_config)

    ok, detail = client.preflight()

    assert ok is True
    assert "supervisor exchange ready" in detail.lower()
    assert Path(rc_config.llm.supervisor.exchange_dir).exists()


def test_supervisor_client_chat_writes_request_and_archive(
    rc_config: RCConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = SupervisorClient.from_rc_config(rc_config)
    request_id = "20260318-000000-0001"
    exchange_dir = Path(rc_config.llm.supervisor.exchange_dir)
    response_path = exchange_dir / "responses" / f"{request_id}.json"
    response_payload = {
        "content": "supervisor reply",
        "model": "codex-supervisor",
        "finish_reason": "stop",
    }

    client._ensure_dirs()
    response_path.write_text(
        json.dumps(response_payload, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(client, "_next_request_id", lambda: request_id)

    result = client.chat(user="ping", system="system prompt")

    request_path = exchange_dir / "requests" / f"{request_id}.json"
    completed_path = exchange_dir / "completed" / f"{request_id}.json"
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    archive_payload = json.loads(completed_path.read_text(encoding="utf-8"))

    assert result.content == "supervisor reply"
    assert result.model == "codex-supervisor"
    assert request_payload["status"] == "completed"
    assert request_payload["messages"] == [{"role": "user", "content": "ping"}]
    assert request_payload["conversation"][0] == {
        "role": "system",
        "content": "system prompt",
    }
    assert archive_payload["response"]["content"] == "supervisor reply"
