#!/usr/bin/env python3
"""
backtest_profitview.py — Mechanical backtest of the ProfitView double-breakout (DBO) method.

Rules encoded (from the ProfitView lessons + SmartAlgo SOP guide):
  Levels   A = green then red candle, line at green close; V = red then green, line at red close.
  DBO sell Two V levels (V2 newer and higher than V1), both broken by one same-colour (red) run that
           starts at/above V2; sell limit at V2, stop above the run's head. Buy is the mirror (A levels).
  Zone     Optional higher-TF regular engulfing: sell zone = green then red closing below the green low,
           box = green open..high; buy zone mirrors. Zone fails on a close through the box; entry level
           must sit inside an active same-direction zone. Optional >=3 same-colour candles before the EG.
  Exits    Fixed RR, or SmartAlgo scaled (50% at 1R -> stop BE+0.2, 30% at 2R -> stop 1R, rest at 3R).
Conservative: stop assumed first when stop and target hit in one bar; costs deducted; no lookahead.

Needs: pandas, numpy.   Usage: python backtest_profitview.py --csv GC_5m.csv --tf-mult 12 --max-stop 4
"""

import argparse
import numpy as np
import pandas as pd


def load(csv):
    d = pd.read_csv(csv, index_col=0)
    d.index = pd.to_datetime(d.index, utc=True).tz_convert("America/New_York")
    d = d[["Open", "High", "Low", "Close"]].dropna()
    d.columns = ["o", "h", "l", "c"]
    return d


def zones(df, rule, life, min_run):
    z = df.resample(rule).agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    delta = pd.Timedelta(rule)
    o, h, l, c = (z[k].values for k in "ohlc")
    out = []
    for i in range(1, len(z)):
        green_p, red_p = c[i - 1] > o[i - 1], c[i - 1] < o[i - 1]
        green, red = c[i] > o[i], c[i] < o[i]
        run = 0
        k = i - 1
        while k >= 0 and ((c[k] > o[k]) == green_p) and ((c[k] < o[k]) == red_p) and (green_p or red_p):
            run += 1
            k -= 1
        if green_p and red and c[i] < l[i - 1] and run >= min_run:
            lo, hi, d = o[i - 1], h[i - 1], -1
        elif red_p and green and c[i] > h[i - 1] and run >= min_run:
            lo, hi, d = l[i - 1], o[i - 1], 1
        else:
            continue
        avail = z.index[i] + delta
        fail = None
        for j in range(i + 1, min(i + 1 + life, len(z))):
            if (d == -1 and c[j] > hi) or (d == 1 and c[j] < lo):
                fail = z.index[j] + delta
                break
        out.append((avail, avail + delta * life, fail, d, lo, hi))
    return out


def signals(df, tf_bars_pending, max_stop, buffer=0.2, tfdelta=None, zlist=None, use_zone=True):
    o, h, l, c = (df[k].values for k in "ohlc")
    idx = df.index
    n = len(df)
    Vs, As = [], []  # [price, formed_idx, broken_idx]
    sigs, used = [], set()
    for i in range(1, n):
        if c[i - 1] < o[i - 1] and c[i] > o[i]:
            Vs.append([c[i - 1], i, None])
        if c[i - 1] > o[i - 1] and c[i] < o[i]:
            As.append([c[i - 1], i, None])
        for lv in Vs:
            if lv[2] is None and c[i] < lv[0]:
                lv[2] = i
        for lv in As:
            if lv[2] is None and c[i] > lv[0]:
                lv[2] = i
        for side, levels, cond in ((-1, Vs, c[i] < o[i]), (1, As, c[i] > o[i])):
            if not cond:
                continue
            s = i
            while s - 1 >= 0 and ((c[s - 1] < o[s - 1]) if side == -1 else (c[s - 1] > o[s - 1])):
                s -= 1
            if (side, s) in used:
                continue
            elig = [lv for lv in levels if lv[1] <= s and lv[2] is not None and s <= lv[2] <= i
                    and ((o[s] >= lv[0]) if side == -1 else (o[s] <= lv[0]))]
            if len(elig) < 2:
                continue
            elig.sort(key=lambda x: x[1])
            lv2 = elig[-1]
            lv1 = next((x for x in reversed(elig[:-1]) if ((x[0] < lv2[0]) if side == -1 else (x[0] > lv2[0]))), None)
            if lv1 is None or lv2[2] != i and lv1[2] != i:
                continue
            entry = lv2[0]
            head = h[lv2[1]:i + 1].max() if side == -1 else l[lv2[1]:i + 1].min()
            stop = head + buffer if side == -1 else head - buffer
            dist = abs(stop - entry)
            if dist <= 0 or dist > max_stop:
                continue
            used.add((side, s))
            if use_zone:
                t = idx[i] + tfdelta
                ok = any(a <= t < e and (f is None or t < f) and d == side and lo <= entry <= hi
                         for a, e, f, d, lo, hi in zlist)
                if not ok:
                    continue
            sigs.append((i, side, entry, stop, dist))
    return sigs


def simulate(df, sig, mode, rr, cost, pending, hold):
    o, h, l, c = (df[k].values for k in "ohlc")
    i, side, entry, stop, dist = sig
    n = len(df)
    fill = None
    for j in range(i + 1, min(i + 1 + pending, n)):
        if (side == -1 and h[j] >= entry) or (side == 1 and l[j] <= entry):
            fill = j
            break
    if fill is None:
        return None
    sgn = side  # +1 buy (profit up), -1 sell (profit down)
    price_r = lambda p: (entry - p) / dist if side == -1 else (p - entry) / dist
    tgt = lambda r: entry + sgn * r * dist
    if mode == "fixed":
        legs = [(1.0, rr)]
    else:
        legs = [(0.5, 1.0), (0.3, 2.0), (0.2, 3.0)]
    cur_stop, done, total, remaining = stop, 0, 0.0, 1.0
    for j in range(fill, min(fill + hold, n)):
        hit_stop = (h[j] >= cur_stop) if side == -1 else (l[j] <= cur_stop)
        if hit_stop:
            total += remaining * price_r(cur_stop)
            remaining = 0
            break
        if j == fill:
            continue
        while done < len(legs):
            w, r = legs[done]
            hit = (l[j] <= tgt(r)) if side == -1 else (h[j] >= tgt(r))
            if not hit:
                break
            total += w * r
            remaining -= w
            done += 1
            if mode != "fixed":
                cur_stop = entry + sgn * 0.2 if done == 1 else entry + sgn * dist
        if remaining <= 1e-9:
            break
    if remaining > 1e-9:
        total += remaining * price_r(c[min(fill + hold, n) - 1])
    return total - cost / dist


def stats(rs):
    rs = np.array(rs)
    if len(rs) == 0:
        return {"n": 0}
    eq = np.cumsum(rs)
    dd = (np.maximum.accumulate(eq) - eq).max()
    gp, gl = rs[rs > 0].sum(), -rs[rs < 0].sum()
    rng = np.random.default_rng(1)
    boots = [rng.choice(rs, len(rs)).mean() for _ in range(3000)]
    return {"n": len(rs), "win%": round(100 * (rs > 0).mean(), 1), "avgR": round(rs.mean(), 3),
            "PF": round(gp / gl, 2) if gl > 0 else float("inf"), "totR": round(rs.sum(), 1),
            "maxDD_R": round(dd, 1), "avgR_95CI": (round(np.percentile(boots, 2.5), 2), round(np.percentile(boots, 97.5), 2))}


def random_benchmark(df, sigs, mode, rr, cost, pending, hold, sims=200, seed=7):
    rng = np.random.default_rng(seed)
    c = df["c"].values
    out = []
    for _ in range(sims):
        rs = []
        for (_, side, entry, stop, dist) in sigs:
            j = rng.integers(5, len(df) - hold - 2)
            e = c[j]
            s = e + dist if side == -1 else e - dist
            r = simulate(df, (j, side, e, s, dist), mode, rr, cost, pending, hold)
            if r is not None:
                rs.append(r)
        if rs:
            out.append(np.mean(rs))
    return np.array(out)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", required=True)
    p.add_argument("--zone-rule", default="1h")
    p.add_argument("--zone-life", type=int, default=72)
    p.add_argument("--entry-minutes", type=int, default=5)
    p.add_argument("--max-stop", type=float, default=4.0)
    p.add_argument("--cost", type=float, default=0.4, help="round-trip cost in price units")
    p.add_argument("--pending", type=int, default=18)
    p.add_argument("--hold", type=int, default=288)
    p.add_argument("--min-run", type=int, default=1)
    a = p.parse_args()
    df = load(a.csv)
    tfd = pd.Timedelta(minutes=a.entry_minutes)
    print(f"{len(df)} bars {df.index.min()} -> {df.index.max()}")
    zl = zones(df, a.zone_rule, a.zone_life, a.min_run)
    print(f"{len(zl)} zones ({a.zone_rule}, min_run={a.min_run})")
    for use_zone in (False, True):
        sg = signals(df, a.pending, a.max_stop, tfdelta=tfd, zlist=zl, use_zone=use_zone)
        print(f"\n=== {'DBO + zone' if use_zone else 'DBO only (no zone)'}: {len(sg)} signals, max stop {a.max_stop}")
        for mode, rr in (("fixed", 1), ("fixed", 2), ("fixed", 3), ("fixed", 4), ("scaled", 0)):
            rs = [r for r in (simulate(df, s, mode, rr, a.cost, a.pending, a.hold) for s in sg) if r is not None]
            st = stats(rs)
            line = f"{mode}{rr or ''}: {st}"
            if rs:
                b = random_benchmark(df, sg, mode, rr, a.cost, a.pending, a.hold)
                line += f" | random-entry mean {b.mean():.3f}, strategy beats {100*(b<np.mean(rs)).mean():.0f}% of random runs"
            print(line)


if __name__ == "__main__":
    main()
