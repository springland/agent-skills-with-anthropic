#!/usr/bin/env python3.13
"""Budget reallocation engine — applies rules to campaign efficiency data."""

import csv
from collections import defaultdict

# ── Parameters ─────────────────────────────────────────────────────────
TARGET_ROAS = 4.0
MAX_CPA = 50.0
SHIPPING_COST = 8.0
PRODUCT_COST_PCT = 0.35
INCREASE_CAP = 0.15          # per-channel max increase
USER_REALLOCATION_LIMIT = 10000.0  # max total $ shifted into increases

CSV_PATH = "campaign_data_week1.csv"

# ── Load & aggregate ───────────────────────────────────────────────────
with open(CSV_PATH, newline="") as f:
    rows = list(csv.DictReader(f))

chan = defaultdict(lambda: {"impressions": 0, "clicks": 0, "conversions": 0,
                             "spend": 0, "revenue": 0, "orders": 0})
for row in rows:
    ch = row["channel"]
    for col in ["impressions", "clicks", "conversions", "spend", "revenue", "orders"]:
        val = row[col].strip()
        if val:
            chan[ch][col] += float(val)

# ── Compute metrics per channel ────────────────────────────────────────
metrics = {}
for ch in ["Facebook_Ads", "Google_Ads", "TikTok_Ads", "Email"]:
    d = chan[ch]
    rev = d["revenue"]
    sp = d["spend"]
    conv = d["conversions"]
    ords = d["orders"]

    roas = rev / sp if sp > 0 else 0
    cpa = sp / conv if conv > 0 else float("inf")
    shipping = ords * SHIPPING_COST
    product_cost = rev * PRODUCT_COST_PCT
    net_profit = rev - sp - shipping - product_cost

    metrics[ch] = {
        "spend": sp, "revenue": rev, "conversions": conv, "orders": ords,
        "roas": roas, "cpa": cpa, "net_profit": net_profit,
        "shipping": shipping, "product_cost": product_cost,
    }

# ══════════════════════════════════════════════════════════════════════════
# RULE 0 — Minimum Data Eligibility
# ══════════════════════════════════════════════════════════════════════════
print("=" * 90)
print("RULE 0 — MINIMUM DATA ELIGIBILITY (>= 50 conversions)")
print("=" * 90)
for ch in ["Facebook_Ads", "Google_Ads", "TikTok_Ads", "Email"]:
    conv = metrics[ch]["conversions"]
    eligible = "ELIGIBLE" if conv >= 50 else "INSUFFICIENT_DATA"
    print(f"  {ch:<16} conversions = {conv:,.0f}  →  {eligible}")

# ══════════════════════════════════════════════════════════════════════════
# RULE 1 — Channel Classification
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 90)
print("RULE 1 — CHANNEL CLASSIFICATION (first match wins)")
print("=" * 90)

ROAS_50PCT = TARGET_ROAS * 0.5       # 2.0
CPA_150PCT = MAX_CPA * 1.5           # $75
ROAS_115PCT = TARGET_ROAS * 1.15     # 4.6
CPA_80PCT = MAX_CPA * 0.8            # $40
ROAS_80PCT = TARGET_ROAS * 0.8       # 3.2
CPA_120PCT = MAX_CPA * 1.2           # $60

classifications = {}

for ch in ["Facebook_Ads", "Google_Ads", "TikTok_Ads", "Email"]:
    m = metrics[ch]
    roas = m["roas"]
    cpa = m["cpa"]
    np_ = m["net_profit"]

    roas_pct = (roas / TARGET_ROAS) * 100
    cpa_pct = (cpa / MAX_CPA) * 100

    cls = None
    reason = ""

    # PAUSE (requires user-stated multi-week context — not available)
    # Skip: no historical context provided.

    # DECREASE_HEAVY
    if cls is None:
        if roas < ROAS_50PCT and np_ <= 0:
            cls = "DECREASE_HEAVY"
            reason = f"ROAS {roas:.2f}x < {ROAS_50PCT:.1f}x (50% of target) AND Net Profit <= 0"
        elif cpa > CPA_150PCT and np_ <= 0:
            cls = "DECREASE_HEAVY"
            reason = f"CPA ${cpa:,.2f} > ${CPA_150PCT:,.0f} (150% of max) AND Net Profit <= 0"
        elif roas < TARGET_ROAS and cpa > MAX_CPA and np_ <= 0:
            cls = "DECREASE_HEAVY"
            reason = f"All three fail: ROAS {roas:.2f}x < {TARGET_ROAS}x, CPA ${cpa:,.2f} > ${MAX_CPA:.0f}, Net Profit <= 0"

    # INCREASE (all conditions must be met)
    if cls is None:
        if roas >= ROAS_115PCT and cpa <= CPA_80PCT and np_ > 0:
            cls = "INCREASE"
            reason = (f"ROAS {roas:.2f}x >= {ROAS_115PCT:.1f}x (115%), "
                      f"CPA ${cpa:,.2f} <= ${CPA_80PCT:.0f} (80%), "
                      f"Net Profit ${np_:,.2f} > 0")

    # DECREASE_LIGHT
    if cls is None:
        if roas < ROAS_80PCT:
            cls = "DECREASE_LIGHT"
            reason = f"ROAS {roas:.2f}x < {ROAS_80PCT:.1f}x (80% of target)"
        elif cpa > CPA_120PCT:
            cls = "DECREASE_LIGHT"
            reason = f"CPA ${cpa:,.2f} > ${CPA_120PCT:.0f} (120% of max)"

    # MAINTAIN
    if cls is None:
        cls = "MAINTAIN"
        reason = "Does not meet any decrease or increase condition"

    classifications[ch] = cls
    print(f"\n  {ch}")
    print(f"    ROAS {roas:.2f}x ({roas_pct:.0f}% of target) | "
          f"CPA ${cpa:,.2f} ({cpa_pct:.0f}% of max) | "
          f"Net Profit ${np_:,.2f}")
    print(f"    → {cls}  ({reason})")

# ══════════════════════════════════════════════════════════════════════════
# RULE 2 — Calculate Budget Changes
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 90)
print("RULE 2 — BUDGET CHANGE CALCULATIONS")
print("=" * 90)

CHANGE_PCT = {
    "PAUSE": -1.00,
    "DECREASE_HEAVY": -0.45,
    "DECREASE_LIGHT": -0.25,
    "MAINTAIN": 0.00,
    "INCREASE": INCREASE_CAP,
}

# Step 1 & 2: Calculate decreases and freed budget
print("\n── Step 1 & 2: Decreases & Freed Budget ──")
freed = 0.0
for ch in ["Facebook_Ads", "Google_Ads", "TikTok_Ads", "Email"]:
    cls = classifications[ch]
    spend = metrics[ch]["spend"]
    if CHANGE_PCT[cls] < 0:
        decrease = spend * abs(CHANGE_PCT[cls])
        freed += decrease
        print(f"  {ch:<16} {cls:<20} ${spend:>10,.2f} × {abs(CHANGE_PCT[cls]):.0%} = ${decrease:>10,.2f} freed")
    else:
        print(f"  {ch:<16} {cls:<20} ${spend:>10,.2f} → no decrease")

print(f"\n  TOTAL FREED BUDGET: ${freed:,.2f}")

# Step 3: Allocate to INCREASE channels proportionally by net profit
print("\n── Step 3: Allocate to INCREASE Channels (by Net Profit weight) ──")
increase_channels = [ch for ch, cls in classifications.items() if cls == "INCREASE"]
total_np = sum(metrics[ch]["net_profit"] for ch in increase_channels)

proposed = {}
for ch in increase_channels:
    weight = metrics[ch]["net_profit"] / total_np
    proposed[ch] = freed * weight
    print(f"  {ch:<16} weight = ${metrics[ch]['net_profit']:,.2f} / ${total_np:,.2f} = {weight:.1%}  "
          f"→ proposed ${proposed[ch]:,.2f}")

# Step 4: Apply caps
print("\n── Step 4: Apply Caps ──")
print(f"  Per-channel cap: {INCREASE_CAP:.0%} of current spend")
print(f"  User reallocation limit: ${USER_REALLOCATION_LIMIT:,.2f} (applies to increases only)")

capped = {}
sum_capped = 0.0
for ch in increase_channels:
    max_inc = metrics[ch]["spend"] * INCREASE_CAP
    capped[ch] = min(proposed[ch], max_inc)
    sum_capped += capped[ch]
    if proposed[ch] > max_inc:
        print(f"  {ch:<16} proposed ${proposed[ch]:,.2f} > cap ${max_inc:,.2f} → capped at ${capped[ch]:,.2f}")
    else:
        print(f"  {ch:<16} proposed ${proposed[ch]:,.2f} ≤ cap ${max_inc:,.2f} → ${capped[ch]:,.2f}")

# User reallocation limit
if sum_capped > USER_REALLOCATION_LIMIT:
    scale = USER_REALLOCATION_LIMIT / sum_capped
    print(f"\n  Sum of capped (${sum_capped:,.2f}) > user limit (${USER_REALLOCATION_LIMIT:,.2f})")
    print(f"  Scale factor: {scale:.4f}")
    for ch in increase_channels:
        capped[ch] *= scale
        print(f"  {ch:<16} scaled to ${capped[ch]:,.2f}")
    sum_capped = sum(capped.values())

# Step 5: Unallocated
print("\n── Step 5: Unallocated Savings ──")
unallocated = freed - sum_capped
print(f"  Freed: ${freed:,.2f}  −  Allocated: ${sum_capped:,.2f}  =  Reserve: ${unallocated:,.2f}")

# ══════════════════════════════════════════════════════════════════════════
# FINAL OUTPUT TABLES
# ══════════════════════════════════════════════════════════════════════════
print("\n\n" + "╔" + "═" * 88 + "╗")
print("║" + "  REQUIRED OUTPUT FORMAT".center(88) + "║")
print("╚" + "═" * 88 + "╝")

# 1. Classification Table
print("\n── 1. Classification Table ──")
print(f"\n{'Channel':<16} {'ROAS':>8} {'% of Tgt':>10} {'CPA':>10} {'% of Max':>10} {'Net Profit':>13} {'Classification':<20}")
print("-" * 92)
for ch in ["Facebook_Ads", "Google_Ads", "TikTok_Ads", "Email"]:
    m = metrics[ch]
    roas_pct = (m["roas"] / TARGET_ROAS) * 100
    cpa_pct = (m["cpa"] / MAX_CPA) * 100
    print(f"{ch:<16} {m['roas']:>7.2f}x {roas_pct:>9.0f}% "
          f"${m['cpa']:>9,.2f} {cpa_pct:>9.0f}% "
          f"${m['net_profit']:>12,.2f}  {classifications[ch]:<20}")

# 2. Calculation Steps
print("\n── 2. Calculation Steps ──")
print(f"""
  Freed Budget: ${freed:,.2f} (from TikTok DECREASE_HEAVY −45%)

  Allocation Weights (by Net Profit):
""")
for ch in increase_channels:
    weight = metrics[ch]["net_profit"] / total_np
    print(f"    {ch}: ${metrics[ch]['net_profit']:,.2f} / ${total_np:,.2f} = {weight:.1%}")

print(f"""
  Proposed vs. Capped Increases:
""")
for ch in increase_channels:
    max_inc = metrics[ch]["spend"] * INCREASE_CAP
    print(f"    {ch}: proposed ${proposed[ch]:,.2f} → capped at ${capped[ch]:,.2f} "
          f"(max ${max_inc:,.2f})")

print(f"""
  Unallocated Savings: ${freed:,.2f} − ${sum_capped:,.2f} = ${unallocated:,.2f}
  → Available for reserve or future reallocation.
""")

# 3. Final Reallocation Table
print("── 3. Final Reallocation Table ──")
print(f"\n{'Channel':<16} {'Current':>12} {'Change %':>10} {'Change $':>12} {'New Budget':>12} {'Classification':<20}")
print("-" * 90)

total_current = 0
total_new = 0
for ch in ["Facebook_Ads", "Google_Ads", "TikTok_Ads", "Email"]:
    current = metrics[ch]["spend"]
    cls = classifications[ch]
    pct = CHANGE_PCT[cls]

    if pct < 0:
        change_dollar = current * pct
    elif cls == "INCREASE":
        change_dollar = capped[ch]
        pct = change_dollar / current
    else:
        change_dollar = 0.0

    new_budget = current + change_dollar
    total_current += current
    total_new += new_budget

    pct_str = f"{pct:+.1%}" if pct != 0 else "0%"
    print(f"{ch:<16} ${current:>11,.2f} {pct_str:>10} ${change_dollar:>11,.2f} ${new_budget:>11,.2f}  {cls:<20}")

# Reserve row
print(f"{'Reserve':<16} {'—':>12} {'—':>10} ${unallocated:>11,.2f} {'—':>12}  {'—':<20}")
total_new += unallocated

print("-" * 90)
print(f"{'TOTAL':<16} ${total_current:>11,.2f} {'':>10} ${total_new - total_current:>11,.2f} ${total_new:>11,.2f}")

# ══════════════════════════════════════════════════════════════════════════
# IMPACT ESTIMATE
# ══════════════════════════════════════════════════════════════════════════
print("\n── Impact Estimate (if efficiency holds) ──")
print(f"\n{'Channel':<16} {'Budget Δ':>12} {'ROAS':>8} {'Est. Rev Δ':>14} {'Est. Profit Δ':>14}")
print("-" * 70)

for ch in ["Facebook_Ads", "Google_Ads", "TikTok_Ads", "Email"]:
    m = metrics[ch]
    current = m["spend"]
    cls = classifications[ch]
    pct = CHANGE_PCT[cls]
    if pct < 0:
        change_dollar = current * pct
    elif cls == "INCREASE":
        change_dollar = capped[ch]
    else:
        change_dollar = 0.0

    rev_delta = change_dollar * m["roas"]
    # Approximate profit delta: revenue change minus spend change, minus product cost on rev change
    profit_delta = rev_delta - change_dollar - (rev_delta * PRODUCT_COST_PCT)

    print(f"{ch:<16} ${change_dollar:>11,.2f} {m['roas']:>7.2f}x "
          f"${rev_delta:>13,.2f} ${profit_delta:>13,.2f}")

print("\n" + "=" * 90)
print("REALLOCATION COMPLETE")
print("=" * 90)
