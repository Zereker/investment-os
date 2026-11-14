# ChatGPT usage

Production targets are SPYM 55%, QQQM 30%, and USD cash 15% of account NAV.
Only SPYM and QQQM shares may receive security-related broker writes, for
both BUY and SELL. Other holdings/orders are read-only anomalies reconciled
from IBKR; Legacy and IC review never create a trading exception. A chat statement that a position was closed is not a
live account snapshot or authority to change open orders.

Investment OS is skill-first. The MCP implementation is archived and no longer
registered by the plugin. A GitHub URL is neither an installed skill nor a tool
connection. Reading its text in a conversation does not install persistent tools.

Use the host's supported skill/plugin installation when available. Enable the
Interactive Brokers integration separately for authoritative live account facts.
For a host with code execution and the installed skill files, the skill invokes
its bundled Python helper after running the evidence and capability checks in
`references/07-runtime-checks.md`. The helper does not fetch IBKR data, write
orders, or save account input. Pass data in memory or stdin, never a repository
file, command-line argument, debug log or public issue.

A conversation with only rule text can still discuss policy and disclose facts
returned by IBKR. It must not claim the local helper is installed or executable.
If Python execution is unavailable, close only deployment arithmetic and continue
the independent checks. Monthly funding requires authoritative contribution evidence as well as fresh settled USD cash. No MCP or skill creates a missing broker capability.

A reviewed public ChatGPT Plugins Directory release is a separate publication
step; a repository version or tag does not establish one.

The helper separates account, monthly DCA/baseline, independent drawdown and
private funding-journal transitions, plus the mandatory trade_scope instrument gate. Each held contract needs an IBKR ID-based
canonical mapping. A journal result is not persisted by the helper: the host
needs verified private storage with atomic revision updates and readback before
dependent live DCA execution. Ordinary chat memory or a public GitHub file does
not provide that capability. Reviews and synthetic simulations do not reserve funds.
