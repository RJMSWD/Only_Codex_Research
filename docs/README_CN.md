# Only_Codex_Research

[English](../README.md) | 简体中文

面向 Codex 的科研自动化仓库，用于把研究想法推进成可投稿论文。

Only_Codex_Research 基于 `AutoResearchClaw` 的流水线架构继续发展，但对外工作方式已经调整为 Codex 优先：Codex 先学习仓库结构与代理分工，再通过 `supervisor` 模式推进整条论文流水线。

## 项目特点

- 以 Codex 作为默认编排核心
- 在 [AGENTS.md](../AGENTS.md) 中明确给出子智能体拓扑与职责
- 提供安全的起始配置 [config.only_codex.example.yaml](../config.only_codex.example.yaml)
- 默认使用基于文件交换的 `supervisor` LLM 后端
- 覆盖文献调研、实现、实验、写作与内部审稿的端到端阶段

## 快速开始

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/Only_Codex_Research.git
cd Only_Codex_Research
pip install -e .
cp config.only_codex.example.yaml config.local.yaml
```

建议的启动提示词：

```text
先阅读 AGENTS.md 和 config.only_codex.example.yaml。
你作为 lead orchestrator。
默认使用 supervisor 模式。
只在必要时创建 AGENTS.md 中定义的子智能体。
所有结论都必须有证据支撑。
先执行 validate 和 doctor，再围绕这个主题启动端到端论文流程：<你的主题>。
```

第一次正式运行前，请先把 `config.local.yaml` 中的 `experiment.sandbox.python_path` 改成当前环境里可执行的 Python 解释器路径。

常用命令：

```bash
only-codex-research validate --config config.local.yaml --no-check-paths
only-codex-research doctor --config config.local.yaml
only-codex-research run --config config.local.yaml --topic "你的研究主题" --auto-approve
```

## 工作方式

1. Codex 先阅读 [AGENTS.md](../AGENTS.md)，理解默认角色分工。
2. Codex 使用 [config.only_codex.example.yaml](../config.only_codex.example.yaml) 作为起始配置。
3. 主流程把阶段请求写入 `.researchclaw-supervisor/requests/`。
4. Codex 和子智能体把结构化响应写回 `.researchclaw-supervisor/responses/`。
5. 流水线继续完成规划、文献、实现、实验、写作与审稿阶段。

传输机制详见 [supervisor-mode_CN.md](./supervisor-mode_CN.md)。

## 仓库结构

- `researchclaw/`：核心运行包，负责流水线、文献、实验和写作阶段
- `scripts/`：请求交换、响应校验和响应复用脚本
- `tests/`：配置、健康检查、执行流程与 supervisor 模式回归测试
- `docs/`：面向公开用户的使用文档
- `config.only_codex.example.yaml`：公开可用的起始配置

## 兼容性说明

对外推荐使用 `only-codex-research` 命令。内部 Python 包名仍保留为 `researchclaw`，用于兼容继承而来的代码结构。

## 致谢与来源

Only_Codex_Research 基于 `AutoResearchClaw` 的基础流水线继续扩展，重点在于将默认编排方式调整为 Codex 优先。
