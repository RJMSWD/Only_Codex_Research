"""ACP (Agent Client Protocol) LLM client via acpx.

Uses acpx as the ACP bridge to communicate with any ACP-compatible agent
(Claude Code, Codex, Gemini CLI, etc.) via persistent named sessions.

Key advantage: a single persistent session maintains context across all
23 pipeline stages — the agent remembers everything.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any

from researchclaw.llm.client import LLMResponse

logger = logging.getLogger(__name__)

# acpx output markers
_DONE_RE = re.compile(r"^\[done\]")
_CLIENT_RE = re.compile(r"^\[client\]")
_ACPX_RE = re.compile(r"^\[acpx\]")
_TOOL_RE = re.compile(r"^\[tool\]")


@dataclass
class ACPConfig:
    """Configuration for ACP agent connection."""

    agent: str = "claude"
    cwd: str = "."
    acpx_command: str = ""  # auto-detect if empty
    session_name: str = "researchclaw"
    timeout_sec: int = 600  # per-prompt timeout


def _find_acpx() -> str | None:
    """Find the acpx binary — check PATH, then OpenClaw's plugin directory."""
    found = shutil.which("acpx")
    if found:
        return found
    # Check OpenClaw's bundled acpx plugin
    openclaw_acpx = os.path.expanduser(
        "~/.openclaw/extensions/acpx/node_modules/.bin/acpx"
    )
    if os.path.isfile(openclaw_acpx) and os.access(openclaw_acpx, os.X_OK):
        return openclaw_acpx
    return None


class ACPClient:
    """LLM client that uses acpx to communicate with ACP agents.

    Spawns persistent named sessions via acpx, reusing them across
    ``.chat()`` calls so the agent maintains context across the full
    23-stage pipeline.
    """

    def __init__(self, acp_config: ACPConfig) -> None:
        self.config = acp_config
        self._acpx: str | None = acp_config.acpx_command or None
        self._session_ready = False
        self._use_exec_only = False

    @classmethod
    def from_rc_config(cls, rc_config: Any) -> ACPClient:
        """Build from a ResearchClaw ``RCConfig``."""
        acp = rc_config.llm.acp
        return cls(ACPConfig(
            agent=acp.agent,
            cwd=acp.cwd,
            acpx_command=getattr(acp, "acpx_command", ""),
            session_name=getattr(acp, "session_name", "researchclaw"),
        ))

    # ------------------------------------------------------------------
    # Public interface (matches LLMClient)
    # ------------------------------------------------------------------

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
        """Send a prompt and return the agent's response.

        Parameters mirror ``LLMClient.chat()`` for drop-in compatibility.
        ``model``, ``max_tokens``, ``temperature``, and ``json_mode`` are
        accepted but not forwarded — the agent manages its own model and
        parameters.
        """
        normalized = list(messages or [])
        if user is not None:
            normalized.append({"role": "user", "content": user})
        if not normalized:
            raise ValueError("chat() requires messages or user input")

        prompt_text = self._messages_to_prompt(normalized, system=system)
        content = self._send_prompt(prompt_text)
        return LLMResponse(
            content=content,
            model=f"acp:{self.config.agent}",
            finish_reason="stop",
        )

    def preflight(self) -> tuple[bool, str]:
        """Check that acpx and the agent are available."""
        acpx = self._resolve_acpx()
        if not acpx:
            return False, (
                "acpx not found. Install it: npm install -g acpx  "
                "or set llm.acp.acpx_command in config."
            )
        # Check the agent binary exists
        agent = self.config.agent
        if not shutil.which(agent):
            return False, f"ACP agent CLI not found: {agent!r} (not on PATH)"
        # Create the session if supported; otherwise fall back to one-shot exec mode
        try:
            self._ensure_session()
            if self._use_exec_only:
                return True, f"OK - ACP exec mode ready ({agent} via acpx)"
            return True, f"OK - ACP session ready ({agent} via acpx)"
        except Exception as exc:  # noqa: BLE001
            return False, f"ACP session init failed: {exc}"

    def close(self) -> None:
        """Close the acpx session."""
        if not self._session_ready:
            return
        acpx = self._resolve_acpx()
        if not acpx:
            return
        try:
            subprocess.run(
                [acpx, "--cwd", self._abs_cwd(),
                 self.config.agent, "sessions", "close",
                 self.config.session_name],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
        except Exception:  # noqa: BLE001
            pass
        self._session_ready = False

    def __del__(self) -> None:
        """Best-effort cleanup on garbage collection."""
        try:
            self.close()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_acpx(self) -> str | None:
        """Resolve the acpx binary path (cached)."""
        if self._acpx:
            return self._acpx
        self._acpx = _find_acpx()
        return self._acpx

    def _abs_cwd(self) -> str:
        return os.path.abspath(self.config.cwd)

    def _ensure_session(self) -> None:
        """Find or create the named acpx session."""
        if self._session_ready:
            return
        acpx = self._resolve_acpx()
        if not acpx:
            raise RuntimeError("acpx not found")

        # Use 'ensure' which finds existing or creates new
        result = subprocess.run(
            [acpx, "--cwd", self._abs_cwd(),
             self.config.agent, "sessions", "ensure",
             "--name", self.config.session_name],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
        if result.returncode != 0:
            # Fall back to 'new'
            result = subprocess.run(
                [acpx, "--cwd", self._abs_cwd(),
                 self.config.agent, "sessions", "new",
                 "--name", self.config.session_name],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=30,
            )
            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                raise RuntimeError(
                    f"Failed to create ACP session: {stderr}"
                )

        # Some raw/custom ACP agents work only in one-shot exec mode even when
        # sessions commands exit 0. Probe the named session and degrade gracefully.
        probe = subprocess.run(
            [acpx, "--cwd", self._abs_cwd(),
             self.config.agent, "sessions", "show",
             self.config.session_name],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
        if probe.returncode != 0:
            self._use_exec_only = True
            self._session_ready = False
            logger.warning(
                "ACP agent '%s' has no usable persistent session in cwd %s; "
                "falling back to one-shot exec mode.",
                self.config.agent,
                self._abs_cwd(),
            )
            return

        self._session_ready = True
        logger.info("ACP session '%s' ready (%s)", self.config.session_name, self.config.agent)

    # Linux MAX_ARG_STRLEN is 128KB; stay well under to leave room for env
    _MAX_CLI_PROMPT_BYTES = 100_000

    def _send_prompt(self, prompt: str) -> str:
        """Send a prompt via acpx and return the response text.

        For large prompts that would exceed the OS argument-length limit
        (``E2BIG``), the prompt is written to a temp file and the agent
        is asked to read it.
        """
        acpx = self._resolve_acpx()
        if not acpx:
            raise RuntimeError("acpx not found")
        if not self._use_exec_only:
            self._ensure_session()

        prompt_bytes = len(prompt.encode("utf-8"))
        if self._use_exec_only:
            if prompt_bytes <= self._MAX_CLI_PROMPT_BYTES:
                return self._send_prompt_exec(acpx, prompt)
            logger.info(
                "Prompt too large for CLI arg (%d bytes). Using exec file mode.",
                prompt_bytes,
            )
            return self._send_prompt_exec_via_file(acpx, prompt)

        if prompt_bytes <= self._MAX_CLI_PROMPT_BYTES:
            return self._send_prompt_cli(acpx, prompt)

        logger.info(
            "Prompt too large for CLI arg (%d bytes). Using temp file.",
            prompt_bytes,
        )
        return self._send_prompt_via_file(acpx, prompt)

    def _send_prompt_cli(self, acpx: str, prompt: str) -> str:
        """Send prompt as a CLI argument (original path)."""
        result = subprocess.run(
            [acpx, "--approve-all", "--cwd", self._abs_cwd(),
             self.config.agent, "-s", self.config.session_name,
             prompt],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=self.config.timeout_sec,
        )

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if self._should_fallback_to_exec(stderr):
                self._use_exec_only = True
                self._session_ready = False
                logger.warning(
                    "ACP session prompt failed for agent '%s'; falling back to exec mode.",
                    self.config.agent,
                )
                return self._send_prompt_exec(acpx, prompt)
            raise RuntimeError(f"ACP prompt failed (exit {result.returncode}): {stderr}")

        return self._extract_response(result.stdout or "")

    def _send_prompt_via_file(self, acpx: str, prompt: str) -> str:
        """Write prompt to a temp file, ask the agent to read and respond."""
        fd, prompt_path = tempfile.mkstemp(
            suffix=".md", prefix="rc_prompt_"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(prompt)

            result = subprocess.run(
                [acpx, "--approve-all", "--cwd", self._abs_cwd(),
                 self.config.agent, "-s", self.config.session_name,
                 "--file", prompt_path],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=self.config.timeout_sec,
            )

            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                if self._should_fallback_to_exec(stderr):
                    self._use_exec_only = True
                    self._session_ready = False
                    logger.warning(
                        "ACP file prompt failed for agent '%s'; falling back to exec mode.",
                        self.config.agent,
                    )
                    return self._send_prompt_exec_via_file(acpx, prompt)
                raise RuntimeError(
                    f"ACP prompt failed (exit {result.returncode}): {stderr}"
                )

            return self._extract_response(result.stdout or "")
        finally:
            try:
                os.unlink(prompt_path)
            except OSError:
                pass

    @staticmethod
    def _should_fallback_to_exec(stderr: str) -> bool:
        return (
            "No acpx session found" in stderr
            or "No named session" in stderr
            or "status: no-session" in stderr
        )

    def _send_prompt_exec(self, acpx: str, prompt: str) -> str:
        """Send prompt in one-shot exec mode (no persistent session)."""
        result = subprocess.run(
            [acpx, "--approve-all", "--format", "quiet", "--cwd", self._abs_cwd(),
             self.config.agent, "exec", prompt],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=self.config.timeout_sec,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RuntimeError(f"ACP exec prompt failed (exit {result.returncode}): {stderr}")
        return (result.stdout or "").strip()

    def _send_prompt_exec_via_file(self, acpx: str, prompt: str) -> str:
        """Send large prompt via acpx exec --file."""
        fd, prompt_path = tempfile.mkstemp(suffix=".md", prefix="rc_prompt_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(prompt)
            result = subprocess.run(
                [acpx, "--approve-all", "--format", "quiet", "--cwd", self._abs_cwd(),
                 self.config.agent, "exec", "--file", prompt_path],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=self.config.timeout_sec,
            )
            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                raise RuntimeError(
                    f"ACP exec prompt failed (exit {result.returncode}): {stderr}"
                )
            return (result.stdout or "").strip()
        finally:
            try:
                os.unlink(prompt_path)
            except OSError:
                pass

    @staticmethod
    def _extract_response(raw_output: str) -> str:
        """Extract the agent's actual response from acpx output.

        Strips acpx metadata lines ([client], [acpx], [tool], [done])
        and their continuation lines (indented or sub-field lines like
        ``input:``, ``output:``, ``files:``, ``kind:``).
        """
        lines: list[str] = []
        in_tool_block = False
        for line in raw_output.splitlines():
            # Skip acpx control lines
            if _DONE_RE.match(line) or _CLIENT_RE.match(line) or _ACPX_RE.match(line):
                in_tool_block = False
                continue
            if _TOOL_RE.match(line):
                in_tool_block = True
                continue
            # Tool blocks have indented continuation lines
            if in_tool_block:
                if line.startswith("  ") or not line.strip():
                    continue
                # Non-indented, non-empty line = end of tool block
                in_tool_block = False
            # Skip empty lines at start
            if not lines and not line.strip():
                continue
            lines.append(line)

        # Trim trailing empty lines
        while lines and not lines[-1].strip():
            lines.pop()

        return "\n".join(lines)

    @staticmethod
    def _messages_to_prompt(
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
    ) -> str:
        """Flatten a chat-messages list into a single text prompt.

        Preserves role labels so the agent can distinguish context.
        """
        parts: list[str] = []
        if system:
            parts.append(f"[System]\n{system}")
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"[System]\n{content}")
            elif role == "assistant":
                parts.append(f"[Previous Response]\n{content}")
            else:
                parts.append(content)
        return "\n\n".join(parts)
