#!/usr/bin/env python3
"""Fetch SPYM / QQQM / SOXX holdings & sector data and compute combined
look-through exposure for the quarterly manual check (skills/using-investment-os/references/08-lookthrough-check.md).

Data layers (proven to work in the AI execution sandbox, 2026-07-31):

  1. SPYM  — SSGA official holdings xlsx (FULL holdings, Green source):
             https://www.ssga.com/us/en/individual/library-content/products/
             fund-data/etfs/us/holdings-daily-us-en-spym.xlsx
  2. QQQM / SOXX — stockanalysis.com holdings pages (top-25 rows, registered
             aggregator, Yellow): plain HTTPS GET works through the proxy.
             iShares / Invesco official pages block headless fetch (403/406);
             cross-check numbers against those pages in a browser or via the
             agent's web-fetch tool when Green quality is required.
  3. yfinance — the常用 Python library for ETF data (Ticker(x).funds_data
             gives sector_weightings / top_holdings). NOTE: blocked in this
             sandbox (curl_cffi TLS impersonation vs proxy MITM). Try it on
             an unrestricted machine; do not assume it works here.

Usage:
  python3 skills/routing-investment-research/scripts/fetch_etf_data.py                         # per-fund data only
  python3 skills/routing-investment-research/scripts/fetch_etf_data.py --scenario current      # + combined @ Cash15/SPYM51/QQQM28/SOXX6
  python3 skills/routing-investment-research/scripts/fetch_etf_data.py --scenario final-void   # + combined @ voided 15% end-state (reference)
  python3 skills/routing-investment-research/scripts/fetch_etf_data.py --weights spym=0.492,qqqm=0.195,soxx=0.078,cash=0.235
  python3 skills/routing-investment-research/scripts/fetch_etf_data.py --scenario current --markdown   # snapshot block for skills/using-investment-os/references/08-YYYY-MM-DD-lookthrough-check.md

Output quality is labeled per source. This tool reports facts and guardrail
comparisons only; it never changes the Registry and never authorizes trades.
Missing data prints N/A and the affected conclusion becomes DATA INCOMPLETE —
never guess, never reuse stale numbers.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import urllib.request
from datetime import date

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

SSGA_SPYM_XLSX = (
    "https://www.ssga.com/us/en/individual/library-content/products/"
    "fund-data/etfs/us/holdings-daily-us-en-spym.xlsx"
)
STOCKANALYSIS = "https://stockanalysis.com/etf/{sym}/holdings/"

# GICS Semiconductors & Semiconductor Equipment (storage hardware like
# SNDK/WDC/STX is Tech Hardware, NOT semi — keep it out, report separately).
SEMI = {
    "NVDA", "AVGO", "AMD", "TXN", "QCOM", "INTC", "MU", "AMAT", "LRCX", "KLAC",
    "ADI", "NXPI", "MCHP", "ON", "MPWR", "TER", "SWKS", "QRVO", "FSLR", "ENPH",
    "ASML", "TSM", "UMC", "ASX", "MRVL", "ALAB", "CRDO", "ENTG", "MTSI", "ARM",
    "GFS", "LSCC", "ONTO", "AMKR", "SLAB",
}
ISSUER_MERGE = {"GOOG": "GOOGL(A+C)", "GOOGL": "GOOGL(A+C)"}

# Constitution guardrails (v4.0): they constrain discretionary tilt additions,
# not routine Core paths.
GUARD_IT_WARN, GUARD_IT_FREEZE = 45.0, 50.0
GUARD_SEMI_IC = 15.0
GUARD_ISSUER_WARN, GUARD_ISSUER_FREEZE = 8.0, 10.0

SCENARIOS = {
    "current": {"cash": 0.15, "spym": 0.51, "qqqm": 0.28, "soxx": 0.06},
    "final-void": {"cash": 0.15, "spym": 0.42, "qqqm": 0.28, "soxx": 0.15},
}


def http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_spym_ssga() -> tuple[dict[str, float], str]:
    """Full SPYM holdings from the official SSGA xlsx. Returns ({ticker: w%}, as_of)."""
    try:
        import openpyxl  # optional dep: pip install openpyxl
    except ImportError:
        raise RuntimeError("openpyxl not installed — pip install openpyxl")
    raw = http_get(SSGA_SPYM_XLSX)
    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True)
    rows = list(wb.active.iter_rows(values_only=True))
    as_of = ""
    for r in rows[:6]:
        joined = " ".join(str(c) for c in r if c)
        m = re.search(r"As of\s+(.+)", joined)
        if m:
            as_of = m.group(1).strip()
    out: dict[str, float] = {}
    for r in rows[5:]:
        if not r or not r[1] or r[1] == "-":
            continue
        try:
            out[str(r[1]).strip()] = float(r[4])
        except (TypeError, ValueError, IndexError):
            continue
    if len(out) < 400:
        raise RuntimeError(f"SSGA xlsx parsed only {len(out)} rows — layout changed?")
    return out, as_of


def fetch_stockanalysis(sym: str) -> tuple[dict[str, float], str]:
    """Top-25 holdings from stockanalysis.com. Returns ({ticker: w%}, as_of)."""
    html = http_get(STOCKANALYSIS.format(sym=sym.lower())).decode("utf-8", "replace")
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)  # strip Svelte comment noise
    m = re.search(r"As of ([A-Z][a-z]{2} \d{1,2}, \d{4})", html)
    as_of = m.group(1) if m else "N/A"
    out: dict[str, float] = {}
    # rows look like: <a ...>NVDA</a></td><td class="shr ...">NVIDIA ...</td><td ...>8.56%</td>
    for tick, pct in re.findall(
        r'>([A-Z][A-Z0-9.]{0,6})</a></td><td[^>]*>[^<]*</td><td[^>]*>([\d.]+)%', html
    ):
        out.setdefault(tick, float(pct))
    if len(out) < 10:
        raise RuntimeError(f"stockanalysis parse for {sym} got {len(out)} rows — layout changed?")
    return out, as_of


def fund_exposure(w: dict[str, float], semi_residual: float = 0.0) -> dict[str, float]:
    known = sum(w.values())
    semi = sum(v for t, v in w.items() if t in SEMI) + semi_residual
    return {"known": known, "unknown": max(100.0 - known - semi_residual, 0.0), "semi": semi}


def parse_weights(text: str) -> dict[str, float]:
    out = {}
    for part in text.split(","):
        k, v = part.split("=")
        out[k.strip().lower()] = float(v)
    missing = {"cash", "spym", "qqqm", "soxx"} - set(out)
    if missing:
        raise SystemExit(f"--weights missing keys: {missing}")
    total = sum(out.values())
    if abs(total - 1.0) > 0.02:
        raise SystemExit(f"--weights sum to {total:.3f}, expected ~1.0 (include cash/other)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", choices=sorted(SCENARIOS), help="preset portfolio weights")
    ap.add_argument("--weights", help="custom weights, e.g. spym=0.49,qqqm=0.20,soxx=0.08,cash=0.23")
    ap.add_argument("--markdown", action="store_true", help="emit snapshot block for skills/using-investment-os/references/08-YYYY-MM-DD-lookthrough-check.md")
    args = ap.parse_args()

    funds: dict[str, dict] = {}
    errors: list[str] = []

    try:
        w, as_of = fetch_spym_ssga()
        funds["SPYM"] = {"w": w, "as_of": as_of, "src": SSGA_SPYM_XLSX, "quality": "Green (official, full holdings)", "semi_residual": 0.0}
    except Exception as e:  # noqa: BLE001 — report and continue, fail-closed downstream
        errors.append(f"SPYM/SSGA: {e}")
        try:
            w, as_of = fetch_stockanalysis("SPYM")
            funds["SPYM"] = {"w": w, "as_of": as_of, "src": STOCKANALYSIS.format(sym="spym"), "quality": "Yellow (aggregator, top-25 only)", "semi_residual": 0.0}
        except Exception as e2:  # noqa: BLE001
            errors.append(f"SPYM/stockanalysis: {e2}")

    for sym in ("QQQM", "SOXX"):
        try:
            w, as_of = fetch_stockanalysis(sym)
            residual = (100.0 - sum(w.values())) if sym == "SOXX" else 0.0  # SOXX is a pure semi fund
            funds[sym] = {"w": w, "as_of": as_of, "src": STOCKANALYSIS.format(sym=sym.lower()), "quality": "Yellow (aggregator, top-25; cross-check official page for Green)", "semi_residual": residual}
        except Exception as e:  # noqa: BLE001
            errors.append(f"{sym}/stockanalysis: {e}")

    print(f"# ETF look-through fetch — {date.today().isoformat()}\n")
    for sym, f in funds.items():
        e = fund_exposure(f["w"], f["semi_residual"])
        print(f"## {sym}  (source_as_of: {f['as_of']}, quality: {f['quality']})")
        print(f"   source: {f['src']}")
        note = "（残余按半导体计,纯半导体基金）" if f["semi_residual"] else ""
        print(f"   已知权重覆盖 {e['known'] + f['semi_residual']:.1f}%  半导体已知下界 {e['semi']:.1f}%{note}  未覆盖尾部 {e['unknown']:.1f}%")
        top = sorted(f["w"].items(), key=lambda kv: -kv[1])[:10]
        print("   top10: " + ", ".join(f"{t} {v:.2f}%" for t, v in top))
        print()
    for err in errors:
        print(f"!! DATA INCOMPLETE: {err}")

    weights = None
    if args.weights:
        weights = parse_weights(args.weights)
    elif args.scenario:
        weights = SCENARIOS[args.scenario]

    if weights:
        needed = {"SPYM", "QQQM", "SOXX"} - set(funds)
        if needed:
            print(f"\n合并计算跳过 — 缺少基金数据: {needed}（DATA INCOMPLETE）")
            sys.exit(0)
        sleeve = {k.upper(): v for k, v in weights.items() if k != "cash"}
        semi_known = sum(sleeve[s] * fund_exposure(funds[s]["w"], funds[s]["semi_residual"])["semi"] for s in sleeve)
        tail = sum(sleeve[s] * fund_exposure(funds[s]["w"], funds[s]["semi_residual"])["unknown"] for s in sleeve)
        issuers: dict[str, float] = {}
        for s in sleeve:
            for t, v in funds[s]["w"].items():
                key = ISSUER_MERGE.get(t, t)
                issuers[key] = issuers.get(key, 0.0) + sleeve[s] * v
        top_issuers = sorted(issuers.items(), key=lambda kv: -kv[1])[:10]

        hdr = "## 合并穿透 @ " + ", ".join(f"{k}={v:.1%}" for k, v in weights.items())
        print("\n" + hdr)
        semi_flag = "≥15% → 倾斜新增须IC" if semi_known >= GUARD_SEMI_IC else "ok"
        print(f"   半导体已知下界: {semi_known:.1f}%  [{semi_flag}]  + 未覆盖尾部上界 {tail:.1f}pp")
        if semi_known < GUARD_SEMI_IC <= semi_known + tail:
            print("   !! 已知值未越线但『已知+未覆盖』可能越线 → 倾斜新增结论 WAIT / DATA INCOMPLETE")
        print("   信息技术: 用管理人官方行业表手工计算（本工具持仓表不含行业列）——见 08-lookthrough-check.md 第2步")
        print(f"   单一发行人 (>8% WARN / ≥10% 冻结倾斜):")
        for t, v in top_issuers:
            flag = " ≥10 FREEZE" if v >= GUARD_ISSUER_FREEZE else (" >8 WARN" if v > GUARD_ISSUER_WARN else "")
            print(f"     {t:<12}{v:6.2f}%{flag}")

        if args.markdown:
            print("\n---8<--- 保存为 skills/using-investment-os/references/08-YYYY-MM-DD-lookthrough-check.md ---")
            print(f"# Look-through Check — {date.today().isoformat()}\n")
            print(f"- observed_at: {date.today().isoformat()}")
            print(f"- 组合权重 w: " + ", ".join(f"{k}={v:.1%}" for k, v in weights.items()))
            for sym in ("SPYM", "QQQM", "SOXX"):
                f = funds[sym]
                print(f"- {sym}: {f['src']} / source_as_of {f['as_of']} / quality {f['quality']}")
            print(f"- Semi_combined(已知下界) = {semi_known:.1f}% ｜ 未覆盖尾部 ≤{tail:.1f}pp ｜ 结论: "
                  + ("倾斜新增须IC" if semi_known >= GUARD_SEMI_IC else "见上界分析"))
            print("- IT_combined = 手工填写（官方行业表加权）｜ 结论:")
            print("- Top issuers combined: " + ", ".join(f"{t} {v:.1f}%" for t, v in top_issuers[:5]))
            print("- 未分类/近似处理说明: QQQM/SOXX 仅 top-25（聚合源）；SPYM 官方全量")
            print("- 总结论: PASS / WARN / FREEZE-TILT / DATA INCOMPLETE（人工判定）")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
