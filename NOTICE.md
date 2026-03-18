Only_Codex_Research is a derivative repository based on AutoResearchClaw.

The inherited code structure, 23-stage pipeline design, and core research automation framework originate from AutoResearchClaw.

This repository changes the default operating model:

- Codex is the primary orchestrator.
- Filesystem-backed `supervisor` mode is the default transport.
- The public starter path is designed for users who only sign in to Codex and want Codex to learn the repository, create the right sub-agents, and run the workflow end to end.
