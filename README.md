# Only_Codex_Research

[English](./README_EN.md)

[![GitHub stars](https://img.shields.io/github/stars/RJMSWD/Only_Codex_Research?style=social)](https://github.com/RJMSWD/Only_Codex_Research)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE)
[![Codex First](https://img.shields.io/badge/Codex-First-black)](./AGENTS.md)
[![Supervisor Mode](https://img.shields.io/badge/Mode-Supervisor-orange)](./docs/supervisor-mode_CN.md)

<p align="center">
  <img src="./image/logo.png" alt="Only_Codex_Research Logo" width="280" />
</p>

**🔥 登录你的 Codex，在合适环境下，几小时内把 idea 推进成完整可投稿论文。**

无需复杂 API 编排，默认通过 `supervisor` 文件模式驱动多智能体流水线，把科研流程从想法一路推进到文献调研、实现、实验、论文写作与内部审稿。

## 项目特点

- Codex-first 全自动科研编排
- 端到端覆盖：文献调研 → 代码实现 → 实验 → 论文写作 → 内部审稿
- 基于 `AutoResearchClaw` 的成熟流水线继续演化，默认工作方式更适合公开用户直接使用
- 默认使用文件系统 `supervisor` 模式，无需 ACP 作为主通道
- 子智能体拓扑、职责和推理强度已经写入 [AGENTS.md](./AGENTS.md)

## 流程架构

![Framework](./image/framework.png)

## 快速开始

```bash
git clone https://github.com/RJMSWD/Only_Codex_Research.git
cd Only_Codex_Research
pip install -e .
cp config.only_codex.example.yaml config.local.yaml
```

建议启动提示词：

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

1. Codex 先阅读 [AGENTS.md](./AGENTS.md)，理解默认角色分工。
2. Codex 使用 [config.only_codex.example.yaml](./config.only_codex.example.yaml) 作为起始配置。
3. 主流程把阶段请求写入 `.researchclaw-supervisor/requests/`。
4. Codex 和子智能体把结构化响应写回 `.researchclaw-supervisor/responses/`。
5. 流水线继续完成规划、文献、实现、实验、写作与审稿阶段。

传输机制详见 [docs/supervisor-mode_CN.md](./docs/supervisor-mode_CN.md)。

## 仓库结构

- `researchclaw/`：核心运行包，负责流水线、文献、实验和写作阶段
- `scripts/`：请求交换、响应校验和响应复用脚本
- `tests/`：配置、健康检查、执行流程与 supervisor 模式回归测试
- `docs/`：技术文档与扩展说明
- `config.only_codex.example.yaml`：公开可用的起始配置

## 兼容性说明

对外推荐使用 `only-codex-research` 命令。内部 Python 包名仍保留为 `researchclaw`，用于兼容继承而来的代码结构。

## 致谢与来源

Only_Codex_Research 基于 `AutoResearchClaw` 的基础流水线继续扩展，重点在于将默认编排方式调整为 Codex 优先。
