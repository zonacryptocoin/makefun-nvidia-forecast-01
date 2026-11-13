"""Forecast Polymarket's next NVIDIA CEO prices, minute by minute, 4 hours ahead.

Model: persistence median + per-market spread from recent realised moves.
  - Median: the market's last price (no drift — drift hurt on the practice).
  - Spread: q_tau(h) = x + z_tau * sigma * sqrt(h), clamped to [0, 1], 6 decimals.
  - sigma: per market, from the exponentially weighted mean absolute
    1-minute price change over the last 10 hours (5h halflife, so recent
    moves count more), converted to a normal scale (x1.2533) and shrunk
    (x0.6). A robust scale: the plain std is inflated by rare jumps and
    makes the forecast far too wide; the mean absolute move tracks the
    typical minute.
  - Practice loss ~0.275 vs the house baseline's 0.364 (mean pinball loss).

Reads every <id>.in in $MAKEFUN_INPUT_DIR (else /input), writes <id>.out to
$MAKEFUN_OUTPUT_DIR (else /output). Stdlib only, no network, deterministic.
"""

import json
import math
import os

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.644854, -0.67449, 0.0, 0.67449, 1.644854]
WINDOW_MINUTES = 600          # last 10 hours of 1-minute changes
HALFLIFE_MINUTES = 300        # exponential weight halflife (5h): recent moves count more
SCALE = 1.2533 * 0.6          # mean-abs -> normal scale, then shrink
SIGMA_FLOOR = 0.0002
SIGMA_CAP = 0.01


def price6(x):
    """Clamp to [0, 1], round to 6 decimals (0, never -0)."""
    return round(min(1.0, max(0.0, x)) * 1e6) / 1e6 + 0


def sigma_for(prices):
    """Per-market spread from the exponentially weighted mean absolute
    1-minute change (recent moves count more, so the spread adapts when a
    market's volatility regime changes)."""
    diffs = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]
    w = diffs[-WINDOW_MINUTES:] if len(diffs) > WINDOW_MINUTES else diffs
    if not w:
        return 0.0025
    weighted = 0.0
    weight_sum = 0.0
    for k, v in enumerate(reversed(w)):
        wt = 0.5 ** (k / HALFLIFE_MINUTES)
        weighted += abs(v) * wt
        weight_sum += wt
    mean_abs = weighted / weight_sum
    s = mean_abs * SCALE
    if s < SIGMA_FLOOR:
        s = SIGMA_FLOOR
    if s > SIGMA_CAP:
        s = SIGMA_CAP
    return s


def forecast_market(prices, horizon):
    x = prices[-1]
    s = sigma_for(prices)
    rows = []
    for h in range(1, horizon + 1):
        sp = s * math.sqrt(h)
        row = [price6(x + z * sp) for z in Z]
        for j in range(1, 5):
            if row[j] < row[j - 1]:
                row[j] = row[j - 1]
        rows.append(row)
    return rows


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    inputs = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".in"))
    for fname in inputs:
        case_id = fname[: -len(".in")]
        with open(os.path.join(INPUT_DIR, fname), "r", encoding="utf-8") as fh:
            case = json.load(fh)
        horizon = case["horizon_minutes"]
        forecasts = []
        for m in case["markets"]:
            forecasts.append({
                "id": m["id"],
                "q": forecast_market(m["prices"], horizon),
            })
        out_path = os.path.join(OUTPUT_DIR, case_id + ".out")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"forecasts": forecasts}) + "\n")


if __name__ == "__main__":
    main()
