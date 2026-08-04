# 评测框架适配器

`evals/run.py` 是 harness 中立的：它校验协议、重新计算判定，并在没有独立 verifier 时拒绝报告通过。它有意不知道该怎么启动一个 agent。这些适配器就是缺掉的另一半——把真实的 Claude Code 与 Codex 会话接到 `--actor-command` 与 `--verifier-command` 后面的具体命令。

## 命令

已验证运行（Claude Code actor，独立 Codex verifier）：

```bash
python3 evals/run.py <scenario> \
  --actor-command 'python3 evals/adapters/claude_actor.py' \
  --verifier-command 'python3 evals/adapters/codex_verifier.py' \
  --timeout 2400 \
  --output evals/results/claude-code-actor__codex-verifier/<scenario>.json
```

Codex 命令需要已认证的 Codex CLI 或 `OPENAI_API_KEY`。适配器为每次 verifier 调用新建一个可写 HOME。订阅模式下它校验宿主的 `~/.codex/auth.json`，以不跟随链接的方式按 `0600` 复制进一次性 HOME，并随临时目录一起删除该副本。它从不继承宿主的 Codex 配置、插件、skill、会话或规则。API-key 模式下只传入密钥和一个很小的环境白名单。该白名单在存在时还会保留受管运行时的 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY`、`NO_PROXY`、`SSL_CERT_FILE` 与 `REQUESTS_CA_BUNDLE`，且不写入证据。这让 verifier 在经批准的代理后面保持联网能力，同时维持与宿主状态的隔离。

全量注册扫描（唯一能产出聚合 `VERIFIED PASS` 的命令）：

```bash
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
python3 evals/run_all.py \
  --actor-command 'python3 evals/adapters/claude_actor.py' \
  --verifier-command 'python3 evals/adapters/codex_verifier.py' \
  --timeout 2400 \
  --output-dir "evals/artifacts/claude-code-actor__codex-verifier/${RUN_ID}"
```

输出目录中每个场景各含一份结果、适配器 stdout/stderr 原文与 Codex JSONL，最后是 `aggregate.json`。`run_all.py` 遇到失败会继续跑，但只有在每个注册场景都是 schema 合法的 `VERIFIED PASS`、每份结果文件都存在、且全扫描范围内 actor 与 verifier 的会话身份都唯一时，才零退出。运行目录必须是新建或空目录；陈旧输出会被拒绝，而不是被覆盖或误当作本次调用的证据。

Actor 冒烟运行（仅供调试；恒为非零退出并报告 `NOT VERIFIED`）：

```bash
python3 evals/run.py <scenario> \
  --actor-command 'python3 evals/adapters/claude_actor.py' --actor-only
```

多轮场景会跑掉若干个真实会话量级的轮次。给 `--timeout` 留足余量：runner 的超时覆盖整条 actor 命令，不是单轮。

## 这些适配器为何满足独立性契约

| 契约要求 | 如何满足 |
|---|---|
| 干净的 actor 会话 | 每次运行生成全新 UUID 并用 `--session-id` 传入。没有它，CLI 可能复用调用方会话，从而静默作废整轮运行。 |
| 跨轮次的单一持久会话 | 第 1 轮用 `--session-id`，后续轮次 `--resume` 同一个 id。 |
| 以已安装分发为权威 | actor 跑在插件的一次性副本上，排除 `.git` 与既往评测结果。它无法在运行时解析仓库 commit，也无法从已记录的答案中学习。 |
| verifier 独立进程与会话 | Codex 作为独立进程运行，并从其 JSONL 事件流报告一个新的临时 thread id。若与 actor 相同，runner 拒绝该结果。 |
| verifier 不被被测系统污染 | 它跑在中立的临时目录中，不加载任何插件或 Skill，只依据评分标准与 transcript 判定。 |
| 与宿主状态隔离 | Codex verifier 在全新的 HOME/XDG/TMPDIR 树下、以白名单环境运行。只植入选定的认证材料；宿主配置与既往会话一律不存在。 |
| 优先使用不同 harness | `codex_verifier.py` 提供首选的 Claude Code actor / Codex verifier 组合，并报告 `different_harness: true`。 |
| 如实披露 harness 元数据 | 适配器在结果 JSON 中报告模型、工具、会话身份与隔离状态。 |

## 为什么一次评测运行碰不到真实账户

场景是合成的，但那只是文本层面的属性。这些适配器把隔离做成结构性的：

- `--strict-mcp-config` 配空的 `--mcp-config`，让两个进程**完全没有任何 MCP server**，因此会话里根本不存在可调用的券商连接器；
- actor 跑在一次性、无 git 的插件分发副本中，既往评测结果已被移除；
- actor 被限制为只读工具（`Read`、`Grep`、`Glob`、`Skill`）加分发自带的确定性 Python 脚本；直接写入、无限制 shell 与网络抓取一律拒绝，脚本产生的任何文件都被限制在一次性副本内；
- Codex verifier 以临时且只读方式运行，用户配置、项目规则、MCP server 与网页搜索全部关闭；若其 JSONL 轨迹中出现工具调用项，该轮运行即被拒绝。

actor 仍然通过 `--plugin-dir` 加载 Investment OS 插件——因为它的 canonical Skill 与已发布规则正是被测系统本身。

## 环境变量

| 变量 | 默认值 | 含义 |
|---|---|---|
| `EVAL_ACTOR_MODEL` | `claude-sonnet-5` | actor 模型 |
| `EVAL_CODEX_BIN` | `codex` | Codex CLI 可执行文件或绝对路径 |
| `EVAL_CODEX_VERIFIER_MODEL` | `gpt-5.6-sol` | Codex verifier 模型 |
| `EVAL_CODEX_VERIFIER_REASONING_EFFORT` | `medium` | Codex verifier 推理强度 |
| `EVAL_CODEX_AUTH_MODE` | `auto` | `auto`、`subscription` 或 `api-key`；auto 优先使用显式导出的 API key，否则使用 Codex 登录认证 |
| `EVAL_CODEX_AUTH_FILE` | Codex 登录路径 | 可选的订阅 `auth.json` 来源覆盖 |
| `EVAL_ACTOR_TIMEOUT` | `600` | 单轮超时（秒）；超时使该轮运行作废，而不是产出一个结果 |
| `EVAL_CODEX_VERIFIER_TIMEOUT` | `600` | Codex verifier 超时（秒） |
| `EVAL_PLUGIN_DIR` | 仓库根目录 | 被复制进一次性 actor 分发的 Investment OS 插件源 |
| `EVAL_EVIDENCE_DIR` | 未设置 | 可选的本地目录，用于存放适配器/CLI 原始证据；由 `run_all.py` 自动设置 |

## 一份结果能证明什么、不能证明什么

一个 `VERIFIED PASS` 覆盖的是**一个场景、一组 harness、一次运行**。它证明该行为在这个场景的压力下成立，不证明系统整体已被验证。其他场景的行为主张在真正跑过并记录之前一律悬空。

`evals/results/` 下的结果按构造即为合成的——actor 没有券商访问权限，账户数字进不了 transcript。绝不要把 `--output` 指向非合成的运行。

真实模型运行属于受信任的本地操作，不属于公开 CI。`evals/artifacts/` 已被 Git 忽略；分享原始 transcript 与日志前请先审阅，并且绝不提交或粘贴认证文件。
