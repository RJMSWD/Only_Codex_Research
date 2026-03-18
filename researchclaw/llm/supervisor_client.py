"""Filesystem-backed LLM client for external supervisor orchestration."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from typing import Any

from researchclaw.llm.client import LLMResponse

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class SupervisorLLMConfig:
    exchange_dir: str = ".researchclaw-supervisor"
    primary_model: str = "codex-supervisor"
    fallback_models: list[str] = field(default_factory=list)
    timeout_sec: int = 3600
    poll_interval_sec: float = 1.0


class SupervisorClient:
    """LLM client that exchanges requests and responses via the filesystem."""

    def __init__(self, config: SupervisorLLMConfig) -> None:
        self.config = config
        self._counter = count(1)
        self._root = Path(config.exchange_dir)
        self._requests_dir = self._root / "requests"
        self._responses_dir = self._root / "responses"
        self._completed_dir = self._root / "completed"

    @classmethod
    def from_rc_config(cls, rc_config: Any) -> SupervisorClient:
        supervisor = rc_config.llm.supervisor
        return cls(
            SupervisorLLMConfig(
                exchange_dir=supervisor.exchange_dir,
                primary_model=rc_config.llm.primary_model or "codex-supervisor",
                fallback_models=list(rc_config.llm.fallback_models or []),
                timeout_sec=supervisor.timeout_sec,
                poll_interval_sec=supervisor.poll_interval_sec,
            )
        )

    def preflight(self) -> tuple[bool, str]:
        try:
            self._ensure_dirs()
        except OSError as exc:
            return False, f"Supervisor exchange directory is not writable: {exc}"
        return True, f"OK - supervisor exchange ready at {self._root.resolve()}"

    def chat(
        self,
        messages: list[dict[str, str]] | None = None,
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
        system: str | None = None,
        user: str | None = None,
    ) -> LLMResponse:
        request_id = self._next_request_id()
        chosen_model = model or self.config.primary_model
        conversation = self._normalize_messages(messages, user=user)
        request_path = self._requests_dir / f"{request_id}.json"
        response_path = self._responses_dir / f"{request_id}.json"

        self._ensure_dirs()
        payload = {
            "id": request_id,
            "created_at": _utcnow_iso(),
            "provider": "supervisor",
            "model": chosen_model,
            "system": system or "",
            "messages": conversation,
            "conversation": (
                [{"role": "system", "content": system}] + conversation
                if system
                else conversation
            ),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "json_mode": json_mode,
            "status": "pending",
        }
        request_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Supervisor request queued: %s", request_path)

        response = self._wait_for_response(response_path)
        content = self._extract_content(response)
        self._archive_request(request_path, response_path, payload, response)

        return LLMResponse(
            content=content,
            model=str(response.get("model", chosen_model)),
            finish_reason=str(response.get("finish_reason", "stop")),
            raw={
                "request_id": request_id,
                "request_path": str(request_path),
                "response_path": str(response_path),
            },
        )

    def _ensure_dirs(self) -> None:
        self._requests_dir.mkdir(parents=True, exist_ok=True)
        self._responses_dir.mkdir(parents=True, exist_ok=True)
        self._completed_dir.mkdir(parents=True, exist_ok=True)

    def _next_request_id(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"{ts}-{next(self._counter):04d}"

    def _normalize_messages(
        self,
        messages: list[dict[str, str]] | None,
        *,
        user: str | None,
    ) -> list[dict[str, str]]:
        normalized = list(messages or [])
        if user is not None:
            normalized.append({"role": "user", "content": user})
        if not normalized:
            raise ValueError("Supervisor chat() requires messages or user input")
        return normalized

    def _wait_for_response(self, response_path: Path) -> dict[str, Any]:
        deadline = time.monotonic() + max(self.config.timeout_sec, 1)
        while time.monotonic() < deadline:
            if response_path.exists():
                try:
                    loaded = json.loads(response_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    time.sleep(self.config.poll_interval_sec)
                    continue
                if isinstance(loaded, dict):
                    return loaded
                return {"content": str(loaded)}
            time.sleep(self.config.poll_interval_sec)
        raise TimeoutError(
            f"Timed out waiting for supervisor response: {response_path}"
        )

    def _extract_content(self, response: dict[str, Any]) -> str:
        if "content" in response:
            return str(response["content"])
        if "json" in response:
            return json.dumps(response["json"], ensure_ascii=False)
        raise ValueError("Supervisor response must contain 'content' or 'json'")

    def _archive_request(
        self,
        request_path: Path,
        response_path: Path,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
    ) -> None:
        updated_request = dict(request_payload)
        updated_request["status"] = "completed"
        updated_request["answered_at"] = _utcnow_iso()
        updated_request["response_file"] = str(response_path)
        request_path.write_text(
            json.dumps(updated_request, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        archive_path = self._completed_dir / request_path.name
        archive_path.write_text(
            json.dumps(
                {"request": updated_request, "response": response_payload},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
