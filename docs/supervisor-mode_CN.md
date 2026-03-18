# Supervisor 模式

这是 `Only_Codex_Research` 的默认传输模式。

这个仓库已经被改造成支持基于文件系统的 `supervisor` LLM provider。
在这个模式下，流水线不再直接调用 ACP 或远程 LLM API，
而是把请求写入 `.researchclaw-supervisor/requests`，再等待外部总控把响应写入
`.researchclaw-supervisor/responses`。

## 已完成的仓库级改造

- 新增 `llm.provider: "supervisor"` 路径。
- 健康检查在 supervisor 模式下不再强制要求 API key。
- 流水线可以在本地 Python 解释器上通过文件交换完成请求/响应闭环。
- 修复了代码修复回路里 `code_agent.py` 的 prompt 格式化 bug，
  避免因为字面量 `{target_file}` 触发 `.format(...)` 崩溃。

## 关键代码文件

- `researchclaw/llm/supervisor_client.py`
- `researchclaw/llm/client.py`
- `researchclaw/llm/__init__.py`
- `researchclaw/config.py`
- `researchclaw/health.py`
- `researchclaw/pipeline/executor.py`
- `researchclaw/pipeline/runner.py`
- `researchclaw/pipeline/code_agent.py`

## 新增辅助脚本

- `scripts/supervisor_exchange.py`
  查看 pending request，并手动写回 response。
- `scripts/verify_supervisor_response.py`
  从 `filename:...` fenced response 中提取代码并对 Python 文件执行 `py_compile`。
- `scripts/replay_supervisor_responses.py`
  对重复运行中内容完全一致的 request，自动复用旧 response。

## 最小配置示例

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

## 典型使用方式

1. 用 `llm.provider: "supervisor"` 的配置启动 `only-codex-research run ...`。
   开箱即用起点配置是 `config.only_codex.example.yaml`。
2. 查看 pending 请求：

   ```bash
   python scripts/supervisor_exchange.py pending
   ```

3. 查看某条 request：

   ```bash
   python scripts/supervisor_exchange.py show 20260318-015410-0001
   ```

4. 用准备好的 JSON 回包：

   ```bash
   python scripts/supervisor_exchange.py respond 20260318-015410-0001 --json-file response.json
   ```

5. 如果是重跑流程，可开启旧响应复用：

   ```bash
   python scripts/replay_supervisor_responses.py --watch
   ```

6. 如果 response 是代码生成结果，可先本地校验：

   ```bash
   python scripts/verify_supervisor_response.py .researchclaw-supervisor/responses/20260318-015410-0001.json
   ```

## 适用场景

- 外部主控代理或子代理代替真正的 LLM 提供响应
- 重跑同一研究流程时希望复用已验证过的旧响应
- 明确不想走 ACP
- 不希望在实际运行路径里依赖远程 API key
