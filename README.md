# Investment OS

## 这是什么

面向长期投资的 Karpathy 式规则集：一个 [Agent skill](skills/investment-os/SKILL.md)、三份政策 references，以及确定性的事实、数学与执行控制。

```text
事实 → 规则 → LLM 判断 → 所有者授权的执行
```

本仓库就是可安装的产品本体。它保存规则，永不保存个人组合数据。本项目服务于个人投资纪律，不构成投资建议。

## 安装

Codex：

```bash
codex plugin marketplace add Zereker/investment-os --ref master
codex plugin add investment-os@investment-os
```

Claude Code：

```text
/plugin marketplace add Zereker/investment-os
/plugin install investment-os@investment-os
```

## 使用

开一个新会话，直接说 `Daily`，或要求月度资金复盘、评估一笔交易、研究一项政策变更，或明确授权一次券商操作。Skill 只加载该任务真正需要的政策文件。
