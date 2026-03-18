# Only_Codex_Research

这是一个面向 Codex 的端到端自动科研仓库，目标是把“一个研究想法”推进成“可提交论文”。

这个仓库脱胎于 `AutoResearchClaw`。核心流水线、阶段结构和执行框架继承自原项目，但默认使用方式已经改变：

- 这个仓库默认由 Codex 充当总指挥。
- 不再要求 OpenClaw 作为顶层调度器。
- 不再把 ACP 作为默认主通道。
- 推荐路径是：登录你自己的 Codex 账号，让 Codex 先学习这个仓库，再由 Codex 按照 `supervisor` 模式调度子智能体完成论文全流程。

## 与原项目的关键不同

- Codex 是默认编排器。
- 子智能体要怎么建、负责什么、推理强度建议是什么，都写在 [AGENTS.md](../AGENTS.md)。
- 开箱即用配置是 [config.only_codex.example.yaml](../config.only_codex.example.yaml)。
- 默认 LLM provider 是 `supervisor`，通过本地文件交换请求/响应，而不是依赖 ACP 或远程 API key。

## 公开仓库安全策略

这个可公开推送的仓库已经排除了以下内容：

- 本地 API key
- 机器专属 Python 路径
- 实验产物、缓存、检查点和运行痕迹
- 本地专用配置，例如 `config*.local.yaml`

## 快速开始

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/Only_Codex_Research.git
cd Only_Codex_Research
pip install -e .
cp config.only_codex.example.yaml config.local.yaml
```

然后在 Codex 里打开这个仓库，直接给它一个类似下面的提示：

```text
先阅读 AGENTS.md 和 config.only_codex.example.yaml。
使用 Codex 作为顶层编排器。
只在必要时创建推荐的子智能体。
除非缺少外部关键信息，否则不要打断我提问。
然后先做 validate 和 doctor，再以这个主题启动端到端论文流程：<你的主题>。
```

常用命令：

```bash
researchclaw validate --config config.local.yaml --no-check-paths
researchclaw doctor --config config.local.yaml
researchclaw run --config config.local.yaml --topic "你的研究主题" --auto-approve
```

## Codex 默认工作流

1. Codex 先读 [AGENTS.md](../AGENTS.md)，理解默认多智能体拓扑。
2. Codex 使用 [config.only_codex.example.yaml](../config.only_codex.example.yaml) 作为起始配置。
3. 主流程把请求写入 `.researchclaw-supervisor/requests/`。
4. Codex 和子智能体生成响应，写回 `.researchclaw-supervisor/responses/`。
5. 流水线继续完成文献、假设、代码、实验、写作和审稿阶段。

`supervisor` 机制详见 [supervisor-mode_CN.md](supervisor-mode_CN.md)。

## 仓库结构

- `researchclaw/`：核心流水线、LLM 集成、文献、实验和写作模块
- `scripts/`：请求回包、响应校验和重复响应复用脚本
- `tests/`：配置、健康检查、流水线和 supervisor 模式测试
- `docs/`：面向公开使用者的说明文档
- `config.only_codex.example.yaml`：给 Codex 用户的安全示例配置

## 内部命名说明

为了兼容继承而来的代码，内部 Python 包名和 CLI 仍然叫 `researchclaw`。变化的是仓库名称和默认运行范式。

## 来源说明

本项目基于 `AutoResearchClaw` 演化而来。这里强调的不是“换个名字”，而是把默认交互改造成“只登录 Codex，就能让 Codex 学习仓库、创建合适的子智能体，并把论文流程跑到底”。
