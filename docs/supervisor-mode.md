# Supervisor Mode

This is the default transport mode for `Only_Codex_Research`.

This repository has been adapted to support a filesystem-backed `supervisor`
LLM provider. In this mode, the pipeline does not call ACP or a remote LLM
API directly. Instead, it writes requests into `.researchclaw-supervisor/requests`
and waits for a compatible external supervisor to write responses into
`.researchclaw-supervisor/responses`.

## What Changed

- `llm.provider: "supervisor"` is now a first-class provider path.
- health checks accept supervisor mode without requiring API keys.
- pipeline execution can run with a local Python interpreter and filesystem
  request/response exchange.
- targeted code repair prompt formatting was fixed so runtime repair no longer
  crashes on literal `{target_file}` text.

## Core Files

- `researchclaw/llm/supervisor_client.py`
- `researchclaw/llm/client.py`
- `researchclaw/llm/__init__.py`
- `researchclaw/config.py`
- `researchclaw/health.py`
- `researchclaw/pipeline/executor.py`
- `researchclaw/pipeline/runner.py`
- `researchclaw/pipeline/code_agent.py`

## Local Helper Scripts

- `scripts/supervisor_exchange.py`
  Inspect pending requests and write responses manually.
- `scripts/verify_supervisor_response.py`
  Extract `filename:...` fenced code blocks from a response and `py_compile`
  the Python files before handing them back to the pipeline.
- `scripts/replay_supervisor_responses.py`
  Replay exact-match responses from earlier runs for repeated stages.

## Minimal Config Example

```yaml
llm:
  provider: "supervisor"
  primary_model: "codex-supervisor"
  fallback_models: []
  supervisor:
    exchange_dir: ".researchclaw-supervisor"
    timeout_sec: 3600
    poll_interval_sec: 1.0

experiment:
  mode: "sandbox"
  sandbox:
    python_path: "C:\\path\\to\\python.exe"
```

## Typical Workflow

1. Run `only-codex-research run ...` with a config that sets `llm.provider` to
   `supervisor`. A safe starter config is `config.only_codex.example.yaml`.
2. Inspect pending requests:

   ```bash
   python scripts/supervisor_exchange.py pending
   ```

3. Show a request:

   ```bash
   python scripts/supervisor_exchange.py show 20260318-015410-0001
   ```

4. Answer with a prepared JSON payload:

   ```bash
   python scripts/supervisor_exchange.py respond 20260318-015410-0001 --json-file response.json
   ```

5. Optionally replay matching responses from earlier runs:

   ```bash
   python scripts/replay_supervisor_responses.py --watch
   ```

6. Optionally verify code-generation responses before writing them back:

   ```bash
   python scripts/verify_supervisor_response.py .researchclaw-supervisor/responses/20260318-015410-0001.json
   ```

## Intended Use

This mode is useful when:

- an external coding agent or orchestrator is acting as the real LLM supervisor
- local reruns should reuse validated earlier responses
- ACP is not desired
- remote API credentials should not be part of the run path
