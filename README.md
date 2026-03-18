# Only_Codex_Research

Codex-first autonomous research pipeline for turning an idea into a paper.

This repository is derived from `AutoResearchClaw`. The core pipeline, stage structure, and execution framework come from that project. The key difference is operational:

- `Only_Codex_Research` is designed to be run directly by Codex.
- The default workflow does not require OpenClaw as the top-level orchestrator.
- The default workflow does not require ACP as the primary transport.
- The intended path is: sign in to Codex, let Codex read this repository, and let Codex coordinate sub-agents through the filesystem-backed `supervisor` mode to complete the end-to-end paper workflow.

## What Makes This Repo Different

- Codex is the default orchestrator.
- Sub-agent roles, responsibilities, and reasoning strength are documented in [AGENTS.md](AGENTS.md).
- The out-of-box config is [config.only_codex.example.yaml](config.only_codex.example.yaml).
- The default LLM backend is `llm.provider: "supervisor"`, so the pipeline can exchange requests and responses through local files instead of ACP or remote API credentials.

## Public Repo Safety

This publishable repository intentionally excludes:

- local API keys
- machine-specific Python paths
- local experiment outputs
- caches, checkpoints, and runtime artifacts
- local-only configs such as `config*.local.yaml`

## Quick Start

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/Only_Codex_Research.git
cd Only_Codex_Research
pip install -e .
cp config.only_codex.example.yaml config.local.yaml
```

Then open the repository in Codex and use a prompt like:

```text
Read AGENTS.md and config.only_codex.example.yaml first.
Use Codex as the top-level orchestrator.
Create the recommended sub-agents only when needed.
Ask me only if blocked by missing external information.
Then validate the config, run doctor, and start the end-to-end paper workflow for this topic: <YOUR_TOPIC>.
```

Before the first real run, Codex should resolve `experiment.sandbox.python_path`
to the active interpreter in the current environment and update `config.local.yaml`
if needed.

Typical commands:

```bash
researchclaw validate --config config.local.yaml --no-check-paths
researchclaw doctor --config config.local.yaml
researchclaw run --config config.local.yaml --topic "Your research topic" --auto-approve
```

## Codex-First Workflow

1. Codex reads [AGENTS.md](AGENTS.md) and learns the default multi-agent topology.
2. Codex uses [config.only_codex.example.yaml](config.only_codex.example.yaml) as the baseline config.
3. The main process writes requests into `.researchclaw-supervisor/requests/`.
4. Codex and its sub-agents generate the required responses and write them into `.researchclaw-supervisor/responses/`.
5. The pipeline continues through literature review, hypothesis generation, code generation, experiments, paper writing, and review.

Supervisor transport details are documented in [docs/supervisor-mode.md](docs/supervisor-mode.md).

## Repository Layout

- `researchclaw/`: core pipeline, LLM integration, literature, experiment, and writing modules
- `scripts/`: supervisor exchange, response verification, and replay helpers
- `tests/`: regression tests for config, health checks, pipeline execution, and supervisor mode
- `docs/`: public documentation for Codex-first and supervisor-mode usage
- `config.only_codex.example.yaml`: safe starter config for Codex users

## Internal Naming

The internal Python package and CLI remain `researchclaw` for compatibility with the inherited codebase. The repository name and operating model are what changed.

## Origin

This project is a derivative work of `AutoResearchClaw`. The derivative focus here is practical: make the framework usable by someone who only signs in to Codex and wants Codex to learn the repo, create the right sub-agents, and drive the paper workflow end to end.
