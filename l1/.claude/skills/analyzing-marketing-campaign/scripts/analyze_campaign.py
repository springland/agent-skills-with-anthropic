#!/usr/bin/env python3.13
"""Campaign performance analysis — data quality + funnel metrics vs benchmarks.

Refactored so each analysis step lives in its own function, making the code
easier to read and test.
"""

import csv
import sys
from collections import defaultdict

# ── Constants ──────────────────────────────────────────────────────────

BENCHMARKS = {
    "Facebook_Ads":  {"CTR": 2.5,  "CVR": 3.8},
    "Google_Ads":    {"CTR": 5.0,  "CVR": 4.5},
    "TikTok_Ads":    {"CTR": 2.0,  "CVR": 0.9},
    "Email":         {"CTR": 15.0, "CVR": 2.1},
}

NUMERIC_COLS = ["impressions", "clicks", "conversions", "spend", "revenue", "orders"]

CSV_PATH = "campaign_data_week1.csv"

SHIPPING_COST_PER_ORDER = 8.0
PRODUCT_COST_PCT = 0.35
TARGET_ROAS = 4.0
MAX_CPA = 50.0


# ═══════════════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════════════

def load_data(path):
    """Read the CSV and return a list of dict rows."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return [r for r in reader]


# ═══════════════════════════════════════════════════════════════════════════
# Part 1 — Data-quality checks (each returns results; printing is separate)
# ═══════════════════════════════════════════════════════════════════════════

def check_missing_values(rows):
    """Return list of (line_number, column_name) for every empty cell."""
    missing = []
    for i, row in enumerate(rows, start=2):  # line 2 = first data row
        for col in row:
            if row[col].strip() == "":
                missing.append((i, col))
    return missing


def print_missing_values(missing):
    """Print a human-readable summary of missing-value findings."""
    if not missing:
        print("\n✅ No missing values found.")
        return

    print(f"\n⚠️  MISSING VALUES ({len(missing)} cells):")
    by_col = defaultdict(list)
    for line, col in missing:
        by_col[col].append(line)
    for col, lines in sorted(by_col.items()):
        print(f"  • {col}: {len(lines)} rows empty — lines {lines[0]}–{lines[-1]}")


def check_duplicates(rows):
    """Return the count of exact duplicate rows."""
    seen = set()
    dups = 0
    for row in rows:
        key = tuple(row.values())
        if key in seen:
            dups += 1
        else:
            seen.add(key)
    return dups


def print_duplicates(dup_count):
    """Print duplicate-row findings."""
    if dup_count:
        print(f"\n⚠️  DUPLICATE ROWS: {dup_count} exact duplicate(s)")
    else:
        print("\n✅ No duplicate rows.")


def check_anomalies(rows, numeric_cols):
    """Return list of (column, raw_value, reason) for non-numeric / negative values."""
    anomalies = []
    for row in rows:
        for col in numeric_cols:
            val = row[col].strip()
            if val == "":
                continue  # already flagged as missing
            try:
                v = float(val)
            except ValueError:
                anomalies.append((col, val, "non-numeric"))
                continue
            if v < 0:
                anomalies.append((col, val, "negative"))
    return anomalies


def print_anomalies(anomalies):
    """Print anomaly findings."""
    if anomalies:
        print(f"\n⚠️  ANOMALIES ({len(anomalies)}):")
        for col, val, reason in anomalies:
            print(f"  • {col} = '{val}' ({reason})")
    else:
        print("\n✅ No anomalous values in numeric columns.")


def check_key_integrity(rows):
    """Return count of rows where conversions != orders (both non-empty)."""
    mismatch = 0
    for row in rows:
        conv = row["conversions"].strip()
        ord_ = row["orders"].strip()
        if conv and ord_ and conv != ord_:
            mismatch += 1
    return mismatch


def print_key_integrity(mismatch):
    """Print key-integrity findings."""
    if mismatch:
        print(f"\n⚠️  conversions ≠ orders in {mismatch} rows")
    else:
        print("\n✅ conversions always equals orders (consistent).")


def check_email_impressions(rows):
    """Return (email_row_count, all_blank) for Email channel."""
    email_rows = [r for r in rows if r["channel"] == "Email"]
    all_blank = all(r["impressions"].strip() == "" for r in email_rows)
    return len(email_rows), all_blank


def print_email_impressions(email_count, all_blank):
    """Print Email-impressions expectation check."""
    status = "expected (email has no impression metric)" if all_blank else "UNEXPECTED"
    print(f"\nℹ️  Email impressions: all {email_count} Email rows have blank impressions "
          f"— {status}")


def collect_summary_info(rows):
    """Return (dates, channels, campaigns) summary tuples."""
    dates = sorted(set(r["date"] for r in rows))
    channels = sorted(set(r["channel"] for r in rows))
    campaigns = sorted(set(r["campaign_name"] for r in rows))
    return dates, channels, campaigns


def print_summary_info(dates, channels, campaigns):
    """Print date range, channel list, and campaign list."""
    print(f"\nℹ️  Date range: {dates[0]} → {dates[-1]} ({len(dates)} days)")
    print(f"\nℹ️  Channels: {', '.join(channels)}")
    print(f"ℹ️  Campaigns: {', '.join(campaigns)}")


# ═══════════════════════════════════════════════════════════════════════════
# Shared helpers
# ═══════════════════════════════════════════════════════════════════════════

def aggregate_by_channel(rows):
    """Sum every numeric column per channel.  Returns {channel: {col: float}}."""
    chan = defaultdict(lambda: {col: 0 for col in NUMERIC_COLS})
    for row in rows:
        ch = row["channel"]
        for col in NUMERIC_COLS:
            val = row[col].strip()
            if val:
                chan[ch][col] += float(val)
    return chan


def aggregate_by_campaign(rows):
    """Sum every numeric column per campaign.  Returns {campaign: {col: float}}."""
    camp = defaultdict(lambda: {col: 0 for col in NUMERIC_COLS})
    for row in rows:
        cname = row["campaign_name"]
        for col in NUMERIC_COLS:
            val = row[col].strip()
            if val:
                camp[cname][col] += float(val)
    return camp


def campaign_to_channel(rows, campaign_name):
    """Return the channel for a given campaign name (first match)."""
    return next(r["channel"] for r in rows if r["campaign_name"] == campaign_name)


def compare_to_benchmark(actual, bench):
    """Return (formatted_value, formatted_delta) strings for a metric vs benchmark."""
    if actual is None:
        return "N/A", "N/A"
    diff = actual - bench
    arrow = "▲" if diff > 0 else ("▼" if diff < 0 else "=")
    return f"{actual:.2f}%", f"{arrow}{abs(diff):.2f}pp"


def ctr_cvr_verdict(ctr, ctr_bench, cvr, cvr_bench):
    """Build a verdict string like 'CTR✓ | CVR✗' from actual-vs-benchmark pairs."""
    parts = []
    if ctr is not None:
        parts.append("CTR✓" if ctr >= ctr_bench else "CTR✗")
    if cvr is not None:
        parts.append("CVR✓" if cvr >= cvr_bench else "CVR✗")
    return " | ".join(parts) if parts else "N/A"


def efficiency_verdict(roas, cpa, net_profit,
                       roas_target=TARGET_ROAS, cpa_max=MAX_CPA):
    """Build a verdict string for the efficiency targets (ROAS, CPA, Profit)."""
    parts = [
        "ROAS✓" if roas >= roas_target else "ROAS✗",
        "CPA✓" if cpa <= cpa_max else "CPA✗",
        "Profit✓" if net_profit > 0 else "Profit✗",
    ]
    return " | ".join(parts)


def compute_ctr_cvr(d):
    """Return (ctr_pct, cvr_pct) from an aggregate dict; None when denominator is 0."""
    imp = d["impressions"]
    clk = d["clicks"]
    conv = d["conversions"]
    ctr = (clk / imp * 100) if imp > 0 else None
    cvr = (conv / clk * 100) if clk > 0 else None
    return ctr, cvr


# ═══════════════════════════════════════════════════════════════════════════
# Part 2 — Funnel analysis
# ═══════════════════════════════════════════════════════════════════════════

def print_funnel_header():
    """Print the section header and table header for Part 2."""
    print("\n" + "=" * 80)
    print("PART 2 — FUNNEL ANALYSIS (CTR & CVR by Channel)")
    print("=" * 80)


def print_funnel_table(chan_data, channels):
    """Print the main CTR/CVR-by-channel comparison table."""
    print(f"\n{'Channel':<16} {'Impressions':>14} {'Clicks':>10} {'Conv.':>8} "
          f"{'CTR':>8} {'Bench':>8} {'Δ':>8}  "
          f"{'CVR':>8} {'Bench':>8} {'Δ':>8}  {'Verdict'}")
    print("-" * 130)

    for ch in channels:
        d = chan_data[ch]
        ctr, cvr = compute_ctr_cvr(d)

        bm = BENCHMARKS[ch]
        b_ctr, b_cvr = bm["CTR"], bm["CVR"]

        ctr_str, ctr_delta = compare_to_benchmark(ctr, b_ctr)
        cvr_str, cvr_delta = compare_to_benchmark(cvr, b_cvr)

        verdict = ctr_cvr_verdict(ctr, b_ctr, cvr, b_cvr)

        imp_str = f"{d['impressions']:,.0f}" if d["impressions"] > 0 else "N/A"
        print(f"{ch:<16} {imp_str:>14} {d['clicks']:>10,.0f} {d['conversions']:>8,.0f} "
              f"{ctr_str:>8} {b_ctr:>6.1f}% {ctr_delta:>8}  "
              f"{cvr_str:>8} {b_cvr:>5.1f}% {cvr_delta:>8}  {verdict}")


def print_per_campaign_breakdown(rows):
    """Print CTR and CVR for every campaign."""
    print("\n" + "-" * 130)
    print("\n📊  PER-CAMPAIGN BREAKDOWN")
    print(f"\n{'Campaign':<32} {'Channel':<16} {'CTR':>8} {'CVR':>8}")

    camp_data = aggregate_by_campaign(rows)
    for cname in sorted(camp_data):
        d = camp_data[cname]
        ctr, cvr = compute_ctr_cvr(d)

        ch = campaign_to_channel(rows, cname)
        ctr_s = f"{ctr:.2f}%" if ctr is not None else "N/A"
        cvr_s = f"{cvr:.2f}%" if cvr is not None else "N/A"
        print(f"{cname:<32} {ch:<16} {ctr_s:>8} {cvr_s:>8}")


def print_roas_summary(chan_data, channels):
    """Print ROAS by channel."""
    print("\n" + "-" * 130)
    print("\n💰  ROAS (Return on Ad Spend) by Channel")
    print(f"\n{'Channel':<16} {'Spend':>12} {'Revenue':>12} {'ROAS':>8}")
    print("-" * 52)
    for ch in channels:
        d = chan_data[ch]
        roas = d["revenue"] / d["spend"] if d["spend"] > 0 else 0
        print(f"{ch:<16} ${d['spend']:>11,.2f} ${d['revenue']:>11,.2f} {roas:>7.2f}x")


def run_funnel_analysis(rows, channels, chan_data):
    """Orchestrate all of Part 2 — funnel metrics."""
    print_funnel_header()
    print_funnel_table(chan_data, channels)
    print_per_campaign_breakdown(rows)
    print_roas_summary(chan_data, channels)


# ═══════════════════════════════════════════════════════════════════════════
# Part 3 — Efficiency analysis
# ═══════════════════════════════════════════════════════════════════════════

def print_efficiency_header():
    """Print the section header, assumptions, and table header for Part 3."""
    print("\n" + "=" * 80)
    print("PART 3 — EFFICIENCY ANALYSIS (ROAS, CPA, Net Profit)")
    print("=" * 80)

    print(f"\nAssumptions: Shipping = ${SHIPPING_COST_PER_ORDER:.0f}/order | "
          f"Product Cost = {PRODUCT_COST_PCT * 100:.0f}% of revenue")
    print(f"Targets: ROAS ≥ {TARGET_ROAS:.1f}x | CPA ≤ ${MAX_CPA:.0f} | Net Profit > $0")


def print_efficiency_table(chan_data, channels):
    """Print the main efficiency table (ROAS, CPA, Net Profit by channel)."""
    print(f"\n{'Channel':<16} {'Revenue':>12} {'Spend':>12} {'Orders':>8} "
          f"{'ROAS':>8} {'Target':>8} {'CPA':>8} {'Max':>8} "
          f"{'Ship.':>10} {'Prod.':>10} {'Net Profit':>12}  {'Verdict'}")
    print("-" * 148)

    for ch in channels:
        d = chan_data[ch]
        revenue = d["revenue"]
        spend = d["spend"]
        orders = d["orders"]
        conversions = d["conversions"]

        roas = revenue / spend if spend > 0 else 0
        cpa = spend / conversions if conversions > 0 else float("inf")

        shipping_total = orders * SHIPPING_COST_PER_ORDER
        product_cost = revenue * PRODUCT_COST_PCT
        net_profit = revenue - (spend + shipping_total + product_cost)

        verdict = efficiency_verdict(roas, cpa, net_profit)

        print(f"{ch:<16} ${revenue:>11,.2f} ${spend:>11,.2f} {orders:>8,.0f} "
              f"{roas:>7.2f}x {'≥' + str(TARGET_ROAS) + 'x':>8} "
              f"${cpa:>7,.2f} {'≤$' + str(int(MAX_CPA)):>8} "
              f"${shipping_total:>9,.2f} ${product_cost:>9,.2f} "
              f"${net_profit:>11,.2f}  {verdict}")


def print_per_campaign_efficiency(rows):
    """Print ROAS, CPA, and Net Profit for every campaign."""
    print("\n" + "-" * 148)
    print("\n📊  PER-CAMPAIGN EFFICIENCY")
    print(f"\n{'Campaign':<32} {'Channel':<16} {'ROAS':>8} {'CPA':>10} "
          f"{'Net Profit':>12}  {'Verdict'}")

    camp_full = aggregate_by_campaign(rows)
    for cname in sorted(camp_full):
        d = camp_full[cname]
        roas = d["revenue"] / d["spend"] if d["spend"] > 0 else 0
        cpa = d["spend"] / d["conversions"] if d["conversions"] > 0 else float("inf")
        shipping_total = d["orders"] * SHIPPING_COST_PER_ORDER
        product_cost = d["revenue"] * PRODUCT_COST_PCT
        net_profit = d["revenue"] - (d["spend"] + shipping_total + product_cost)

        verdict = efficiency_verdict(roas, cpa, net_profit)

        ch = campaign_to_channel(rows, cname)
        print(f"{cname:<32} {ch:<16} {roas:>7.2f}x ${cpa:>9,.2f} "
              f"${net_profit:>11,.2f}  {verdict}")


def print_profit_bridge(chan_data, channels):
    """Print the profit-bridge waterfall — where money comes from and goes."""
    print("\n" + "-" * 148)
    print("\n💰  PROFIT BRIDGE — Where the money goes")
    print(f"\n{'Channel':<16} {'Revenue':>12} {'- Spend':>12} {'- Shipping':>12} "
          f"{'- Prod Cost':>12} {'= Net Profit':>12} {'Margin %':>10}")
    print("-" * 90)

    for ch in channels:
        d = chan_data[ch]
        rev = d["revenue"]
        sp = d["spend"]
        ship = d["orders"] * SHIPPING_COST_PER_ORDER
        pcost = rev * PRODUCT_COST_PCT
        np_ = rev - sp - ship - pcost
        margin = (np_ / rev * 100) if rev > 0 else 0
        print(f"{ch:<16} ${rev:>11,.2f} ${sp:>11,.2f} ${ship:>11,.2f} "
              f"${pcost:>11,.2f} ${np_:>11,.2f} {margin:>9.1f}%")


def run_efficiency_analysis(rows, channels, chan_data):
    """Orchestrate all of Part 3 — efficiency metrics."""
    print_efficiency_header()
    print_efficiency_table(chan_data, channels)
    print_per_campaign_efficiency(rows)
    print_profit_bridge(chan_data, channels)


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main(csv_path=CSV_PATH):
    """Load data, run data-quality checks, then funnel and efficiency analysis."""
    # ── Load ────────────────────────────────────────────────────────────
    rows = load_data(csv_path)

    # ── Part 1: Data quality ────────────────────────────────────────────
    print("=" * 80)
    print("PART 1 — DATA QUALITY REPORT")
    print("=" * 80)
    print(f"\nTotal rows loaded: {len(rows)}")

    print_missing_values(check_missing_values(rows))
    print_duplicates(check_duplicates(rows))
    print_anomalies(check_anomalies(rows, NUMERIC_COLS))
    print_key_integrity(check_key_integrity(rows))

    email_count, email_ok = check_email_impressions(rows)
    print_email_impressions(email_count, email_ok)

    dates, channels, campaigns = collect_summary_info(rows)
    print_summary_info(dates, channels, campaigns)

    # ── Aggregate once, reuse across parts 2 & 3 ────────────────────────
    chan_data = aggregate_by_channel(rows)

    # ── Part 2: Funnel analysis ─────────────────────────────────────────
    run_funnel_analysis(rows, channels, chan_data)

    # ── Part 3: Efficiency analysis ─────────────────────────────────────
    run_efficiency_analysis(rows, channels, chan_data)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else CSV_PATH
    main(path)
