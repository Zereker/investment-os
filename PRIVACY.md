# Privacy Policy

Effective date: October 17, 2026

Investment OS is an open-source rules and workflow plugin. The repository does
not collect, receive, store, or transmit personal information, brokerage
credentials, account identifiers, balances, positions, orders, fills, or
authorization records.

When a user connects Interactive Brokers, account and market data are handled
by ChatGPT and the Interactive Brokers integration under their respective
privacy policies and account settings. Investment OS supplies instructions that
may cause the host to request those capabilities, but it does not operate a
separate server or database. Current account snapshots remain in the private
host runtime. Funding deduplication journals and execution receipts may persist
in a verified private store configured by the host, outside this repository.
The helper only returns in-memory journal transitions; it neither chooses a
storage provider nor saves them. Storage retention, access and deletion follow
that host's settings and policies. Without verified private persistence, live
DCA execution that depends on the journal remains unavailable.

Repository maintainers may receive information that a user voluntarily submits
through GitHub issues or other support channels. GitHub processes that
information under its own privacy terms. Do not include brokerage credentials,
account data, or other sensitive personal information in a public issue.

Questions about this policy may be submitted through the support channel in
[SUPPORT.md](SUPPORT.md).
