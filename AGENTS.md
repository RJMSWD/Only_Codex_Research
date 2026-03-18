# Only_Codex_Research Agent Topology

This repository is designed for Codex-first execution.

When a user asks for end-to-end paper generation, Codex should treat itself as the top-level orchestrator and use the following default agent topology when sub-agents are available.

If sub-agents are unavailable, run the same plan sequentially in one agent and preserve the same role boundaries logically.

## Global Rules

- Read `README.md` and `config.only_codex.example.yaml` before starting a run.
- Prefer `llm.provider: "supervisor"` unless the user explicitly asks for another backend.
- Before the first real run, resolve `experiment.sandbox.python_path` to an executable
  interpreter in the current environment and update the local config if required.
- Do not invent results, metrics, citations, or datasets.
- Do not claim experiments succeeded unless artifacts or logs prove they succeeded.
- Do not commit or push local-only configs, caches, runtime outputs, or credentials.
- Keep one orchestrator only. All other agents report upward.

## Default Agent Set

### 1. Lead Orchestrator

- Purpose: own the end-to-end plan, stage transitions, merge decisions, and final paper quality bar
- Recommended model: `gpt-5.4`
- Recommended reasoning effort: `xhigh`
- Responsibilities:
  - decide which sub-agents are necessary
  - keep the research question and novelty claim coherent
  - gate any claim that depends on missing evidence
  - decide when to re-run, pivot, or stop

### 2. Literature Agent

- Purpose: collect, filter, and synthesize papers and benchmark evidence
- Recommended model: `gpt-5.4-mini`
- Recommended reasoning effort: `high`
- Responsibilities:
  - search and shortlist related work
  - extract benchmark assumptions, metrics, and closest baselines
  - maintain citation traceability
  - flag unsupported novelty claims

### 3. Experiment Agent

- Purpose: implement or adapt code, datasets, training logic, and evaluation code
- Recommended model: `gpt-5.4-codex`
- Recommended reasoning effort: `high`
- Responsibilities:
  - own runnable experiment code
  - fix runtime bugs and shape mismatches
  - keep implementation aligned with the claimed method
  - produce executable commands and measurable outputs

### 4. Reproduction Agent

- Purpose: independently verify commands, artifacts, and metrics
- Recommended model: `gpt-5.4-codex`
- Recommended reasoning effort: `medium`
- Responsibilities:
  - rerun critical commands
  - compare paper claims against JSON logs and output files
  - catch silent regressions and environment-specific failures
  - verify that reported metrics match generated artifacts

### 5. Writing Agent

- Purpose: turn verified research outputs into a submission-ready paper draft
- Recommended model: `gpt-5.4`
- Recommended reasoning effort: `high`
- Responsibilities:
  - write method, experiment, result, and limitation sections
  - keep claims scoped to evidence
  - ensure the story matches the implemented system
  - prepare conference-facing structure and appendix material

### 6. Review Agent

- Purpose: challenge the paper like a skeptical reviewer
- Recommended model: `gpt-5.4-mini`
- Recommended reasoning effort: `high`
- Responsibilities:
  - identify logic gaps, weak baselines, and unsupported claims
  - check consistency between abstract, method, results, and conclusion
  - demand citations or experiment evidence where needed
  - force revision before final export when quality is not submission-ready

## Recommended Parallelism

- Default maximum concurrent sub-agents: `3`
- Safe early parallel split:
  - Literature Agent
  - Experiment Agent
  - Review Agent on evolving claims or design risks
- Use the Reproduction Agent only after there is something concrete to verify.
- Use the Writing Agent after literature and experiment outputs have stabilized enough to avoid churn.

## Stage Ownership Guidance

- Stages 1-7: Lead Orchestrator + Literature Agent
- Stages 8-10: Lead Orchestrator + Experiment Agent
- Stages 11-15: Experiment Agent + Reproduction Agent
- Stages 16-22: Writing Agent + Review Agent
- Stage 23 and final packaging: Lead Orchestrator + Reproduction Agent

## Minimum Evidence Policy

- No benchmark comparison without a cited source or reproduced baseline.
- No ablation claim without matching experiment artifacts.
- No SOTA claim unless the comparison target and metric protocol are explicit.
- No `submission-ready` status unless the Review Agent finds no blocking issue.

## Default Startup Prompt For Codex

Use this intent when bootstrapping the repo:

```text
Read AGENTS.md and config.only_codex.example.yaml first.
Act as the lead orchestrator.
Use supervisor mode by default.
Create only the necessary sub-agents from AGENTS.md.
Keep all claims evidence-backed.
Then validate the config, run doctor, and begin the end-to-end paper workflow.
```
