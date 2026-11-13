# Polymarket NVIDIA CEO price forecaster

Entry for the make.fun bounty
[polymarket-nvidia-ceo-forecast-01](https://make.fun/bounty/polymarket-nvidia-ceo-forecast-01)
— forecast every trading market of Polymarket's "Next CEO of NVIDIA?" event,
minute by minute, 4 hours ahead, as 5 quantiles (5/25/50/75/95%).

## Model

`main.py` (Python 3.13, stdlib only, no network, deterministic) reads the
case file and writes one forecast per market:

- **Median: persistence.** The market's last price. No drift — adding a drift
  from recent moves hurt on the practice cases.
- **Spread: a random-walk widening** `q_tau(h) = x + z_tau * sigma * sqrt(h)`,
  clamped to [0, 1], rounded to 6 decimals.
- **sigma: per market**, from the exponentially weighted mean absolute
  1-minute price change over the last 10 hours (5h halflife, so recent
  moves count more), converted to a normal scale (x1.2533) and shrunk
  (x0.6), floored at 0.0002 and capped at 0.01. A robust scale: the plain
  std is inflated by rare jumps and makes the forecast far too wide; the
  mean absolute move tracks the typical minute.

## Practice result

Mean pinball loss on the six practice cases (scored against Polymarket's own
history, fetched and gridded the same way the house does): **0.275**, vs the
house baseline's **0.364** — about 24% better. Runtime ~0.05 s per case
(limit 8 s); output is byte-identical across runs.

## License

MIT — see LICENSE.
